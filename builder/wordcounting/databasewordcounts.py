# -*- coding: utf-8 -*-
# !../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque
from itertools import chain
from multiprocessing import Pool
from statistics import mean, median
from string import punctuation

from builder.builderclasses import dbWordCountObject
from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbdataintoobjects import graballcountsasobjects, grablemmataasobjects, \
	grablineobjectsfromlist, loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors
from builder.dbinteraction.dbloading import generatecopystream
from builder.wordcounting.wordcountdbfunctions import createwordcounttable, insertchronologicalmetadata, \
	insertgenremetadata
from builder.wordcounting.wordcounthelperfunctions import acuteforgrave, cleanwords, dictmerger, \
	prettyprintcohortdata
from builder.workers import setworkercount


def wordcounter(restriction=None, authordict=None, workdict=None):
	"""

	:return:
	"""
	wordcounttable = 'wordcounts'

	if not authordict:
		authordict = loadallauthorsasobjects()
		workdict = loadallworksasobjects()
		authordict = loadallworksintoallauthors(authordict, workdict)

	# [a] figure out which works we are looking for: [universalid1, universalid2, ...]
	idlist = generatesearchidlist(restriction, authordict, workdict)

	# [b] figure out what table index values we will need to assemble them: {tableid1: range1, tableid2: range2, ...}

	dbdictwithranges = generatedbdictwithranges(idlist, authordict, workdict)

	# [c] divide up the work evenly: {1: {tableid1: range1, tableid2: range2, ...}, 2: {tableidX: rangeX, tableidY: rangeY, ...}
	scopes = {key: len(list(dbdictwithranges[key])) for key in dbdictwithranges}

	# dbdictwithranges was exhausted, it needs to be regenerated
	dbdictwithranges = generatedbdictwithranges(idlist, authordict, workdict)

	numberofpiles = setworkercount()
	totalpilesize = sum(scopes[key] for key in scopes)
	maxindividualpilesize = totalpilesize / numberofpiles

	workpiles = dict()
	thispilenumber = 0
	currentpilesize = 0
	for key in dbdictwithranges:
		currentpilesize += scopes[key]
		if currentpilesize < maxindividualpilesize:
			# print('key: currentpilesize < maxindividualpilesize - {k}: {c} < {m}'.format(k=key, c=currentpilesize, m=maxindividualpilesize))
			try:
				workpiles[thispilenumber].append((key, dbdictwithranges[key]))
			except KeyError:
				workpiles[thispilenumber] = [(key, dbdictwithranges[key])]
		else:
			currentpilesize = 0
			thispilenumber += 1
			workpiles[thispilenumber] = [(key, dbdictwithranges[key])]

	# [d] send the work off for processing

	with Pool(processes=numberofpiles) as pool:
		getlistofdictionaries = [pool.apply_async(buildindexdictionary, (i, workpiles[i])) for i in range(numberofpiles)]

		# you were returned [ApplyResult1, ApplyResult2, ...]
		listofdictionaries = [result.get() for result in getlistofdictionaries]

	# [e] merge the results
	masterconcorcdance = concordancemerger(listofdictionaries)

	# [f] build the tables if needed
	if not restriction:
		generatewordcounttablesonfirstpass(wordcounttable, masterconcorcdance)

	return masterconcorcdance


def generatesearchidlist(restriction, authordict, workdict):
	"""

	need to know all of the lines you will need to examine in all of the works you will need to examine

	this will return a list of workids OR a list of authorids depending on your restriction

	[universalid1, universalid2, ...]

	:return:
	"""

	searchlist = list()

	if not authordict:
		authordict = loadallauthorsasobjects()

	if restriction:
		if not workdict:
			workdict = loadallworksasobjects()

		try:
			tr = restriction['time']
			# restriction should be a date range tuple (-850,300), e.g.
			searchlist = [key for key in authordict.keys() if
			              authordict[key].converted_date and tr[0] < int(authordict[key].converted_date) < tr[1]]
			searchlist += [key for key in workdict.keys() if
			               workdict[key].converted_date and tr[0] < int(workdict[key].converted_date) < tr[1]]
		except KeyError:
			# no such restriction
			pass
		try:
			restriction['genre']
			# restriction will be an item from the list of known genres
			searchlist = [key for key in workdict.keys() if workdict[key].workgenre == restriction['genre']]
		except KeyError:
			# no such restriction
			pass
	else:
		searchlist = list(authordict.keys())

	return searchlist


def generatedbdictwithranges(idlist, authordict, workdict):
	"""

	given a list of universalids, convert this list into a dictionary with authorid keys (ie, table names)

	each id will be associated with a range of line numbers that need to be pulled from that author table

	{tableid1: range1, tableid2: range2, ...}

	:return:
	"""

	dbswithranges = dict()
	for db in idlist:
		if len(db) == 6:
			# we are reading a full author
			dbswithranges[db] = [range(authordict[db].findfirstlinenumber(), authordict[db].findlastlinenumber()+1)]
		else:
			# we are reading an individual work
			try:
				dbswithranges[db[0:6]].append([range(workdict[db].starts, workdict[db].ends+1)])
			except KeyError:
				dbswithranges[db[0:6]] = [range(workdict[db].starts, workdict[db].ends+1)]

	dbswithranges = {key: chain.from_iterable(dbswithranges[key]) for key in dbswithranges}

	return dbswithranges


def buildindexdictionary(pilenumber, workpiles):
	"""

	a workpile looks like:

		[('gr1346', <itertools.chain object at 0x10a858898>), ('gr3136', <itertools.chain object at 0x10d81e898>), ...]

	:return:
	"""

	dbconnection = setconnection(autocommit=True, simple=True)
	dbcursor = dbconnection.cursor()

	print('worker #{p} gathering lines'.format(p=pilenumber))

	graves = re.compile(r'[ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ]')
	# pull this out of cleanwords() so you don't waste cycles recompiling it millions of times: massive speedup
	punct = re.compile('[%s]' % re.escape(punctuation + '\′‵’‘·“”„—†⌈⌋⌊∣⎜͙ˈͻ✳※¶§⸨⸩｟｠⟫⟪❵❴⟧⟦→◦⊚𐄂𝕔☩(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'))

	# grab all lines
	lineobjects = deque()
	for w in workpiles:
		# w ('gr1346', <itertools.chain object at 0x10a858898>)
		lineobjects.extend(grablineobjectsfromlist(w[0], w[1], dbcursor))

	print('worker #{p} gathered {n} lines'.format(p=pilenumber, n=len(lineobjects)))

	# debug
	lineobjects = list(lineobjects)
	lineobjects = lineobjects[:10000]

	progresschunks = int(len(lineobjects) / 4)

	indexdictionary = dict()

	index = 0
	for line in lineobjects:
		words = line.wordlist('polytonic')
		words = [cleanwords(w, punct) for w in words]
		words = [re.sub(graves, acuteforgrave, w) for w in words]
		words = [re.sub('v', 'u', w) for w in words]
		words[:] = [x.lower() for x in words]
		prefix = line.universalid[0:2]
		for w in words:
			# uncomment to watch individual words enter the dict
			# if w == 'docilem':
			# 	print(line.universalid,line.unformattedline())
			try:
				indexdictionary[w][prefix] += 1
			except KeyError:
				indexdictionary[w] = dict()
				indexdictionary[w][prefix] = 1
		index += 1
		if index % progresschunks == 0:
			percent = round((index / len(lineobjects)) * 100, 1)
			print('worker #{p} progress: {n}%'.format(p=pilenumber, n=percent))
			# uncomment to see where we stand with a given set of words
			# if line.universalid[0:2] == 'lt':
			# 	print('worker #{p}  @ line.universalid {u}'.format(p=pilenumber, u=line.universalid))
			# 	print('\t{ln}'.format(ln=line.wordlist('polytonic')))
			# 	for w in line.wordlist('polytonic'):
			# 		try:
			# 			print(w, indexdictionary[w][line.universalid[0:2]])
			# 		except:
			# 			print('{w} not in indexdictionary'.format(w=w))

	return indexdictionary


def concordancemerger(listofconcordancedicts):
	"""

	:return:
	"""

	print('merging the partial results')
	try:
		masterconcorcdance = listofconcordancedicts.pop()
	except IndexError:
		masterconcorcdance = dict()

	for cd in listofconcordancedicts:
		# find the 'gr' in something like {'τότοιν': {'gr': 1}}
		tdk = list(cd.keys())
		tdl = list(cd[tdk[0]].keys())
		label = tdl[0]
		masterconcorcdance = dictmerger(masterconcorcdance, cd, label)

	# test
	# Sought » θήϲομαί «
	# Searched 7,461 texts and found 26 passages (0.71s)

	# print('masterconcorcdance["θήϲομαί"]', masterconcorcdance["θήϲομαί"])

	# add the zeros and do the sums
	print('summing the finds')
	for word in masterconcorcdance:
		for db in ['gr', 'lt', 'in', 'dp', 'ch']:
			if db not in masterconcorcdance[word]:
				masterconcorcdance[word][db] = 0
		masterconcorcdance[word]['total'] = sum([masterconcorcdance[word][x] for x in masterconcorcdance[word]])

	return masterconcorcdance


def generatewordcounttablesonfirstpass(wordcounttable, masterconcorcdance):
	"""

	no restriction: then this is our first pass and we should write the results to the master counts
	restriction implies subsequent passes that are for metadata derived from unrestricted data;
	these passes should not overwrite that data

	:return:
	"""
	dbcconnection = setconnection()
	dbcursor = dbcconnection.cursor()

	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	for letter in letters:
		createwordcounttable('{w}_{l}'.format(w=wordcounttable, l=letter))

	columns = ('entry_name',
				'total_count',
				'gr_count',
				'lt_count',
				'dp_count',
				'in_count',
				'ch_count')

	separator = '\t'

	for letter in letters:
		print('generating {l}'.format(l=letter))
		queryvalues = generatemasterconcorcdancevaluetuples(masterconcorcdance, letter)
		stream = generatecopystream(queryvalues, separator=separator)
		table = '{w}_{l}'.format(w=wordcounttable, l=letter)
		dbcursor.copy_from(stream, table, sep=separator, columns=columns)

	dbcconnection.connectioncleanup()

	return


def generatemasterconcorcdancevaluetuples(masterconcorcdance, letter):
	"""

	entries look like:
		'θήϲομαί': {'gr': 1, 'lt': 0, 'in': 0, 'dp': 0, 'ch': 0, 'total': 1}


	:param masterconcorcdance:
	:param letter:
	:return:
	"""

	validletters = 'abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'

	valuetuples = deque()

	# oddly it seems you cen get null keys...
	# key[0] can give you an IndexError

	if letter != '0':
		subset = {key: masterconcorcdance[key] for key in masterconcorcdance if key and key[0] == letter}
	else:
		subset = {key: masterconcorcdance[key] for key in masterconcorcdance if key and key[0] not in validletters}

	for item in subset:
		valuetuples.append(tuple([item, subset[item]['total'], subset[item]['gr'], subset[item]['lt'], subset[item]['dp'], subset[item]['in'], subset[item]['ch']]))

	return valuetuples

# oldcode


def headwordcounts():
	"""

	count morphological forms using the wordcount data

	[a] grab all possible forms of all dictionary words
	[b] count all hits of all forms of those words
	[c1] record the hits
	[c2] record statistics about those hits

	:return:
	"""

	dbc = setconnection()
	cursor = dbc.cursor()

	# loading is slow: avoid doing it 2x
	lemmataobjectslist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)

	# 'v' should be empty, though; ϙ will go to 0
	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	letters = {letters[l] for l in range(0, len(letters))}
	countobjectlist = list()
	for l in letters:
		countobjectlist += graballcountsasobjects('wordcounts_' + l, cursor)
	countdict = {word.entryname: word for word in countobjectlist}
	del countobjectlist

	dictionarycounts = buildcountsfromlemmalist(lemmataobjectslist, countdict)

	"""
	75 items return from:
		select * from works where workgenre IS NULL and universalid like 'gr%'

	will model the other DBs after this
	will also add Agric. as a genre for LAT

	"""

	knownworkgenres = [
		'Acta',
		'Agric.',
		'Alchem.',
		'Anthol.',
		'Apocalyp.',
		'Apocryph.',
		'Apol.',
		'Astrol.',
		'Astron.',
		'Biogr.',
		'Bucol.',
		'Caten.',
		'Chronogr.',
		'Comic.',
		'Comm.',
		'Concil.',
		'Coq.',
		'Dialog.',
		'Docu.',
		'Doxogr.',
		'Eccl.',
		'Eleg.',
		'Encom.',
		'Epic.',
		'Epigr.',
		'Epist.',
		'Evangel.',
		'Exeget.',
		'Fab.',
		'Geogr.',
		'Gnom.',
		'Gramm.',
		'Hagiogr.',
		'Hexametr.',
		'Hist.',
		'Homilet.',
		'Hymn.',
		'Hypoth.',
		'Iamb.',
		'Ignotum',
		'Invectiv.',
		'Inscr.',
		'Jurisprud.',
		'Lexicogr.',
		'Liturg.',
		'Lyr.',
		'Magica',
		'Math.',
		'Mech.',
		'Med.',
		'Metrolog.',
		'Mim.',
		'Mus.',
		'Myth.',
		'Narr. Fict.',
		'Nat. Hist.',
		'Onir.',
		'Orac.',
		'Orat.',
		'Paradox.',
		'Parod.',
		'Paroem.',
		'Perieg.',
		'Phil.',
		'Physiognom.',
		'Poem.',
		'Polyhist.',
		'Prophet.',
		'Pseudepigr.',
		'Rhet.',
		'Satura',
		'Satyr.',
		'Schol.',
		'Tact.',
		'Test.',
		'Theol.',
		'Trag.'
	]

	# test for a single genre
	# knownworkgenres = ['Satura']

	cleanedknownworkgenres = [g.lower() for g in knownworkgenres]
	cleanedknownworkgenres = [re.sub(r'[\.\s]', '', g) for g in cleanedknownworkgenres]

	thetable = 'dictionary_headword_wordcounts'
	createwordcounttable(thetable, extracolumns=cleanedknownworkgenres)

	# note that entries are stored under their 'analysis name' ('ἀμφί-λαμβάνω', etc.) and not their LSJ name

	commitcount = 0
	keys = dictionarycounts.keys()
	keys = sorted(keys)
	for word in keys:
		commitcount += 1
		q = 'INSERT INTO {tb} (entry_name, total_count, gr_count, lt_count, dp_count, in_count, ch_count) ' \
		    'VALUES (%s, %s, %s, %s, %s, %s, %s)'.format(tb=thetable)
		d = (word, dictionarycounts[word]['total'], dictionarycounts[word]['gr'], dictionarycounts[word]['lt'],
		     dictionarycounts[word]['dp'], dictionarycounts[word]['in'], dictionarycounts[word]['ch'])
		cursor.execute(q, d)
		if commitcount % 2500 == 0:
			dbc.commit()
	dbc.commit()

	# now figure out and record the percentiles
	# derivedictionaryentrymetadata() will generate one set of numbers
	# then it will call derivechronologicalmetadata() to supplement those numbers
	# then you can call derivegenremetadata() to add still more information

	thetable = 'dictionary_headword_wordcounts'
	metadata = derivedictionaryentrymetadata(thetable, cursor)
	lemmataobjectslist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)
	metadata = derivechronologicalmetadata(metadata, lemmataobjectslist)
	metadata = insertchronologicalmetadata(metadata, thetable)
	metadata = derivegenremetadata(metadata, lemmataobjectslist, thetable, knownworkgenres)

	# print('ἅρπαξ',metadata['ἅρπαξ'])
	# ἅρπαξ {'frequency_classification': 'core vocabulary (more than 50)', 'early': 42, 'middle': 113, 'late': 468}
	# print('stuprum',metadata['stuprum'])

	dbc.connectioncleanup()

	return metadata


def buildcountsfromlemmalist(lemmataobjectslist, wordcountdict):
	"""

	given a list of lemmata objects, build a dictionary of statistics
	about how often the various forms under that dictionary heading are used

	check each item on the list of possible forms against a master dict of observed forms

	return a dictionary of lexicon entry keywords and the associated totals of all observed forms

	countdict['euulgato']
	<builder.builder_classes.dbWordCountObject object at 0x1364d61d0>
	countdict['euulgato'].t
	1


	:param lemmataobjectslist:
	:return:
	"""

	lexiconentrycounts = dict()

	for lem in lemmataobjectslist:
		thewordtolookfor = lem.dictionaryentry
		# comprehensions would be nice, but they fail because of exceptions
		lexiconentrycounts[thewordtolookfor] = dict()
		for item in ['total', 'gr', 'lt', 'dp', 'in', 'ch']:
			sum = 0
			for form in lem.formlist:
				# need to make sure that u/v and apostrophes, etc. have all been addressed
				# that is, the forms in the formlist need to match what is found in the texts
				# but the formlists were generated with differently processed data
				try:
					sum += wordcountdict[form].getelement(item)
				except KeyError:
					# word not found
					pass
			lexiconentrycounts[thewordtolookfor][item] = sum

	return lexiconentrycounts


def derivedictionaryentrymetadata(headwordtable, cursor):
	"""

	now that you know how many times a word occurs, put that number into perspective

	:param cursor:
	:return:
	"""

	metadata = dict()

	extrasql = ' ORDER BY total_count DESC'
	greekvowel = re.compile(r'[άέίόύήώἄἔἴὄὔἤὤᾅᾕᾥᾄᾔᾤαειουηω]')

	headwordobjects = graballcountsasobjects(headwordtable, cursor, extrasql)

	# the number of words with 0 as its total reflects parsing problems that need fixing elsewhere
	greek = [w for w in headwordobjects if re.search(greekvowel, w.entryname) and w.t > 0]
	latin = [w for w in headwordobjects if re.search(r'[a-z]', w.entryname) and w.t > 0]

	for dataset in [(greek, 'greek'), (latin, 'latin')]:
		d = dataset[0]
		label = dataset[1]
		mostcommon = d[:250]
		common = d[250:2500]
		remainder = d[2500:]
		veryrare = [x for x in remainder if x.t < 5]
		rare = [x for x in remainder if 5 < x.t < 51]
		core = [x for x in remainder if x.t > 50 and (x not in common or x not in mostcommon)]
		explorecore = False
		if explorecore:
			# slice it into 10 bundles
			chunksize = int(len(core) / 10)
			chunks = [core[i:i + chunksize] for i in range(0, len(core), chunksize)]
			chunkstats = dict()
			for chunkid, chunk in enumerate(chunks):
				chunkstats[chunkid] = cohortstats(chunk)

		printstats = False
		for item in [
			('full set', d),
			('top 250', mostcommon),
			('top 2500', common),
			('core (>50 occurrences; not in top 2500)', core),
			('rare (between 50 and 5 occurrences)', rare),
			('very rare (fewer than 5 occurrences)', veryrare),
		]:
			if printstats:
				if item == ('full set', d):
					print('\n', label)
				prettyprintcohortdata(item[0], cohortstats(item[1]))
			if item[0] != 'full set':
				for entry in item[1]:
					metadata[entry.entryname] = {'frequency_classification': item[0]}

	return metadata


def derivechronologicalmetadata(metadata, lemmataobjectlist):
	"""

	find frequencies by eras:
		-850 to -300
		-299 to 300
		301 to 1500

	attach this data to our existing metadata which is keyed to dictionary entry

	:param metadata:
	:return:
	"""

	eras = {'early': (-850, -300), 'middle': (-299, 300), 'late': (301, 1500)}
	authordict = loadallauthorsasobjects()
	workdict = loadallworksasobjects()

	for era in eras:
		print('calculating use by era:', era)
		eraconcordance = wordcounter(restriction={'time': eras[era]}, authordict=authordict, workdict=workdict)
		# close, but we need to match the template above:
		# countdict = {word.entryname: word for word in countobjectlist}
		countobjectlist = [
			dbWordCountObject(w, eraconcordance[w]['total'], eraconcordance[w]['gr'], eraconcordance[w]['lt'],
			                  eraconcordance[w]['dp'], eraconcordance[w]['in'], eraconcordance[w]['ch']) for w in
			eraconcordance]
		countdict = {word.entryname: word for word in countobjectlist}
		lexiconentrycounts = buildcountsfromlemmalist(lemmataobjectlist, countdict)
		for entry in lexiconentrycounts:
			try:
				metadata[entry]
			except KeyError:
				metadata[entry] = dict()
			metadata[entry][era] = lexiconentrycounts[entry]['total']

	return metadata


def derivegenremetadata(metadata, lemmataobjectlist, thetable, knownworkgenres):
	"""

	can/should do 'Inscr.' separately? It's just the sum of 'in' + 'ch'

	:param metadata:
	:param cursor:
	:return:
	"""

	authordict = loadallauthorsasobjects()
	workdict = loadallworksasobjects()

	for genre in knownworkgenres:
		print('compiling metadata for', genre)
		genrecordance = wordcounter(restriction={'genre': genre}, authordict=authordict, workdict=workdict)
		countobjectlist = [
			dbWordCountObject(w, genrecordance[w]['total'], genrecordance[w]['gr'], genrecordance[w]['lt'],
			                  genrecordance[w]['dp'], genrecordance[w]['in'], genrecordance[w]['ch']) for w in
			genrecordance]
		countdict = {word.entryname: word for word in countobjectlist}
		lexiconentrycounts = buildcountsfromlemmalist(lemmataobjectlist, countdict)
		for entry in lexiconentrycounts:
			try:
				metadata[entry]
			except KeyError:
				metadata[entry] = dict()
			metadata[entry][genre] = lexiconentrycounts[entry]['total']
		print('inserting metadata for', genre)
		insertgenremetadata(metadata, genre, thetable)

	return metadata


def cohortstats(wordobjects):
	"""

	take a cluster and generate stats for it

	:param wordobjects:
	:return:
	"""

	totals = [word.t for word in wordobjects]
	high = max(totals)
	low = min(totals)
	avg = mean(totals)
	med = median(totals)
	returndict = {'h': high, 'l': low, 'a': avg, 'm': med, '#': len(wordobjects)}

	return returndict



"""
you get 334 rows if you:
	select * from authors where genres IS NULL and universalid like 'gr%'
"""

knownauthorgenres = [
	'Alchemistae',
	'Apologetici',
	'Astrologici',
	'Astronomici',
	'Atticistae',
	'Biographi',
	'Bucolici',
	'Choliambographi',
	'Chronographi',
	'Comici',
	'Doxographi',
	'Elegiaci',
	'Epici',
	'Epigrammatici',
	'Epistolographi',
	'Geographi',
	'Geometri',
	'Gnomici',
	'Gnostici',
	'Grammatici',
	'Hagiographi',
	'Historici',
	'Hymnographi',
	'Iambici',
	'Lexicographi',
	'Lyrici',
	'Mathematici',
	'Mechanici',
	'Medici',
	'Mimographi',
	'Musici',
	'Mythographi',
	'Nomographi',
	'Onirocritici',
	'Oratores',
	'Paradoxographi',
	'Parodii',
	'Paroemiographi',
	'Periegetae',
	'Philologi',
	'Philosophici',
	'Poetae',
	'Poetae Didactici',
	'Poetae Medici',
	'Poetae Philosophi',
	'Polyhistorici',
	'Rhetorici',
	'Scriptores Ecclesiastici',
	'Scriptores Erotici',
	'Scriptores Fabularum',
	'Scriptores Rerum Naturalium',
	'Sophistae',
	'Tactici',
	'Theologici',
	'Tragici'
]

"""
manual testing/probing

Python 3.6.2 (default, Jul 17 2017, 16:44:45)
[GCC 4.2.1 Compatible Apple LLVM 8.1.0 (clang-802.0.42)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import configparser
>>> config = configparser.ConfigParser()
>>> config.read('config.ini')
>>> from builder.dbinteraction.connection import setconnection
>>> dbc = setconnection()
>>> cursor = dbc.cursor()
>>> from builder.postbuild.postbuildhelperfunctions import graballlinesasobjects, acuteforgrave, graballcountsasobjects, grablemmataasobjects, createwordcounttable, cleanwords, prettyprintcohortdata, dictmerger
>>> lemmataobjectslist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)
>>> allletters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
>>> letters = {allletters[l] for l in range(0, len(allletters))}
>>> countobjectlist = list()
>>> for l in letters: countobjectlist += graballcountsasobjects('wordcounts_' + l, cursor)
...
>>> countdict = {word.entryname: word for word in countobjectlist}
>>> del countobjectlist
>>> from builder.postbuild.databasewordcounts import buildcountsfromlemmalist
>>> dictionarycounts = buildcountsfromlemmalist(lemmataobjectslist, countdict)
>>> from builder.postbuild.databasewordcounts import derivedictionaryentrymetadata
>>> thetable = 'dictionary_headword_wordcounts'
>>> metadata = derivedictionaryentrymetadata(thetable, cursor)
>>> metadata['φεῦ']
{'frequency_classification': 'core (>50 occurrences; not in top 2500)', 'Iamb.': 17}
>>> x = {m for m in metadata if m['Iamb.'] > 0}



"""


"""

pulling results from asyncio...


async def factorial(name, number):
	f = 1
	for i in range(2, number+1):
		print("Task %s: Compute factorial(%s)..." % (name, i))
		await asyncio.sleep(.5)
		f *= i
	print("Task %s: factorial(%s) = %s" % (name, number, f))
	return f

loop = asyncio.get_event_loop()

arguments = [("A", 2), ("B", 3), ("C", 4)]
sm = starmap(factorial, arguments)
results = asyncio.gather(*[x for x in sm])

loop.run_until_complete(results)

print(results.result())
for r in results.result():
	print(r)

loop.close()


# this works: but it also blocks...
# https://stackoverflow.com/questions/15143837/how-to-multi-thread-an-operation-within-a-loop-in-python

wordcounterloop = asyncio.new_event_loop()
asyncio.set_event_loop(wordcounterloop)

connections = {i: setconnection(autocommit=True) for i in range(numberofpiles)}
cursors = {i: connections[i].cursor() for i in range(numberofpiles)}

argumentstopass = [(pilenumber, workpiles[pilenumber], cursors[pilenumber]) for pilenumber in workpiles]
functionstogather = starmap(buildindexdictionary, argumentstopass)

getlistofdictionaries = asyncio.gather(*[x for x in functionstogather], loop=wordcounterloop)

wordcounterloop.run_until_complete(getlistofdictionaries)
listofdictionaries = getlistofdictionaries.result()
wordcounterloop.close()


"""

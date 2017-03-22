# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import configparser
import re
from multiprocessing import Pool
from statistics import mean, median
from string import punctuation

from builder.builder_classes import dbWordCountObject
from builder.dbinteraction.db import setconnection, loadallauthorsasobjects, loadallworksasobjects
from builder.parsers.betacode_to_unicode import cleanaccentsandvj
from builder.postbuild.postbuildhelperfunctions import forceterminalacute, graballlinesasobjects, \
	graballcountsasobjects, grablemmataasobjects, createwordcounttable, cleanwords, prettyprintcohortdata, dictmerger

config = configparser.ConfigParser()
config.read('config.ini')


def wordcounter(restriction=None):
	"""

	count all of the words in all of the dbs or a subset thereof: 'restriction' will do subsets

	restriction is either a list of time tuples or a list of genre names associated with a dict key

	:param timerestriction:
	:return:
	"""
	wordcounttable = 'wordcounts'

	authordict = loadallauthorsasobjects()

	if restriction:
		workdict = loadallworksasobjects()
		try:
			tr = restriction['time']
			# restriction should be a date range tuple (-850,300), e.g.
			dbs = [key for key in authordict.keys() if authordict[key].converted_date and tr[0] < int(authordict[key].converted_date) < tr[1]]
			dbs += [key for key in workdict.keys() if workdict[key].converted_date and tr[0] < int(workdict[key].converted_date) < tr[1]]
			# mostly lots of little dicts: notifications get spammy
			chunksize = 350
		except KeyError:
			# no such restriction
			pass
		try:
			restriction['genre']
			# restriction will be an item from the list of known genres
			dbs = [key for key in workdict.keys() if workdict[key].workgenre == restriction['genre']]
			chunksize = 20
		except KeyError:
			# no such restriction
			pass
	else:
		chunksize = 200
		dbs = list(authordict.keys())

	# limit to NN for testing purposes
	# dbs = dbs[101:102]

	datasets = set([db[0:2] for db in dbs])
	dbswithranges = {}
	for db in dbs:
		if len(db) == 6:
			# we are reading a full author
			dbswithranges[db] = (-1,-1)
		else:
			# we are reading an individual work
			dbswithranges[db] = (workdict[db].starts, workdict[db].ends)

	dictofdbdicts = {dset:{db: dbswithranges[db] for db in dbswithranges if db[0:2] == dset} for dset in datasets}
	listofworkdicts = [dictofdbdicts[key] for key in dictofdbdicts]


	# parallelize by sending each db to its own worker: 291 ch tables to check; 463 in tables to check; 1823 gr tables to check; 362 lt tables to check; 516 dp tables to check
	# 'gr' is much bigger than the others, though let's split that one up
	# nb: many of the tables are very small and the longest ones cluster in related numerical zones; there is a tendency to drop down to a wait for 1 or 2 final threads
	# when we run through again with the time restriction there will be a massive number of chunks

	# chunksize = 200
	chunked = []

	for l in listofworkdicts:
		keys = list(l.keys())
		count = 0
		while keys:
			count += 1
			chunk = {}
			for p in range(0,chunksize):
				try:
					k = keys.pop()
					chunk[k] = l[k]
				except:
					pass
			try:
				chunked += [chunk]
			except:
				# you hit the pop exception on the first try
				pass

	# a chunk will look like:
	# {'in0010w0be': (173145, 173145), 'in0010w0bd': (173144, 173144), 'in0010w0bf': (173146, 173146), 'in0010w0bg': (173147, 173147), 'in0010w0bi': (173149, 173149), 'in0010w0bh': (173148, 173148)}

	# a genre chunk:
	# Invectiv.
	# [{'gr2022w019': (22221, 23299), 'gr2022w018': (19678, 22220), 'gr0062w049': (28525, 29068), 'gr0062w038': (20977, 22028), 'gr0062w042': (23956, 24575), 'gr0062w028': (14516, 15055)}]

	print('breaking up the lists and parallelizing:', len(chunked),'chunks to analyze')
	# safe to almost hit number of cores here since we are not doing both db and regex simultaneously in each thread
	# here's hoping that the workers number was not over-ambitious to begin with

	bigpool = int(config['io']['workers'])+(int(config['io']['workers'])/2)
	with Pool(processes=int(bigpool)) as pool:
		listofconcordancedicts = pool.map(concordancechunk, enumerate(chunked))

	# merge the results
	print('merging the partial results')
	try:
		masterconcorcdance = listofconcordancedicts.pop()
	except IndexError:
		masterconcorcdance = {}

	for cd in listofconcordancedicts:
		# find the 'gr' in something like {'τότοιν': {'gr': 1}}
		tdk = list(cd.keys())
		tdl = list(cd[tdk[0]].keys())
		label = tdl[0]
		masterconcorcdance = dictmerger(masterconcorcdance, cd, label)

	# add the zeros and do the sums
	print('summing the finds')
	for word in masterconcorcdance:
		for db in ['gr', 'lt', 'in', 'dp', 'ch']:
			if db not in masterconcorcdance[word]:
				masterconcorcdance[word][db] = 0
		masterconcorcdance[word]['total'] = sum([masterconcorcdance[word][x] for x in masterconcorcdance[word]])

	if restriction == None:
		# no restriction: then this is our first pass and we should write the results to the master counts
		# restriction implies subsequent passes that are for metadata derived from unrestricted data;
		# these passes should not overwrite that data

		letters= '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
		for l in letters:
			createwordcounttable(wordcounttable + '_' + l)

		wordkeys = list(masterconcorcdance.keys())
		wordkeys = sorted(wordkeys)
		print(len(wordkeys),'unique items to catalog (nb: plenty of these are word fragments and not whole words)')

		chunksize = 100000
		chunkedkeys = [wordkeys[i:i + chunksize] for i in range(0, len(wordkeys), chunksize)]
		argmap = [(c, masterconcorcdance, wordcounttable) for c in enumerate(chunkedkeys)]
		print('breaking up the lists and parallelizing:', len(chunkedkeys), 'chunks to insert')

		# lots of swapping if you go high: wordcounttable is huge and you are making multiple copies of it
		notsobigpool = int(config['io']['workers'])
		with Pool(processes=int(notsobigpool)) as pool:
			# starmap: Like map() except that the elements of the iterable are expected to be iterables that are unpacked as arguments.
			pool.starmap(dbchunkloader, argmap)

	return masterconcorcdance


def concordancechunk(enumerateddbdict):
	"""

	dbdict looks like:
		{'in0010w0be': (173145, 173145), 'in0010w0bd': (173144, 173144), 'in0010w0bf': (173146, 173146), 'in0010w0bg': (173147, 173147), 'in0010w0bi': (173149, 173149), 'in0010w0bh': (173148, 173148)}

	it would be possible to do a where clause via the univesalid, but it should be (a lot) faster to do it by index

	:param dblist:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	chunknumber = enumerateddbdict[0]
	dbdict = enumerateddbdict[1]

	dblist = list(dbdict.keys())

	graves = 'ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ'
	graves = {graves[g] for g in range(0, len(graves))}

	terminalgravea = re.compile(r'([ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ])$')
	terminalgraveb = re.compile(r'([ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ])(.)$')
	# pull this out of cleanwords() so you don't waste cycles recompiling it millions of times: massive speedup
	punct = re.compile('[%s]' % re.escape(punctuation + '\′‵’‘·“”„—†⌈⌋⌊∣⎜͙ˈͻ✳※¶§⸨⸩｟｠⟫⟪❵❴⟧⟦→◦⊚𐄂𝕔☩(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'))

	concordance = {}
	count = 0
	for db in dblist:
		count += 1
		rng = dbdict[db]
		lineobjects = graballlinesasobjects(db[0:6], rng, cursor)
		dbc.commit()
		for line in lineobjects:
			words = line.wordlist('polytonic')
			words = [cleanwords(w, punct) for w in words]
			words = list(set(words))
			words[:] = [x.lower() for x in words]
			prefix = line.universalid[0:2]
			for w in words:
				# uncomment to watch individual words enter the dict
				# if w == 'docilem':
				# 	print(line.universalid,line.unformattedline())
				if 'v' in w:
					# 'vivere' --> 'uiuere'
					w = re.sub('v','u',w)
				try:
					if w[-1] in graves:
						w = re.sub(terminalgravea, forceterminalacute, w)
				except:
					# the word was not >0 char long
					pass
				try:
					if w[-2] in graves:
						w = re.sub(terminalgraveb, forceterminalacute, w)
				except:
					# the word was not >1 char long
					pass
				try:
					concordance[w][prefix] += 1
				except:
					concordance[w] = {}
					concordance[w][prefix] = 1

	print('\tfinished chunk',chunknumber+1)

	return concordance


def dbchunkloader(enumeratedchunkedkeys, masterconcorcdance, wordcounttable):
	"""

	:param resultbundle:
	:return:
	"""
	dbc = setconnection(config)
	cursor = dbc.cursor()

	# 'v' should be empty, though; ϙ will go to 0
	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	letters = {letters[l] for l in range(0,len(letters))}

	chunknumber = enumeratedchunkedkeys[0]
	chunkedkeys = enumeratedchunkedkeys[1]

	count = 0
	for key in chunkedkeys:
		count += 1
		cw = masterconcorcdance[key]
		skip = False
		try:
			lettertable = cleanaccentsandvj(key[0])
			# fine, but this just put any 'v' words inside of 'u' where they can never be found
			# so v issue has to be off the table by now
		except:
			# IndexError: string index out of range
			lettertable = '0'
			skip = True

		if lettertable not in letters:
			lettertable = '0'

		if skip is not True:
			q = 'INSERT INTO ' + wordcounttable + '_' + lettertable + \
			    ' (entry_name, total_count, gr_count, lt_count, dp_count, in_count, ch_count) VALUES (%s, %s, %s, %s, %s, %s, %s)'
			d = (key, cw['total'], cw['gr'], cw['lt'], cw['dp'], cw['in'], cw['ch'])
			try:
				cursor.execute(q, d)
			except:
				print('failed to insert', key)

		if count % 2500 == 0:
			dbc.commit()

	#print('\t', str(len(chunkedkeys)), 'words inserted into the wordcount tables')
	print('\tfinished chunk',chunknumber+1)

	dbc.commit()
	return


def headwordcounts():
	"""

	count morphological forms using the wordcount data

	[a] grab all possible forms of all dictionary words
	[b] count all hits of all forms of those words
	[c1] record the hits
	[c2] record statistics about those hits

	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	# loading is slow: avoid doing it 2x
	lemmatalist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)

	# 'v' should be empty, though; ϙ will go to 0
	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	letters = {letters[l] for l in range(0, len(letters))}
	countobjectlist = []
	for l in letters:
		countobjectlist += graballcountsasobjects('wordcounts_' + l, cursor)
	countdict = {word.entryname: word for word in countobjectlist}
	del countobjectlist

	dictionarycounts = buildcountsfromlemmalist(lemmatalist, countdict)

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
	cleanedknownworkgenres = [g.lower() for g in knownworkgenres]
	cleanedknownworkgenres = [re.sub(r'[\.\s]','',g) for g in cleanedknownworkgenres]

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
		cursor.execute(q,d)
		if commitcount % 2500 == 0:
			dbc.commit()
	dbc.commit()

	# now figure out and record the percentiles
	# derivedictionaryentrymetadata() will generate one set of numbers
	# then it will call derivechronologicalmetadata() to supplement those numbers
	# then you can call derivegenremetadata() to add still more information

	thetable = 'dictionary_headword_wordcounts'
	metadata = derivedictionaryentrymetadata(thetable, cursor)
	lemmatalist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)
	metadata = derivechronologicalmetadata(metadata, lemmatalist, cursor)
	metadata = insertchronologicalmetadata(metadata, thetable)
	metadata = derivegenremetadata(metadata, lemmatalist, thetable, knownworkgenres, cursor)

	# print('ἅρπαξ',metadata['ἅρπαξ'])
	# ἅρπαξ {'frequency_classification': 'core vocabulary (more than 50)', 'early': 42, 'middle': 113, 'late': 468}
	# print('stuprum',metadata['stuprum'])


	return metadata


def buildcountsfromlemmalist(lemmatalist, wordcountdict):
	"""

	given a list of lemmata objects, build a dictionary of statistics
	about how often the verious forms under that dictionary heading are used

	check each item on the list of possible forms against a master dict of observed forms

	return a dictionary of lexicon entry keywords and the associated totals of all observed forms

	:param lemmatalist:
	:return:
	"""

	lexiconentrycounts = {}

	for lem in lemmatalist:
		thewordtolookfor = lem.dictionaryentry
		# should probably prevent the dictionary from having 'v' or 'j' in it in the first place...
		thewordtolookfor = re.sub(r'v', 'u', thewordtolookfor.lower())
		# comprehensions would be nice, but they fail because of exceptions
		lexiconentrycounts[thewordtolookfor] = {}
		for item in ['total', 'gr', 'lt', 'dp', 'in', 'ch']:
			sum = 0
			for form in lem.formlist:
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

	metadata = {}

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
		rare = [x for x in remainder if x.t < 51 and x.t > 5]
		core = [x for x in remainder if x.t > 50 and (x not in common or x not in mostcommon)]
		explorecore = False
		if explorecore:
			# slice it into 10 bundles
			chunksize = int(len(core) / 10)
			chunks = [core[i:i + chunksize] for i in range(0, len(core), chunksize)]
			chunkstats = {}
			for chunkid, chunk in enumerate(chunks):
				chunkstats[chunkid] = cohortstats(chunk)

		printstats = False
		for item in [
			('full set', d),
			('top 250', mostcommon),
			('top 2500',common),
			('core (>50 occurrences; not in top 2500)', core),
			('rare (between 50 and 5 occurrences)', rare),
			('very rare (fewer than 5 occurrences)', veryrare),
			]:
			if printstats:
				if item == ('full set', d):
					print('\n',label)
				prettyprintcohortdata(item[0], cohortstats(item[1]))
			if item[0] != 'full set':
				for entry in item[1]:
					metadata[entry.entryname] = {'frequency_classification': item[0]}

	return metadata


def derivechronologicalmetadata(metadata, lemmataobjectlist, cursor):
	"""

	find frequencies by eras:
		-850 to -300
		-299 to 300
		301 to 1500

	attach this data to our existing metadata which is keyed to dictionary entry

	:param metadata:
	:return:
	"""

	eras = { 'early': (-850, -300), 'middle': (-299, 300), 'late': (301,1500)}

	for era in eras:
		print('calculating use by era:',era)
		eraconcordance = wordcounter(restriction={'time': eras[era]})
		# close, but we need to match the template above:
		# countdict = {word.entryname: word for word in countobjectlist}
		countobjectlist = [dbWordCountObject(w, eraconcordance[w]['total'], eraconcordance[w]['gr'], eraconcordance[w]['lt'],
		                   eraconcordance[w]['dp'], eraconcordance[w]['in'], eraconcordance[w]['ch']) for w in eraconcordance]
		countdict = {word.entryname: word for word in countobjectlist}
		lexiconentrycounts = buildcountsfromlemmalist(lemmataobjectlist, countdict)
		for entry in lexiconentrycounts:
			try:
				metadata[entry]
			except:
				metadata[entry] = {}
			metadata[entry][era] = lexiconentrycounts[entry]['total']

	return metadata


def derivegenremetadata(metadata, lemmataobjectlist, thetable, knownworkgenres, cursor):
	"""

	can/should do 'Inscr.' separately? It's just the sum of 'in' + 'ch'

	:param metadata:
	:param cursor:
	:return:
	"""

	for genre in knownworkgenres:
		print('compiling metadata for',genre)
		genrecordance = wordcounter(restriction={'genre': genre})
		countobjectlist = [dbWordCountObject(w, genrecordance[w]['total'], genrecordance[w]['gr'], genrecordance[w]['lt'],
							genrecordance[w]['dp'], genrecordance[w]['in'], genrecordance[w]['ch']) for w in genrecordance]
		countdict = {word.entryname: word for word in countobjectlist}
		lexiconentrycounts = buildcountsfromlemmalist(lemmataobjectlist, countdict)
		for entry in lexiconentrycounts:
			try:
				metadata[entry]
			except:
				metadata[entry] = {}
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


def insertchronologicalmetadata(metadatadict, thetable):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	metadatadict:
		ἅρπαξ: {'frequency_classification': 'core vocabulary (more than 50)', 'early': 2, 'middle': 6, 'late': 0}

	:param countdict:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM {tb} LIMIT 0'.format(tb=thetable)
	cursor.execute(q)

	count = 0
	for entry in metadatadict.keys():
		count += 1
		q = 'INSERT INTO tmp_metadata (entry_name, frequency_classification, early_occurrences, middle_occurrences, late_occurrences) ' \
		    'VALUES ( %s, %s, %s, %s, %s)'
		try:
			d = (entry, metadatadict[entry]['frequency_classification'], metadatadict[entry]['early'],
		     metadatadict[entry]['middle'], metadatadict[entry]['late'])
		except KeyError:
			# there is no date data because the word is not found in a dateable text
			# d = (entry, metadatadict[entry]['frequency_classification'], '', '', '')
			d = None
		if d:
			cursor.execute(q, d)

		if count % 2500 == 0:
			dbc.commit()

	dbc.commit()
	qtemplate = """
		UPDATE {tb} SET
			frequency_classification = tmp_metadata.frequency_classification,
			early_occurrences = tmp_metadata.early_occurrences,
			middle_occurrences = tmp_metadata.middle_occurrences,
			late_occurrences = tmp_metadata.late_occurrences
		FROM tmp_metadata
		WHERE {tb}.entry_name = tmp_metadata.entry_name
	"""
	q = qtemplate.format(tb=thetable)
	cursor.execute(q)
	dbc.commit()

	q = 'DROP TABLE tmp_metadata'
	cursor.execute(q)
	dbc.commit()

	# return the dict so you can reuse the data
	return metadatadict


def insertgenremetadata(metadatadict, genrename, thetable):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	metadatadict:
		ἅρπαξ: {'frequency_classification': 'core vocabulary (more than 50)', 'early': 2, 'middle': 6, 'late': 0}

	:param countdict:
	:return:
	"""

	# a clash between the stored genre names 'Alchem.' and names that are used for columns (which can't include period or whitespace)
	thecolumn = re.sub(r'[\.\s]','',genrename).lower()

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM {tb} LIMIT 0'.format(tb=thetable)
	cursor.execute(q)

	count = 0
	for entry in metadatadict.keys():
		count += 1
		q = 'INSERT INTO tmp_metadata (entry_name, {tc}) VALUES ( %s, %s)'.format(tc=thecolumn)
		try:
			d = (entry, metadatadict[entry][genrename])
		except KeyError:
			# there is no date data because the word is not found in a dateable text
			# d = (entry, metadatadict[entry]['frequency_classification'], '', '', '')
			d = None
		if d:
			cursor.execute(q, d)

		if count % 2500 == 0:
			dbc.commit()

	dbc.commit()
	q = 'UPDATE {tb} SET {tc} = tmp_metadata.{tc} FROM tmp_metadata WHERE {tb}.entry_name = tmp_metadata.entry_name'.format(tb=thetable, tc=thecolumn)
	cursor.execute(q)
	dbc.commit()

	q = 'DROP TABLE tmp_metadata'
	cursor.execute(q)
	dbc.commit()

	# return the dict so you can reuse the data
	return metadatadict


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



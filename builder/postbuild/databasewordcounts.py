# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
import configparser

from multiprocessing import Pool
from string import punctuation
from statistics import mean, median
from builder.builder_classes import dbWorkLine, dbWordCountObject, dbLemmaObject
from builder.dbinteraction.db import setconnection, loadallauthorsasobjects, loadallworksasobjects
from builder.parsers.betacode_to_unicode import stripaccents

config = configparser.ConfigParser()
config.read('config.ini')


def wordcounter(timerestriction=None):
	"""

	count all of the words in all of the dbs or a subset thereof



	:param timerestriction:
	:return:
	"""
	wordcounttable = 'wordcounts'

	authordict = loadallauthorsasobjects()

	if timerestriction:
		# restriction should be a date range tuple (-850,300), e.g.
		workdict = loadallworksasobjects()
		dbs = [key for key in authordict.keys() if authordict[key].converted_date and timerestriction[0] < int(authordict[key].converted_date) < timerestriction[1]]
		dbs += [key for key in workdict.keys() if workdict[key].converted_date and timerestriction[0] < int(workdict[key].converted_date) < timerestriction[1]]
	else:
		dbs = list(authordict.keys())

	# limit to NN for testing purposes
	# dbs = dbs[0:20]

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

	# test on a subset
	#listofworklists = [dictofdblists[key] for key in ['lt']]

	# parallelize by sending each db to its own worker: 291 ch tables to check; 463 in tables to check; 1823 gr tables to check; 362 lt tables to check; 516 dp tables to check
	# 'gr' is much bigger than the others, though let's split that one up
	# nb: many of the tables are very small and the longest ones cluster in related numerical zones; there is a tendency to drop down to a wait for 1 or 2 final threads
	# when we run through again with the time restriction there will be a massive number of chunks

	chunksize = 200
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

	print('breaking up the lists and parallelizing:', len(chunked),'chunks to analyze')
	# safe to almost hit number of cores here since we are not doing both db and regex simultaneously in each thread
	# here's hoping that the workers number was not over-ambitious to begin with

	bigpool = int(config['io']['workers'])+(int(config['io']['workers'])/2)
	with Pool(processes=int(bigpool)) as pool:
		listofconcordancedicts = pool.map(concordancechunk, enumerate(chunked))

	# merge the results
	print('merging the partial results')
	masterconcorcdance = listofconcordancedicts.pop()
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

	testing = False
	if testing == False and timerestriction == None:
		# not testing: then it is safe to reset the database...
		# no timerestriction: then this is our first pass and we should write the results to the master counts
		# timerestriction implies subsequent passes that are for metadata derived from unrestricted data and should not overwrite it

		letters= '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
		for l in letters:
			createwordcounttable(wordcounttable+'_'+l)

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


def dictmerger(masterdict, targetdict, label):
	"""

	:param masterdict:
	:param targetdict:
	:return:
	"""

	for item in targetdict:
		if item in masterdict:
			try:
				masterdict[item][label] += targetdict[item][label]
			except:
				masterdict[item][label] = targetdict[item][label]
		else:
			masterdict[item] = {}
			masterdict[item][label] = targetdict[item][label]

	return masterdict


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
						w = re.sub(terminalgravea,forceterminalacute, w)
				except:
					# the word was not >0 char long
					pass
				try:
					if w[-2] in graves:
						w = re.sub(terminalgraveb,forceterminalacute, w)
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


def forceterminalacute(matchgroup):
	"""
	θαμά and θαμὰ need to be stored in the same place

	otherwise you will click on θαμὰ, search for θαμά and get prevalence data that is not what you really wanted

	:param match:
	:return:
	"""

	map = { 'ὰ': 'ά',
			'ὲ': 'έ',
			'ὶ': 'ί',
			'ὸ': 'ό',
			'ὺ': 'ύ',
			'ὴ': 'ή',
			'ὼ': 'ώ',
			'ἂ': 'ἄ',
			'ἒ': 'ἔ',
			'ἲ': 'ἴ',
			'ὂ': 'ὄ',
			'ὒ': 'ὔ',
			'ἢ': 'ἤ',
			'ὢ': 'ὤ',
			'ᾃ': 'ᾅ',
			'ᾓ': 'ᾕ',
			'ᾣ': 'ᾥ',
			'ᾂ': 'ᾄ',
			'ᾒ': 'ᾔ',
			'ᾢ': 'ᾤ',
		}

	substitute = map[matchgroup[1]]
	try:
		# the word did not end with a vowel
		substitute += matchgroup[2]
	except:
		# the word ended with a vowel
		pass

	return substitute


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
			lettertable = stripaccents(key[0])
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


def formcounter():
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

	skipping = True
	if skipping != True:
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

		thetable = 'dictionary_headword_wordcounts'
		createwordcounttable(thetable, extracolumns=True)

		commitcount = 0
		keys = dictionarycounts.keys()
		keys = sorted(keys)
		for word in keys:
			commitcount += 1
			q = 'INSERT INTO '+thetable+' (entry_name, total_count, gr_count, lt_count, dp_count, in_count, ch_count) ' \
			                            'VALUES (%s, %s, %s, %s, %s, %s, %s)'
			d = (word, dictionarycounts[word]['total'], dictionarycounts[word]['gr'], dictionarycounts[word]['lt'],
			     dictionarycounts[word]['dp'], dictionarycounts[word]['in'], dictionarycounts[word]['ch'])
			cursor.execute(q,d)
			if commitcount % 2500 == 0:
				dbc.commit()
		dbc.commit()

	# now figure out and record the percentiles

	thetable = 'dictionary_headword_wordcounts'
	metadata = derivedictionaryentrymetadata(thetable, cursor)
	print('ἅρπαξ',metadata['ἅρπαξ'])

	insertmetadata(metadata, thetable)

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
	sort the words into 20 chunks (i.e. blocks of 5%)
	then figure out what the profile of each chunk is: max, min, avg number of words in that chunk

	:param cursor:
	:return:
	"""

	metadata = {}

	extrasql = ' ORDER BY total_count DESC'
	greekvowel = re.compile(r'[άέίόύήώἄἔἴὄὔἤὤᾅᾕᾥᾄᾔᾤαειουηω]')

	headwordobjects = graballcountsasobjects(headwordtable,cursor,extrasql)

	# the number of words with 0 as its total reflects parsing problems that need fixing elsewhere
	greek = [w for w in headwordobjects if re.search(greekvowel, w.entryname) and w.t > 0]
	latin = [w for w in headwordobjects if re.search(r'[a-z]', w.entryname) and w.t > 0]

	for dataset in [(greek, 'greek'), (latin, 'latin')]:
		d = dataset[0]
		label = dataset[1]
		mostcommon = d[:25]
		remainder = d[25:]
		veryrare = [x for x in remainder if x.t < 5]
		rare = [x for x in remainder if x.t < 51 and x.t > 5]
		core = [x for x in remainder if x.t > 50]
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
			('top twenty five', mostcommon),
			('core vocabulary (more than 50)',core),
			('rare (between 50 and 5)', rare),
			('very rare (less than 5)', veryrare),
			]:
			if printstats:
				if item == ('full set', d):
					print('\n',label)
				prettyprintcohortdata(item[0], cohortstats(item[1]))
			if item[0] != 'full set':
				for entry in item[1]:
					metadata[entry.entryname] = {'frequency_classification': item[0]}

		if label == 'greek':
			metadata = derivechronologicalmetadata(metadata, cursor)

	return metadata


def derivechronologicalmetadata(metadata, cursor):
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
	lemmatalist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)

	for era in eras:
		print('calculating use by era:',era)
		eraconcordance = wordcounter(timerestriction=eras[era])
		# close, but we need to match the template above:
		# countdict = {word.entryname: word for word in countobjectlist}
		countobjectlist = [dbWordCountObject(w, eraconcordance[w]['total'], eraconcordance[w]['gr'], eraconcordance[w]['lt'],
		                   eraconcordance[w]['dp'], eraconcordance[w]['in'], eraconcordance[w]['ch']) for w in eraconcordance]
		countdict = {word.entryname: word for word in countobjectlist}
		lexiconentrycounts = buildcountsfromlemmalist(lemmatalist, countdict)
		for entry in lexiconentrycounts:
			try:
				metadata[entry]
			except:
				metadata[entry] = {}
			metadata[entry][era] = lexiconentrycounts[entry]['total']

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


def prettyprintcohortdata(label, cohortresultsdict):
	"""
	take some results and print them (for use in one of HipparchiaServer's info pages)

	:return:
	"""

	titles = {'h': 'high', 'l': 'low', 'a': 'average', 'm': 'median', '#': 'count'}

	print()
	print(label)
	for item in ['#', 'h', 'l', 'a', 'm']:
		print('\t'+titles[item]+'\t'+str(int(cohortresultsdict[item])))

	return

"""
greek

full set
	count	113010
	high	3649037
	low	1
	average	794
	median	7

top twenty five
	count	25
	high	3649037
	low	429120
	average	1177696
	median	949783

core vocabulary (more than 50)
	count	28376
	high	425747
	low	51
	average	2099
	median	229

rare (between 50 and 5)
	count	32614
	high	50
	low	6
	average	18
	median	15

very rare (less than 5)
	count	48003
	high	4
	low	1
	average	1
	median	2
latin

full set
	count	27960
	high	244812
	low	1
	average	348
	median	11

top twenty five
	count	25
	high	244812
	low	40371
	average	86260
	median	64356

core vocabulary (more than 50)
	count	8624
	high	40256
	low	51
	average	859
	median	219

rare (between 50 and 5)
	count	8095
	high	50
	low	6
	average	19
	median	16

very rare (less than 5)
	count	10404
	high	4
	low	1
	average	1
	median	2
"""


def graballlinesasobjects(db, linerangetuple, cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	if linerangetuple == (-1,-1):
		whereclause = ''
	else:
		whereclause = ' WHERE index >= %s and index <= %s'
		data = (linerangetuple[0], linerangetuple[1])

	query = 'SELECT * FROM ' + db + whereclause

	if whereclause != '':
		cursor.execute(query, data)
	else:
		cursor.execute(query)

	lines = cursor.fetchall()

	lineobjects = [dblineintolineobject(l) for l in lines]

	return lineobjects


def graballcountsasobjects(db,cursor, extrasql=''):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM ' + db + extrasql
	cursor.execute(query)
	lines = cursor.fetchall()

	countobjects = [dbWordCountObject(l[0], l[1], l[2], l[3], l[4], l[5], l[6]) for l in lines]

	return countobjects


def grablemmataasobjects(db, cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM ' + db
	cursor.execute(query)
	lines = cursor.fetchall()

	lemmaobjects = [dbLemmaObject(l[0], l[1], l[2]) for l in lines]

	return lemmaobjects


def createwordcounttable(tablename, extracolumns=False):
	"""
	the SQL to generate the wordcount table
	:param tablename:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	query = 'DROP TABLE IF EXISTS public.' + tablename
	cursor.execute(query)

	query = 'CREATE TABLE public.' + tablename
	query += '( entry_name character varying(64),'
	query += ' total_count integer,'
	query += ' gr_count integer,'
	query += ' lt_count integer,'
	query += ' dp_count integer,'
	query += ' in_count integer,'
	query += ' ch_count integer'
	if extracolumns:
		query += 'frequency_classification character varying(64),'
		query += 'early_occurrences integer,'
		query += 'middle_occurrences integer,'
		query += 'late_occurrences integer,'
	query += ') WITH ( OIDS=FALSE );'

	cursor.execute(query)

	query = 'GRANT SELECT ON TABLE ' + tablename + ' TO hippa_rd;'
	cursor.execute(query)

	tableletter = tablename[-2:]

	q = 'CREATE UNIQUE INDEX wcindex'+tableletter+' ON '+tablename+' (entry_name)'
	cursor.execute(q)

	dbc.commit()

	return


def insertmetadata(metadatadict, thetable):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	metadatadict:
		ἅρπαξ: {'frequency_classification': 'core vocabulary (more than 50)', 'early': 2, 'middle': 6, 'late': 0}

	:param countdict:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM '+thetable+' LIMIT 0'
	cursor.execute(q)

	count = 0
	for entry in metadatadict.keys():
		count += 1
		q = 'INSERT INTO tmp_metadata (entry_name, frequency_classification, early_occurrences, middle_occurrences, late_occurrences) ' \
		    'VALUES ( %s, %s, %s, %s, %s)'
		d = (entry, metadatadict[entry]['frequency_classification'], metadatadict[entry]['early'],
		     metadatadict[entry]['middle'], metadatadict[entry]['late'])
		cursor.execute(q, d)
		if count % 2500 == 0:
			dbc.commit()

	dbc.commit()
	q = 'UPDATE '+thetable+' SET frequency_classification = tmp_metadata.frequency_classification,' \
			'early_occurrences = tmp_metadata.early_occurrences,' \
			'middle_occurrences = tmp_metadata.middle_occurrences,' \
			'late_occurrences = tmp_metadata.late_occurrences,' \
			' FROM tmp_metadata ' \
			'WHERE '+thetable+'.entry_name = tmp_metadata.entry_name'
	cursor.execute(q)
	dbc.commit()

	q = 'DROP TABLE tmp_metadata'
	cursor.execute(q)
	dbc.commit()

	return

"""

these functions are lifted/adapted from HipparchiaServer

"""

def dblineintolineobject(dbline):
	"""
	convert a db result into a db object

	basically all columns pushed straight into the object with one twist: 1, 0, 2, 3, ...

	:param dbline:
	:return:
	"""

	# note the [1], [0], [2], order: wkuinversalid, index, level_05_value, ...

	lineobject = dbWorkLine(dbline[1], dbline[0], dbline[2], dbline[3], dbline[4], dbline[5], dbline[6], dbline[7],
	                        dbline[8], dbline[9], dbline[10], dbline[11], dbline[12])

	return lineobject


def cleanwords(word, punct):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
	# strip all non-greek if we are doing greek
	# best do punct before this next one...

	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass

	return word


def makeablankline(work, fakelinenumber):
	"""
	sometimes (like in lookoutsidetheline()) you need a dummy line
	this will build one
	:param work:
	:return:
	"""

	lineobject = dbWorkLine(work, fakelinenumber, '-1', '-1', '-1', '-1', '-1', '-1', '', '', '', '', '')

	return lineobject

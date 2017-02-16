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
from builder.builder_classes import dbWorkLine, dbWordCountObject, dbLemmaObject
from builder.dbinteraction.db import setconnection
from builder.parsers.betacode_to_unicode import stripaccents

config = configparser.ConfigParser()
config.read('config.ini')


def wordcounter():
	wordcounttable = 'wordcounts'

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'SELECT universalid FROM authors'
	cursor.execute(q)
	results = cursor.fetchall()

	dbs = [r[0] for r in results]

	datasets = set([db[0:2] for db in dbs])
	dictofdblists = {dset:[db for db in dbs if db[0:2] == dset] for dset in datasets}
	listofworklists = [dictofdblists[key] for key in dictofdblists]

	# test on a subset
	# listofworklists = [dictofdblists[key] for key in ['lt']]

	# parallelize by sending each db to its own worker: 291 ch tables to check; 463 in tables to check; 1823 gr tables to check; 362 lt tables to check; 516 dp tables to check
	# 'gr' is much bigger than the others, though let's split that one up
	# nb: many of the tables are very small and the longest ones cluster in related numerical zones; there is a tendency to drop down to a wait for 1 or 2 final threads
	chunksize = 200
	chunkedlists = []

	for l in listofworklists:
		chunks = [l[i:i + chunksize] for i in range(0, len(l), chunksize)]
		for c in chunks:
			chunkedlists.append(c)

	# trim for testing
	# chunkedlists = chunkedlists[0:3]

	print('breaking up the lists and parallelizing:', len(chunkedlists),'chunks to analyze')
	# safe to almost hit number of cores here since we are not doing both db and regex simultaneously in each thread
	# here's hoping that the workers number was not over-ambitious to begin with

	bigpool = int(config['io']['workers'])+(int(config['io']['workers'])/2)
	with Pool(processes=int(bigpool)) as pool:
		listofconcordancedicts = pool.map(concordancechunk, enumerate(chunkedlists))

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
	if testing == False:
		# then it is safe to reset the database...

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

	return


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


def concordancechunk(enumerateddblist):
	"""

	:param dblist:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	chunknumber = enumerateddblist[0]
	dblist = enumerateddblist[1]

	prefix = dblist[0][0:2]
	# print('\treceived a chunk of',len(dblist), prefix, 'tables to check')

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
		lineobjects = graballlinesasobjects(db, cursor)
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

	lemmatalist = grablemmataasobjects('greek_lemmata', cursor) + grablemmataasobjects('latin_lemmata', cursor)

	# 'v' should be empty, though; ϙ will go to 0
	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	letters = {letters[l] for l in range(0, len(letters))}
	countlists = []
	for l in letters:
		countlists += graballcountsasobjects('wordcounts_' + l, cursor)
	countdict = {word.entryname: word for word in countlists}
	del countlists

	dictionarycounts = {}
	for lem in lemmatalist:
		thewordtolookfor = lem.dictionaryentry
		# should probably prevent the dictionary from having 'v' or 'j' in it in the first place...
		thewordtolookfor = re.sub(r'v', 'u', thewordtolookfor.lower())
		# comprehensions would be nice, but they fail because of exceptions
		dictionarycounts[thewordtolookfor] = {}
		for item in ['total', 'gr', 'lt', 'dp', 'in', 'ch']:
			sum = 0
			for form in lem.formlist:
				try:
					sum += countdict[form].getelement(item)
				except KeyError:
					# word not found
					pass
			dictionarycounts[thewordtolookfor][item] = sum
		# 	print('dictionarycounts[lem.dictionaryentry]: ',lem.dictionaryentry,dictionarycounts[lem.dictionaryentry])

	testing = False
	if testing == False:
		thetable = 'dictionary_headword_wordcounts'
		createwordcounttable(thetable)

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

	return


def graballlinesasobjects(db,cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM ' + db
	cursor.execute(query)
	lines = cursor.fetchall()

	lineobjects = [dblineintolineobject(l) for l in lines]

	return lineobjects


def graballcountsasobjects(db,cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM ' + db
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


def createwordcounttable(tablename):
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
	query += ') WITH ( OIDS=FALSE );'

	cursor.execute(query)

	query = 'GRANT SELECT ON TABLE ' + tablename + ' TO hippa_rd;'
	cursor.execute(query)

	tableletter = tablename[-2:]

	q = 'CREATE UNIQUE INDEX wcindex'+tableletter+' ON '+tablename+' (entry_name)'
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

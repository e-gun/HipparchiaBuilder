# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque
from string import punctuation
from multiprocessing.pool import Pool

from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbdataintoobjects import loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors, grabhollowlineobjectsfromlist
from builder.dbinteraction.dbloading import generatecopystream
from builder.wordcounting.wordcountdbfunctions import createwordcounttable
from builder.wordcounting.wordcounthelperfunctions import acuteforgrave, cleanwords, unpackchainedranges, \
	concordancemerger, grouper
from builder.workers import setworkercount


def mpwordcounter(restriction=None, authordict=None, workdict=None):
	"""

	count all of the words in all of the lines so you can find out the following re προϲώπου:

		Prevalence (this form): Ⓖ 8,455 / Ⓛ 1 / Ⓘ 7 / Ⓓ 68 / Ⓒ 6 / Ⓣ 8,537

	:param alllineobjects:
	:param restriction:
	:param authordict:
	:param workdict:
	:return:
	"""

	wordcounttable = 'wordcounts'

	if not authordict:
		print('loading information about authors and works')
		authordict = loadallauthorsasobjects()
		workdict = loadallworksasobjects()
		authordict = loadallworksintoallauthors(authordict, workdict)

	# [a] figure out which works we are looking for: idlist = ['lt1002', 'lt1351', 'lt2331', 'lt1038', 'lt0690', ...]
	idlist = generatesearchidlist(restriction, authordict, workdict)

	# [b] figure out what table index values we will need to assemble them: {tableid1: range1, tableid2: range2, ...}

	dbdictwithranges = generatedbdictwithranges(idlist, workdict)

	# [c] turn this into a list of lines we will need
	# bug in convertrangedicttolineset() evident at firstpass
	# len(alllineobjects) 11902961
	# len(linesweneed) 2103514

	linesweneed = list(convertrangedicttolineset(dbdictwithranges))
	# if you do not sort, four workers will each look for different lines in the same table
	linesweneed.sort()

	workers = setworkercount()
	chunksize = int(len(linesweneed) / workers) + 1
	workpiles = grouper(linesweneed, chunksize)
	workpiles = [list(w) for w in workpiles]

	# [d] send the work off for processing

	with Pool(processes=workers) as pool:
		getlistofdictionaries = [pool.apply_async(mpbuildindexdictionary, (i, workpiles[i])) for i in range(workers)]

		# you were returned [ApplyResult1, ApplyResult2, ...]
		listofdictionaries = [result.get() for result in getlistofdictionaries]

	# [e] merge the results
	masterconcorcdance = concordancemerger(listofdictionaries)

	# [f] totals are needed both initially and in the subsearches
	masterconcorcdance = calculatetotals(masterconcorcdance)

	# [g] build the tables if needed
	if not restriction:
		generatewordcounttablesonfirstpass(wordcounttable, masterconcorcdance)

	return masterconcorcdance


def mpbuildindexdictionary(pilenumber, workpile):
	"""
	a workpile looks like:
		['gr2042_LN_40997', 'gr1306_LN_503', 'gr0081_LN_51401', 'gr0006_LN_4864', 'gr2047_LN_21226', ...]
	:return:
	"""

	# unevenly sized groups are padded with None by grouper
	workpile = [w for w in workpile if w]

	graves = re.compile(r'[ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ]')
	# pull this out of cleanwords() so you don't waste cycles recompiling it millions of times: massive speedup
	punct = re.compile('[%s]' % re.escape(punctuation + '\′‵’‘·“”„—†⌈⌋⌊∣⎜͙ˈͻ✳※¶§⸨⸩｟｠⟫⟪❵❴⟧⟦→◦⊚𐄂𝕔☩(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'))

	if pilenumber == 0:
		print('gathering lines'.format(p=pilenumber))

	workdict = dict()
	for line in workpile:
		workandline = line.split('_LN_')
		w = workandline[0]
		l = int(workandline[1])
		try:
			workdict[w].append(l)
		except KeyError:
			workdict[w] = [l]

	lineobjects = deque()
	for key in workdict:
		lineobjects.extend(grabhollowlineobjectsfromlist(key, workdict[key]))

	if pilenumber == 0:
		print('worker #{p} gathered {n} lines'.format(p=pilenumber, n=len(lineobjects)))

	# debug
	# lineobjects = list(lineobjects)
	# lineobjects = lineobjects[:10000]

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
			if pilenumber == 0:
				print('\tworker #{p} progress: {n}%'.format(p=pilenumber, n=percent))
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


def generatedbdictwithranges(idlist, workdict):
	"""

	given a list of universalids, convert this list into a dictionary with authorid keys (ie, table names)

	each id will be associated with a range of line numbers that need to be pulled from that author table

	{tableid1: range1, tableid2: range2, ...}

	:return:
	"""

	dbcconnection = setconnection(autocommit=True)
	dbcursor = dbcconnection.cursor()

	minq = 'SELECT index FROM {t} ORDER BY index ASC LIMIT 1'
	maxq = 'SELECT index FROM {t} ORDER BY index DESC LIMIT 1'

	dbswithranges = dict()
	for db in idlist:
		if len(db) == 6:
			# we are reading a full author
			dbcursor.execute(minq.format(t=db))
			low = dbcursor.fetchone()
			dbcursor.execute(maxq.format(t=db))
			high = dbcursor.fetchone()
			dbswithranges[db] = [range(low[0], high[0] + 1)]
		else:
			# we are reading an individual work
			try:
				dbswithranges[db[0:6]].extend([range(workdict[db].starts, workdict[db].ends+1)])
			except KeyError:
				dbswithranges[db[0:6]] = [range(workdict[db].starts, workdict[db].ends+1)]

	dbswithranges = {key: dbswithranges[key] for key in dbswithranges}

	dbcconnection.connectioncleanup()

	return dbswithranges


def convertrangedicttolineset(dbswithranges):
	"""

	{tableid1: [range1.1, range1.2], tableid2: [range2.1, range2.2], ...} ==> {lineuniversalid1, lineuniversalid2, ... }


	:param dbswithranges:
	:return:
	"""

	lineset = set()
	for table in dbswithranges:
		tablelines = unpackchainedranges(dbswithranges[table])
		lineset.update({'{wk}_LN_{li}'.format(wk=table, li=l) for l in tablelines})

	return lineset


def generatewordcounttablesonfirstpass(wordcounttable, masterconcorcdance):
	"""

	no restriction: then this is our first pass and we should write the results to the master counts
	restriction implies subsequent passes that are for metadata derived from unrestricted data;
	these passes should not overwrite that data


	after this runs you will be able to do the following:

	hipparchiaDB=# select * from wordcounts_θ where entry_name='θυγατριδοῦϲ';
	 entry_name  | total_count | gr_count | lt_count | dp_count | in_count | ch_count
	-------------+-------------+----------+----------+----------+----------+----------
	 θυγατριδοῦϲ |         115 |      115 |        0 |        0 |        0 |        0
	(1 row)

	:return:
	"""

	print('generating fresh word count tables')

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
		# print('\tgenerating {l}'.format(l=letter))
		queryvalues = generatemasterconcorcdancevaluetuples(masterconcorcdance, letter)
		stream = generatecopystream(queryvalues, separator=separator)
		table = '{w}_{l}'.format(w=wordcounttable, l=letter)
		dbcursor.copy_from(stream, table, sep=separator, columns=columns)

	dbcconnection.connectioncleanup()

	return


def calculatetotals(masterconcorcdance):
	"""

	find the Ⓣ for something like πρόϲωπον given Ⓖ Ⓛ Ⓘ Ⓓ & Ⓒ

		Ⓖ 11,346 / Ⓛ 12 / Ⓘ 292 / Ⓓ 105 / Ⓒ 12 / Ⓣ 11,767

	:param masterconcorcdance:
	:return:
	"""

	print('calculating totals')
	for word in masterconcorcdance:
		for db in ['gr', 'lt', 'in', 'dp', 'ch']:
			if db not in masterconcorcdance[word]:
				masterconcorcdance[word][db] = 0
		masterconcorcdance[word]['total'] = sum([masterconcorcdance[word][x] for x in masterconcorcdance[word]])

	return masterconcorcdance


def generatemasterconcorcdancevaluetuples(masterconcorcdance, letter):
	"""

	entries look like:
		'WORD': {'gr': 1, 'lt': 2, 'in': 3, 'dp': 4, 'ch': 5, 'total': 15}


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


the pool paradigm:

def launchindexpool(self):
	print('launching indexing pool')
	with Pool(processes=self.workers) as pool:
		getlistofdictionaries = [pool.apply_async(self.buildindexdictionary, (i, workpiles[i])) for i in range(workers)]
		# you were returned [ApplyResult1, ApplyResult2, ...]
		listofdictionaries = [result.get() for result in getlistofdictionaries]
	return listofdictionaries

"""

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque
from statistics import mean, median

from builder.builderclasses import dbWordCountObject
from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbdataintoobjects import graballcountsasobjects, grablemmataasobjects, \
	loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors
from builder.dbinteraction.dbloading import generatecopystream
from builder.wordcounting.databasewordcounts import mpwordcounter
from builder.wordcounting.wordcountdbfunctions import createwordcounttable, insertchronologicalmetadata, \
	insertgenremetadata
from builder.wordcounting.wordcounthelperfunctions import prettyprintcohortdata

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


def headwordcounts():
	"""

	count morphological forms using the wordcount data

	[a] grab all possible forms of all dictionary words
	[b] count all hits of all forms of those words
	[c1] record the hits
	[c2] record statistics about those hits

	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	# loading is slow: avoid doing it 2x
	lemmataobjectslist = grablemmataasobjects('greek_lemmata', dbcursor) + grablemmataasobjects('latin_lemmata', dbcursor)

	# 'v' should be empty, though; ϙ will go to 0
	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	letters = {letters[l] for l in range(0, len(letters))}
	countobjectlist = list()
	for l in letters:
		countobjectlist.extend(graballcountsasobjects('wordcounts_' + l, dbcursor))
	countdict = {word.entryname: word for word in countobjectlist}
	del countobjectlist

	dictionarycounts = buildcountsfromlemmalist(lemmataobjectslist, countdict)

	cleanedknownworkgenres = [g.lower() for g in knownworkgenres]
	cleanedknownworkgenres = [re.sub(r'[\.\s]', '', g) for g in cleanedknownworkgenres]

	thetable = 'dictionary_headword_wordcounts'
	createwordcounttable(thetable, extracolumns=cleanedknownworkgenres)

	# note that entries are stored under their 'analysis name' ('ἀμφί-λαμβάνω', etc.) and not their LSJ name

	columns = ('entry_name',
				'total_count',
				'gr_count',
				'lt_count',
				'dp_count',
				'in_count',
				'ch_count')

	separator = '\t'

	queryvalues = deque()
	for word in dictionarycounts.keys():
		t = tuple([word, dictionarycounts[word]['total'], dictionarycounts[word]['gr'], dictionarycounts[word]['lt'], dictionarycounts[word]['dp'], dictionarycounts[word]['in'], dictionarycounts[word]['ch']])
		queryvalues.append(t)

	stream = generatecopystream(queryvalues, separator=separator)
	dbcursor.copy_from(stream, thetable, sep=separator, columns=columns)

	dbconnection.commit()

	# now figure out and record the percentiles
	# derivedictionaryentrymetadata() will generate one set of numbers
	# then it will call derivechronologicalmetadata() to supplement those numbers
	# then you can call derivegenremetadata() to add still more information

	thetable = 'dictionary_headword_wordcounts'
	metadata = derivedictionaryentrymetadata(thetable, dbcursor)
	lemmataobjectslist = grablemmataasobjects('greek_lemmata', dbcursor) + grablemmataasobjects('latin_lemmata', dbcursor)
	metadata = derivechronologicalmetadata(metadata, lemmataobjectslist)
	metadata = insertchronologicalmetadata(metadata, thetable)
	metadata = derivegenremetadata(metadata, lemmataobjectslist, thetable, knownworkgenres)

	# print('ἅρπαξ',metadata['ἅρπαξ'])
	# ἅρπαξ {'frequency_classification': 'core vocabulary (more than 50)', 'early': 42, 'middle': 113, 'late': 468}
	# print('stuprum',metadata['stuprum'])

	dbconnection.connectioncleanup()

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

		hipparchiaDB=# select frequency_classification
		from dictionary_headword_wordcounts where entry_name='κλόκιον';

		frequency_classification
		-------------------------------------
		rare (between 50 and 5 occurrences)


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


def derivechronologicalmetadata(metadata, lemmataobjectlist, authordict=None):
	"""

	find frequencies by eras:
		-850 to -300
		-299 to 300
		301 to 1500

	attach this data to our existing metadata which is keyed to dictionary entry

		hipparchiaDB=# select early_occurrences,middle_occurrences,late_occurrences
		from dictionary_headword_wordcounts where entry_name='φιάλη';

			early_occurrences | middle_occurrences | late_occurrences
			-------------------+--------------------+------------------
			           392 |               3069 |             1061

	:param metadata:
	:return:
	"""

	eras = {'early': (-850, -300), 'middle': (-299, 300), 'late': (301, 1500)}

	if not authordict:
		authordict = loadallauthorsasobjects()
		workdict = loadallworksasobjects()
		authordict = loadallworksintoallauthors(authordict, workdict)

	for era in eras:
		print('calculating use by era:', era)
		eraconcordance = mpwordcounter(restriction={'time': eras[era]}, authordict=authordict, workdict=workdict)
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

	hipparchiaDB=# select alchem from dictionary_headword_wordcounts where entry_name='φιάλη';

		 alchem
		--------
		     46
		(1 row)


	hipparchiaDB=# select comm,epist,exeget,fab from dictionary_headword_wordcounts where entry_name='ἐγκεντρίζω';

		 comm | epist | exeget | fab
		------+-------+--------+-----
		   12 |     6 |     41 |   1
		(1 row)

	:param metadata:
	:param cursor:
	:return:
	"""

	authordict = loadallauthorsasobjects()
	workdict = loadallworksasobjects()

	for genre in knownworkgenres:
		print('compiling metadata for', genre)
		genrecordance = mpwordcounter(restriction={'genre': genre}, authordict=authordict, workdict=workdict)
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
		print('\tinserting metadata for', genre)
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

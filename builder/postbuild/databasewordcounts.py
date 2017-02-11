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
from string import punctuation
from builder.builder_classes import dbWorkLine
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

	# at the moment this is slow and single-threaded
	# could speed this up by running several dbs in parallel and then merging the dicts?
	# [faster than a single managed dict of dicts, which ought to get pretty hairy]
	concordance = multidbconcordance(dbs, cursor)

	letters= '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	for l in letters:
		createwordcounttable(wordcounttable+'_'+l)

	count = 0
	for initialletter in concordance:
		wordkeys = concordance[initialletter].keys()
		wordkeys = sorted(wordkeys)
		for word in wordkeys:
			ciw = concordance[initialletter][word]
			lettertable = stripaccents(initialletter)
			if lettertable not in letters:
				lettertable = '0'
			count += 1
			for db in ['gr', 'lt', 'in', 'dp', 'ch']:
				try:
					testforexistence = ciw[db]
				except:
					ciw[db] = 0
			if word != '':
				q = 'INSERT INTO '+wordcounttable+'_'+lettertable+' (entry_name, total_count, gr_count, lt_count, dp_count, in_count, ch_count) ' \
						' VALUES (%s, %s, %s, %s, %s, %s, %s)'
				d = (word, ciw['total'], ciw['gr'], ciw['lt'], ciw['dp'], ciw['in'], ciw['ch'])
				try:
					cursor.execute(q,d)
				except:
					print('failed to insert',word)

			if count % 2500 == 0:
				dbc.commit()
			if count % 50000 == 0:
				print('\t',str(count),'words inserted into the wordcount tables')

	dbc.commit()

	return


def multidbconcordance(dblist, cursor):
	"""

	:param dblist:
	:return:
	"""

	concordance = {}
	# letters= 'abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	# for l in letters:
	# 	concordance[l] = {}

	# this is significantly slower than a unified dict: stripaccents(w[0]) too costly? [Build took 147.91 minutes vs c. 55min]
	# nevertheless the data that hits HipparchiaServer in a version that makes for much speedier searching

	print(len(dblist),'tables to check')
	count = 0
	for db in dblist:
		count += 1
		lineobjects = graballlinesasobjects(db, cursor)
		for line in lineobjects:
			words = line.wordlist('polytonic')
			words = [cleanwords(w) for w in words]
			words = list(set(words))
			words[:] = [x.lower() for x in words]
			prefix = line.universalid[0:2]
			for w in words:
				try:
					# initialletter = stripaccents(w[0])
					initialletter = w[0]
				except:
					# IndexError: string index out of range
					pass
				try:
					checkexistence = concordance[initialletter]
				except:
					concordance[initialletter] = {}
				try:
					concordance[initialletter][w]['total'] += 1
				except:
					concordance[initialletter][w] = {}
					concordance[initialletter][w]['total'] = 1
				try:
					concordance[initialletter][w][prefix] += 1
				except:
					concordance[initialletter][w][prefix] = 1

		if count % 250 == 0:
			print('\t',count,'tables checked.')

	return concordance


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


def cleanwords(word):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""
	punct = re.compile('[%s]' % re.escape(punctuation + '\′‵’‘·“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'))
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
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


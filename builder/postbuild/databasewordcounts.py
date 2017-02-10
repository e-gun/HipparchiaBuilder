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

	# could probably speed this up by running several dbs in parallel and then merging the dicts
	# [faster than a single managed dict?]
	concordance = multidbconcordance(dbs, cursor)

	createwordcounttable(wordcounttable)

	count = 0
	print(str(len(concordance)),'distinct words found')
	for word in concordance:
		count += 1
		for db in ['gr', 'lt', 'in', 'dp', 'ch']:
			try:
				testforexistence = concordance[word][db]
			except:
				concordance[word][db] = 0
		q = 'INSERT INTO '+wordcounttable+' (entry_name, total_count, gr_count, lt_count, dp_count, in_count, ch_count) ' \
				' VALUES (%s, %s, %s, %s, %s, %s, %s)'
		d = (word, concordance[word]['total'], concordance[word]['gr'], concordance[word]['lt'],
		     concordance[word]['dp'], concordance[word]['in'], concordance[word]['ch'])

		try:
			cursor.execute(q,d)
		except:
			print('failed to insert',word)

		if count % 2500 == 0:
			dbc.commit()
		if count % 50000 == 0:
			print('\t',str(count),'words inserted into the wordcount table')

	return


def multidbconcordance(dblist, cursor):
	"""

	:param dblist:
	:return:
	"""

	concordance = {}
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
					concordance[w]['total'] += 1
				except:
					concordance[w] = {}
					concordance[w]['total'] = 1
				try:
					concordance[w][prefix] += 1
				except:
					concordance[w][prefix] = 1
		if count % 250 == 0:
			print('\t',count,'tables checked. Currently aware of',len(concordance),'distinct words (and parts of words, symbols, etc.)')

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


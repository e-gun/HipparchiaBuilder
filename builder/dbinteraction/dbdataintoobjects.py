# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import psycopg2

from builder.builderclasses import dbAuthor, dbOpus, dbWordCountObject, dbLemmaObject, dbWorkLine
from builder.dbinteraction.connection import setconnection


def dbfetchauthorobject(uid, cursor):
	# only call this AFTER you have built all of the work objects so that they can be placed into it

	query = 'SELECT * from authors where universalid = %s'
	data = (uid,)
	cursor.execute(query, data)
	try:
		results = cursor.fetchone()
	except:
		# note that there is no graceful way out of this: you have to have an authorobject in the end
		print('failed to find the requested author:', query, data)
		results = None

	author = dbAuthor(*results)

	return author


def dbauthorandworkloader(authoruid, cursor):
	# note that this will return an AUTHOR filled with WORKS
	# the original Opus objects only exist at the end of HD reads
	# rebuild them from the DB instead: note that this object is simpler than the earlier version, but the stuff you need should all be there...

	author = dbfetchauthorobject(authoruid, cursor)

	query = """
			SELECT universalid, title, language, publication_info, 
				levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05, 
				workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, 
				firstline, lastline, authentic 
			FROM works WHERE universalid LIKE %s
			"""
	data = (authoruid + '%',)
	cursor.execute(query, data)
	try:
		results = cursor.fetchall()
	except:
		# see the notes on the exception to dbauthormakersubroutine: you can get here and then die for the same reason
		print('failed to find the requested work:', query, data)
		results = list()

	for match in results:
		work = dbOpus(*match)
		author.addwork(work)

	return author


def graballlinesasobjects(db, linerangetuple, cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	data = ''

	if linerangetuple == (-1, -1):
		whereclause = ''
	else:
		whereclause = ' WHERE index >= %s and index <= %s'
		data = (linerangetuple[0], linerangetuple[1])

	query = 'SELECT * FROM ' + db + whereclause

	if whereclause != '':
		cursor.execute(query, data)
	else:
		cursor.execute(query)

	try:
		lines = cursor.fetchall()
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: no results to fetch
		print('something is broken - no results for q="{q}" d="{d}"'.format(q=query, d=data))
		lines = None

	lineobjects = [dblineintolineobject(l) for l in lines]

	return lineobjects


def graballcountsasobjects(db, cursor, extrasql=''):
	"""

	:param db:
	:param cursor:
	:param extrasql:
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

	lemmaobjects = [dbLemmaObject(*l) for l in lines]

	return lemmaobjects


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


def makeablankline(work, fakelinenumber):
	"""
	sometimes (like in lookoutsidetheline()) you need a dummy line
	this will build one
	:param work:
	:return:
	"""

	lineobject = dbWorkLine(work, fakelinenumber, '-1', '-1', '-1', '-1', '-1', '-1', '', '', '', '', '')

	return lineobject


def loadallauthorsasobjects():
	"""

	return a dict of all possible author objects

	:return:
	"""

	dbconnection = setconnection()
	curs = dbconnection.cursor()

	q = 'SELECT * FROM authors'

	curs.execute(q)
	results = curs.fetchall()

	authorsdict = {r[0]: dbAuthor(*r) for r in results}

	dbconnection.connectioncleanup()

	return authorsdict


def loadallworksasobjects():
	"""

	return a dict of all possible work objects

	:return:
	"""

	dbconnection = setconnection()
	curs = dbconnection.cursor()

	q = 'SELECT universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, ' \
	        'levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, ' \
			'firstline, lastline, authentic FROM works'
	curs.execute(q)
	results = curs.fetchall()

	worksdict = {r[0]: dbOpus(*r) for r in results}

	dbconnection.connectioncleanup()

	return worksdict

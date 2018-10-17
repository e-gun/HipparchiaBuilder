# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2

from builder.builderclasses import dbAuthor, dbLemmaObject, dbOpus, dbWordCountObject, dbWorkLine
from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbhelperfunctions import resultiterator


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


def generatecomprehensivesetoflineobjects():
	"""

	grab every line from every table

	turn ito into a hollow lineobject (since we only need the polytonic line and the universalid)

	note the construction of the index: 'gr3018_LN_4773', etc.

	:return:
	"""

	print('grabbing every line from every table: this is slow and memory-intensive...')

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'SELECT universalid FROM authors'
	dbcursor.execute(q)

	authors = [a[0] for a in resultiterator(dbcursor)]

	# test
	# authors = authors[:10]

	qtemplate = 'SELECT index, wkuniversalid, accented_line FROM {t}'

	everyline = dict()
	total = len(authors)
	steps = int(total/10)
	index = 0
	for a in authors:
		q = qtemplate.format(t=a)
		dbcursor.execute(q)
		foundlines = resultiterator(dbcursor)
		minimallineobjects = [makeminimallineobject(*f) for f in foundlines]
		everyline.update({'{a}_LN_{ln}'.format(a=a, ln=h.index): h for h in minimallineobjects})
		index += 1
		if index % steps == 0:
			percent = int((index / steps) * 10)
			print('\t{n}% of authors loaded'.format(n=percent))

	return everyline


def makeminimallineobject(index, wkuniversalid, accented_line):
	"""

	build a line object with only three items fleshed out:
		index, wkuinversalid, accented_line

	wkuinversalid, index, level_05_value, level_04_value, level_03_value, level_02_value,
	             level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words,
	             annotations

	:return:
	"""

	return dbWorkLine(wkuniversalid, index, None, None, None, None, None, None, None, accented_line, None, '', None)


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


def loadallworksintoallauthors(authorsdict, worksdict):
	"""

	add the right work objects to the proper author objects

	:param authorsdict:
	:param worksdict:
	:return:
	"""

	for wkid in worksdict.keys():
		auid = wkid[0:6]
		authorsdict[auid].addwork(worksdict[wkid])

	return authorsdict


def grabminimallineobjectsfromlist(db, linelist):
	"""

	example:
		table id: 'gr0001'
		index values: [1, 2, 5, 10]

	:param db:
	:param range:
	:return:
	"""

	dbconnection = setconnection(simple=True)
	dbcursor = dbconnection.cursor()

	linelist.sort()

	q = 'SELECT index, wkuniversalid, accented_line FROM {d} WHERE index = ANY(%s)'.format(d=db)

	d = (linelist,)

	# if db == 'gr2042':
	# 	print('gr2042', linelist)

	dbcursor.execute(q, d)
	foundlines = resultiterator(dbcursor)
	minimallineobjects = [makeminimallineobject(*f) for f in foundlines]

	dbconnection.connectioncleanup()

	return minimallineobjects


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

	hipparchiaDB=# select * from latin_lemmata where dictionary_entry like '%eritas' limit 10;
	 dictionary_entry | xref_number |                                                        derivative_forms
	------------------+-------------+---------------------------------------------------------------------------------------------------------------------------------
	 veritas          |    82616897 | {ueritates,ueritatique,ueritatisque,ueritatemque,ueritatis,ueritasque,ueritatem,ueritas,ueritate,ueritati}
	 teneritas        |    77551938 | {teneritatem,teneritate,teneritas}
	...

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

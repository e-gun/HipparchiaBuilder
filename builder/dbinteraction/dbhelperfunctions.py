# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from builder.dbinteraction.connection import setconnection


def resultiterator(cursor, chunksize=5000):
	"""

	Yield a generator from fetchmany to keep memory usage down in contrast to

		results = curs.fetchall()

	see: http://code.activestate.com/recipes/137270-use-generators-for-fetching-large-db-record-sets/

	:param cursor:
	:param chunksize:
	:return:
	"""

	while True:
		results = cursor.fetchmany(chunksize)
		if not results:
			break
		for result in results:
			yield result


def authortablemaker(authordbname, dbconnection):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""

	dbcursor = dbconnection.cursor()

	query = 'DROP TABLE IF EXISTS public.{adb}'.format(adb=authordbname)
	dbcursor.execute(query)

	template = """
		CREATE TABLE public.{adb} (
			index integer NOT NULL UNIQUE DEFAULT nextval('{adb}'::regclass),
            wkuniversalid character varying(10) COLLATE pg_catalog."default",
            level_05_value character varying(64) COLLATE pg_catalog."default",
            level_04_value character varying(64) COLLATE pg_catalog."default",
            level_03_value character varying(64) COLLATE pg_catalog."default",
            level_02_value character varying(64) COLLATE pg_catalog."default",
            level_01_value character varying(64) COLLATE pg_catalog."default",
            level_00_value character varying(64) COLLATE pg_catalog."default",
            marked_up_line text COLLATE pg_catalog."default",
            accented_line text COLLATE pg_catalog."default",
            stripped_line text COLLATE pg_catalog."default",
            hyphenated_words character varying(128) COLLATE pg_catalog."default",
            annotations character varying(256) COLLATE pg_catalog."default"
        ) WITH ( OIDS=FALSE );
	"""

	query = template.format(adb=authordbname)

	dbcursor.execute(query)

	query = 'GRANT SELECT ON TABLE {adb} TO hippa_rd;'.format(adb=authordbname)
	dbcursor.execute(query)

	# print('failed to create',workdbname)

	dbconnection.commit()

	return


def tablenamer(authorobject, indexedat):
	"""
	tell me the name of the table we will be working with

	called by: dbauthoradder & workmaker
	:param authorobject:
	:param thework:
	:return:
	"""

	wk = authorobject.works[indexedat]
	nm = authorobject.number
	wn = wk.worknumber

	if wn < 10:
		nn = '00' + str(wn)
	elif wn < 100:
		nn = '0' + str(wn)
	else:
		nn = str(wn)

	pr = authorobject.universalid[0:2]

	workdbname = pr + nm + 'w' + nn

	return workdbname


def dbauthoradder(authorobject, dbconnection):
	"""
	SQL setup

	:param authorobject:
	:param cursor:
	:return:

	"""

	cursor = dbconnection.cursor()

	uid = authorobject.universalid
	if authorobject.language == '':
		lang = authorobject.works[0].language
	else:
		lang = authorobject.language

	query = 'DELETE FROM authors WHERE universalid = %s'
	data = (uid,)
	try:
		cursor.execute(query, data)
	except:
		pass

	query = """
			INSERT INTO authors 
				(universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location)
			VALUES 
				(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			"""
	# no empty values in recorded_date or location
	data = (uid, lang, authorobject.idxname, authorobject.aka, authorobject.shortname, authorobject.cleanname,
			authorobject.genre, 'Unavailable', None, 'Unavailable')
	try:
		cursor.execute(query, data)
	except Exception as e:
		print('dbauthoradder() failed to insert', authorobject.cleanname)
		print(e)
		print('aborted query was:', query, data)

	dbconnection.commit()

	return


def workmaker(authorobject, indexedat, cursor):
	uid = tablenamer(authorobject, indexedat)
	wk = authorobject.works[indexedat]

	query = 'DELETE FROM works WHERE universalid = %s'
	data = (uid,)
	try:
		cursor.execute(query, data)
	except:
		pass

	ll = list()
	for level in range(0, 6):
		try:
			ll.append(wk.structure[level])
		except:
			ll.append('')

	query = """
			INSERT INTO works 
				(universalid, title, language, publication_info, 
				levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05)
			VALUES 
				(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			"""
	data = (uid, wk.title, wk.language, '', ll[0], ll[1], ll[2], ll[3], ll[4], ll[5])
	try:
		cursor.execute(query, data)
	except:
		print('workmaker() failed to insert', uid, wk.title)
		print(cursor.query)

	return


def resetauthorsandworksdbs(tmpprefix, prefix):
	"""
	clean out any old info before insterting new info
	you have to purge the inscription and ddp dbs every time because the names can change between builds

	:param prefix:
	:return:
	"""
	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	for zap in [tmpprefix, prefix]:
		q = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		d = (zap + '%',)
		dbcursor.execute(q, d)
		results = dbcursor.fetchall()
		dbconnection.commit()

		authors = list()
		for r in results:
			authors.append(r[0][0:6])
		authors = list(set(authors))

		print('\t', len(authors), zap, 'tables to drop')

		count = 0
		for a in authors:
			count += 1
			q = 'DROP TABLE public.' + a
			try:
				dbcursor.execute(q)
			except:
				# 'table "in090cw001" does not exist'
				# because a build got interrupted? one hopes it is safe to pass
				pass
			if count % 500 == 0:
				dbconnection.commit()
			if count % 10000 == 0:
				print('\t', count, zap, 'tables dropped')
		dbconnection.commit()

		q = 'DELETE FROM authors WHERE universalid LIKE %s'
		d = (zap + '%',)
		dbcursor.execute(q, d)

		q = 'DELETE FROM works WHERE universalid LIKE %s'
		d = (zap + '%',)
		dbcursor.execute(q, d)

	dbconnection.connectioncleanup()

	return


def updatedbfromtemptable(table, sharedcolumn, targetcolumnlist, insertiondict):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	countdict:
		{ uid1: count1, uid2: count2, ... }


	:param countdict:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_{t} AS SELECT * FROM {t} LIMIT 0'.format(t=table)
	dbcursor.execute(q)
	dbconnection.commit()

	targetcolumns = ', '.join(targetcolumnlist)
	blankvals = ['%s' for i in range(0,len(targetcolumnlist)+1)]
	vv = ', '.join(blankvals)
	count = 0
	for k in insertiondict.keys():
		q = 'INSERT INTO tmp_{t} ({s}, {c}) VALUES ({vv} )'.format(t=table, c=targetcolumns, s=sharedcolumn, vv=vv)
		d = tuple([k] + insertiondict[k])
		dbcursor.execute(q, d)
		count += 1
		dbconnection.checkneedtocommit(count)

	dbconnection.commit()

	tc = targetcolumns.split(',')
	tc = [re.sub('\s', '', c) for c in tc]

	targs = ['{c}=tmp_{t}.{c}'.format(t=table,c=c) for c in tc]
	targs = ', '.join(targs)

	q = 'UPDATE {t} SET {targs} FROM tmp_{t} WHERE {t}.{s}=tmp_{t}.{s}'.format(t=table, targs=targs, s=sharedcolumn)
	dbcursor.execute(q)
	dbconnection.commit()

	q = 'DROP TABLE tmp_{t}'.format(t=table)
	dbcursor.execute(q)

	dbconnection.connectioncleanup()

	return
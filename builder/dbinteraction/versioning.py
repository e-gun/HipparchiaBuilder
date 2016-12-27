# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""


from datetime import datetime


sqltemplateversion = 12272016


def versiontablemaker(dbconnection, cursor):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""
	query = 'DROP TABLE IF EXISTS public.builderversion'
	cursor.execute(query)

	query = 'CREATE TABLE public.builderversion '
	query += ' ( templateversion integer,'
	query += 'corpusname character varying(2),'
	query += 'corpusbuilddate character varying(20)'
	query += ') WITH ( OIDS=FALSE );'

	cursor.execute(query)

	query = 'GRANT SELECT ON TABLE public.builderversion TO hippa_rd;'
	cursor.execute(query)

	dbconnection.commit()

	return


def timestampthebuild(corpusname, dbconnection, cursor):
	"""

	store the build time and template version in the DB

	:param dbname:
	:param cursor:
	:return:
	"""

	now = datetime.now().strftime("%Y-%m-%d %H:%M")

	q = 'SELECT to_regclass(%s);'
	d = ('public.builderversion',)
	cursor.execute(q, d)
	results = cursor.fetchone()

	if results[0] is None:
		versiontablemaker(dbconnection, cursor)

	q = 'DELETE FROM builderversion WHERE corpusname = %s'
	d = (corpusname,)
	try:
		cursor.execute(q, d)
	except:
		pass

	q = 'INSERT INTO builderversion ( templateversion, corpusname, corpusbuilddate ) VALUES (%s, %s, %s)'
	d = (sqltemplateversion, corpusname, now)
	cursor.execute(q, d)

	dbconnection.commit()

	return



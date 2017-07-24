# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from datetime import datetime


#sqltemplateversion = 12272016
#sqltemplateversion = 2182017
#sqltemplateversion = 5112017
#sqltemplateversion = 6012017
sqltemplateversion = 7242017

config = configparser.ConfigParser()
config.read('config.ini')
stamp = config['buildoptions']['timestamp']


def versiontablemaker(dbconnection, cursor):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""
	query = 'DROP TABLE IF EXISTS public.builderversion'
	cursor.execute(query)

	query = """
		CREATE TABLE public.builderversion 
			(templateversion integer,
			corpusname character varying(2),
			corpusbuilddate character varying(20)) 
			WITH ( OIDS=FALSE );
		"""

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

	if stamp == 'y':
		now = datetime.now().strftime("%Y-%m-%d %H:%M")
	else:
		now = '[an undated build]'

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

	dbconnection.commit()

	q = 'INSERT INTO builderversion ( templateversion, corpusname, corpusbuilddate ) VALUES (%s, %s, %s)'
	d = (sqltemplateversion, corpusname, now)
	cursor.execute(q, d)

	dbconnection.commit()

	return



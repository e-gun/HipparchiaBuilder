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

	try:
		# trying because you might not actually have the needed file, etc
		# i.e. readgitdata() is liable to a FileNotFoundError
		commit = readgitdata()
	except:
		commit = None

	if stamp == 'y':
		# d = datetime.now().strftime("%Y-%m-%d %H:%M")
		d = datetime.now().strftime("%Y-%m-%d")
		if commit:
			now = '{c} @ {d}'.format(d=d, c=commit[0:6])
		else:
			now = d
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


def readgitdata():
	"""

	find the commit value for the code used for this build

	a sample lastline:

		'3b0c66079f7337928b02df429f4a024dafc80586 63e01ae988d2d720b65c1bf7db54236b7ad6efa7 EG <egun@antisigma> 1510756108 -0500\tcommit: variable name changes; code tidy-ups\n'

	:return:
	"""

	gitfile = './.git/logs/HEAD'
	line = ''

	with open(gitfile) as fh:
		for line in fh:
			pass
		lastline = line

	gitdata = lastline.split(' ')
	commit = gitdata[1]

	return commit

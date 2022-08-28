# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from datetime import datetime

from builder.dbinteraction.connection import setconnection


hipparchiabuilderversion = '1.6.0'
#sqltemplateversion = 7242017
#sqltemplateversion = 2242018
#sqltemplateversion = 10082019
sqltemplateversion = 6182021

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')
stamp = config['buildoptions']['timestamp']


def versiontablemaker(dbconnection):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""

	dbcursor = dbconnection.cursor()

	query = 'DROP TABLE IF EXISTS public.builderversion'
	dbcursor.execute(query)

	query = """
		CREATE TABLE public.builderversion 
			( templateversion integer,
			corpusname character varying(2),
			corpusbuilddate character varying(64),
			buildoptions character varying(512) )
			WITH ( OIDS=FALSE );
		"""

	dbcursor.execute(query)

	query = 'GRANT SELECT ON TABLE public.builderversion TO hippa_rd;'
	dbcursor.execute(query)

	dbconnection.commit()

	return


def timestampthebuild(corpusname: str, dbconnection=None):
	"""

	store the build time and template version in the DB

	:param dbname:
	:param cursor:
	:return:
	"""

	optionrecord = list()
	optionstotrack = ['hideknownblemishes', 'htmlifydatabase', 'rationalizetags', 'simplifybrackets', 'simplifyquotes', 'smartsinglequotes']
	for o in optionstotrack:
		try:
			setting = config['buildoptions'][o]
			optionrecord.append('{o}: {s}'.format(o=o, s=setting))
		except KeyError:
			# you did not have 'htmlifydatabase' in your config.ini?
			pass
	options = ', '.join(optionrecord)

	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()

	try:
		# trying because you might not actually have the needed file, etc
		# i.e. readgitdata() is liable to a FileNotFoundError
		commit = readgitdata()
	except FileNotFoundError:
		commit = None

	if stamp == 'y':
		# d = datetime.now().strftime("%Y-%m-%d %H:%M")
		d = datetime.now().strftime("%Y-%m-%d")
		if commit:
			datestamp = '{v} ({c}) @ {d}'.format(v=hipparchiabuilderversion, d=d, c=commit[0:6])
		else:
			datestamp = '{v} @ {d}'.format(v=hipparchiabuilderversion, d=d)
	else:
		datestamp = '[an undated build]'

	q = 'SELECT to_regclass(%s);'
	d = ('public.builderversion',)
	dbcursor.execute(q, d)
	results = dbcursor.fetchone()

	if results[0] is None:
		versiontablemaker(dbconnection)

	q = 'DELETE FROM builderversion WHERE corpusname = %s'
	d = (corpusname,)
	try:
		dbcursor.execute(q, d)
	except:
		pass

	dbconnection.commit()

	q = 'INSERT INTO builderversion ( templateversion, corpusname, corpusbuilddate, buildoptions ) VALUES (%s, %s, %s, %s)'
	d = (sqltemplateversion, corpusname, datestamp, options)

	try:
		dbcursor.execute(q, d)
	except:
		# psycopg2.errors.UndefinedColumn:
		#   you tried to add to an old version table
		# psycopg2.errors.StringDataRightTruncation:
		#   you tried to add to an old version table with 'corpusbuilddate character varying(20)'
		# AttributeError:
		#   module 'psycopg2' has no attribute 'errors'
		# owing to the possibility of the last, we skip the prior two... [bleh]
		versiontablemaker(dbconnection)
		dbcursor.execute(q, d)

	dbconnection.connectioncleanup()

	return


def readgitdata() -> str:
	"""

	find the commit value for the code used for this build

	a sample lastline:

		'3b0c66079f7337928b02df429f4a024dafc80586 63e01ae988d2d720b65c1bf7db54236b7ad6efa7 EG <egun@antisigma> 1510756108 -0500\tcommit: variable name changes; code tidy-ups\n'

	:return:
	"""

	gitfile = './.git/logs/HEAD'
	line = str()

	with open(gitfile) as fh:
		for line in fh:
			pass
		lastline = line

	gitdata = lastline.split(' ')
	commit = gitdata[1]

	return commit

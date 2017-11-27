# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

try:
	# python3
	# latin build: Build took 4.0 minutes
	import psycopg2
except ImportError:
	# pypy3
	# pypy3 support is EXPERIMENTAL (and unlikely to be actively pursued)
	# latin build: Build took 3.67 minutes
	# greek will fail: too many connections to the db
	# wordcounts will fail unless you increase the ulimit: Too many open files in system
	import psycopg2cffi as psycopg2


def setconnection(config, autocommit=False):
	dbconnection = psycopg2.connect(user=config['db']['DBUSER'], host=config['db']['DBHOST'],
									port=config['db']['DBPORT'], database=config['db']['DBNAME'],
									password=config['db']['DBPASS'])

	if autocommit:
		dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	return dbconnection
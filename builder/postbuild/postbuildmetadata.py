# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import configparser
from multiprocessing import Pool
from builder.dbinteraction.db import setconnection

config = configparser.ConfigParser()
config.read('config.ini')


def insertfirstsandlasts(workcategoryprefix, cursor, dbconnection):
	"""
	public.works needs to know
		firstline integer,
        lastline integer,
	:param cursor:
	:return:
	"""
	
	print('inserting work db metatata: first/last lines')
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
	data = (workcategoryprefix+'%',)
	cursor.execute(query, data)
	results = cursor.fetchall()
	
	for r in results:
		oneworkdinsertfirstsandlasts(r[0], cursor, dbconnection)
	
	return


def oneworkdinsertfirstsandlasts(universalid, cursor, dbconnection):
	"""
	public.works needs to know
		firstline integer,
        lastline integer

	(allow one author at a time so you can debug)
	:param cursor:
	:param dbconnection:
	:return:
	"""
	
	query = 'SELECT index FROM ' + universalid + ' ORDER BY index ASC LIMIT 1'
	cursor.execute(query)
	firstline = cursor.fetchone()
	first = int(firstline[0])
	
	query = 'SELECT index FROM ' + universalid + ' ORDER BY index DESC LIMIT 1'
	cursor.execute(query)
	lastline = cursor.fetchone()
	last = int(lastline[0])
	
	query = 'UPDATE works SET firstline=%s, lastline=%s WHERE universalid=%s'
	data = (first, last, universalid)
	cursor.execute(query, data)
	
	dbconnection.commit()
	
	return


def findwordcounts(cursor, dbconnection):
	"""
	if you don't already have an official wordcount, generate one
	:param cursor:
	:return:
	"""
	print('inserting work db metatata: wordcounts')
	query = 'SELECT universalid FROM works WHERE wordcount IS NULL ORDER BY universalid ASC'
	cursor.execute(query)
	results = cursor.fetchall()

	count = 0
	for r in results:
		count += 1
		oneworkwordcounts(r[0], cursor, dbconnection)
		if count % 500 == 0:
			print('\tcount recorded for',count,'works')
	return


def oneworkwordcounts(universalid, cursor, dbconnection):
	"""
	if you don't already have an official wordcount, generate one
	
	(allow one author at a time so you can debug)
	
	:param universalid:
	:param cursor:
	:param dbconnection:
	:return:
	"""
	
	query = 'SELECT COUNT (hyphenated_words) FROM ' + universalid + ' WHERE hyphenated_words <> %s'
	data = ('',)
	cursor.execute(query, data)
	hcount = cursor.fetchone()
	
	query = 'SELECT stripped_line FROM ' + universalid + ' ORDER BY index ASC'
	cursor.execute(query)
	lines = cursor.fetchall()
	wordcount = 0
	for line in lines:
		words = line[0].split(' ')
		words = [x for x in words if x]
		wordcount += len(words)
	
	totalwords = wordcount - hcount[0]
	
	query = 'UPDATE works SET wordcount=%s WHERE universalid=%s'
	data = (totalwords, universalid)
	cursor.execute(query, data)
	
	dbconnection.commit()
	
	return


def buildtrigramindices(workcategoryprefix, cursor):
	"""
	build indices for the works based on trigrams keyed to the stripped line
	
	:param cursor:
	:param dbconnection:
	:return:
	"""
	
	print('building indices for work dbs')
	
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
	data = (workcategoryprefix+'%',)
	cursor.execute(query,data)
	results = cursor.fetchall()
	
	resultarray = []
	for r in results:
		resultarray.append(r[0])
	
	pool = Pool(processes=int(config['io']['workers']))
	pool.map(mpindexbuilder, resultarray)
	
	return


def mpindexbuilder(results):
	"""
	mp aware indexing pool: helps you crank through 'em
	:param results:
	:return:
	"""
	
	buildoneindex(results)

	return


def buildoneindex(universalid):
	"""
	build indices for the works based on trigrams keyed to the stripped line
	
	(allow one author at a time so you can debug)
	
	:param universalid:
	:param cursor:
	:param dbconnection:
	:return:
	"""
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	for column in [('_mu','accented_line'), ('_st','stripped_line')]:
		query = 'DROP INDEX IF EXISTS '+universalid+column[0]+'_trgm_idx'
		try:
			curs.execute(query)
			dbc.commit()
		except:
			print('failed to drop index for',universalid)
			pass
		
		query = 'CREATE INDEX '+universalid+column[0]+'_trgm_idx ON '+universalid+' USING GIN ('+column[1]+' gin_trgm_ops)'
		try:
			curs.execute(query)
			dbc.commit()
		except:
			print('failed to create index for',universalid,'\n\t',query)
	
	dbc.commit()
	curs.close()
	del dbc
	
	return
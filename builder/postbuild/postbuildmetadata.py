# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from multiprocessing import Process, Manager, Pool
from builder.dbinteraction.db import setconnection
from builder.builder_classes import MPCounter

config = configparser.ConfigParser()
config.read('config.ini')

"""
	SPEED NOTES

    thousands of UPDATEs flying at the postgresql server makes it sad

    currently refactoring to dodge 'UPDATE' as much as possible or to update all relevant fields at once

	the following the faster way to do bulk UPDATES: create a tmp table and then update another table from it
	[http://dba.stackexchange.com/questions/41059/optimizing-bulk-update-performance-in-postgresql]

	10x+ faster if you use this trick: worth the trouble

"""


def insertfirstsandlasts(workcategoryprefix, cursor):
	"""
	public.works needs to know
		firstline integer,
        lastline integer,

	:param cursor:
	:return:
	"""
	
	print('inserting work db metatata: first/last lines')
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid DESC'
	data = (workcategoryprefix+'%',)
	cursor.execute(query, data)
	results = cursor.fetchall()

	uids = []
	for r in results:
		uids.append(r[0])

	boundaries = boundaryfinder(uids)
	insertboundaries(boundaries)

	return


def boundaryfinder(uids):
	"""

	find first and last lines

	return a list of tuples:

		[(universalid1, first1, last1), (universalid2, first2, last2), ...]

	:param uids:
	:return:
	"""

	manager = Manager()
	uids = manager.list(uids)
	commitcount = MPCounter()
	found = manager.list()

	print('\t', len(uids), 'items to examine')
	workers = int(config['io']['workers'])
	jobs = [Process(target=mpboundaryfinder, args=(uids, commitcount, found)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()

	return found


def insertboundaries(boundariestuplelist):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	boundariestuplelist:
		[(universalid1, first1, last1), (universalid2, first2, last2), ...]


	:param boundariestuplelist:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'CREATE TEMP TABLE tmp_works AS SELECT * FROM works LIMIT 0'
	cursor.execute(q)

	count = 0
	for b in boundariestuplelist:
		count += 1
		q = 'INSERT INTO tmp_works (universalid, firstline, lastline) VALUES ( %s, %s, %s)'
		d = b
		cursor.execute(q, d)
		if count % 5000 == 0:
			dbc.commit()

	dbc.commit()
	q = 'UPDATE works SET firstline = tmp_works.firstline, lastline = tmp_works.lastline ' \
			'FROM tmp_works WHERE works.universalid = tmp_works.universalid'
	cursor.execute(q)
	dbc.commit()

	q = 'DROP TABLE tmp_works'
	cursor.execute(q)
	dbc.commit()

	return


def mpboundaryfinder(universalids, commitcount, found):
	"""
	public.works needs to know
		firstline integer,
        lastline integer
	(allow one author at a time so you can debug)
	:param cursor:
	:param dbconnection:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	while len(universalids) > 0:
		try:
			universalid = universalids.pop()
		except:
			universalid = ''

		auid = universalid[0:6]

		if universalid != '':
			query = 'SELECT index FROM ' + auid + ' WHERE wkuniversalid = %s ORDER BY index ASC'
			data = (universalid,)
			cursor.execute(query, data)
			lines = cursor.fetchall()
			firstline = lines[0]
			lastline = lines[-1]
			first = int(firstline[0])
			last = int(lastline[0])

			found.append((universalid, first, last))

		commitcount.increment()
		if commitcount.value % 250 == 0:
			dbc.commit()
		if commitcount.value % 10000 == 0:
			print('\t', commitcount.value, 'works examined')

	dbc.commit()

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
	dbconnection.commit()

	uids = []
	for r in results:
		uids.append(r[0])

	counts = calculatewordcounts(uids)
	insertcounts(counts)

	return


def calculatewordcounts(uids):
	"""

	take a list of ids and grab wordcounts for the corresponding works

	return a dict:
		{ uid1: count1, uid2: count2, ... }

	:param uids:
	:return:
	"""

	manager = Manager()
	uids = manager.list(uids)
	counttuplelist = manager.list()
	commitcount = MPCounter()

	print('\t',len(uids),'works to examine')

	workers = int(config['io']['workers'])
	jobs = [Process(target=mpworkwordcountworker, args=(uids, counttuplelist, commitcount)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()

	countdict = {w[0]: w[1] for w in counttuplelist}

	return countdict


def insertcounts(countdict):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	countdict:
		{ uid1: count1, uid2: count2, ... }


	:param countdict:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'CREATE TEMP TABLE tmp_works AS SELECT * FROM works LIMIT 0'
	cursor.execute(q)

	count = 0
	for id in countdict.keys():
		count += 1
		q = 'INSERT INTO tmp_works (universalid, wordcount) VALUES ( %s, %s )'
		d = (id, countdict[id])
		cursor.execute(q, d)
		if count % 5000 == 0:
			dbc.commit()

	dbc.commit()
	q = 'UPDATE works SET wordcount = tmp_works.wordcount FROM tmp_works WHERE works.universalid = tmp_works.universalid'
	cursor.execute(q)
	dbc.commit()

	q = 'DROP TABLE tmp_works'
	cursor.execute(q)
	dbc.commit()

	return


def mpworkwordcountworker(universalids, counttuplelist, commitcount):
	"""
	if you don't already have an official wordcount, generate one
	
	return a tuplelist:

		[(uid1, count1), (uid2, count2), ...]
	
	:param universalid:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	while len(universalids) > 0:
		try:
			universalid = universalids.pop()
		except:
			universalid = ''

		if universalid != '':
			query = 'SELECT COUNT (hyphenated_words) FROM ' + universalid[0:6] + ' WHERE (wkuniversalid=%s AND hyphenated_words <> %s)'
			data = (universalid,'')
			cursor.execute(query, data)
			hcount = cursor.fetchone()

			query = 'SELECT stripped_line FROM ' + universalid[0:6] + ' WHERE wkuniversalid=%s ORDER BY index ASC'
			data = (universalid,)
			cursor.execute(query, data)
			lines = cursor.fetchall()
			wordcount = 0
			for line in lines:
				words = line[0].split(' ')
				words = [x for x in words if x]
				wordcount += len(words)

			totalwords = wordcount - hcount[0]

			counttuplelist.append((universalid,totalwords))
			commitcount.increment()
			if commitcount.value % 250 == 0:
				dbc.commit()
			if commitcount.value % 10000 == 0:
				print('\t', commitcount.value, 'works examined')
	
	dbc.commit()
	
	return counttuplelist


def buildtrigramindices(workcategoryprefix, cursor):
	"""
	build indices for the works based on trigrams keyed to the stripped line
	
	:param cursor:
	:param dbconnection:
	:return:
	"""
	
	print('building indices for author dbs')
	
	query = 'SELECT universalid FROM authors WHERE universalid LIKE %s ORDER BY universalid ASC'
	data = (workcategoryprefix+'%',)
	cursor.execute(query,data)
	results = cursor.fetchall()
	
	manager = Manager()
	uids = manager.list()
	commitcount = MPCounter()

	for r in results:
		uids.append(r[0])

	print('\t',len(uids),'items to index')

	workers = int(config['io']['workers'])
	jobs = [Process(target=mpindexbuilder, args=(uids, commitcount)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()


	return


def mpindexbuilder(universalids, commitcount):
	"""
	mp aware indexing pool: helps you crank through 'em

	:param results:
	:return:
	"""

	dbc = setconnection(config)
	curs = dbc.cursor()

	while len(universalids) > 0:
		try:
			universalid = universalids.pop()
		except:
			universalid = ''

		if universalid != '':
			for column in [('_mu', 'accented_line'), ('_st', 'stripped_line')]:
				query = 'DROP INDEX IF EXISTS ' + universalid + column[0] + '_trgm_idx'
				try:
					curs.execute(query)
				except:
					print('failed to drop index for', universalid)
					pass

				query = 'CREATE INDEX ' + universalid + column[0] + '_trgm_idx ON ' + universalid + ' USING GIN (' + column[
					1] + ' gin_trgm_ops)'
				try:
					curs.execute(query)
				except:
					print('failed to create index for', universalid, '\n\t', query)

			commitcount.increment()
			if commitcount.value % 250 == 0:
				dbc.commit()
			if commitcount.value % 250 == 0:
				print('\t', commitcount.value, 'indices created')

	dbc.commit()

	return



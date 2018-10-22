# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


from multiprocessing import Manager, Process

from builder.builderclasses import MPCounter
from builder.dbinteraction.connection import setconnection, icanpickleconnections
from builder.dbinteraction.dbhelperfunctions import resultiterator
from builder.workers import setworkercount

"""
	SPEED NOTES
	thousands of UPDATEs flying at the postgresql server makes it sad
	dodge 'UPDATE' as much as possible or to update all relevant fields at once

	the following the faster way to do bulk UPDATES: create a tmp table and then update another table from it
	[http://dba.stackexchange.com/questions/41059/optimizing-bulk-update-performance-in-postgresql]

	10x+ faster if you use this trick: worth the trouble
"""


def insertfirstsandlasts(workcategoryprefix,):
	"""

	public.works needs to know
	firstline integer,
	lastline integer,

	:param workcategoryprefix:
	:param cursor:
	:return:
	"""
	dbconnection = setconnection()
	cursor = dbconnection.cursor()

	print('inserting work db metatata: first/last lines')
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid DESC'
	data = (workcategoryprefix+'%',)
	cursor.execute(query, data)
	results = resultiterator(cursor)

	uids = [r[0] for r in results]

	boundaries = boundaryfinder(uids)
	insertboundaries(boundaries)

	dbconnection.connectioncleanup()

	return


def boundaryfinder(uids):
	"""

	find first and last lines

	return a list of tuples:

		[(universalid1, first1, last1), (universalid2, first2, last2), ...]

	:param uids:
	:return:
	"""

	dbconnection = setconnection()
	cursor = dbconnection.cursor()

	# don't need to do 100k queries by asking for every work inside of every author
	# instead ask for it all at once and then sort it on this end

	# find all authors
	authors = dict()
	for uid in uids:
		try:
			authors[uid[0:6]].append(uid)
		except KeyError:
			authors[uid[0:6]] = [uid]

	# get all line values for all works
	workmapper = dict()
	for a in authors:
		q = 'SELECT index, wkuniversalid FROM {a}'.format(a=a)
		cursor.execute(q)
		indexvalues = resultiterator(cursor)

		for i in indexvalues:
			try:
				workmapper[i[1]].append(i[0])
			except:
				workmapper[i[1]] = [i[0]]

	# determine the min/max for each work
	found = [(w, min(workmapper[w]), max(workmapper[w])) for w in workmapper]

	dbconnection.connectioncleanup()

	return found


def insertboundaries(boundariestuplelist):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	boundariestuplelist:
		[(universalid1, first1, last1), (universalid2, first2, last2), ...]


	:param boundariestuplelist:
	:return:
	"""

	dbconnection = setconnection()
	cursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_works AS SELECT * FROM works LIMIT 0'
	cursor.execute(q)

	count = 0
	for b in boundariestuplelist:
		count += 1
		q = 'INSERT INTO tmp_works (universalid, firstline, lastline) VALUES ( %s, %s, %s)'
		d = b
		cursor.execute(q, d)
		if count % 5000 == 0:
			dbconnection.commit()

	dbconnection.commit()
	q = 'UPDATE works SET firstline = tmp_works.firstline, lastline = tmp_works.lastline ' \
			'FROM tmp_works WHERE works.universalid = tmp_works.universalid'
	cursor.execute(q)
	dbconnection.commit()

	q = 'DROP TABLE tmp_works'
	cursor.execute(q)

	dbconnection.connectioncleanup()

	return


def findwordcounts(dbconnection):
	"""

	if you don't already have an official wordcount, generate one

	:param cursor:
	:param dbconnection:
	:return:
	"""

	db = dbconnection.cursor()

	print('inserting work db metatata: wordcounts')
	query = 'SELECT universalid FROM works WHERE wordcount IS NULL ORDER BY universalid ASC'
	db.execute(query)
	results = resultiterator(db)
	dbconnection.commit()

	uids = [r[0] for r in results]

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

	dbconnection = setconnection()
	cursor = dbconnection.cursor()

	# don't need to do 100k queries by asking for every work inside of every author
	# instead ask for it all at once and then sort it on this end

	# find all authors
	authors = dict()
	for uid in uids:
		try:
			authors[uid[0:6]].append(uid)
		except KeyError:
			authors[uid[0:6]] = [uid]

	# get all line values for all works
	countdict = dict()
	for a in authors:
		q = 'SELECT wkuniversalid, stripped_line, hyphenated_words FROM {a}'.format(a=a)
		cursor.execute(q)
		lines = resultiterator(cursor)

		for l in lines:
			uid = l[0]
			stripped = l[1]
			hyphens = l[2]
			h = 0
			if len(hyphens) > 0:
				h = 1

			try:
				countdict[uid]
			except KeyError:
				countdict[uid] = 0
			words = stripped.split(' ')
			words = [x for x in words if x]
			countdict[uid] += len(words) + h

	dbconnection.connectioncleanup()

	return countdict


def insertcounts(countdict):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	countdict:
		{ uid1: count1, uid2: count2, ... }


	:param countdict:
	:return:
	"""

	dbconnection = setconnection()
	cursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_works AS SELECT * FROM works LIMIT 0'
	cursor.execute(q)

	count = 0
	for idnum in countdict.keys():
		count += 1
		q = 'INSERT INTO tmp_works (universalid, wordcount) VALUES ( %s, %s )'
		d = (idnum, countdict[idnum])
		cursor.execute(q, d)
		if count % 5000 == 0:
			dbconnection.commit()

	dbconnection.commit()
	q = 'UPDATE works SET wordcount = tmp_works.wordcount FROM tmp_works WHERE works.universalid = tmp_works.universalid'
	cursor.execute(q)
	dbconnection.commit()

	q = 'DROP TABLE tmp_works'
	cursor.execute(q)

	dbconnection.connectioncleanup()

	return


def buildtrigramindices(workcategoryprefix):
	"""
	build indices for the works based on trigrams keyed to the stripped line
	
	:param cursor:
	:param dbconnection:
	:return:
	"""
	
	print('building indices for author dbs')
	dbconnection = setconnection()
	cursor = dbconnection.cursor()

	query = 'SELECT universalid FROM authors WHERE universalid LIKE %s ORDER BY universalid ASC'
	data = (workcategoryprefix+'%',)
	cursor.execute(query, data)
	results = resultiterator(cursor)
	
	manager = Manager()
	uids = manager.list([r[0] for r in results])
	commitcount = MPCounter()

	dbconnection.connectioncleanup()
	print('\t', len(uids), 'items to index')

	workers = setworkercount()
	if not icanpickleconnections():
		connections = [None for _ in range(workers)]
	else:
		connections = {i: setconnection() for i in range(workers)}

	jobs = [Process(target=mpindexbuilder, args=(uids, commitcount, connections[i])) for i in range(workers)]
	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	if connections[0]:
		for c in connections:
			connections[c].connectioncleanup()

	return


def mpindexbuilder(universalids, commitcount, dbconnection):
	"""
	mp aware indexing pool: helps you crank through 'em

	:param results:
	:return:
	"""

	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()

	while universalids:
		try:
			universalid = universalids.pop()
		except IndexError:
			universalid = None
			universalids = None

		if universalid:
			for column in [('_mu', 'accented_line'), ('_st', 'stripped_line')]:
				query = 'DROP INDEX IF EXISTS {i}_trgm_idx'.format(i=universalid + column[0])
				try:
					dbcursor.execute(query)
				except ImportError:
					print('failed to drop index for', universalid)
					pass

				query = 'CREATE INDEX {i}_trgm_idx ON {t} USING GIN ({c} gin_trgm_ops)'.format(i=universalid + column[0], t=universalid, c=column[1])
				try:
					dbcursor.execute(query)
				except ImportError:
					print('failed to create index for', universalid, '\n\t', query)

			commitcount.increment()
			if commitcount.value % 250 == 0:
				dbconnection.commit()
			if commitcount.value % 250 == 0:
				print('\t', commitcount.value, 'indices created')

	return

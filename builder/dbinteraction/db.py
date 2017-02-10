# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import json
import configparser
import psycopg2

from builder.parsers.parse_binfiles import peekatcanon
from builder.builder_classes import dbOpus, dbAuthor

config = configparser.ConfigParser()
config.read('config.ini')


def dbcitationinsert(authorobject, dbreadyversion, cursor, dbconnection):
	"""
	run throught the dbreadyversion and put it into the db
	iterate through the works
	problems, though: some work numbers are incorrect/impossible

	NOTE: before 26 dec 2016 works were stored in their own DBs; this worked quite wel, but it yielded a problem when
	the INS and DDP data was finally merged into Hipparchia: suddenly postrgresql was working with 190k DBs, and that
	yields a significant scheduler and filesystem problem; the costs were too high; nevertheless a TLG and LAT only system
	could readily used the old model

	here is a marked line...
	['1', [('0', '87'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1')], "Μή μ' ἔπεϲιν μὲν ϲτέργε, νόον δ' ἔχε καὶ φρέναϲ ἄλληι, ", "Μη μ' επεϲιν μεν ϲτεργε, νοον δ' εχε και φρεναϲ αλληι, "]

	Warning Never, never, NEVER use Python string concatenation (+) or string parameters interpolation (%) to pass variables to a SQL query string. Not even at gunpoint.
	The correct way to pass variables in a SQL command is using the second argument of the execute() method:

	sample query: SELECT * from gr9999w999 WHERE stripped_line LIKE '%debeas%'
	won't stick until you dbconnection.commit()
	for hypens:
	SELECT * from gr9999w999 WHERE (stripped_line LIKE '%marinam%') OR (hyphenated_words LIKE '%marinam%')
	:param authorobject:
	:param dbreadyversion:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	dbauthoradder(authorobject, cursor)
	authortablemaker(authorobject.universalid, cursor)

	for indexedat in range(len(authorobject.works)):
		# warning: '002' might be the value at work[0]
		workmaker(authorobject, authorobject.works[indexedat].worknumber, indexedat, cursor)

	index = 0
	for line in dbreadyversion:
		if line[2] == '' or line[2] == ' ':
			# cd resets can produce blanks with bad line numbers, etc
			# this can leave a blank line numbered '5.1' sandwiched between 5.292 and 5.293
			# let's hope nothing with useful info gets skipped...
			pass
		else:
			if index % 2000 == 0:
				dbconnection.commit()

			index += 1
			wn = int(line[0])

			if wn < 10:
				wn = '00' + str(wn)
			elif wn < 100:
				wn = '0' + str(wn)
			else:
				wn = str(wn)

			wkuniversalid = authorobject.universalid + 'w' + wn

			try:
				wk = authorobject.works[authorobject.workdict[wn]]
				wklvs = list(wk.structure.keys())
				wklvs.sort()
				try:
					toplvl = wklvs.pop()
				except:
					# this does in fact seem to be at the bottom of a certain class of error; and it likely emerges from bad idx parsing: tough
					print(
						'could not find top level; workobject level list is empty: anum=' + authorobject.universalid + ' wn=' + str(
							wk.worknumber) + ' tit=' + wk.title)
					if authorobject.universalid[0] == 'g':
						print('\tin a cold sweat i am attempting to derive work structure from canon file')
						labels = peekatcanon(wkuniversalid)
						toplvl = len(labels)
						for i in range(0, toplvl):
							wk.structure[i] = labels[i]
						print('\tstructure set to', wk.structure)

				tups = line[1]

				if authorobject.universalid[0:2] in ['ZZ', 'XX', 'YY', 'in', 'dp', 'ch']:
					# level 5 contains useful information for the inscriptions: don't nuke it
					# level00 = line; level01 = face; [gap in levels]; level05 = documentID
					# all of this gets taken care of in secondpassdbrewrite.py
					pass
				else:
					for lvl in range(0, len(tups)):
						if lvl > toplvl:
							# do we want '-1' instead?
							tups[lvl] = (lvl, -1)

				# print('ll',wn,wkuniversalid,wk.structure,wklvs, toplvl,tups,line[2])
				# tempting to not add the -1's, but they are used to check top levels later
				query = 'INSERT INTO ' + authorobject.universalid + \
						' (index, wkuniversalid, level_00_value, level_01_value, ' \
						'level_02_value, level_03_value, level_04_value, level_05_value, marked_up_line, accented_line, ' \
						'stripped_line, hyphenated_words, annotations) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
				data = (index, wkuniversalid, tups[0][1], tups[1][1], tups[2][1], tups[3][1], tups[4][1], tups[5][1],
						line[2], line[3], line[4], line[5], line[6])
				try:
					cursor.execute(query, data)

				except psycopg2.DatabaseError as e:
					print('insert into ', authorobject.universalid, 'failed at', index, 'while attempting', data)
					print('Error %s' % e)

			except:
				if index < 2:
					# the proper work number will be set real soon now
					pass
				else:
					print('failed to set a work number for db insert: at line', str(index), 'work', wn,
						  'does not fit with', authorobject.idxname)
					ws = json.dumps(wk.structure)
					print('workobject: wn=' + str(wk.worknumber) + ' tit=' + wk.title + ' struct=' + ws)
					# print('compare to the authorobject: ' + authorobject.universalid + ' wks=' + authorobject.works)
					print(line)
				pass

	dbconnection.commit()

	return


def authortablemaker(authordbname, cursor):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""
	query = 'DROP TABLE IF EXISTS public.' + authordbname
	cursor.execute(query)

	query = 'CREATE TABLE public.' + authordbname
	query += '( index integer NOT NULL DEFAULT nextval(\'' + authordbname + '\'::regclass), '
	query += 'wkuniversalid character varying(10),'
	query += 'level_05_value character varying(64),'
	query += 'level_04_value character varying(64),'
	query += 'level_03_value character varying(64),'
	query += 'level_02_value character varying(64),'
	query += 'level_01_value character varying(64),'
	query += 'level_00_value character varying(64),'
	query += 'marked_up_line text,'
	query += 'accented_line text,'
	query += 'stripped_line text,'
	query += 'hyphenated_words character varying(128),'
	query += 'annotations character varying(256) ) WITH ( OIDS=FALSE );'

	cursor.execute(query)

	query = 'GRANT SELECT ON TABLE ' + authordbname + ' TO hippa_rd;'
	cursor.execute(query)

	# print('failed to create',workdbname)

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
	try:
		lg = wk.language
	except:
		lg = authorobject.language
	# how many bilingual authors are there again?

	pr = authorobject.universalid[0:2]

	workdbname = pr + nm + 'w' + nn

	return workdbname


def dbauthoradder(authorobject, cursor):
	"""
	SQL setup
	:param authorobject:
	:param cursor:
	:return:
	"""
	# steal from above: get a table name and then drop the 'w001' bit
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

	query = 'INSERT INTO authors (universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location) ' \
			'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
	data = (uid, lang, authorobject.idxname, authorobject.aka, authorobject.shortname, authorobject.cleanname,
			authorobject.genre, '', '', '')
	try:
		cursor.execute(query, data)
	except Exception as e:
		print('dbauthoradder() failed to insert', authorobject.cleanname)
		print(e)
		print('aborted query was:', query, data)

	return


def dbauthorloadersubroutine(uid, cursor):
	# only call this AFTER you have built all of the work objects so that they can be placed into it

	query = 'SELECT * from authors where universalid = %s'
	data = (uid,)
	cursor.execute(query, data)
	try:
		results = cursor.fetchone()
	except:
		# browser forward was producing random errors:
		# 'failed to find the requested author: SELECT * from authors where universalid = %s ('gr1194',)'
		# but this is the author being browsed and another click will browse him further
		# a timing issue: the solution seems to be 'hipparchia.run(threaded=False, host="0.0.0.0")'
		print('failed to find the requested author:', query, data)
	# note that there is no graceful way out of this: you have to have an authorobject in the end

	# (universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location)
	# supposed to fit the dbAuthor class exactly
	author = dbAuthor(results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7],
					  results[8], results[9])

	return author


def dbauthorandworkloader(authoruid, cursor):
	# note that this will return an AUTHOR filled with WORKS
	# the original Opus objects only exist at the end of HD reads
	# rebuild them from the DB instead: note that this object is simpler than the earlier version, but the stuff you need should all be there...

	author = dbauthorloadersubroutine(authoruid, cursor)

	query = 'SELECT universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, ' \
			'levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, ' \
			'firstline, lastline, authentic FROM works WHERE universalid LIKE %s'
	data = (authoruid + '%',)
	cursor.execute(query, data)
	try:
		results = cursor.fetchall()
	except:
		# see the notes on the exception to dbauthormakersubroutine: you can get here and then die for the same reason
		print('failed to find the requested work:', query, data)
		results = []

	for match in results:
		work = dbOpus(match[0], match[1], match[2], match[3], match[4], match[5], match[6], match[7], match[8],
					  match[9], match[10], match[11], match[12], match[13], match[14], match[15], match[16],
					  match[17], match[18], match[19])
		author.addwork(work)

	return author


def workmaker(authorobject, worknumber, indexedat, cursor):
	uid = tablenamer(authorobject, indexedat)
	wk = authorobject.works[indexedat]

	query = 'DELETE FROM works WHERE universalid = %s'
	data = (uid,)
	try:
		cursor.execute(query, data)
	except:
		pass

	ll = []
	for level in range(0, 6):
		try:
			ll.append(wk.structure[level])
		except:
			ll.append('')

	query = 'INSERT INTO works (universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05) ' \
			'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
	data = (uid, wk.title, wk.language, '', ll[0], ll[1], ll[2], ll[3], ll[4], ll[5])
	try:
		cursor.execute(query, data)
	except:
		print('workmaker() failed to insert', uid, wk.title)
		print(cursor.query)

	return


def setconnection(config):
	dbconnection = psycopg2.connect(user=config['db']['DBUSER'], host=config['db']['DBHOST'],
									port=config['db']['DBPORT'], database=config['db']['DBNAME'],
									password=config['db']['DBPASS'])
	# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	return dbconnection


def resetauthorsandworksdbs(tmpprefix, prefix):
	"""
	clean out any old info before insterting new info
	you have to purge the inscription and ddp dbs every time because the names can change between builds

	:param prefix:
	:return:
	"""
	dbc = setconnection(config)
	cursor = dbc.cursor()

	for zap in [tmpprefix, prefix]:
		q = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		d = (zap + '%',)
		cursor.execute(q, d)
		results = cursor.fetchall()
		dbc.commit()

		authors = []
		for r in results:
			authors.append(r[0][0:6])
		authors = list(set(authors))

		print('\t', len(authors), zap, 'tables to drop')

		count = 0
		for a in authors:
			count += 1
			q = 'DROP TABLE public.' + a
			try:
				cursor.execute(q)
			except:
				# 'table "in090cw001" does not exist'
				# because a build got interrupted? one hopes it is safe to pass
				pass
			if count % 500 == 0:
				dbc.commit()
			if count % 10000 == 0:
				print('\t', count, zap, 'tables dropped')

		q = 'DELETE FROM authors WHERE universalid LIKE %s'
		d = (zap + '%',)
		cursor.execute(q, d)

		q = 'DELETE FROM works WHERE universalid LIKE %s'
		d = (zap + '%',)
		cursor.execute(q, d)

	dbc.commit()
	return


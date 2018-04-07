# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

import psycopg2

from builder.builderclasses import dbAuthor, dbOpus
from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbhelperfunctions import generatequeryvaluetuples, generatecopystream, tablenamer


def insertworksintoauthortable(authorobject, dbreadyversion, dbconnection):
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

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	for indexedat in range(len(authorobject.works)):
		# warning: '002' might be the value at work[0]
		workmaker(authorobject, indexedat, dbcursor)

	queryvalues = generatequeryvaluetuples(dbreadyversion, authorobject)

	stream = generatecopystream(queryvalues)

	columns = ('index',
				'wkuniversalid',
				'level_00_value',
				'level_01_value',
				'level_02_value',
				'level_03_value',
				'level_04_value',
				'level_05_value',
				'marked_up_line',
				'accented_line',
				'stripped_line',
				'hyphenated_words',
				'annotations')

	table = authorobject.universalid

	separator = '\t'

	dbcursor.copy_from(stream, table, sep=separator, columns=columns)

	return


def dbauthoradder(authorobject, dbconnection):
	"""
	SQL setup
	:param authorobject:
	:param cursor:
	:return:

	"""

	cursor = dbconnection.cursor()

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
			authorobject.genre, '', None, '')
	try:
		cursor.execute(query, data)
	except Exception as e:
		print('dbauthoradder() failed to insert', authorobject.cleanname)
		print(e)
		print('aborted query was:', query, data)

	dbconnection.commit()

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
		results = list()

	for match in results:
		work = dbOpus(match[0], match[1], match[2], match[3], match[4], match[5], match[6], match[7], match[8],
					  match[9], match[10], match[11], match[12], match[13], match[14], match[15], match[16],
					  match[17], match[18], match[19])
		author.addwork(work)

	return author


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

	query = 'INSERT INTO works (universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05) ' \
			'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
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
	cursor = dbconnection.cursor()

	for zap in [tmpprefix, prefix]:
		q = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		d = (zap + '%',)
		cursor.execute(q, d)
		results = cursor.fetchall()
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
				cursor.execute(q)
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
		cursor.execute(q, d)

		q = 'DELETE FROM works WHERE universalid LIKE %s'
		d = (zap + '%',)
		cursor.execute(q, d)

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
	cursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_{t} AS SELECT * FROM {t} LIMIT 0'.format(t=table)
	cursor.execute(q)
	dbconnection.commit()

	targetcolumns = ', '.join(targetcolumnlist)
	blankvals = ['%s' for i in range(0,len(targetcolumnlist)+1)]
	vv = ', '.join(blankvals)
	count = 0
	for k in insertiondict.keys():
		count += 1
		q = 'INSERT INTO tmp_{t} ({s}, {c}) VALUES ({vv} )'.format(t=table, c=targetcolumns, s=sharedcolumn, vv=vv)
		d = tuple([k] + insertiondict[k])
		cursor.execute(q, d)
		if count % 100 == 0:
			dbconnection.commit()

	dbconnection.commit()

	tc = targetcolumns.split(',')
	tc = [re.sub('\s', '', c) for c in tc]

	targs = ['{c}=tmp_{t}.{c}'.format(t=table,c=c) for c in tc]
	targs = ', '.join(targs)

	q = 'UPDATE {t} SET {targs} FROM tmp_{t} WHERE {t}.{s}=tmp_{t}.{s}'.format(t=table, targs=targs, s=sharedcolumn)
	cursor.execute(q)
	dbconnection.commit()

	q = 'DROP TABLE tmp_{t}'.format(t=table)
	cursor.execute(q)

	dbconnection.connectioncleanup()

	return


"""
	one bugged insert in CHR:
	
	promted by: *)IEZE[KIH/L\].

	psycopg2.DataError: missing data for column "hyphenated_words"
	CONTEXT:  COPY zz0012, line 668: "668	ZZ0012w002	1	a	1	1	1	3﹕52	<hmu_metadata_region value="Constantinople" /><hmu_metadata_city val..."


	bugged line (668, 'ZZ0012w002', '1', 'a', '1', '1', '1', '3﹕52', '<hmu_metadata_region value="Constantinople" /><hmu_metadata_city value="Hagia Sophia" /><hmu_metadata_date value="c 886-912 ac?" /><hmu_metadata_publicationinfo value="Materials 59" /><hmu_metadata_documentnumber value="33" />Ἰεζε[κιήλ\\].', 'ἰεζεκιήλ\\', 'ιεζεκιηλ\\', '', '')

	[ch0202w00x]
	Constantinople [Chr.] (Ekphrasis H. Sophias),
	3:52
	a, line 1
	(Assigned date of 899 CE)
		Region:  Constantinople
		City:  Hagia Sophia
		Additional publication info:  Materials 59
		Editor's date:  c 886-912 ac?

		Ἰεζε[κιήλ\]. 	a 1

		[Ἀββα]κου⟨μ⟩ Ἀμβακούμ 	b 1

		[Ἰων]ᾶϲ 	c 1

		Ἰερεμίαϲ. 	d,1 1

hipparchiaDB=# select index,hyphenated_words from ch0202 order by index asc;
 index | hyphenated_words
-------+------------------
   591 |
   592 |
   593 |
   594 |
   595 |
   596 |
   597 |
   598 |
   599 |
   600 |
   601 |
   602 |
   603 |
   604 |
   605 |
   606 | εἰρήνη
   607 |
   608 |
   609 |
   610 | φῶϲ
   611 |
   612 |
   613 |
   614 |
   615 |
   616 |
   617 |
   618 |
   619 |
   620 |
   621 |
   622 |
   623 |
   624 |
   625 |
   626 |
   627 |
   628 |
   629 |
   630 |
   631 |
   632 |
   633 |
   634 |
   635 |
   636 |
   637 |
   638 | βοήθη
   639 |
   640 | νηκήτα
   641 |
   642 |
   643 |
   644 |
   645 |
   646 |
   647 | οἰκουμενικοῦ
   648 |
   649 |
   650 |
   651 |
   652 |
   653 |
   654 |
   655 |
   656 |
   657 |
   658 |
   659 |
   660 |
   661 |
   662 |
   663 |
   664 |
   665 | τέξεται
   666 |
   667 |
   668 |
   669 |
   670 |
   671 |
   672 |
   673 |
   674 |
   675 |
   676 |
   677 | ἡμῶν
   678 | λογιϲθήϲε-
   679 |
   680 | ἕτεροϲ
   681 |
   682 | αὐτόν
   683 |
(93 rows)

"""
# -*- coding: utf-8 -*-
# assuming py35 or higher
import json
import re
from builder.parsers.parse_binfiles import peekatcanon

import psycopg2

from builder.builder_classes import dbOpus
from builder.dbinteraction.dbprepsubstitutions import quarterspacer


def dbcitationinsert(authorobject, dbreadyversion, cursor, dbconnection):
	"""
	run throught the dbreadyversion and put it into the db
	iterate through the works
	problems, though: some work numbers are incorrect/impossible

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

	for indexedat in range(len(authorobject.works)):
		# because '002' might be the value at work[0]
		tablemaker(tablenamer(authorobject, authorobject.works[indexedat].worknumber, indexedat), cursor)
		workmaker(authorobject, authorobject.works[indexedat].worknumber, indexedat, cursor)
	
	# debugging
	# dbreadyversion = pickle.load(open(outputfile, "rb"))
	
	index = 0
	for line in dbreadyversion:
		if line[2] == '' or line[2] == ' ':
			# cd resets can produce blanks with bad line numbers, etc
			# let's hope nothing with useful info gets skipped...
			# this can leave a blank line numbered '5.1' sandwiched between 5.292 and 5.293
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

			workdbname = authorobject.universalid+'w'+wn
			# workdbname = 'gr9999w999'

			try:
				wk = authorobject.works[authorobject.workdict[wn]]
				wklvs = list(wk.structure.keys())
				try:
					toplvl = wklvs.pop()
				except:
					# this does in fact seem to be at the bottom of a certain class of error; and it likely emerges from bad idx parsing: tough
					print('could not find top level; workobject level list is empty: anum='+authorobject.universalid+' wn='+str(wk.worknumber)+' tit='+wk.title)
					if authorobject.universalid[0] == 'g':
						print('\tin a cold sweat i am attempting to derive work structure from canon file')
						labels = peekatcanon(workdbname)
						toplvl = len(labels)
						for i in range(0,toplvl):
							wk.structure[i] = labels[i]
						print('\tstructure set to',wk.structure)
						
				tups = line[1]
				for lvl in range(0, len(tups)):
					if lvl > toplvl:
						# do we want '-1' instead?
						tups[lvl] = (lvl, -1)

				# tempting to not add the -1's, but they are used to check top levels later
				query = 'INSERT INTO ' + workdbname + ' (index, level_00_value, level_01_value, level_02_value, level_03_value, level_04_value, level_05_value, marked_up_line, stripped_line, hyphenated_words, annotations)' \
				                                      ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
				data = (index, tups[0][1], tups[1][1], tups[2][1], tups[3][1], tups[4][1], tups[5][1], line[2], line[3], line[4], line[5])
				try:
					cursor.execute(query, data)
				except psycopg2.DatabaseError as e:
					# db overheats?
					# unfortunately pausing does seem to help: note that retried queries sometimes work
					#
					# second effort failed: b"INSERT INTO lt0474w006 (index, level_00_value, level_01_value, level_02_value, level_03_value, level_04_value, level_05_value, marked_up_line, stripped_line, hyphenated_words, annotations) VALUES (16814, '5', '50',  -1,  -1,  -1,  -1, 'ac repugnabit, non occides; quod si repugnat, \xe2\x80\x98<hmu_small_latin_capitals>endoplo-', 'ac repugnabit, non occides; quod si repugnat, \xe2\x80\x98endoplo-', '\xe2\x80\x98<hmu_small_latin_capitals>endoplo</hmu_small_latin_capitals>7rato&,\xe2\x80\x99 \xe2\x80\x98<hmu_small_latin_capitals>endoplo</hmu_small_latin_capitals>7rato&,\xe2\x80\x99', '')"
					# note that there is an \x80 in there...
					print('insert into ',workdbname,'failed at',index,'while attempting',data)
					print('Error %s' % e)
					print('Policy is to assume bad hyphen parsing and to build that line without the relevant hyphen data. This word will now be very hard to find.\n')
					data = ( index, tups[0][1], tups[1][1], tups[2][1], tups[3][1], tups[4][1], tups[5][1], line[2], line[3], '', line[5])
					try:
						cursor.execute(query, data)
					except:
						print('That failed too..')

			except:
				if index < 2:
					# the proper work number will be set real soon now
					pass
				else:
					print('failed to set a work number for db insert: at line',str(index),'work',wn,'does not fit with',authorobject.idxname)
					ws = json.dumps(wk.structure)
					print('workobject: wn='+str(wk.worknumber)+' tit='+wk.title+' struct='+ws)
					# print('compare to the authorobject: ' + authorobject.universalid + ' wks=' + authorobject.works)
					print(line)
				pass

	dbconnection.commit()

	return


def tablenamer(authorobject, thework, indexedat):
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
	if lg == 'G':
		pr = 'gr'
	elif lg == 'L':
		pr = 'lt'
	else:
		pr = ''
		print('oh, I do not speak', lg, 'and I will be unable to access a DB')

	workdbname = pr + nm + 'w' + nn

	return workdbname


def tablemaker(workdbname, cursor):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""
	query = 'DROP TABLE IF EXISTS public.' + workdbname
	cursor.execute(query)

	query = 'CREATE TABLE public.' + workdbname
	query += '( index integer NOT NULL DEFAULT nextval(\'' + workdbname + '\'::regclass), '
	query += 'level_05_value character varying(64),'
	query += 'level_04_value character varying(64),'
	query += 'level_03_value character varying(64),'
	query += 'level_02_value character varying(64),'
	query += 'level_01_value character varying(64),'
	query += 'level_00_value character varying(64),'
	query += 'marked_up_line text,'
	query += 'stripped_line text,'
	query += 'hyphenated_words character varying(128),'
	query += 'annotations character varying(256) ) WITH ( OIDS=FALSE );'

	cursor.execute(query)

	# query = 'DROP INDEX '+wdkbname+'_index_idx'

	# query = 'CREATE INDEX ' + workdbname + '_index_idx '
	# query += 'ON public.' + workdbname
	# query += ' USING btree (index);'

	# cursor.execute(query)

	query = 'GRANT SELECT ON TABLE ' + workdbname + ' TO hippa_rd;'
	cursor.execute(query)

	# print('failed to create',workdbname)

	return


def labelmaker(workuid, cursor):
	"""
	SQL setup
	:param workuid:
	:param cursor:
	:return:
	"""
	query = 'SELECT levellabels_05,levellabels_04,levellabels_03,levellabels_02,levellabels_01,levellabels_00 from works where universalid = %s'
	# query = 'SELECT levellabels_00,levellabels_01,levellabels_02,levellabels_03,levellabels_04,levellabels_05 from works where universalid = %s'
	data = (workuid,)
	try:
		cursor.execute(query, data)
	except:
		print('somehow failed to find work info for', workuid)

	results = cursor.fetchone()
	return results


def dbauthoradder(authorobject, cursor):
	"""
	SQL setup
	:param authorobject:
	:param cursor:
	:return:
	"""
	# steal from above: get a table name and then drop the 'w001' bit
	uid = authorobject.universalid
	lang = authorobject.works[0].language

	query = 'DELETE FROM authors WHERE universalid = %s'
	data = (uid,)
	try:
		cursor.execute(query, data)
	except:
		pass

	query = 'INSERT INTO authors (universalid, language, idxname, akaname, shortname, cleanname, genres, floruit, location) ' \
	        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
	data = (uid, lang, authorobject.idxname, authorobject.aka, authorobject.shortname, authorobject.cleanname,
	        authorobject.genre, '', '')
	try:
		cursor.execute(query, data)
	except:
		print('failed to insert', authorobject.cleanname)
		print('aborted query was:', query)

	return


def dbauthormakersubroutine(uid, cursor):
	# only call this AFTER you have built all of the work objects so that they can be placed into it
	# the original Author objects only exist at the end of HD reads
	# rebuild them from the DB instead: note that this object is simpler than the earlier version, but the stuff you need should all be there...

	query = 'SELECT * from authors where universalid = %s'
	data = (uid,)

	cursor.execute(query, data)
	results = cursor.fetchone()
	# (universalid, language, idxname, akaname, shortname, cleanname, genres, birth, death, floruit, location)
	# supposed to fit the dbAuthor class exactly
	author = dbAuthor(results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7],
	                  results[8], results[9], results[10])

	return author


def dbauthorandworkmaker(authoruid, cursor):
	# note that this will return an AUTHOR filled with WORKS
	# the original Opus objects only exist at the end of HD reads
	# rebuild them from the DB instead: note that this object is simpler than the earlier version, but the stuff you need should all be there...

	author = dbauthormakersubroutine(authoruid, cursor)

	query = 'SELECT * from works where universalid LIKE %s'
	data = (authoruid + '%',)
	cursor.execute(query, data)
	results = cursor.fetchall()
	# (universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05)

	for match in results:
		work = dbOpus(match[0], match[1], match[2], match[3], match[4], match[5], match[6], match[7], match[8],
		              match[9])
		author.addwork(work)

	return author


def workmaker(authorobject, worknumber, indexedat, cursor):
	uid = tablenamer(authorobject, worknumber, indexedat)
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
		print('failed to insert', uid, wk.title)
		print(cursor.query)

	return


def setconnection(config):
	dbconnection = psycopg2.connect(user=config['db']['DBUSER'], host=config['db']['DBHOST'],
	                                port=config['db']['DBPORT'], database=config['db']['DBNAME'],
	                                password=config['db']['DBPASS'])
	# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
	
	return dbconnection



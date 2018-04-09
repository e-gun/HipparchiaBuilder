# -*- coding: utf-8 -*-
# !../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from builder.dbinteraction.connection import setconnection


def createwordcounttable(tablename, extracolumns=False):
	"""
	the SQL to generate the wordcount table
	:param tablename:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	query = 'DROP TABLE IF EXISTS public.' + tablename
	dbcursor.execute(query)

	query = 'CREATE TABLE public.' + tablename
	query += '( entry_name character varying(64),'
	query += ' total_count integer,'
	query += ' gr_count integer,'
	query += ' lt_count integer,'
	query += ' dp_count integer,'
	query += ' in_count integer,'
	query += ' ch_count integer'
	if extracolumns:
		query += ', frequency_classification character varying(64),'
		query += ' early_occurrences integer,'
		query += ' middle_occurrences integer,'
		query += ' late_occurrences integer'
		if type(extracolumns) == type([]):
			for c in extracolumns:
				query += ', '+c+' integer'
	query += ') WITH ( OIDS=FALSE );'

	dbcursor.execute(query)

	query = 'GRANT SELECT ON TABLE {tn} TO hippa_rd;'.format(tn=tablename)
	dbcursor.execute(query)

	tableletter = tablename[-2:]

	q = 'DROP INDEX IF EXISTS public.wcindex{tl}'.format(tl=tableletter, tn=tablename)
	dbcursor.execute(q)

	q = 'CREATE UNIQUE INDEX wcindex{tl} ON {tn} (entry_name)'.format(tl=tableletter, tn=tablename)
	dbcursor.execute(q)

	dbconnection.connectioncleanup()

	return


def deletetemporarydbs(temprefix):
	"""

	kill off the first pass info now that you have made the second pass

	:param temprefix:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'SELECT universalid FROM works WHERE universalid LIKE %s'
	d = (temprefix+'%',)
	dbcursor.execute(q, d)
	results = dbcursor.fetchall()

	authors = list()
	for r in results:
		a = r[0]
		authors.append(a[0:6])
	authors = list(set(authors))

	for a in authors:
		q = 'DROP TABLE public.{a}'.format(a=a)
		dbcursor.execute(q)

	q = 'DELETE FROM authors WHERE universalid LIKE %s'
	d = (temprefix + '%',)
	dbcursor.execute(q, d)

	q = 'DELETE FROM works WHERE universalid LIKE %s'
	d = (temprefix + '%',)
	dbcursor.execute(q, d)

	dbconnection.connectioncleanup()

	return


def insertchronologicalmetadata(metadatadict, thetable):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	metadatadict:
		ἅρπαξ: {'frequency_classification': 'core vocabulary (more than 50)', 'early': 2, 'middle': 6, 'late': 0}

	:param countdict:
	:return:
	"""

	dbcconnection = setconnection()
	dbcursor = dbcconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM {tb} LIMIT 0'.format(tb=thetable)
	dbcursor.execute(q)

	count = 0
	for entry in metadatadict.keys():
		count += 1
		dbcconnection.checkneedtocommit(count)

		q = 'INSERT INTO tmp_metadata (entry_name, frequency_classification, early_occurrences, middle_occurrences, late_occurrences) ' \
		    'VALUES ( %s, %s, %s, %s, %s)'
		try:
			d = (entry, metadatadict[entry]['frequency_classification'], metadatadict[entry]['early'],
			     metadatadict[entry]['middle'], metadatadict[entry]['late'])
		except KeyError:
			# there is no date data because the word is not found in a dateable text
			# d = (entry, metadatadict[entry]['frequency_classification'], '', '', '')
			d = None
		if d:
			dbcursor.execute(q, d)

	dbcconnection.commit()

	qtemplate = """
		UPDATE {tb} SET
			frequency_classification = tmp_metadata.frequency_classification,
			early_occurrences = tmp_metadata.early_occurrences,
			middle_occurrences = tmp_metadata.middle_occurrences,
			late_occurrences = tmp_metadata.late_occurrences
		FROM tmp_metadata
		WHERE {tb}.entry_name = tmp_metadata.entry_name
	"""
	q = qtemplate.format(tb=thetable)
	dbcursor.execute(q)
	dbcconnection.commit()

	q = 'DROP TABLE tmp_metadata'
	dbcursor.execute(q)
	dbcconnection.commit()

	dbcconnection.connectioncleanup()
	# return the dict so you can reuse the data
	return metadatadict


def insertgenremetadata(metadatadict, genrename, thetable):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	metadatadict:
		ἅρπαξ: {'frequency_classification': 'core vocabulary (more than 50)', 'early': 2, 'middle': 6, 'late': 0}

	:param countdict:
	:return:
	"""

	# a clash between the stored genre names 'Alchem.' and names that are used for columns (which can't include period or whitespace)
	thecolumn = re.sub(r'[\.\s]', '', genrename).lower()

	dbc = setconnection()
	cursor = dbc.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM {tb} LIMIT 0'.format(tb=thetable)
	cursor.execute(q)

	count = 0
	for entry in metadatadict.keys():
		count += 1
		q = 'INSERT INTO tmp_metadata (entry_name, {tc}) VALUES ( %s, %s)'.format(tc=thecolumn)
		try:
			d = (entry, metadatadict[entry][genrename])
		except KeyError:
			# there is no date data because the word is not found in a dateable text
			# d = (entry, metadatadict[entry]['frequency_classification'], '', '', '')
			d = None
		if d:
			cursor.execute(q, d)

		if count % 2500 == 0:
			dbc.commit()

	dbc.commit()
	q = 'UPDATE {tb} SET {tc} = tmp_metadata.{tc} FROM tmp_metadata WHERE {tb}.entry_name = tmp_metadata.entry_name'.format(
		tb=thetable, tc=thecolumn)
	cursor.execute(q)
	dbc.commit()

	q = 'DROP TABLE tmp_metadata'
	cursor.execute(q)
	dbc.commit()

	# return the dict so you can reuse the data
	return metadatadict


def dbchunkloader(enumeratedchunkedkeys, masterconcorcdance, wordcounttable):
	"""

	:param resultbundle:
	:return:
	"""

	dbconnection = setconnection(simple=True)
	dbcursor = dbconnection.cursor()

	qtemplate = """
	INSERT INTO {wct}_{lt} (entry_name, total_count, gr_count, lt_count, dp_count, in_count, ch_count)
		VALUES (%s, %s, %s, %s, %s, %s, %s)
	"""

	transtable = buildhipparchiatranstable()

	# 'v' should be empty, though; ϙ will go to 0
	letters = '0abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ'
	letters = {letters[l] for l in range(0, len(letters))}

	chunknumber = enumeratedchunkedkeys[0]
	chunkedkeys = enumeratedchunkedkeys[1]

	count = 0
	for key in chunkedkeys:
		count += 1
		cw = masterconcorcdance[key]
		skip = False
		try:
			lettertable = cleanaccentsandvj(key[0], transtable)
		# fine, but this just put any 'v' words inside of 'u' where they can never be found
		# so v issue has to be off the table by now
		except:
			# IndexError: string index out of range
			lettertable = '0'
			skip = True

		if lettertable not in letters:
			lettertable = '0'

		if skip is not True:
			q = qtemplate.format(wct=wordcounttable, lt=lettertable)
			d = (key, cw['total'], cw['gr'], cw['lt'], cw['dp'], cw['in'], cw['ch'])
			try:
				dbcursor.execute(q, d)
			except:
				print('failed to insert', key)

		if count % 2000 == 0:
			dbconnection.commit()

	# print('\t', str(len(chunkedkeys)), 'words inserted into the wordcount tables')
	print('\tfinished chunk', chunknumber + 1)

	dbconnection.connectioncleanup()

	return
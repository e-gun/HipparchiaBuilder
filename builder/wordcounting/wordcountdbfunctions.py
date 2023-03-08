# -*- coding: utf-8 -*-
# !../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-23
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from builder.dbinteraction.connection import setconnection


def createwordcounttable(tablename, extracolumns=False):
	"""
	the SQL to generate the wordcount table

	simple example:

		CREATE TABLE public.wordcounts_ζ (
			entry_name character varying(64),
			total_count integer DEFAULT 0,
			gr_count integer DEFAULT 0,
			lt_count integer DEFAULT 0,
			dp_count integer DEFAULT 0,
			in_count integer DEFAULT 0,
			ch_count integer DEFAULT 0
			)

	compound example:

		CREATE TABLE public.dictionary_headword_wordcounts (
			entry_name character varying(64),
			total_count integer DEFAULT 0,
			gr_count integer DEFAULT 0,
			lt_count integer DEFAULT 0,
			dp_count integer DEFAULT 0,
			in_count integer DEFAULT 0,
			ch_count integer DEFAULT 0,
			frequency_classification character varying(64),
			early_occurrences integer DEFAULT 0,
			middle_occurrences integer DEFAULT 0,
			late_occurrences integer DEFAULT 0
		,			acta integer DEFAULT 0,
			agric integer DEFAULT 0,
			...
			)

	:param tablename:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	query = 'DROP TABLE IF EXISTS public.{t}'.format(t=tablename)
	dbcursor.execute(query)

	qtemplateextension = ''

	qtemplatebase = """
		CREATE TABLE public.{t} (
			entry_name character varying(64),
			total_count integer DEFAULT 0,
			gr_count integer DEFAULT 0,
			lt_count integer DEFAULT 0,
			dp_count integer DEFAULT 0,
			in_count integer DEFAULT 0,
			ch_count integer DEFAULT 0{x}
			)
	"""

	if extracolumns:
		qtemplateextension = """,
			frequency_classification character varying(64),
			early_occurrences integer DEFAULT 0,
			middle_occurrences integer DEFAULT 0,
			late_occurrences integer DEFAULT 0
		"""

	if isinstance(extracolumns, list):
		qtemplatesupplement = '\t\t\t{c} integer DEFAULT 0'
		supplement = list()
		for c in extracolumns:
			supplement.append(qtemplatesupplement.format(c=c))
		qtemplateextension = qtemplateextension + ',' + ',\n'.join(supplement)

	query = qtemplatebase.format(t=tablename, x=qtemplateextension)

	dbcursor.execute(query)

	query = 'GRANT SELECT ON TABLE {tn} TO hippa_rd'.format(tn=tablename)
	dbcursor.execute(query)

	tableletter = tablename[-2:]

	query = 'DROP INDEX IF EXISTS public.wcindex{tl}'.format(tl=tableletter, tn=tablename)
	dbcursor.execute(query)

	query = 'CREATE UNIQUE INDEX wcindex{tl} ON {tn} (entry_name)'.format(tl=tableletter, tn=tablename)
	dbcursor.execute(query)

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

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM {tb} LIMIT 0'.format(tb=thetable)
	dbcursor.execute(q)

	count = 0
	for entry in metadatadict.keys():
		count += 1
		dbconnection.checkneedtocommit(count)

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

	dbconnection.commit()

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
	dbconnection.commit()

	q = 'DROP TABLE tmp_metadata'
	dbcursor.execute(q)
	dbconnection.commit()

	dbconnection.connectioncleanup()
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

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_metadata AS SELECT * FROM {tb} LIMIT 0'.format(tb=thetable)
	dbcursor.execute(q)

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
			dbcursor.execute(q, d)

		if count % 2500 == 0:
			dbconnection.commit()

	dbconnection.commit()
	q = 'UPDATE {tb} SET {tc} = tmp_metadata.{tc} FROM tmp_metadata WHERE {tb}.entry_name = tmp_metadata.entry_name'.format(
		tb=thetable, tc=thecolumn)
	dbcursor.execute(q)
	dbconnection.commit()

	q = 'DROP TABLE tmp_metadata'
	dbcursor.execute(q)
	dbconnection.commit()

	dbconnection.connectioncleanup()
	
	# return the dict so you can reuse the data
	return metadatadict

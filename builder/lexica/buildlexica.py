# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from multiprocessing import Manager

from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.genericworkerobject import GenericInserterObject
from builder.lexica.mplexicalworkers import mpanalysisinsert, mpgreekdictionaryinsert, mplatindictionaryinsert, \
	mplemmatainsert

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


def formatgklexicon():
	"""

	parse the XML for Liddell and Scott and insert it into the DB

	:return:
	"""

	dictfile = config['lexica']['lexicadir'] + config['lexica']['greeklexicon']
	dictdb = 'greek_dictionary'

	sqldict = getlexicaltablestructuredict(dictdb)

	resettable(dictdb, sqldict['columns'], sqldict['index'])

	f = open(dictfile, encoding='utf-8', mode='r')
	entries = f.readlines()
	f.close()

	print('formatting Liddell and Scott.', len(entries), 'entries to parse')

	# testing
	# entries = entries[10000:10010]

	manager = Manager()
	entries = manager.list(entries)

	workerobject = GenericInserterObject(mpgreekdictionaryinsert, argumentlist=[dictdb, entries])
	workerobject.dothework()

	return


def formatlatlexicon():
	"""

	parse the XML for Lewis and Short and insert it into the DB

	:return:
	"""

	dictfile = config['lexica']['lexicadir'] + config['lexica']['latinlexicon']
	dictdb = 'latin_dictionary'

	sqldict = getlexicaltablestructuredict(dictdb)

	resettable(dictdb, sqldict['columns'], sqldict['index'])

	f = open(dictfile, encoding='utf-8', mode='r')
	entries = f.readlines()
	f.close()

	print('formatting Lewis and Short.', len(entries), 'entries to parse')

	manager = Manager()
	entries = manager.list(entries)

	workerobject = GenericInserterObject(mplatindictionaryinsert, argumentlist=[dictdb, entries])
	workerobject.dothework()

	return


def grammarloader(language):
	"""
	pick and language to shove into the grammardb; parse; shove

    a slight shift in the finder should let you do both lemm and anal, but cumbersome to build the switches and triggers
	the format is dictionary entry + tab + magic number + a tabbed list of forms with the morph in parens.
	lemmata:
	a(/dhn	1750487	a(/ddhn (indeclform (adverb))	a(/dhn (indeclform (adverb))	a)/ddhn (indeclform (adverb))	a)/dhn (indeclform (adverb))

	analyses:
	!ane/ntwn	{9619125 9 a)ne/ntwn,a)ni/hmi	send up	aor imperat act 3rd pl}{9619125 9 a)ne/ntwn,a)ni/hmi	send up	aor part act masc/neut gen pl}{37155703 9 e)ne/ntwn,e)ni/hmi	send in	aor imperat act 3rd pl}{37155703 9 e)ne/ntwn,e)ni/hmi	send in	aor part act masc/neut gen pl}

	:param language:
	:return:
	"""

	if language == 'latin':
		lemmafile = config['lexica']['lexicadir'] + config['lexica']['ltlemm']
		table = 'latin_lemmata'
		islatin = True
	elif language == 'greek':
		lemmafile = config['lexica']['lexicadir'] + config['lexica']['gklemm']
		table = 'greek_lemmata'
		islatin = False
	else:
		lemmafile = ''
		table = 'no_such_table'
		islatin = False
		print('I do not know', language, '\nBad things are about to happen.')

	sqldict = getlexicaltablestructuredict('lemma')

	resettable(table, sqldict['columns'], sqldict['index'])

	f = open(lemmafile, encoding='utf-8', mode='r')
	entries = f.readlines()
	f.close()

	print('loading', language, 'lemmata.', len(entries), 'items to load')

	manager = Manager()
	entries = manager.list(entries)

	workerobject = GenericInserterObject(mplemmatainsert, argumentlist=[table, entries, islatin])
	workerobject.dothework()

	return


def analysisloader(language):
	"""

	turn 'greek-analyses.txt' into a db table

	an analysis line looks like this:
		!a/sdwn {32430564 9 e)/sdwn,ei)sdi/dwmi flow into       aor ind act 3rd pl (epic doric aeolic)}{32430564 9 e)/sdwn,ei)sdi/dwmi  flow into       aor ind act 1st sg (epic)}

		word + {analysis 1}{analysis 2}{...}

	each inset analysis is:
		{xrefnumber digit ancientform1,ancientform2 translation parsinginfo}

	the real parsing work is done by mpanalysisinsert

	:param language:
	:return:
	"""

	# a slight shift in the finder should let you do both lemm and anal, but cumbersome to build the switches and triggers
	# the format is dictionary entry + tab + magic number + a tabbed list of forms with the morph in parens.
	# lemmata:
	# a(/dhn	1750487	a(/ddhn (indeclform (adverb))	a(/dhn (indeclform (adverb))	a)/ddhn (indeclform (adverb))	a)/dhn (indeclform (adverb))

	# analyses:
	# !ane/ntwn	{9619125 9 a)ne/ntwn,a)ni/hmi	send up	aor imperat act 3rd pl}{9619125 9 a)ne/ntwn,a)ni/hmi	send up	aor part act masc/neut gen pl}{37155703 9 e)ne/ntwn,e)ni/hmi	send in	aor imperat act 3rd pl}{37155703 9 e)ne/ntwn,e)ni/hmi	send in	aor part act masc/neut gen pl}

	if language == 'latin':
		morphfile = config['lexica']['lexicadir'] + config['lexica']['ltanal']
		table = 'latin_morphology'
		islatin = True
	elif language == 'greek':
		morphfile = config['lexica']['lexicadir'] + config['lexica']['gkanal']
		table = 'greek_morphology'
		islatin = False
	else:
		morphfile = ''
		table = 'no_such_table'
		islatin = False
		print('I do not know', language, '\nBad things are about to happen.')

	sqldict = getlexicaltablestructuredict('analysis')

	resettable(table, sqldict['columns'], sqldict['index'])
	f = open(morphfile, encoding='utf-8', mode='r')
	forms = f.readlines()
	f.close()

	# rather than manage a list of 100s of MB in size let's get chunky
	# this also allows us to send updates outside of the commit() moment
	# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks#1751478
	print('loading {lg} morphology. {n} items to load'.format(lg=language, n=len(forms)))

	chunksize = 50000
	formbundles = [forms[i:i + chunksize] for i in range(0, len(forms), chunksize)]
	bundlecount = 0

	for bundle in formbundles:
		bundlecount += 1
		manager = Manager()
		# need this because all searches are lower case and so you can't find "Διόϲ" via what will be a search for "διόϲ"
		bundle[:] = [x.lower() for x in bundle]
		items = manager.list(bundle)

		workerobject = GenericInserterObject(mpanalysisinsert, argumentlist=[table, items, islatin])
		workerobject.dothework()

		if bundlecount * chunksize < len(forms):
			# this check prevents saying '950000 forms inserted' at the end when there are only '911871 items to load'
			print('\t', str(bundlecount * chunksize), 'forms inserted')

	# we will be doing some searches inside of possible_dictionary_forms: need the right kind of index for it
	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'CREATE INDEX {l}_analysis_trgm_idx ON {l}_morphology USING GIN ( possible_dictionary_forms gin_trgm_ops)'.format(l=language)
	dbcursor.execute(q)

	dbconnection.connectioncleanup()

	return


def resettable(tablename, tablestructurelist, indexcolumn):
	"""

	drop old table and create a new empty table

		tablestructurelist = ['dictionary_entry character varying(64)', 'xref_number integer', 'derivative_forms text']
		indexcolumn = 'dictionary_entry'

	:param tablename:
	:param tablestructurelist:
	:param indexcolumn:
	:return:
	"""

	dbc = setconnection()
	cursor = dbc.cursor()

	columns = ', '.join(tablestructurelist)

	q = 'DROP TABLE IF EXISTS public.{tn}; DROP INDEX IF EXISTS {tn}_idx;'.format(tn=tablename)
	cursor.execute(q)

	q = 'CREATE TABLE public.{tn} ( {c} ) WITH ( OIDS=FALSE );'.format(tn=tablename, c=columns)
	cursor.execute(q)

	q = 'GRANT SELECT ON TABLE public.{tn} TO hippa_rd;'.format(tn=tablename)
	cursor.execute(q)

	q = 'CREATE INDEX {tn}_idx ON public.{tn} USING btree ({ic} COLLATE pg_catalog."default");'.format(tn=tablename, ic=indexcolumn)
	cursor.execute(q)

	dbc.connectioncleanup()

	return


def getlexicaltablestructuredict(tablename):
	"""

	find out what to send resettable()

	unique indices are only available to the latin dictionary

		hipparchiaDB=# CREATE UNIQUE INDEX greek_dictionary_idx ON greek_dictionary (entry_name);
		ERROR:  could not create unique index "greek_dictionary_idx"
		DETAIL:  Key (entry_name)=(δέλτοϲ) is duplicated.

		hipparchiaDB=# CREATE UNIQUE INDEX latin_dictionary_idx ON latin_dictionary (entry_name);
		CREATE INDEX

		CREATE UNIQUE INDEX greek_lemmata_idx on greek_lemmata (dictionary_entry);
		ERROR:  could not create unique index "greek_lemmata_idx"
		DETAIL:  Key (dictionary_entry)=(ϲκάφοϲ) is duplicated.

		hipparchiaDB=# CREATE UNIQUE INDEX greek_morphology_idx on public.greek_morphology (observed_form);
		ERROR:  could not create unique index "greek_morphology_idx"
		DETAIL:  Key (observed_form)=(Ἀιδωνῆοϲ) is duplicated.

	:return:
	"""

	options = {
		'lemma': {
			'columns': ['dictionary_entry character varying(64)', 'xref_number integer', 'derivative_forms text[]'],
			'index': 'dictionary_entry'},
		'analysis': {
			'columns': ['observed_form character varying(64)', 'xrefs character varying(128)', 'prefixrefs character varying(128)', 'possible_dictionary_forms text'],
			'index': 'observed_form'},
		'latin_dictionary': {
			'columns': ['entry_name character varying(64)', 'metrical_entry character varying(64)', 'id_number integer',
						'entry_key character varying(64)', 'pos character varying(64)', 'translations text', 'entry_body text'],
			'index': 'entry_name'},
		'greek_dictionary': {
			'columns': ['entry_name character varying(64)', 'metrical_entry character varying(64)', 'unaccented_entry character varying(64)',
						'id_number integer', 'pos character varying(64)', 'translations text', 'entry_body text'],
			'index': 'entry_name'}
	}

	returndict = options[tablename]

	return returndict

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from multiprocessing import Manager

from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.genericworkerobject import GenericInserterObject
from builder.lexica.mpgrammarworkers import mpanalysisinsert, mplemmatainsert
from builder.lexica.fixmorphologydefs import mpanalysisrewrite
from builder.lexica.mpgreekinserters import mpgreekdictionaryinsert, oldxmlmpgreekdictionaryinsert
from builder.lexica.mplatininsterters import newmplatindictionaryinsert, oldmplatindictionaryinsert

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

	print('formatting Liddell and Scott. {e} entries to parse'.format(e=len(entries)))

	# testing
	# entries = entries[1000:1010]

	if config['lexica']['greeklexicon'] == 'greek-lexicon_1999.04.0057.xml':
		# a crude and highly fallible check, but...
		print('using the old style lexical parser')
		inserter = oldxmlmpgreekdictionaryinsert
	else:
		print('using the logeion lexical parser')
		inserter = mpgreekdictionaryinsert

	manager = Manager()
	entries = manager.list(entries)
	workerobject = GenericInserterObject(inserter, argumentlist=[dictdb, entries])
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

	if config['lexica']['latinlexicon'] == 'latin-lexicon_1999.04.0059.xml':
		# a crude and highly fallible check, but...
		print('using the (reliable) old style lexical parser')
		inserter = oldmplatindictionaryinsert
	else:
		print('using the (unrelaible) new sytle lexical parser')
		inserter = newmplatindictionaryinsert

	manager = Manager()
	entries = manager.list(entries)

	workerobject = GenericInserterObject(inserter, argumentlist=[dictdb, entries])
	workerobject.dothework()

	return


def grammarloader(language: str):
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


def analysisloader(language: str):
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
		morphfile = str()
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


def fixmorphologytranslations(language: str):
	"""

	the stock translations included with the observed forms can be defective; a rewritten dictionary entry can fix this

	hipparchiaDB=# select * from greek_morphology where observed_form='πάϲχω';
	 observed_form |  xrefs   | prefixrefs |                                                                  possible_dictionary_forms
	---------------+----------+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------
	 πάϲχω         | 80650925 |            | <possibility_1>πάϲχω<xref_value>80650925</xref_value><xref_kind>9</xref_kind><transl>have</transl><analysis>pres subj act 1st sg</analysis></possibility_1>+
	               |          |            | <possibility_2>πάϲχω<xref_value>80650925</xref_value><xref_kind>9</xref_kind><transl>have</transl><analysis>pres ind act 1st sg</analysis></possibility_2> +
	               |          |            |


	hipparchiaDB=# select id_number from greek_dictionary where entry_name='πάϲχω';
	 id_number
	-----------
	     79983


	hipparchiaDB=# select dictionary_entry,xref_number from greek_lemmata where dictionary_entry='πάϲχω';
	 dictionary_entry | xref_number
	------------------+-------------
	 πάϲχω            |    80650925


	 hipparchiaDB=# select translations from greek_dictionary where entry_name='πάϲχω';
	                                                                                                                                                                                                         translations
	 ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
	  have something done to one ‖ suffer ‖ be ‖ passion ‖ opp. do ‖ to be subject to ‖ he suffer ‖ evil ‖ to be passive ‖ am I to do? ‖ changes ‖ can I help it? ‖ have experience of ‖ were to happen ‖ die ‖ come to be in a state ‖ patient, PMag. Par. ‖ to be ill, suffer ‖ feeling, to be affected ‖ to have ‖ to be ‖ suffer punishment, pay the penalty ‖ ill ‖ thou ‖ state of mind ‖ case ‖ happen ‖ come to be) in a
	 (1 row)


	hipparchiaDB=# SELECT * FROM greek_lemmata limit 3;
	 dictionary_entry | xref_number |                                            derivative_forms
	------------------+-------------+--------------------------------------------------------------------------------------------------------
	 ζῳοπλάϲτηϲ       |    45889565 | {ζῳοπλαϲτῶν,ζῳοπλάϲται,ζῳοπλάϲταϲ,ζῳοπλάϲτηϲ}
	 ζῳογόνοϲ         |    45877520 | {ζωιογόνοι,ζῳογόνων,ζωιογόνοϲ,ζῳογόνον,ζῳογόνῳ,ζῳογόνοϲ,ζῳογόνοιϲ,ζῳογόνοι,ζῳογόνου,ζῳογόνουϲ,ζῳογόνα}
	 ζῳοφαγία         |    45906672 | {ζῳοφαγίαϲ,ζῳοφαγία,ζῳοφαγίαν}
	(3 rows)

	1. grab all of the xref_number values from greek_lemmata
	2. associate the first two translations from the dictionary with this headword
	3. then gobble up all of the greek_morphology entries that have this xref
	4. then check each '<transl></transl>' inside of all of the possible_dictionary_forms for these entries


	:param language:
	:return:
	"""

	assert language in ['greek', 'latin']

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	table = '{lg}_lemmata'.format(lg=language)

	q = 'SELECT dictionary_entry, xref_number FROM {t}'.format(t=table)
	dbcursor.execute(q)

	headwords = dbcursor.fetchall()
	headwords = {h[0]: h[1] for h in headwords if h[0]}

	table = '{lg}_dictionary'.format(lg=language)
	q = 'SELECT entry_name, translations FROM {t}'.format(t=table)
	dbcursor.execute(q)

	translations = dbcursor.fetchall()
	translations = {t[0]: t[1].split(' ‖ ')[:1] for t in translations}

	headwords = [(h, headwords[h], translations[h]) for h in headwords if h in translations]
	headwords = [(h[0], h[1], ', '.join(h[2])) for h in headwords]

	dbconnection.connectioncleanup()

	print('fixing definitions in {lg}_morphology table. cross-referencing against {n} headwords'.format(lg=language, n=len(headwords)))

	# chunksize = 10000
	chunksize = 500  # debug
	formbundles = [headwords[i:i + chunksize] for i in range(0, len(headwords), chunksize)]
	bundlecount = 0

	for bundle in formbundles:
		bundlecount += 1
		manager = Manager()
		items = manager.list(bundle)

		workerobject = GenericInserterObject(mpanalysisrewrite, argumentlist=[language, items])
		workerobject.dothework()

		if bundlecount * chunksize < len(headwords):
			# this check prevents saying '950000 forms inserted' at the end when there are only '911871 items to load'
			print('\t', str(bundlecount * chunksize), 'forms checked')

	return


def resettable(tablename: str, tablestructurelist: list, indexcolumn: str):
	"""

	drop old table and create a new empty table

		tablestructurelist = ['dictionary_entry character varying(64)', 'xref_number integer', 'derivative_forms text']
		indexcolumn = 'dictionary_entry'

	:param tablename:
	:param tablestructurelist:
	:param indexcolumn:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	columns = ', '.join(tablestructurelist)

	q = 'DROP TABLE IF EXISTS public.{tn}; DROP INDEX IF EXISTS {tn}_idx;'.format(tn=tablename)
	dbcursor.execute(q)

	q = 'CREATE TABLE public.{tn} ( {c} ) WITH ( OIDS=FALSE );'.format(tn=tablename, c=columns)
	dbcursor.execute(q)

	q = 'GRANT SELECT ON TABLE public.{tn} TO hippa_rd;'.format(tn=tablename)
	dbcursor.execute(q)

	q = 'CREATE INDEX {tn}_idx ON public.{tn} USING btree ({ic} COLLATE pg_catalog."default");'.format(tn=tablename, ic=indexcolumn)
	dbcursor.execute(q)

	dbconnection.connectioncleanup()

	return


def getlexicaltablestructuredict(tablename: str) -> dict:
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
			'columns': ['entry_name character varying(256)', 'metrical_entry character varying(256)', 'id_number real',
						'entry_key character varying(64)', 'pos character varying(64)', 'translations text', 'entry_body text'],
			'index': 'entry_name'},
		'greek_dictionary': {
			'columns': ['entry_name character varying(256)', 'metrical_entry character varying(256)', 'unaccented_entry character varying(256)',
						'id_number real', 'pos character varying(64)', 'translations text', 'entry_body text'],
			'index': 'entry_name'}
	}

	returndict = options[tablename]

	return returndict

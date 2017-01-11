# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import configparser
from multiprocessing import Process, Manager

from builder.builder_classes import MPCounter
from builder.dbinteraction.mplexicalworkers import mplatindictionaryinsert, mpgreekdictionaryinsert, mplemmatainsert, mpanalysisinsert
from builder.dbinteraction.db import setconnection

config = configparser.ConfigParser()
config.read('config.ini')


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

	print('formatting Liddell and Scott.',len(entries),'entries to parse')

	manager = Manager()
	entries = manager.list(entries)
	commitcount = MPCounter()

	workers = int(config['io']['workers'])
	jobs = [Process(target=mpgreekdictionaryinsert, args=(dictdb, entries, commitcount)) for i in
			range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()

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

	print('formatting Lewis and Short.',len(entries),'entries to parse')

	manager = Manager()
	entries = manager.list(entries)
	commitcount = MPCounter()

	workers = int(config['io']['workers'])
	jobs = [Process(target=mplatindictionaryinsert, args=(dictdb, entries, commitcount)) for i in
			range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()

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

	:param lemmalanguage:
	:param lemmabasedir:
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
		print('I do not know',language,'\nBad things are about to happen.')

	sqldict = getlexicaltablestructuredict('lemma')

	resettable(table, sqldict['columns'], sqldict['index'])

	f = open(lemmafile, encoding='utf-8', mode='r')
	entries = f.readlines()
	f.close()

	print('loading', language, 'lemmata.',len(entries),'items to load')

	manager = Manager()
	entries = manager.list(entries)
	commitcount = MPCounter()
	
	workers = int(config['io']['workers'])
	jobs = [Process(target=mplemmatainsert, args=(table, entries, islatin, commitcount)) for i in
	        range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return


def analysisloader(language):
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
		print('I do not know',language,'\nBad things are about to happen.')

	sqldict = getlexicaltablestructuredict('lemma')

	resettable(table, sqldict['columns'], sqldict['index'])
	f = open(morphfile, encoding='utf-8', mode='r')
	forms = f.readlines()
	f.close()
	
	# rather than manage a list of 100s of MB in size let's get chunky
	# this also allows us to send updates outside of the commit() moment
	# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks#1751478
	print('loading', language, 'morphology.',len(forms),'items to load')

	chunksize = 50000
	formbundles = [forms[i:i + chunksize] for i in range(0, len(forms), chunksize)]
	bundlecount = 0
	
	for bundle in formbundles:
		bundlecount += 1
		manager = Manager()
		# need this because all searches are lower case and so you can't find "Διόϲ" via what will be a search for "διόϲ"
		bundle[:] = [x.lower() for x in bundle]
		items = manager.list(bundle)
		commitcount = MPCounter()

		workers = int(config['io']['workers'])
		jobs = [Process(target=mpanalysisinsert, args=(table, items, islatin, commitcount)) for i in
		        range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()
		if str(bundlecount*chunksize) < len(forms):
			# this check prevents saying '950000 forms inserted' at the end when there are only '911871 items to load'
			print('\t',str(bundlecount*chunksize),'forms inserted')
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

	dbc = setconnection(config)
	cursor = dbc.cursor()

	columns = ', '.join(tablestructurelist)

	q = 'DROP TABLE IF EXISTS public.' + tablename + '; DROP INDEX IF EXISTS ' + tablename + '_idx;'
	cursor.execute(q)

	q = 'CREATE TABLE public.' + tablename + ' ( '+columns+' ) WITH ( OIDS=FALSE );'
	cursor.execute(q)

	q = 'GRANT SELECT ON TABLE public.' + tablename + ' TO hippa_rd;'
	cursor.execute(q)

	q = 'CREATE INDEX ' + tablename + '_idx ON public.' + tablename + ' USING btree ('+indexcolumn+' COLLATE pg_catalog."default");'
	cursor.execute(q)

	dbc.commit()

	return


def getlexicaltablestructuredict(tablename):
	"""

	find out what to send resettable()

	:return:
	"""

	options = {
		'lemma': {
			'columns': ['dictionary_entry character varying(64)', 'xref_number integer', 'derivative_forms text'],
			'index': 'dictionary_entry' },
		'analysis': {
			'columns': ['observed_form character varying(64)', 'possible_dictionary_forms text'],
			'index': 'observed_form'},
		'latin_dictionary': {
			'columns': [ 'entry_name character varying(64)', 'metrical_entry character varying(64)', 'id_number character varying(8)',
						 'entry_type character varying(8)', 'entry_key character varying(64)', 'entry_options "char"', 'entry_body text' ],
			'index': 'entry_name'},
		'greek_dictionary': {
			'columns': ['entry_name character varying(64)', 'metrical_entry character varying(64)', 'unaccented_entry character varying(64)',
						'id_number character varying(8)', 'entry_type character varying(8)', 'entry_options "char"', 'entry_body text'],
			'index': 'entry_name'}
	}

	returndict = options[tablename]

	return returndict

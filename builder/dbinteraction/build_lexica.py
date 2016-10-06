# -*- coding: utf-8 -*-
import re
from builder.parsers.lexica import gr1betaconverter

import configparser
from multiprocessing import Process, Manager

from builder.builder_classes import MPCounter
from builder.dbinteraction.mplexicalworkers import mplatindictionaryinsert, mpgreekdictionaryinsert, mplemmatainsert, mpanalysisinsert

config = configparser.ConfigParser()
config.read('config.ini')

def formatlewisandshort(dbconnection, cursor, topdir):
	dictfiles = findlexiconfiles('l', topdir + 'HipparchiaData/lexica/')
	
	dictdb = 'latin_dictionary'
	
	resetlatindictdb(dictdb, dbconnection, cursor)
	
	for df in dictfiles:
		f = open(df, encoding='utf-8', mode='r')
		entries = f.readlines()
		f.close()
				
		manager = Manager()
		entries = manager.list(entries)
		commitcount = MPCounter()
		
		workers = int(config['io']['workers'])
		jobs = [Process(target=mplatindictionaryinsert, args=(dictdb, entries, commitcount)) for i in range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()
		
	return


def formatliddellandscott(dbconnection, cursor, topdir):
	# n29246 can't be entered because it has no key
	
	dictfiles = findlexiconfiles('g', topdir + 'HipparchiaData/lexica/')
	dictdb = 'greek_dictionary'
	
	resetgreekdictdb(dictdb, dbconnection, cursor)
	
	for df in dictfiles:
		f = open(df, encoding='utf-8', mode='r')
		entries = f.readlines()
		f.close()
		
		manager = Manager()
		entries = manager.list(entries)
		commitcount = MPCounter()
		
		workers = int(config['io']['workers'])
		jobs = [Process(target=mpgreekdictionaryinsert, args=(dictdb, entries, commitcount)) for i in
		        range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()
		
	return


def grammarloader(lemmalanguage, lemmabasedir, dbconnection, cursor):
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
	
	# send 'gl' or 'll'
	
	fileanddb = findlemmafiles(lemmalanguage, lemmabasedir)
	grammardb = fileanddb[1]
	lemmafile = fileanddb[0]
	
	if lemmalanguage == 'll':
		latin = True
	else:
		latin = False
	
	print('loading',grammardb)
	resetlemmadb(grammardb, dbconnection, cursor)
	
	f = open(lemmafile, encoding='utf-8', mode='r')
	entries = f.readlines()
	f.close()
	
	manager = Manager()
	entries = manager.list(entries)
	commitcount = MPCounter()
	
	workers = int(config['io']['workers'])
	jobs = [Process(target=mplemmatainsert, args=(grammardb, entries, latin, commitcount)) for i in
	        range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return


def analysisloader(analysisfile, grammardb, l, dbconnection, cursor):
	# a slight shift in the finder should let you do both lemm and anal, but cumbersome to build the switches and triggers
	# the format is dictionary entry + tab + magic number + a tabbed list of forms with the morph in parens.
	# lemmata:
	# a(/dhn	1750487	a(/ddhn (indeclform (adverb))	a(/dhn (indeclform (adverb))	a)/ddhn (indeclform (adverb))	a)/dhn (indeclform (adverb))
	
	# analyses:
	# !ane/ntwn	{9619125 9 a)ne/ntwn,a)ni/hmi	send up	aor imperat act 3rd pl}{9619125 9 a)ne/ntwn,a)ni/hmi	send up	aor part act masc/neut gen pl}{37155703 9 e)ne/ntwn,e)ni/hmi	send in	aor imperat act 3rd pl}{37155703 9 e)ne/ntwn,e)ni/hmi	send in	aor part act masc/neut gen pl}
	
	if l == 'l':
		latin = True
	else:
		latin = False
	
	print('loading', grammardb)
	resetanalysisdb(grammardb, dbconnection, cursor)
	
	f = open(analysisfile, encoding='utf-8', mode='r')
	forms = f.readlines()
	f.close()
	
	# rather than manage a list of 100s of MB in size let's get chunky
	# this also allows us to send updates outside of the commit() moment
	# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks#1751478
	
	chunksize = 50000
	formbundles = [forms[i:i + chunksize] for i in range(0, len(forms), chunksize)]
	bundlecount = 0
	
	for bundle in formbundles:
		bundlecount += 1
		manager = Manager()
		items = manager.list(bundle)
		commitcount = MPCounter()

		workers = int(config['io']['workers'])
		jobs = [Process(target=mpanalysisinsert, args=(grammardb, items, latin, commitcount)) for i in
		        range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()
		print('\t',str(bundlecount*chunksize),'forms inserted')
	return


def findlexiconfiles(lexiconlanguage, dictbasedir):
	"""
	tell me your language and i will give you a list of dictionaries to load
	:param lexiconname:
	:param dictbasedir:
	:return:
	"""
	
	lexicondict = {
		'e': ['english_dictionary.txt'],
		'l': ['latin_lewis_short_a-k.xml', 'latin_lewis_short_l-z.xml'],
		'g': ['greek_liddell_scott_a-de.xml', 'greek_liddell_scott_di-kath.xml', 'greek_liddell_scott_kai-pew.xml',
		      'greek_liddell_scott_pe-ww.xml']
	}
	
	lexlist = lexicondict[lexiconlanguage]
	newlexlist = []
	for lex in lexlist:
		newlexlist.append(dictbasedir + lex)
	
	return newlexlist


def findlemmafiles(lemmalanguage, lemmabasedir):
	"""
	tell me your language and i will give you a list of lemma files to load
	and where to load them
	:param lemmalanguage:
	:param dictbasedir:
	:return:
	"""
	lemmadict = {
		'gl': 'greek-lemmata.txt',
		'ga': 'greek-analyses.txt',
		'll': 'latin-lemmata.txt',
		'la': 'latin-analyses.txt'
	}
	
	lemmadb = {
		'gl': 'greek_lemmata',
		'ga': 'greek_morphology',
		'll': 'latin_lemmata',
		'la': 'latin_morphology'
	}
	
	fileanddb = [lemmabasedir + lemmadict[lemmalanguage], lemmadb[lemmalanguage]]
	
	return fileanddb


def resetlatindictdb(dictdb, dbconnection, cursor):
	"""
	drop if exists and build the framework
	:param dbconnection:
	:param cursor:
	:return:
	"""
	
	q = 'DROP TABLE IF EXISTS public.'+dictdb+';'
	cursor.execute(q)
	
	q = 'CREATE TABLE public.'+dictdb+' ( entry_name character varying(64), metrical_entry character varying(64), id_number character varying(8), entry_type character varying(8), entry_key character varying(64), entry_options "char", entry_body text ) WITH ( OIDS=FALSE );'
	cursor.execute(q)
	
	q = 'GRANT SELECT ON TABLE public.'+dictdb+' TO hippa_rd;'
	cursor.execute(q)
	
	q = 'CREATE INDEX latinentry_idx ON public.'+dictdb+' USING btree (entry_name COLLATE pg_catalog."default");'
	cursor.execute(q)
	dbconnection.commit()
	
	return


def resetgreekdictdb(dictdb, dbconnection, cursor):
	"""
	drop if exists and build the framework
	:param dbconnection:
	:param cursor:
	:return:
	"""
	
	q = 'DROP TABLE IF EXISTS public.' + dictdb + ';'
	cursor.execute(q)
	
	q = 'CREATE TABLE public.' + dictdb + ' ( entry_name character varying(64), metrical_entry character varying(64), unaccented_entry character varying(64), id_number character varying(8), entry_type character varying(8), entry_options "char", entry_body text ) WITH ( OIDS=FALSE );'
	cursor.execute(q)
	
	q = 'GRANT SELECT ON TABLE public.' + dictdb + ' TO hippa_rd;'
	cursor.execute(q)
	
	q = 'CREATE INDEX gkentryword_index ON public.' + dictdb + ' USING btree (entry_name COLLATE pg_catalog."default");'
	cursor.execute(q)
	dbconnection.commit()
	
	return


def resetlemmadb(grammardb, dbconnection, cursor):
	"""
	drop if exists and build the framework
	:param dbconnection:
	:param cursor:
	:return:
	"""
	
	q = 'DROP TABLE IF EXISTS public.' + grammardb + '; DROP INDEX IF EXISTS '+grammardb+'_idx;'
	cursor.execute(q)
	
	q = 'CREATE TABLE public.' + grammardb + ' ( dictionary_entry character varying(64), xref_number integer, derivative_forms text ) WITH ( OIDS=FALSE );'
	cursor.execute(q)
	
	q = 'GRANT SELECT ON TABLE public.' + grammardb + ' TO hippa_rd;'
	cursor.execute(q)
	
	q = 'CREATE INDEX '+grammardb+'_idx ON public.' + grammardb + ' USING btree (dictionary_entry COLLATE pg_catalog."default");'
	cursor.execute(q)
	dbconnection.commit()
	
	return


def resetanalysisdb(grammardb, dbconnection, cursor):
	"""
	drop if exists and build the framework
	:param dbconnection:
	:param cursor:
	:return:
	"""
	
	q = 'DROP TABLE IF EXISTS public.' + grammardb + '; DROP INDEX IF EXISTS ' + grammardb + '_idx;'
	cursor.execute(q)
	
	q = 'CREATE TABLE public.' + grammardb + ' ( observed_form character varying(64), possible_dictionary_forms text ) WITH ( OIDS=FALSE );'
	cursor.execute(q)
	
	q = 'GRANT SELECT ON TABLE public.' + grammardb + ' TO hippa_rd;'
	cursor.execute(q)
	
	q = 'CREATE INDEX ' + grammardb + '_idx ON public.' + grammardb + ' USING btree (observed_form COLLATE pg_catalog."default");'
	cursor.execute(q)
	dbconnection.commit()
	
	return


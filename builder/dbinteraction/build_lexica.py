# -*- coding: utf-8 -*-
from multiprocessing import Process, Manager
import configparser
import time
import re
from builder.parsers.lexica import betaconvertandsave, greekwithvowellengths, gr1betaconverter, gr2betaconverter, \
	latinvowellengths
from builder.parsers.betacode_to_unicode import stripaccents, replacegreekbetacode
from builder.dbinteraction.db import setconnection
from builder.builder_classes import MPCounter

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
		jobs = [Process(target=parallellatindictionaryinsert, args=(dictdb, entries, commitcount)) for i in range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()
		
	return


def parallellatindictionaryinsert(dictdb, entries, commitcount):
	"""
	work on an indivudual entry
	:param entry:
	:return:
	"""
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	bodyfinder = re.compile(r'(<entryFree(.*?)>)(.*?)(</entryFree>)')
	greekfinder = re.compile(r'(<foreign lang="greek">)(.*?)(</foreign>)')
	
	while len(entries) > 0:
		try: entry = entries.pop()
		except: entry = ''
	
		if entry[0:10] != "<entryFree":
			# print(entry[0:25])
			pass
		else:
			segments = re.search(bodyfinder, entry)
			try:
				body = segments.group(3)
			except:
				print('died at', entry)
				body = ''
			info = segments.group(2)
			parsedinfo = re.search('id="(.*?)"\stype="(.*?)"\skey="(.*?)" opt="(.*?)"', info)
			id = parsedinfo.group(1)
			type = parsedinfo.group(2)
			key = parsedinfo.group(3)
			opt = parsedinfo.group(4)
			
			# handle words like abactus which have key... n... opt... where n is the variant number
			# this pattern interrupts the std parsedinfo flow
			metricalentry = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
			entry = re.sub('(_|\^)', '', metricalentry)
			metricalentry = latinvowellengths(metricalentry)
			
			key = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
			key = latinvowellengths(key)
			
			# do some quickie greek replacements
			body = re.sub(greekfinder, gr2betaconverter, body)
			
			query = 'INSERT INTO ' + dictdb + ' (entry_name, metrical_entry, id_number, entry_type, entry_key, entry_options, entry_body) VALUES (%s, %s, %s, %s, %s, %s, %s)'
			data = (entry, metricalentry, id, type, key, opt, body)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				print('at',id, entry)
	
	dbc.commit()
	curs.close()
	del dbc
	
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
		jobs = [Process(target=parallelgreekdictionaryinsert, args=(dictdb, entries, commitcount)) for i in
		        range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()
		
		id = 0
		
	return


def parallelgreekdictionaryinsert(dictdb, entries, commitcount):
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
	greekfinder = re.compile('(<*?lang="greek"*?>)(.*?)(</.*?>)')
	groptfinder = re.compile('(<*?lang="greek"\sopt="n">)(.*?)(</.*?>)')
	orthographyfinder = re.compile('(<orth.*?>)(.*?)(</orth>)')
	
	id = 0
	while len(entries) > 0:
		try: entry = entries.pop()
		except: entry = ''
		
		if entry[0:10] != "<entryFree":
			# print(entry[0:25])
			pass
		else:
			segments = re.search(bodyfinder, entry)
			try:
				body = segments.group(3)
			except:
				body = ''
				print('died at', id, entry)
			info = segments.group(2)
			parsedinfo = re.search('id="(.*?)"\skey=(".*?")\stype="(.*?)"\sopt="(.*?)"', info)
			id = parsedinfo.group(1)
			try:
				key = parsedinfo.group(2)
			except:
				key = ''
				print('did not find key at', id, entry)
			type = parsedinfo.group(3)
			opt = parsedinfo.group(4)
			
			entry = re.sub(r'"(.*?)"', gr1betaconverter, key.upper())
			entry = re.sub(r'(\d{1,})', r' (\1)', entry)
			metrical = re.sub(r'(")(.*?)(")', greekwithvowellengths, key.upper())
			metrical = re.sub(r'(\d{1,})', r'', metrical)
			metrical = re.sub(r'"', r'', metrical)
			
			body = re.sub(greekfinder, gr2betaconverter, body)
			
			orth = re.search(orthographyfinder, body)
			orth = greekwithvowellengths(orth)
			orth = replacegreekbetacode(orth)
			body = re.sub(orthographyfinder, r'\1' + orth + r'\3', body)
			stripped = stripaccents(entry)
			
			query = 'INSERT INTO ' + dictdb + ' (entry_name, metrical_entry, unaccented_entry, id_number, entry_type, entry_options, entry_body) VALUES (%s, %s, %s, %s, %s, %s, %s)'
			data = (entry, metrical, stripped, id, type, opt, body)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				print('at', id, entry)
				
	dbc.commit()
	curs.close()
	del dbc
	
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
	
	query = 'TRUNCATE ' + grammardb
	cursor.execute(query)
	
	f = open(lemmafile, encoding='utf-8', mode='r')
	l = f.readlines()
	f.close()
	
	# this next one for greeklemmata
	keywordfinder = re.compile(r'(.*?\t)(\d{1,})(.*?)$')
	greekfinder = re.compile(r'(\t.*?)(\s.*?)(?=(\t|$))')
	
	count = 0
	for entry in l:
		count += 1
		segments = re.search(keywordfinder, entry)
		dictionaryform = segments.group(1)
		if latin is True:
			dictionaryform = re.sub(r'\t', '', dictionaryform)
		else:
			dictionaryform = re.sub(r'(.*?)\t', gr1betaconverter, dictionaryform.upper())
		otherforms = segments.group(3)
		if latin is not True:
			otherforms = re.sub(greekfinder, betaconvertandsave, otherforms)
		xref = int(segments.group(2))
		# be careful: the corresponding xref is a str inside a text field
		
		query = 'INSERT INTO ' + grammardb + ' (dictionary_entry, xref_number, derivative_forms) VALUES (%s, %s, %s)'
		data = (dictionaryform, xref, otherforms)
		cursor.execute(query, data)
		if count % 5000 == 0:
			print(count, dictionaryform)
			dbconnection.commit()
	dbconnection.commit()
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
	
	trunc = True
	if trunc is True:
		query = 'TRUNCATE ' + grammardb
		cursor.execute(query)
	
	f = open(analysisfile, encoding='utf-8', mode='r')
	l = f.readlines()
	f.close()
	
	# this next one for analyses
	keywordfinder = re.compile(r'(.*?\t)(.*?)$')
	greekfinder = re.compile(r'(\{(\d{1,})\s\d\s(.*?\t)(.*?)\t(.*?)\})')
	
	count = 0
	for entry in l:
		count += 1
		segments = re.search(keywordfinder, entry)
		dictionaryform = segments.group(1)
		
		if latin is True:
			dictionaryform = re.sub(r'\t', '', dictionaryform)
			dictionaryform = latinvowellengths(dictionaryform)
		else:
			dictionaryform = re.sub(r'(.*?)\t', gr1betaconverter, dictionaryform.upper())
		otherforms = segments.group(2)
		entries = re.findall(greekfinder, otherforms)
		# 'πελαθόμην
		# [('{41945513 9 e)pelaqo/mhn,e)pilanqa/nomai\tcause to forget\taor ind mid 1st sg}', 'e)pelaqo/mhn,e)pilanqa/nomai', '\tcause to forget', '\taor ind mid 1st sg'), ('{41945513 9 e)pela_qo/mhn,e)pilanqa/nomai\tcause to forget\timperf ind mp 1st sg (doric)}', 'e)pela_qo/mhn,e)pilanqa/nomai', '\tcause to forget', '\timperf ind mp 1st sg (doric)')]
		possibilities = ''
		number = 0
		for found in entries:
			number += 1
			if latin is True:
				wd = re.sub(r'\t', '', found[2])
				wd = latinvowellengths(wd)
			else:
				wd = re.sub(r'(.*?)\t', gr1betaconverter, found[2].upper())
			possibilities += '<possibility_' + str(number) + '>' + wd + '<xref_value>' + found[
				1] + '</xref_value><transl>' + found[3] + '</transl>' + '<analysis>' + found[
				                 4] + '</analysis></possibility_' + str(number) + '>\n'
		# ' '.join(possibilities)
		query = 'INSERT INTO ' + grammardb + ' (observed_form, possible_dictionary_forms) VALUES (%s, %s)'
		data = (dictionaryform, possibilities)
		cursor.execute(query, data)
		if count % 5000 == 0:
			print(count, dictionaryform)
			dbconnection.commit()
	dbconnection.commit()
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

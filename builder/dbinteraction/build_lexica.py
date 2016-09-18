# -*- coding: utf-8 -*-
from builder.parsers import lexica
import time
import re

def formatlewisandshort(dbconnection, cursor, topdir):

	dictfiles = findlexiconfiles('l',topdir+'HipparchiaData/lexica/')

	dictdb = 'latin_dictionary'

	query = 'TRUNCATE '+dictdb
	cursor.execute(query)

	for df in dictfiles:
		f = open(df, encoding='utf-8', mode='r')
		d = f.readlines()
		f.close()

		bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
		greekfinder = re.compile('(<foreign lang="greek">)(.*?)(</foreign>)')

		for entry in d:
			if entry[0:10] != "<entryFree":
				print(entry[0:25])
			else:
				segments = re.search(bodyfinder,entry)
				try:
					body = segments.group(3)
				except:
					print('died at',entry)
				info = segments.group(2)
				parsedinfo = re.search('id="(.*?)"\stype="(.*?)"\skey="(.*?)" opt="(.*?)"',info)
				id = parsedinfo.group(1)
				type = parsedinfo.group(2)
				key = parsedinfo.group(3)
				opt = parsedinfo.group(4)
				entry = re.sub('(_|\^)','',key)
				# handle words like abactus which have key... n... opt... where n is the variant number
				# this pattern interrupts the std parsedinfo flow
				entry = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', entry)
				key = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
				key = lexica.latinvowellengths(key)

				# do some quickie greek replacements
				body = re.sub(greekfinder, lexica.gr2betaconverter, body)

				query = 'INSERT INTO '+dictdb+' (entry_name, id_number, entry_type, entry_key, entry_options, entry_body) VALUES (%s, %s, %s, %s, %s, %s)'
				data = (entry, id, type, key, opt, body)
				cursor.execute(query, data)
				if int(id[1:]) % 1000 == 0:
					# very consistently died in the middle of entry n29985, but seemingly from overloading the DB, not from the entry itself
					# LSJ has a similar problem: c. 30k lines is about all we are good for before a pause
					print(id)
					dbconnection.commit()
					time.sleep(.1)

	return


def formatliddellandscott(dbconnection, cursor, topdir):
	# n29246 can't be entered because it has no key

	dictfiles = findlexiconfiles('g', topdir + 'HipparchiaData/lexica/')
	dictdb = 'greek_dictionary'

	query = 'TRUNCATE '+dictdb
	cursor.execute(query)

	bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
	greekfinder = re.compile('(<*?lang="greek"*?>)(.*?)(</.*?>)')
	groptfinder = re.compile('(<*?lang="greek"\sopt="n">)(.*?)(</.*?>)')

	for df in dictfiles:
		f = open(df, encoding='utf-8', mode='r')
		d = f.readlines()
		f.close()

		id = 0

		for entry in d:
			if entry[0:10] != "<entryFree":
				print(entry[0:25])
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
					print('did not find key at',id, entry)
				type = parsedinfo.group(3)
				opt = parsedinfo.group(4)

				# entry = re.sub('.*?', replacegreekbetacode, key.upper())
				entry = re.sub(r'"(.*?)"', lexica.gr1betaconverter, key.upper())
				entry = re.sub(r'(\d{1,})', r' (\1)',entry)
				# entry = key
				body = re.sub(greekfinder, lexica.greekvowellengths, body)
				body = re.sub(greekfinder, lexica.gr2betaconverter, body)
				body = re.sub(groptfinder, lexica.gr2betaconverter, body)
				body = re.sub(r' lang="greek"','',body)
				stripped = lexica.stripaccents(entry)

				query = 'INSERT INTO ' + dictdb + ' (entry_name, unaccented_entry, id_number, entry_type, entry_options, entry_body) VALUES (%s, %s, %s, %s, %s, %s)'
				data = (entry, stripped, id, type, opt, body)
				cursor.execute(query, data)
				if int(id[1:]) % 1000 == 0:
					# very consistently died in the middle of entry n29985, but seemingly from overloading the DB, not from the entry itself
					# LSJ has a similar problem: c. 30k lines is about all we are good for before a pause
					print(id)
					dbconnection.commit()
					time.sleep(.1)

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
		segments = re.search(keywordfinder,entry)
		dictionaryform = segments.group(1)
		if latin is True:
			dictionaryform = re.sub(r'\t', '', dictionaryform)
		else:
			dictionaryform = re.sub(r'(.*?)\t', lexica.gr1betaconverter, dictionaryform.upper())
		otherforms = segments.group(3)
		if latin is not True:
			otherforms = re.sub(greekfinder,lexica.betaconvertandsave,otherforms)
		xref = int(segments.group(2))
		# be careful: the corresponding xref is a str inside a text field

		query = 'INSERT INTO ' + grammardb + ' (dictionary_entry, xref_number, derivative_forms) VALUES (%s, %s, %s)'
		data = (dictionaryform, xref, otherforms)
		cursor.execute(query, data)
		if count % 5000 == 0:
			print(count,dictionaryform)
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
		segments = re.search(keywordfinder,entry)
		dictionaryform = segments.group(1)

		if latin is True:
			dictionaryform = re.sub(r'\t', '', dictionaryform)
			dictionaryform = lexica.latinvowellengths(dictionaryform)
		else:
			dictionaryform = re.sub(r'(.*?)\t', lexica.gr1betaconverter, dictionaryform.upper())
		otherforms = segments.group(2)
		entries = re.findall(greekfinder,otherforms)
		# 'πελαθόμην
		# [('{41945513 9 e)pelaqo/mhn,e)pilanqa/nomai\tcause to forget\taor ind mid 1st sg}', 'e)pelaqo/mhn,e)pilanqa/nomai', '\tcause to forget', '\taor ind mid 1st sg'), ('{41945513 9 e)pela_qo/mhn,e)pilanqa/nomai\tcause to forget\timperf ind mp 1st sg (doric)}', 'e)pela_qo/mhn,e)pilanqa/nomai', '\tcause to forget', '\timperf ind mp 1st sg (doric)')]
		possibilities = ''
		number = 0
		for found in entries:
			number += 1
			if latin is True:
				wd = re.sub(r'\t', '', found[2])
				wd = lexica.latinvowellengths(wd)
			else:
				wd = re.sub(r'(.*?)\t',lexica.gr1betaconverter,found[2].upper())
			possibilities += '<possibility_'+str(number)+'>'+wd+'<xref_value>'+found[1]+'</xref_value><transl>'+found[3]+'</transl>'+'<analysis>'+found[4]+'</analysis></possibility_'+str(number)+'>\n'
		# ' '.join(possibilities)
		query = 'INSERT INTO ' + grammardb + ' (observed_form, possible_dictionary_forms) VALUES (%s, %s)'
		data = (dictionaryform, possibilities)
		cursor.execute(query, data)
		if count % 5000 == 0:
			print(count,dictionaryform)
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
		'l': ['latin_lewis_short_a-k.xml','latin_lewis_short_l-z.xml'],
		'g': ['greek_liddell_scott_a-de.xml', 'greek_liddell_scott_di-kath.xml', 'greek_liddell_scott_kai-pew.xml','greek_liddell_scott_pe-ww.xml' ]
	}

	lexlist = lexicondict[lexiconlanguage]
	newlexlist = []
	for lex in lexlist:
		newlexlist.append(dictbasedir+lex)

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

	fileanddb = [lemmabasedir+lemmadict[lemmalanguage],lemmadb[lemmalanguage]]


	return fileanddb

# english not working yet

def formatenglishentries(englishdictionary):
	## still screwing up some entries where the POS arrives irregularly
	## just skip that?

	f = open(englishdictionary, 'r')
	d = f.readlines()
	f.close()

	# testing
	# d = englishdictionary

	newdictionary=[]
	for entry in d:
		newentry = []
		# find entry and pos.
		s = re.match('(.*?)\s',entry)
		# s = re.search(r'(^.*?)(\s\\.*?\\*\s)(.*?\.)\t(.*?)', entry)
		newentry.append(s.group(1))
		entry = entry[len(s.group(0)):]
		s = re.match(r'\\.*\\', entry)
		try:
			entry = entry[len(s.group(0)):]
		except:
			pass
		s = re.match(r'.*?(\w{1,}\.)\t', entry)
		try:
			newentry.append(s.group(1))
		except:
			newentry.append('')
		try:
			entry = entry[len(s.group(0))+1:]
		except:
			pass
		# remove that stuff so we just have the headings left
		# entry = re.sub(r'(.*?)\s\\.*?\\*\s(.*?\.)\t','',entry)
		# remove loci
		entry = re.sub(r'\[.*?\]','',entry)
		# remove leading + multiple spaces and tabs
		entry = re.sub(r'^\s{1,}', '', entry)
		entry = re.sub(r'\t', '', entry)
		entry = re.sub(r'\s{2,}', ' ', entry)
		newentry.append(entry)
		newdictionary.append(newentry)
	return newdictionary


def uploadenglishdict(englishdictionary):
	## INCOMPLETE
	for entry in englishdictionary:
		query = 'INSERT INTO '

	return





# LONG loads for the greek: be careful
# grammarloader(greeklemmata, greeklemmadb, 'g')
# analysisloader(greekanalyses, gkanalysisdb, 'g')
# analysisloader(latinanalyses, latanalysisdb, 'l')
# grammarloader(latinlemmata, latinlemmadb, 'l')

# if you have done it once and like the results, you probably don't ever want to do it again
# loadlewisandshort(lewisandshortxml_pt1, lewisandshortxml_pt2)
# loadlsj(lsjlist)

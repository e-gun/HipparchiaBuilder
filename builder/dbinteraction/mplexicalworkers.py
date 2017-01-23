# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re

from builder.dbinteraction.db import setconnection
from builder.parsers.betacode_to_unicode import stripaccents
from builder.parsers.lexica import latinvowellengths, greekwithvowellengths, betaconvertandsave, greekwithoutvowellengths, \
	lsjgreekswapper

config = configparser.ConfigParser()
config.read('config.ini')


def mplatindictionaryinsert(dictdb, entries, commitcount):
	"""
	work on dictdb entries
	assignable to an mp worker
	insert into db at end
	:param entry:
	:return:
	"""
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	bodyfinder = re.compile(r'(<entryFree(.*?)>)(.*?)(</entryFree>)')
	defectivebody = re.compile(r'(<entryFree(.*?)>)(.*?)')
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
				segments = re.search(defectivebody, entry)
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
			body = re.sub(greekfinder, lambda x: greekwithvowellengths(x.group(2)), body)
			
			query = 'INSERT INTO ' + dictdb + ' (entry_name, metrical_entry, id_number, entry_type, entry_key, entry_options, entry_body) VALUES (%s, %s, %s, %s, %s, %s, %s)'
			data = (entry, metricalentry, id, type, key, opt, body)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				print('\tat',id, entry)
	
	dbc.commit()
	curs.close()
	del dbc
	
	return


def mpgreekdictionaryinsert(dictdb, entries, commitcount):
	"""
	work on dictdb entries
	assignable to an mp worker
	insert into db at end
	:param entry:
	:return:
	"""
	
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	# places where you can find lang="greek"
	# <foreign>; <orth>; <pron>; <quote>; <gen>; <itype>
	# but there can be a nested tag: you can't convert its contents
	# not clear how much one needs to care: but a search inside a match group could be implemented.
	
	bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
	greekfinder = re.compile('(<(foreign|orth|pron|quote|gen|itype|etym|ref).*?lang="greek".*?>)(.*?)(</(foreign|orth|pron|quote|gen|itype|etym|ref)>)')
	# these arise from nested tags: a more elegant solution would be nice; some other day
	restorea = re.compile(r'<γεν λανγ="γρεεκ" οπτ="ν">(.*?)(</gen>)')
	restoreb = re.compile(r'<προν εχτεντ="φυλλ" λανγ="γρεεκ" οπτ="ν"(.*?)(</pron>)')
	restorec = re.compile(r'<ιτψπε λανγ="γρεεκ" οπτ="ν">(.*?)(</itype>)')
	
	id = 0
	while len(entries) > 0:
		try:
			entry = entries.pop()
		except:
			entry = ''
		
		if entry[0:10] != "<entryFree":
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
			try:
				id = parsedinfo.group(1)
				key = parsedinfo.group(2)
				type = parsedinfo.group(3)
				opt = parsedinfo.group(4)
			except:
				# only one greek dictionary entry will throw an exception: n29246
				# print('did not find key at', id, entry)
				id = 'n29246'
				key = ''
				type = ''
				opt = ''
			entry = re.sub(r'"(.*?)"', lambda x: greekwithoutvowellengths(x.group(1)), key.upper())
			entry = re.sub(r'(\d{1,})', r' (\1)', entry)
			metrical = re.sub(r'(")(.*?)(")', lambda x: greekwithvowellengths(x.group(2)), key.upper())
			metrical = re.sub(r'(\d{1,})', r'', metrical)
			metrical = re.sub(r'"', r'', metrical)
			
			body = re.sub(greekfinder, lsjgreekswapper, body)
			body = re.sub(restorea, r'<gen lang="greek" opt="n">\1\2', body)
			body = re.sub(restoreb, r'<pron extent="full">\1\2', body)
			body = re.sub(restorec, r'<itype lang="greek" opt="n">\1\2', body)
			
			stripped = stripaccents(entry)
			
			query = 'INSERT INTO ' + dictdb + ' (entry_name, metrical_entry, unaccented_entry, id_number, entry_type, entry_options, entry_body) VALUES (%s, %s, %s, %s, %s, %s, %s)'
			data = (entry, metrical, stripped, id, type, opt, body)
			try:
				curs.execute(query, data)
			except:
				print('failed insert:',data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				try:
					print('\tat', id, entry)
				except:
					# UnicodeEncodeError
					print('\tat', id)
	
	dbc.commit()
	curs.close()
	del dbc
	
	return


def mplemmatainsert(grammardb, entries, islatin, commitcount):
	"""
	work on grammardb entries
	assignable to an mp worker
	insert into db at end
	:param entry:
	:return:
	"""
	
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	keywordfinder = re.compile(r'(.*?\t)(\d{1,})(.*?)$')
	greekfinder = re.compile(r'(\t.*?)(\s.*?)(?=(\t|$))')

	while len(entries) > 0:
		try:
			entry = entries.pop()
			segments = re.search(keywordfinder, entry)
			dictionaryform = segments.group(1)
			if islatin is True:
				dictionaryform = re.sub(r'\t', '', dictionaryform)
			else:
				dictionaryform = re.sub(r'(.*?)\t', lambda x: greekwithoutvowellengths(x.group(1)), dictionaryform.upper())
			otherforms = segments.group(3)
			if islatin is not True:
				otherforms = re.sub(greekfinder, betaconvertandsave, otherforms)
			xref = int(segments.group(2))
			# be careful: the corresponding xref is a str inside a text field
			
			query = 'INSERT INTO ' + grammardb + ' (dictionary_entry, xref_number, derivative_forms) VALUES (%s, %s, %s)'
			data = (dictionaryform, xref, otherforms)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				print('\tat', dictionaryform)
		except:
			pass
		
	dbc.commit()
	curs.close()
	del dbc
	
	return


def mpanalysisinsert(grammardb, items, islatin, commitcount):
	"""
	work on grammardb entries
	assignable to an mp worker
	insert into db at end
	:param entry:
	:return:
	"""
	
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	keywordfinder = re.compile(r'(.*?\t)(.*?)$')
	greekfinder = re.compile(r'(\{(\d{1,})\s\d\s(.*?\t)(.*?)\t(.*?)\})')
		
	while len(items) > 0:
		try:
			entry = items.pop()
			segments = re.search(keywordfinder, entry)
			dictionaryform = segments.group(1)
			if islatin is True:
				dictionaryform = re.sub(r'\t', '', dictionaryform)
				dictionaryform = latinvowellengths(dictionaryform)
			else:
				dictionaryform = re.sub(r'(.*?)\t', lambda x: greekwithoutvowellengths(x.group(1)), dictionaryform.upper())
			otherforms = segments.group(2)
			entries = re.findall(greekfinder, otherforms)
			# 'πελαθόμην
			# [('{41945513 9 e)pelaqo/mhn,e)pilanqa/nomai\tcause to forget\taor ind mid 1st sg}', 'e)pelaqo/mhn,e)pilanqa/nomai', '\tcause to forget', '\taor ind mid 1st sg'), ('{41945513 9 e)pela_qo/mhn,e)pilanqa/nomai\tcause to forget\timperf ind mp 1st sg (doric)}', 'e)pela_qo/mhn,e)pilanqa/nomai', '\tcause to forget', '\timperf ind mp 1st sg (doric)')]
			possibilities = ''
			number = 0
			for found in entries:
				number += 1
				if islatin is True:
					wd = re.sub(r'\t', '', found[2])
					wd = latinvowellengths(wd)
				else:
					wd = re.sub(r'(.*?)\t', lambda x: greekwithoutvowellengths(x.group(1)), found[2].upper())
				possibilities += '<possibility_' + str(number) + '>' + wd + '<xref_value>' + found[1] + \
				                 '</xref_value><transl>' + found[3] + '</transl>' + '<analysis>' + found[4] + \
				                 '</analysis></possibility_' + str(number) + '>\n'
			# ' '.join(possibilities)
			query = 'INSERT INTO ' + grammardb + ' (observed_form, possible_dictionary_forms) VALUES (%s, %s)'
			data = (dictionaryform, possibilities)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
		except:
			pass

	dbc.commit()
	curs.close()
	del dbc
	
	return
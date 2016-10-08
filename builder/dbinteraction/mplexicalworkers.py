import re
import configparser

from builder.dbinteraction.db import setconnection
from builder.parsers.betacode_to_unicode import replacegreekbetacode, stripaccents
from builder.parsers.lexica import latinvowellengths, gr2betaconverter, gr1betaconverter, greekwithvowellengths, \
	betaconvertandsave

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
	
	bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
	greekfinder = re.compile('(<*?lang="greek"*?>)(.*?)(</.*?>)')
	orthographyfinder = re.compile('(<orth.*?>)(.*?)(</orth>)')
	genfinder = re.compile('(<gen lang="gr.*?>)(.*?)(</gen>)')
	purge = re.compile('<.*?λανγ="γρεεκ".*?>')
	
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
			body = re.sub(genfinder, gr2betaconverter, body)
			
			orth = re.search(orthographyfinder, body)
			orth = greekwithvowellengths(orth)
			orth = replacegreekbetacode(orth)
			body = re.sub(orthographyfinder, r'\1' + orth + r'\3', body)
			body = re.sub(purge,'',body)
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
				dictionaryform = re.sub(r'(.*?)\t', gr1betaconverter, dictionaryform.upper())
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
				print('at', dictionaryform)
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
				dictionaryform = re.sub(r'(.*?)\t', gr1betaconverter, dictionaryform.upper())
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
					wd = re.sub(r'(.*?)\t', gr1betaconverter, found[2].upper())
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
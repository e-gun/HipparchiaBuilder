# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re

from builder.dbinteraction.connection import setconnection
from builder.parsers.betacodeandunicodeinterconversion import cleanaccentsandvj
from builder.parsers.lexica import latinvowellengths, greekwithvowellengths, betaconvertandsave, greekwithoutvowellengths, \
	lsjgreekswapper, translationsummary
from builder.parsers.swappers import superscripterzero, superscripterone

config = configparser.ConfigParser()
config.read('config.ini')


def mplatindictionaryinsert(dictdb, entries, commitcount):
	"""

	work on dictdb entries
	assignable to an mp worker
	insert into db at end

	:param dictdb:
	:param entries:
	:param commitcount:
	:return:
	"""

	dbc = setconnection(config)
	curs = dbc.cursor()

	bodyfinder = re.compile(r'(<entryFree(.*?)>)(.*?)(</entryFree>)')
	defectivebody = re.compile(r'(<entryFree(.*?)>)(.*?)')
	greekfinder = re.compile(r'(<foreign lang="greek">)(.*?)(</foreign>)')
	posfinder = re.compile(r'<pos.*?>(.*?)</pos>')

	while len(entries) > 0:
		try:
			entry = entries.pop()
		except IndexError:
			entry = ''

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
			idnum = parsedinfo.group(1)
			etype = parsedinfo.group(2)  # will go unused
			key = parsedinfo.group(3)
			opt = parsedinfo.group(4)  # will go unused

			# handle words like abactus which have key... n... opt... where n is the variant number
			# this pattern interrupts the std parsedinfo flow
			metricalentry = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
			metricalentry = re.sub(r' \((\d)\)', superscripterone, metricalentry)
			# kill off the tail if you still have one: fĭber" n="1
			metricalentry = re.sub(r'(.*?)"\s.*?$', r'\1', metricalentry)
			entryname = re.sub('(_|\^)', '', metricalentry)
			metricalentry = latinvowellengths(metricalentry)

			key = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
			key = re.sub(r' \((\d)\)', superscripterone, key)
			key = latinvowellengths(key)

			# 'n1000' --> 1000
			idnum = int(re.sub(r'^n', '', idnum))

			pos = ''
			pos += ' ‖ '.join(set(re.findall(posfinder, body)))
			pos = pos.lower()

			translationlist = translationsummary(entry, 'hi')
			# do some quickie greek replacements
			body = re.sub(greekfinder, lambda x: greekwithvowellengths(x.group(2)), body)
			qtemplate = """
			INSERT INTO {d} 
				(entry_name, metrical_entry, id_number, entry_key, pos, translations, entry_body)
				VALUES (%s, %s, %s, %s, %s, %s, %s)"""
			query = qtemplate.format(d=dictdb)
			data = (entryname, metricalentry, idnum, key, pos, translationlist, body)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				print('\tat', idnum, entryname)

			# if idnum == 18069:
			# 	items = [entryname, metricalentry, idnum, type, key, opt, translationlist, body]
			# 	for i in items:
			# 		print(i)

	dbc.commit()
	curs.close()
	del dbc

	return


def mpgreekdictionaryinsert(dictdb, entries, commitcount):
	"""

	work on dictdb entries
	assignable to an mp worker
	insert into db at end

	:param dictdb:
	:param entries:
	:param commitcount:
	:return:
	"""

	dbc = setconnection(config)
	curs = dbc.cursor()

	# places where you can find lang="greek"
	# <foreign>; <orth>; <pron>; <quote>; <gen>; <itype>
	# but there can be a nested tag: you can't convert its contents
	# not clear how much one needs to care: but a search inside a match group could be implemented.

	bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
	posfinder = re.compile(r'<pos.*?>(.*?)</pos>')
	prepfinder = re.compile(r'Prep. with')
	verbfinder = re.compile(r'<tns.*?>(.*?)</tns>')
	# <orth extent="full" lang="greek" opt="n">χύτρ-α</orth>, <gen lang="greek" opt="n">ἡ</gen>,
	nounfindera = re.compile(r'<orth extent=".*?".*?</orth>, <gen.*?>(.*?)</gen>')
	# <orth extent="full" lang="greek" opt="n">βωρεύϲ</orth>, <itype lang="greek" opt="n">εωϲ</itype>, <gen lang="greek" opt="n">ὁ</gen>
	nounfinderb = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?</itype>, <gen.*?>(.*?)</gen>')
	# <orth extent="full" lang="greek" opt="n">βωλο-ειδήϲ</orth>, <itype lang="greek" opt="n">έϲ</itype>,
	twoterminationadjfinder = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?>(.*?)</itype>, <[^g]')
	# <orth extent="full" lang="greek" opt="n">βωμιαῖοϲ</orth>, <itype lang="greek" opt="n">α</itype>, <itype lang="greek" opt="n">ον</itype>,
	threeterminationadjfinder = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?>(.*?)</itype>, <itype .*?>.*?</itype>, <[^g]')

	greekfinder = re.compile(
		'(<(foreign|orth|pron|quote|gen|itype|etym|ref).*?lang="greek".*?>)(.*?)(</(foreign|orth|pron|quote|gen|itype|etym|ref)>)')
	# these arise from nested tags: a more elegant solution would be nice; some other day
	restorea = re.compile(r'<γεν λανγ="γρεεκ" οπτ="ν">(.*?)(</gen>)')
	restoreb = re.compile(r'<προν εχτεντ="φυλλ" λανγ="γρεεκ" οπτ="ν"(.*?)(</pron>)')
	restorec = re.compile(r'<ιτψπε λανγ="γρεεκ" οπτ="ν">(.*?)(</itype>)')

	idnum = 0
	while len(entries) > 0:
		try:
			entry = entries.pop()
		except IndexError:
			entry = ''

		if entry[0:10] != "<entryFree":
			pass
		else:
			segments = re.search(bodyfinder, entry)
			try:
				body = segments.group(3)
			except:
				body = ''
				print('died at', idnum, entry)
			info = segments.group(2)
			parsedinfo = re.search('id="(.*?)"\skey=(".*?")\stype="(.*?)"\sopt="(.*?)"', info)
			try:
				idnum = parsedinfo.group(1)
				key = parsedinfo.group(2)
				etype = parsedinfo.group(3)  # will go unused
				opt = parsedinfo.group(4)  # will go unused
			except:
				# only one greek dictionary entry will throw an exception: n29246
				# print('did not find key at', idnum, entry)
				idnum = 'n29246'
				key = ''
				etype = ''
				opt = ''
			entryname = re.sub(r'"(.*?)"', lambda x: greekwithoutvowellengths(x.group(1)), key.upper())
			entryname = re.sub(r'(\d+)', superscripterone, entryname)
			metrical = re.sub(r'(")(.*?)(")', lambda x: greekwithvowellengths(x.group(2)), key.upper())
			metrical = re.sub(r'(\d+)', superscripterone, metrical)
			metrical = re.sub(r'"', r'', metrical)

			body = re.sub(greekfinder, lsjgreekswapper, body)
			body = re.sub(restorea, r'<gen lang="greek" opt="n">\1\2', body)
			body = re.sub(restoreb, r'<pron extent="full">\1\2', body)
			body = re.sub(restorec, r'<itype lang="greek" opt="n">\1\2', body)

			startofbody = body[:150]
			partsofspeech = set(re.findall(posfinder, startofbody))
			preps = re.findall(prepfinder, startofbody)
			if preps:
				partsofspeech.add('prep.')
			nouns = [n for n in re.findall(nounfindera, startofbody) if n in ['ὁ', 'ἡ', 'τό']]
			nouns += [n for n in re.findall(nounfinderb, startofbody) if n in ['ὁ', 'ἡ', 'τό']]
			if nouns:
				partsofspeech.add('subst.')
			adjs = [a for a in re.findall(twoterminationadjfinder, startofbody) if a in ['έϲ']]
			adjs += [a for a in re.findall(threeterminationadjfinder, startofbody) if a in ['α', 'ά', 'η', 'ή']]
			if adjs:
				partsofspeech.add('adj.')
			verbs = re.findall(verbfinder, startofbody)
			if verbs:
				partsofspeech.add('v.')
			if not partsofspeech and entryname[-1] == 'ω':
				partsofspeech.add('v.')

			pos = ''
			pos += ' ‖ '.join(partsofspeech)
			pos = pos.lower()

			# 'n1000' --> 1000
			idnum = int(re.sub(r'^n', '', idnum))
			translationlist = translationsummary(entry, 'tr')
			stripped = cleanaccentsandvj(entryname)
			qtemplate = """
			INSERT INTO {d} 
				(entry_name, metrical_entry, unaccented_entry, id_number, pos, translations, entry_body)
				VALUES (%s, %s, %s, %s, %s, %s, %s)"""
			query = qtemplate.format(d=dictdb)
			data = (entryname, metrical, stripped, idnum, pos, translationlist, body)

			try:
				curs.execute(query, data)
			except:
				# psycopg2.DataError
				print('failed to insert', entryname)
				print('\t>>',entryname, metrical, stripped, idnum, pos,'<<')

			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				try:
					print('\tat', idnum, entryname)
				except UnicodeEncodeError:
					# UnicodeEncodeError
					print('\tat', idnum)

	dbc.commit()
	curs.close()
	del dbc

	return


def mplemmatainsert(grammardb, entries, islatin, commitcount):
	"""

	work on grammardb entries
	assignable to an mp worker
	insert into db at end

	:param grammardb:
	:param entries:
	:param islatin:
	:param commitcount:
	:return:
	"""
	
	dbc = setconnection(config)
	curs = dbc.cursor()
	
	keywordfinder = re.compile(r'(.*?\t)(\d{1,})(.*?)$')
	greekfinder = re.compile(r'(\t.*?)(\s.*?)(?=(\t|$))')
	invals = "vjσς"
	outvals = "uiϲϲ"

	while len(entries) > 0:
		try:
			entry = entries.pop()
		except IndexError:
			entry = None

		if entry:
			segments = re.search(keywordfinder, entry)
			dictionaryform = segments.group(1)
			if islatin is True:
				dictionaryform = re.sub(r'\t', '', dictionaryform)
			else:
				dictionaryform = re.sub(r'(.*?)\t', lambda x: greekwithoutvowellengths(x.group(1)), dictionaryform.upper())
			dictionaryform = re.sub(r'\d', superscripterzero, dictionaryform)
			dictionaryform = re.sub(r'%', '', dictionaryform)
			otherforms = segments.group(3)
			if islatin is not True:
				otherforms = re.sub(greekfinder, betaconvertandsave, otherforms)
			xref = int(segments.group(2))
			# be careful: the corresponding xref is a str inside a text field

			# clean the derivativeforms: note that this involves a loss of info
			# ζῳωδία           |    49601761 |         ζῳωδίαϲ (fem acc pl) (fem gen sg (attic doric aeolic))  ζῳωδίᾳ (fem dat sg (attic doric aeolic))
			# becomes
			# ζῳωδία           |    49601761 | {ζῳωδίαϲ,ζῳωδίᾳ}
			# but nothing in HipparchiaServer currently needs anything other than the list of extant forms

			formlist = [f for f in otherforms.split('\t') if f]
			formlist = [f.split(' ')[0] for f in formlist]
			formlist = [re.sub(r'\'', '', f) for f in formlist]
			formlist = [f.lower() for f in formlist]
			formlist = [f.translate(str.maketrans(invals, outvals)) for f in formlist]
			formlist = list(set(formlist))

			query = 'INSERT INTO {g} (dictionary_entry, xref_number, derivative_forms) VALUES (%s, %s, %s)'.format(g=grammardb)
			data = (dictionaryform, xref, formlist)
			curs.execute(query, data)
			commitcount.increment()
			if commitcount.value % 5000 == 0:
				dbc.commit()
				print('\tat', dictionaryform)
		
	dbc.commit()
	curs.close()
	del dbc
	
	return


def mpanalysisinsert(grammardb, items, islatin, commitcount):
	"""

	work on grammardb entries
	assignable to an mp worker
	insert into db at end

	an analysis line looks like this:
		!a/sdwn {32430564 9 e)/sdwn,ei)sdi/dwmi flow into       aor ind act 3rd pl (epic doric aeolic)}{32430564 9 e)/sdwn,ei)sdi/dwmi  flow into       aor ind act 1st sg (epic)}

		beluasque	{8991758 9 be_lua_s,belua	a beast	fem acc pl}{9006674 9 be_lua_s,beluus	 	fem acc pl}

		word(TAB){analysis 1}{analysis 2}{...}

	each inset analysis is:
		{xrefnumber digit ancientform1,ancientform2(TAB)translation(TAB)parsinginfo}

	:param grammardb:
	:param items:
	:param islatin:
	:param commitcount:
	:return:
	"""

	dbc = setconnection(config)
	curs = dbc.cursor()

	# most end with '}', but some end with a bracketed number or numbers
	# w)ph/sasqai	{49798258 9 a)ph/sasqai,a)po/-h(/domai	swād-	aor inf mid (ionic)}[12711488]
	# a)mfiperih|w/rhntai	{3398393 9 a)mfiperi+h|w/rhntai,a)mfi/,peri/-ai)wre/w	lift up	perf ind mp 3rd pl}[6238652][88377399]

	# hunting down the bracketrefs will get you to things like: ἀπό and ἀμφί
	# that is, these mark words that have a prefix and THAT information can be used as part of the solution to the comma conundrum
	# namely, ὑπό,ἀνά,ἀπό-νέω needs to be recomposed by attending to the commas, but the commas are not only associated with prefixes
	# cf. ἠχήϲαϲα: <possibility_1>ἠχθόμαν, ἄχθομαι<xref_value>19480186</xref_value>

	# the number of items in bracketrefs corresponds to the number of prefix checks you will need to make to recompose the verb

	bracketrefs = re.compile(r'\[\d\d+\]')
	formfinder = re.compile(r'(.*?\t){(.*?)}$')
	analysisfinder = re.compile(r'(\d+)\s(\d)\s(.*?)\t(.*?)\t(.*?$)')

	qtemplate = 'INSERT INTO {gdb} (observed_form, xrefs, prefixrefs, possible_dictionary_forms) VALUES (%s, %s, %s, %s)'

	ptemplate = list()
	ptemplate.append('<possibility_{p}>{wd}')
	ptemplate.append('<xref_value>{xrv}</xref_value>')
	ptemplate.append('<xref_kind>{xrk}</xref_kind>')
	ptemplate.append('<transl>{t}</transl>')
	ptemplate.append('<analysis>{a}</analysis>')
	ptemplate.append('</possibility_{p}>\n')
	ptemplate = ''.join(ptemplate)

	while items:
		try:
			entry = items.pop()
		except IndexError:
			entry = None

		if entry:
			bracketed = ''
			if re.search(bracketrefs,entry) is not None:
				bracketed = re.findall(bracketrefs, entry)
				bracketed = list(set(bracketed))
				bracketed = ', '.join(bracketed)
				bracketed = re.sub(r'[\[\]]', '', bracketed)
				entry = re.sub(bracketrefs, '', entry)
			segments = re.search(formfinder, entry)
			try:
				observedform = segments[1]
			except TypeError:
				print('\tfailed to find the observed form for', entry)
				observedform = None
			if observedform:
				if islatin is True:
					observedform = re.sub(r'[\t\s]', '', observedform)
					observedform = re.sub(r'v', 'u', observedform)
					observedform = latinvowellengths(observedform)
				else:
					observedform = re.sub(r'(.*?)\t', lambda x: greekwithoutvowellengths(x[1]), observedform.upper())
				analysislist = segments.group(2).split('}{')
				# analysislist πολυγώνοιϲ ['92933543 9 polu/gwnon\tpolygonal\tneut dat pl', '92933543 9 polu/gwnos\tpolygonal\tmasc/fem/neut dat pl']
				xrefs = set([str(x.split(' ')[0]) for x in analysislist])
				xrefs = (', ').join(xrefs)
				# pass an item through analysisfinder and you will get this:
				# i[1] = '92933543'
				# i[2] = '9'
				# i[3] = 'polu/gwnon'
				# i[4] = 'polygonal'
				# i[5] = 'neut dat pl'

				possibilities = list()
				# example:
				# <possibility_1>ἠχήϲαϲα, ἠχέω<xref_value>50902522</xref_value><xref_kind>9</xref_kind><transl>sound</transl><analysis>aor part act fem nom/voc sg (attic epic ionic)</analysis></possibility_1>

				number = 0
				for found in analysislist:
					elements = re.search(analysisfinder, found)
					number += 1
					if islatin is True:
						wd = latinvowellengths(elements.group(3))
						wd = re.sub(r'#(\d)', superscripterone, wd)
					else:
						wd = greekwithoutvowellengths(elements.group(3).upper())
						wd = re.sub(r'\d', superscripterzero, wd)
					wd = re.sub(r',', r', ', wd)
					possibilities.append(ptemplate.format(p=number, wd=wd, xrv=elements.group(1), xrk=elements.group(2), t=elements.group(4), a=elements.group(5)))

				ptext = ''.join(possibilities)
				query = qtemplate.format(gdb=grammardb)
				data = (observedform, xrefs, bracketed, ptext)
				# print(entry,'\n',observedform,xrefs,bracketed,'\n\t',possibilities)
				curs.execute(query, data)
				commitcount.increment()
				if commitcount.value % 2500 == 0:
					dbc.commit()

	dbc.commit()
	curs.close()
	del dbc

	return

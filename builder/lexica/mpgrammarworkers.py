# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from psycopg2.extras import execute_values as insertlistofvaluetuples

from builder.dbinteraction.connection import setconnection
from builder.parsers.lexica import greekwithoutvowellengths, betaconvertandsave, latinvowellengths
from builder.parsers.swappers import superscripterzero, superscripterone


def mplemmatainsert(grammardb, entries, islatin, dbconnection):
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
	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	query = 'INSERT INTO {g} (dictionary_entry, xref_number, derivative_forms) VALUES %s'.format(g=grammardb)

	keywordfinder = re.compile(r'(.*?\t)(\d{1,})(.*?)$')
	greekfinder = re.compile(r'(\t.*?)(\s.*?)(?=(\t|$))')
	invals = "vjσς"
	outvals = "uiϲϲ"

	bundlesize = 1000

	while len(entries) > 0:
		bundelofrawentries = list()
		for e in range(bundlesize):
			try:
				bundelofrawentries.append(entries.pop())
			except IndexError:
				pass

		bundelofcookedentries = list()
		for entry in bundelofrawentries:
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

			# clean the derivativeforms: note that this involves a LOSS OF INFORMATION
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

			bundelofcookedentries.append(tuple([dictionaryform, xref, formlist]))

		insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

	return


def mpanalysisinsert(grammardb, entries, islatin, dbconnection):
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
	:param entries:
	:param islatin:
	:param commitcount:
	:return:
	"""
	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

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

	qtemplate = 'INSERT INTO {gdb} (observed_form, xrefs, prefixrefs, possible_dictionary_forms) VALUES %s'
	query = qtemplate.format(gdb=grammardb)

	ptemplate = list()
	ptemplate.append('<possibility_{p}>{wd}')
	ptemplate.append('<xref_value>{xrv}</xref_value>')
	ptemplate.append('<xref_kind>{xrk}</xref_kind>')
	ptemplate.append('<transl>{t}</transl>')
	ptemplate.append('<analysis>{a}</analysis>')
	ptemplate.append('</possibility_{p}>\n')
	ptemplate = str().join(ptemplate)

	bundlesize = 1000

	while entries:
		bundelofrawentries = list()
		for e in range(bundlesize):
			try:
				bundelofrawentries.append(entries.pop())
			except IndexError:
				pass

		bundelofcookedentries = list()
		for entry in bundelofrawentries:
			bracketed = ''
			if re.search(bracketrefs, entry) is not None:
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
					observedform = re.sub(r'[\t\s]', str(), observedform)
					observedform = re.sub(r'v', 'u', observedform)
					observedform = latinvowellengths(observedform)
				else:
					observedform = re.sub(r'(.*?)\t', lambda x: greekwithoutvowellengths(x[1]), observedform.upper())
				analysislist = segments.group(2).split('}{')
				# analysislist πολυγώνοιϲ ['92933543 9 polu/gwnon\tpolygonal\tneut dat pl', '92933543 9 polu/gwnos\tpolygonal\tmasc/fem/neut dat pl']

				xrefs = set([str(x.split(' ')[0]) for x in analysislist])
				xrefs = ', '.join(xrefs)
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

				ptext = str().join(possibilities)

				bundelofcookedentries.append(tuple([observedform, xrefs, bracketed, ptext]))

		insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

	return

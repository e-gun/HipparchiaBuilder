# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from psycopg2.extras import execute_values as insertlistofvaluetuples

from builder.dbinteraction.connection import setconnection
from builder.parsers.lexicalparsing import betaconvertandsave, greekwithoutvowellengths, latinvowellengths
from builder.parsers.swappers import superscripterone, superscripterzero


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

	possible_dictionary_forms is going to be JSON:
		{'NUMBER': {
				'headword': 'WORD',
				'scansion': 'SCAN',
				'xref_value': 'VAL',
				'xref_kind': 'KIND',
				'transl': 'TRANS',
				'analysis': 'ANAL'
			},
		'NUMBER': {
				'headword': 'WORD',
				'scansion': 'SCAN',
				'xref_value': 'VAL',
				'xref_kind': 'KIND',
				'transl': 'TRANS',
				'analysis': 'ANAL'
			},
		...}

	note that scansion is meaningless for the greek words

	 observed_form |   xrefs   | prefixrefs |                                                                      possible_dictionary_forms
	 βάδην         | 18068282 |            | {"1": {"scansion": "", "headword": "\u03b2\u03ac\u03b4\u03b7\u03bd", "xref_value": "18068282", "xref_kind": "9", "transl": "step by step", "analysis": "indeclform (adverb)"}}
	 βάδιζ'        | 18070850 |            | {"1": {"scansion": "\u03b2\u03ac\u03b4\u03b9\u03b6\u03b5", "headword": "\u03b2\u03b1\u03b4\u03af\u03b6\u03c9", "xref_value": "18070850", "xref_kind": "9", "transl": "walk", "analysis": "pres imperat act 2nd sg"}, "2": {"scansion": "\u03b2\u03ac\u03b4\u03b9\u03b6\u03b5", "headword": "\u03b2\u03b1\u03b4\u03af\u03b6\u03c9", "xref_value": "18070850", "xref_kind": "9", "transl": "walk", "analysis": "imperf ind act 3rd sg (homeric ionic)"}}
	 βάδιζε        | 18070850 |            | {"1": {"scansion": "", "headword": "\u03b2\u03b1\u03b4\u03af\u03b6\u03c9", "xref_value": "18070850", "xref_kind": "9", "transl": "walk", "analysis": "pres imperat act 2nd sg"}, "2": {"scansion": "", "headword": "\u03b2\u03b1\u03b4\u03af\u03b6\u03c9", "xref_value": "18070850", "xref_kind": "9", "transl": "walk", "analysis": "imperf ind act 3rd sg (homeric ionic)"}}

	 cubabunt      | 19418734 |            | {"1": {"scansion": "cuba\u0304bunt", "headword": "cubo", "xref_value": "19418734", "xref_kind": "9", "transl": " ", "analysis": "fut ind act 3rd pl"}}
	 cubandi       | 19418734 |            | {"1": {"scansion": "cubandi\u0304", "headword": "cubo", "xref_value": "19418734", "xref_kind": "9", "transl": " ", "analysis": "gerundive masc nom/voc pl"}, "2": {"scansion": "cubandi\u0304", "headword": "cubo", "xref_value": "19418734", "xref_kind": "9", "transl": " ", "analysis": "gerundive neut gen sg"}, "3": {"scansion": "cubandi\u0304", "headword": "cubo", "xref_value": "19418734", "xref_kind": "9", "transl": " ", "analysis": "gerundive masc gen sg"}}

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

	qtemplate = 'INSERT INTO {gdb} (observed_form, xrefs, prefixrefs, possible_dictionary_forms, related_headwords) VALUES %s'
	query = qtemplate.format(gdb=grammardb)

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
			prefixrefs = str()
			if re.search(bracketrefs, entry) is not None:
				prefixrefs = re.findall(bracketrefs, entry)
				prefixrefs = list(set(prefixrefs))
				prefixrefs = ', '.join(prefixrefs)
				prefixrefs = re.sub(r'[\[\]]', str(), prefixrefs)
				entry = re.sub(bracketrefs, str(), entry)
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
				pdict = dict()
				hw = set()
				for found in analysislist:
					adict = dict()
					elements = re.search(analysisfinder, found)
					number += 1
					if islatin is True:
						wd = latinvowellengths(elements.group(3))
						wd = re.sub(r'#(\d)', superscripterone, wd)
					else:
						wd = greekwithoutvowellengths(elements.group(3).upper())
						wd = re.sub(r'\d', superscripterzero, wd)
					sp = wd.split(',')
					if len(sp) > 1:
						adict['scansion'] = sp[0]
					else:
						adict['scansion'] = str()

					adict['headword'] = sp[-1]
					adict['xref_value'] = elements.group(1)
					adict['xref_kind'] = elements.group(2)
					adict['transl'] = elements.group(4)
					adict['analysis'] = elements.group(5)
					pdict[number] = adict
					hw.add(sp[-1])
					# note that this would be a moment where HServer's _getgreekbaseform(), etc could be used
				j = json.dumps(pdict)
				h = ' '.join(hw)
				bundelofcookedentries.append(tuple([observedform, xrefs, prefixrefs, j, h]))

		insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

	return

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

try:
	regexmatch = re.Match
except AttributeError:
	# python < 3.7
	regexmatch = object()


def htmltounicode(htmltext: str, brevefinder=None, macrfinder=None) -> str:
	"""

	turn &abreve; into ă, usw.

	:param htmltext:
	:return:
	"""
	shorts = {
		'a': 'ă',
		'e': 'ĕ',
		'i': 'ĭ',
		'o': 'ŏ',
		'u': 'ŭ',
		'A': 'Ă',
		'E': 'Ĕ',
		'I': 'Ĭ',
		'O': 'Ŏ',
		'U': 'Ŭ'
	}

	longs = {
		'a': 'ā',
		'e': 'ē',
		'i': 'ī',
		'o': 'ō',
		'u': 'ū',
		'A': 'Ā',
		'E': 'Ē',
		'I': 'Ī',
		'O': 'Ō',
		'U': 'Ū'
	}

	if not brevefinder or not macrfinder:
		brevefinder = re.compile(r'&([aeiouAEIOU])breve;')
		macrfinder = re.compile(r'&([aeiouAEIOU])macr;')

	shortswap = lambda x: shorts[x.group(1)]
	longswap = lambda x: longs[x.group(1)]

	swapped = re.sub(brevefinder, shortswap, htmltext)
	swapped = re.sub(macrfinder, longswap, swapped)
	return swapped


# x = """sh;</sense><sense id="n47174.55" n="(d)" level="5"> <hi rend="ital">Sing.</hi>: <orth extent="full" lang="la">s&ubreve;a</orth>, suae. <gen>f.</gen>, <hi rend="ital">a sweetheart</hi>, <hi rend="ital">mistress</hi> (rare): illam suam suas res sibi habere jussit. <bibl n="urn:cts:latinLit:phi0474.phi035.perseus-lat1:2:28"><author>"""
# print(htmltounicode(x))

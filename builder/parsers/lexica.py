# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from string import punctuation

from builder.parsers.betacodeandunicodeinterconversion import replacegreekbetacode


try:
	regexmatch = re.Match
except AttributeError:
	# python < 3.7
	regexmatch = object()


#
# lexica parser helpers
#

def greekwithoutvowellengths(betagreek: str) -> str:
	"""
	quick vowel len stripper that then sends you to greek conversion

	:param betagreek:
	:return:
	"""

	betagreek = re.sub(r'[\^_]', r'', betagreek)
	unigreek = replacegreekbetacode(betagreek)
	
	return unigreek


def greekwithvowellengths(ttc):
	"""
	the non-documented long-and-short codes
	this can/will confuse lexical lookups from greek passages
	use the combining long/short so that you stand a chance of doing both accents and lengths
	:param ttc: [ttc <class '_sre.SRE_Match'>]
	:return:
	"""

	# ttc = match.group(2)

	if re.search(r'[a-z]', ttc) is not None:
		# this will keep things that have already been turned into greek from turning into upper case greek
		ttc = ttc.upper()
	else:
		# we are already greek: still, while we are here...
		# ttc = re.sub(r'\_', u'/\u0304', ttc)
		# ttc = re.sub(r'\^', u'/\u0306', ttc)
		pass
	
	ttc = re.sub(r'\^\/', u'/\u0306', ttc)
	ttc = re.sub(r'\_\/', u'/\u0304', ttc)
	ttc = re.sub(r'([AIU])\^', r'\1'+u'\u0306',ttc)
	ttc = re.sub(r'([AIU])\_', r'\1' + u'\u0304', ttc)

	ttc = replacegreekbetacode(ttc)
	
	return ttc


def latinvowellengths(texttoclean: str) -> str:
	"""
	now you have a new problem: matching vowel lengths when the TXT files do not have that information
	only send items this way whose transformation will prevent successful searches
	using the combining forms
	:param texttoclean:
	:return:
	"""
	textualmarkuptuples = list()

	betacodetuples = (
		(r'a_', u'a\u0304'),
		(r'a\^', u'a\u0306'),
		(r'e_', u'e\u0304'),
		(r'e\^', u'e\u0306'),
		(r'i_', u'i\u0304'),
		(r'i\^', u'i\u0306'),
		(r'o_', u'o\u0304'),
		(r'o\^', u'o\u0306'),
		(r'u_', u'u\u0304'),
		(r'u\^', u'u\u0306'),
		(r'y\_', u'y\u0304'),
		(r'y\^', u'y\u0306')
	)
	for i in range(0, len(betacodetuples)):
		textualmarkuptuples.append((betacodetuples[i][0], betacodetuples[i][1]))

	for reg in textualmarkuptuples:
		texttoclean = re.sub(reg[0], reg[1], texttoclean)

	return texttoclean


def betaconvertandsave(convertme: regexmatch) -> str:
	betagreek = convertme.group(1)
	notgreek = convertme.group(2)
	unigreek = replacegreekbetacode(betagreek.upper())+notgreek
	return unigreek


def lsjgreekswapper(match: regexmatch) -> str:
	"""
	greekfinder in mpgreekdictionaryinsert() will find 5 things:
		match1 + match 3 + match 4 reassembles the markup block
		match 3 is likely greek, but you ought to make sure that there are not more tags inside of it
		ntl, there are a very small number of affected edge cases (5): <num>'A</num>;  <hi rend="underline">SKLA</hi>; ...
	:param match:
	:return:
	"""
	
	# markup = re.compile(r'(<.*?>)(.*?)(</.*?>)')
	
	target = match.group(3)
	
	# if re.search(markup,target) is not None:
	# 	toswap = re.search(markup,target).group(2)
	# 	substitute = re.sub(markup, gr2betaconverter, toswap.upper())
	# 	substitute = re.search(markup,target).group(1) + substitute + re.search(markup,target).group(3)
	# 	print('xs',substitute)
	# else:
	# 	substitute = replacegreekbetacode(target.upper())
	
	substitute = greekwithvowellengths(target.upper())
	substitute = match.group(1) + substitute + match.group(4)
	
	return substitute


def translationsummary(fullentry: str, translationlabel: str) -> str:
	"""

	sample:
		<tr opt="n">commander of an army, general</tr>

	adapted from hserver

	return a list of all senses to be found in an entry

	if re.search(r'[a-z]', seekingentry):
		usedictionary = 'latin'
		translationlabel = 'hi'
	else:
		usedictionary = 'greek'
		translationlabel = 'tr'

	:param fullentry:
	:param translationlabel:
	:return:
	"""

	fingerprint = re.compile(r'<{label}.*?>(.*?)</{label}>'.format(label=translationlabel))
	tr = re.findall(fingerprint, fullentry)
	exclude = ['ab', 'de', 'ex', 'ut', 'nihil', 'quam', 'quid']

	try:
		tr = [t for t in tr if '.' not in t]
		tr = [t for t in tr if t not in exclude]
	except TypeError:
		# argument of type 'NoneType' is not iterable
		tr = list()

	# so 'go' and 'go,' are not both on the list
	depunct = '[{p}]$'.format(p=re.escape(punctuation))
	tr = [re.sub(depunct, '', t) for t in tr]
	tr = [t[0].lower() + t[1:] for t in tr if len(t) > 1]

	# interested in keeping the first two in order so that we can privilege the primary senses
	# the fixed translations can be fed to the morphology summary translation
	# if you just clean via set() you lose the order...
	firsttwo = tr[:2]
	alltrans = list(set(tr))
	alltrans.sort()
	translationlist = firsttwo + [t for t in alltrans if t not in firsttwo]

	translations = ' ‖ '.join(translationlist)

	return translations

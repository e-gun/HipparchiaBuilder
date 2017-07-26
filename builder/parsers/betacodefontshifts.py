# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import configparser
from builder.parsers.betacodeandunicodeinterconversion import parsegreekinsidelatin

config = configparser.ConfigParser()
config.read('config.ini')

if config['buildoptions']['warnings'] == 'y':
	warnings = True
else:
	warnings = False


def replacegreekmarkup(texttoclean):
	"""
	turn $NN into markup
	:param texttoclean:
	:return:
	"""

	# notice 'unlatin + unsmall' in:
	# █⑧⓪ *(ISTORIW=N [&10fr. 93 FHG I 215]$10 [2LE/GEI PROSISTORW=N]2 E)PI/SHMON A)/NDRA GEGONE/NAI TO\N @1
	# just make this 'unlatin' since 'unsmall' happens automatically after &10
	unun = re.compile(r'&(\d{1,2})([^█]*?)\$(\d{1,2})')

	texttoclean = re.sub(unun, lambda x: removeshiftsymmetry(x.group(1), x.group(2), x.group(3)), texttoclean)

	dollars = re.compile(r'\$(\d{1,2})([^\&█]*?)(\$\d{0,1})')
	texttoclean = re.sub(dollars, lambda x: dollarssubstitutes(int(x.group(1)), x.group(2)), texttoclean)

	straydollars = re.compile(r'\$(\d{1,2})(.*?)(\s{0,1}█)')
	texttoclean = re.sub(straydollars, lambda x: dollarssubstitutes(int(x.group(1)), x.group(2), extra=x.group(3)), texttoclean)

	return texttoclean


def latinfontlinemarkupprober(texttoclean):
	"""

	take line-like segments of the text

	then hand them off to another function to check them for '&' escapes

	if you find them, do the substitutions

	:param txt:
	:return:
	"""
	grabaline = re.compile(r'(.*?)(\s{0,1}█)')
	texttoclean = re.sub(grabaline, latinfontlinemarkupparser, texttoclean)

	return texttoclean


def latinfontlinemarkupparser(match):
	"""

	check a quasi-line for '&' escapes

	scholia are a great place to look for the hardest cases

	remaining difficulties
		(will get "SyntaxError: (unicode error) 'unicodeescape' codec..." if you put some of them in here
		[TLG0085] [ '"3' vel sim  as something that counts as 'off' and requires 'greek on']
		[TLG5014] ['%10' as something that counts as 'off' and requires 'greek on']

	:param match:
	:return:
	"""

	m = match.group(1)
	tail = match.group(2)

	ands = m.split('&')
	if len(ands) == 1:
		# the line does not actually have any escapes: we are done
		return match.group(0)

	newline = [ands[0]]
	nodollar = re.compile(r'^(\d{0,})(.*?)$')
	yesdollar = re.compile(r'^(\d{0,})(.*?)(\$\d{0,2})(.*?)$')
	dollars = re.compile(r'\$')
	alreadyshifted = re.compile(r'^(\d{0,})([^\$]*?)(<hmu_fontshift_greek.*?>)')

	for a in ands[1:]:
		if re.search(alreadyshifted, a):
			# do this before checking nodollar
			newand = re.sub(alreadyshifted, lambda x: andsubstitutes(x.group(1), x.group(2), x.group(3)), a)
		elif not re.search(dollars, a):
			newand = re.sub(nodollar, lambda x: andsubstitutes(x.group(1), x.group(2), ''), a)
		else:
			# note that we are killing off whatever special thing happens with the '$' because of (\$\d{0,2})
			# see Aeschylus, Fragmenta for '█⑨⑥ &10❨Dionysos tritt auf﹕❩$8'
			# it is not clear what we are supposed to do with a trailing '8' like that...: 'greek vertical'
			# notice 'unlatin + unsmall' in:
			# █⑧⓪ *(ISTORIW=N [&10fr. 93 FHG I 215]$10 [2LE/GEI PROSISTORW=N]2 E)PI/SHMON A)/NDRA GEGONE/NAI TO\N @1
			newand = re.sub(yesdollar, lambda x: andsubstitutes(x.group(1), x.group(2), x.group(4)), a)
		newline.append(newand)

	newline = ''.join(newline)

	returnline = '{n}{t}'.format(n=newline, t=tail)

	return returnline


def latinauthorlinemarkupprober(texttoclean, grabber=None):
	"""

	a steamlined version of the greek author equivalent [sorry, DRY fetishists...]

	take line-like segments of the text: only works with LAT authors

	then hand them off to another function to check them for '&' escapes

	if you find them, do the substitutions

	:param txt:
	:return:
	"""

	if not grabber:
		grabaline = re.compile(r'(.*?)(\s{0,1}█)')
	else:
		grabaline = grabber
	texttoclean = re.sub(grabaline, latinauthordollarshiftparser, texttoclean)
	insetgreek = re.compile(r'<hmu_fontshift_greek_.*?>(.*?)</hmu_fontshift_greek_.*?>')
	texttoclean = re.sub(insetgreek, parsegreekinsidelatin, texttoclean)
	texttoclean = re.sub(grabaline, latinauthordollarshiftparser, texttoclean)
	texttoclean = re.sub(grabaline, latinauthorandshiftparser, texttoclean)

	return texttoclean


def latinauthordollarshiftparser(match):
	"""

	check a quasi-line for '$' escapes

	gellius is a good test case:
		procul dubio $A)KW/LUTOS&, $A)NANA/GKASTOS&, $A)PARAPO/DISTOS&, $E)LEU/-

	:param match:
	:return:
	"""

	m = match.group(1)
	tail = match.group(2)

	dollars = m.split('$')
	if len(dollars) == 1:
		# the line does not actually have any escapes: we are done
		return match.group(0)

	newline = [dollars[0]]
	whichdollar = re.compile(r'^(\d{0,})(.*?)(&|$)')

	appendix = [re.sub(whichdollar, lambda x: dollarssubstitutes(x.group(1), x.group(2), ''), d) for d in dollars[1:]]

	newline = ''.join(newline+appendix)

	returnline = '{n}{t}'.format(n=newline, t=tail)

	return returnline


def latinauthorandshiftparser(match):
	"""

	check a quasi-line for '&' escapes

	only appropriate for latin authors where you can find '&7...&', etc.

	:param match:
	:return:
	"""

	m = match.group(1)
	tail = match.group(2)

	ands = m.split('&')
	if len(ands) == 1:
		# the line does not actually have any escapes: we are done
		return match.group(0)

	newline = [ands[0]]
	whichand = re.compile(r'^(\d{0,})(.*?)$')

	appendix = [re.sub(whichand, lambda x: andsubstitutes(x.group(1), x.group(2), ''), a) for a in ands[1:]]

	newline = ''.join(newline+appendix)

	returnline = '{n}{t}'.format(n=newline, t=tail)

	return returnline


def dollarssubstitutes(val, core, extra=''):
	"""
	turn $NN...$ into unicode
	:param match:
	:return:
	"""

	try:
		val = int(val)
	except:
		val = 0

	substitutions = {
		70: [r'<hmu_fontshift_greek_uncial>', r'</hmu_fontshift_greek_uncial>'],
		53: [r'<hmu_fontshift_greek_hebrew>', r'</hmu_fontshift_greek_hebrew>'],
		52: [r'<hmu_fontshift_greek_arabic>', r'</hmu_fontshift_greek_arabic>'],
		51: [r'<hmu_fontshift_greek_demotic>', r'</hmu_fontshift_greek_demotic>'],
		50: [r'<hmu_fontshift_greek_coptic>', r'</hmu_fontshift_greek_coptic>'],
		40: [r'<hmu_fontshift_greek_extralarge>', r'</hmu_fontshift_greek_extralarge>'],
		30: [r'<hmu_fontshift_greek_extrasmall>', r'</hmu_fontshift_greek_extrasmall>'],
		20: [r'<hmu_fontshift_greek_largerthannormal>', r'</hmu_fontshift_greek_largerthannormal>'],
		18: [r'<hmu_fontshift_greek_smallerthannormal>', r'</hmu_fontshift_greek_smallerthannormal>'],  # + 'vertical', but deprecated
		16: [r'<hmu_fontshift_greek_smallerthannormalsuperscriptbold>', r'</hmu_fontshift_greek_smallerthannormalsuperscriptbold>'],
		15: [r'<hmu_fontshift_greek_smallerthannormalsubscript>', r'</hmu_fontshift_greek_smallerthannormalsubscript>'],
		14: [r'<hmu_fontshift_greek_smallerthannormalsuperscript>', r'</hmu_fontshift_greek_smallerthannormalsuperscript>'],
		13: [r'<hmu_fontshift_greek_smallerthannormalitalic>', r'</hmu_fontshift_greek_smallerthannormalitalic>'],
		11: [r'<hmu_fontshift_greek_smallerthannormalbold>', r'</hmu_fontshift_greek_smallerthannormalbold>'],
		10: [r'<hmu_fontshift_greek_smallerthannormal>', r'</hmu_fontshift_greek_smallerthannormal>'],
		9: [r'<hmu_fontshift_greek_regular>', r'</hmu_fontshift_greek_regular>'],
		8: [r'<hmu_fontshift_greek_vertical>', r'</hmu_fontshift_greek_vertical>'],
		6: [r'<hmu_fontshift_greek_superscriptbold>', r'</hmu_fontshift_greek_superscriptbold>'],
		5: [r'<hmu_fontshift_greek_subscript>', r'</hmu_fontshift_greek_subscript>'],
		4: [r'<hmu_fontshift_greek_superscript>', r'</hmu_fontshift_greek_superscript>'],
		3: [r'<hmu_fontshift_greek_italic>', r'</hmu_fontshift_greek_italic>'],
		2: [r'<hmu_fontshift_greek_bolditalic>', r'</hmu_fontshift_greek_bolditalic>'],
		1: [r'<hmu_fontshift_greek_bold>', r'</hmu_fontshift_greek_bold>'],
		0: [r'<hmu_fontshift_greek_normal>', r'</hmu_fontshift_greek_normal>']
	}

	try:
		substitute = substitutions[val][0] + core + substitutions[val][1] + extra
	except KeyError:
		substitute = '<hmu_unhandled_greek_font_shift betacodeval="{v}" />{c}{e}'.format(v=val, c=core, e=extra)
		if warnings:
			print('\t',substitute)

	return substitute


def andsubstitutes(groupone, grouptwo, groupthree):
	"""
	turn &NN...& into unicode
	:param match:
	:return:
	"""

	try:
		val = int(groupone)
	except:
		val = 0

	core = grouptwo

	groupthree = re.sub(r'\$','', groupthree)

	substitutions = {
		91: [r'<hmu_fontshift_latin_undocumented_font_shift_AND91>',r'</hmu_fontshift_latin_undocumented_font_shift_AND91>'],
		90: [r'<hmu_fontshift_latin_undocumented_font_shift_AND90>', r'</hmu_fontshift_latin_undocumented_font_shift_AND90>'],
		82: [r'<hmu_fontshift_latin_undocumented_font_shift_AND82>', r'</hmu_fontshift_latin_undocumented_font_shift_AND82>'],
		81: [r'<hmu_fontshift_latin_undocumented_font_shift_AND81>', r'</hmu_fontshift_latin_undocumented_font_shift_AND81>'],
		20: [r'<hmu_fontshift_latin_largerthannormal>',r'</hmu_fontshift_latin_largerthannormal>'],
		14: [r'<hmu_fontshift_latin_smallerthannormalsuperscript>',r'</hmu_fontshift_latin_smallerthannormalsuperscript>'],
		13: [r'<hmu_fontshift_latin_smallerthannormalitalic>', r'</hmu_fontshift_latin_smallerthannormalitalic>'],
		10: [r'<hmu_fontshift_latin_smallerthannormal>', r'</hmu_fontshift_latin_smallerthannormal>'],
		9: [r'<hmu_fontshift_latin_normal>', r'</hmu_fontshift_latin_normal>'],
		8: [r'<hmu_fontshift_latin_smallcapitalsitalic>', r'</hmu_fontshift_latin_smallcapitalsitalic>'],
		7: [r'<hmu_fontshift_latin_smallcapitals>', r'</hmu_fontshift_latin_smallcapitals>'],
		6: [r'<hmu_fontshift_latin_romannumerals>', r'</hmu_fontshift_latin_romannumerals>'],
		5: [r'<hmu_fontshift_latin_subscript>', r'</hmu_fontshift_latin_subscript>'],
		4: [r'<hmu_fontshift_latin_superscript>', r'</hmu_fontshift_latin_superscript>'],
		3: [r'<hmu_fontshift_latin_italic>', r'</hmu_fontshift_latin_italic>'],
		2: [r'<hmu_fontshift_latin_bolditalic>', r'</hmu_fontshift_latin_bolditalic>'],
		1: [r'<hmu_fontshift_latin_bold>', r'</hmu_fontshift_latin_bold>'],
		0: [r'<hmu_fontshift_latin_normal>', r'</hmu_fontshift_latin_normal>'],
	}

	try:
		substitute = substitutions[val][0] + core + substitutions[val][1] + groupthree
	except KeyError:
		substitute = '<hmu_unhandled_greek_font_shift betacodeval="{v}" />{c}'.format(v=val, c=core)
		if warnings:
			print('\t',substitute)

	return substitute


def removeshiftsymmetry(groupone, grouptwo, groupthree):
	"""

	notice that we are requesting 'unlatin + unsmall' in:

	*(ISTORIW=N [&10fr. 93 FHG I 215]$10 [2LE/GEI PROSISTORW=N]2

	turn this into '&10... $'

	otherwise you will get 'small latin span' + 'small greek span'

	:param groupone:
	:param grouptwo:
	:param groupthree:
	:return:
	"""

	value = '&' + groupone + grouptwo + '$'

	if groupone != groupthree:
		value += groupthree

	return value


def hmufontshiftsintospans(texttoclean, language):
	"""

	turn '<hmu_fontshift_latin_italic>b </hmu_fontshift_latin_italic>'

	into '<span class="latin italic">b </span>'

	:param texttoclean:
	:return:
	"""

	shiftfinder = re.compile(r'<hmu_fontshift_(.*?)_(.*?)>')
	shiftcleaner = re.compile(r'</hmu_fontshift_.*?>')

	texttoclean = re.sub(shiftfinder, lambda x: matchskipper(x.group(1), x.group(2), language), texttoclean)
	texttoclean = re.sub(shiftcleaner, r'</span>', texttoclean)

	return texttoclean


def latinhmufontshiftsintospans(texttoclean):
	"""

	needed just so you can pass language to hmufontshiftsintospans

	:param texttoclean:
	:return:
	"""

	return hmufontshiftsintospans(texttoclean, 'latin')


def greekhmufontshiftsintospans(texttoclean):
	"""

	needed just so you can pass language to hmufontshiftsintospans

	:param texttoclean:
	:return:
	"""


	return hmufontshiftsintospans(texttoclean, 'greek')


def matchskipper(groupone, grouptwo, language):
	"""

	r'<span class="\1 \2">'

	or

	r'<span class="\2">'

	skip a matchgroup if it matches language

	this is useful because "latin normal" in a latin author can lead to
	a color shift, vel sim. when you really don't need to flag 'latinity' in this
	context

	:param match:
	:param language:
	:return:
	"""

	if groupone != language:
		spanner = '<span class="{a} {b}">'.format(a=groupone, b=grouptwo)
	else:
		spanner = '<span class="{b}">'.format(a=groupone, b=grouptwo)

	return spanner
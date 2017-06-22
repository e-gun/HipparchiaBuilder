# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import configparser

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
	dollars = re.compile(r'\$(\d{1,2})(.*?)(\$\d{0,1})')
	texttoclean = re.sub(dollars, dollarssubstitutes, texttoclean)

	# these strays are rough
	#texttoclean = re.sub(r'\$(.*?)\$', '<hmu_shift_greek_font betacodeval="regular">\1</hmu_shift_greek_font>', texttoclean)

	return texttoclean


def replacelatinmarkup(texttoclean):
	"""
	turn &NN into markup
	:param texttoclean:
	:return:
	"""
	ands = re.compile(r'&(\d{1,2})(.*?)(&\d{0,1})')
	texttoclean = re.sub(ands, andsubstitutes, texttoclean)

	#texttoclean = re.sub(r'\&(.*?)\&', r'<hmu_shift_latin_font betacodeval="regular">\1</hmu_shift_latin_font>', texttoclean)

	anddollars = re.compile(r'&(\d{1,2})(.*?)(\$\d{0,1})')
	texttoclean = re.sub(anddollars, andsubstitutes, texttoclean)

	# these strays are rough
	# texttoclean = re.sub(r'\&(.*?)\&', r'<hmu_shift_latin_font betacodeval="regular">\1</hmu_shift_latin_font>', texttoclean)

	return texttoclean


def dollarssubstitutes(match):
	"""
	turn $NN...$ into unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))
	core = match.group(2)

	substitutions = {
		70: [r'<span class="uncial">', r'</span>'],
		53: [r'<span class="hebrew">', r'</span>'],
		52: [r'<span class="arabic">', r'</span>'],
		51: [r'<span class="demotic">', r'</span>'],
		50: [r'<span class="coptic">', r'</span>'],
		40: [r'<span class="extralarge">', r'</span>'],
		30: [r'<span class="extrasmall">', r'</span>'],
		20: [r'<span class="largerthannormal">', r'</span>'],
		18: [r'<span class="smallerthannormal">', r'</span>'],  # + 'vertical', but deprecated
		16: [r'<span class="smallerthannormalsuperscriptbold">', r'</span>'],
		15: [r'<span class="smallerthannormalsubscript">', r'</span>'],
		14: [r'<span class="smallerthannormalsuperscript">', r'</span>'],
		13: [r'<span class="smallerthannormalitalic">', r'</span>'],
		11: [r'<span class="smallerthannormalbold">', r'</span>'],
		10: [r'<span class="smallerthannormal">', r'</span>'],
		9: [r'<span class="regular">', r'</span>'],
		8: [r'<span class="vertical">', r'</span>'],
		6: [r'<span class="superscriptbold">', r'</span>'],
		5: [r'<span class="subscript">', r'</span>'],
		4: [r'<span class="superscript">', r'</span>'],
		3: [r'<span class="italic">', r'</span>'],
		2: [r'<span class="bolditalic">', r'</span>'],
		1: [r'<span class="bold">', r'</span>']
	}

	try:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	except KeyError:
		substitute = '<hmu_unhandled_greek_font_shift betacodeval="{v}" />{c}'.format(v=val, c=core)
		if warnings:
			print('\t',substitute)

	return substitute


def andsubstitutes(match):
	"""
	turn &NN...& into unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))
	core = match.group(2)

	substitutions = {
		91: [r'<hmu_undocumented_font_shift_AND91>',r'</hmu_undocumented_font_shift_AND91>'],
		90: [r'<hmu_undocumented_font_shift_AND90>', r'</hmu_undocumented_font_shift_AND90>'],
		82: [r'<hmu_undocumented_font_shift_AND82>', r'</hmu_undocumented_font_shift_AND82>'],
		81: [r'<hmu_undocumented_font_shift_AND81>', r'</hmu_undocumented_font_shift_AND81>'],
		20: [r'<span class="largerthannormal">',r'</span>'],
		14: [r'<span class="smallerthannormalsuperscript">',r'</span>'],
		13: [r'<span class="smallerthannormalitalic">', r'</span>'],
		10: [r'<span class="smallerthannormal">', r'</span>'],
		9: [r'<span class="normal">', r'</span>'],
		8: [r'<span class="smallcapitalsitalic">', r'</span>'],
		7: [r'<span class="smallcapitals">', r'</span>'],
		6: [r'<span class="romannumerals">', r'</span>'],
		5: [r'<span class="subscript">', r'</span>'],
		4: [r'<span class="superscript">', r'</span>'],
		3: [r'<span class="italic">', r'</span>'],
		2: [r'<span class="bolditalic">', r'</span>'],
		1: [r'<span class="bold">', r'</span>'],
	}

	try:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	except KeyError:
		substitute = '<hmu_unhandled_latin_font_shift betacodeval="{v}" />{c}'.format(v=val, c=core)
		if warnings:
			print('\t',substitute)

	return substitute
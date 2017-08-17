# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

def replacecoptic(texttoclean):
	"""

	:param texttoclean:
	:return:
	"""

	# a latin fontshift can come before hmu_fontshift_greek_coptic; see INS0180
	# <hmu_fontshift_greek_coptic>ⲕⲑϥⲫϥⲙϥⲱ <hmu_fontshift_latin_normal><span class="hmu_marginaltext">vac.</span></hmu_fontshift_greek_coptic>
	insetcoptic = re.compile(r'(<hmu_fontshift_greek_coptic>)(.*?)(&|</hmu_fontshift_greek_coptic>)')

	cleaned = re.sub(insetcoptic, copticprobe, texttoclean)

	return cleaned


def copticprobe(match):
	"""

	:param match:
	:return:
	"""

	opentag = match.group(1)
	closetag = match.group(3)
	body = match.group(2)

	# print('copticprobe body:', body)

	capitalfinder = re.compile(r'\*([a-zA-Z])')

	body = re.sub(capitalfinder, lambda x: copticuppercases(x.group(1)), body)
	body = re.sub(r'[a-zA-Z]', lambda x: copticlowercases(x.group(0)), body)

	newcoptic = '{a}{b}{c}'.format(a=opentag, b=body, c=closetag)

	return newcoptic


def copticuppercases(val):
	"""

	:param val:
	:return:
	"""

	substitutions = {
		'A': u'\u2c80',
		'B': u'\u2c82',
		'C': u'\u2c9c',
		'D': u'\u2c86',
		'E': u'\u2c86',
		'F': u'\u2caa',
		'f': u'\u03e4',
		'G': u'\u2c84',
		'g': u'\u03ec',
		'H': u'\u2c8e',
		'h': u'\u03e8',
		'I': u'\u2c92',
		'j': u'\u03ea',
		'K': u'\u2c94',
		'L': u'\u2c96',
		'M': u'\u2c98',
		'N': u'\u2c9a',
		'O': u'\u2c9e',
		'P': u'\u2ca0',
		'Q': u'\u2c90',
		'R': u'\u2ca2',
		'S': u'\u2ca4',
		's': u'\u03e2',
		'T': u'\u2ca6',
		't': u'\u03ee',
		'U': u'\u2ca8',
		'V': u'\u2c8a',
		'W': u'\u2cb0',
		'X': u'\u2cac',
		'Y': u'\u2cae',
		'Z': u'\u2c8c',
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		# print('coptic capital confusion:', val)
		substitute = val

	return substitute


def copticlowercases(val):

	substitutions = {
		'A': u'\u2c81',
		'B': u'\u2c83',
		'C': u'\u2c9d',
		'D': u'\u2c87',
		'E': u'\u2c89',
		'F': u'\u2cab',
		'f': u'\u03e5',
		'G': u'\u2c85',
		'g': u'\u03ed',
		'H': u'\u2c8f',
		'h': u'\u03e9',
		'I': u'\u2c93',
		# 'J': u'\u03eb',  # ? DDP0088 has a 'J'
		'j': u'\u03eb',
		'K': u'\u2c95',
		'L': u'\u2c97',
		'M': u'\u2c99',
		'N': u'\u2c9b',
		'O': u'\u2c9f',
		'P': u'\u2ca1',
		'Q': u'\u2c91',
		'R': u'\u2ca3',
		'S': u'\u2ca5',
		's': u'\u03e3',
		'T': u'\u2ca7',
		't': u'\u03ef',
		'U': u'\u2ca9',
		'V': u'\u2c8b',
		'W': u'\u2cb1',
		'X': u'\u2cad',
		'Y': u'\u2caf',
		'Z': u'\u2c8d',
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		# print('coptic lowercase confusion:', val)
		substitute = val

	return substitute



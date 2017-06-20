# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from builder.parsers.swappers import hextohighunicode


def loadidt(filepath):
	"""
	simple simon: a raw read of the file to prepare it for the brutal parse
	:param filepath:
	:return: idtdata
	"""
	f = open(filepath, 'rb')
	idtdata = f.read()
	f.close()

	return idtdata


def findauthors(pathtoauthtab):
	"""
	tell me the disk path to the authtab file
	I will give you a list of authornumbers&authornames
	[('2000', '&1Ablabius&'), ('0400', 'Lucius &1Accius&'), ...]
	:param pathtoauthtab:
	:return: availableauthors (dict with key as author number)
	"""
	# need to drop the LAT or GRK prefix
	
	f = open(pathtoauthtab + 'AUTHTAB.DIR', 'rb')
	o = f.read()
	o = "".join(map(chr, o))
	f.close()

	# authorparser = re.compile('(\w\w\w\d)\s+([\x01-\x7f]*[a-zA-Z][^\x83\xff]*)')
	authorparser = re.compile('([A-Z]{1,3}\w\w\w\d)\s+([\x01-\x7f]*[a-zA-Z][^\x83\xff]*)')
	availableauthors = dict(authorparser.findall(o))

	return availableauthors


def highunicodefileload(filepath):
	"""
	open a CD file and get it ready for parsing
	:return: a collection of characters with the unprintable chars swapped out for their hex representation
	"""

	f = open(filepath, 'rb')
	o = f.read()
	f.close()

	utf = ''.join(map(chr, o))

	# swap out the high values for hex representations of those values:
	#   █ⓔⓕ █⑧⓪ █ⓑ⓪ █ⓑ⓪ █ⓑ① █ⓑ⓪ █ⓕⓕ

	txt = []
	for c in range(0, len(o) - 1):
		if (o[c] >= 128) or (o[c] <= 31):
			x = hex(o[c])
			# cumbersome and painful, but it prevents any possibility of confusing the ascii and the control sequences
			x = '█' + hextohighunicode(x[2:4]) # FULL BLOCK Unicode: U+2588
			txt.append(x + ' ')
		else:
			txt.append(utf[c])

	txt = ''.join(txt)

	return txt


def dirtyhexloader(filepath):
	"""
	open a CD file and get it ready for parsing
	:return: a collection of characters with the unprintable chars swapped out for their hex representation
	"""

	f = open(filepath, 'rb')
	o = f.read()
	f.close()

	utf = ''.join(map(chr, o))

	# swap out the high values for hex representations of those values

	txt = []
	for c in range(0, len(o) - 1):
		if (o[c] >= 128) or (o[c] <= 31):
			txt.append(hex(o[c]) + ' ')
		else:
			txt.append(utf[c])

	txt = ''.join(txt)

	return txt


def loadbin(filepath):
	"""
	simple simon: a raw read of the file to prepare it for the brutal parse
	:param filepath:
	:return: binfile data
	"""
	f = open(filepath, 'rb')
	binfile = f.read()
	f.close()

	return binfile



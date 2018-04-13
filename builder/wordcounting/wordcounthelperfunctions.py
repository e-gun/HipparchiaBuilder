# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
from itertools import zip_longest


def dictmerger(masterdict, targetdict, label):
	"""

	:param masterdict:
	:param targetdict:
	:return:
	"""

	for item in targetdict:
		if item in masterdict:
			try:
				targetdict[item][label]
			except KeyError:
				targetdict[item][label] = 0
			try:
				masterdict[item][label] += targetdict[item][label]
			except KeyError:
				masterdict[item][label] = targetdict[item][label]
		else:
			masterdict[item] = dict()
			try:
				masterdict[item][label] = targetdict[item][label]
			except KeyError:
				targetdict[item][label] = 0
				masterdict[item][label] = 0

	return masterdict


def acuteforgrave(matchgroup):
	"""

	swap acute version for the grave

	:param matchgroup:
	:return:
	"""

	lettermap = {'ὰ': 'ά',
	       'ὲ': 'έ',
	       'ὶ': 'ί',
	       'ὸ': 'ό',
	       'ὺ': 'ύ',
	       'ὴ': 'ή',
	       'ὼ': 'ώ',
	       'ἂ': 'ἄ',
	       'ἒ': 'ἔ',
	       'ἲ': 'ἴ',
	       'ὂ': 'ὄ',
	       'ὒ': 'ὔ',
	       'ἢ': 'ἤ',
	       'ὢ': 'ὤ',
	       'ᾃ': 'ᾅ',
	       'ᾓ': 'ᾕ',
	       'ᾣ': 'ᾥ',
	       'ᾂ': 'ᾄ',
	       'ᾒ': 'ᾔ',
	       'ᾢ': 'ᾤ'
	       }

	try:
		substitute = lettermap[matchgroup.group(0)]
	except KeyError:
		substitute = ''

	return substitute


def cleanwords(word, punct):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
	# strip all non-greek if we are doing greek
	# best do punct before this next one...

	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass

	return word


def prettyprintcohortdata(label, cohortresultsdict):
	"""
	take some results and print them (for use in one of HipparchiaServer's info pages)

	:return:
	"""

	titles = {'h': 'high', 'l': 'low', 'a': 'average', 'm': 'median', '#': 'count'}

	print()
	print(label)
	for item in ['#', 'h', 'l', 'a', 'm']:
		print('\t'+titles[item]+'\t'+str(int(cohortresultsdict[item])))

	return


def rebasedcounter(decimalvalue, base):
	"""

	return a three character encoding of a decimal number in 'base N'
	designed to allow work names to fit into a three 'digit' space

	:param decimalvalue:
	:return:
	"""

	# base = 36

	if base < 11:
		iterable = range(0, base)
		remap = {i: str(i) for i in iterable}
	elif base < 37:
		partone = {i: str(i) for i in range(0, 10)}
		parttwo = {i: chr(87 + i) for i in range(10, base)}
		remap = {**partone, **parttwo}
	else:
		print('unsupported base value', base, '- opting for base10')
		remap = {i: str(i) for i in range(0, 10)}

	# base = 36
	# {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
	# 10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f', 16: 'g', 17: 'h', 18: 'i', 19: 'j',
	# 20: 'k', 21: 'l', 22: 'm', 23: 'n', 24: 'o', 25: 'p', 26: 'q', 27: 'r', 28: 's', 29: 't',
	# 30: 'u', 31: 'v', 32: 'w', 33: 'x', 34: 'y', 35: 'z'}

	lastdigit = remap[decimalvalue % base]
	remainder = int(decimalvalue / base)
	if remainder > 0:
		seconddigit = remap[remainder % base]
		remainder = int(remainder / base)
		if remainder > 0:
			thirddigit = remap[remainder % base]
		else:
			thirddigit = '0'
	else:
		seconddigit = '0'
		thirddigit = '0'

	rebased = thirddigit + seconddigit + lastdigit

	return rebased


def unpackchainedranges(chainedranges):
	"""

	turn a list of flat numbers and ranges into a flat list of numbers

	:param chainedranges:
	:return:
	"""

	chainedlines = list(chainedranges)
	# but you now have a list that itself might contain ranges:
	# in001a [190227, range(188633, 188638), range(183054, 183056), range(183243, 183246), ...]
	linelist = list()
	for item in chainedlines:
		if isinstance(item, int):
			linelist.append(item)
		elif isinstance(item, range):
			linelist.extend(list(item))
		else:
			print('problem item {i} is type {t}'.format(i=item, t=type(item)))

	# linelist = list(set(linelist))
	# linelist.sort()

	return linelist


def concordancemerger(listofconcordancedicts):
	"""

	:return:
	"""

	print('\tmerging the partial results')
	try:
		masterconcorcdance = listofconcordancedicts.pop()
	except IndexError:
		masterconcorcdance = dict()

	for cd in listofconcordancedicts:
		# find the 'gr' in something like {'τότοιν': {'gr': 1}}
		tdk = list(cd.keys())
		tdl = list(cd[tdk[0]].keys())
		label = tdl[0]
		masterconcorcdance = dictmerger(masterconcorcdance, cd, label)

	return masterconcorcdance


def grouper(iterable, n, fillvalue=None):
	"""
	recipe from https://docs.python.org/3.6/library/itertools.html

	Collect data into fixed-length chunks or blocks

	grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx

	:param iterable:
	:param n:
	:param fillvalue:
	:return:
	"""

	args = [iter(iterable)] * n
	return zip_longest(*args, fillvalue=fillvalue)


"""
prettyprintcohortdata()

greek

full set
	count	113010
	high	3649037
	low	1
	average	794
	median	7

top 250
	count	250
	high	3649037
	low	39356
	average	218482
	median	78551

top 2500
	count	2250
	high	38891
	low	3486
	average	9912
	median	7026

core (not in top 2500; >50 occurrences)
	count	25901
	high	3479
	low	51
	average	466
	median	196

rare (between 50 and 5 occurrences)
	count	32614
	high	50
	low	6
	average	18
	median	15

very rare (fewer than 5 occurrences)
	count	48003
	high	4
	low	1
	average	1
	median	2


latin

full set
	count	27960
	high	244812
	low	1
	average	348
	median	11

top 250
	count	250
	high	244812
	low	5859
	average	19725
	median	10358

top 2500
	count	2250
	high	5843
	low	541
	average	1565
	median	1120

core (not in top 2500; >50 occurrences)
	count	6149
	high	541
	low	51
	average	181
	median	139

rare (between 50 and 5 occurrences)
	count	8095
	high	50
	low	6
	average	19
	median	16

very rare (fewer than 5 occurrences)
	count	10404
	high	4
	low	1
	average	1
	median	2
"""

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque

try:
	regexmatch = re.Match
except AttributeError:
	# python < 3.7
	regexmatch = object()


def transliteratecolums(deprepdeque: deque):
	"""

	call transliteratethedeque() for the columns you want to modify

	2 and/or 3, I guess

	:param deprepdeque:
	:return:
	"""

	columns = [2, 3, 4]
	for c in columns:
		deprepdeque = transliteratethedeque(deprepdeque, c)

	return deprepdeque


def transliteratethedeque(deprepdeque: deque, workingcolumn=4) -> deque:
	"""

	3: modify the stripped column


	:param deprepdeque:
	:return:
	"""

	dbreadyversion = deque()

	for line in deprepdeque:
		tomodify = line[workingcolumn]
		modified = runsswapsuite(tomodify)
		newline = list()
		for c in range(len(line)):
			if c != workingcolumn:
				newline.append(line[c])
			else:
				if workingcolumn == 4:
					newline.append(modified.lower())
				else:
					newline.append(modified)
		dbreadyversion.append(newline)

	return dbreadyversion


def runsswapsuite(texttoswap: str) -> str:
	"""
	sequence:
		hforrough()
		stripaccents()
		.lower()
		twoletterswaps() x
		oneletterswaps() x
		oneintotwosubs()

	"""

	functionlist = [hforrough, stripaccents, str.lower, twoletterswaps, oneletterswaps,
	                oneintotwosubs, str.upper]
	for f in functionlist:
		texttoswap = f(texttoswap)

	return texttoswap


def hforrough(texttoswap: str) -> str:

	therough = r'[ᾃᾓᾣᾅᾕᾥᾇᾗᾧἃἓἳὃὓἣὣἅἕἵὅὕἥὥἇἑ͂ἷὁ͂ὗἧὧᾁᾑᾡἁἑἱὁὑἡὡ]'

	matchswapper = lambda x: 'H' + x.group(0)

	swapped = re.sub(therough, matchswapper, texttoswap)

	return swapped


def twoletterswaps(texttoswap: str) -> str:
	"""

	ει	-> I
	ou	-> O

	:param texttoswap:
	:return:
	"""

	t = re.sub(r'ει', 'I', texttoswap)
	t = re.sub(r'ou', 'O', t)

	return t


def oneletterswaps(texttoswap: str) -> str:
	"""

	α -> A
	β -> B
	...

	:param texttoswap:
	:return:
	"""

	invals = 'αβγδεζηικλμνξοπρϲτυω'
	outvals = 'ABGDEZEIKLMNXOPRSTUO'
	transtable = str.maketrans(invals, outvals)
	swapped = texttoswap.translate(transtable)

	return swapped


def oneintotwosubs(texttoswap: str) -> str:
	"""

	θ	TH
	φ	PH
	χ	CH
	ψ	PS

	:param texttoswap:
	:return:
	"""

	substitutes = {
		'θ': 'TH',
		'φ': 'PH',
		'χ': 'CH',
		'ψ': 'PS'
	}

	seeking = r'[θφχψ]'

	twocharmatchswapper = lambda x: substitutes[x.group(0)]

	swapped = re.sub(seeking, twocharmatchswapper, texttoswap)
	return swapped


def stripaccents(texttostrip: str, transtable=None) -> str:
	"""

	turn ᾶ into α, etc

	there are more others ways to do this; but this is the fast way
	it turns out that this was one of the slowest functions in the profiler

	transtable should be passed here outside of a loop
	but if you are just doing things one-off, then it is fine to have
	stripaccents() look up transtable itself

	:param texttostrip:
	:param transtable:
	:return:
	"""

	# if transtable == None:
	# 	transtable = buildhipparchiatranstable()

	try:
		stripped = texttostrip.translate(transtable)
	except TypeError:
		stripped = stripaccents(texttostrip, transtable=buildhipparchiatranstable())

	return stripped


def buildhipparchiatranstable() -> dict:
	"""

	pulled this out of stripaccents() so you do not maketrans 200k times when
	polytonicsort() sifts an index

	:return:
	"""

	invals = list()
	outvals = list()

	invals.append('ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰά')
	outvals.append('α' * len(invals[-1]))
	invals.append('ἐἑἒἓἔἕὲέ')
	outvals.append('ε' * len(invals[-1]))
	invals.append('ἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐ')
	outvals.append('ι' * len(invals[-1]))
	invals.append('ὀὁὂὃὄὅόὸ')
	outvals.append('ο' * len(invals[-1]))
	invals.append('ὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺ')
	outvals.append('υ' * len(invals[-1]))
	invals.append('ᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧ')
	outvals.append('η' * len(invals[-1]))
	invals.append('ὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ')
	outvals.append('ω' * len(invals[-1]))

	invals.append('ᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ')
	outvals.append('α' * len(invals[-1]))
	invals.append('ἘἙἚἛἜἝΕ')
	outvals.append('ε' * len(invals[-1]))
	invals.append('ἸἹἺἻἼἽἾἿΙ')
	outvals.append('ι' * len(invals[-1]))
	invals.append('ὈὉὊὋὌὍΟ')
	outvals.append('ο' * len(invals[-1]))
	invals.append('ὙὛὝὟΥ')
	outvals.append('υ' * len(invals[-1]))
	invals.append('ᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯΗ')
	outvals.append('η' * len(invals[-1]))
	invals.append('ᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯ')
	outvals.append('ω' * len(invals[-1]))
	invals.append('ῤῥῬ')
	outvals.append('ρρρ')
	invals.append('ΒΨΔΦΓΞΚΛΜΝΠϘΡσΣςϹΤΧΘΖ')
	outvals.append('βψδφγξκλμνπϙρϲϲϲϲτχθζ')

	# some of the vowels with quantities are compounds of vowel + accent: can't cut and paste them into the xformer
	invals.append('vUJjÁÄáäÉËéëÍÏíïÓÖóöÜÚüúăāĕēĭīŏōŭū')
	outvals.append('uVIiaaaaeeeeiiiioooouuuuaaeeiioouu')

	invals = ''.join(invals)
	outvals = ''.join(outvals)

	transtable = str.maketrans(invals, outvals)

	return transtable


# x = 'εἰκῇ λεγόμενα τοῖϲ ἐπιτυχοῦϲιν ὀνόμαϲιν'
# t = 'ἡλικίᾳ ὥϲπερ μειρακίῳ πλάττοντι λόγουϲ εἰϲ ὑμᾶϲ εἰϲιέναι'
# print(runsswapsuite(t))
# print(runsswapsuite(x))

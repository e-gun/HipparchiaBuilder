# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from builder.parsers.betacodeletterscapitals import capitalletters
from builder.parsers.betacodeletterslowercase import lowercaseletters

def replacegreekbetacode(texttoclean):
	"""
	swap betacode for unicode values
	:param texttoclean:
	:return:
	"""

	texttoclean = capitalletters(texttoclean)
	texttoclean = lowercaseletters(texttoclean)
	# combining dot
	texttoclean = re.sub(r'\?', u'\u0323', texttoclean)

	# exclmation point not properly documented
	# note that runs of individual '!' can be found: '∙∙∙'
	# but if you see '!21`45' you are supposed to print
	# 21 of them and then '45'
	texttoclean = re.sub(r'!(\d+)', multipledots, texttoclean)
	texttoclean = re.sub(r'!', u'\u2219', texttoclean)

	return texttoclean


# interconversion functions

def parseromaninsidegreek(texttoclean):
	"""
	note that this is called via a re.match group
	:param texttoclean:
	:return:
	"""
	mangledroman = texttoclean.group(2)

	# note that combining dot below is at the end: 0323
	invals = u'αβξδεφγηι⒣κλμνοπθρϲστυϝωχψζϋ·̣'
	outvals = u'ABCDEFGHIJKLMNOPQRSSTUVWXYZü:?'
	transformed = mangledroman.translate(str.maketrans(invals, outvals))

	span = '{open}{t}{close}'.format(t=transformed, open=texttoclean.group(1), close=texttoclean.group(3))

	return span


def parsegreekinsidelatin(texttoclean):
	betagreek = texttoclean.group(0)
	unigreek = replacegreekbetacode(betagreek)
	# print(betagreek, unigreek)
	return unigreek


def restoreromanwithingreek(texttoclean):
	search = r'(<hmu_fontshift_latin_.*?>)(.*?)(</hmu_fontshift_latin_.*?>)'
	texttoclean = re.sub(search, parseromaninsidegreek, texttoclean)
	texttoclean = re.sub(search, ldc, texttoclean)

	return texttoclean


def cleanaccentsandvj(texttostrip, transtable=None):
	"""

	turn ᾶ into α, etc

	there are more others ways to do this; but this is the fast way
	it turns out that this was one of the slowest functions in the profiler

	transtable should be passed here outside of a loop
	but if you are just doing things one-off, then it is fine to have
	stripaccents() look up transtable itself

	:param texttostrip:
	:return:
	"""

	if transtable == None:
		transtable = buildhipparchiatranstable()

	stripped = texttostrip.translate(transtable)

	return stripped


def buildhipparchiatranstable():
	"""

	pulled this out of stripaccents() so you do not maketrans 200k times when
	polytonicsort() sifts an index

	:return:
	"""

	invals = ['ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ']
	outvals = ['αααααααααααααααααααααααααεεεεεεεειιιιιιιιιιιιιιιιιοοοοοοοουυυυυυυυυυυυυυυυυηηηηηηηηηηηηηηηηηηηηηηηωωωωωωωωωωωωωωωωωωωωωωω']

	invals.append('ᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑἘἙἚἛἜἝΕἸἹἺἻἼἽἾἿΙὈὉὊὋὌὍΟὙὛὝὟΥᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯΗᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯῤῥῬΒΨΔΦΓΞΚΛΜΝΠϘΡσΣςϹΤΧΘΖ')
	outvals.append('αααααααααααααααααεεεεεεειιιιιιιιιοοοοοοουυυυυηηηηηηηηηηηηηηηηηωωωωωωωωωωωωωωωωρρρβψδφγξκλμνπϙρϲϲϲϲτχθζ')

	invals.append('vUjÁÄáäÉËéëÍÏíïÓÖóöÜÚüú')
	outvals.append('uViaaaaeeeeiiiioooouuuu')

	invals = ''.join(invals)
	outvals = ''.join(outvals)

	transtable = str.maketrans(invals, outvals)

	return transtable


def purgehybridgreekandlatinwords(texttoclean):
	"""

	files that have both greek and latin are naughty about flagging the swaps in language
	the result can be stuff like this:
		"domno piissimo αugusto λeone anno χϝι et ξonstantino"

	this will look for g+latin and turn it into Latin
	the roman numeral problem will remain: so the real fix is to dig into this elsewhere/earlier

	:param texttoclean:
	:return:
	"""

	# fixes: ξonstantino
	mix = re.compile(r'([α-ωϲϝ])([a-z])')
	transformed = re.sub(mix, unmixer, texttoclean)

	# fixes: s(anctae) ῥomanae
	mix = re.compile(r'([ἁἑἱὁὑἡὡῥ])([a-z])')
	transformed = re.sub(mix, unbreather, transformed)

	# fixes: λ. Pomponius
	mix = re.compile(r'(\s)([α-ωϲϝ])(\.\s[A-Z])')
	transformed = re.sub(mix, unpunctuated, transformed)

	# fixes: ξ[apitoli]o or ξ(apitolio)
	mix = re.compile(r'(\s)([α-ωϲϝ])(\[[a-z]|\([a-z])')
	transformed = re.sub(mix, unpunctuated, transformed)

	return transformed


def unmixer(matchgroup):
	"""

	helper for purgehybridgreekandlatinwords()

	fixes: ξonstantino

	10 of these will be found in CHR

	:param matchgroup:
	:return:
	"""
	greekchar = matchgroup.group(1)
	latinchar = matchgroup.group(2)

	invals = u'αβξδεφγηι⒣κλμνοπρϲτυϝωχυζ'
	outvals = u'ABCDEFGHIJKLMNOPRSTUVWXYZ'
	transformed = greekchar.translate(str.maketrans(invals, outvals))
	transformed += latinchar

	return transformed


def unbreather(matchgroup):
	"""

	another helper for purgehybridgreekandlatinwords()

	fixes: s(anctae) ῥomanae

	c. 35 of these will be found in CHR

	:param matchgroup:
	:return:
	"""

	greekchar = matchgroup.group(1)
	latinchar = matchgroup.group(2)

	errantbreathing = {
		u'ἁ': '(A',
		u'ἑ': '(E',
		u'ἱ': '(I',
		u'ὁ': '(O',
		u'ὑ': '(U',
		u'ἡ': '(H',
		u'ὡ': '(W',
		u'ῥ': '(R'
	}

	transformed = errantbreathing[greekchar] + latinchar

	return transformed


def unpunctuated(matchgroup):
	"""

	another helper for purgehybridgreekandlatinwords()

	depending on matchgroup.group(3):

		fixes: λ. Pomponius
		fixes: ξ[apitoli]o or ξ(apitolio)

	0 of these will be found in CHR

	:param matchgroup:
	:return:
	"""

	initial = matchgroup.group(1)
	greekchar = matchgroup.group(2)
	punct = matchgroup.group(3)

	invals = u'αβξδεφγηι⒣κλμνοπρϲτυϝωχυζ'
	outvals = u'ABCDEFGHIJKLMNOPRSTUVWXYZ'
	transformed = greekchar.translate(str.maketrans(invals, outvals))

	transformed = initial + transformed + punct

	return transformed


def multipledots(matchgroup):
	"""

	if you see '!21`45' you are supposed to print 21 copies of ∙ and then '45'

	:param matchgroup:
	:return:
	"""

	dotcount = 1

	try:
		dotcount = int(matchgroup.group(1))
	except:
		pass

	lotsofdots = []
	for d in range(0, dotcount):
		lotsofdots.append('∙')

	# '∙ ' for the sake of line spacing
	lotsofdots = ' '.join(lotsofdots)

	return lotsofdots


# bleh: circular import if you try to load from regex_substitutions
# kludge for the moment


def ldcfindandclean(texttoclean):
	"""

	find text with latin diacritical marks
	then send it to the cleaners

	:param texttoclean:
	:return:
	"""

	finder = re.compile(r'[aeiouyAEIOU][\+\\=/]')

	texttoclean = re.sub(finder, latinsubstitutes, texttoclean)

	return texttoclean


def latinsubstitutes(matchgroup):
	val = matchgroup.group(0)

	substitues = {
		'a/': u'\u00e1',
		'e/': u'\u00e9',
		'i/': u'\u00ed',
		'o/': u'\u00f3',
		'u/': u'\u00fa',
		'y/': u'\u00fd',
		'A/': u'\u00c1',
		'E/': u'\u00c9',
		'I/': u'\u00cd',
		'O/': u'\u00d3',
		'U/': u'\u00da',
		'a+': 'ä',
		'A+': 'Ä',
		'e+': 'ë',
		'E+': 'Ë',
		'i+': 'ï',
		'I+': 'Ï',
		'o+': 'ö',
		'O+': 'Ö',
		'u+': 'ü',
		'U+': 'Ü',
		'a=': 'â',
		'A=': 'Â',
		'e=': 'ê',
		'E=': 'Ê',
		'i=': 'î',
		'I=': 'Î',
		'o=': 'ô',
		'O=': 'Ô',
		'u=': 'û',
		'U=': 'Û',
		'a\\': 'à',
		'A\\': 'À',
		'e\\': 'è',
		'E\\': 'È',
		'i\\': 'ì',
		'I\\': 'Ì',
		'o\\': 'ò',
		'O\\': 'Ò',
		'u\\': 'ù',
		'U\\': 'Ù',
	}

	if val in substitues:
		substitute = substitues[val]
	else:
		substitute = ''

	return substitute


def ldc(matchgroup):
	"""

	a matchgroup clone of latindiacriticals() in regex_substitutions
	should refactor to consolidate, but the the circular import note above

	:param matchgroup:
	:return:
	"""

	texttoclean = matchgroup.group(0)
	texttoclean = ldcfindandclean(texttoclean)

	return texttoclean

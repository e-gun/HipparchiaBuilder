# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from builder.parsers.betacodecapitals import capitalletters
from builder.parsers.betacodelowercase import lowercaseletters

def replacegreekbetacode(texttoclean):
	"""
	swap betacode for unicode values
	:param texttoclean:
	:return:
	"""
	
	texttoclean = capitalletters(texttoclean)
	texttoclean = lowercaseletters(texttoclean)
	# combining dot
	texttoclean = re.sub(r'\?', u'\u0323',texttoclean)
	# exclmation point not properly documented
	texttoclean = re.sub(r'\!', u'\u2219',texttoclean)

	return texttoclean


# interconversion functions

def parseromaninsidegreek(texttoclean):
	"""
	note that this is called via a re.match group
	:param texttoclean:
	:return:
	"""
	mangledroman = texttoclean.group(0)
	
	invals = u'αβξδεφγηι⒣κλμνοπρϲτυϝωχυζ·'
	outvals = u'ABCDEFGHIJKLMNOPRSTUVWXYZ:'
	transformed = mangledroman.translate(str.maketrans(invals, outvals))
	
	return transformed


def parsegreekinsidelatin(texttoclean):
	betagreek = texttoclean.group(0)
	unigreek = replacegreekbetacode(betagreek)
	# print(betagreek, unigreek)
	return unigreek


def restoreromanwithingreek(texttoclean):
	search = r'<hmu_roman_in_a_greek_text>(.*?)</hmu_roman_in_a_greek_text>'
	texttoclean = re.sub(search, parseromaninsidegreek, texttoclean)

	return texttoclean


def stripaccents(texttostrip):
	"""
	turn ᾶ into α, etc
	a non-function that makes this set of substitutes available to more than one function
	:return:
	"""
	substitutes = (
		('v', 'u'),
		('U', 'V'),
		('(Á|Ä)', 'A'),
		('(á|ä)', 'a'),
		('(É|Ë)', 'E'),
		('(é|ë)', 'e'),
		('(Í|Ï)', 'I'),
		('(í|ï)', 'i'),
		('(Ó|Ö)', 'O'),
		('(ó|ö)', 'o'),
		('(ῥ|ῤ|Ῥ)', 'ρ'),
		# some sort of problem with acute alpha which seems to be unkillable
		# (u'u\1f71',u'\u03b1'),
		('(ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά)', 'α'),
		('(ἐ|ἑ|ἒ|ἓ|ἔ|ἕ|ὲ|έ)', 'ε'),
		('(ἰ|ἱ|ἲ|ἳ|ἴ|ἵ|ἶ|ἷ|ὶ|ί|ῐ|ῑ|ῒ|ΐ|ῖ|ῗ|ΐ)', 'ι'),
		('(ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ)', 'ο'),
		('(ὐ|ὑ|ὒ|ὓ|ὔ|ὕ|ὖ|ὗ|ϋ|ῠ|ῡ|ῢ|ΰ|ῦ|ῧ|ύ|ὺ)', 'υ'),
		('(ὠ|ὡ|ὢ|ὣ|ὤ|ὥ|ὦ|ὧ|ᾠ|ᾡ|ᾢ|ᾣ|ᾤ|ᾥ|ᾦ|ᾧ|ῲ|ῳ|ῴ|ῶ|ῷ|ώ|ὼ)', 'ω'),
		# similar problems with acute eta
		# (u'\u1f75','η'),
		('(ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|ή|ἠ|ἡ|ἦ|ἧ)', 'η'),
		('(ᾨ|ᾩ|ᾪ|ᾫ|ᾬ|ᾭ|ᾮ|ᾯ|Ὠ|Ὡ|Ὢ|Ὣ|Ὤ|Ὥ|Ὦ|Ὧ|Ω)', 'ω'),
		('(Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ|Ο)', 'ο'),
		('(ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)', 'α'),
		('(Ἐ|Ἑ|Ἒ|Ἓ|Ἔ|Ἕ|Ε)', 'ε'),
		('(Ἰ|Ἱ|Ἲ|Ἳ|Ἴ|Ἵ|Ἶ|Ἷ|Ι)', 'ι'),
		('(Ὑ|Ὓ|Ὕ|Ὗ|Υ)', 'υ'),
		('(ᾘ|ᾙ|ᾚ|ᾛ|ᾜ|ᾝ|ᾞ|ᾟ|Ἠ|Ἡ|Ἢ|Ἣ|Ἤ|Ἥ|Ἦ|Ἧ|Η)', 'η'),
		('Β', 'β'),
		('Ψ', 'ψ'),
		('Δ', 'δ'),
		('Φ', 'φ'),
		('Γ', 'γ'),
		('Ξ', 'ξ'),
		('Κ', 'κ'),
		('Λ', 'λ'),
		('Μ', 'μ'),
		('Ν', 'ν'),
		('Π', 'π'),
		('Ϙ', 'ϙ'),
		('Ρ', 'ρ'),
		('Ϲ', 'ϲ'),
		('Τ', 'τ'),
		('Θ', 'θ'),
		('Ζ', 'ζ')
	)
	
	for swap in range(0, len(substitutes)):
		texttostrip = re.sub(substitutes[swap][0], substitutes[swap][1], texttostrip)
	
	return texttostrip


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
	transformed = re.sub(mix,unmixer,texttoclean)

	# fixes: s(anctae) ῥomanae
	mix = re.compile(r'([ἁἑἱὁὑἡὡῥ])([a-z])')
	transformed = re.sub(mix, unbreather, transformed)

	# fixes: λ. Pomponius
	mix = re.compile(r'(\s)([α-ωϲϝ])(\.\s[A-Z])')
	transformed = re.sub(mix, unpunctuated, transformed)

	# fixes: ξ[apitoli]o or ξ(apitolio)
	mix = re.compile(r'(\s)([α-ωϲϝ])(\[|\([a-z])')
	transformed = re.sub(mix, unpunctuated, transformed)

	return transformed


def unmixer(matchgroup):
	"""

	helper for purgehybridgreekandlatinwords()

	fixes: ξonstantino

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



# -*- coding: utf-8 -*-
import re

def replacegreekbetacode(texttoclean):
	textualmarkuptuples = []
	# so inefficient...: would faster be better, though?
	# but you are only supposed to do this once per author ever...
	# once did this as a dict, but you can't enforce order that way
	betacodetuples = (
		# capitals with breathings
		# did not implement subscripts (yet)
		(r'[*]\(\=A', u'\u1f0f'),
		(r'[*]\)\=A', u'\u1f0e'),
		(r'[*]\(\/A', u'\u1f0d'),
		(r'[*]\)\/A', u'\u1f0c'),
		(r'[*]\(\\A', u'\u1f08'),
		(r'[*]\)\\A', u'\u1f0a'),
		(r'[*]\(A', u'\u1f09'),
		(r'[*]\)A', u'\u1f08'),
		(r'[*]\(\/E', u'\u1f1d'),
		(r'[*]\)\/E', u'\u1f1c'),
		(r'[*]\(\\E', u'\u1f1b'),
		(r'[*]\)\\E', u'\u1f1a'),
		(r'[*]\(E', u'\u1f19'),
		(r'[*]\)E', u'\u1f18'),
		(r'[*]\(\=I', u'\u1f3f'),
		(r'[*]\)\=I', u'\u1f3e'),
		(r'[*]\(\/I', u'\u1f3d'),
		(r'[*]\)\/I', u'\u1f3c'),
		(r'[*]\(\\I', u'\u1f3b'),
		(r'[*]\)\\I', u'\u1f3a'),
		(r'[*]\(I', u'\u1f39'),
		(r'[*]\)I', u'\u1f38'),
		(r'[*]\(\/O', u'\u1f4d'),
		(r'[*]\)\/O', u'\u1f4c'),
		(r'[*]\(\\O', u'\u1f4b'),
		(r'[*]\)\\O', u'\u1f4a'),
		(r'[*]\(O', u'\u1f49'),
		(r'[*]\)O', u'\u1f48'),
		(r'[*]\(\=U', u'\u1f5f'),
		(r'[*]\(\/U', u'\u1f5d'),
		(r'[*]\(\\U', u'\u1f5b'),
		(r'[*]\(U', u'\u1f59'),
		(r'[*]\(\=W', u'\u1f6f'),
		(r'[*]\)\=W', u'\u1f6e'),
		(r'[*]\(\/W', u'\u1f6d'),
		(r'[*]\)\/W', u'\u1f6c'),
		(r'[*]\(\\W', u'\u1f68'),
		(r'[*]\)\\W', u'\u1f6a'),
		(r'[*]\(W', u'\u1f69'),
		(r'[*]\)W', u'\u1f68'),
		(r'[*]\)\\H\|', u'\u1f9a'),
		(r'[*]\(\\H\|', u'\u1f9b'),
		(r'[*]\)\/H\|', u'\u1f9c'),
		(r'[*]\(\/H\|', u'\u1f9d'),
		(r'[*]\)\=H\|', u'\u1f9e'),
		(r'[*]\(\=H\|', u'\u1f9f'),
		(r'[*]\(\=H', u'\u1f2f'),
		(r'[*]\)\=H', u'\u1f2e'),
		(r'[*]\(\/H', u'\u1f2d'),
		(r'[*]\)\/H', u'\u1f2c'),
		(r'[*]\(\\H', u'\u1f28'),
		(r'[*]\)\\H', u'\u1f2a'),
		(r'[*]\(H', u'\u1f29'),
		(r'[*]\)H', u'\u1f28'),
		(r'[*]H\|', u'\u1fcc'),
		(r'[*]\(R', u'\u1fec'),
		# plain capitals
		(r'[*]A', u'\u0391'),
		(r'[*]B', u'\u0392'),
		(r'[*]C', u'\u039e'),
		(r'[*]D', u'\u0394'),
		(r'[*]E', u'\u0395'),
		(r'[*]F', u'\u03a6'),
		(r'[*]G', u'\u0393'),
		(r'[*]H', u'\u0397'),
		(r'[*]I', u'\u0399'),
		(r'[*]K', u'\u039a'),
		(r'[*]L', u'\u039b'),
		(r'[*]M', u'\u039c'),
		(r'[*]N', u'\u039d'),
		(r'[*]O', u'\u039f'),
		(r'[*]P', u'\u03a0'),
		(r'[*]Q', u'\u0398'),
		(r'[*]R', u'\u03a1'),
		# turn all sigmas into lunates
		(r'[*]S[3]{0,1}', u'\u03f9'),
		(r'[*]T', u'\u03a4'),
		(r'[*]U', u'\u03a5'),
		(r'[*]V', u'\u03dc'),
		(r'[*]W', u'\u03a9'),
		(r'[*]X', u'\u03a7'),
		(r'[*]Y', u'\u03a8'),
		(r'[*]Z', u'\u0396'),
		# lowercase non-vowels
		(r'B', u'\u03b2'),
		(r'C', u'\u03be'),
		(r'D', u'\u03b4'),
		(r'F', u'\u03c6'),
		(r'G', u'\u03b3'),
		(r'K', u'\u03ba'),
		(r'L', u'\u03bb'),
		(r'M', u'\u03bc'),
		(r'N', u'\u03bd'),
		(r'P', u'\u03c0'),
		(r'Q', u'\u03b8'),
		(r'R\(', u'\u1fe5'),
		(r'R\)', u'\u1fe4'),
		(r'R', u'\u03c1'),
		# turn all sigmas into lunates
		(r'S[1-3]{0,1}', u'\u03f2'),
		(r'T', u'\u03c4'),
		(r'V', u'\u03dd'),
		(r'X', u'\u03c7'),
		(r'Y', u'\u03c8'),
		(r'Z', u'\u03b6'),
		# lowecase vowels with diacritical marks
		# alphas: start with the subscript versions
		(r'A\)\\\|', u'\u1f82'),
		(r'A\)\=\|', u'\u1f86'),
		(r'A\)\/\|', u'\u1f84'),
		(r'A\)\|', u'\u1f80'),
		(r'A\(\\\|', u'\u1f83'),
		(r'A\(\=\|', u'\u1f87'),
		(r'A\(\/\|', u'\u1f85'),
		(r'A\(\|', u'\u1f81'),
		(r'A\/\|', u'\u1fb4'),
		(r'A\=\|', u'\u1fb7'),
		(r'A\\\|', u'\u1fb2'),
		# r'A\+\|': u'\u1f70',
		(r'A\|\|', u'\u1fb3'),
		(r'A\)\\', u'\u1f02'),
		(r'A\)\=', u'\u1f06'),
		(r'A\)\/', u'\u1f04'),
		(r'A\)', u'\u1f00'),
		(r'A\(\\', u'\u1f03'),
		(r'A\(\=', u'\u1f07'),
		(r'A\(\/', u'\u1f05'),
		(r'A\(', u'\u1f01'),
		(r'A\/', u'\u03ac'),
		(r'A\=', u'\u1fb6'),
		(r'A\\', u'\u1f70'),
		# r'A\+': u'\u1f70',
		(r'A\|', u'\u1fb3'),
		# sublinear dot is...?
		# r'A\?': u'\u1f70',
		# epsilons
		(r'E\(\/', u'\u1f15'),
		(r'E\)\/', u'\u1f14'),
		(r'E\(\\', u'\u1f13'),
		(r'E\)\\', u'\u1f12'),
		# re.compile('[E]\/'): u'\u03ad',
		(r'E\/', u'\u03ad'),
		(r'E\)', u'\u1f10'),
		(r'E\(', u'\u1f11'),
		(r'E\\', u'\u1f72'),
		# iotas
		(r'I\)\\', u'\u1f32'),
		(r'I\(\\', u'\u1f33'),
		(r'I\)\/', u'\u1f34'),
		(r'I\(\/', u'\u1f35'),
		(r'I\)\=', u'\u1f36'),
		(r'I\(\=', u'\u1f37'),
		(r'I\\\+', u'\u1fd2'),
		(r'I\/\+', u'\u0390'),
		(r'I\/', u'\u03af'),
		(r'I\)', u'\u1f30'), # roman numeral problem: (XI) will wind up as (Xἰ; very had to fix because a lookahead of (?!\s) will ruin εἰ
		(r'I\(', u'\u1f31'),
		(r'I\\', u'\u1f76'),
		(r'I\=', u'\u1fd6'),
		(r'I\+', u'\u03ca'),
		# omicrons
		(r'O\)\\', u'\u1f42'),
		(r'O\(\\', u'\u1f43'),
		(r'O\)\/', u'\u1f44'),
		(r'O\(\/', u'\u1f45'),
		(r'O\/', u'\u03cc'),
		(r'O\)', u'\u1f40'),
		(r'O\(', u'\u1f41'),
		(r'O\\', u'\u1f78'),
		# upsilons
		(r'U\)\\', u'\u1f52'),
		(r'U\(\\', u'\u1f53'),
		(r'U\)\/', u'\u1f54'),
		(r'U\(\/', u'\u1f55'),
		(r'U\)\=', u'\u1f56'),
		(r'U\(\=', u'\u1f57'),
		(r'U\\\+', u'\u1fe2'),
		(r'U\/\+', u'\u03b0'),
		(r'U\=\+', u'\u1fe7'),
		(r'U\/', u'\u03cd'),
		(r'U\)', u'\u1f50'),
		(r'U\(', u'\u1f51'),
		(r'U\\', u'\u1f7a'),
		(r'U\=', u'\u1fe6'),
		(r'U\+', u'\u03cb'),
		# etas (missing any subscript versions?)
		(r'H\)\=\|', u'\u1f96'),
		(r'H\(\=\|', u'\u1f97'),
		(r'H\)\/\|', u'\u1f94'),
		(r'H\)\\', u'\u1f22'),
		(r'H\(\\', u'\u1f23'),
		(r'H\)\/', u'\u1f24'),
		(r'H\(\/', u'\u1f25'),
		(r'H\)\=', u'\u1f26'),
		(r'H\(\=', u'\u1f27'),
		(r'H\=\|', u'\u1fc7'),
		(r'H\/\|', u'\u1fc4'),
		(r'H\\\|', u'\u1fc2'),
		(r'H\)\|', u'\u1f90'),
		(r'H\(\|', u'\u1f91'),
		(r'H\)', u'\u1f20'),
		(r'H\(', u'\u1f21'),
		(r'H\\', u'\u1f74'),
		(r'H\/', u'\u1f75'),
		(r'H\=', u'\u1fc6'),
		(r'H\|', u'\u1fc3'),
		# omegas
		(r'W\(\=\|', u'\u1fa7'),
		(r'W\)\=\|', u'\u1fa6'),
		(r'W\(\/\|', u'\u1fa5'),
		(r'W\)\/\|', u'\u1fa4'),
		(r'W\(\\\|', u'\u1fa3'),
		(r'W\)\\\|', u'\u1fa2'),
		(r'W\=\|', u'\u1ff7'),
		(r'W\/\|', u'\u1ff4'),
		(r'W\\\|', u'\u1ff2'),
		(r'W\(\|', u'\u1fa1'),
		(r'W\)\|', u'\u1fa0'),
		(r'W\(\=', u'\u1f67'),
		(r'W\)\=', u'\u1f66'),
		(r'W\(\/', u'\u1f65'),
		(r'W\)\/', u'\u1f64'),
		(r'W\(\\', u'\u1f63'),
		(r'W\)\\', u'\u1f62'),
		(r'W\|', u'\u1ff3'),
		(r'W\=', u'\u1ff6'),
		(r'W\\', u'\u1f7c'),
		(r'W\(', u'\u1f61'),
		(r'W\)', u'\u1f60'),
		(r'W\/', u'\u03ce'),
		# here comes something that did not crop up until using perseus' LSJ: vowel+_ for long-vowel and vowel+^ for short
		# if you use these converters you will get two new problems: [1] not every vowellen + accent is available in your charset;
		# [2] now you will have trouble matching found words with dictionary entries
		# this should be handled separately with an additional check: send some items through each route; ugh.
		# this is the 'right version'
		# (r'A_', u'\u1fb1'),
		# (r'I_', u'\u1fd1'),
		# (r'U_', u'\u1fe1'),
		# (r'A\^', u'\u1fb0'),
		# (r'I\^', u'\u1fd0'),
		# (r'U\^', u'\u1fe0'),
		# this is the 'cheat version' (accents w/out lengths)
		# lowercase unaccented vowels
		(r'A_', u'\u03b1'),
		(r'I_', u'\u03b9'),
		(r'U_', u'\u03c5'),
		(r'A\^', u'\u03b1'),
		(r'I\^', u'\u03b9'),
		(r'U\^', u'\u03c5'),
		(r'A', u'\u03b1'),
		(r'E', u'\u03b5'),
		(r'I', u'\u03b9'),
		(r'O', u'\u03bf'),
		(r'U', u'\u03c5'),
		(r'H', u'\u03b7'),
		(r'W', u'\u03c9'),
		# punctuation + combining diacriticals (which typically don't combine...)
		# note that the colon is already used in the comments
		(r'(?<!\d)\:', u'\u00b7'),
		## combining dot is \u0323 [try \u0325?]: but see the note. The Unicode Standard 5.0 does not have a non-combining clone for Combining Dot Below. Currently, 002E Period represents a ‘best fit’ solution.
		#(r'\?', u'\u002e'),
		(r'\?', u'\u0323'),
		## exclmation point not properly documented
		(r'\!', u'\u2219')
	)

	for i in range(0, len(betacodetuples)):
		textualmarkuptuples.append((betacodetuples[i][0], betacodetuples[i][1]))

	for reg in textualmarkuptuples:
		texttoclean = re.sub(reg[0], reg[1], texttoclean)

	# handy way to see if the greek char matches the betacode that searches for it
	# for tup in textualmarkuptuples:
	#   print(tup[0]+" "+tup[1])
	return texttoclean


# interconversion functions

def parseromaninsidegreek(texttoclean):
	"""
	note that this is called via a re.match group
	:param texttoclean:
	:return:
	"""
	mangledroman = texttoclean.group(0)
	# the Roman capitals will have been turned into lower case greek
	# undo this
	textualmarkuptuples = []
	betacodetuples = (
		(u'α', u'A'),
		(u'β', u'B'),
		(u'ξ', u'C'),
		(u'δ', u'D'),
		(u'ε', u'E'),
		(u'φ', u'F'),
		(u'γ', u'G'),
		(u'η', u'H'),
		(u'ι', u'I'),
		(u'κ', u'K'),
		(u'λ', u'L'),
		(u'μ', u'M'),
		(u'ν', u'N'),
		(u'ο', u'O'),
		(u'π', u'P'),
		(u'ρ', u'R'),
		(u'ϲ', u'S'),
		(u'τ', u'T'),
		(u'υ', u'U'),
		(u'ϝ', u'V'),
		(u'ω', u'W'),
		(u'χ', u'X'),
		(u'υ', u'Y'),
		(u'ζ', u'Z')
	)

	for i in range(0, len(betacodetuples)):
		mangledroman = re.sub(betacodetuples[i][0], betacodetuples[i][1], mangledroman)

	return mangledroman


def parselatininsidegreek(texttoclean):
	betaroman = texttoclean.group(0)
	uniroman = romanswapper(betaroman)
	# print(betagreek, unigreek)
	return uniroman


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
		('(ῥ|Ῥ)', 'ρ'),
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
		('(ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|\u1f75|ἠ|ἡ|ἦ|ἧ)', 'η'),
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

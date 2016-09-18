from builder.parsers.betacode_to_unicode import *

#
# lexica parser helpers
#

def gr1betaconverter(convertme):
	"""
	sadly these are necessary because the core converter is not ready for match groups with these numbers
	:param convertme:
	:return:
	"""
	betagreek = convertme.group(1)
	unigreek = replacegreekbetacode(betagreek.upper())
	return unigreek


def gr2betaconverter(texttoclean):
	# because the lsj betacode greek is lowercase...
	betagreek = texttoclean.group(2).upper()
	unigreek = replacegreekbetacode(betagreek)
	unigreek = texttoclean.group(1)+unigreek+texttoclean.group(3)
	# print(betagreek, unigreek)
	return unigreek


def gr3betaconverter(texttoclean):
	# because their greek is lowercase...
	betagreek = texttoclean.group(2).upper()
	unigreek = replacegreekbetacode(betagreek)
	unigreek = texttoclean.group(1)+unigreek+texttoclean.group(3)
	# print(betagreek, unigreek)
	return unigreek


def stripaccents(greek):
	"""
	deaccentuate greek characters
	:param greek:
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
		('(ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|ή|ἡ|ἦ)', 'η'),
		('(ᾨ|ᾩ|ᾪ|ᾫ|ᾬ|ᾭ|ᾮ|ᾯ|Ὠ|Ὡ|Ὢ|Ὣ|Ὤ|Ὥ|Ὦ|Ὧ)', 'Ω'),
		('(Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ)', 'Ο'),
		('(ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ)', 'Α'),
		('(Ἐ|Ἑ|Ἒ|Ἓ|Ἔ|Ἕ)', 'Ε'),
		('(Ἰ|Ἱ|Ἲ|Ἳ|Ἴ|Ἵ|Ἶ|Ἷ)', 'Ι'),
		('(Ὑ|Ὓ|Ὕ|Ὗ)', 'Υ'),
		('(ᾘ|ᾙ|ᾚ|ᾛ|ᾜ|ᾝ|ᾞ|ᾟ|Ἠ|Ἡ|Ἢ|Ἣ|Ἤ|Ἥ|Ἦ|Ἧ)', 'Η'),
	)

	for swap in range(0, len(substitutes)):
		greek = re.sub(substitutes[swap][0], substitutes[swap][1], greek)

	return greek


def greekvowellengths(texttoclean):
	"""
	the non-documented long-and-short codes
	this can/will confuse lexical lookups from greek passages
	:param texttoclean: [ttc <class '_sre.SRE_Match'>]
	:return:
	"""
	textualmarkuptuples = []

	ttc = texttoclean.group(0)

	betacodetuples = (
		(r'A_', u'\u1fb1'),
		(r'I_', u'\u1fd1'),
		(r'U_', u'\u1fe1'),
		(r'A\^', u'\u1fb0'),
		(r'I\^', u'\u1fd0'),
		(r'U\^', u'\u1fe0')
	)

	for i in range(0, len(betacodetuples)):
		textualmarkuptuples.append((betacodetuples[i][0], betacodetuples[i][1]))

	for reg in textualmarkuptuples:
		ttc = re.sub(reg[0], reg[1], ttc)

	return ttc


def latinvowellengths(texttoclean):
	"""
	now you have a new problem: matching vowel lengths when the TXT files do not have that information
	only send items this way whose transformation will prevent successful searches
	:param texttoclean:
	:return:
	"""
	textualmarkuptuples = []

	betacodetuples = (
		# capitals with breathings
		# did not implement subscripts (yet)
		(r'a_', r'ā'),
		(r'a\^', r'ă'),
		(r'e_', r'ē'),
		(r'e\^', r'ĕ'),
		(r'i_', r'ī'),
		(r'i\^', r'ĭ'),
		(r'o_', r'ō'),
		(r'o\^', r'ŏ'),
		(r'u_', r'ū'),
		(r'u\^', r'ŭ')
	)
	for i in range(0, len(betacodetuples)):
		textualmarkuptuples.append((betacodetuples[i][0], betacodetuples[i][1]))

	for reg in textualmarkuptuples:
		texttoclean = re.sub(reg[0], reg[1], texttoclean)

	return texttoclean


def betaconvertandsave(convertme):
	betagreek = convertme.group(1)
	notgreek = convertme.group(2)
	unigreek = replacegreekbetacode(betagreek.upper())+notgreek
	return unigreek



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
	betagreek = re.sub(r'[\^_]', r'', betagreek)
	unigreek = replacegreekbetacode(betagreek.upper())
	return unigreek

def gr2betaconverter(texttoclean):
	# because the lsj betacode greek is lowercase...
	betagreek = texttoclean.group(2).upper()
	unigreek = replacegreekbetacode(betagreek)
	unigreek = texttoclean.group(1)+unigreek+texttoclean.group(3)
	# print( texttoclean.group(1)+betagreek+texttoclean.group(3),'\n\t',unigreek)
	return unigreek


def gr3betaconverter(texttoclean):
	# because their greek is lowercase...
	betagreek = texttoclean.group(2).upper()
	unigreek = replacegreekbetacode(betagreek)
	unigreek = texttoclean.group(1)+unigreek+texttoclean.group(3)
	# print(betagreek, unigreek)
	return unigreek


def greekwithvowellengths(ttc):
	"""
	the non-documented long-and-short codes
	this can/will confuse lexical lookups from greek passages
	use the combining long/short so that you stand a chance of doing both accents and lengths
	:param texttoclean: [ttc <class '_sre.SRE_Match'>]
	:return:
	"""

	# ttc = match.group(2)

	if re.search(r'[a-z]',ttc) is not None:
		# this will keep things that have already been turned into greek from turning into upper case greek
		ttc = ttc.upper()
	else:
		# we are already greek: still, while we are here...
		# ttc = re.sub(r'\_', u'/\u0304', ttc)
		# ttc = re.sub(r'\^', u'/\u0306', ttc)
		pass
	
	ttc = re.sub(r'\^\/', u'/\u0306',ttc)
	ttc = re.sub(r'\_\/', u'/\u0304',ttc)
	ttc = re.sub(r'([AIU])\^',r'\1'+u'\u0306',ttc)
	ttc = re.sub(r'([AIU])\_', r'\1' + u'\u0304', ttc)

	ttc = replacegreekbetacode(ttc)

	return ttc


def latinvowellengths(texttoclean):
	"""
	now you have a new problem: matching vowel lengths when the TXT files do not have that information
	only send items this way whose transformation will prevent successful searches
	using the combining forms
	:param texttoclean:
	:return:
	"""
	textualmarkuptuples = []

	betacodetuples = (
		(r'a_', u'a\u0304'),
		(r'a\^', u'a\u0306'),
		(r'e_', u'e\u0304'),
		(r'e\^', u'e\u0306'),
		(r'i_', u'i\u0304'),
		(r'i\^', u'i\u0306'),
		(r'o_', u'o\u0304'),
		(r'o\^', u'o\u0306'),
		(r'u_', u'u\u0304'),
		(r'u\^', u'u\u0306'),
		(r'y\_', u'y\u0304'),
		(r'y\^', u'y\u0306')
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

#
# slated for removal
#

def oldgreekvowellengths(match):
	"""
	the non-documented long-and-short codes
	this can/will confuse lexical lookups from greek passages
	:param texttoclean: [ttc <class '_sre.SRE_Match'>]
	:return:
	"""
	textualmarkuptuples = []

	ttc = match.group(0)

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


def oldlatinvowellengths(texttoclean):
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
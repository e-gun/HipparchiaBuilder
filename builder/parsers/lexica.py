from builder.parsers.betacode_to_unicode import *

#
# lexica parser helpers
#

def greekwithoutvowellengths(betagreek):
	"""
	quick vowel len stripper that then sends you to greek conversion
	:param ttc:
	:return:
	"""

	betagreek = re.sub(r'[\^_]', r'', betagreek)
	unigreek = replacegreekbetacode(betagreek)
	
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


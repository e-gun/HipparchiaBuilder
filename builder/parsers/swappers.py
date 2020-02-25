# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


def highunicodetohex(highunicode):
	"""
	detransform the hexruns
	:param highunicode:
	:return:
	"""
	outvals = u'0123456789abcdef'
	invals = u'⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ'
	hexsequence = highunicode.translate(str.maketrans(invals, outvals))
	
	return hexsequence


def hutohxgrouper(matchgroup):
	x = matchgroup.group(0)
	x = highunicodetohex(x)
	
	return x


def hextohighunicode(twocharhexstring):
	"""
	detransform the hexruns
	:param twocharhexstring:
	:return:
	"""
	
	invals = u'0123456789abcdef'
	outvals = u'⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ'
	transformed = twocharhexstring.translate(str.maketrans(invals, outvals))
	
	return transformed


def bitswapchars(valuelist):
	"""
	remove the mask from a char
	:param valuelist:
	:return:
	"""

	asciival = ''
	for hv in valuelist:
		asciival += chr(int(hv, 16) & int('7f', 16))
	return asciival


def superscripterone(digitmatch):
	"""

	turn 1 into ¹ and 2 into ²

	:param digitmatch:
	:return:
	"""

	digit = digitmatch[1]

	invals = u'0123456789'
	outvals = u'⁰¹²³⁴⁵⁶⁷⁸⁹'
	transformed = digit.translate(str.maketrans(invals, outvals))

	return transformed


def superscripterzero(digitmatch):
	"""

	turn 1 into ¹ and 2 into ²

	:param digitmatch:
	:return:
	"""

	digit = digitmatch[0]

	invals = u'0123456789'
	outvals = u'⁰¹²³⁴⁵⁶⁷⁸⁹'
	transformed = digit.translate(str.maketrans(invals, outvals))

	return transformed


def forceregexsafevariants(text: str) -> str:
	"""

	get rid of small variants of '+', etc.
	:return:
	"""

	invals = "?*/!|=+%&:'(){}[]"
	outvals = "﹖﹡／﹗│﹦﹢﹪﹠﹕＇❨❩❴❵⟦⟧"

	try:
		cleantext = text.translate(str.maketrans(invals, outvals))
	except AttributeError:
		# did you send me an int instead of a string?
		cleantext = text

	return cleantext


def avoidregexsafevariants(text: str) -> str:
	"""

	get rid of small variants of '+', etc.
	:return:
	"""

	invals = "﹖﹡／﹗│﹦﹢﹪﹠﹕＇❨❩❴❵⟦⟧"
	outvals = "?*/!|=+%&:'(){}[]"

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext


def forcelunates(text: str) -> str:

	invals = "σςΣ"
	outvals = "ϲϲϹ"

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext

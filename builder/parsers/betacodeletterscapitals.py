# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-23
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import configparser

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')

try:
	regexmatch = re.Match
except AttributeError:
	# python < 3.7
	regexmatch = object()


def capitalletters(betacode: str) -> str:
	# needs to be done in order of length of regex string
	# capital + breathing + accent + adscript
	# '*)/W|ETO GOU=N KAI\ O( *DIONU/SIOS...'
	csga = re.compile(r'[*]\)\\([AHW])\|')
	crga = re.compile(r'[*]\(\\([AHW])\|')
	csaa = re.compile(r'[*]\)\/([AHW])\|')
	craa = re.compile(r'[*]\(\/([AHW])\|')
	csca = re.compile(r'[*]\(\=([AHW])\|')
	crca = re.compile(r'[*]\(\=([AHW])\|')

	unicode = re.sub(csga, capitalsmoothgraveadscript, betacode)
	unicode = re.sub(crga, capitalroughgraveadscript, unicode)
	unicode = re.sub(csaa, capitalsmoothacuteadscript, unicode)
	unicode = re.sub(craa, capitalroughacuteadscript, unicode)
	unicode = re.sub(csca, capitalsmoothcircumflexadscript, unicode)
	unicode = re.sub(crca, capitalroughcircumflexadscript, unicode)

	# capital + breathing + accent
	csg = re.compile(r'[*]\)\\([AEIOUHW])')
	crg = re.compile(r'[*]\(\\([AEIOUHW])')
	csa = re.compile(r'[*]\)\/([AEIOUHW])')
	cra = re.compile(r'[*]\(\/([AEIOUHW])')
	csc = re.compile(r'[*]\)\=([AEIOUHW])')
	crc = re.compile(r'[*]\(\=([AEIOUHW])')

	unicode = re.sub(csg, capitalsmoothgrave, unicode)
	unicode = re.sub(crg, capitalroughgrave, unicode)
	unicode = re.sub(csa, capitalsmoothacute, unicode)
	unicode = re.sub(cra, capitalroughacute, unicode)
	unicode = re.sub(csc, capitalsmoothcircumflex, unicode)
	unicode = re.sub(crc, capitalroughcircumflex, unicode)

	# capital + breathing
	cs = re.compile(r'[*]\)([AEIOUHWR])')
	cr = re.compile(r'[*]\(([AEIOUHWR])')

	unicode = re.sub(cs, capitalsmooth, unicode)
	unicode = re.sub(cr, capitalrough, unicode)

	# capital + accent
	cg = re.compile(r'[*]([AEIOUHW])\\')
	ca = re.compile(r'[*]([AEIOUHW])/')
	cc = re.compile(r'[*]([AEIOUHW])=')

	unicode = re.sub(cg, capitalgrave, unicode)
	unicode = re.sub(ca, capitalacute, unicode)
	unicode = re.sub(cc, capitalcircumflex, unicode)

	# capital + adscript
	cad = re.compile(r'[*]([AHW])\|')

	unicode = re.sub(cad, capitaladscript, unicode)

	# sigmas: all lunates

	if config['buildoptions']['lunate'] == 'n':
		sig = re.compile(r'[*]S([1-3]){0,1}')
		unicode = re.sub(sig, capitalsigmassubsitutes, unicode)
	else:
		sig = re.compile(r'[*]S[1-3]{0,1}')
		unicode = re.sub(sig, u'\u03f9', unicode)

	# capitals
	cap = re.compile(r'[*]([A-Z])')
	unicode = re.sub(cap, capitals, unicode)

	return unicode


def capitalsigmassubsitutes(match: regexmatch) -> str:
	substitutions = {
		3: u'\u03f9'
		}

	try:
		substitute = substitutions[match.group(1)]
	except KeyError:
		substitute = 'Σ'

	return substitute


# capital + breathing + accent + adscript
def capitalsmoothgraveadscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾊ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾚ',
		'W': u'ᾪ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalroughgraveadscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾋ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾛ',
		'W': u'ᾫ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalsmoothacuteadscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾌ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾜ',
		'W': u'ᾬ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalroughacuteadscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾍ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾝ',
		'W': u'ᾭ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalsmoothcircumflexadscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾎ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾞ',
		'W': u'ᾮ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalroughcircumflexadscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾏ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾟ',
		'W': u'ᾯ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# capital + breathing + accent
def capitalsmoothgrave(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἂ',
		'E': u'Ἒ',
		'I': u'Ἲ',
		'O': u'Ὂ',
		'U': u'',
		'H': u'Ἢ',
		'W': u'Ὢ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalroughgrave(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἃ',
		'E': u'Ἓ',
		'I': u'Ἳ',
		'O': u'Ὃ',
		'U': u'Ὓ',
		'H': u'Ἣ',
		'W': u'Ὣ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalsmoothacute(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἄ',
		'E': u'Ἔ',
		'I': u'Ἴ',
		'O': u'Ὄ',
		'U': u'',
		'H': u'Ἤ',
		'W': u'Ὤ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalroughacute(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἅ',
		'E': u'Ἕ',
		'I': u'Ἵ',
		'O': u'Ὅ',
		'U': u'Ὕ',
		'H': u'Ἥ',
		'W': u'Ὥ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalsmoothcircumflex(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἆ',
		'E': u'',
		'I': u'Ἶ',
		'O': u'',
		'U': u'',
		'H': u'Ἦ',
		'W': u'Ὦ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalroughcircumflex(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἇ',
		'E': u'',
		'I': u'Ἷ',
		'O': u'',
		'U': u'Ὗ',
		'H': u'Ἧ',
		'W': u'Ὧ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# capital + breathing
def capitalsmooth(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἀ',
		'E': u'Ἐ',
		'I': u'Ἰ',
		'O': u'Ὀ',
		'U': u'',
		'H': u'Ἠ',
		'W': u'Ὠ',
		'R': u'Ρ'
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitalrough(match: regexmatch) -> str:
	substitutions = {
		'A': u'Ἁ',
		'E': u'Ἑ',
		'I': u'Ἱ',
		'O': u'Ὁ',
		'U': u'Ὑ',
		'H': u'Ἡ',
		'W': u'Ὡ',
		'R': u'Ῥ'
	}

	substitute = substitutions[match.group(1)]

	return substitute


# capital + accent
def capitalgrave(match: regexmatch) -> str:
	"""

	this sort of thing will get requested, but it looks nuts:
		ΠΕΡῚ ἈΝΑΓΝΏϹΕΩϹ
		ΠΕΡῚ ΓΡΑΜΜΑΤΙΚΗ῀Ϲ

	just return the capitals instead

	NB, you are still going to get stuck with ΠΕΡΙ ἈΝΑΓΝΩϹΕΩϹ because you can't turn off
	the 'Ἀ' to handle this situation without producing chaos throughout every other text
	(unless you are willing to waste precious cycles in order to do some sort of BLANK+CAP+CAP check)

	:param match:
	:return:
	"""

	substitutions = {
		'A': u'Ὰ',
		'E': u'Ὲ',
		'I': u'Ὶ',
		'O': u'Ὸ',
		'U': u'Ὺ',
		'H': u'Ὴ',
		'W': u'Ὼ',
	}

	simplesubstitutions = {
		'A': u'Α',
		'E': u'Ε',
		'I': u'Ι',
		'O': u'Ο',
		'U': u'Υ',
		'H': u'Η',
		'W': u'Ω',
	}

	substitute = simplesubstitutions[match.group(1)]

	return substitute


def capitalacute(match: regexmatch) -> str:
	"""

	this sort of thing will get requested, but it looks nuts:
		ΠΕΡῚ ἈΝΑΓΝΏϹΕΩϹ
		ΠΕΡῚ ΓΡΑΜΜΑΤΙΚΗ῀Ϲ

	just return the capitals instead

	:param match:
	:return:
	"""

	substitutions = {
		'A': u'Ά',
		'E': u'Έ',
		'I': u'Ί',
		'O': u'Ό',
		'U': u'Ύ',
		'H': u'Ή',
		'W': u'Ώ',
		}

	simplesubstitutions = {
		'A': u'Α',
		'E': u'Ε',
		'I': u'Ι',
		'O': u'Ο',
		'U': u'Υ',
		'H': u'Η',
		'W': u'Ω',
	}

	substitute = simplesubstitutions[match.group(1)]

	return substitute

def capitalcircumflex(match: regexmatch) -> str:
	"""

	this sort of thing will get requested, but it looks nuts:
		ΠΕΡῚ ἈΝΑΓΝΏϹΕΩϹ
		ΠΕΡῚ ΓΡΑΜΜΑΤΙΚΗ῀Ϲ

	just return the capitals instead

	:param match:
	:return:
	"""

	substitutions = {
		'A': u'Α\u1fc0',
		'E': u'Ε\u1fc0',
		'I': u'Ι\u1fc0',
		'O': u'Ο\u1fc0',
		'U': u'Υ\u1fc0',
		'H': u'Η\u1fc0',  # there is no capital eta with a circumflex; but TLG0063 will ask for *G*R*A*M*M*A*T*I*K*H=*S3 anyway
		'W': u'Ω\u1fc0',
	}

	simplesubstitutions = {
		'A': u'Α',
		'E': u'Ε',
		'I': u'Ι',
		'O': u'Ο',
		'U': u'Υ',
		'H': u'Η',
		'W': u'Ω',
	}

	substitute = simplesubstitutions[match.group(1)]

	return substitute


def capitaladscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾼ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ῌ',
		'W': u'ῼ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def capitals(match: regexmatch) -> str:
	substitutions = {
		'A': u'Α',
		'B': u'Β',
		'C': u'Ξ',
		'D': u'Δ',
		'E': u'Ε',
		'F': u'Φ',
		'G': u'Γ',
		'H': u'Η',
		'I': u'Ι',
		'J': u'⒣',
		# need the unused J because Roman characters are present; see IG I3 1-2 [1-500 501-1517]) - 370: fr d-f, line 69 - Jέ[κτει Jεμέραι -- ⒣εμέραι is what we want
		'K': u'Κ',
		'L': u'Λ',
		'M': u'Μ',
		'N': u'Ν',
		'O': u'Ο',
		'P': u'Π',
		'Q': u'Θ',
		'R': u'Ρ',
		'S': u'Ϲ',
		'T': u'Τ',
		'U': u'Υ',
		'V': u'Ϝ',
		'W': u'Ω',
		'X': u'Χ',
		'Y': u'Ψ',
		'Z': u'Ζ'
	}

	substitute = substitutions[match.group(1)]

	return substitute

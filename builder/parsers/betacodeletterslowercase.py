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


def lowercaseletters(betacode: str) -> str:
	"""
	swap betacode for unicode values

	notice the problem that we can get with the papyri:
		μεμίϲθ(ωμαἰ ὡϲ πρόκ(ἐιται
		vs
		μεμίϲθ(ωμαι) ὡϲ πρόκ(ε)ιται

	the betacode knows how to prevent this:
		MEMI/SQ[1WMAI]1 W(S PRO/K[1E]1ITAI

	so you can't convert '[1' and ']1' into '(' and ')' before you get here

	:param betacode:
	:return:
	"""
	# needs to be done in order of length of regex string
	# otherwise 4-element items will disappear in the wake of doing all of the 3s, etc.

	# roman numeral problem:
	#   (XI) will wind up as (Xἰ
	#   IG II(2) 891 --> IG Iἱ2) 891.1–3
	# very had to fix because a lookahead of (?!\s) will ruin εἰ

	# lowercase + breathing + accent + subscript
	lsga = re.compile(r'([AHW])\)\\\|')
	lrga = re.compile(r'([AHW])\(\\\|')
	lsaa = re.compile(r'([AHW])\)\/\|')
	lraa = re.compile(r'([AHW])\(\/\|')
	lsca = re.compile(r'([AHW])\)\=\|')
	lrca = re.compile(r'([AHW])\(\=\|')

	unicode = re.sub(lsga, lowercasesmoothgravesubscript, betacode)
	unicode = re.sub(lrga, lowercaseroughgravesubscript, unicode)
	unicode = re.sub(lsaa, lowercasesmoothacutesubscript, unicode)
	unicode = re.sub(lraa, lowercaseroughacutesubscript, unicode)
	unicode = re.sub(lsca, lowercasesmoothcircumflexsubscript, unicode)
	unicode = re.sub(lrca, lowercaseroughcircumflexsubscript, unicode)

	# lowercase + breathing + accent
	lsg = re.compile(r'([AEIOUHW])\)\\')
	lrg = re.compile(r'([AEIOUHW])\(\\')
	lsa = re.compile(r'([AEIOUHW])\)\/')
	lra = re.compile(r'([AEIOUHW])\(\/')
	lsc = re.compile(r'([AEIOUHW])\)\=')
	lrc = re.compile(r'([AEIOUHW])\(\=')

	unicode = re.sub(lsg, lowercasesmoothgrave, unicode)
	unicode = re.sub(lrg, lowercaseroughgrave, unicode)
	unicode = re.sub(lsa, lowercasesmoothacute, unicode)
	unicode = re.sub(lra, lowercaseroughacute, unicode)
	unicode = re.sub(lsc, lowercasesmoothcircumflex, unicode)
	unicode = re.sub(lrc, lowercaseroughcircumflex, unicode)

	# lowercase + accent + subscript
	lga = re.compile(r'([AHW])\\\|')
	laa = re.compile(r'([AHW])\/\|')
	lca = re.compile(r'([AHW])\=\|')

	unicode = re.sub(lga, lowercasegravesub, unicode)
	unicode = re.sub(laa, lowercaseacutedsub, unicode)
	unicode = re.sub(lca, lowercasesircumflexsub, unicode)

	# lowercase + breathing + subscript
	lss = re.compile(r'([AHW])\)\|')
	lrs = re.compile(r'([AHW])\(\|')

	unicode = re.sub(lss, lowercasesmoothsub, unicode)
	unicode = re.sub(lrs, lowercaseroughsub, unicode)

	# lowercase + accent + diaresis
	lgd = re.compile(r'([IU])\\\+')
	lad = re.compile(r'([IU])\/\+')
	lcd = re.compile(r'([U])\=\+')

	unicode = re.sub(lgd, lowercasegravediaresis, unicode)
	unicode = re.sub(lad, lowercaseacutediaresis, unicode)
	unicode = re.sub(lcd, lowercasesircumflexdiaresis, unicode)

	# lowercase + breathing
	ls = re.compile(r'([AEIOUHWR])\)')
	# IG II(2) 891 --> IG Iἱ2) 891.1–3
	lr = re.compile(r'([AEIOUHWR])\((?!\d)')

	unicode = re.sub(ls, lowercasesmooth, unicode)
	unicode = re.sub(lr, lowercaserough, unicode)

	# lowercase + accent
	lg = re.compile(r'([AEIOUHW])\\')
	la = re.compile(r'([AEIOUHW])\/')
	lc = re.compile(r'([AEIOUHW])\=')

	unicode = re.sub(lg, lowercasegrave, unicode)
	unicode = re.sub(la, lowercaseacute, unicode)
	unicode = re.sub(lc, lowercascircumflex, unicode)

	# lowercase + diaresis
	ld = re.compile(r'([IU])\+')

	unicode = re.sub(ld, lowercasediaresis, unicode)

	# lowercase + subscript
	lad = re.compile(r'([AHW])\|')

	unicode = re.sub(lad, lowercasesubscript, unicode)

	# lowercase + vowel length
	# perseus' LSJ: vowel+_ for long-vowel and vowel+^ for short
	# short = re.compile(r'[AIU]\^')
	# long = re.compile(r'[AIU]_')

	if config['buildoptions']['lunate'] == 'n':
		sig = re.compile(r'S([1-3]){0,1}')
		unicode = re.sub(sig, lowercasesigmassubsitutes, unicode)
		# look out for ς’ instead of σ’
		straypunct = r'\<\>\{\}\[\]\(\)⟨⟩₍₎\.\?\!⌉⎜͙✳※¶§͜﹖→𐄂𝕔;:ˈ＇,‚‛‘“”„·‧∣'
		combininglowerdot = u'\u0323'
		boundaries = r'([' + combininglowerdot + straypunct + '\s]|$)'
		terminalsigma = re.compile(r'σ'+boundaries)
		unicode = re.sub(terminalsigma, r'ς\1', unicode)
	else:
		sig = re.compile(r'S[1-3]{0,1}')
		unicode = re.sub(sig, u'ϲ', unicode)

	# lowercases
	lap = re.compile(r'([A-Z])')
	unicode = re.sub(lap, lowercases, unicode)

	return unicode


def lowercasesigmassubsitutes(match: regexmatch) -> str:
	substitutions = {
		1: u'σ',
		2: u'ς',
		3: u'ϲ'
		}

	try:
		substitute = substitutions[match.group(1)]
	except:
		substitute = 'σ'

	return substitute


# lowercase + breathing + accent + subscript
def lowercasesmoothgravesubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾂ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾒ',
		'W': u'ᾢ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughgravesubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾃ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾓ',
		'W': u'ᾣ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercasesmoothacutesubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾄ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾔ',
		'W': u'ᾤ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughacutesubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾅ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾕ',
		'W': u'ᾥ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercasesmoothcircumflexsubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾆ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾖ',
		'W': u'ᾦ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughcircumflexsubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾇ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾗ',
		'W': u'ᾧ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + breathing + accent
def lowercasesmoothgrave(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἂ',
		'E': u'ἒ',
		'I': u'ἲ',
		'O': u'ὂ',
		'U': u'ὒ',
		'H': u'ἢ',
		'W': u'ὢ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughgrave(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἃ',
		'E': u'ἓ',
		'I': u'ἳ',
		'O': u'ὃ',
		'U': u'ὓ',
		'H': u'ἣ',
		'W': u'ὣ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercasesmoothacute(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἄ',
		'E': u'ἔ',
		'I': u'ἴ',
		'O': u'ὄ',
		'U': u'ὔ',
		'H': u'ἤ',
		'W': u'ὤ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughacute(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἅ',
		'E': u'ἕ',
		'I': u'ἵ',
		'O': u'ὅ',
		'U': u'ὕ',
		'H': u'ἥ',
		'W': u'ὥ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercasesmoothcircumflex(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἆ',
		'E': u'ἐ͂',  # IG 104.27: AI)/TIOS E)=I FO/NO --> αἴτιος ἐ͂ι φόνο [U1f10 + U0342]
		'I': u'ἶ',
		'O': u'ὀ͂',  # IG 127.36: E)PAINE/SAI W(S O)=SIN A)NDRA/SIN --> ἐπαινέσαι ὡς ὀ͂σιν ἀνδράσιν [U1f40 + U0342]
		'U': u'ὖ',
		'H': u'ἦ',
		'W': u'ὦ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughcircumflex(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἇ',
		'E': u'ἑ͂',  # IG: TE=S BOLE=S E(=I
		'I': u'ἷ',
		'O': u'ὁ͂',  # IG: PE]RI\ DE\ O(=[N !]DIK
		'U': u'ὗ',
		'H': u'ἧ',
		'W': u'ὧ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + accent + subscript
def lowercasegravesub(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾲ',
		'H': u'ῂ',
		'W': u'ῲ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseacutedsub(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾴ',
		'H': u'ῄ',
		'W': u'ῴ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercasesircumflexsub(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾷ',
		'H': u'ῇ',
		'W': u'ῷ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + breathing + subscript

def lowercasesmoothsub(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾀ',
		'H': u'ᾐ',
		'W': u'ᾠ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseroughsub(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾁ',
		'H': u'ᾑ',
		'W': u'ᾡ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + accent + diaresis
def lowercasegravediaresis(match: regexmatch) -> str:
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ῒ',
		'O': u'',
		'U': u'ῢ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseacutediaresis(match: regexmatch) -> str:
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ΐ',
		'O': u'',
		'U': u'ΰ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercasesircumflexdiaresis(match: regexmatch) -> str:
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'ῧ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + breathing
def lowercasesmooth(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἀ',
		'E': u'ἐ',
		'I': u'ἰ',
		'O': u'ὀ',
		'U': u'ὐ',
		'H': u'ἠ',
		'W': u'ὠ',
		'R': u'ῤ'
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaserough(match: regexmatch) -> str:
	substitutions = {
		'A': u'ἁ',
		'E': u'ἑ',
		'I': u'ἱ',
		'O': u'ὁ',
		'U': u'ὑ',
		'H': u'ἡ',
		'W': u'ὡ',
		'R': u'ῥ'
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + accent
def lowercasegrave(match: regexmatch) -> str:
	substitutions = {
		'A': u'ὰ',
		'E': u'ὲ',
		'I': u'ὶ',
		'O': u'ὸ',
		'U': u'ὺ',
		'H': u'ὴ',
		'W': u'ὼ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercaseacute(match: regexmatch) -> str:
	substitutions = {
		'A': u'ά',
		'E': u'έ',
		'I': u'ί',
		'O': u'ό',
		'U': u'ύ',
		'H': u'ή',
		'W': u'ώ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


def lowercascircumflex(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾶ',
		'E': u'\u03b5\u0342',
		# epsilon-for-eta; see something like 1-500 501-1517, Attica (IG I3 1-2 [1-500 501-1517]) - 370: fr d-f, line 75
		'I': u'ῖ',
		'O': u'\u03bf\u0342',
		# to avoid blanking in a case of omicron-for-omega;  Attica (IG I3 1-2 [1-500 501-1517]) - 342: line 12; χρυϲο͂ν
		'U': u'ῦ',
		'H': u'ῆ',
		'W': u'ῶ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + diaresis
def lowercasediaresis(match: regexmatch) -> str:
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ϊ',
		'O': u'',
		'U': u'ϋ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercase + subscript
def lowercasesubscript(match: regexmatch) -> str:
	substitutions = {
		'A': u'ᾳ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ῃ',
		'W': u'ῳ',
	}

	substitute = substitutions[match.group(1)]

	return substitute


# lowercases
def lowercases(match: regexmatch) -> str:
	substitutions = {
		'A': u'α',
		'B': u'β',
		'C': u'ξ',
		'D': u'δ',
		'E': u'ε',
		'F': u'φ',
		'G': u'γ',
		'H': u'η',
		'I': u'ι',
		'J': u'J',
		'K': u'κ',
		'L': u'λ',
		'M': u'μ',
		'N': u'ν',
		'O': u'ο',
		'P': u'π',
		'Q': u'θ',
		'R': u'ρ',
		'S': u'ϲ',
		'T': u'τ',
		'U': u'υ',
		'V': u'ϝ',
		'W': u'ω',
		'X': u'χ',
		'Y': u'ψ',
		'Z': u'ζ'
	}

	substitute = substitutions[match.group(0)]

	return substitute

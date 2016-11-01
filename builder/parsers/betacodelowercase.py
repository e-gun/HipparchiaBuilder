# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re


def lowercaseletters(betacode):
	"""
	swap betacode for unicode values
	:param betacode:
	:return:
	"""
	# needs to be done in order of length of regex string
	# otherwise 4-element items will disappear in the wake of doing all of the 3s, etc.
	
	# roman numeral problem: (XI) will wind up as (Xἰ
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
	lr = re.compile(r'([AEIOUHWR])\(')
	
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
	
	# sigmas: all lunates
	sig = re.compile(r'S[1-3]{0,1}')
	unicode = re.sub(sig, u'ϲ', unicode)
	
	# lowercases
	lap = re.compile(r'([A-Z])')
	unicode = re.sub(lap, lowercases, unicode)
	
	return unicode


# lowercase + breathing + accent + subscript
def lowercasesmoothgravesubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾂ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾒ',
		'W': u'ᾢ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughgravesubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾃ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾓ',
		'W': u'ᾣ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercasesmoothacutesubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾄ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾔ',
		'W': u'ᾤ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughacutesubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾅ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾕ',
		'W': u'ᾥ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercasesmoothcircumflexsubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾆ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾖ',
		'W': u'ᾦ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughcircumflexsubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾇ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾗ',
		'W': u'ᾧ',
	}
	
	substitute = substitutions[val]
	
	return substitute


# lowercase + breathing + accent
def lowercasesmoothgrave(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ἂ',
		'E': u'ἒ',
		'I': u'ἲ',
		'O': u'ὂ',
		'U': u'ὒ',
		'H': u'ἢ',
		'W': u'ὢ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughgrave(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ἃ',
		'E': u'ἓ',
		'I': u'ἳ',
		'O': u'ὃ',
		'U': u'ὓ',
		'H': u'ἣ',
		'W': u'ὣ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercasesmoothacute(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ἄ',
		'E': u'ἔ',
		'I': u'ἴ',
		'O': u'ὄ',
		'U': u'ὔ',
		'H': u'ἤ',
		'W': u'ὤ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughacute(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ἅ',
		'E': u'ἕ',
		'I': u'ἵ',
		'O': u'ὅ',
		'U': u'ὕ',
		'H': u'ἥ',
		'W': u'ὥ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercasesmoothcircumflex(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ἆ',
		'E': u'',
		'I': u'ἶ',
		'O': u'',
		'U': u'ὖ',
		'H': u'ἦ',
		'W': u'ὦ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughcircumflex(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ἇ',
		'E': u'',
		'I': u'ἷ',
		'O': u'',
		'U': u'ὗ',
		'H': u'ἧ',
		'W': u'ὧ',
	}
	
	substitute = substitutions[val]
	
	return substitute


# lowercase + accent + subscript
def lowercasegravesub(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾲ',
		'H': u'ῂ',
		'W': u'ῲ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseacutedsub(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾴ',
		'H': u'ῄ',
		'W': u'ῴ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercasesircumflexsub(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾷ',
		'H': u'ῇ',
		'W': u'ῷ',
	}
	
	substitute = substitutions[val]
	
	return substitute

# lowercase + breathing + subscript

def lowercasesmoothsub(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾀ',
		'H': u'ᾐ',
		'W': u'ᾠ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseroughsub(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾁ',
		'H': u'ᾑ',
		'W': u'ᾡ',
	}
	
	substitute = substitutions[val]
	
	return substitute


# lowercase + accent + diaresis
def lowercasegravediaresis(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ῒ',
		'O': u'',
		'U': u'ῢ',
		'H': u'',
		'W': u'',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseacutediaresis(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ΐ',
		'O': u'',
		'U': u'',
		'H': u'ΰ',
		'W': u'',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercasesircumflexdiaresis(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'ῧ',
		'H': u'',
		'W': u'',
	}
	
	substitute = substitutions[val]
	
	return substitute

# lowercase + breathing
def lowercasesmooth(match):
	val = match.group(1)
	
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
	
	substitute = substitutions[val]
	
	return substitute


def lowercaserough(match):
	val = match.group(1)
	
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
	
	substitute = substitutions[val]
	
	return substitute


# lowercase + accent
def lowercasegrave(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ὰ',
		'E': u'ὲ',
		'I': u'ὶ',
		'O': u'ὸ',
		'U': u'ὺ',
		'H': u'ὴ',
		'W': u'ὼ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercaseacute(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ά',
		'E': u'έ',
		'I': u'ί',
		'O': u'ό',
		'U': u'ύ',
		'H': u'ή',
		'W': u'ώ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def lowercascircumflex(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾶ',
		'E': u'',
		'I': u'ῖ',
		'O': u'',
		'U': u'ῦ',
		'H': u'ῆ',
		'W': u'ῶ',
	}
	
	substitute = substitutions[val]
	
	return substitute


# lowercase + diaresis
def lowercasediaresis(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ϊ',
		'O': u'',
		'U': u'ϋ',
		'H': u'',
		'W': u'',
	}
	
	substitute = substitutions[val]
	
	return substitute

# lowercase + subscript
def lowercasesubscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾳ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ῃ',
		'W': u'ῳ',
	}

	substitute = substitutions[val]
	
	return substitute


# lowercases
def lowercases(match):
	val = match.group(0)
	
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
	
	substitute = substitutions[val]
	
	return substitute


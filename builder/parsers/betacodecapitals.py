# -*- coding: utf-8 -*-
import re


def capitalletters(betacode):
	# needs to be done in order of length of regex string
	# capital + breathing + accent + adscript
	csga = re.compile(r'[*]\)\\\|([AHW])')
	crga = re.compile(r'[*]\(\\\|([AHW])')
	csaa = re.compile(r'[*]\)\/\|([AHW])')
	craa = re.compile(r'[*]\(\/\|([AHW])')
	csca = re.compile(r'[*]\(\=\|([AHW])')
	crca = re.compile(r'[*]\(\=\|([AHW])')
	
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
	cg = re.compile(r'[*]\\([AEIOUHW])')
	ca = re.compile(r'[*]\/([AEIOUHW])')
	
	unicode = re.sub(cg, capitalgrave, unicode)
	unicode = re.sub(ca, capitalacute, unicode)
	
	# capital + adscript
	cad = re.compile(r'[*]\|([AHW])')
	
	unicode = re.sub(cad, capitaladscript, unicode)
	
	# sigmas: all lunates
	sig = re.compile(r'[*]S[1-3]{0,1}')
	unicode = re.sub(sig, u'\u03f9', unicode)
	
	# capitals
	cap = re.compile(r'[*]([A-Z])')
	unicode = re.sub(cap, capitals, unicode)
	
	return unicode


# capital + breathing + accent + adscript
def capitalsmoothgraveadscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾊ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾚ',
		'W': u'ᾪ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalroughgraveadscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾋ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾛ',
		'W': u'ᾫ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalsmoothacuteadscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾌ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾜ',
		'W': u'ᾬ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalroughacuteadscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾍ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾝ',
		'W': u'ᾭ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalsmoothcircumflexadscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾎ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾞ',
		'W': u'ᾮ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalroughcircumflexadscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾏ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾟ',
		'W': u'ᾯ',
	}
	
	substitute = substitutions[val]
	
	return substitute


# capital + breathing + accent
def capitalsmoothgrave(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ἂ',
		'E': u'Ἒ',
		'I': u'Ἲ',
		'O': u'Ὂ',
		'U': u'',
		'H': u'Ἢ',
		'W': u'Ὢ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalroughgrave(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ἃ',
		'E': u'Ἓ',
		'I': u'Ἳ',
		'O': u'Ὃ',
		'U': u'Ὓ',
		'H': u'Ἣ',
		'W': u'Ὣ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalsmoothacute(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ἄ',
		'E': u'Ἔ',
		'I': u'Ἴ',
		'O': u'Ὄ',
		'U': u'',
		'H': u'Ἤ',
		'W': u'Ὤ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalroughacute(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ἅ',
		'E': u'Ἕ',
		'I': u'Ἵ',
		'O': u'Ὅ',
		'U': u'Ὕ',
		'H': u'Ἥ',
		'W': u'Ὥ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalsmoothcircumflex(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ἆ',
		'E': u'',
		'I': u'Ἶ',
		'O': u'',
		'U': u'',
		'H': u'Ἦ',
		'W': u'Ὦ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalroughcircumflex(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ἇ',
		'E': u'',
		'I': u'Ἷ',
		'O': u'',
		'U': u'Ὗ',
		'H': u'Ἧ',
		'W': u'Ὧ',
	}
	
	substitute = substitutions[val]
	
	return substitute

# capital + breathing
def capitalsmooth(match):
	val = match.group(1)
	
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
	
	substitute = substitutions[val]
	
	return substitute


def capitalrough(match):
	val = match.group(1)
	
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
	
	substitute = substitutions[val]
	
	return substitute


# capital + accent
def capitalgrave(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ὰ',
		'E': u'Ὲ',
		'I': u'Ὶ',
		'O': u'Ὸ',
		'U': u'Ὺ',
		'H': u'Ὴ',
		'W': u'Ὼ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitalacute(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'Ά',
		'E': u'Έ',
		'I': u'Ί',
		'O': u'Ό',
		'U': u'Ύ',
		'H': u'Ή',
		'W': u'Ώ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitaladscript(match):
	val = match.group(1)
	
	substitutions = {
		'A': u'ᾼ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ῌ',
		'W': u'ῼ',
	}
	
	substitute = substitutions[val]
	
	return substitute


def capitals(match):
	val = match.group(1)
	
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
		'J': u'J', # need the unused J because Roman characters are present
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
	
	substitute = substitutions[val]
	
	return substitute

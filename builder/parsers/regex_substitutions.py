# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import configparser
import re

from builder.parsers.betacodeescapedcharacters import percentsubstitutes, quotesubstitutesa, quotesubstitutesb
from builder.parsers.betacodefontshifts import latinauthorandshiftparser
from builder.parsers.citation_builder import citationbuilder
from builder.parsers.swappers import highunicodetohex, hutohxgrouper, hextohighunicode, bitswapchars

config = configparser.ConfigParser()
config.read('config.ini')

if config['buildoptions']['warnings'] == 'y':
	warnings = True
else:
	warnings = False


# [nb: some regex happens in db.py as prep for loading]


def earlybirdsubstitutions(texttoclean):
	"""

	try to get out in front of some of the trickiest bits
	note that you can't use quotation marks in here

	:param texttoclean:
	:return:
	"""

	if config['buildoptions']['smartsinglequotes'] == 'y':
		# 'smart' single quotes; but this produces an intial elision problem for something like ’κείνων which will be ‘κείνων instead
		supplement = [
			(r'\s\'', r' ‘'),
			(r'\'( |\.|,|;)', r'’\1')
			]
	else:
		# single quotes are a problem because OTOH, we have elision at the first letter of the word and, OTOH, we have plain old quotes
		# full width variant for now
		supplement = [(r'\'', r'＇')]

	betacodetuples = [
		(r'<(?!\d)',r'‹'),  # '<': this one is super-dangerous: triple-check
		(r'>(?!\d)', u'›'),  # '>': this one is super-dangerous: triple-check
		(r'_', u' \u2014 '),  # doing this without spaces was producing problems with giant 'hyphenated' line ends
		(r'\\\{', r'❴'),
		(r'\\\}', r'❵'),

		# the papyri exposed an interesting problem with '?'
		# let's try to deal with this at earlybirdsubstitutions() because if you let '?' turn into '\u0323' it seems impossible to undo that
		#
		# many papyrus lines start like: '[ &c ? ]$' (cf. '[ &c ? $TO\ PRA=]GMA')
		# this will end up as: '[ <hmu_latin_normal>c ̣ ]</hmu_latin_normal>'
		# the space after '?' is not always there
		# 	'[ &c ?]$! KEKEI/NHKA DI/KH PERI\ U(/BREWS [4!!!!!!!!!![ &c ?]4 ]$'
		# also get a version of the pattern that does not have '[' early because we are not starting a line:
		#	'&{10m4}10 [ c ? ]$IASNI#80 *)EZIKEH\ M[ARTURW= &c ? ]$'
		# this one also fails to have '&c' because the '&' came earlier
		# here's hoping there is no other way to achieve this pattern...
		(r'&c\s\?(.*?)\$', r'&c ﹖\1$'), # the question mark needs to be preserved, so we substitute a small question mark
		(r'\[\sc\s\?(.*?)\$', r'[ c ﹖\1$'), # try to catch '&{10m4}10 [ c ? ]$I' without doing any damage
		(r'&\?(.*?)\](.*?)\$',r'&﹖\1]\2$') # some stray lonely '?' cases remain
	]

	betacodetuples += supplement

	for i in range(0, len(betacodetuples)):
		texttoclean = re.sub(betacodetuples[i][0], betacodetuples[i][1], texttoclean)

	return texttoclean


def replacequotationmarks(texttoclean):
	"""
	purge " markup
	:param texttoclean:
	:return:
	"""
	quotes = re.compile(r'\"(\d{1,2})')
	texttoclean = re.sub(quotes, quotesubstitutesa, texttoclean)
	texttoclean = re.sub(r'\"(.*?)\"', r'“\1”', texttoclean)

	quotes = re.compile(r'QUOTE(\d)(.*?)QUOTE(\d)')
	texttoclean = re.sub(quotes, quotesubstitutesb, texttoclean)

	return texttoclean


def latindiacriticals(texttoclean):
	"""

	find text with latin diacritical marks
	then send it to the cleaners

	:param texttoclean:
	:return:
	"""

	finder = re.compile(r'[aeiouyAEIOUV][\+\\=/]')

	texttoclean = re.sub(finder, latinsubstitutes, texttoclean)

	return texttoclean


def latinsubstitutes(matchgroup):

	val = matchgroup.group(0)

	substitues = {
		'a/': u'\u00e1',
		'e/': u'\u00e9',
		'i/': u'\u00ed',
		'o/': u'\u00f3',
		'u/': u'\u00fa',
		'y/': u'\u00fd',
		'A/': u'\u00c1',
		'E/': u'\u00c9',
		'I/': u'\u00cd',
		'O/': u'\u00d3',
		'U/': u'\u00da',
		'V/': u'\u00da',
		'a+': 'ä',
		'A+': 'Ä',
		'e+': 'ë',
		'E+': 'Ë',
		'i+': 'ï',
		'I+': 'Ï',
		'o+': 'ö',
		'O+': 'Ö',
		'u+': 'ü',
		'U+': 'Ü',
		'a=': 'â',
		'A=': 'Â',
		'e=': 'ê',
		'E=': 'Ê',
		'i=': 'î',
		'I=': 'Î',
		'o=': 'ô',
		'O=': 'Ô',
		'u=': 'û',
		'U=': 'Û',
		'V=': 'Û',
		'a\\': 'à',
		'A\\': 'À',
		'e\\': 'è',
		'E\\': 'È',
		'i\\': 'ì',
		'I\\': 'Ì',
		'o\\': 'ò',
		'O\\': 'Ò',
		'u\\': 'ù',
		'U\\': 'Ù',
		'V\\': 'Ù'
	}

	try:
		substitute = substitues[val]
	except KeyError:
		substitute = ''

	return substitute


def lastsecondsubsitutions(texttoclean):
	"""
	regex work that for some reason or other needs to be put off until the very last second
	:param texttoclean:
	:return:
	"""
	betacodetuples = (
		# a format shift code like '[3' if followed by a number that is supposed to print has an intervening ` to stop the TLG parser
		# if you do this prematurely you will generate spurious codes by joining numbers that should be kept apart
		(r'`(\d)',r'\1'),
		(r'\\\(',r'('),
		(r'\\\)', r')'),
	)

	for i in range(0, len(betacodetuples)):
		texttoclean = re.sub(betacodetuples[i][0], betacodetuples[i][1], texttoclean)

	if config['buildoptions']['simplifybrackets'] != 'n':
		tosimplify = re.compile(r'[❨❩❴❵⟦⟧⟪⟫《》‹›⦅⦆₍₎]')
		texttoclean = re.sub(tosimplify, bracketsimplifier, texttoclean)

	# combining breve is misplaced
	texttoclean = re.sub(r'(.)(\u035c)', r'\2\1', texttoclean)

	# misbalanced punctuation in something like ’αὐλῶνεϲ‘: a trivial issue that will add a lot of time to builds if you do all of the variants
	# easy enough to turn this off

	if config['buildoptions']['smartsinglequotes'] == 'y':
		# if you enable the next a problem arises with initial elision: ‘κείνων instead of ’κείνων
		texttoclean = re.sub(r'(\W)’(\w)', r'\1‘\2', texttoclean)
		# now we try to undo the mess we just created by looking for vowel+space+quote+char
		# the assumption is that an actual quotation will have a punctuation mark that will invalidate this check
		# Latin is a mess, and you will get too many bad mathces: De uerbo ’quiesco’
		# but the following will still be wrong: τὰ ϲπέρματα· ‘κείνων γὰρ
		# it is unfixable? how do I know that a proper quote did not just start?
		previousendswithvowel = re.compile(r'([aeiouαειουηωᾳῃῳᾶῖῦῆῶάέίόύήώὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ]\s)‘(\w)')
		texttoclean = re.sub(previousendswithvowel, r'\1’\2', texttoclean)
	resized = re.compile(r'[﹖﹡／﹗│﹦﹢﹪﹠﹕＇]')
	texttoclean = re.sub(resized, sizeshifter, texttoclean)
	texttoclean = re.sub(r'([\w\.,;])‘([\W])', r'\1’\2', texttoclean)
	texttoclean = re.sub(r'(\W)”(\w)', r'\1“\2', texttoclean)
	texttoclean = re.sub(r'([\w\.,;])“([\W])', r'\1”\2', texttoclean)
	# ['‵', '′'], # reversed prime and prime (for later fixing)
	texttoclean = re.sub(r'([\w\.,])‵([\W])', r'\1′\2', texttoclean)
	texttoclean = re.sub(r'(\W)′(\w)', r'\1‵\2', texttoclean)
	texttoclean = re.sub(r'‵', r'‘', texttoclean)
	texttoclean = re.sub(r'′', r'’', texttoclean)

	return texttoclean


def sizeshifter(match):
	"""

	swap a little and (﹠) for a big one (&), etc.

	:param match:
	:return:
	"""

	val = match.group(0)

	substitutions = {
		'﹖': '?',
		'﹡': '*',
		'／': '/',
		'﹗': '!',
		'│': '|',
		'﹦': '=',
		'﹢': '+',
		'﹪': '%',
		'﹠': '&',
		'﹕': ':',
		'＇': u'\u0027',  # simple apostrophe
		}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = ''

	return substitute


def bracketsimplifier(match):
	"""

	lots of brackets are out there; converge upon a smaller set

	note that most of them were chosen to avoid confusing the parser, so restoring these puts us
	more in line with the betacode manual

	comment some of these out to restore biodiversity

	:param matchgroup:
	:return:
	"""

	val = match.group(0)

	substitutions = {
		'❨': '(',
		'❩': ')',
		'❴': '{',
		'❵': '}',
		'⟦': '[',
		'⟧': ']',
		'⦅': '(',
		'⦆': ')',
		'⸨': '(',
		'⸩': ')',
		# '₍': '(', # '[11' (enclose missing letter dots (!), expressing doubt whether there is a letter there at all)
		# '₎': ')', # '11]'
		# various angled brackets all set to 'mathematical left/right angle bracket' (u+27e8, u+27e9)
		# alternately one could consider small versions instead of the full-sized versions (u+fe64, u+fe65)
		# the main issue is that '<' and '>' are being kept out of the text data because of the HTML problem
		# '⟪': '⟨', # but these are all asserted in the betacode
		# '⟫': '⟩', # but these are all asserted in the betacode
		'《': '⟨',
		'》': '⟩',
		'‹': '⟨',
		'›': '⟩'
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = val

	return substitute


def swapregexbrackets(match):
	"""

	get rid of [](){}

	insert safe substitutes

	currently unused

	:param match:
	:return:
	"""

	val = match.group(0)

	substitutions = {
		'(': '❨',
		')': '❩',
		'{': '❴',
		'}': '❵',
		'[': '⟦',
		']': '⟧',
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = val

	return substitute


def debughostilesubstitutions(texttoclean):
	"""
	all sorts of things will be hard to figure out if you run this suite
	but it does make many things 'look better' even if there are underlying problems.

	see latinfontlinemarkupparser() for notes on what the problems are/look like

	if the $ is part of an irrational 'on-without-off' Greek font toggle, then we don't care
	it is anything that does not fit that pattern that is the problem

	the hard part is churning through lots of texts looking for ones that do not fit that pattern

	at the moment few texts seem to have even the benign toggle issue; still looking for places
	where there is a genuine problem

	:param texttoclean:
	:return:
	"""

	if config['buildoptions']['hideknownblemishes'] != 'y':
		return texttoclean

	betacodetuples = [ (r'[\$]', r'') ,
	                   ]


	# note that '&' will return to the text via the hexrunner: it can be embedded in the annotations
	# and you will want it later in order to format that material when it hits HipparchiaServer:
	# in 'Gel. &3N.A.& 20.3.2' the '&3' turns on italics and stripping & leaves you with 3N.A. (which is hard to deal with)

	# $ is still a problem:
	# e.g., 0085:
	#   Der Antiatt. p. 115, 3 Bekk.: ‘ὑδρηλοὺϲ’ $πίθουϲ καὶ ‘οἰνηροὺϲ’
	#   @&Der Antiatt. p. 115, 3 Bekk.%10 $8’U(DRHLOU\S‘ $PI/QOUS KAI\ $8’OI)NHROU\S‘$

	for i in range(0, len(betacodetuples)):
		texttoclean = re.sub(betacodetuples[i][0], betacodetuples[i][1], texttoclean)

	return texttoclean


def cleanuplingeringmesses(texttoclean):
	"""

	we've made it to the bitter end but there is something ugly in the results
	here we can clean things up that we are too lazy/stupid/afraid-of-worse to prevent from ending up at this end

	:param texttoclean:
	:return:
	"""

	return texttoclean


def bracketspacer(matchgroup):
	"""
	this is not good:
		'[      <hmu_latin_normal>c 27     </hmu_latin_normal>π]όλεωϲ χ⦅αίρειν⦆. ὁμολογῶ'

	it should be:
		'[(spaces)c 27(spaces)π]όλεωϲ χ⦅αίρειν⦆. ὁμολογῶ'

	not too hard to get the spaces right; but they will only display in a compacted manner if sent out as
	so you should substitute u'\u00a0' (no-break space)

	:param matchgroup:
	:return:
	"""

	grpone = re.sub(r'\s',u'\u00a0', matchgroup.group(1))
	grptwo = re.sub(r'\s',u'\u00a0', matchgroup.group(2))
	grpthree = re.sub(r'\s', u'\u00a0', matchgroup.group(3))

	substitute = '[{x}c{y}]{z}'.format(x=grpone, y=grptwo, z=grpthree)

	return substitute


#
# matchgroup substitutions
#

#
# cleanup of the cleaned up: generative citeable texts
#


def totallemmatization(parsedtextfile):
	"""
	will use decoded hex commands to build a citation value for every line in the text file
	can produce a formatted line+citation, but really priming us for the move to the db

	note the potential gotcha: some authors have a first work that is not 001 but instead 002+

	:param parsedtextfile:
	:return: tuples that levelmap+the line
	"""

	levelmapper = {
		# be careful about re returning '1' and not 1
		0: 1,
		1: 1,
		2: 1,
		3: 1,
		4: 1,
		5: 1
	}

	dbready = []

	work = 1

	setter = re.compile(r'<hmu_set_level_(\d)_to_(.*?)\s/>')
	adder = re.compile(r'<hmu_increment_level_(\d)_by_1\s')
	wnv = re.compile(r'<hmu_cd_assert_work_number betacodeval="(\d{1,3})')

	for line in parsedtextfile:
		gotwork = re.search(wnv, line)
		if gotwork != None:
			work = int(gotwork.group(1))
			for l in range(0, 6):
				levelmapper[l] = 1
		gotsetting = re.search(setter, line)
		if gotsetting != None:
			level = int(gotsetting.group(1))
			setting = gotsetting.group(2)
			# Euripides (0006) has <hmu_set_level_0_to_post 961 /> after πῶς οὖν ἔτ’ ἂν θνήισκοιμ’ ἂν ἐνδίκως, πόσι,
			# 'post 961' becomes a problem: you need to add one to 961, but you will fail 'str(int(setting)'
			# slicing at the whitespace will fix this (sort of)
			# but then you get a new problem: UPZ (DDP0155) and its new documents '<hmu_set_level_5_to_2 rp />'
			# the not so pretty solution of the hour is to build a quasi-condition that is seldom met
			# it is almost never true that the split will yield anything other than the original item
			# it also is not clear how many other similar cases are out there: 'after 1001', etc.
			levelmapper[level] = setting.split('post ')[-1]
			if level > 0:
				for l in range(0, level):
					levelmapper[l] = 1

		gotincrement = re.search(adder, line)
		# if you don't reset the lower counters, then you will get something like 'line 10' when you first initialize a new section

		if gotincrement != None:
			level = int(gotincrement.group(1))
			setting = 1
			try:
				# are we adding integers?
				levelmapper[level] = str(int(setting) + int(levelmapper[level]))
			except ValueError:
				# ok, we are incrementing a letter; hope it's not z+1
				# can handle multicharacter strings, but how often is it not "a --> b"?
				lastchar = levelmapper[level][-1]
				newlastchar = chr(ord(lastchar) + setting)
				levelmapper[level] = levelmapper[level][:-1] + newlastchar
			# if you increment lvl 1, you need to reset lvl 0
			# this is a bit scary because sometimes you get an 0x81 and sometimes you don't
			if level > 0:
				for l in range(0, level):
					levelmapper[l] = 1

		# db version: list of tuples + the line
		tups = [('0',str(levelmapper[0])),('1',str(levelmapper[1])),('2',str(levelmapper[2])),('3',str(levelmapper[3])),('4',str(levelmapper[4])), ('5',str(levelmapper[5]))]
		dbready.append([str(work), tups, line])

	return dbready


def addcdlabels(texttoclean, authornumber):
	"""
	not totally necessary and a potential source of problems
	emerged before hexrunner worked right and not always in agreement with it?

	the CD would re-initilize values every block; this turns that info into human-readable info

	:param texttoclean:
	:param authornumber:
	:return:
	"""

	# cd blocks end 0xf3 + 0x0
	# the newline lets you reset levels right?

	search = r'(█ⓕⓔ\s(█⓪\s){1,})'
	replace = '\n<hmu_end_of_cd_block_re-initialize_key_variables />'
	texttoclean = re.sub(search, replace, texttoclean)

	authornumber = hextohighunicode(authornumber)
	digits = re.match(r'(.)(.)(.)(.)', authornumber)
	search = '█ⓔⓕ █⑧⓪ █ⓑ' + digits.group(1) + ' █ⓑ' + digits.group(2) + ' █ⓑ' \
	         + digits.group(3) + ' █ⓑ' + digits.group(4) + ' █ⓕⓕ '
	replace = '<hmu_cd_assert_author_number value=\"' + highunicodetohex(authornumber) + '\"/>'
	texttoclean = re.sub(search, replace, texttoclean)

	# 'primary level (81)' info stored in a run of 6 bytes:
	# 0xef 0x81 0xb0 0xb0 0xb1 0xff
	# the NEWLINE here has subtle implications: might need to play with it...
	# if you do not then you can include the last ilne of one work in the next...
	search = r'(█ⓔⓕ █⑧① █ⓑ(.) █ⓑ(.) █ⓑ(.) █ⓕⓕ )'
	replace = r'\n<hmu_cd_assert_work_number betacodeval="\2\3\4"/>'
	texttoclean = re.sub(search, replace, texttoclean)

	# 'secondary level (82)' info stored in a run of bytes whose length varies: add 127 to them and you get an ascii value
	# compare geasciistring() in idt file reader: '& int('7f',16))'
	# 0xef 0x82 0xc1 0xf0 0xef 0xec 0xff
	# 0xef 0x82 0xcd 0xf5 0xee 0xff
	search = r'(█ⓔⓕ\s█⑧②\s((█..\s){1,}?)█ⓕⓕ) '
	replace = r'<hmu_cd_assert_work_abbreviation betacodeval="\2"/>'
	texttoclean = re.sub(search, replace, texttoclean)

	# 'tertiray level (83)' info stored in a run of bytes whose length varies: add 127 to them and you get an ascii value
	# 0xef 0x83 0xc1 0xf0 0xf5 0xec 0xff
	search = r'(█ⓔⓕ\s█⑧③\s((█..\s){1,}?)█ⓕⓕ) '
	replace = r'<hmu_cd_assert_author_abbrev betacodeval="\2"/>'
	texttoclean = re.sub(search, replace, texttoclean)

	# now reparse

	search = r'<hmu_cd_assert_work_number betacodeval="..."/>'
	texttoclean = re.sub(search, hutohxgrouper, texttoclean)

	search = r'(<hmu_cd_assert_work_abbreviation betacodeval=")(.*?)\s("/>)'
	texttoclean = re.sub(search, converthextoascii, texttoclean)

	search = r'(<hmu_cd_assert_author_abbrev betacodeval=")(.*?)\s("/>)'
	texttoclean = re.sub(search, converthextoascii, texttoclean)

	# next comes something terrifying: after the author_abbrev we get 4 - 6  hex values
	# try to handle it with the citationbuilder
	search = r'(<hmu_cd_assert_author_abbrev betacodeval="(.*?)" />)((█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]{1,2}\s){2,})'
	texttoclean = re.sub(search, citationbuilder, texttoclean)

	return texttoclean


def hexrunner(texttoclean):
	"""
	First you find the hex runs.
	Then you send these to the citation builder to be read/decoded
	All of the heavy lifting happens there

	:param texttoclean:
	:param authornumber:
	:param worklist:
	:return: texttoclean
	"""

	# re.sub documentation: if repl is a function, it is called for every non-overlapping occurrence of pattern. The function takes a single match object argument, and returns the replacement string
	search = r'((█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]{1,2}\s){1,})'
	texttoclean = re.sub(search, citationbuilder, texttoclean)

	return texttoclean


#
# misc little tools
#
# some of these functions done similarly in idtfiles parsing
# refactor to consolidate if you care
#

def converthextoascii(hextoasciimatch):
	"""
	undo the human readability stuff so you can decode the raw data
	:param hextoascii:
	:return:
	"""
	asciilevel = ''
	hexlevel = hextoasciimatch.group(2)
	hexlevel = highunicodetohex(hexlevel)
	hexvals = re.split(r'█', hexlevel)
	del hexvals[0]
	asciilevel = bitswapchars(hexvals)
	a = hextoasciimatch.group(1) + asciilevel + hextoasciimatch.group(3)

	return a


def cleanworkname(betacodeworkname):
	"""
	turn a betacode workname into a 'proper' workname
	:param betacodeworkname:
	:return:
	"""

	if '*' in betacodeworkname and '$' not in betacodeworkname:
		re.sub(r'\*',r'$*',betacodeworkname)

	percents = re.compile(r'%(\d{1,3})')
	workname = re.sub(percents, percentsubstitutes, betacodeworkname)
	ands = re.compile(r'&(\d{1,})(.*?)')
	workname = re.sub(ands, latinauthorandshiftparser, betacodeworkname)

	workname = re.sub(r'\[2(.*?)]2', r'⟨\1⟩',workname)
	workname = re.sub(r'<.*?>','', workname)
	workname = re.sub(r'&\d{1,}(`|)', '', workname) # e.g.: IG I&4`2&
	workname = re.sub(r'&', '', workname)
	workname = re.sub(r'`', '', workname)

	# nb latin diacriticals still potentially here

	return workname


def colonshift(txt):
	"""

	colon to middot

	:param txt:
	:return:
	"""
	return re.sub(r':', '·', txt)


def insertnewlines(txt):
	"""

	break up the file into something you can walk through line-by-line

	:param txt:
	:return:
	"""
	txt =  re.sub(r'(<hmu_set_level)', r'\n\1', txt)
	txt = txt.split('\n')

	return txt

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-23
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
from string import punctuation
from typing import List

import configparser
import re

from builder.parsers.betacodeescapedcharacters import percentsubstitutes, quotesubstitutesa, quotesubstitutesb
from builder.parsers.betacodefontshifts import latinauthorandshiftparser
from builder.parsers.citationbuilder import citationbuilder
from builder.parsers.swappers import bitswapchars, hextohighunicode, highunicodetohex, hutohxgrouper

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')

if config['buildoptions']['warnings'] == 'y':
	warnings = True
else:
	warnings = False


# [nb: some regex happens in dbloading.py as prep for loading]


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
		(r'<(?!\d)', r'‹'),  # '<': this one is super-dangerous: triple-check
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
		(r'&c\s\?(.*?)\$', r'&c ﹖\1$'),  # the question mark needs to be preserved, so we substitute a small question mark
		(r'\[\sc\s\?(.*?)\$', r'[ c ﹖\1$'),  # try to catch '&{10m4}10 [ c ? ]$I' without doing any damage
		(r'&\?(.*?)\](.*?)\$', r'&﹖\1]\2$')  # some stray lonely '?' cases remain
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


def lastsecondsubsitutions(texttoclean):
	"""
	regex work that for some reason or other needs to be put off until the very last second

	:param texttoclean:
	:return:
	"""

	# gr2762 and chr0012 will fail the COPY TO command because of '\\'

	texttoclean = texttoclean.replace('\\', '')

	betacodetuples = (
		# a format shift code like '[3' if followed by a number that is supposed to print has an intervening ` to stop the TLG parser
		# if you do this prematurely you will generate spurious codes by joining numbers that should be kept apart
		(r'`(\d)', r'\1'),
		(r'\\\(', r'('),
		(r'\\\)', r')'),
	)

	for i in range(0, len(betacodetuples)):
		texttoclean = re.sub(betacodetuples[i][0], betacodetuples[i][1], texttoclean)

	if config['buildoptions']['simplifybrackets'] != 'n':
		tosimplify = re.compile(r'[❨❩❴❵⟦⟧⟪⟫《》‹›⦅⦆₍₎]')
		texttoclean = re.sub(tosimplify, bracketsimplifier, texttoclean)

	# change:
	#   <span class="latin smallerthannormal">Gnom. Vatic. 743 [</span>
	# into:
	#   <span class="latin smallerthannormal">Gnom. Vatic. 743 </span>[

	bracketandspan = re.compile(r'([❨❩❴❵⟦⟧⟪⟫《》‹›⦅⦆₍₎⟨⟩\[\](){}])(</span>)')
	texttoclean = re.sub(bracketandspan, r'\2\1', texttoclean)

	spanandbracket = re.compile(r'(<span class="[^"]*?">)([❨❩❴❵⟦⟧⟪⟫《》‹›⦅⦆₍₎⟨⟩\[\](){}])')
	texttoclean = re.sub(spanandbracket, r'\2\1', texttoclean)

	# be careful not to delete whole lines: [^"]*? vs .*?
	voidspan = re.compile(r'<span class="[^"]*?"></span> ')
	texttoclean = re.sub(voidspan, r'', texttoclean)

	# combining double inverted breve is misplaced: <3 >3
	# combining breve below is misplaced: <4 >4
	# combining breve (035d) ?: <5 >5

	swaps = re.compile(u'(.)([\u035c\u035d\u0361])')

	texttoclean = re.sub(swaps, r'\2\1', texttoclean)

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
	texttoclean = re.sub(resized, makepunctuationnormalsized, texttoclean)
	texttoclean = re.sub(r'([\w.,;])‘([\W])', r'\1’\2', texttoclean)
	texttoclean = re.sub(r'(\W)”(\w)', r'\1“\2', texttoclean)
	texttoclean = re.sub(r'([\w.,;])“([\W])', r'\1”\2', texttoclean)
	# ['‵', '′'], # reversed prime and prime (for later fixing)
	texttoclean = re.sub(r'([\w.,])‵([\W])', r'\1′\2', texttoclean)
	texttoclean = re.sub(r'(\W)′(\w)', r'\1‵\2', texttoclean)
	texttoclean = re.sub(r'‵', r'‘', texttoclean)
	texttoclean = re.sub(r'′', r'’', texttoclean)

	return texttoclean


def makepunctuationnormalsized(match):
	"""

	swap a normal and (﹠) for a little one (&), etc.

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


def makepunctuationsmall(val):
	"""

	swap a little and (﹠) for a big one (&), etc.

	:param val:
	:return:
	"""

	substitutions = {
		'?': '﹖',
		'*': '﹡',
		'/': '／',
		'!': '﹗',
		'|': '│',
		'=': '﹦',
		'+': '﹢',
		'%': '﹪',
		'&': '﹠',
		':': '﹕',
		u'\u0027': '＇'  # simple apostrophe
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


def swapregexbrackets(val):
	"""

	get rid of [](){}

	insert safe substitutes

	currently unused

	:param match:
	:return:
	"""

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

	betacodetuples = [(r'[\$]', r''),]

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

	grpone = re.sub(r'\s', u'\u00a0', matchgroup.group(1))
	grptwo = re.sub(r'\s', u'\u00a0', matchgroup.group(2))
	grpthree = re.sub(r'\s', u'\u00a0', matchgroup.group(3))

	substitute = '[{x}c{y}]{z}'.format(x=grpone, y=grptwo, z=grpthree)

	return substitute


#
# fix problems with the original data
#

def fixhmuoragnizationlinebyline(txt: List[str]) -> List[str]:
	"""

	the original data has improper nesting of some tags; try to fix that

	this is meaningless if you have set htmlifydatabase to 'y' since the 'spanning' will hide the phenomenon

	:param txt:
	:return:
	"""

	try:
		htmlify = config['buildoptions']['htmlifydatabase']
	except KeyError:
		htmlify = 'y'

	try:
		rationalizetags = config['buildoptions']['rationalizetags']
	except KeyError:
		rationalizetags = 'n'

	if htmlify == 'y' or rationalizetags == 'n':
		pass
	else:
		txt = [fixhmuirrationaloragnization(x) for x in txt]

	return txt


def fixhmuirrationaloragnization(worlkine: str):
		"""

		Note the irrationality (for HTML) of the following (which is masked by the 'spanner'):
		[have 'EX_ON' + 'SM_ON' + 'EX_OFF' + 'SM_OFF']
		[need 'EX_ON' + 'SM_ON' + 'SM_OFF' + 'EX_OFF' + 'SM_ON' + 'SM_OFF' ]

		hipparchiaDB=# SELECT index, marked_up_line FROM gr0085 where index = 14697;
		 index |                                                                           marked_up_line
		-------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------
		 14697 | <hmu_span_expanded_text><hmu_fontshift_greek_smallerthannormal>τίϲ ἡ τάραξιϲ</hmu_span_expanded_text> τοῦ βίου; τί βάρβιτοϲ</hmu_fontshift_greek_smallerthannormal>
		(1 row)


		hipparchiaDB=> SELECT index, marked_up_line FROM gr0085 where index = 14697;
		 index |                                                marked_up_line
		-------+---------------------------------------------------------------------------------------------------------------
		 14697 | <span class="expanded_text"><span class="smallerthannormal">τίϲ ἡ τάραξιϲ</span> τοῦ βίου; τί βάρβιτοϲ</span>
		(1 row)


		fixing this is an interesting question; it seems likely that I have missed some way of doing it wrong...
		but note 'b' below: this is pretty mangled and the output is roughly right...

		invalidline = '<hmu_span_expanded_text><hmu_fontshift_greek_smallerthannormal>τίϲ ἡ τάραξιϲ</hmu_span_expanded_text> τοῦ βίου; τί βάρβιτοϲ</hmu_fontshift_greek_smallerthannormal>'
		openspans {0: 'span_expanded_text', 24: 'fontshift_greek_smallerthannormal'}
		closedspans {76: 'span_expanded_text', 123: 'fontshift_greek_smallerthannormal'}
		balancetest [(False, False, True)]

		validline = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<hmu_fontshift_latin_smallcapitals>errantes</hmu_fontshift_latin_smallcapitals><hmu_fontshift_latin_normal> pascentes, ut alibi “mille meae Siculis</hmu_fontshift_latin_normal>'
		openspans {36: 'fontshift_latin_smallcapitals', 115: 'fontshift_latin_normal'}
		closedspans {79: 'fontshift_latin_smallcapitals', 183: 'fontshift_latin_normal'}
		balancetest [(False, True, False)]

		# need a third check: or not (open[okeys[x]] == closed[ckeys[x]])
		z = '&nbsp;&nbsp;&nbsp;<hmu_fontshift_latin_normal>II 47.</hmu_fontshift_latin_normal><hmu_fontshift_latin_italic> prognosticorum causas persecuti sunt et <hmu_span_latin_expanded_text>Boëthus Stoicus</hmu_span_latin_expanded_text>,</hmu_fontshift_latin_italic>'
		openspans {18: 'fontshift_latin_normal', 81: 'fontshift_latin_italic', 150: 'span_latin_expanded_text'}
		closedspans {52: 'fontshift_latin_normal', 195: 'span_latin_expanded_text', 227: 'fontshift_latin_italic'}
		balancetest [(False, True, False), (True, False, True)]

		a = '[]κακ<hmu_span_superscript>η</hmu_span_superscript> βου<hmu_span_superscript>λ</hmu_span_superscript>'
		openspans {5: 'span_superscript', 55: 'span_superscript'}
		closedspans {28: 'span_superscript', 78: 'span_superscript'}
		balancetest [(False, True, False)]

		b = []κακ<hmu_span_superscript>η</hmu_span_superscript> β<hmu_span_x>ο<hmu_span_y>υab</hmu_span_x>c<hmu_span_superscript>λ</hmu_span_y></hmu_span_superscript>
		testresult (False, True, False)
		testresult (False, False, True)
		testresult (False, False, True)
		balanced to:
			[]κακ<hmu_span_superscript>η</hmu_span_superscript> β<hmu_span_x>ο<hmu_span_y>υab</hmu_span_y></hmu_span_x><hmu_span_y>c<hmu_span_superscript>λ</hmu_span_superscript></hmu_span_y><hmu_span_superscript></hmu_span_superscript>

		"""

		opener = re.compile(r'<hmu_(span|fontshift)_(.*?)>')
		closer = re.compile(r'</hmu_(span|fontshift)_(.*?)>')

		openings = list(re.finditer(opener, worlkine))
		openspans = {x.span()[0]: '{a}_{b}'.format(a=x.group(1), b=x.group(2)) for x in openings}

		closings = list(re.finditer(closer, worlkine))
		closedspans = {x.span()[0]: '{a}_{b}'.format(a=x.group(1), b=x.group(2)) for x in closings}

		balancetest = list()
		invalidpattern = (False, False, True)

		if len(openspans) == len(closedspans) and len(openspans) > 1:
			# print('openspans', openspans)
			# print('closedspans', closedspans)

			rng = range(len(openspans) - 1)
			okeys = sorted(openspans.keys())
			ckeys = sorted(closedspans.keys())
			# test 1: a problem if the next open ≠ this close and next open position comes before this close position
			#   	open: {0: 'span_expanded_text', 24: 'fontshift_greek_smallerthannormal'}
			# 		closed: {76: 'span_expanded_text', 123: 'fontshift_greek_smallerthannormal'}
			# test 2: succeed if the next open comes after the this close AND the this set of tags match
			#       open {18: 'fontshift_latin_normal', 81: 'fontshift_latin_italic', 150: 'span_latin_expanded_text'}
			# 		closed {52: 'fontshift_latin_normal', 195: 'span_latin_expanded_text', 227: 'fontshift_latin_italic'}
			# test 3: succeed if the next open comes before the previous close

			testone = [not (openspans[okeys[x + 1]] != closedspans[ckeys[x]]) and (okeys[x + 1] < ckeys[x]) for x in rng]
			testtwo = [okeys[x + 1] > ckeys[x] and openspans[okeys[x]] == closedspans[ckeys[x]] for x in rng]
			testthree = [okeys[x + 1] < ckeys[x] for x in rng]

			balancetest = [(testone[x], testtwo[x], testthree[x]) for x in rng]
			# print('balancetest', balancetest)

		if invalidpattern in balancetest:
			# print('{a} needs balancing:\n\t{b}'.format(a=str(), b=worlkine))
			modifications = list()
			balancetest.reverse()
			itemnumber = 0
			while balancetest:
				testresult = balancetest.pop()
				if testresult == invalidpattern:
					needinsertionat = ckeys[itemnumber]
					insertionreopentag = openings[itemnumber + 1].group(0)
					insertionclosetag = re.sub(r'<', r'</', openings[itemnumber + 1].group(0))
					modifications.append({'item': itemnumber,
					                      'position': needinsertionat,
					                      'closetag': insertionclosetag,
					                      'opentag': insertionreopentag})
				itemnumber += 1

			newline = str()
			placeholder = 0
			for m in modifications:
				item = m['item']
				newline += worlkine[placeholder:m['position']]
				newline += m['closetag']
				newline += closings[item].group(0)
				newline += m['opentag']
				placeholder = m['position'] + len(closings[item].group(0))
			newline += worlkine[placeholder:]

			# print('{a} balanced to:\n\t{b}'.format(a=str(), b=newline))
			worlkine = newline

		return worlkine


#
# cleanup of the cleaned up: generative citeable texts
#


def totallemmatization(parsedtextfile: List[str]) -> List[str]:
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

	dbready = list()

	work = 1

	setter = re.compile(r'<hmu_set_level_(\d)_to_(.*?)\s/>')
	adder = re.compile(r'<hmu_increment_level_(\d)_by_1\s')
	wnv = re.compile(r'<hmu_cd_assert_work_number betacodeval="(\d{1,3})')

	for line in parsedtextfile:
		gotwork = re.search(wnv, line)
		if gotwork:
			work = int(gotwork.group(1))
			for l in range(0, 6):
				levelmapper[l] = 1
		gotsetting = re.search(setter, line)
		if gotsetting:
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

		if gotincrement:
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
		tups = [('0', str(levelmapper[0])), ('1', str(levelmapper[1])), ('2', str(levelmapper[2])), ('3', str(levelmapper[3])), ('4', str(levelmapper[4])), ('5', str(levelmapper[5]))]
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

	template = '█ⓔⓕ █⑧⓪ █ⓑ{one} █ⓑ{two} █ⓑ{three} █ⓑ{four} █ⓕⓕ '
	authornumber = hextohighunicode(authornumber)
	digits = re.match(r'(.)(.)(.)(.)', authornumber)
	search = template.format(one=digits.group(1), two=digits.group(2), three=digits.group(3), four=digits.group(4))
	replace = '<hmu_cd_assert_author_number value=\"{v}\"/>'.format(v=highunicodetohex(authornumber))
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

	# 'tertiary level (83)' info stored in a run of bytes whose length varies: add 127 to them and you get an ascii value
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
	:param hextoasciimatch:
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
		re.sub(r'\*', r'$*', betacodeworkname)

	percents = re.compile(r'%(\d{1,3})')
	workname = re.sub(percents, percentsubstitutes, betacodeworkname)
	ands = re.compile(r'&(\d+)(.*?)')
	workname = re.sub(ands, latinauthorandshiftparser, workname)

	workname = re.sub(r'\[2(.*?)]2', r'⟨\1⟩', workname)
	workname = re.sub(r'<.*?>', '', workname)
	workname = re.sub(r'&\d+(`|)', '', workname)  # e.g.: IG I&4`2&
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
	txt = re.sub(r'(<hmu_set_level)', r'\n\1', txt)
	txt = txt.split('\n')

	return txt


def tidyupterm(word: str, punct=None) -> str:
	"""

	remove gunk that should not be present in a cleaned line
	pass punct if you do not feel like compiling it 100k times
	:param word:
	:param punct:
	:return:
	"""

	if not punct:
		elidedextrapunct = '\′‵‘·̆́“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⟨⟩⸐„⸏⸖⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚̄⁝͜‖͡⸓͝'
		extrapunct = elidedextrapunct + '’'
		punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)

	invals = u'jv'
	outvals = u'iu'
	word = word.translate(str.maketrans(invals, outvals))

	return word


def capitalvforcapitalu(thetext: str) -> str:
	"""

	Latin texts have "Ubi" instead of "Vbi"
	Livy and Justinian even have Ualerius instead of Valerius

	you need to do this right away before any markup, etc appears

	a problem: Greek inside a Roman author will get mangled: "PARADOXON II: Ὅτι αϝ)τάρκηϲ ἡ ἀρετὴ πρὸϲ εϝ)δαιμονίαν."
	This arises from: $*(/OTI AV)TA/RKHS H( A)RETH\ PRO\S EV)DAIMONI/AN.&}1

	:param thetext:
	:return:
	"""

	# print('applying U -> V transformation to {a}'.format(a=thisauthor))
	thetext = re.sub(r'U', 'V', thetext)
	lookingfor = re.compile(r'\$(.*?)&')
	uswap = lambda x: '$' + re.sub(r'V', r'U', x.group(1)) + '&'
	thetext = re.sub(lookingfor, uswap, thetext)

	return thetext
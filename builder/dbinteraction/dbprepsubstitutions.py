# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import configparser
from collections import deque
from builder.parsers.betacodeandunicodeinterconversion import cleanaccentsandvj, buildhipparchiatranstable
from builder.parsers.regexsubstitutions import swapregexbrackets, makepunctuationsmall
from builder.parsers.transliteration import transliteratecolums

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


def dbprepper(dbunreadyversion: list) -> deque:
	"""
	pull out markups, etc
	:param dbunreadyversion:
	:return:
	"""
	
	# findhyphens() vs addcdlabels()
	
	# '-█ⓕⓔ' lines are not read as ending with '-' by the time they get to findhyphens().
	#
	# it's an ugly issue
	
	# the following lines of isaeus refuse to match any conditional to test for a hypen you throw at them and so will not enter into the 'if...' clause; but if you cut and paste the text '-' == 'True'
	
	#   "ἔφη τήν τε ἡλικίαν ὑφορᾶϲθαι τὴν ἑαυτοῦ καὶ τὴν ἀπαι-"
	#   █⑧⓪ E)/FH TH/N TE H(LIKI/AN U(FORA=SQAI TH\N E(AUTOU= KAI\ TH\N A)PAI-█ⓕⓔ
	#   "Εἶτα αὐτὸϲ μὲν εἰ ἦν ἄπαιϲ, ἐποιήϲατ’ ἄν· τὸν δὲ Με-"
	#   █⑧⓪ *EI)=TA AU)TO\S ME\N EI) H)=N A)/PAIS, E)POIH/SAT' A)/N: TO\N DE\ *ME-█ⓕⓔ
	#
	# >>> x = 'ἀπαι-'
	# >>> if '-' in x: print('yes')
	# ...
	# yes
	# >>>
	
	#  the fix is to remove the trailing space in regexsubs addcdlabels(). but then that kills your ability to get the last line of a work into the db
	#   replace = '\n<hmu_end_of_cd_block_re-initialize_key_variables />' vs replace = '\n<hmu_end_of_cd_block_re-initialize_key_variables /> '
	
	# so the simple solution to a complex problem is to slap a single whitespace at the end of the file
	dbunreadyversion[-1][2] = dbunreadyversion[-1][2] + ' '
	
	dbunreadyversion = cleanblanks(dbunreadyversion)
	dbunreadyversion = dbpdeincrement(dbunreadyversion)
	dbunreadyversion = dbstrippedliner(dbunreadyversion)

	try:
		if config['playground']['transliterate'] == 'y':
			dbunreadyversion = transliteratecolums(dbunreadyversion)
	except KeyError:
		# your config file is old...
		pass

	# you will have problems browsing to 'Left/Right (1b:2)' if you don't do something here
	dbunreadyversion = dbswapoutbadcharsfromcitations(dbunreadyversion)
	dbunreadyversion = dbfindhypens(dbunreadyversion)
	dbunreadyversion = dbfindannotations(dbunreadyversion)
	dbunreadyversion = hmutonbsp(dbunreadyversion)
	dbunreadyversion = noleadingortrailingwhitespace(dbunreadyversion)
	dbreadyversion = dbunreadyversion
	
	return dbreadyversion


def cleanblanks(dbunreadyversion: list) -> list:
	"""
	multiple sets and level shifts in rapid succession sometimes leaves blank lines that are 'numbered': zap them

	note that this is an old, subtle issue. and it tends to shift as with changes to the functions that come befor it.

	the defunct halflinecleanup() was a flawed fix for a slightly different version of the problem.

	it may be necessary to keep debugging this: lyric is the best place to look for the issue

	aristophanes:

		['6', [('0', '1099'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_blank_quarter_spaces quantity="63" /> ἠρινά τε βοϲκόμεθα παρθένια '],
		['6', [('0', '1100-1101'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1100-1101 /><hmu_blank_quarter_spaces quantity="63" /> λευκότροφα μύρτα Χαρίτων τε κηπεύματα. '],
		['6', [('0', '1100-1101'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1100-1101 /><br /> '],
		['6', [('0', '1102'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1102 /><hmu_blank_quarter_spaces quantity="38" /> Τοῖϲ κριταῖϲ εἰπεῖν τι βουλόμεϲθα τῆϲ νίκηϲ πέρι, '],
		['6', [('0', '1103'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_blank_quarter_spaces quantity="38" /> ὅϲ’ ἀγάθ’, ἢν κρίνωϲιν ἡμᾶϲ, πᾶϲιν αὐτοῖϲ δώϲομεν, '],

	aeschylus:

		['1', [('0', '175e'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_blank_quarter_spaces quantity="27" /> χαλεποῦ γὰρ ἐκ ']
		['1', [('0', '175f'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_blank_quarter_spaces quantity="43" /> πνεύματοϲ εἶϲι χειμών.⟩ ']
		['1', [('0', '175f'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_175f /><br /> ']
		['1', [('0', '176'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_176 /><hmu_blank_quarter_spaces quantity="4" /> <span class="speaker"><span class="smallerthannormal">ΔΑΝΑΟϹ</span></span> ']

	:param dbunreadyversion:
	:return:
	"""

	workingcolumn = 2

	blankline = re.compile(r'<hmu_set_level_0_to_.*?\s/><br />\s$')
	dbreadyversion = [d for d in dbunreadyversion if not re.search(blankline, d[workingcolumn])]

	return dbreadyversion


def dbpdeincrement(dbunreadyversion: list) -> deque:
	"""
	a formattind stripper:
	
	sample in:
		['1', [('0', '4'), ('1', '3'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_standalone_tabbedtext />ταύτηϲ γὰρ κεῖνοι δάμονέϲ εἰϲι μάχηϲ ']
		
	sample out:
		['1', [('0', '4'), ('1', '3'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_standalone_tabbedtext />ταύτηϲ γὰρ κεῖνοι δάμονέϲ εἰϲι μάχηϲ ']
	
	:param dbunreadyversion:
	:return:
	"""

	workingcolumn = 2

	#setter = re.compile(r'<hmu_set_level_\d_to_[A-Za-z0-9]{1,}\s/>')
	# wont catch '<hmu_set_level_1_to_98* />'
	setter = re.compile(r'<hmu_set_level_\d_to_.*?\s/>')
	adder = re.compile(r'<hmu_increment_level_(\d)_by_1\s/>')
	blocker = re.compile(r'<hmu_cd_assert_(.*?)>')
	eob = re.compile(r'<hmu_end_of_cd_block_re-initialize_key_variables />')
	docu = re.compile(r'<hmu_assert_document_number_(.*?)>')
	# empty = r'(?<!*)\s{0,1}(?=!*)'
		
	dbreadyversion = deque()

	for line in dbunreadyversion:
		for expression in [setter, adder, blocker, eob, docu]:
			line[workingcolumn] = re.sub(expression, '', line[workingcolumn])

		if line[workingcolumn] != '':
			dbreadyversion.append(line)

	return dbreadyversion


def dbstrippedliner(dbunreadyversion: deque) -> deque:
	"""
	generate the easy to search stripped column
	
	sample in:
		['1', [('0', '2'), ('1', '5'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_standalone_tabbedtext />ἔντοϲ ἀμώμητον, κάλλιπον οὐκ ἐθέλων· ']
	
	sample out:
		['1', [('0', '2'), ('1', '5'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_standalone_tabbedtext />ἔντοϲ ἀμώμητον, κάλλιπον οὐκ ἐθέλων· ', 'ἔντοϲ ἀμώμητον κάλλιπον οὐκ ἐθέλων ', 'εντοϲ αμωμητον καλλιπον ουκ εθελων ']

	:param dbunreadyversion:
	:return:
	"""

	# generate the easy-to-search column
	# example:
	# ['1', [('0', '5'), ('1', '1'), ('2', '4'), ('3', 'Milt'), ('4', '1')], 'hostem esse Atheniensibus, quod eorum auxilio Iones Sardis expugnas-']
	# be careful: the next will kill even editorial insertions 'do <ut> des': you have to be sure that no 'pure' angled brackets made it this far
	# ⟨abc⟩ should be all that you see
	nukemarkup = re.compile(r'<.*?>')
	combininglowerdot = u'\u0323'
	straydigits = r'\d'
	sigmas = re.compile(r'[σς]')
	# straypunct is a big deal: it defines what a clean line will look like and so what you can search for
	#   sadly can't nuke :punct: as a class because we need hyphens
	#   if you want to find »αʹ« you need ʹ
	#   if you want to find »͵α« you need ͵
	#   if you want to search for undocumented/idiosyncratic chars you need ◦⊚
	#   misc other things that one might want to exclude but are currently included: ☩ͻ
	#   the following are supposed to be killed off by bracketsimplifier(): ❨❩⟨⟩⟪⟫⦅⦆❴❵
	#   no longer relevant?: ⸨⸩｟｠《
	straypunct = r'\<\>\{\}\[\]\(\)⟨⟩₍₎\'\.\?\!⌉⎜͙✳※¶§͜﹖→𐄂𝕔;:ˈ＇,‚‛‘’“”„·‧∣⸏'

	nukepunct = re.compile('['+combininglowerdot+straydigits+straypunct+']')

	dbreadyversion = deque()
	workingcolumn = 2

	# remove things like '<speaker>Cr.</speaker>' from the search column
	# many 'ltcurlybracketsubstitutes' are interesting candidates for purging
	# you can get a '\s\s' problem with these erasures
	dbtagnuker = config['buildoptions']['unsearchable'].split(' ')
	dbtagnuker = [t for t in dbtagnuker if t]
	fingerprints = [re.compile(r'<{t}>.*?</{t}>\s*'.format(t=tag)) for tag in dbtagnuker]

	for line in dbunreadyversion:
		# must do this before running the markup cleaner
		clean = line[workingcolumn]
		for f in fingerprints:
			clean = re.sub(f, '', clean)
		clean = re.sub(nukemarkup, '', clean)
		clean = re.sub(nukepunct, '', clean)
		clean = clean.lower()
		if config['buildoptions']['lunate'] == 'n':
			clean = re.sub(sigmas, 'ϲ', clean)
		clean = re.sub(r'\s{2,}', ' ', clean)
		line.append(clean)
		# this is the clean line with accents
		dbreadyversion.append(line)

	dbunreadyversion = dbreadyversion
	dbreadyversion = deque()
	workingcolumn = 3

	# capitalization can be made to still matter; does that matter?
	# you won't get the first word of the iliad right unless you search for capital Mu
	# it seems like you will seldom wish you had caps and that remembering to handle them as a casual user is not so hot

	transtable = buildhipparchiatranstable()

	for line in dbunreadyversion:
		unaccented = cleanaccentsandvj(line[workingcolumn], transtable)
		line = line + [unaccented]
		dbreadyversion.append(line)
		
	return dbreadyversion


def dbswapoutbadcharsfromcitations(dbunreadyversion: deque) -> deque:
	"""

	sample in:
		['2', [('0', '6'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], 'ἀγῶϲι πρόνοιαν· ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ Ἰτα-', 'ἀγῶϲι πρόνοιαν ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ ἰτα-', 'αγωϲι προνοιαν οϲ και τοτε περαιουμενοϲ ναυϲιν εϲ ιτα-']

	but not everybody looks like in column 1:
		[('0', '6'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')]

	instead of '1' at level01, some of these can have:
		'Right/Left F,11(1)'

	HipparchiaServer *hates* that: the '/' will call a different URL; the '(' makes the regex engine sad; usw.

	So we will swap out the relevant chars...

	:param dbunreadyversion:
	:return:
	"""

	dbreadyversion = deque()
	workingcolumn = 1

	brackets = re.compile(r'[\]\[\(\)\{\}]')
	punct = re.compile(r'[?*/!|=+%&:\']')

	while dbunreadyversion:
		line = dbunreadyversion.popleft()
		citation = line[workingcolumn]
		newcitation = [(c[0], re.sub(brackets, lambda x: swapregexbrackets(x.group(0)), c[1])) for c in citation]
		newcitation = [(c[0], re.sub(punct, lambda x: makepunctuationsmall(x.group(0)), c[1])) for c in newcitation]
		newrow = line[0:workingcolumn] + [newcitation] + line[workingcolumn+1:]
		dbreadyversion.append(newrow)

	return dbreadyversion


def dbfindhypens(dbunreadyversion: deque) -> deque:
	"""

	sample in:
		['2', [('0', '6'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], 'ἀγῶϲι πρόνοιαν· ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ Ἰτα-', 'ἀγῶϲι πρόνοιαν ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ ἰτα-', 'αγωϲι προνοιαν οϲ και τοτε περαιουμενοϲ ναυϲιν εϲ ιτα-']
	sample out:
		['2', [('0', '6'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], 'ἀγῶϲι πρόνοιαν· ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ Ἰτα-', 'ἀγῶϲι πρόνοιαν ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ ἰταλίαν', 'αγωϲι προνοιαν οϲ και τοτε περαιουμενοϲ ναυϲιν εϲ ἰταλίαν']
		
	:param dbunreadyversion:
	:return:
	"""

	dbreadyversion = deque()
	workingcolumn = 3
	# previous = dbunreadyversion[0]
	previous = dbunreadyversion.popleft()
	lastline = dbunreadyversion[-1]

	transtable = buildhipparchiatranstable()

	while dbunreadyversion:
		line = dbunreadyversion.popleft()
		try:
			# a problem if the line is empty: nothing to split
			# a good opportunity to skip adding a line to dbreadyversion
			prevend = previous[workingcolumn].rsplit(None, 1)[1]
			if prevend[-1] == '-':
				thisstart = line[workingcolumn].split(None, 1)[0]
				hyphenated = prevend[:-1] + thisstart
				if len(hyphenated) > 0:
					newlines = consolidatecontiguouslines(previous, line, hyphenated, transtable)
					previous = newlines['p']
					line = newlines['l']
				previous.append(hyphenated)
			else:
				previous.append('')
			dbreadyversion.append(previous)
			previous = line
		except:
			previous.append('')
			dbreadyversion.append(previous)
			previous = line
	
	if lastline[workingcolumn] != '' and lastline[workingcolumn] != ' ':
		dbreadyversion.append(lastline)
	
	return dbreadyversion


def dbfindannotations(dbunreadyversion):
	workingcolumn = 2
	dbreadyversion = deque()
	search = re.compile(r'<hmu(_|_metadata_)annotations value="(.*?)" />')
	for line in dbunreadyversion:
		notes = re.findall(search, line[workingcolumn])
		notes = [n[1] for n in notes]
		notes = [n for n in notes if n]
		notes = list(set(notes))

		line[workingcolumn] = re.sub(search, '', line[workingcolumn])
			
		if len(notes) > 0:
			notetext = ''
			for n in notes:
				notetext += n+'; '
			notetext = notetext[:-2]
			line.append(notetext)
		else:
			line.append('')
		dbreadyversion.append(line)

	return dbreadyversion


def hmutonbsp(dbunreadyversion: list) -> deque:
	"""
	pseudo-markup into html
	this is a place where some commitments that have been deferred will get made
	obviously you could put all of this in earlier for the sake of efficiency,
	but handling this here and now is convenient: one stop shopping w/out tripping up the parser earlier
	:param dbunreadyversion:
	:return:
	"""
	workingcolumn = 2
	dbreadyversion = deque()
	bqs = re.compile(r'<hmu_blank_quarter_spaces quantity="(\d+)" />')
	
	for line in dbunreadyversion:
		line[workingcolumn] = re.sub(bqs, quarterspacer, line[workingcolumn])
		# used to do 4, but the indentations could pile up
		line[workingcolumn] = re.sub(r'<hmu_standalone_tabbedtext />', r'&nbsp;&nbsp;&nbsp;', line[workingcolumn])
		dbreadyversion.append(line)
	
	return dbreadyversion


def quarterspacer(matchgroup):
	"""
	take a found collection of quarter spaces and turn them into spaces
	:param matchgroup:
	:return: a digit as a string
	"""
	digit = int(matchgroup.group(1))
	# used to do 4, but the indentations could pile up
	spaces = divmod(digit, 5)[0]
	substitution = ''
	for i in range(0, spaces):
		substitution += '&nbsp;'

	return substitution


def noleadingortrailingwhitespace(dbunreadyversion: list) -> deque:
	"""
	get rid of whitespace at ends of columns
	otherwise HipparchiaServer is constantly doing this
	:param dbunreadyversion:
	:return:
	"""
	dbreadyversion = deque()
	
	for line in dbunreadyversion:
		for column in [2, 3, 4]:
			line[column] = re.sub(r'(^\s|\s$)', '', line[column])
		dbreadyversion.append(line)
	
	return dbreadyversion


def consolidatecontiguouslines(previousline: list, thisline: list, hypenatedword: str, transtable):
	"""

	helper function for the stripped line column: if a previousline ends with a hypenated word:
		put the whole word at line end
		drop the half-word from the start of thisline

	:param previousline:
	:param thisline:
	:param hypenatedword:
	:param transtable:
	:return:
	"""
	
	accentedcolumn = 3
	strippedcolumn = 4
	
	column = accentedcolumn
	pc = re.sub(r'\s$', '', previousline[column])
	p = pc.split(' ')
	t = thisline[column].split(' ')
	
	p = p[:-1] + [hypenatedword]
	t = t[1:]
	
	p = ' '.join(p)
	t = ' '.join(t)
	
	pl = previousline[0:column] + [p]
	tl = thisline[0:column] + [t]
		
	column = strippedcolumn
	pc = re.sub(r'\s$', '', previousline[column])
	p = pc.split(' ')
	t = thisline[column].split(' ')
	
	p = p[:-1] + [cleanaccentsandvj(hypenatedword, transtable)]
	t = t[1:]
	
	p = ' '.join(p)
	t = ' '.join(t)
	
	pl = pl + [p]
	tl = tl + [t]

	newlines = dict()
	newlines['p'] = pl
	newlines['l'] = tl

	return newlines

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time
from collections import deque
from builder.parsers.betacode_to_unicode import stripaccents


def dbprepper(dbunreadyversion):
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
	
	dbunreadyversion = halflinecleanup(dbunreadyversion)
	dbunreadyversion = dbpdeincrement(dbunreadyversion)
	dbunreadyversion = dbstrippedliner(dbunreadyversion)
	dbunreadyversion = dbfindhypens(dbunreadyversion)
	dbunreadyversion = dbfindannotations(dbunreadyversion)
	dbunreadyversion = hmutonbsp(dbunreadyversion)
	dbunreadyversion = noleadingortrailingwhitespace(dbunreadyversion)
	dbreadyversion = dbunreadyversion
	
	return dbreadyversion


def halflinecleanup(dbunreadyversion):
	"""
	this painful next kludge is a function of half-lines that do multiple sets and level shifts in rapid succession and leave the actual text on 'line 1' unless you do something drastic:
		['6', [('0', '1099'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_blank_quarter_spaces quantity="63" /> ἠρινά τε βοϲκόμεθα παρθένια ']
		['6', [('0', '1100'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1100-11 />']
		['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '2'), ('4', '1'), ('5', '1')], '<hmu_increment_level_3_by_1 />']
		['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_3_to_1 /><hmu_blank_quarter_spaces quantity="63" /> λευκότροφα μύρτα Χαρίτων τε κηπεύματα. ']
		['6', [('0', '1100'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1100-11 />']
		['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '2'), ('4', '1'), ('5', '1')], '<hmu_increment_level_3_by_1 />']
		['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_3_to_1 /><hmu_blank_line />']
		['6', [('0', '1102'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1102 /><hmu_blank_quarter_spaces quantity="38" /> Τοῖϲ κριταῖϲ εἰπεῖν τι βουλόμεϲθα τῆϲ νίκηϲ πέρι, ']
	
	:param dbunreadyversion:
	:return:
	"""
	#

	lvlzerodasher = re.compile(r'<hmu_set_level_0_to_(\d{1,})-(\d{1,})\s/>')
	adder = re.compile(r'<hmu_increment_level_(\d)_by_1\s/>')
	setter = re.compile(r'<hmu_set_level_(\d)_to_(\d{1,})\s/>')
	
	workingcolumn = 2
	dbreadyversion = []
	memory = None
	for line in dbunreadyversion:
		try:
			add = re.search(adder,line[workingcolumn]).span(0)[1]
		except:
			add = 9999
		try:
			set = re.search(setter,line[workingcolumn]).span(0)[1]
		except:
			set = 9999
		if re.search(lvlzerodasher, line[workingcolumn]) is not None:
			memory = line
		elif (memory is not None):
			if add != len(line[workingcolumn]) and set != len(line[workingcolumn]):
				# print('xformed',line)
				line = [memory[0],memory[1],line[workingcolumn]]
				# print('into',line)
				dbreadyversion.append(line)
				memory = None
		else:
			dbreadyversion.append(line)
		
	return dbreadyversion


def dbpdeincrement(dbunreadyversion):
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
		
	dbreadyversion = []

	for line in dbunreadyversion:
		for expression in [setter, adder, blocker, eob, docu]:
			line[workingcolumn] = re.sub(expression, '', line[workingcolumn])

		if line[workingcolumn] != '':
			dbreadyversion.append(line)

	return dbreadyversion


def dbstrippedliner(dbunreadyversion):
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
	# be careful: the next will kill even editorial insertions 'do <ut> des'
	# markup = re.compile(r'\<.*?\>')
	markup = re.compile(r'\<hmu_.*?\>')
	unmarkup = re.compile(r'\</hmu_.*?\>')
	span = re.compile(r'<span .*?>')
	unspan = re.compile(r'</span>')
	combininglowerdot = re.compile(u'\u0323')
	# this will help with some and hurt with others? need to double-check
	# squarebrackets = re.compile(r'\[.*?\]')
	straydigits = re.compile(r'\d')
	# sadly can't nuke :punct: as a class because we need hyphens
	straypunct = re.compile('[\<\>\{\}⎜͙✳※§｟｠《⟪⟫⦅⦆❴❵\.\?﹖𝕔☩\!;:,’“”·\[\]\(\)]')
	
	dbreadyversion = []
	workingcolumn = 2

	# tempting to strip delenda here, but that presupposes you caught all the number-brackets before
	# '[delenda]' vs '[2 formatted_text...'
	
	for line in dbunreadyversion:
		# in two parts because it is possible that the markup jumps lines
		clean = re.sub(markup, '', line[workingcolumn])
		clean = re.sub(unmarkup, '', clean)
		clean = re.sub(straydigits, '', clean)
		# clean = re.sub(squarebrackets, '', clean)
		clean = re.sub(span, '', clean)
		clean = re.sub(unspan, '', clean)
		clean = re.sub(straypunct, '', clean)
		clean = re.sub(combininglowerdot, '', clean)
		clean = clean.lower()
		
		line.append(clean)
		# this is the clean line with accents
		dbreadyversion.append(line)

	dbunreadyversion = dbreadyversion
	dbreadyversion = []
	workingcolumn = 3
	# capitalization can be made to still matter; does that matter?
	# you won't get the first word of the iliad right unless you search for capital Mu
	# it seems like you will seldom wish you had caps and that remembering to handle them as a casual user is not so hot

	for line in dbunreadyversion:
		unaccented = stripaccents(line[workingcolumn])
		line = line + [unaccented]
		dbreadyversion.append(line)
		
	return dbreadyversion


def dbfindhypens(dbunreadyversion):
	"""

	sample in:
		['2', [('0', '6'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], 'ἀγῶϲι πρόνοιαν· ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ Ἰτα-', 'ἀγῶϲι πρόνοιαν ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ ἰτα-', 'αγωϲι προνοιαν οϲ και τοτε περαιουμενοϲ ναυϲιν εϲ ιτα-']
	sample out:
		['2', [('0', '6'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], 'ἀγῶϲι πρόνοιαν· ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ Ἰτα-', 'ἀγῶϲι πρόνοιαν ὃϲ καὶ τότε περαιούμενοϲ ναυϲὶν ἐϲ ἰταλίαν', 'αγωϲι προνοιαν οϲ και τοτε περαιουμενοϲ ναυϲιν εϲ ἰταλίαν']
		
	:param dbunreadyversion:
	:return:
	"""
	dbreadyversion = []
	workingcolumn = 3
	previous = dbunreadyversion[0]

	for line in dbunreadyversion[1:]:
		try:
			# a problem if the line is empty: nothing to split
			# a good opportunity to skip adding a line to dbreadyversion
			prevend = previous[workingcolumn].rsplit(None, 1)[1]
			if prevend[-1] == '-':
				thisstart = line[workingcolumn].split(None, 1)[0]
				hyphenated = prevend[:-1] + thisstart
				if len(hyphenated) > 0:
					newlines = consolidatecontiguouslines(previous, line, hyphenated)
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
	
	if dbunreadyversion[-1][workingcolumn] != '' and dbunreadyversion[-1][workingcolumn] != ' ':
		dbreadyversion.append(dbunreadyversion[-1])
	
	return dbreadyversion


def dbfindannotations(dbunreadyversion):
	workingcolumn = 2
	dbreadyversion = []
	search = re.compile(r'<hmu(_|_metadata_)annotations value="(.*?)" />')
	for line in dbunreadyversion:
		notes = re.findall(search, line[workingcolumn])
		notes = [n[1] for n in notes]
		notes = [n for n in notes if n]
		notes = list(set(notes))

		line[workingcolumn] = re.sub(search,'',line[workingcolumn])
			
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


def hmutonbsp(dbunreadyversion):
	"""
	pseudo-markup into html
	this is a place where some commitments that have been deferred will get made
	obviously you could put all of this in earlier for the sake of efficiency,
	but handling this here and now is convenient: one stop shopping w/out tripping up the parser earlier
	:param dbunreadyversion:
	:return:
	"""
	workingcolumn = 2
	dbreadyversion = []
	bqs = re.compile(r'<hmu_blank_quarter_spaces quantity="(\d{1,})" />')
	
	for line in dbunreadyversion:
		line[workingcolumn] = re.sub(bqs, quarterspacer, line[workingcolumn])
		line[workingcolumn] = re.sub(r'<hmu_standalone_tabbedtext />', r'&nbsp;&nbsp;&nbsp;&nbsp; ', line[workingcolumn])
		dbreadyversion.append(line)
	
	return dbreadyversion


def quarterspacer(matchgroup):
	"""
	take a found collection of quarter spaces and turn them into spaces
	:param matchgroup:
	:return: a digit as a string
	"""
	digit = int(matchgroup.group(1))
	spaces = divmod(digit,4)[0]
	substitution = ''
	for i in range(0,spaces):
		substitution += '&nbsp;'

	return substitution


def noleadingortrailingwhitespace(dbunreadyversion):
	"""
	get rid of whitespace at ends of columns
	otherwise HipparchiaServer is constantly doing this
	:param dbunreadyversion:
	:return:
	"""
	dbreadyversion = []
	
	for line in dbunreadyversion:
		for column in [2,3,4]:
			line[column] = re.sub(r'(^\s|\s$)','',line[column])
		dbreadyversion.append(line)
	
	return dbreadyversion


def consolidatecontiguouslines(previousline, thisline, hypenatedword):
	"""
	helper function for the stripped line column: if a previousline ends with a hypenated word:
		put the whole word at line end
		drop the half-word from the start of thisline
	:param previousline:
	:param thisline:
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
	
	p = p[:-1] + [stripaccents(hypenatedword)]
	t = t[1:]
	
	p = ' '.join(p)
	t = ' '.join(t)
	
	pl = pl + [p]
	tl = tl + [t]
	
	
	newlines = {}
	newlines['p'] = pl
	newlines['l'] = tl

	return newlines
	
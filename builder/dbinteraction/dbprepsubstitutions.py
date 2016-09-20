import re
import string

from builder.parsers.betacode_to_unicode import stripaccents


def dbprepper(dbunreadyversion):
	"""
	pull out markups, etc
	:param dbunreadyversion:
	:return:
	"""
	dbunreadyversion = halflinecleanup(dbunreadyversion)
	dbunreadyversion = dbpdeincrement(dbunreadyversion)
	dbunreadyversion = dbstrippedliner(dbunreadyversion)
	dbunreadyversion = dbfindhypens(dbunreadyversion)
	dbunreadyversion = dbfindcitations(dbunreadyversion)
	dbunreadyversion = hmutonbsp(dbunreadyversion)
	dbreadyversion = dbunreadyversion
	return dbreadyversion


def halflinecleanup(dbunreadyversion):
	# this painful next kludge is a function of half-lines that do multiple sets and level shifts in rapid succession and leave the actual text on 'line 1' unless you do something drastic:
	# ['6', [('0', '1099'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 /><hmu_blank_quarter_spaces quantity="63" /> ἠρινά τε βοϲκόμεθα παρθένια ']
	# ['6', [('0', '1100'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1100-11 />']
	# ['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '2'), ('4', '1'), ('5', '1')], '<hmu_increment_level_3_by_1 />']
	# ['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_3_to_1 /><hmu_blank_quarter_spaces quantity="63" /> λευκότροφα μύρτα Χαρίτων τε κηπεύματα. ']
	# ['6', [('0', '1100'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1100-11 />']
	# ['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '2'), ('4', '1'), ('5', '1')], '<hmu_increment_level_3_by_1 />']
	# ['6', [('0', '1'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_3_to_1 /><hmu_blank_line />']
	# ['6', [('0', '1102'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_set_level_0_to_1102 /><hmu_blank_quarter_spaces quantity="38" /> Τοῖϲ κριταῖϲ εἰπεῖν τι βουλόμεϲθα τῆϲ νίκηϲ πέρι, ']

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
			# print('mem',line)
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
	# a formatting stripper
	# example:
	# ['1', [('0', '6'), ('1', '2'), ('2', '30'), ('3', '1'), ('4', '1'), ('5', '1')], '<hmu_increment_level_0_by_1 />instructis quam latissime potuit porrecta equitum pe']

	workingcolumn = 2

	#setter = re.compile(r'<hmu_set_level_\d_to_[A-Za-z0-9]{1,}\s/>')
	# wont catch '<hmu_set_level_1_to_98* />'
	setter = re.compile(r'<hmu_set_level_\d_to_.*?\s/>')
	adder = re.compile(r'<hmu_increment_level_(\d)_by_1\s/>')
	blocker = re.compile(r'<hmu_cd_assert_(.*?)>')
	eob = re.compile(r'<hmu_end_of_cd_block_re-initialize_key_variables />')
	# empty = r'(?<!*)\s{0,1}(?=!*)'
		
	dbreadyversion = []

	for line in dbunreadyversion:
		line[workingcolumn] = re.sub(setter, '', line[workingcolumn])
		line[workingcolumn] = re.sub(adder, '', line[workingcolumn])
		line[workingcolumn] = re.sub(blocker, '', line[workingcolumn])
		line[workingcolumn] = re.sub(eob, '', line[workingcolumn])
		# do this late because it won't be empty before prior scrubbing
		# what are the chances that an empty line contained useful level codes?
		# if re.search(empty, line[workingcolumn]):
		#	pass
		# else:
		#	dbreadyversion.append(line)
		if line[workingcolumn] != '':
			dbreadyversion.append(line)

	return dbreadyversion


def dbstrippedliner(dbunreadyversion):
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
	squarebrackets = re.compile(r'\[.*?\]')
	straydigits = re.compile(r'\d')
	# sadly can't nuke :punct: because we need hyphens
	straypunct = re.compile('[\<\>\{\}⟪⟫]')
	dbreadyversion = []
	workingcolumn = 2

	# tempting to strip delenda here, but that presupposes you caught all the number-brackets before
	# '[delenda]' vs '[2 formatted_text...'

	for line in dbunreadyversion:
		# in two parts because it is possible that the markup jumps lines
		clean = re.sub(markup, '', line[workingcolumn])
		clean = re.sub(unmarkup, '', clean)
		clean = re.sub(straydigits, '', clean)
		clean = re.sub(squarebrackets, '', clean)
		clean = re.sub(span, '', clean)
		clean = re.sub(unspan, '', clean)
		clean = re.sub(straypunct, '', clean)
		clean = re.sub(combininglowerdot, '', clean)
		line.append(clean)
		dbreadyversion.append(line)

	dbunreadyversion = dbreadyversion
	dbreadyversion = []
	workingcolumn = 3

	# capitalization can be made to still matter; does that matter?
	# you won't get the first word of the iliad right unless you search for capital Mu
	# it seems like you will seldom wish you had caps and that remembering to handle them as a casual user is not so hot
	# nevertheless, the inset citations all have caps; so they will look stupid
	# just decapitalize the greek and not the latin?
	# latin searches should be made case insensitive, though
	# kill all non-word chars other than periods and semicolons?

	for line in dbunreadyversion:
		line[workingcolumn] = stripaccents(line[workingcolumn])
		dbreadyversion.append(line)

	return dbreadyversion


def dbfindhypens(dbunreadyversion):
	dbreadyversion = []
	workingcolumn = 2
	previous = dbunreadyversion[0]
	punct = re.compile('[%s]' % re.escape(string.punctuation+'“”·'))
	markup = re.compile(r'<(|/).*?>')

	for line in dbunreadyversion[1:]:
		try:
			# a problem if the line is empty: nothing to split
			# a good opportunity to skip adding a line to dbreadyversion
			prevend = previous[workingcolumn].rsplit(None, 1)[1]
			if prevend[-1] == '-':
				# kill markup the sneaky way
				e = prevend.split('>')
				prevend = e[-1]
				thisstart = line[workingcolumn].split(None, 1)[0]
				s = thisstart.split('<')
				thisstart = s[0]
				hyphenated = prevend[:-1] + thisstart
				# hyphenated = re.sub(markup,'',hyphenated)
				#if re.search(punct,hyphenated[-1]) != None:
				#	hyphenated = hyphenated[:-1]
				hyphenated = re.sub(punct, '', hyphenated)
				stripped = stripaccents(hyphenated)
				previous.append(hyphenated+' '+stripped)
			elif prevend[-2:-1] == '- ':
				# kill markup the sneaky way
				e = prevend.split('>')
				prevend = e[-1]
				thisstart = line[workingcolumn].split(None, 1)[0]
				s = thisstart.split('<')
				thisstart = s[0]
				hyphenated = prevend[:-2] + thisstart
				# hyphenated = re.sub(markup, '', hyphenated)
				# if re.search(punct,hyphenated[-1]) != None:
				#	hyphenated = hyphenated[:-1]
				hyphenated = re.sub(punct, '', hyphenated)
				stripped = stripaccents(hyphenated)
				previous.append(hyphenated+' '+stripped)
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


def dbfindcitations(dbunreadyversion):
	workingcolumn = 2
	dbreadyversion = []
	search = re.compile(r'<hmu_annotations value="(.*?)" />')
	for line in dbunreadyversion:
		citation = re.findall(search, line[workingcolumn])
		line[workingcolumn] = re.sub(search,'',line[workingcolumn])
		try:
			# i wonder about multiple citations...
			citations = ','.join(citation)
			line.append(citations)
		except:
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


#
# matchgroup substitutions
#

def hmustandalonesubstitutes(match):
	val = match.group(1)
	
	substitutions = {
		'blank_line': r'<br />',
		'break_in_text': r'<span class="italic>[break in text for unknown length]<span>',
		'omitted_graphic_marker': r'',
		'column_end': r'',
		'mid_line_citation_boundary': r'———',
		'endofpage': r'',
		'linetoolongforscreen': r'',
		'stacked_text_lower': r'',
		'stacked_text_upper': r'',
		'start_of_columnar_text': r'',
		'tabbedtext': r'&nbsp;&nbsp;&nbsp;&nbsp; '
	}
	
	if 'set_level' in val:
		substitute = val
	else:
		if val in substitutions:
			substitute = substitutions[val]
		else:
			substitute = '<unhandled_hmustandalone_cleanup value="' + match.group(1) + '" />'
			print(substitute)
	
	return substitute


def hmuopenandclosesubstitutes(matchgroups):
	"""
	send me 3 match groups
	i test if 1 = 3 and so we have a formatting bracket
	:param matchgroups:
	:return:
	"""
	
	substitutions = {
		'expanded_latin_text': [r'<span class="expandedtext">', r'</span>'],
		'expanded_text': [r'<span class="expandedtext">', r'</span>'],
		'font_shift_superscript': [r'<span class="superscript">', r'</span>'],
		'inset_diagram': [r'<span class="diagram">', r'</span>'],
		'interlinear_text': [r'<span class="interlineartext">', r'</span>'],
		'interlinear_marginalia': [r'<span class="interlinearmarginalia">', r'</span>'],
		'marginal_text': [r'<span class="marginaltext">', r'</span>'],
		'overline_and_underline': [r'<span class="overunder">', r'</span>'],
		'poetic_text': [r'<span class="poetictext">', r'</span>'],
		'quoted_text': [r'<span class="quotedtext">', r'</span>'],
		'reference_in_scholium': [r'<span class="scholium">', r'</span>'],
		'roman_in_a_greek_text': r'',
		'servius_bracket': r'<span class="serviusformatting">',
		'shift_font_to_roman value="latin_bold_italic"': r'<span class="bolditalic">',
		'shift_font_to_roman value="latin_bold"': r'<span class="bold">',
		'shift_font_to_roman value="latin_italic"': r'<span class="italic">',
		'shift_font_to_roman value="latin_smaller_than_normal_italic"': r'<span class="smallerthannormalitalic">',
		'shift_font_to_roman value="latin_smaller_than_normal_superscript"': r'<span class="smallerthannormalsuperscript">',
		'shift_font_to_roman value="latin_smaller_than_normal"': r'<span class="smallerthannormal">',
		'shift_font_to_roman value="latin_subscript"': r'<span class="subscript">',
		'shift_font_to_roman value="latin_superscript"': r'<span class="superscript">',
		'shift_font_to_roman value="normal"': r'<span class="normal">',
		'shift_font_to_roman value="roman_numerals"': r'<span class="romannumerals">',
		'shift_font_to_roman value="small_capitals_italic"': r'<span class="smallcapsitalic">',
		'shift_font_to_roman value="small_capitals"': r'<span class="smallcaps">',
		'shift_font_to_subscript': r'<span class="subscript">',
		'shift_font_to_superscript': r'<span class="superscript">',
		'shift_greek_font value="bold"': r'<span class="bold">',
		'shift_greek_font value="extra_large"': r'<span class="extralarge">',
		'shift_greek_font value = "greek_uncial"': r'<span class="uncial">',
		'shift_greek_font value="italic"': r'<span class="italic">',
		'shift_greek_font value="larger_than_normal"': r'<span class="largerthannormal">',
		'shift_greek_font value="regular"': r'<span class="regular">',
		'shift_greek_font value="smaller_than_normal_superscript"': r'<span class="smallsuperscript">',
		'shift_greek_font value="smaller_than_normal"': r'<span class="smallerthannormal">',
		'shift_greek_font value="superscript"': r'<span class="superscript">',
		'small_latin_capitals': r'<span class="smlatcaps">',
		'speaker': r'<span class="speaker">',
		'speakers': r'<span class="speaker">',
		'stacked_text_lower': r'<span class="stackedtextlower">',
		'stacked_text_upper': r'<span class="stackedtextupper">',
		'start_of_columnar_text': r'<span class="columnartext">',
		'text_printed_in_a_non_standard_direction': r'<span class="reversed">',
		'textual_lemma': r'<span class="textuallemma">',
		'title': r'<span class="title">'
	}
	
	if matchgroups.group(1) == matchgroups.group(3):
		print('balanced:', matchgroups.group(1))
	
	if 'set_level' in val:
		substitute = val
	elif 'unhandled' in val:
		substitute = val
	else:
		if val in substitutions:
			substitute = substitutions[val]
		else:
			substitute = '<unhandled_hmuopen_cleanup value="' + match.group(1) + '" />'
			print(substitute)
	
	return substitute


def hmuopensubstitutes(match):
	val = match.group(1)
	
	substitutions = {
		'expanded_latin_text': r'<span class="expandedtext">',
		'expanded_text': r'<span class="expandedtext">',
		'font_shift_superscript': r'<span class="superscript">',
		'inset_diagram': r'<span class="diagram">',
		'interlinear_text': r'<span class="interlineartext">',
		'interlinear_marginalia': r'<span class="interlinearmarginalia">',
		'marginal_text': r'<span class="marginaltext">',
		'overline_and_underline': r'<span class="overunder">',
		'poetic_text': r'<span class="poetictext">',
		'quoted_text': r'<span class="quotedtext">',
		'reference_in_scholium': r'<span class="scholium">',
		'roman_in_a_greek_text': r'',
		'servius_bracket': r'<span class="serviusformatting">',
		'shift_font_to_roman value="latin_bold_italic"': r'<span class="bolditalic">',
		'shift_font_to_roman value="latin_bold"': r'<span class="bold">',
		'shift_font_to_roman value="latin_italic"': r'<span class="italic">',
		'shift_font_to_roman value="latin_smaller_than_normal_italic"': r'<span class="smallerthannormalitalic">',
		'shift_font_to_roman value="latin_smaller_than_normal_superscript"': r'<span class="smallerthannormalsuperscript">',
		'shift_font_to_roman value="latin_smaller_than_normal"': r'<span class="smallerthannormal">',
		'shift_font_to_roman value="latin_subscript"': r'<span class="subscript">',
		'shift_font_to_roman value="latin_superscript"': r'<span class="superscript">',
		'shift_font_to_roman value="normal"': r'<span class="normal">',
		'shift_font_to_roman value="roman_numerals"': r'<span class="romannumerals">',
		'shift_font_to_roman value="small_capitals_italic"': r'<span class="smallcapsitalic">',
		'shift_font_to_roman value="small_capitals"': r'<span class="smallcaps">',
		'shift_font_to_subscript': r'<span class="subscript">',
		'shift_font_to_superscript': r'<span class="superscript">',
		'shift_greek_font value="bold"': r'<span class="bold">',
		'shift_greek_font value="extra_large"': r'<span class="extralarge">',
		'shift_greek_font value = "greek_uncial"': r'<span class="uncial">',
		'shift_greek_font value="italic"': r'<span class="italic">',
		'shift_greek_font value="larger_than_normal"': r'<span class="largerthannormal">',
		'shift_greek_font value="regular"': r'<span class="regular">',
		'shift_greek_font value="smaller_than_normal_superscript"': r'<span class="smallsuperscript">',
		'shift_greek_font value="smaller_than_normal"': r'<span class="smallerthannormal">',
		'shift_greek_font value="superscript"': r'<span class="superscript">',
		'small_latin_capitals': r'<span class="smlatcaps">',
		'speaker': r'<span class="speaker">',
		'speakers': r'<span class="speaker">',
		'stacked_text_lower': r'<span class="stackedtextlower">',
		'stacked_text_upper': r'<span class="stackedtextupper">',
		'start_of_columnar_text': r'<span class="columnartext">',
		'text_printed_in_a_non_standard_direction': r'<span class="reversed">',
		'textual_lemma': r'<span class="textuallemma">',
		'title': r'<span class="title">'
	}
	
	if 'set_level' in val:
		substitute = val
	elif 'unhandled' in val:
		substitute = val
	else:
		if val in substitutions:
			substitute = substitutions[val]
		else:
			substitute = '<unhandled_hmuopen_cleanup value="' + match.group(1) + '" />'
			print(substitute)
	
	return substitute

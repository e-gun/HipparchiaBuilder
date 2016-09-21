# -*- coding: utf-8 -*-
import re

from builder.parsers.swappers import highunicodetohex, hutohxgrouper, hextohighunicode, bitswapchars
from .betacode_to_unicode import parsegreekinsidelatin
from .citation_builder import citationbuilder


##
## hex datafile and betacode cleanup
##
## [nb: some regex happens in db.py as prep for loading]


def earlybirdsubstitutions(texttoclean):
	# try to get out in front of some of the trickiest bits
	# note that you can't use quotation marks in here
	textualmarkuptuples = []
	
	betacodetuples = (
		(r'<(?!\d)',r'‹'), # '<': this one is super-dangerous: triple-check
		(r'>(?!\d)', u'›'), # '>': this one is super-dangerous: triple-check
		(r'_', u' \u2014 '),  # doing this without spaces was producing problems with giant 'hyphenated' line ends
		(r'\s\'', r' ‘'),
		(r'\'( |\.|,|;)', r'’\1'),
	)
	
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


def replaceaddnlchars(texttoclean):
	"""
	purge #, %, [, {, < markup
	this method is 10x faster than going through over and over again:
		took: 0.20757389068603516 [old]
		took: 0.020704030990600586 [new]
	:param texttoclean:
	:return:
	"""
	
	#hexnearmarkup = re.compile(r'(\d)(0x[0-9a-f][0-9a-f]\s)')
	#texttoclean = re.sub(hexnearmarkup, r'\1 \2', texttoclean)
	
	texttoclean = re.sub(r'\^(\d{1,2})+', r'<hmu_blank_quarter_spaces quantity="\1" /> ', texttoclean)
	
	pounds = re.compile(r'\#(\d{1,4})')
	texttoclean = re.sub(pounds, poundsubstitutes, texttoclean)
	texttoclean = re.sub(r'\#', u'\u0374', texttoclean)
	
	percents = re.compile(r'\%(\d{1,3})')
	texttoclean = re.sub(percents, percentsubstitutes, texttoclean)
	texttoclean = re.sub(r'\%', u'\u2020', texttoclean)
	
	ltsqbrackets = re.compile(r'\[(\d{1,2})')
	texttoclean = re.sub(ltsqbrackets, leftbracketsubstitutions, texttoclean)
	
	rtsqbrackets = re.compile(r'\](\d{1,2})')
	texttoclean = re.sub(rtsqbrackets, rightbracketsubstitutions, texttoclean)
	
	atsigns = re.compile(r'@(\d{1,2})')
	texttoclean = re.sub(atsigns, atsignsubstitutions, texttoclean)
	texttoclean = re.sub(r'@', r'<hmu_standalone_tabbedtext />', texttoclean)
	
	ltcurlybracket = re.compile(r'\{(\d{1,2})')
	texttoclean = re.sub(ltcurlybracket, ltcurlybracketsubstitutes, texttoclean)
	texttoclean = re.sub(r'\{', r'<span class="speaker">', texttoclean)
	
	rtcurlybracket = re.compile(r'\}(\d{1,2})')
	texttoclean = re.sub(rtcurlybracket, rtcurlybracketsubstitutes, texttoclean)
	texttoclean = re.sub(r'\}', r'</span>', texttoclean)
	
	ltanglebracket = re.compile(r'\<(\d{1,2})')
	texttoclean = re.sub(ltanglebracket, ltanglebracketsubstitutes, texttoclean)
	
	rtanglebracket = re.compile(r'\>(\d{1,2})')
	texttoclean = re.sub(rtanglebracket, rtanglebracketsubstitutes, texttoclean)
	
	
	return texttoclean


def replacegreekmarkup(texttoclean):
	"""
	turn $NN into markup
	:param texttoclean:
	:return:
	"""
	dollars = re.compile(r'\$(\d{1,2})(.*?)(\$\d{0,1})')
	texttoclean = re.sub(dollars, dollarssubstitutes, texttoclean)
	
	# these strays are rough
	#texttoclean = re.sub(r'\$(.*?)\$', '<hmu_shift_greek_font value="regular">\1</hmu_shift_greek_font>', texttoclean)
	
	return texttoclean


def replacelatinmarkup(texttoclean):
	"""
	turn &NN into markup
	:param texttoclean:
	:return:
	"""
	ands = re.compile(r'\&(\d{1,2})(.*?)(\&\d{0,1})')
	texttoclean = re.sub(ands, andsubstitutes, texttoclean)
	
	#texttoclean = re.sub(r'\&(.*?)\&', r'<hmu_shift_latin_font value="regular">\1</hmu_shift_latin_font>', texttoclean)
	
	anddollars = re.compile(r'\&(\d{1,2})(.*?)(\$\d{0,1})')
	texttoclean = re.sub(anddollars, andsubstitutes, texttoclean)
	
	# these strays are rough
	# texttoclean = re.sub(r'\&(.*?)\&', r'<hmu_shift_latin_font value="regular">\1</hmu_shift_latin_font>', texttoclean)
	
	return texttoclean
	

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
		(r'\\\{', r'{'),
		(r'\\\}', r'}'),
	)

	for i in range(0, len(betacodetuples)):
		texttoclean = re.sub(betacodetuples[i][0], betacodetuples[i][1], texttoclean)

	return texttoclean


def debughostilesubstitutions(texttoclean):
	"""
	all sorts of things will be hard to figure out if you run this suite
	but it does make many things 'look better' even if there are underlying problems.
	:param texttoclean:
	:return:
	"""
	betacodetuples = (
		# a format shift code like '[3' if followed by a number that is supposed to print has an intervening ` to stop the TLG parser
		(r'\$',r''),
		(r'\&',r'')
	)

	for i in range(0, len(betacodetuples)):
		texttoclean = re.sub(betacodetuples[i][0], betacodetuples[i][1], texttoclean)

	return texttoclean


#
# matchgroup substitutions
#

def quotesubstitutesa(match):
	"""
	turn "N into unicode
	have to do this first because html quotes are going to appear soon
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		1: u'\u201e',
		2: 'QUOTE2',
		3: 'QUOTE3',
		4: 'u\u201a',
		5: 'u\u201b',
		6: 'QUOTE6',
		7: 'QUOTE7',
		8: 'QUOTE8'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_quote_markup value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def quotesubstitutesb(match):
	"""
	turn "N into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	core = match.group(2)
	
	substitutions = {
		2: ['“', '”'],
		3: ['‘', '’'],
		6: ['«', '»'],
		7: ['‹', '›'],
		8: ['“', '„'],
	}
	
	if val in substitutions:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	else:
		substitute = '<hmu_unhandled_quote_markup value="' + match.group(1) + '" />' + core
		print('\t',substitute)
	
	return substitute


def poundsubstitutes(match):
	"""
	turn # into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		# u'\u',
		# 1326: idiosync magical char
		1136: u'\u2112',
		1135: u'\u002f\u002f',
		1126: u'\u004f',
		1115: u'\u007c',
		1110: u'\u002d',
		1109: u'\u003d',
		1108: u'\u0058\u0036',
		1107: u'\u0053\u0335\u0053\u0336',
		1105: u'\u004d\u030a',
		1104: u'S\u0038', #  deprecated, use &S%162$
		1103: u'\u0323\u0313',
		1102: r'H',
		1101: r'IS',
		1100: u'\u2183',
		751: u'\u0661', # arabic-indic digits: only '1' covered ATM
		563: u'\u1d242',
		556: u'\u2629',
		534: u'\u0302',
		532: u'\u2e12',
		523: u'\u2e13',
		524: u'u2297',
		# 522: u'\u', # markup <rotate> 0397
		504: u'\u2e0e',
		508: u'\u203b',
		507: u'\u2e14',
		501: r'πιθ', # abbreviation for πιθανόν
		476: u'\u0283',
		465: u'\u2627',
		461: u'\u007c',
		460: u'\u2014',
		459: u'\u00b7',
		458: u'\u0387',
		456: u'\u2e0e',
		454: u'\u2e10',
		453: u'\u2e11',
		452: u'\u2310',
		313: u'\u2e0e',
		310: u'\u2e0e',
		305: u'\u2e0e',
		303: u'›',
		223: u'\u2605',
		220: u'\u260d',
		219: u'\u2649',
		218: u'\u2652',
		217: u'\u2653',
		216: u'\u264b',
		215: u'\u264a',
		214: u'\u264e',
		213: u'\u2648',
		212: u'\u264c',
		211: u'\u2651',
		210: u'\u2642',
		209: u'\u263e',
		208: u'\u263f',
		207: u'\u2609',
		206: u'\u2644',
		205: u'\u2650',
		204: u'\u2640',
		200: u'u\2643',
		172: u'𐅵',
		171: u'𐅵',
		161: u'𐅵',
		166: u'\u2a5a',
		162: u'\u25a1',
		165: u'\u00d7',
		169: u'𐅵',
		150: u'\u221e',
		131: u'\u10177',
		130: u'\u1018a',
		117: u'\u10183',
		116: u'\u1017c',
		106: u'\u10184',
		# 105: 'idiosyn'
		104: u'\u10182\u03bf', # the omicron is supposed to be superscript too
		103: u'\u039b\u0338',
		101: u'\u1017b',
		100: u'\u10186',
		73: u'\u205a',
		25: u'?',
		23: u'u\03d9',
		22: u'\u0375',
		21: u'𐅵',
		20: u'𐅵',
		19: u'\u0300',
		74: u'\u205d',
		# homeric editorial marks
		16: u'\u03fe',
		15: u'\u003e',
		14: u'\u2e16',
		13: u'\u203b',
		12: u'\u2014',
		11: u'\u03ff',
		10: u'\u03fd',
		9: u'\u0301',
		18: u'《',
		6: u'\u2e0f',
		8: u'\u2e10',
		5: u'\u03e1',
		4: u'\u03d9',
		3: u'\u03d9',
		2: u'\u03da',
		1: u'\u03df'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_pound_sign value="'+match.group(1)+'" />▦'
		print('\t',substitute)
	
	return substitute


def percentsubstitutes(match):
	"""
	turn % into unicode
	
	:param match:
	:return:
	"""
	val = int(match.group(1))
	
	substitutions = {
		# u'\u',
		162: u'\u0338',
		# 157: flipped dagger
		127: u'\u032f',
		150: u'\u007c',
		149: u'\u0328',
		148: u'\u030c',
		147: u'\u030a',
		146: u'\u00b7',
		145: u'\u2013\u0301',
		141: u'\u23d6',
		110: u'\u25cb',
		109: u'\u00b7',
		108: u'\u00b1',
		107: u'\u007e',
		106: u'\u224c',
		101: u'\u0023', # had best do pounds before percents since this is '#'
		100: u'\u003b',
		99: u'\u2248',
		98: u'\u0022',
		95: u'\u1dc1',
		93: u'\u1dc0',
		94: u'\u0307',
		91: u'\u0485',
		80: u'\u0076\u002E', # supposed to put the 'v' in italics too
		49: u'\u23d1\u23d1\u23d1',
		48: u'u23d1\u23d1',
		47: u'\u10111',
		40: u'\u23d1',
		41: u'\u2013',
		42: u'\u23d5',
		43: u'\u00d7',
		44: u'\u23d2',
		45: u'\u23d3',
		46: u'\u23d4',
		38: u'\u1fdf',
		35: u'\u1fce',
		34: u'\u1fc0',
		33: u'\u0060', # look out for future problems: `
		32: u'\u00b4', # look out for future problems: ´
		31: u'u\02bd',
		30: u'\u02bc',
		29: u'\u0323\u0323',
		28: u'\u0308',
		27: u'\u0306',
		26: u'\u0304',
		25: u'\u0327',
		24: u'\u0342',
		20: u'\u0301',
		19: u'\u2013',
		18: u'\u0025', # look out for future problems: '
		17: u'\u2016',
		15: u'\u02c8',
		14: u'\u00a7',
		12: u'\u002a', # look out for future problems: *
		11: u'\u2022',
		10: u'\u003a',
		9: u'\u0026',
		7: u'\u002b',
		3: u'\u002f',
		2: u'\u002a',
		4: u'\u0021',
		5: u'\u007c',
		6: u'\u003d',
		1: u'\u003f'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_percent_sign value="' + match.group(1) + '" />▩'
		print('\t',substitute)
	
	return substitute


def leftbracketsubstitutions(match):
	"""
	turn [N into unicode
	:param match:
	:return:
	"""


	val = int(match.group(1))

	substitutions = {
		# u'\u',
		23: u'u\23a9',
		22: u'u\23a8',
		21: u'u\23aa',
		20: u'u\23a7',
		17: u'\u230a\u230a',
		14: u'\u007c\u003a',
		12: u'\u2192',
		13: u'\u005b', # supposed to be italic as well
		11: u'u\208d',
		9: u'\u2027',
		8: '⌊',
		7: '⌈',
		6: '⌈',
		5: '⌊',
		4: '⟦',
		3: '❴',
		2: '⟪',
		# 2: '‹',
		1: '('
		}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_left_bracket value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def rightbracketsubstitutions(match):
	"""
	turn ]N into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		# u'\u',
		17: u'\u230b\u230b',
		14: u'\003a\u007c',
		13: u'\u005d',  # supposed to be italic as well
		11: u'u\208e',
		9: u'\u2027',
		8: '⌋',
		7: '⌉',
		6: '⌉',
		5: '⌋',
		4: '⟧',
		3: '❵',
		2: '⟫',
		# 2: '›',
		1: ')'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_right_bracket value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def atsignsubstitutions(match):
	"""
	turn @N into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		73: r'<span class="poetictext">',
		74: r'</span>',
		70: r'<span class="quotedtext">',
		71: r'</span>',
		30: r'<hmu_standalone_start_of_stanza />',
		20: r'<hmu_standalone_start_of_columnar_text />',
		21: r'</span>',
		12: r'<hmu_standalone_subcellindicator />',
		11: r'<hmu_standalone_tablecellindicator />',
		10: r'<hmu_standalone_linetoolongforscreen />',
		# problem: 0x80 KRIQEI\S DE\ U(PO\ TW=N *PER- @10x80 SW=N KAI\ BASILEU/SAS, *CE/R-0x80
		# that is @1 + 0x80 and not @10
		# moving over to █⑧⓪ eliminates this whole class of parse problem (while creating another sort of problem)
		9: r'<span class="breakintext">[break in text for unknown length]</span>',
		8: r'———', # hmu_standalone_mid_line_citation_boundary
		7: r'——————',
		6: r'<br />',
		5: r'</span>',
		4: r'<hmu_standalone_table />',
		3: r'<hmu_standalone_omitted_graphic_marker />',
		2: r'<hmu_standalone_column_end />',
		1: r'<hmu_standalone_endofpage />'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_atsign value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def ltcurlybracketsubstitutes(match):
	"""
	turn {N into markup or unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		43: r'<span class="serviusformatting">',
		41: r'<span class="stagedirection">',
		40: r'<span class="speaker">',
		10: u'\u0332',
		# 4: Unconventional Form Written by Scribe
		3: r'<span class="scholium">',
		2: r'<span class="marginaltext">',
		1: r'<span class="title">'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_ltcurlybracket value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def rtcurlybracketsubstitutes(match):
	"""
	turn {N into markup or unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		43: r'</span>', # hmu_servius_bracket
		41: r'</span>', # hmu_stage_direction
		40: r'</span>', # hmu_speaker
		3: r'</span>', # hmu_reference_in_scholium
		2: r'</span>', # hmu_marginal_text
		1: r'</span>' # hmu_title
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_rtcurlybracket value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def ltanglebracketsubstitutes(match):
	"""
	turn <N into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		1: '',
		2: u'\u2035',
		16: u'\u2035',
		19: u'\u2035',
		3: u'\u0361',
		4: u'\u035c',
		5: u'\u035d',
		6: r'<span class="superscript">', # hmu_shift_font_to_superscript
		7: r'<span class="subscript">', # hmu_shift_font_to_subscript
		8: '',
		9: r'<span class="lemma">', # hmu_textual_lemma
		10: r'<span class="stackedlower">', # hmu_stacked_text_lower
		11: r'<span class="stackedupper">', # hmu_stacked_text_upper
		12: r'<span class="nonstandarddirection">',
		14: r'<span class="interlineartext">',
		15: r'<span class="interlinearmarginalia">', # hmu_interlinear_marginalia
		17: '', # Combining Double Underline
		20: r'<span class="expanded">', # hmu_expanded_text
		21: r'<span class="expanded">', # hmu_latin_expanded_text
		30: r'<span class="overline">', # Combining Overline and Dependent Vertical Bars
		31: r'<span class="strikethrough">',
		32: r'<span class="overunder">', # hmu_overline_and_underline
		70: r'<span class="diagram">', # hmu_inset_diagram
		71: r'<span class="diagramsection">', # hmu_inset_diagram
		72: r'<span class="diagramrelation">', # hmu_logical_relationship_in_diagram
		73: r'<span class="diagramlvl03">',
		74: r'<span class="diagramlvl04">'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_ltangle value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def rtanglebracketsubstitutes(match):
	"""
	turn >N into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	
	substitutions = {
		1: u'\u0332',
		2: u'\u2032',
		16: u'\u2032',
		19: u'\u2032',
		3: '',
		4: '',
		5: '',
		6: r'</span>', # hmu_shift_font_to_superscript
		7: r'</span>', # hmu_shift_font_to_subscript
		8: u'\u0333',
		9: r'</span>', # hmu_textual_lemma
		10: r'</span>', # hmu_stacked_text_lower
		11: r'</span>', # hmu_stacked_text_upper
		12: r'</span>', # nonstandarddirection
		13: r'<hmu_standalone_singlelinespacing_in_doublespacedtext />',
		14: r'</span>', # interlineartext
		15: r'</span>', # hmu_interlinear_marginalia
		17: u'u\0333',
		20: r'</span>', # hmu_expanded_text
		21: r'</span>', # hmu_expanded_text
		30 : '</span>', # Combining Overline and Dependent Vertical Bars
		31: r'</span>', # strikethrough
		32: r'</span>', # hmu_overline_and_underline
		70: r'</span>', # hmu_inset_diagram
		71: r'</span>', # hmu_discrete_section_of_diagram
		72: r'</span>', # hmu_logical_relationship_in_diagram
		73: r'</span>', #<span class="diagramlvl03">',
		74: r'</span>'  #<span class="diagramlvl04">'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_rtangle value="' + match.group(1) + '" />'
		print('\t',substitute)
	
	return substitute


def dollarssubstitutes(match):
	"""
	turn $NN...$ into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	core = match.group(2)
	
	substitutions = {
		70: [r'<span class="uncial">', r'</span>'],
		40: [r'<span class="extralarge">', r'</span>'],
		20: [r'<span class="largerthannormal">', r'</span>'],
		15: [r'<span class="smallerthannormalsubscript">', r'</span>'],
		14: [r'<span class="smallerthannormalsuperscript">', r'</span>'],
		11: [r'<span class="smallerthannormalbold">', r'</span>'],
		10: [r'<span class="smallerthannormal">', r'</span>'],
		9: [r'<span class="regular">', r'</span>'],
		8: [r'<span class="vertical">', r'</span>'],
		5: [r'<span class="subscript">', r'</span>'],
		4: [r'<span class="superscript">', r'</span>'],
		3: [r'<span class="italic">', r'</span>'],
		2: [r'<span class="bolditalic">', r'</span>'],
		1: [r'<span class="bold">', r'</span>']
	}
	
	if val in substitutions:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	else:
		substitute = '<hmu_unhandled_greek_font_shift value="' + match.group(1) + '" />' + core
		print('\t',substitute)
	
	return substitute


def andsubstitutes(match):
	"""
	turn &NN...& into unicode
	:param match:
	:return:
	"""
	
	val = int(match.group(1))
	core = match.group(2)
	
	substitutions = {
		14: [r'<span class="smallerthannormalsuperscript">',r'</span>'],
		13: [r'<span class="smallerthannormalitalic">', r'</span>'],
		10: [r'<span class="smallerthannormal">', r'</span>'],
		9: [r'<span class="normal">', r'</span>'],
		8: [r'<span class="smallcapitalsitalic">', r'</span>'],
		7: [r'<span class="smallcapitals">', r'</span>'],
		6: [r'<span class="romannumerals">', r'</span>'],
		5: [r'<span class="subscript">', r'</span>'],
		4: [r'<span class="superscript">', r'</span>'],
		3: [r'<span class="italic">', r'</span>'],
		2: [r'<span class="bolditalic">', r'</span>'],
		1: [r'<span class="bold">', r'</span>'],
	}
	
	if val in substitutions:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	else:
		substitute = '<hmu_unhandled_latin_font_shift value="' + match.group(1) + '" />' + core
		print('\t',substitute)
	
	return substitute

#
# extras
#

def replacelatinbetacode(texttoclean):
	textualmarkuptuples = []

	# greek within latin: handle it now by calling the greek betacode decoder
	# a big problem: the accented latin parser will screw up 'A\', etc
	# problem of lines that start greek and then never close the greek
	# gellius does this in the preface
	# search = r'(0x\d\d\s)(\$\d{0,2})(.*?)(\d)'
	# search = r'(?<=\d)(\s\$\d{0,2})(.*?)(?=\d)'
	# replace = r' <hmu_greek_in_a_latin_text>\2</hmu_greek_in_a_latin_text> '
	# textualmarkuptuples.append((search, replace))
	#
	# search = r'(?<=(\s/>))(\$\d{0,2})(.*?)(?=\d)'
	# replace = r' <hmu_greek_in_a_latin_text>\3</hmu_greek_in_a_latin_text> '
	# textualmarkuptuples.append((search, replace))

	# on but not off again: Plautus, Bacchides, 1163
	search = r'\$\d{0,2}(.*?)(?=█)'
	replace = r'<hmu_greek_in_a_latin_text>\1</hmu_greek_in_a_latin_text>'
	textualmarkuptuples.append((search, replace))

	search = r'\$(.*?)\&'
	replace = r'<hmu_greek_in_a_latin_text>\1</hmu_greek_in_a_latin_text>'
	textualmarkuptuples.append((search, replace))

	## guess what: line-ends don't turn the greek off even as line starts turn it back on (and then off again later)

	for reg in textualmarkuptuples:
		texttoclean = re.sub(reg[0], reg[1], texttoclean)

	search = r'<hmu_greek_in_a_latin_text>.*?</hmu_greek_in_a_latin_text>'
	texttoclean = re.sub(search, parsegreekinsidelatin, texttoclean)
	
	texttoclean = latinadiacriticals(texttoclean)

	return texttoclean


def latinadiacriticals(texttoclean):
	
	textualmarkuptuples = []

	# accented latin in authors like plautus: only safe after you have taken care of greek
	betacodetuples = (
		(r'a\/', u'\u00e1'),
		(r'e\/', u'\u00e9'),
		(r'i\/', u'\u00ed'),
		(r'o\/', u'\u00f3'),
		(r'u\/', u'\u00fa'),
		(r'y\/', u'\u00fd'),
		(r'A\/', u'\u00c1'),
		(r'E\/', u'\u00c9'),
		(r'I\/', u'\u00cd'),
		(r'O\/', u'\u00d3'),
		(r'U\/', u'\u00da'),
		(r'a\+',r'ä'),
		(r'A\+', r'Ä'),
		(r'e\+', r'ë'),
		(r'E\+', r'Ë'),
		(r'i\+', r'ï'),
		(r'I\+', r'Ï'),
		(r'o\+', r'ö'),
		(r'O\+', r'Ö'),
		(r'u\+', r'ü'),
		(r'U\+', r'Ü'),
	)

	for i in range(0, len(betacodetuples)):
		textualmarkuptuples.append((betacodetuples[i][0], betacodetuples[i][1]))

	for reg in textualmarkuptuples:
		texttoclean = re.sub(reg[0], reg[1], texttoclean)
		
	return texttoclean


def findromanwithingreek(texttoclean):
	"""
	need to flag this so you can undo the transformation of capital letters into greek characters
	:param texttoclean:
	:return:
	"""
	
	# &1Catenae &(Novum Testamentum): on but not off
	# a line should turn things off; but what if it does not
	# this yields ordering issues: if you find █, then you should keep it; if you find $, you should drop it
	# and if you do a before b, then you screw up the ability of b to do its thing
	# so we do this in two parts: first grab the whole line, then make sure there is not a section with a $ in it
	
	search = re.compile(r'(&\d{0,2})(.*?)(\s{0,1}█)')
	texttoclean = re.sub(search, doublecheckromanwithingreek, texttoclean)
	
	return texttoclean


def doublecheckromanwithingreek(match):
	"""
	only works in conjunction with findromanwithingreek()
	:param matchgroups:
	:return:
	"""
	internaltermination = re.compile(r'(\&\d{0,2})(.*?)\$(\d{0,2})')
	if re.search(internaltermination, match.group(1) + match.group(2)) is not None:
		substitution = re.sub(internaltermination, r'<hmu_roman_in_a_greek_text>\2</hmu_roman_in_a_greek_text>',
		                      match.group(1) + match.group(2))
	else:
		substitution = r'<hmu_roman_in_a_greek_text>' + match.group(2) + r'</hmu_roman_in_a_greek_text>'
	
	substitution += match.group(3)
	# print(match.group(1) + match.group(2),'\n\t',substitution)
	
	return substitution

##
## cleanup of the cleaned up: generative citeable texts
##


def totallemmatization(parsedtextfile, authorobject):
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
	lemmatized = []
	dbready = []


	work = 1

	setter = re.compile(r'<hmu_set_level_(\d)_to_([A-Za-z0-9]{1,})')
	adder = re.compile(r'<hmu_increment_level_(\d)_by_1\s')
	wnv = re.compile(r'<hmu_cd_assert_work_number value="(\d{1,3})')

	for line in parsedtextfile:
		gotwork = re.search(wnv, line)
		if gotwork != None:
			work = int(gotwork.group(1))
			for l in range(0, 6):
				levelmapper[l] = 1
		gotsetting = re.search(setter, line)
		if gotsetting != None:
			level = int(gotsetting.group(1))
			# sometimes something like 't' is returned
			if type(gotsetting.group(2)) is int:
				setting = str(gotsetting.group(2))
			else:
				setting = gotsetting.group(2)
			levelmapper[level] = setting
			if level > 0:
				for l in range(0, level):
					levelmapper[l] = 1

		gotincrement = re.search(adder, line)
		# if you don't reset the lower counters, then you will get something like 'line 10' when you first initialize a new section

		if gotincrement != None:
			level = int(gotincrement.group(1))
			setting = 1
			# awkward avoidance of type problems
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
		tups = [('0',str(levelmapper[0])),('1',str(levelmapper[1])),('2',str(levelmapper[2])),('3',str(levelmapper[3])),('4',str(levelmapper[4])), ('5',str(levelmapper[4]))]
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


	# recording the blockinfo
	# the info at the very top block seems like it would be worth figuring out

	# cd blocks end 0xf3 + 0x0
	# the newline lets you reset levels right?
	# you'll want that trailing space later: totallemmatization() strips last char from lines; a problem with the very last line of a file
	search = r'(█ⓕⓔ\s(█⓪\s){1,})'
	replace = '\n<hmu_end_of_cd_block_re-initialize_key_variables /> '
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
	replace = r'\n<hmu_cd_assert_work_number value="\2\3\4"/>'
	texttoclean = re.sub(search, replace, texttoclean)
	
	# 'secondary level (82)' info stored in a run of bytes whose length varies: add 127 to them and you get an ascii value
	# compare geasciistring() in idt file reader: '& int('7f',16))'
	# 0xef 0x82 0xc1 0xf0 0xef 0xec 0xff
	# 0xef 0x82 0xcd 0xf5 0xee 0xff
	search = r'(█ⓔⓕ\s█⑧②\s((█..\s){1,}?)█ⓕⓕ) '
	replace = r'<hmu_cd_assert_work_abbreviation value="\2"/>'
	texttoclean = re.sub(search, replace, texttoclean)
	
	# 'tertiray level (83)' info stored in a run of bytes whose length varies: add 127 to them and you get an ascii value
	# 0xef 0x83 0xc1 0xf0 0xf5 0xec 0xff
	search = r'(█ⓔⓕ\s█⑧③\s((█..\s){1,}?)█ⓕⓕ) '
	replace = r'<hmu_cd_assert_author_abbrev value="\2"/>'
	texttoclean = re.sub(search, replace, texttoclean)
	
	# now reparse
	
	search = r'<hmu_cd_assert_work_number value="..."/>'
	texttoclean = re.sub(search, hutohxgrouper, texttoclean)
	
	search = r'(<hmu_cd_assert_work_abbreviation value=")(.*?)\s("/>)'
	texttoclean = re.sub(search, converthextoascii, texttoclean)

	search = r'(<hmu_cd_assert_author_abbrev value=")(.*?)\s("/>)'
	texttoclean = re.sub(search, converthextoascii, texttoclean)

	# next comes something terrifying: after the author_abbrev we get 4 - 6  hex values
	# try to handle it with the citationbuilder
	search = r'(<hmu_cd_assert_author_abbrev value="(.*?)" />)((█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]{1,2}\s){2,})'
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

	textualmarkuptuples = []

	# re.sub documentation: if repl is a function, it is called for every non-overlapping occurrence of pattern. The function takes a single match object argument, and returns the replacement string
	#search = r'((0x[0-9a-f]{1,2}\s){1,})'
	search = r'((█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]{1,2}\s){1,})'
	texttoclean = re.sub(search, citationbuilder, texttoclean)

	return texttoclean


##
## misc little tools
##
## some of these functions done similarly in idtfiles parsing
## refactor to consolidate if you care
##

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



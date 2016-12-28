# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
import configparser

from builder.parsers.swappers import highunicodetohex, hutohxgrouper, hextohighunicode, bitswapchars
from .betacode_to_unicode import parsegreekinsidelatin
from .citation_builder import citationbuilder

config = configparser.ConfigParser()
config.read('config.ini')

#
# hex datafile and betacode cleanup
#
# [nb: some regex happens in db.py as prep for loading]


def earlybirdsubstitutions(texttoclean):
	# try to get out in front of some of the trickiest bits
	# note that you can't use quotation marks in here
	textualmarkuptuples = []
	
	betacodetuples = (
		(r'<(?!\d)',r'‹'),  # '<': this one is super-dangerous: triple-check
		(r'>(?!\d)', u'›'),  # '>': this one is super-dangerous: triple-check
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
	
	pounds = re.compile(r'#(\d{1,4})')
	texttoclean = re.sub(pounds, poundsubstitutes, texttoclean)
	texttoclean = re.sub(r'#', u'\u0374', texttoclean)
	
	percents = re.compile(r'%(\d{1,3})')
	texttoclean = re.sub(percents, percentsubstitutes, texttoclean)
	texttoclean = re.sub(r'%', u'\u2020', texttoclean)
	
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
	
	ltanglebracket = re.compile(r'<(\d{1,2})')
	texttoclean = re.sub(ltanglebracket, ltanglebracketsubstitutes, texttoclean)
	
	rtanglebracket = re.compile(r'>(\d{1,2})')
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
	ands = re.compile(r'&(\d{1,2})(.*?)(&\d{0,1})')
	texttoclean = re.sub(ands, andsubstitutes, texttoclean)
	
	#texttoclean = re.sub(r'\&(.*?)\&', r'<hmu_shift_latin_font value="regular">\1</hmu_shift_latin_font>', texttoclean)
	
	anddollars = re.compile(r'&(\d{1,2})(.*?)(\$\d{0,1})')
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
		if config['build']['warnings'] == 'y':
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
		if config['build']['warnings'] == 'y':
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
		
		1: u'\u03df',
		2: u'\u03da',
		3: u'\u03d9',
		4: u'\u03d9',
		5: u'\u03e1',
		6: u'\u2e0f',
		7: r'<hmu_idiosyncratic_char value="7">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		8: u'\u2e10',
		9: u'\u0301',
		10: u'\u03fd',
		11: u'\u03ff',
		12: u'\u2014',
		13: u'\u203b',
		14: u'\u2e16',
		15: u'\u003e',
		16: u'\u03fe',
		# 17: u'002f',  # careful: '/' is dangerous
		17: r'／', # fulwidth solidus instead
		18: r'《',
		19: u'\u0300',
		20: r'𐅵',
		21: r'𐅵',
		22: u'\u0375',
		23: u'\u03d9',
		24: r'𐅵',
		25: r'?',
		26: u'\u2e0f',
		27: r'𐄂', # 'check mark'; non tlg; and so - AEGEAN CHECK MARK; Unicode: U+10102, UTF-8: F0 90 84 82
		28: r'<hmu_mark_deleting_entry />␥',
		29: u'\u00b7',
		30: r'<hmu_idiosyncratic_char value="30">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		31: r'<hmu_idiosyncratic_char value="31">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		51: u'\u00b7',
		52: u'\u205a',
		53: u'\u205d',
		55: u'\u2059',
		56: r'∣', # 'dividers of other forms'; not a helpful description: trying u2223 for now
		57: r'<hmu_undocumented_poundsign value="57">⊚</hmu_undocumented_poundsign>',
		59: u'\u03fd',
		60: u'\u0399',
		61: r'𐅂',
		62: r'𐅃',
		63: u'\u0394',
		64: r'𐅄',
		65: u'\u0397',
		66: r'𐅅',
		67: u'\u03a7',
		68: r'𐅆',
		69: u'\u039c',
		70: u'\u002e',
		71: u'\u00b7',
		72: u'\u02d9',
		73: u'\u205a',
		74: u'\u205d',
		75: u'\u002e',
		80: u'\u0308',
		81: r'＇', #fullwidth apostrophe instead of the dangerous simple apostrophe
		82: u'\u02ca',
		83: u'\u02cb',
		84: u'\u1fc0',
		85: u'\u02bd',
		86: u'\u02bc',
		87: u'\u0394\u0345',
		90: u'\u2014',
		99: r'<hmu_undocumented_poundsign value="99">⊚</hmu_undocumented_poundsign>',
		100: r'𐆆',
		101: u'𐅻',  #trouble with the four character unicode codes: uh oh
		102: u'𐆂<6\u03c56>',  # upsilon supposed to be superscript too: add betacode for that <6...6>
		103: u'\u039b\u0338',
		104: u'𐆂<6\u03bf6>',  # the omicron is supposed to be superscript too: add betacode for that <6...6>
		105: r'<hmu_idiosyncratic_char value="105">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		106: r'𐆄',
		107: r'<hmu_idiosyncratic_char value="107">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		108: r'<hmu_idiosyncratic_char value="108">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		109: u'𐆂<6\u03bf6>',  # the omicron is supposed to be superscript too: add betacode for that <6...6>
		110: u'<11α>11<10\u0375>10',  # need to do the combining accent second, right?
		111: u'𐆂<6\u03b56>',
		112: r'𐆈',  # 𐆈- GREEK GRAMMA SIGN; Unicode: U+10188, UTF-8: F0 90 86 88
		113: r'𐅼',
		114: r'𐅀',
		116: u'\u2053',
		117: r'𐆃',  # 𐆃GREEK LITRA SIGN; Unicode: U+10183, UTF-8: F0 90 86 83
		118: u'\u03bb\u0338',
		119: r'𐅽',
		121: u'u\03be\u0338',
		122: r'𐅽',
		123: r'𐅼',
		124: r'<hmu_idiosyncratic_char value="124">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		125: u'𐆂<6\u03c56>',  # the upsilon is supposed to be superscript too: add betacode for that <6...6>
		126: r'<hmu_idiosyncratic_char value="126">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		127: u'\u039b\u0325',
		128: u'u\03b',
		129: u'\u039b\u0325',
		130: r'𐆊',
		131: r'𐅷',
		132: u'\u03b2\u0388',
		133: u'u\0393<6\u03b26>',
		134: u'\u0393<6\u03b26>',  # the beta is supposed to be superscript too: add betacode for that <6...6>
		135: u'\u02d9',
		136: u'\u03a3',  # capital sigma: stater
		137: u'\u0393<6\u03b26>',  #the beta is supposed to be superscript: add betacode for that <6...6>
		150: u'\u221e',
		151: u'\u2014',
		152: u'\u205a\u2014',
		153: u'\u2026\u0305',
		154: u'\u2c80',
		155: u'\u2014\u0323',
		156: u'\u2310',
		157: r'<hmu_idiosyncratic_char value="157">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		158: u'\u2237\u0336',
		159: u'\u2237\u0344',
		160: u'\u007e\u0323',
		161: r'𐅵',
		162: u'\u25a1',
		163: u'\u00b6',
		165: u'\u00d7',
		166: u'\u2a5a',
		167: u'\u039c\u039c', # supposed to stack this too
		168: u'\u039c\u039c\u039c', # supposed to stack this too
		169: r'𐅵',
		171: r'𐅵',
		172: r'𐅵',
		200: u'\u2643',
		201: u'\u25a1',
		202: u'\u264f',
		203: u'\u264d',
		204: u'\u2640',
		205: u'\u2650',
		206: u'\u2644',
		207: u'\u2609',
		208: u'\u263f',
		209: u'\u263e',
		210: u'\u2642',
		211: u'\u2651',
		212: u'\u264c',
		213: u'\u2648',
		214: u'\u264e',
		215: u'\u264a',
		216: u'\u264b',
		217: u'\u2653',
		218: u'\u2652',
		219: u'\u2649',
		220: u'♃',
		221: u'\u263d',
		222: u'\u260c',
		223: u'\u2605',
		240: r'𐅷',  # 𐅷 GREEK TWO THIRDS SIGN; Unicode: U+10177, UTF-8: F0 90 85 B7
		241: u'\u260b',
		242: u'\u2651',
		243: r'<hmu_idiosyncratic_char value="243">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		244: u'\u264c',
		246: r'<hmu_idiosyncratic_char value="246">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		247: r'<hmu_idiosyncratic_char value="247">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		302: r'<hmu_idiosyncratic_char value="302">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		303: u'›',
		304: u'\u2e0e',  # but supposed to be just part of a coronis
		305: u'\u2e0e',
		307: u'\u2e0e',  # but supposed to be just part of a coronis
		308: u'\u2e0e', # but supposed to be just part of a coronis
		310: u'\u2e0e',
		312: u'\u2e0e', # but supposed to be just upper half of a coronis
		313: u'\u2e0e',
		314: r'<hmu_idiosyncratic_char value="314">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		315: u'\u2e0e',
		316: r'<hmu_idiosyncratic_char value="316">◦</hmu_idiosyncratic_char>',  # deprecated: no further info
		317: r'<hmu_document_cancelled_with_slashes />⑊⑊⑊⑊⑊',
		318: r'<hmu_line_filled_with_cross-strokes />⧷⧷⧷⧷⧷',
		319: u'\u25cf',
		320: u'\u2629',
		321: u'\u2629',
		322: u'\u2627',
		323: r'﹥', # 'greater-than sign -> line filler' says the instructions; small version instead of the markup version
		324: r'<hmu_filler_stroke_to_margin />',
		325: r'<hmu_large_single_X>✕</hmu_large_single_X>',
		326: r'<hmu_pattern_of_Xs>✕✕✕✕</hmu_pattern_of_Xs>',
		327: r'<hmu_tachygraphic_marks />',
		329: r'<hmu_monogram />',
		330: r'<hmu_drawing />',
		331: r'<hmu_wavy_line_as_divider />〜〜〜〜〜',
		332: r'<hmu_impression_of_stamp_on_papyrus />⦻',
		333: r'<hmu_text_enclosed_in_box_or_circle />',
		334: r'<hmu_text_enclosed_in_brackets />',
		336: r'<hum_redundant_s-type_sign />',
		337: r'<hmu_seal_attached_to_papyrus>❊</hmu_seal_attached_to_papyrus>',
		451: u'\u0283',
		452: u'\u2310',
		453: u'\u2e11',
		454: u'\u2e10',
		456: u'\u2e0e',
		457: r'<hmu_idiosyncratic_char value="457">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		458: u'\u0387',
		459: u'\u00b7',
		460: u'\u2014',
		461: u'\u007c',
		465: u'\u2627',
		467: u'\u2192',
		468: u'\u2e0e',
		476: u'\u0283',
		500: r'<hmu_undocumented_poundsign value="500">⊚</hmu_undocumented_poundsign>',
		501: r'π<6ιθ6>',  # abbreviation for πιθανόν: added own betacode - <6...6>
		502: r'🜚',  # listed as idiosyncratic; but looks like 'alchemical symbol for gold': U+1F71A
		504: u'\u2e0e',
		505: u'\u205c',
		507: u'\u2e14',
		508: u'\u203b',
		509: u'\u0305\u0311',
		512: u'\u03fd',
		513: r'<hmu_idiosyncratic_char value="513">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		514: r'<hmu_idiosyncratic_char value="514">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		515: r'𐆅',
		516: u'\u0394\u0345',
		517: r'𐆅',
		518: r'𐅹',
		519: u'\u2191',
		520: u'\u2629',
		521: r'<hmu_idiosyncratic_char value="521">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		# 522: u'\u',  # markup <rotate> 0397
		523: u'\u2e13',
		524: u'\u2297',
		526: u'\u2190',
		527: u'\u02c6',
		528: u'\u03bb\u032d',
		529: u'\u204b',
		530: r'<hmu_idiosyncratic_char value="530">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		531: u'\u035c',
		532: u'\u2e12',
		533: u'\u03da',
		534: u'\u0302',
		535: r'<hmu_idiosyncratic_char value="535">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		536: r'<hmu_idiosyncratic_char value="536">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		537: r'<hmu_idiosyncratic_char value="537">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		538: r'<hmu_idiosyncratic_char value="538">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		540: r'<hmu_idiosyncratic_char value="540">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		541: r'<hmu_idiosyncratic_char value="541">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		542: u'\u03a1\u0336',
		543: r'<hmu_idiosyncratic_char value="543">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		544: u'\u2058',
		545: r'<hmu_idiosyncratic_char value="545">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		546: r'<hmu_idiosyncratic_char value="546">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		547: r'<hmu_idiosyncratic_char value="547">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		549: r'<hmu_idiosyncratic_char value="549">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		550: u'\u003a\u003a\u2e2e',
		551: u'\u25cc',
		552: r'<hmu_idiosyncratic_char value="552">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		553: r'<hmu_idiosyncratic_char value="553">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		554: r'<hmu_idiosyncratic_char value="554">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		555: r'<hmu_idiosyncratic_char value="555">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		556: u'\u2629',
		557: r'<hmu_idiosyncratic_char value="557">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		558: r'<hmu_idiosyncratic_char value="558">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		559: r'<hmu_idiosyncratic_char value="559">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		561: u'\u2191',
		562: u'\u0305',
		563: r'⏗',
		564: r'⏘',
		565: r'⏙',
		# GREEK INSTRUMENTAL NOTATIONS
		566: r'𝈱',  # 32
		567: r'𝈓',
		568: r'𝈳',
		569: r'𝈶',  # 40
		570: u'\u03f9',
		572: r'𝈩',  # 𝈩GREEK INSTRUMENTAL NOTATION SYMBOL-19; Unicode: U+1D229, UTF-8: F0 9D 88 A9
		573: r'𝈒',
		574: u'\u0393',
		575: r'𝈕',
		576: r'𝈖',
		577: u'\u03a6',
		578: u'\u03a1',
		579: u'\u039c',
		580: u'\u0399',
		581: u'\u0398',
		582: u'𝈍',
		583: u'\u039d',
		584: u'\u2127',
		585: u'\u0396',
		586: r'𝈸',  # 43
		587: u'\0395',
		588: u'𝈈',  # Vocal #9' Instrum #44
		589: r'𝈿',  # 𝈿GREEK INSTRUMENTAL NOTATION SYMBOL-52; Unicode: U+1D23F, UTF-8: F0 9D 88 BF
		590: r'𝈿',
		591: r'𝈛',
		592: r'𝉀',
		593: u'039b',
		598: u'0394',
		600: r'𝈨',  # Instrum #18
		603: u'\u03a0',
		604: r'𝈦',  # 𝈦GREEK INSTRUMENTAL NOTATION SYMBOL-14; Unicode: U+1D226, UTF-8: F0 9D 88 A6
		615: r'𝈰',  # 𝈰GREEK INSTRUMENTAL NOTATION SYMBOL-30; Unicode: U+1D230, UTF-8: F0 9D 88 B0
		618: r'𝈴',  # 𝈴GREEK INSTRUMENTAL NOTATION SYMBOL-38; Unicode: U+1D234, UTF-8: F0 9D 88 B4
		621: r'𝈅',
		622: r'𝈁',
		623: u'\u2127',
		624: u'\u03fd',
		635: r'𝈝',  # 𝈝GREEK INSTRUMENTAL NOTATION SYMBOL-1; Unicode: U+1D21D, UTF-8: F0 9D 88 9D
		651: u'\u03a7',
		652: u'\u03a4',
		660: u'\u0391',
		661: u'\u0392',
		662: u'\u03a5',
		665: r'𝈴',  # 𝈴GREEK INSTRUMENTAL NOTATION SYMBOL-38; Unicode: U+1D234, UTF-8: F0 9D 88 B4
		666: r'𝈯',  # 𝈯GREEK INSTRUMENTAL NOTATION SYMBOL-29; Unicode: U+1D22F, UTF-8: F0 9D 88 AF
		681: r'<hmu_idiosyncratic_char value="681">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		682: r'<hmu_idiosyncratic_char value="682">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		688: u'\u03bc\u030a',
		689: r'𐅵',
		690: u'\u27d8',
		691: u'\u27c0',
		692: u'\u27c1',
		700: u'\u205e',
		701: r'<hmu_idiosyncratic_char value="701">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		702: r'<hmu_idiosyncratic_char value="702">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		703: u'\u25cb\u25cb\u25cb',
		704: u'\u2014\u0307',
		705: r'<hmu_idiosyncratic_char value="705">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		706: r'<hmu_idiosyncratic_char value="706">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		707: r'<hmu_idiosyncratic_char value="707">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		708: r'<hmu_idiosyncratic_char value="708">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		709: u'\u223b',
		710: u'\u039a\u0336',
		711: u'\u03fb',
		741: r'<hmu_idiosyncratic_char value="741">◦</hmu_idiosyncratic_char>',
		751: u'\u0661',  # arabic-indic digits...
		752: u'\u0662',
		753: u'\u0663',
		754: u'\u0664',
		755: u'\u0665',
		756: u'\u0666',
		757: u'\u0667',
		758: u'\u0668',
		759: u'\u0669',
		760: u'\u0660',
		800: u'\u2733',
		801: r'𐅁',
		802: r'𐅀',
		803: u'\u03a7',
		804: r'／', # fulwidth solidus instead
		805: u'\u03a4',
		807: r'𐅦',
		808: r'𐅈',
		811: u'\u03a4',
		812: r'𐅈',
		813: r'𐅉',
		814: r'𐅊',
		815: r'𐅋',
		816: r'𐅌',
		817: r'𐅍',
		818: r'𐅎',
		821: u'\u03a3',
		822: r'𐅟',
		823: r'𐅐',
		824: r'𐅑',
		825: r'𐅒',
		826: r'𐅓',
		827: r'𐅔',
		829: r'𐅕',
		830: r'𐅇',
		831: r'𐅇',
		832: r'𐅖',
		833: u'\u039c',
		834: r'𐅗',
		835: u'\u03a7',
		836: u'\u03a3',
		840: u'\u007c\u007c',
		841: u'\u007c\u007c\u007c',
		843: r'𐅛',
		844: u'\205d',
		845: r'𐅘',
		846: r'𐄐',
		847: r'𐅞',
		848: r'𐄒',
		853: u'\u0399',
		862: u'\u0394',
		863: r'𐅄',
		865: r'𐅅',
		866: u'\u03a7',
		867: r'𐅆',
		870: r'<hmu_undocumented_poundsign value="870">⊚</hmu_undocumented_poundsign>',
		899: r'<hmu_unknown_numeral>',
		900: r'<hmu_undocumented_poundsign value="900">⊚</hmu_undocumented_poundsign>',
		901: r'<hmu_undocumented_poundsign value="901">⊚</hmu_undocumented_poundsign>',
		921: r'<hmu_undocumented_poundsign value="921">⊚</hmu_undocumented_poundsign>',
		922: r'𝈨',
		923: r'<hmu_idiosyncratic_char value="923">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		924: r'<hmu_idiosyncratic_char value="924">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		925: r'𝈗',
		926: r'𝈫',
		927: r'W',
		930: r'<hmu_idiosyncratic_char value="930">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		932: u'\u2733',
		933: r'<hmu_idiosyncratic_char value="933">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		934: r'<hmu_idiosyncratic_char value="934">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		937: r'<hmu_miscellaneous_illustrations>',
		940: r'<hmu_idiosyncratic_char value="940">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		943: r'<hmu_undocumented_poundsign value="943">⊚</hmu_undocumented_poundsign>',
		949: r'<hmu_undocumented_poundsign value="949">⊚</hmu_undocumented_poundsign>',
		961: r'<hmu_line_on_stone_stops_but_edition_continues_line />',
		973: r'<hmu_undocumented_poundsign value="973">⊚</hmu_undocumented_poundsign>',
		1000: r'𐅼',
		1001: r'𐅽',
		1002: r'𐅾',
		1003: r'𐅿',
		1004: r'𐆀',
		1053: r'<hmu_undocumented_poundsign value="1053">⊚</hmu_undocumented_poundsign>',
		1059: r'<hmu_undocumented_poundsign value="1059">⊚</hmu_undocumented_poundsign>',
		1068: r'<hmu_undocumented_poundsign value="1068">⊚</hmu_undocumented_poundsign>',
		1069: r'<hmu_undocumented_poundsign value="1069">⊚</hmu_undocumented_poundsign>',
		1070: r'<hmu_undocumented_poundsign value="1070">⊚</hmu_undocumented_poundsign>',
		1071: r'<hmu_undocumented_poundsign value="1071">⊚</hmu_undocumented_poundsign>',
		1072: r'<hmu_undocumented_poundsign value="1072">⊚</hmu_undocumented_poundsign>',
		1100: u'\u2183',
		1101: r'IS',
		1102: r'H',
		1103: u'\u0323\u0313',
		1104: u'S\u0038',  # deprecated, use &S%162$
		1105: u'\u004d\u030a',
		1106: r'<hmu_idiosyncratic_char value="1106">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1107: u'\u0053\u0335\u0053\u0336',
		1108: u'\u0058\u0036',
		1109: u'\u003d',
		1110: u'\u002d',
		1111: u'\u00b0',
		1112: r'<hmu_idiosyncratic_char value="1112">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1113: r'<hmu_idiosyncratic_char value="1113">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1114: r'𝈁',
		1115: u'\u007c',
		1116: u'\u01a7',
		1117: u'\u005a',
		1118: r'<hmu_idiosyncratic_char value="1118">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1119: u'\u0110',
		1120: r'<hmu_idiosyncratic_char value="1120">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1121: u'\u005a',
		1122: r'<hmu_idiosyncratic_char value="1122">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1123: r'<hmu_idiosyncratic_char value="1123">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1124: u'\u211e',
		1125: r'<hmu_idiosyncratic_char value="1125">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1126: u'\u004f',
		1127: u'\u0076\u0338',
		1128: u'\u0049\u0336\u0049\u0336\u0053\u0336',
		1129: u'\u005a\u0336',
		1130: r'＼', # fullwidth reverse solidus (vs just reverse)
		1131: u'\u005c\u005c',
		1132: u'\u005c\u0336',
		1133: u'\u005c\u0336\u005c\u0336',
		1134: r'<hmu_idiosyncratic_char value="1134">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1135: u'\u002f\u002f',
		1136: u'\u2112',
		1221: u'\u0131',
		1222: u'\u0130',
		1314: u'\u006e\u030a',
		1316: u'\u0292',
		1317: u'\u02d9\002f\u002f\u002e',
		1318: u'\u223b',
		1320: u'\u0375\u0311',
		1321: r'🜚',  # listed as idiosyncratic; but looks like 'alchemical symbol for gold': U+1F71A
		1322: u'\u2644',
		1323: u'\u03b6\u0337\u03c2\u0300',
		1324: u'\u03b8\u03c2\u0302',
		1326: r'<hmu_idiosyncratic_char value="1326">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1327: r'<hmu_idiosyncratic_char value="1327">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1328: r'<hmu_idiosyncratic_char value="1328">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1334: r'<hmu_idiosyncratic_char value="1334">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1335: r'／／', # fulwidth solidus instead
		1336: r'<hmu_unsupported_hebrew_character>□</hmu_unsupported_hebrew_character>',
		1338: r'𐅾',
		1341: r'<hmu_idiosyncratic_char value="1341">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1500: u'\u03b3\u030a',
		1501: r'<hmu_idiosyncratic_char value="1501">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1502: u'\u03a7\u0374',
		1503: r'<hmu_idiosyncratic_char value="1503">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1504: r'<hmu_idiosyncratic_char value="1504">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1506: u'\u0300\u0306',
		1510: u'Α\u0338<6\u0304ν\u002f>6' # A%162<6E%26N%3>6 [!]
	}

	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_pound_sign value="'+match.group(1)+'" />▦'
		if config['build']['warnings'] == 'y':
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
		1: u'\u003f',
		2: u'\u002a',
		3: u'\u002f',
		4: u'\u0021',
		5: u'\u007c',
		6: u'\u003d',
		7: u'\u002b',
		9: u'\u0026',
		10: u'\u003a',
		11: u'\u2022',
		12: u'\u002a',  # look out for future problems: *
		14: u'\u00a7',
		15: u'\u02c8',
		17: u'\u2016',
		18: u'\u0025',  # look out for future problems: '
		19: u'\u2013',
		20: u'\u0301',
		21: u'\u0300',
		22: u'\u0302',
		23: u'\u0308',
		24: u'\u0342',
		25: u'\u0327',
		26: u'\u0304',
		27: u'\u0306',
		28: u'\u0308',
		29: u'\u0323\u0323',
		30: u'\u02bc',
		31: u'u\02bd',
		32: u'\u00b4',  # look out for future problems: ´
		33: u'\u0060',  # look out for future problems: `
		34: u'\u1fc0',
		35: u'\u1fce',
		36: u'\u1fde',
		37: u'\u1fdd',
		38: u'\u1fdf',
		39: u'\u00a8',
		40: u'\u23d1',
		41: u'\u2013',
		42: u'\u23d5',
		43: u'\u00d7',
		44: u'\u23d2',
		45: u'\u23d3',
		46: u'\u23d4',
		47: r'𐄑',
		48: u'u23d1\u23d1',
		49: u'\u23d1\u23d1\u23d1',
		50: r'<hmu_papryological_fraction>((1/2))</hmu_papryological_fraction>',
		51: r'<hmu_papryological_fraction>((1/4))</hmu_papryological_fraction>',
		52: r'<hmu_papryological_fraction>((1/8))</hmu_papryological_fraction>',
		53: r'<hmu_papryological_fraction>((1/16))</hmu_papryological_fraction>',
		54: r'<hmu_papryological_fraction>((1/32))</hmu_papryological_fraction>',
		55: r'<hmu_papryological_fraction>((1/64))</hmu_papryological_fraction>',
		56: r'<hmu_papryological_fraction>((1/128))</hmu_papryological_fraction>',
		57: r'<hmu_undocumented_percentsign value="57">⊚</hmu_undocumented_percentsign>',
		59: r'<hmu_papryological_fraction>((3/4))</hmu_papryological_fraction>',
		60: r'<hmu_papryological_fraction>((1/3))</hmu_papryological_fraction>',
		61: r'<hmu_papryological_fraction>((1/6))</hmu_papryological_fraction>',
		62: r'<hmu_papryological_fraction>((1/12))</hmu_papryological_fraction>',
		63: r'<hmu_papryological_fraction>((1/24))</hmu_papryological_fraction>',
		64: r'<hmu_papryological_fraction>((1/48))</hmu_papryological_fraction>',
		65: r'<hmu_papryological_fraction>((1/96))</hmu_papryological_fraction>',
		69: u'\u03b2\u0338',
		70: r'<hmu_papryological_fraction>((1/50))</hmu_papryological_fraction>',
		71: r'<hmu_papryological_fraction>((1/100))</hmu_papryological_fraction>',
		72: r'<hmu_papryological_fraction>((1/100))</hmu_papryological_fraction>',
		73: r'<hmu_papryological_fraction>((1/100))</hmu_papryological_fraction>',
		79: r'<hmu_undocumented_percentsign value="79">⊚</hmu_undocumented_percentsign>',
		80: u'\u0076\u002E',  # supposed to put the 'v' in italics too
		81: r'<span class="italic">vac.</span>',
		91: u'\u0485',
		92: u'\u0486',
		93: u'\u1dc0',
		94: u'\u0307',
		95: u'\u1dc1',
		96: u'\u035c',
		97: u'\u0308',
		98: u'\u0022',
		99: u'\u2248',
		100: u'\u003b',
		101: u'\u0023',  # had best do pounds before percents since this is '#'
		102: r'’', # single quotation mark
		103: u'\u005c',  # backslash: careful
		105: u'\u007c\u007c\u007c',
		106: u'\u224c',
		107: u'\u007e',
		108: u'\u00b1',
		109: u'\u00b7',
		110: u'\u25cb',
		127: u'\u032f',
		128: u'\u0302',
		129: u'\u2020',
		130: u'\u0307',
		133: u'\u1fcd',
		134: u'\u1fcf',
		140: r'𐄒',
		141: u'\u23d6',
		144: u'\u23d1\u0036',
		145: u'\u2013\u0301',
		146: u'\u00b7',
		147: u'\u030a',
		148: u'\u030c',
		149: u'\u0328',
		150: u'\u007c',
		157: u'\u2e38',
		159: u'\u00d7',
		160: u'\u002d',
		162: u'\u0338'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_percent_sign value="' + match.group(1) + '" />▩'
		if config['build']['warnings'] == 'y':
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
		51: '<span class="erasedepiographicaltext">',
		49: r'<hmu_papyrological_project_lt_bracket_49 />', # 49-35
		35: r'<hmu_papyrological_project_lt_bracket_35 />',
		34: r'<hmu_parenthesis_deletion_marker>⸨',
		33: r'<hmu_parenthesis_ancient_punctuation>｟',
		32: u'\u239d',
		31: u'\u239c',
		30: u'\239b',
		23: u'u\23a9',
		22: u'u\23a8',
		21: u'u\23aa',
		20: u'u\23a7',
		18: u'27ea',
		17: u'\u230a\u230a',
		14: u'\u007c\u003a',
		12: u'\u2192',
		13: u'\u005b',  # supposed to be italic as well
		11: u'u\208d',
		10: r'<span class="largerthannormal">[</span>',
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
		if config['build']['warnings'] == 'y':
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
		51: r'</span>', # erasedepiographicaltext
		49: r'<hmu_papyrological_project_rt_bracket_49 />',  # 49-35
		35: r'<hmu_papyrological_project_rt_bracket_35 />',
		34: r'⸩</hmu_parenthesis_deletion_marker>',
		33: r'｠</hmu_parenthesis_ancient_punctuation>',
		32: u'\u32a0',
		31: u'\u239f',
		30: u'\u329e',
		23: u'\u23ad',
		22: u'\u23ac',
		21: u'\u23aa',
		20: u'\u23ab',
		18: u'\u27eb',
		17: u'\u230b\u230b',
		14: u'\003a\u007c',
		13: u'\u005d',  # supposed to be italic as well
		12: u'\u2190',
		11: u'u\208e',
		10: r'<span class="largerthannormal">]</span>',
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
		if config['build']['warnings'] == 'y':
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
		51: r'<hmu_standalone_writing_inverse_to_main_text />',
		50: r'<hmu_standalone_writing_perpendicular_to_main_text />',
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
		8: r'———',  # hmu_standalone_mid_line_citation_boundary
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
		if config['build']['warnings'] == 'y':
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
		39: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_39 />',
		38: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_38 />',
		37: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_37 />',
		36: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_36 />',
		35: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_35 />',
		34: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_34 />',
		33: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_33 />',
		32: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_32 />',
		31: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_31 />',
		30: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_30 />',
		29: r'<hmu_emendation_by_editor_of_text_not_obviously_incorrect>',
		28: r'<hmu_date_or_numeric_equivalent_of_date>',
		27: u'\u0359',
		26: r'<hmu_recitfied_form>',
		10: u'\u0332',
		9: r'<hmu_alternative_reading>',
		8: r'<hmu_numerical_equivalent>',
		7: r'<hmu_reading_discarded_in_another_source>',
		6: r'<hmu_discarded_form>',
		5: r'<hmu_form_altered_by_scribe>',
		4: r'<hmu_unconventional_form_written_by_scribe>',
		3: r'<span class="scholium">',
		2: r'<span class="marginaltext">',
		1: r'<span class="title">'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_ltcurlybracket value="' + match.group(1) + '" />'
		if config['build']['warnings'] == 'y':
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
		43: r'</span>',  # hmu_servius_bracket
		41: r'</span>',  # hmu_stage_direction
		40: r'</span>',  # hmu_speaker
		29: r'</hmu_emendation_by_editor_of_text_not_obviously_incorrect>',
		28: r'</hmu_date_or_numeric_equivalent_of_date>',
		27: u'\u0359',
		26: r'</hmu_recitfied_form>',
		10: u'\u0332',
		9: r'</hmu_alternative_reading>',
		8: r'</hmu_numerical_equivalent>',
		7: r'</hmu_reading_discarded_in_another_source>',
		6: r'</hmu_discarded_form>',
		5: r'</hmu_form_altered_by_scribe>',
		4: r'</hmu_unconventional_form_written_by_scribe>',
		3: r'</span>',  # hmu_reference_in_scholium
		2: r'</span>',  # hmu_marginal_text
		1: r'</span>' # hmu_title
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_rtcurlybracket value="' + match.group(1) + '" />'
		if config['build']['warnings'] == 'y':
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
		3: '',
		4: '',
		5: '',
		6: r'<span class="superscript">',  # hmu_shift_font_to_superscript
		7: r'<span class="subscript">',  # hmu_shift_font_to_subscript
		8: '',
		9: r'<span class="lemma">',  # hmu_textual_lemma
		10: r'<span class="stackedlower">',  # hmu_stacked_text_lower
		11: r'<span class="stackedupper">',  # hmu_stacked_text_upper
		12: r'<span class="nonstandarddirection">',
		14: r'<span class="interlineartext">',
		15: r'<span class="interlinearmarginalia">',  # hmu_interlinear_marginalia
		17: '',  # Combining Double Underline
		20: r'<span class="expanded">',  # hmu_expanded_text
		21: r'<span class="expanded">',  # hmu_latin_expanded_text
		30: r'<span class="overline">',  # Combining Overline and Dependent Vertical Bars
		31: r'<span class="strikethrough">',
		32: r'<span class="overunder">',  # hmu_overline_and_underline
		34: r'⁄',  # fractions (which have balanced sets of markup...)
		60: r'<hmu_preferred_epigraphical_text_used>',
		61: r'<hmu_epigraphical_text_inserted_after_erasure>',
		62: r'<span class="lineover">',
		63: r'<hmu_epigraphical_text_after_correction>',
		64: r'<span class="letterbox">',
		65: r'<hmu_epigraphical_letters_enclosed_in_wreath>',
		66: r'<hmu_epigraphical_project_escape_66>',
		67: r'<hmu_epigraphical_project_escape_67>',
		68: r'<hmu_epigraphical_project_escape_68>',
		69: r'<hmu_epigraphical_project_escape_69>',
		70: r'<span class="diagram">',  # hmu_inset_diagram
		71: r'<span class="diagramsection">',  # hmu_inset_diagram
		72: r'<span class="diagramrelation">',  # hmu_logical_relationship_in_diagram
		73: r'<span class="diagramlvl03">',
		74: r'<span class="diagramlvl04">'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_ltangle value="' + match.group(1) + '" />'
		if config['build']['warnings'] == 'y':
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
		3: u'\u0361',
		4: u'\u035c',
		5: u'\u035d',
		6: r'</span>',  # hmu_shift_font_to_superscript
		7: r'</span>',  # hmu_shift_font_to_subscript
		8: u'\u0333',
		9: r'</span>',  # hmu_textual_lemma
		10: r'</span>',  # hmu_stacked_text_lower
		11: r'</span>',  # hmu_stacked_text_upper
		12: r'</span>',  # nonstandarddirection
		13: r'<hmu_standalone_singlelinespacing_in_doublespacedtext />',
		14: r'</span>',  # interlineartext
		15: r'</span>',  # hmu_interlinear_marginalia
		17: u'u\0333',
		20: r'</span>',  # hmu_expanded_text
		21: r'</span>',  # hmu_expanded_text
		30: r'</span>',  # Combining Overline and Dependent Vertical Bars
		31: r'</span>',  # strikethrough
		32: r'</span>',  # hmu_overline_and_underline
		34: '',  # fractions
		60: r'</hmu_preferred_epigraphical_text_used>',
		61: r'</hmu_epigraphical_text_inserted_after_erasure>',
		62: r'</span>', # epigraphical line over letters
		63: r'</hmu_epigraphical_text_after_correction>',
		64: r'</span>', # letters in a box
		65: r'</hmu_epigraphical_letters_enclosed_in_wreath>',
		66: r'</hmu_epigraphical_project_escape_66>',
		67: r'</hmu_epigraphical_project_escape_67>',
		68: r'</hmu_epigraphical_project_escape_68>',
		69: r'</hmu_epigraphical_project_escape_69>',
		70: r'</span>',  # hmu_inset_diagram
		71: r'</span>',  # hmu_discrete_section_of_diagram
		72: r'</span>',  # hmu_logical_relationship_in_diagram
		73: r'</span>',  #<span class="diagramlvl03">',
		74: r'</span>'  #<span class="diagramlvl04">'
	}
	
	if val in substitutions:
		substitute = substitutions[val]
	else:
		substitute = '<hmu_unhandled_rtangle value="' + match.group(1) + '" />'
		if config['build']['warnings'] == 'y':
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
		53: [r'<span class="hebrew">', r'</span>'],
		52: [r'<span class="arabic">', r'</span>'],
		51: [r'<span class="demotic">', r'</span>'],
		50: [r'<span class="coptic">', r'</span>'],
		40: [r'<span class="extralarge">', r'</span>'],
		30: [r'<span class="extrasmall">', r'</span>'],
		20: [r'<span class="largerthannormal">', r'</span>'],
		18: [r'<span class="smallerthannormal">', r'</span>'],  # + 'vertical', but deprecated
		16: [r'<span class="smallerthannormalsuperscriptbold">', r'</span>'],
		15: [r'<span class="smallerthannormalsubscript">', r'</span>'],
		14: [r'<span class="smallerthannormalsuperscript">', r'</span>'],
		13: [r'<span class="smallerthannormalitalic">', r'</span>'],
		11: [r'<span class="smallerthannormalbold">', r'</span>'],
		10: [r'<span class="smallerthannormal">', r'</span>'],
		9: [r'<span class="regular">', r'</span>'],
		8: [r'<span class="vertical">', r'</span>'],
		6: [r'<span class="superscriptbold">', r'</span>'],
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
		if config['build']['warnings'] == 'y':
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
		20: [r'<span class="largerthannormal">',r'</span>'],
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
		if config['build']['warnings'] == 'y':
			print('\t',substitute)
	
	return substitute

#
# language interchanges
#


def replacelatinbetacode(texttoclean):
	"""
	first look for greek inside of a latin text
	the add in latin accents
	
	:param texttoclean:
	:return:
	"""
	# on but not off again: Plautus, Bacchides, 1163 + Gellius NA pr.
	# a line should turn things off; but what if it does not?
	# so we do this in two parts: first grab the whole line, then make sure there is not a section with a $ in it
	# if there is: turn off roman at the $; if there is not turn of roman at line end
	
	search = re.compile(r'(\$\d{0,2})(.*?)(\s{0,1}█)')
	texttoclean = re.sub(search, doublecheckgreekwithinlatin, texttoclean)
	
	search = r'<hmu_greek_in_a_latin_text>.*?</hmu_greek_in_a_latin_text>'
	texttoclean = re.sub(search, parsegreekinsidelatin, texttoclean)
	
	texttoclean = latinadiacriticals(texttoclean)
	
	return texttoclean


def doublecheckgreekwithinlatin(match):
	"""
	only works in conjunction with replacelatinbetacode()
	:param match:
	:return:
	"""
	
	linetermination = re.compile(r'(\$\d{0,2})(.*?)(\s{0,1}$)')
	internaltermination = re.compile(r'(\$\d{0,2})(.*?)\&(\d{0,2})')
	if re.search(internaltermination, match.group(1) + match.group(2)) is not None:
		substitution = re.sub(internaltermination, r'<hmu_greek_in_a_latin_text>\2</hmu_greek_in_a_latin_text>',
		                      match.group(1) + match.group(2))
		# OK, you got the internal ones, but a final $xxx can remain at the end of the line
		substitution = re.sub(linetermination, r'<hmu_greek_in_a_latin_text>\2</hmu_greek_in_a_latin_text>\3', substitution)
	else:
		substitution = r'<hmu_greek_in_a_latin_text>' + match.group(2) + r'</hmu_greek_in_a_latin_text>'
	
	substitution += match.group(3)
	# print(match.group(1) + match.group(2),'\n\t',substitution)
	
	return substitution


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
		(r'a\=', r'â'),
		(r'A\=', r'Â'),
		(r'e\=', r'ê'),
		(r'E\=', r'Ê'),
		(r'i\=', r'î'),
		(r'I\=', r'Î'),
		(r'o\=', r'ô'),
		(r'O\=', r'Ô'),
		(r'u\=', r'û'),
		(r'U\=', r'Û'),
		(r'a\\', r'à'),
		(r'A\\', r'À'),
		(r'e\\', r'è'),
		(r'E\\', r'È'),
		(r'i\\', r'ì'),
		(r'I\\', r'Ì'),
		(r'o\\', r'ò'),
		(r'O\\', r'Ò'),
		(r'u\\', r'ù'),
		(r'U\\', r'Ù'),
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
	# a line should turn things off; but what if it does not?
	# so we do this in two parts: first grab the whole line, then make sure there is not a section with a $ in it
	# if there is: turn off roman at the $; if there is not turn of roman at line end
	
	search = re.compile(r'(&\d{0,2})(.*?)(\s{0,1}█)')
	texttoclean = re.sub(search, doublecheckromanwithingreek, texttoclean)
	
	return texttoclean


def doublecheckromanwithingreek(match):
	"""
	only works in conjunction with findromanwithingreek()
	:param matchgroups:
	:return:
	"""
	linetermination = re.compile(r'(&\d{0,2})(.*?)(\s{0,1}$)')
	internaltermination = re.compile(r'(&\d{0,2})(.*?)\$(\d{0,2})')
	if re.search(internaltermination, match.group(1) + match.group(2)) is not None:
		substitution = re.sub(internaltermination, r'<hmu_roman_in_a_greek_text>\2</hmu_roman_in_a_greek_text>',
		                      match.group(1) + match.group(2))
		substitution = re.sub(linetermination, r'<hmu_roman_in_a_greek_text>\2</hmu_roman_in_a_greek_text>\3',
		                      substitution)
	else:
		substitution = r'<hmu_roman_in_a_greek_text>' + match.group(2) + r'</hmu_roman_in_a_greek_text>'
	
	substitution += match.group(3)
	# print(match.group(1) + match.group(2),'\n\t',substitution)
	
	return substitution

#
# cleanup of the cleaned up: generative citeable texts
#


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

	setter = re.compile(r'<hmu_set_level_(\d)_to_(.*?)\s/>')
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
		tups = [('0',str(levelmapper[0])),('1',str(levelmapper[1])),('2',str(levelmapper[2])),('3',str(levelmapper[3])),('4',str(levelmapper[4])), ('5',str(levelmapper[5]))]
		dbready.append([str(work), tups, line])

	return dbready


def modifiedtotallemmatization(parsedtextfile, authorobject):
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
	doca = re.compile(r'<hmu_metadata_documentnumber value="(\d{1,3})')

	for line in parsedtextfile:

		gotwork = re.search(wnv, line)
		if gotwork != None:
			work = int(gotwork.group(1))
			for l in range(0, 6):
				levelmapper[l] = 1
				
		gotsetting = re.search(setter, line)
		if gotsetting != None:
			level = int(gotsetting.group(1))
			# level5 info seems less reliable than watching the notes at level6...
			# if authorobject.universalid[0:2] in ['in', 'dp'] and level == 5:
			# 	level = 1
			# sometimes something like 't' is returned
			if type(gotsetting.group(2)) is int:
				setting = str(gotsetting.group(2))
			else:
				setting = gotsetting.group(2)
			
			if authorobject.universalid[0:2] in ['in', 'dp'] and level == 1:
				# don't let level 1 be set because this is where hipparchia stores the document number
				# the original data does sets that number in 5 and/or 6 (but does not necessarily agree between 5 & 6!)
				# not quite sure what is being set at one, but it is not the document number...
				pass
			elif authorobject.universalid[0:2] in ['in', 'dp'] and level == 3:
				# you can set 3, but don't reset 0
				# '3' is where things like 'a', 'b', 'c' are marked: pieces of reassembled inscriptions, I think.
				levelmapper[3] = setting
				levelmapper[1] = str(levelmapper[1]) + levelmapper[3]
			else:
				levelmapper[level] = setting
				if level > 0:
					for l in range(0, level):
						levelmapper[l] = 1

		gotincrement = re.search(adder, line)
		# if you don't reset the lower counters, then you will get something like 'line 10' when you first initialize a new section

		if gotincrement != None:
			level = int(gotincrement.group(1))

			if authorobject.universalid[0:2] in ['in', 'dp'] and level == 1:
				# don't let level 1 be incremented because this is where hipparchia stores the document number
				# the original data does sets that number in 5 and/or 6 (but does not necessarily agree between 5 & 6!)
				# not quite sure what is being set at one, but it is not the document number...
				pass
			else:
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

		# special treatment for inscriptions and documentary papyri
		# needs to come last since it rewrites earlier work
		if authorobject.universalid[0:2] in ['in', 'dp']:
			# the structure of these works is always the same: 0: line; 1: document_number
			# the document numbers do not increment by adding 1 to level 1 but by asserting a number at level 6
			# level 5 also sees some action: but note how that leaves you with blank levels lower than 5.
			# in fact, the original data tires to claim that there are no lines, just documents (i.e., level 0 = 'document')
			# it's a bit of a mess
			#   level 5 is way off on some inscriptions from level 6
			#   level 1 is storing 'face' information in inscriptions
			gotdoc = re.search(doca, line)
			if gotdoc != None:
				levelmapper[1] = gotdoc.group(1)
			
			if levelmapper[3] is not 1:
				try:
					# if you already have 10a, don't generate 10aa, 10aaa, 10aaaa, ...
					tail = levelmapper[1][-1]
				except:
					levelmapper[1] = str(levelmapper[1]) + levelmapper[3]
			# gotdoc = re.search(docb, line)
			# if gotdoc != None:
			# 	levelmapper[1] = gotdoc.group(1)
						
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
	
	workname = replacelatinbetacode(betacodeworkname)
	
	percents = re.compile(r'%(\d{1,3})')
	workname = re.sub(percents, percentsubstitutes, workname)
	workname = re.sub(r'\[2(.*?)]2', r'⟪\1⟫',workname)
	workname = re.sub(r'<.*?>','', workname)
	workname = re.sub(r'&\d{1,}(`|)', '', workname) # e.g.: IG I&4`2&
	workname = re.sub(r'&', '', workname)
	workname = re.sub(r'`', '', workname)

	return workname
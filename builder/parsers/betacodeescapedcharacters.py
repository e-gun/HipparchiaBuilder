# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

if config['buildoptions']['warnings'] == 'y':
	warnings = True
else:
	warnings = False

if config['buildoptions']['simplifyquotes'] == 'y':
	simplequotes = True
else:
	simplequotes = False


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

	percents = re.compile(r'%(\d{1,3})')
	texttoclean = re.sub(percents, percentsubstitutes, texttoclean)

	ltsqbrackets = re.compile(r'\[(\d{1,2})')
	texttoclean = re.sub(ltsqbrackets, leftbracketsubstitutions, texttoclean)

	rtsqbrackets = re.compile(r'\](\d{1,2})')
	texttoclean = re.sub(rtsqbrackets, rightbracketsubstitutions, texttoclean)

	atsigns = re.compile(r'@(\d{1,2})')
	texttoclean = re.sub(atsigns, atsignsubstitutions, texttoclean)

	ltcurlybracket = re.compile(r'\{(\d{1,2})')
	texttoclean = re.sub(ltcurlybracket, ltcurlybracketsubstitutes, texttoclean)

	rtcurlybracket = re.compile(r'\}(\d{1,2})')
	texttoclean = re.sub(rtcurlybracket, rtcurlybracketsubstitutes, texttoclean)

	ltanglebracket = re.compile(r'<(\d{1,2})')
	texttoclean = re.sub(ltanglebracket, ltanglebracketsubstitutes, texttoclean)

	rtanglebracket = re.compile(r'>(\d{1,2})')
	texttoclean = re.sub(rtanglebracket, rtanglebracketsubstitutes, texttoclean)

	singletons = re.compile(r'[#%@{}]')
	texttoclean = re.sub(singletons, singletonsubstitutes, texttoclean)

	return texttoclean


def singletonsubstitutes(match):
	"""
	turn lone escaped items into unicode: #%@{}
	:param match:
	:return:
	"""

	val = match.group(0)

	substitutions = {
		'#': u'\u0374',
		'%': u'\u2020',  # dagger: †
		'@': r'<hmu_standalone_tabbedtext />',
		'{': r'<speaker>',
		'}': r'</speaker>'
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		print('\tsingletonsubstitutes() sent an invalid value:', val)
		substitute = val

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
		# it is noisy to build with the 'undocumenteds' commented out
		# but, if you want to get the codes as HTML, this is what you need to do...

		1: u'\u03df',
		2: u'\u03da',  # stigma; supposed to be able to handle '*#2' and not just '#2'
		3: u'\u03d9',  # koppa; supposed to be able to handle '*#3' and not just '#3'
		4: u'\u03d9',  # koppa, variant
		5: u'\u03e1',  # sampi; supposed to be able to handle '*#5' and not just '#5'
		6: u'\u2e0f',
		7: r'<hmu_idiosyncratic_char betacodeval="7">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		8: u'\u2e10',
		9: u'\u0301',
		10: u'\u03fd',
		11: u'\u03ff',
		12: u'\u2014',
		13: u'\u203b',
		14: u'\u2e16',
		15: r'⟩',  # officially: u'\u003e', greater than sign, diple
		16: u'\u03fe',
		# 17: u'002f',  # careful: '/' is dangerous
		17: r'／',  # fulwidth solidus instead
		18: r'⟨',  # officially: u'\u003c', less than sign, reversed diple
		19: u'\u0300',
		20: r'𐅵',
		21: r'𐅵',
		22: u'\u0375',
		23: u'\u03d9',
		24: r'𐅵',
		25: r'𐅶',
		26: u'\u2e0f',
		27: r'𐄂',  # 'check mark'; non tlg; and so - AEGEAN CHECK MARK; Unicode: U+10102, UTF-8: F0 90 84 82
		28: r'<hmu_mark_deleting_entry />␥',
		29: u'\u00b7',  # middle dot: ·
		30: r'<hmu_idiosyncratic_char betacodeval="30">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		31: r'<hmu_idiosyncratic_char betacodeval="31">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		# 48: r'<hmu_undocumented_poundsign betacodeval="48">⊚</hmu_undocumented_poundsign>',
		# 50: r'<hmu_undocumented_poundsign betacodeval="50">⊚</hmu_undocumented_poundsign>',
		51: u'\u00b7',  # middle dot: ·
		52: u'\u205a',
		53: u'\u205d',
		# 54: r'<hmu_undocumented_poundsign betacodeval="54">⊚</hmu_undocumented_poundsign>',
		55: u'\u2059',
		56: r'∣',  # 'dividers of other forms'; not a helpful description: trying u2223 for now
		57: r'﹤',  # small variant;  as per http://noapplet.epigraphy.packhum.org/text/3292?&bookid=5&location=7
		58: r'﹥',  # cf #57
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
		81: r'＇', # fullwidth apostrophe instead of the dangerous simple apostrophe
		82: u'\u02ca',
		83: u'\u02cb',
		84: u'\u1fc0',
		85: u'\u02bd',
		86: u'\u02bc',
		87: u'\u0394\u0345', # 'ΔΕ'
		90: u'\u2014',
		99: r'<hmu_undocumented_poundsign betacodeval="99">⊚</hmu_undocumented_poundsign>',
		100: r'𐆆',
		101: u'𐅻',  # trouble with the four character unicode codes: uh oh
		102: u'𐆂<6\u03c56>',  # upsilon supposed to be superscript too: add betacode for that <6...6>
		103: u'\u039b\u0338',
		104: u'𐆂<6\u03bf6>',  # the omicron is supposed to be superscript too: add betacode for that <6...6>
		105: r'<hmu_idiosyncratic_char betacodeval="105">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		106: r'𐆄',
		107: r'<hmu_idiosyncratic_char betacodeval="107">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		108: r'<hmu_idiosyncratic_char betacodeval="108">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		109: u'𐆂<6\u03bf6>',  # the omicron is supposed to be superscript too: add betacode for that <6...6>
		110: u'<11α>11<10\u0375>10',  # need to do the combining accent second, right?
		111: u'𐆂<6\u03b56>',
		112: r'𐆈',  # 𐆈- GREEK GRAMMA SIGN; Unicode: U+10188, UTF-8: F0 90 86 88
		113: r'𐅼',
		114: r'𐅀',
		115: r'𐆉',
		116: u'\u2053',
		117: r'𐆃',  # 𐆃GREEK LITRA SIGN; Unicode: U+10183, UTF-8: F0 90 86 83
		118: u'\u03bb\u0338',
		119: r'𐅽',
		121: u'u\03be\u0338',
		122: r'𐅽',
		123: r'𐅼',
		124: r'<hmu_idiosyncratic_char betacodeval="124">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		125: u'𐆂<6\u03c56>',  # the upsilon is supposed to be superscript too: add betacode for that <6...6>
		126: r'<hmu_idiosyncratic_char betacodeval="126">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		127: u'\u039b\u0325',  # 'ΛΕ'
		128: u'\u03fc',
		129: u'\u039b\u0325',  # 'ΛΕ'
		130: r'𐆊',
		131: r'𐅷',
		132: u'\u03b2\u0388',  # 'βΈ'
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
		157: r'<hmu_idiosyncratic_char betacodeval="157">◦</hmu_idiosyncratic_char>',  # idiosyncratic
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
		243: r'<hmu_idiosyncratic_char betacodeval="243">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		244: u'\u264c',
		246: r'<hmu_idiosyncratic_char betacodeval="246">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		247: r'<hmu_idiosyncratic_char betacodeval="247">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		300: u'\u2e0e',  # but supposed to be just upper half of a coronis
		302: r'<hmu_idiosyncratic_char betacodeval="302">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		303: u'›',
		304: u'\u2e0e',  # but supposed to be just part of a coronis
		305: u'\u2e0e',
		306: u'\u2e0f',  # but supposed to be a double paragraphos
		307: u'\u2e0e',  # but supposed to be just part of a coronis
		308: u'\u2e0e',  # but supposed to be just part of a coronis
		310: u'\u2e0e',
		311: u'\u2e0e',  # but supposed to be just lower half of a coronis
		312: u'\u2e0e',  # but supposed to be just upper half of a coronis
		313: u'\u2e0e',
		314: r'<hmu_idiosyncratic_char betacodeval="314">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		315: u'\u2e0e',
		316: r'<hmu_idiosyncratic_char betacodeval="316">◦</hmu_idiosyncratic_char>',  # deprecated: no further info
		317: r'<hmu_document_cancelled_with_slashes />⑊⑊⑊⑊⑊⑊⑊⑊',
		318: r'<hmu_line_filled_with_cross-strokes />⧷⧷⧷⧷⧷⧷⧷⧷',
		319: u'\u25cf',
		320: u'\u2629',
		321: u'\u2629',
		322: u'\u2627',
		323: r'﹥', # 'greater-than sign -> line filler' says the instructions; small version instead of the markup version (uFE65, cf uFE64)
		324: r'<hmu_filler_stroke_to_margin />',
		325: r'<hmu_large_single_X>✕</hmu_large_single_X>',
		326: r'<hmu_pattern_of_Xs>✕✕✕✕</hmu_pattern_of_Xs>',
		327: r'<hmu_tachygraphic_marks />',
		329: r'<hmu_monogram />',
		330: r'<hmu_drawing />',
		331: r'<hmu_wavy_line_as_divider />〜〜〜〜〜',
		332: r'<span class="hmu_impression_of_stamp_on_papyrus">⦻</span>',
		333: r'<hmu_text_enclosed_in_box_or_circle />',
		334: r'<hmu_text_enclosed_in_brackets />',
		335: r'<span class="strikethrough">N</span>',
		336: r'<hum_redundant_s-type_sign />',
		337: r'<span class="hmu_seal_attached_to_papyrus">❊</span>',
		400: r'ͱ',  # heta; supposed to know how to do capital too: *#400
		401: r'ϳ',  # yot; supposed to know how to do capital too: *#401
		451: u'\u0283',
		452: u'\u2310',
		453: u'\u2e11',
		454: u'\u2e10',
		456: u'\u2e0e',
		457: r'<hmu_idiosyncratic_char betacodeval="457">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		458: u'\u0387',
		459: u'\u00b7',
		460: u'\u2014',
		461: u'\u007c',
		465: u'\u2627',
		466: r'<hmu_idiosyncratic_char betacodeval="466">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		467: u'\u2192',
		468: u'\u2e0e',
		476: u'\u0283',
		# 486: r'<hmu_undocumented_poundsign betacodeval="486">⊚</hmu_undocumented_poundsign>',
		500: r'⋮',
		# 500: r'<hmu_undocumented_poundsign betacodeval="500">⊚</hmu_undocumented_poundsign>',
		501: r'π<6ιθ6>',  # abbreviation for πιθανόν: added own betacode - <6...6>
		502: r'🜚',  # listed as idiosyncratic; but looks like 'alchemical symbol for gold': U+1F71A
		503: r'ΡΠ',  # but supposed to be on top of one another
		504: u'\u2e0e',
		505: u'\u205c',
		506: u'\u2e15',
		507: u'\u2e14',
		508: u'\u203b',
		509: u'\u0305\u0311',
		510: r'ε/π',  # but supposed to be stacked
		511: r'ι/κ', # but supposed to be stacked
		512: u'\u03fd',
		513: r'<hmu_idiosyncratic_char betacodeval="513">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		514: r'<hmu_idiosyncratic_char betacodeval="514">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		515: r'𐆅',
		516: u'\u0394\u0345',
		517: r'𐆅',
		518: r'𐅹',
		519: u'\u2191',
		520: u'\u2629',
		521: r'<hmu_idiosyncratic_char betacodeval="521">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		522: r'<span class="90degreerotate>Η</span>',  # markup <rotate> 0397
		523: u'\u2e13',
		524: u'\u2297',
		526: u'\u2190',
		527: u'\u02c6',
		528: u'\u03bb\u032d',
		529: u'\u204b',
		530: r'<hmu_idiosyncratic_char betacodeval="530">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		531: u'\u035c',
		532: u'\u2e12',
		533: u'\u03da',
		534: u'\u0302',
		535: r'<hmu_idiosyncratic_char betacodeval="535">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		536: r'<hmu_idiosyncratic_char betacodeval="536">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		537: r'<hmu_idiosyncratic_char betacodeval="537">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		538: r'<hmu_idiosyncratic_char betacodeval="538">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		540: r'<hmu_idiosyncratic_char betacodeval="540">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		541: r'<hmu_idiosyncratic_char betacodeval="541">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		542: u'\u03a1\u0336',
		543: r'<hmu_idiosyncratic_char betacodeval="543">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		544: u'\u2058',
		545: r'<hmu_idiosyncratic_char betacodeval="545">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		546: r'<hmu_idiosyncratic_char betacodeval="546">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		547: r'<hmu_idiosyncratic_char betacodeval="547">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		548: r'<span class="superscript">‖̴</span>', # 2016+0334
		549: r'<hmu_idiosyncratic_char betacodeval="549">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		550: u'\u003a\u003a\u2e2e',
		551: u'\u25cc',
		552: r'<hmu_idiosyncratic_char betacodeval="552">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		553: r'<hmu_idiosyncratic_char betacodeval="553">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		554: r'<hmu_idiosyncratic_char betacodeval="554">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		555: r'<hmu_idiosyncratic_char betacodeval="555">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		556: u'\u2629',
		557: r'<hmu_idiosyncratic_char betacodeval="557">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		558: r'<hmu_idiosyncratic_char betacodeval="558">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		559: r'<hmu_idiosyncratic_char betacodeval="559">◦</hmu_idiosyncratic_char>',  # idiosyncratic
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
		571: r'𐅃',
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
		587: u'\u0395',
		588: u'𝈈',  # Vocal #9' Instrum #44
		589: r'𝈿',  # 𝈿GREEK INSTRUMENTAL NOTATION SYMBOL-52; Unicode: U+1D23F, UTF-8: F0 9D 88 BF
		590: r'𝈿',
		591: r'𝈛',
		592: r'𝉀',
		593: u'\u039b',
		# 594: r'', # 'rare' and so has no unicode representation
		# 595: r'', # 'rare' and so has no unicode representation
		# 596: r'', # 'rare' and so has no unicode representation
		# 597: r'', # 'rare' and so has no unicode representation
		598: u'\u0394',
		599: r'𝈔',
		600: r'𝈨',  # Instrum #18
		# 601: r'', # 'rare' and so has no unicode representation
		602: r'𝈷',
		603: u'\u03a0',
		604: r'𝈦',  # 𝈦GREEK INSTRUMENTAL NOTATION SYMBOL-14; Unicode: U+1D226, UTF-8: F0 9D 88 A6
		# 605: r'', # 'rare' and so has no unicode representation
		# 606: r'', # 'rare' and so has no unicode representation
		# 607: r'', # 'rare' and so has no unicode representation
		# 608: r'', # 'rare' and so has no unicode representation
		# 609: r'', # 'rare' and so has no unicode representation
		# 610: r'', # 'rare' and so has no unicode representation
		# 611: r'', # 'rare' and so has no unicode representation
		# 612: r'', # 'rare' and so has no unicode representation
		# 613: r'', # 'rare' and so has no unicode representation
		# 614: r'', # 'rare' and so has no unicode representation
		615: r'𝈰',  # 𝈰GREEK INSTRUMENTAL NOTATION SYMBOL-30; Unicode: U+1D230, UTF-8: F0 9D 88 B0
		616: r'𝈞',
		617: r'Ω',
		# 618: r'', # 'rare' and so has no unicode representation
		619: r'λ',
		# 620: r'', # 'rare' and so has no unicode representation
		621: r'𝈅',
		622: r'𝈁',
		623: u'\u2127',
		624: u'\u03fd',
		# 625: r'', # 'rare' and so has no unicode representation
		# 626: r'', # 'rare' and so has no unicode representation
		627: r'𝈗',
		628: r'Ο',
		629: r'Ξ',
		630: r'Δ',
		631: u'\u039a',
		632: r'𝈎',
		633: r'𝈲',
		634: r'𝈹',
		635: r'𝈝',  # 𝈝GREEK INSTRUMENTAL NOTATION SYMBOL-1; Unicode: U+1D21D, UTF-8: F0 9D 88 9D
		636: r'𝈃',
		637: r'𝈆',
		638: r'𝈉',
		639: r'𝈌',
		640: r'𝈑',
		641: r'Ω',
		642: r'Η',
		643: r'𝈝',
		644: r'𝈟',
		645: r'𝈡',
		646: r'𝈥',
		647: r'𝈬',
		648: r'𝈵',
		649: r'𝈋',
		650: r'𝈏',
		651: u'\u03a7',
		652: u'\u03a4',
		653: r'𝈙',
		654: r'𝈜',
		655: r'𝈂',
		656: r'𝈤',
		657: r'𝈮',
		658: r'𝈾',
		659: r'𝉁',
		660: u'\u0391',
		661: u'\u0392',
		662: u'\u03a5',
		663: u'\u03a8',
		664: r'𝈺',
		665: r'𝈴',  # 𝈴GREEK INSTRUMENTAL NOTATION SYMBOL-38; Unicode: U+1D234, UTF-8: F0 9D 88 B4
		666: r'𝈯',  # 𝈯GREEK INSTRUMENTAL NOTATION SYMBOL-29; Unicode: U+1D22F, UTF-8: F0 9D 88 AF
		667: r'𝈭',
		668: r'𝈐',
		669: r'𝈊',
		670: r'𝈇',
		671: r'𝈛',
		672: r'𝈘',
		673: r'𝈣',
		674: r'𝈢',
		675: r'𝉀',
		676: r'𝈽',
		677: r'μ',
		678: r'𝈠',
		679: r'𝈄',
		681: r'<hmu_idiosyncratic_char betacodeval="681">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		682: r'<hmu_idiosyncratic_char betacodeval="682">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		683: u'\u2733',
		684: r'𝈪',
		# 685: r'', # 'rare' and so has no unicode representation
		# 686: r'', # 'rare' and so has no unicode representation
		# 687: r'', # 'rare' and so has no unicode representation
		688: u'\u03bc\u030a',
		689: r'𐅵',
		690: u'\u27d8',
		691: u'\u27c0',
		692: u'\u27c1',
		693: r'<hmu_idiosyncratic_char betacodeval="693">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		694: r'𝈼',
		695: r'—', # em-dash 2014
		696: r'𝈧',
		697: r'𝉅',
		700: u'\u205e',
		701: r'<hmu_idiosyncratic_char betacodeval="701">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		702: r'<hmu_idiosyncratic_char betacodeval="702">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		703: u'\u25cb\u25cb\u25cb',
		704: u'\u2014\u0307',
		705: r'<hmu_idiosyncratic_char betacodeval="705">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		706: r'<hmu_idiosyncratic_char betacodeval="706">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		707: r'<hmu_idiosyncratic_char betacodeval="707">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		708: r'<hmu_idiosyncratic_char betacodeval="708">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		709: u'\u223b',
		710: u'\u039a\u0336',
		711: u'\u03fb',
		741: r'<hmu_idiosyncratic_char betacodeval="741">◦</hmu_idiosyncratic_char>',
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
		806: u'\u039A',
		807: r'𐅦',
		808: r'𐅈',
		809: r'𐅃', # http://noapplet.epigraphy.packhum.org/text/335386?&bookid=859&location=16
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
		837: u'\u03a4',
		838: u'𐅃',
		839: u'𐅁',
		840: u'\u007c\u007c',
		841: u'\u007c\u007c\u007c',
		842: u'\u00b7',
		843: r'𐅛',
		844: u'\u205d',
		845: r'𐅘',
		846: r'𐄐',
		847: r'𐅞',
		848: r'𐄒',
		# 850: [not known by PHI]
		850: r'<hmu_undocumented_poundsign betacodeval="850">⊚</hmu_undocumented_poundsign>',
		853: u'\u0399',
		862: u'\u0394',
		863: r'𐅄',
		865: r'𐅅',
		866: u'\u03a7',
		867: r'𐅆',
		870: r'Ε',
		# PHI will show you glyphs, but 'private use area' means that they are feeding them to you
		# it seems that there is no official support for these characters
		# 875: r'', # see http://noapplet.epigraphy.packhum.org/text/247092?&bookid=489&location=1689; private use area
		875: r'<hmu_unsupported_poundsign betacodeval="875">●</hmu_undocumented_poundsign>',  # u'\ue022', # private use area
		876: r'<hmu_unsupported_poundsign betacodeval="876">●</hmu_undocumented_poundsign>',  # u'\ue023', # private use area
		877: r'<hmu_unsupported_poundsign betacodeval="877">●</hmu_undocumented_poundsign>',  # u'\ue024', # inferred; private use area
		878: r'<hmu_unsupported_poundsign betacodeval="878">●</hmu_undocumented_poundsign>',  # u'\ue025', # inferred; private use area
		879: r'<hmu_unsupported_poundsign betacodeval="879">●</hmu_undocumented_poundsign>',  # u'\ue026',  # inferred; private use area
		880: r'<hmu_unsupported_poundsign betacodeval="880">●</hmu_undocumented_poundsign>',  # u'\ue027',  # inferred; private use area
		881: r'<hmu_unsupported_poundsign betacodeval="881">●</hmu_undocumented_poundsign>',  # u'\ue028',  # inferred; private use area
		882: r'<hmu_unsupported_poundsign betacodeval="882">●</hmu_undocumented_poundsign>',  # u'\ue029',  # inferred; private use area
		883: r'<hmu_unsupported_poundsign betacodeval="883">●</hmu_undocumented_poundsign>',  # u'\ue02a', # private use area
		# 898: [not known by PHI]
		898: r'<hmu_undocumented_poundsign betacodeval="898">⊚</hmu_undocumented_poundsign>',
		899: r'<hmu_unknown_numeral>',
		900: r'○', # '❦' (?!) is what you can see at http://noapplet.epigraphy.packhum.org/text/232427?&bookid=396&location=7
		# 901: [not known by PHI]
		901: r'<hmu_undocumented_poundsign betacodeval="901">⊚</hmu_undocumented_poundsign>',
		# 921: [not known by PHI]
		921: r'<hmu_undocumented_poundsign betacodeval="921">⊚</hmu_undocumented_poundsign>',
		922: r'𝈨',
		923: r'<hmu_idiosyncratic_char betacodeval="923">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		924: r'<hmu_idiosyncratic_char betacodeval="924">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		925: r'𝈗',
		926: r'𝈫',
		927: r'W',
		928: r'𝈋',
		929: r'𝈔',
		930: r'<hmu_idiosyncratic_char betacodeval="930">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		932: u'\u2733',
		933: r'<hmu_idiosyncratic_char betacodeval="933">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		934: r'<hmu_idiosyncratic_char betacodeval="934">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		# 936: [not known by PHI]
		936: r'<hmu_undocumented_poundsign betacodeval="936">⊚</hmu_undocumented_poundsign>',
		937: r'<hmu_miscellaneous_illustrations>',
		# 938: r'', # http://noapplet.epigraphy.packhum.org/text/260647?&bookid=509&location=1035; private use area?
		938: r'Ƨ',  # 01a7
		939: r'~',
		940: r'<hmu_idiosyncratic_char betacodeval="940">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		943: r'﹥',  # PHI
		# 947: [not known by PHI]
		947: r'<hmu_undocumented_poundsign betacodeval="947">⊚</hmu_undocumented_poundsign>',
		# 948: [not known by PHI]
		948: r'<hmu_undocumented_poundsign betacodeval="948">⊚</hmu_undocumented_poundsign>',
		949: r'—',  # http://noapplet.epigraphy.packhum.org/text/251612?&bookid=491&location=1689
		961: r'<hmu_line_on_stone_stops_but_edition_continues_line />',
		# 973: [not known by PHI]
		973: r'<hmu_undocumented_poundsign betacodeval="973">⊚</hmu_undocumented_poundsign>',
		977: r'§',  # Caria (Stratonikeia), 8 2, line 12; http://noapplet.epigraphy.packhum.org/text/262496?&bookid=526&location=1035
		# 990: r'<hmu_undocumented_poundsign betacodeval="990">⊚</hmu_undocumented_poundsign>',
		# 981: [not known by PHI]
		981: r'<hmu_undocumented_poundsign betacodeval="981">⊚</hmu_undocumented_poundsign>',
		# 982: [not known by PHI]
		982: r'<hmu_undocumented_poundsign betacodeval="982">⊚</hmu_undocumented_poundsign>',
		1000: r'𐅼',
		1001: r'𐅽',
		1002: r'𐅾',
		1003: r'𐅿',
		1004: r'𐆀',
		1009: r'',  # http://noapplet.epigraphy.packhum.org/text/247092?&bookid=489&location=1689
		# a huge run of undocumented poundsigns in the inscriptions: this only scratches the surface
		# packhum.org has representations of many of them
		# see especially: http://noapplet.epigraphy.packhum.org/text/260603?&bookid=509&location=1035
		1012: u'\ue036',
		1023: r'ηʹ',  # http://noapplet.epigraphy.packhum.org/text/247092?&bookid=489&location=1689
		# 1045: [not known by PHI]
		1045: r'<hmu_undocumented_poundsign betacodeval="1045">⊚</hmu_undocumented_poundsign>',
		1053: r'<hmu_undocumented_poundsign betacodeval="1053">⊚</hmu_undocumented_poundsign>',
		# 1057: r'', # http://noapplet.epigraphy.packhum.org/text/258019?&bookid=493&location=1035; private use area?
		1059: r'<hmu_undocumented_poundsign betacodeval="1059">⊚</hmu_undocumented_poundsign>',
		1061: r'γʹ',
		1062: r'δʹ',
		1063: r'εʹ',
		1064: r'ϛʹ',
		1065: r'ζʹ',
		1067: r'θʹ',
		1068: r'ιʹ',
		1069: r'κʹ',
		1070: r'λʹ',
		1071: r'μʹ',
		1072: r'νʹ',
		1073: r'ξʹ',
		1074: r'οʹ',
		1075: r'πʹ',
		1077: r'ρʹ',
		1078: r'σʹ',
		1079: r'τʹ',
		1080: r'υʹ',
		1082: r'χʹ',
		1084: r'ωʹ', # Caria (Tralles), 243: line 16; http://noapplet.epigraphy.packhum.org/text/263093?&bookid=531&location=1035
		1085: r' ϡʹ',
		1086: r'͵α',
		1087: r'͵β',
		1100: u'\u2183',
		1101: r'IS',
		1102: r'H',
		1103: u'\u0323\u0313',
		1104: u'S\u0038',  # deprecated, use &S%162$
		1105: u'\u004d\u030a',
		1106: r'<hmu_idiosyncratic_char betacodeval="1106">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1107: u'\u0053\u0335\u0053\u0336',
		1108: u'\u0058\u0036',
		1109: u'\u003d',
		1110: u'\u002d',
		1111: u'\u00b0',
		1112: r'<hmu_idiosyncratic_char betacodeval="1112">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1113: r'<hmu_idiosyncratic_char betacodeval="1113">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1114: r'𝈁',
		1115: u'\u007c',
		1116: u'\u01a7',
		1117: u'\u005a',
		1118: r'<hmu_idiosyncratic_char betacodeval="1118">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1119: u'\u0110',
		1120: r'<hmu_idiosyncratic_char betacodeval="1120">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1121: u'\u005a',
		1122: r'<hmu_idiosyncratic_char betacodeval="1122">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1123: r'<hmu_idiosyncratic_char betacodeval="1123">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1124: u'\u211e',
		1125: r'<hmu_idiosyncratic_char betacodeval="1125">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1126: u'\u004f',
		1127: u'\u0076\u0338',
		1128: u'\u0049\u0336\u0049\u0336\u0053\u0336',
		1129: u'\u005a\u0336',
		1130: r'＼', # fullwidth reverse solidus (vs just reverse)
		1131: u'\u005c\u005c',
		1132: u'\u005c\u0336',
		1133: u'\u005c\u0336\u005c\u0336',
		1134: r'<hmu_idiosyncratic_char betacodeval="1134">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1135: u'\u002f\u002f',
		1136: u'\u2112',
		1221: u'\u0131',
		1222: u'\u0130',
		1314: u'\u006e\u030a',
		1315: r'ΜΡ', # but supposed to be on top of one another
		1316: u'\u0292',
		1317: u'\u02d9\002f\u002f\u002e',
		1318: u'\u223b',
		1320: u'\u0375\u0311',
		1321: r'🜚',  # listed as idiosyncratic; but looks like 'alchemical symbol for gold': U+1F71A
		1322: u'\u2644',
		1323: u'\u03b6\u0337\u03c2\u0300',
		1324: u'\u03b8\u03c2\u0302',
		1326: r'<hmu_idiosyncratic_char betacodeval="1326">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1327: r'<hmu_idiosyncratic_char betacodeval="1327">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1328: r'<hmu_idiosyncratic_char betacodeval="1328">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1334: r'<hmu_idiosyncratic_char betacodeval="1334">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1335: r'／／',  # fulwidth solidus instead
		1336: r'<hmu_unsupported_hebrew_character>□</hmu_unsupported_hebrew_character>',
		1337: r'﹥',  # supposed to be 003e, ie simple angle bracket ; this is fe65
		1338: r'𐅾',
		1341: r'<hmu_idiosyncratic_char betacodeval="1341">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1500: u'\u03b3\u030a',
		1501: r'<hmu_idiosyncratic_char betacodeval="1501">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1502: u'\u03a7\u0374',
		1503: r'<hmu_idiosyncratic_char betacodeval="1503">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1504: r'<hmu_idiosyncratic_char betacodeval="1504">◦</hmu_idiosyncratic_char>',  # idiosyncratic
		1505: r'<hmu_unknown_abbreviation betacodeval="1505">◦</hmu_unknown_abbreviation>',
		1506: u'\u0300\u0306',
		1509: r'πληθ',  # supposed to be a symbol
		1510: u'Α\u0338<6\u0304ν\u002f>6',  # A%162<6E%26N%3>6 [!]
		1511: r'π<span class="superscript">ε:`</span>',
		# 1806: [not known by PHI]
		1806: r'<hmu_undocumented_poundsign betacodeval="1806">⊚</hmu_undocumented_poundsign>'
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		# substitute = '<span class="unhandledpound">﹟{v}</span>'.format(v=val)
		substitute = '<hmu_unhandled_pound_sign betacodeval="{v}" /><span class="unhandledpound">﹟</span>'.format(v=val)
		if warnings:
			print('\t', substitute)

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
		# many of these early items can look like betacode accents, etc.
		# using small variants now; then lastpass can restore them
		1: r'﹖',  # '?' (003f), but using small variant instead: fe56
		2: r'﹡',  # '*' (u002a), but using small variant instead: fe61
		3: u'／',  # '/' (u002f), but using fullwidth variant instead: ff0f
		4: u'﹗',  # '!' (u0021), but using small variant instead: ff57
		5: u'│',  # '|' (u007c), but using box drawings light vertical instead: 2502
		6: u'﹦',  # '=' (u003d); but using small variant instead: fe66
		7: u'﹢',  # '+' (u002b); but using small variant instead: fe62
		8: u'﹪',  # '%' (u0025), but using small variant instead: fe6a
		9: u'﹠',  # '&' (0026) is also a control character; using small version instead (fe60); can swap it out in the end
		10: r'﹕',  # ':' (003a); samll variant instead: fe55
		11: u'\u2022',
		12: u'﹡',  # '*' (u002a) might lead to future problems: small version instead (fe61); can swap it out in the end
		14: u'\u00a7',
		15: u'\u02c8',
		16: u'\u00a6',
		17: u'\u2016',
		18: u'\u0027',  # look out for future problems: '
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
		50: r'<hmu_papyrological_fraction>½</hmu_papyrological_fraction>',
		51: r'<hmu_papyrological_fraction>¼</hmu_papyrological_fraction>',
		52: r'<hmu_papyrological_fraction>⅛</hmu_papyrological_fraction>',
		53: r'<hmu_papyrological_fraction>⅟<span class="denominator">16</span></hmu_papyrological_fraction>',
		54: r'<hmu_papyrological_fraction>⅟<span class="denominator">32</span></hmu_papyrological_fraction>',
		55: r'<hmu_papyrological_fraction>⅟<span class="denominator">64</span></hmu_papyrological_fraction>',
		56: r'<hmu_papyrological_fraction>⅟<span class="denominator">128</span></hmu_papyrological_fraction>',
		57: r'<hmu_undocumented_percentsign betacodeval="57">⊚</hmu_undocumented_percentsign>',
		59: r'<hmu_papyrological_fraction>¾</hmu_papyrological_fraction>',
		60: r'<hmu_papyrological_fraction>⅓</hmu_papyrological_fraction>',
		61: r'<hmu_papyrological_fraction>⅙</hmu_papyrological_fraction>',
		62: r'<hmu_papyrological_fraction>⅟<span class="denominator">12</span></hmu_papyrological_fraction>',
		63: r'<hmu_papyrological_fraction>⅟<span class="denominator">24</span></hmu_papyrological_fraction>',
		64: r'<hmu_papyrological_fraction>⅟<span class="denominator">48</span></hmu_papyrological_fraction>',
		65: r'<hmu_papyrological_fraction>⅟<span class="denominator">96</span></hmu_papyrological_fraction>',
		69: u'\u03b2\u0338',
		70: r'<hmu_papyrological_fraction>⅟<span class="denominator">50</span></hmu_papyrological_fraction>',
		71: r'<hmu_papyrological_fraction>⅟<span class="denominator">100</span></hmu_papyrological_fraction>',
		72: r'<hmu_papyrological_fraction>⅟<span class="denominator">100</span></hmu_papyrological_fraction>',
		73: r'<hmu_papyrological_fraction>⅟<span class="denominator">100</span></hmu_papyrological_fraction>',
		75: r'<hmu_undocumented_percentsign betacodeval="75">⊚</hmu_undocumented_percentsign>',
		79: r'<hmu_undocumented_percentsign betacodeval="79">⊚</hmu_undocumented_percentsign>',
		80: u'<span class="italic"> v. </span>',
		81: r'<span class="italic"> vac. </span>',
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
		# 101: u'\u0023',  # had best do pounds before percents since this is '#'
		101: r'﹟',  # small number sign instead (ufe5f)
		102: r'’',  # single quotation mark
		# 103: u'\u005c',  # backslash: careful
		103: r'﹨',  # small reverse solidus instead: ufe68
		105: u'\u007c\u007c\u007c',
		106: u'\u224c',
		107: u'\u007e',  # '~'
		108: u'\u00b1',  # '±'
		109: u'\u00b7',  # middle dot: '·'
		110: u'\u25cb',
		127: u'\u032f',
		128: u'\u0302',
		129: u'\u2020',
		130: u'\u0307',
		132: r'΅',
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
		159: u'\u00d7',  # multiplication sign: '×'
		160: u'\u002d',  # hyphen-minus: '-'
		162: u'\u0338'
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		# substitute = '<span class="unhandledpercent">﹪{v}</span>'.format(v=val)
		substitute = '<hmu_unhandled_percent_sign betacodeval="{v}" /><span class="unhandledpercent">﹪</span>'.format(v=val)
		if warnings:
			print('\t', substitute)

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
		1: '❨', # supposed to be parenthesis '('; but can interfere with betacode parsing; either swap here or change order of execution
		# 2: u'\u2329', # '〈'
		2: '⟨',
		3: '❴',
		4: '⟦',
		5: '⌊',
		6: '⌈',
		7: '⌈',
		8: '⌊',
		9: u'\u2027',
		10: r'<span class="largerthannormal">[</span>',
		11: u'\u208d',
		12: u'\u2192',
		13: u'<span class="italic">\u005b',  # supposed to be italic as well
		14: u'\u007c\u003a',
		17: u'\u230a\u230a',
		18: u'27ea',
		20: u'\u23a7',
		21: u'\u23aa',
		22: u'\u23a8',
		23: u'\u23a9',
		30: u'\u239b',
		31: u'\u239c',
		32: u'\u239d',
		# this one is odd: you will 'open' it 17x in dp0002 and 'close' it 1x; what is really going on?
		33: r'<hmu_parenthesis_ancient_punctuation>｟',
		34: r'<span class="parenthesis_deletion_marker>"⸨',
		35: r'<hmu_papyrological_project_lt_bracket_35 />',
		49: r'<hmu_papyrological_project_lt_bracket_49 />', # 49-35
		51: '<span class="erasedepigraphicaltext">'
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_left_bracket betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)


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
		1: '❩',  # swapped for ')'
		# 2: u'\u232a', # '〉'
		2: '⟩',
		3: '❵',
		4: '⟧',
		5: '⌋',
		6: '⌉',
		7: '⌉',
		8: '⌋',
		9: u'\u2027',
		10: r'<span class="largerthannormal">]</span>',
		11: u'\u208e',
		12: u'\u2190',
		13: u'\u005d</span>',  # supposed to be italic as well
		14: u'\u003a\u007c',  # ':|'
		17: u'\u230b\u230b',  # '⌋⌋'
		18: u'\u27eb',  # '⟫'
		20: u'\u23ab',  # '⎫'
		21: u'\u23aa',  # '⎪'
		22: u'\u23ac',  # '⎬'
		23: u'\u23ad',  # '⎭'
		30: u'\u239e',  # '⎞' typo in betacode manual: should say 239e and not 329e (㊞)
		31: u'\u239f',
		32: u'\u23a0',  # '⎠' typo in betacode manual: should say 23a0 and not 32a0 (㊠)
		33: r'｠</hmu_parenthesis_ancient_punctuation>',
		34: r'⸩</span>',  # parenthesis_deletion_marker
		35: r'<hmu_papyrological_project_rt_bracket_35 />',
		49: r'<hmu_papyrological_project_rt_bracket_49 />',  # 49-35
		51: r'</span>',  # erasedepigraphicaltext
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_right_bracket betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def atsignsubstitutions(match):
	"""
	turn @N into unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))

	substitutions = {
		1: r'<hmu_standalone_endofpage />',
		2: r'<hmu_standalone_column_end />',
		3: r'<hmu_standalone_omitted_graphic_marker />',
		4: r'<hmu_standalone_table />',
		5: r'</span>',
		6: r'<br />',
		7: r'——————',
		8: r'———',  # hmu_standalone_mid_line_citation_boundary
		9: r'<span class="breakintext">[break in text for unknown length]</span>',
		10: r'<hmu_standalone_linetoolongforscreen />',
		11: r'<hmu_standalone_tablecellindicator />',
		12: r'<hmu_standalone_subcellindicator />',
		20: r'<hmu_standalone_start_of_columnar_text />',
		21: r'</span>',
		30: r'<hmu_standalone_start_of_stanza />',
		50: r'<hmu_standalone_writing_perpendicular_to_main_text />',
		51: r'<hmu_standalone_writing_inverse_to_main_text />',
		70: r'<span class="quotedtext">',
		71: r'</span>',
		73: r'<span class="poetictext">',
		74: r'</span>',

	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_atsign betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def ltcurlybracketsubstitutes(match):
	"""
	turn {N into markup or unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))

	substitutions = {
		1: r'<hmutitle>',
		2: r'<span class="hmu_marginaltext">',
		3: r'<span class="hmu_scholium">',
		4: r'<span class="hmu_unconventional_form_written_by_scribe">',
		5: r'<span class="hmu_form_altered_by_scribe">',
		6: r'<span class="hmu_discarded_form">',
		7: r'<span class="hmu_reading_discarded_in_another_source">',
		8: r'<span class="hmu_numerical_equivalent">',
		9: r'<span class="hmu_alternative_reading">',
		# 10: u'\u0332',
		10: r'⟨', # the inactive version is what the betacode manual says to do, but in the inscriptions we just want brackets and not a combining underline
		26: r'<span class="hmu_rectified_form">',
		27: u'\u0359',
		28: r'<span class="hmu_date_or_numeric_equivalent_of_date">',
		29: r'<span class="hmu_emendation_by_editor_of_text_not_obviously_incorrect">',
		30: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_30 />',
		31: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_31 />',
		32: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_32 />',
		33: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_33 />',
		34: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_34 />',
		35: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_35 />',
		36: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_36 />',
		37: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_37 />',
		38: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_38 />',
		39: r'<hmu_unhandled_bracket_inscriptional_project_non_text_characters_39 />',
		40: r'<speaker>',
		41: r'<span class="stagedirection">',
		43: r'<span class="serviusformatting">',
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_ltcurlybracket betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def rtcurlybracketsubstitutes(match):
	"""
	turn {N into markup or unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))

	substitutions = {
		1: r'</hmutitle>',  # hmu_title
		2: r'</span>',  # hmu_marginal_text
		3: r'</span>',  # hmu_reference_in_scholium
		4: r'</span>',  # hmu_unconventional_form_written_by_scribe
		5: r'</span>',  # hmu_form_altered_by_scribe
		6: r'</span>',  # hmu_discarded_form
		7: r'</span>',  # hmu_reading_discarded_in_another_source
		8: r'</span>',  # hmu_numerical_equivalent
		9: r'</span>',  # hmu_alternative_reading
		# 10: u'\u0332',
		# cf. ltanglebracketsubstitutes() #1
		# Diogenes seems to have decided that this is the way to go; I wonder how often you will be sorry that you do not have \u0332 instead...
		10: r'⟩', # the inactive version is what the betacode manual says to do, but in the inscriptions we just want brackets and not a combining underline
		26: r'</span>',  # hmu_rectified_form
		27: u'\u0359',
		28: r'</span>',  # hmu_date_or_numeric_equivalent_of_date
		29: r'</span>',  # hmu_emendation_by_editor_of_text_not_obviously_incorrect
		40: r'</speaker>',  # hmu_speaker
		41: r'</span>',  # hmu_stage_direction
		43: r'</span>',  # hmu_servius_bracket
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_rtcurlybracket betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def ltanglebracketsubstitutes(match):
	"""
	turn <N into unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))

	substitutions = {
		# 1: '',
		# Diogenes seems to have decided that this is the way to go; I wonder how often you will be sorry that you do not have \u0332 instead...
		1: '⟨',
	# the inactive version is what the betacode manual says to do, but in the inscriptions we just want brackets and not a combining underline
		2: u'\u2035',
		3: '',
		4: '',
		5: '',
		6: r'<span class="superscript">',  # hmu_shift_font_to_superscript
		7: r'<span class="subscript">',  # hmu_shift_font_to_subscript
		8: '',
		9: r'<span class="hmu_textual_lemma">',  # hmu_textual_lemma
		10: r'<span class="hmu_stacked_text_lower">',  # hmu_stacked_text_lower
		11: r'<span class="hmu_stacked_text_upper">',  # hmu_stacked_text_upper
		12: r'<span class="nonstandarddirection">',
		13: r'<hmu_standalone_singlelinespacing_in_doublespacedtext />',
		14: r'<span class="interlineartext">',
		15: r'<span class="interlinearmarginalia">',  # hmu_interlinear_marginalia
		16: u'\u2035',
		17: '',  # Combining Double Underline
		19: u'\u2035',
		20: r'<span class="hmu_expanded_text">',  # hmu_expanded_text
		21: r'<span class="hmu_latin_expanded_text">',  # hmu_latin_expanded_text
		22: r'<hmu_undocumented_anglebracketspan22>',
		24: r'<hmu_undocumented_anglebracketspan24>',
		30: r'<span class="overline">',  # Combining Overline and Dependent Vertical Bars
		31: r'<span class="strikethrough">',
		32: r'<span class="hmu_overline_and_underline">',  # hmu_overline_and_underline
		34: r'⁄',  # fractions (which have balanced sets of markup...)
		48: r'<hmu_undocumented_anglebracketspan48>',
		50: r'<hmu_undocumented_anglebracketspan50>',
		51: r'<hmu_undocumented_anglebracketspan51>',
		52: r'<hmu_undocumented_anglebracketspan52>',
		53: r'<hmu_undocumented_anglebracketspan53>',
		60: r'<span class="hmu_preferred_epigraphical_text_used">',
		61: r'<span class="hmu_epigraphical_text_inserted_after_erasure">',
		62: r'<span class="lineover">',
		63: r'<span class="hmu_epigraphical_text_after_correction">',
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
		74: r'<span class="diagramlvl04">',
		96: r'<hmu_undocumented_anglebracketspan96>',
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_ltangle betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def rtanglebracketsubstitutes(match):
	"""
	turn >N into unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))

	substitutions = {
		#1: u'\u0332',
		1: r'⟩',  # see note in ltanglebracketsubstitutes()
		2: u'\u2032',
		3: u'\u0361',  # Combining Inverted Breve
		4: u'\u035c',  # Combining Breve Below
		5: u'\u035d',  # Combining Breve
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
		16: u'\u2032',
		17: u'u\0333',
		19: u'\u2032',
		20: r'</span>',  # hmu_expanded_text
		21: r'</span>',  # hmu_expanded_text
		22: r'</hmu_undocumented_anglebracketspan22>',
		24: r'<hmu_undocumented_anglebracketspan24>',
		30: r'</span>',  # Combining Overline and Dependent Vertical Bars
		31: r'</span>',  # strikethrough
		32: r'</span>',  # hmu_overline_and_underline
		34: '',  # fractions
		48: r'<hmu_undocumented_anglebracketspan48>',
		50: r'</hmu_undocumented_anglebracketspan50>',
		51: r'</hmu_undocumented_anglebracketspan51>',
		52: r'</hmu_undocumented_anglebracketspan52>',
		53: r'</hmu_undocumented_anglebracketspan53>',
		60: r'</span>',  # hmu_preferred_epigraphical_text_used
		61: r'</span>',  # hmu_epigraphical_text_inserted_after_erasure
		62: r'</span>',  # epigraphical line over letters
		63: r'</span>',  # hmu_epigraphical_text_after_correction
		64: r'</span>',  # letters in a box
		65: r'</hmu_epigraphical_letters_enclosed_in_wreath>',
		66: r'</hmu_epigraphical_project_escape_66>',
		67: r'</hmu_epigraphical_project_escape_67>',
		68: r'</hmu_epigraphical_project_escape_68>',
		69: r'</hmu_epigraphical_project_escape_69>',
		70: r'</span>',  # hmu_inset_diagram
		71: r'</span>',  # hmu_discrete_section_of_diagram
		72: r'</span>',  # hmu_logical_relationship_in_diagram
		73: r'</span>',  #<span class="diagramlvl03">',
		74: r'</span>',  #<span class="diagramlvl04">'
		96: r'</hmu_undocumented_anglebracketspan96>',
	}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_rtangle betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def quotesubstitutesa(match):
	"""
	turn "N into unicode
	have to do this first because html quotes are going to appear soon
	:param match:
	:return:
	"""

	val = int(match.group(1))

	if simplequotes:
		substitutions = {
			1: '“',
			2: 'QUOTE2',
			3: 'QUOTE3',
			4: u'‘',
			5: u'’',
			6: 'QUOTE6',
			7: 'QUOTE7',
			8: 'QUOTE8'
		}
	else:
		substitutions = {
			1: u'\u201e',
			2: 'QUOTE2',
			3: 'QUOTE3',
			4: u'\u201a',
			5: u'\u201b',
			6: 'QUOTE6',
			7: 'QUOTE7',
			8: 'QUOTE8'
		}

	try:
		substitute = substitutions[val]
	except KeyError:
		substitute = '<hmu_unhandled_quote_markup betacodeval="{v}" />'.format(v=val)
		if warnings:
			print('\t', substitute)

	return substitute


def quotesubstitutesb(match):
	"""
	turn "N into unicode
	:param match:
	:return:
	"""

	val = int(match.group(1))
	core = match.group(2)

	if simplequotes:
		substitutions = {
			2: ['“', '”'],
			3: ['‵', '′'],  # reversed prime and prime (for later fixing)
			6: ['“', '”'],
			7: ['‵', '′'],  # reversed prime and prime (for later fixing)
			8: ['“', '”'],
		}
	else:
		substitutions = {
			2: ['“', '”'],
			3: ['‵', '′'],  # reversed prime and prime (for later fixing)
			6: ['«', '»'],
			7: ['‹', '›'],
			8: ['“', '„'],
		}

	try:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	except KeyError:
		substitute = '<hmu_unhandled_quote_markup betacodeval="{v}" />{c}'.format(v=val, c=core)
		if warnings:
			print('\t', substitute)

	return substitute

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
		
		1: u'\u03df',
		2: u'\u03da',
		3: u'\u03d9',
		4: u'\u03d9',
		5: u'\u03e1',
		6: u'\u2e0f',
		7: r'<hmu_idiosyncratic_char value="7">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		8: u'\u2e10',
		9: u'\u0301',
		10: u'\u03fd',
		11: u'\u03ff',
		12: u'\u2014',
		13: u'\u203b',
		14: u'\u2e16',
		15: u'\u003e',
		16: u'\u03fe',
		# 17: u'002f', # careful: '/' is dangerous
		18: r'《',
		19: u'\u0300',
		20: r'𐅵',
		21: r'𐅵',
		22: u'\u0375',
		23: u'\u03d9',
		24: r'𐅵',
		25: r'?',
		69: u'\u039c',
		73: u'\u205a',
		74: u'\u205d',
		82: u'\u02ca',
		83: u'\u02cb',
		86: u'\u02bc',
		87: u'\u0394\u0345',
		100: u'\u10186',
		101: u'𐅻', #trouble with the four character unicode codes: uh oh
		102: u'\u10182<6\u03c56>', # upsilon supposed to be superscript too: add betacode for that <6...6>
		103: u'\u039b\u0338',
		104: u'\u10182<6\u03bf6>',  # the omicron is supposed to be superscript too: add betacode for that <6...6>
		105: r'<hmu_idiosyncratic_char value="105">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		106: u'\u10184',
		107: r'<hmu_idiosyncratic_char value="107">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		108: r'<hmu_idiosyncratic_char value="108">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		109: u'𐆂<6\u03bf6>', # the omicron is supposed to be superscript too: add betacode for that <6...6>
		111: r'𐆈', # 𐆈- GREEK GRAMMA SIGN; Unicode: U+10188, UTF-8: F0 90 86 88
		116: u'\u1017c',
		117: u'\u10183',
		118: u'\u03bb\u0338',
		121: u'u\03be\u0338',
		125: u'𐆂<6\u03c56>', # the upsilon is supposed to be superscript too: add betacode for that <6...6>
		129: u'\u039b\u0325',
		128: u'u\03b',
		130: u'\u1018a',
		131: u'\u10177',
		132: u'\u03b2\u0388',
		134: u'\u0393<6\u03b26>', # the beta is supposed to be superscript too: add betacode for that <6...6>
		135: u'\u02d9',
		136: u'\u03a3', # capital sigma: stater
		137: u'\u0393<6\u03b26>', #the beta is supposed to be superscript: add betacode for that <6...6>
		150: u'\u221e',
		151: u'\u2014',
		152: u'\u205a\u2014',
		157: r'<hmu_idiosyncratic_char value="157">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		
		159: u'\u2237\u0344',
		160: u'\u007e\u0323',
		161: r'𐅵',
		162: u'\u25a1',
		163: u'\u00b6',
		165: u'\u00d7',
		166: u'\u2a5a',
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
		303: u'›',
		305: u'\u2e0e',
		310: u'\u2e0e',
		313: u'\u2e0e',
		314: r'<hmu_idiosyncratic_char value="314">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		315: u'\u2e0e',
		452: u'\u2310',
		453: u'\u2e11',
		454: u'\u2e10',
		456: u'\u2e0e',
		457: r'<hmu_idiosyncratic_char value="457">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		458: u'\u0387',
		459: u'\u00b7',
		460: u'\u2014',
		461: u'\u007c',
		465: u'\u2627',
		467: u'\u2192',
		468: u'\u2e0e',
		476: u'\u0283',
		501: r'π<6ιθ6>',  # abbreviation for πιθανόν: added own betacode - <6...6>
		502: r'🜚', # listed as idiosyncratic; but looks like 'alchemical symbol for gold': U+1F71A
		504: u'\u2e0e',
		505: u'\u205c',
		507: u'\u2e14',
		508: u'\u203b',
		512: u'\u03fd',
		515: r'𐆅',
		516: u'\u0394\u0345',
		517: r'𐆅',
		519: u'\u2191',
		520: u'\u2629',
		# 522: u'\u', # markup <rotate> 0397
		523: u'\u2e13',
		524: u'\u2297',
		526: u'\u2190',
		527: u'\u02c6',
		532: u'\u2e12',
		533: u'\u03da',
		534: u'\u0302',
		535: r'<hmu_idiosyncratic_char value="535">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		536: r'<hmu_idiosyncratic_char value="536">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		537: r'<hmu_idiosyncratic_char value="537">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		538: r'<hmu_idiosyncratic_char value="538">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		540: r'<hmu_idiosyncratic_char value="540">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		541: r'<hmu_idiosyncratic_char value="541">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		542: u'\u03a1\u0336',
		543: r'<hmu_idiosyncratic_char value="543">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		545: r'<hmu_idiosyncratic_char value="545">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		546: r'<hmu_idiosyncratic_char value="546">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		547: r'<hmu_idiosyncratic_char value="547">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		552: r'<hmu_idiosyncratic_char value="552">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		550: u'\u003a\u003a\u2e2e',
		553: r'<hmu_idiosyncratic_char value="553">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		554: r'<hmu_idiosyncratic_char value="554">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		555: r'<hmu_idiosyncratic_char value="555">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		556: u'\u2629',
		561: u'\u2191',
		563: u'\u1d242',
		572: r'𝈩', # 𝈩GREEK INSTRUMENTAL NOTATION SYMBOL-19; Unicode: U+1D229, UTF-8: F0 9D 88 A9
		589: r'𝈿', # 𝈿GREEK INSTRUMENTAL NOTATION SYMBOL-52; Unicode: U+1D23F, UTF-8: F0 9D 88 BF
		604: r'𝈦', # 𝈦GREEK INSTRUMENTAL NOTATION SYMBOL-14; Unicode: U+1D226, UTF-8: F0 9D 88 A6
		615: r'𝈰', # 𝈰GREEK INSTRUMENTAL NOTATION SYMBOL-30; Unicode: U+1D230, UTF-8: F0 9D 88 B0
		618: r'𝈴', # 𝈴GREEK INSTRUMENTAL NOTATION SYMBOL-38; Unicode: U+1D234, UTF-8: F0 9D 88 B4
		635: r'𝈝', # 𝈝GREEK INSTRUMENTAL NOTATION SYMBOL-1; Unicode: U+1D21D, UTF-8: F0 9D 88 9D
		651: u'\u03a7',
		652: u'\u03a4',
		660: u'\u0391',
		661: u'\u0392',
		662: u'\u03a5',
		665: r'𝈴', # 𝈴GREEK INSTRUMENTAL NOTATION SYMBOL-38; Unicode: U+1D234, UTF-8: F0 9D 88 B4
		666: r'𝈯', # 𝈯GREEK INSTRUMENTAL NOTATION SYMBOL-29; Unicode: U+1D22F, UTF-8: F0 9D 88 AF
		681: r'<hmu_idiosyncratic_char value="681">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		682: r'<hmu_idiosyncratic_char value="682">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		688: u'\u03bc\u030a',
		689: r'𐅵',
		692: u'\u27c1',
		700: u'\u205e',
		701: r'<hmu_idiosyncratic_char value="701">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		702: r'<hmu_idiosyncratic_char value="702">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		703: u'\u25cb\u25cb\u25cb',
		704: u'\u2014\u0307',
		705: r'<hmu_idiosyncratic_char value="705">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		706: r'<hmu_idiosyncratic_char value="706">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		707: r'<hmu_idiosyncratic_char value="707">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		708: r'<hmu_idiosyncratic_char value="708">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		709: u'\u223b',
		711: u'\u03fb',
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
		801: r'𐅁',
		802: r'𐅀',
		821: u'\u03a3',
		853: u'\u0399',
		862: u'\u0394',
		863: r'𐅄',
		865: r'𐅅',
		866: u'\u03a7',
		1000: r'𐅼',
		1001: r'𐅽',
		1003: r'𐅾',
		1100: u'\u2183',
		1101: r'IS',
		1102: r'H',
		1103: u'\u0323\u0313',
		1104: u'S\u0038',  # deprecated, use &S%162$
		1105: u'\u004d\u030a',
		1106: r'<hmu_idiosyncratic_char value="1106">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1107: u'\u0053\u0335\u0053\u0336',
		1108: u'\u0058\u0036',
		1109: u'\u003d',
		1110: u'\u002d',
		1111: u'\u00b0',
		1112: r'<hmu_idiosyncratic_char value="1112">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		1113: r'<hmu_idiosyncratic_char value="1113">⌑</hmu_idiosyncratic_char>', # idiosyncratic
		1114: u'\u1d201',
		1115: u'\u007c',
		1118: r'<hmu_idiosyncratic_char value="1118">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1119: u'\u0110',
		1120: r'<hmu_idiosyncratic_char value="1120">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1121: u'\u005a',
		1122: r'<hmu_idiosyncratic_char value="1122">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1123: r'<hmu_idiosyncratic_char value="1123">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1125: r'<hmu_idiosyncratic_char value="1125">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1126: u'\u004f',
		1135: u'\u002f\u002f',
		1136: u'\u2112',
		1314: u'\u006e\u030a',
		1316: u'\u0292',
		1320: u'\u0375\u0311',
		1326: r'<hmu_idiosyncratic_char value="1326">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1338: r'𐅾',
		1341: r'<hmu_idiosyncratic_char value="1341">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1501: r'<hmu_idiosyncratic_char value="1501">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1502: u'\u03a7\u0374',
		1503: r'<hmu_idiosyncratic_char value="1503">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1504: r'<hmu_idiosyncratic_char value="1504">⌑</hmu_idiosyncratic_char>',  # idiosyncratic
		1506: u'\u0300\u0306',
		1510: u'Α\u0338<6\u0304ν\u002f>6' # A%162<6E%26N%3>6 [!]
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
		12: u'\u002a', # look out for future problems: *
		14: u'\u00a7',
		15: u'\u02c8',
		17: u'\u2016',
		18: u'\u0025', # look out for future problems: '
		19: u'\u2013',
		20: u'\u0301',
		24: u'\u0342',
		25: u'\u0327',
		26: u'\u0304',
		27: u'\u0306',
		28: u'\u0308',
		29: u'\u0323\u0323',
		30: u'\u02bc',
		31: u'u\02bd',
		32: u'\u00b4', # look out for future problems: ´
		33: u'\u0060', # look out for future problems: `
		34: u'\u1fc0',
		35: u'\u1fce',
		38: u'\u1fdf',
		39: u'\u00a8',
		40: u'\u23d1',
		41: u'\u2013',
		42: u'\u23d5',
		43: u'\u00d7',
		44: u'\u23d2',
		45: u'\u23d3',
		46: u'\u23d4',
		47: u'\u10111',
		48: u'u23d1\u23d1',
		49: u'\u23d1\u23d1\u23d1',
		80: u'\u0076\u002E', # supposed to put the 'v' in italics too
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
		101: u'\u0023', # had best do pounds before percents since this is '#'
		103: u'\u005c', # backslash: careful
		106: u'\u224c',
		107: u'\u007e',
		108: u'\u00b1',
		109: u'\u00b7',
		110: u'\u25cb',
		127: u'\u032f',
		128: u'\u0302',
		129: u'\u2020',
		133: u'\u1fcd',
		134: u'\u1fcf',
		141: u'\u23d6',
		144: u'\u23d1\u0036',
		145: u'\u2013\u0301',
		146: u'\u00b7',
		147: u'\u030a',
		148: u'\u030c',
		149: u'\u0328',
		150: u'\u007c',
		159: u'\u00d7',
		# 157: flipped dagger
		162: u'\u0338'
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
		18: u'27ea',
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
		32: u'\u32a0',
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
		27: u'\u0359',
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
		27: u'\u0359',
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
		3: '',
		4: '',
		5: '',
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
		3: u'\u0361',
		4: u'\u035c',
		5: u'\u035d',
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
		30: [r'<span class="extrasmall">', r'</span>'],
		20: [r'<span class="largerthannormal">', r'</span>'],
		15: [r'<span class="smallerthannormalsubscript">', r'</span>'],
		14: [r'<span class="smallerthannormalsuperscript">', r'</span>'],
		13: [r'<span class="smallerthannormalitalic">', r'</span>'],
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
	linetermination = re.compile(r'(\&\d{0,2})(.*?)(\s{0,1}$)')
	internaltermination = re.compile(r'(\&\d{0,2})(.*?)\$(\d{0,2})')
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


def cleanworkname(betacodeworkname):
	"""
	turn a betacode workname into a 'proper' workname
	:param betacodeworkname:
	:return:
	"""
	
	if '*' in betacodeworkname and '$' not in betacodeworkname:
		re.sub(r'\*',r'$*',betacodeworkname)
	
	workname = replacelatinbetacode(betacodeworkname)
	
	percents = re.compile(r'\%(\d{1,3})')
	workname = re.sub(percents, percentsubstitutes, workname)
	workname = re.sub(r'\[2(.*?)]2', r'⟪\1⟫',workname)
	workname = re.sub(r'<.*?>','', workname)

	return workname
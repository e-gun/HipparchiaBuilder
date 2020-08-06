# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from string import punctuation

from builder.dbinteraction.connection import setconnection
from builder.parsers.betacodeandunicodeinterconversion import cleanaccentsandvj
from builder.parsers.transliteration import stripaccents

euripides = {
	"Al.": ("035", "Alcestis"),
	"Alc.": ("035", "Alcestis"),
	"Andr.": ("039", "Andromacha"),
	"Ba.": ("050", "Bacchae"),
	"Cyc.": ("034", "Cyclops"),
	"El.": ("042", "Electra"),
	"Epigr.": ("031", "Epigrammata"),
	"U1": ("022", "Epinicium in Alcibiadem (fragmenta)"),
	"Fr.": ("020", "Fragmenta"),
	"U3": ("033", "Fragmenta"),
	"U4": ("029", "Fragmenta"),
	"U5": ("025", "Fragmenta Alexandri"),
	"Antiop.": ("024", "Fragmenta Antiopes"),
	"Hyps.": ("026", "Fragmenta Hypsipyles"),
	"Oen.": ("030", "Fragmenta Oenei"),
	"Phaeth.": ("023", "Fragmenta Phaethontis"),
	"U6": ("032", "Fragmenta Phaethontis incertae sedis"),
	"U7": ("027", "Fragmenta Phrixei (P. Oxy. 34.2685)"),
	"U8": ("028", "Fragmenta fabulae incertae"),
	"U9": ("021", "Fragmenta papyracea"),
	"Hec.": ("040", "Hecuba"),
	"Hel.": ("047", "Helena"),
	"Heracl.": ("037", "Heraclidae"),
	"HF": ("043", "Hercules"),
	"Hipp.": ("038", "Hippolytus"),
	"Ion": ("046", "Ion"),
	"IA": ("051", "Iphigenia Aulidensis"),
	"IT": ("045", "Iphigenia Taurica"),
	"Med.": ("036", "Medea"),
	"Or.": ("049", "Orestes"),
	"Ph.": ("048", "Phoenisae"),
	"Rh.": ("052", "Rhesus"),
	"Supp.": ("041", "Supplices"),
	"Tr.": ("044", "Troiades")
}

seneca = {
	'ad Helv.':  ('1017', '012:12:'),
	'ad Marc.': ('1017', '012:6:'),
	'ad Polyb.': ('1017', '012:11:'),
	'Agm.': ('1017', '007:'),
	'Agam.': ('1017', '007:'),
	'Apoc.': ('1017', '011:'),
	'Apocol.': ('1017', '011:'),
	'Apocol.p.': ('1017', '011:'),
	'Ben.': ('1017', '013:'),
	'Benef.': ('1017', '013:'),
	'Brev. Vit.': ('1017', '014:'),
	'Clem.': ('1017', '012:10:'),
	'de Clem.': ('1017', '012:10:'),
	'de Prov.': ('1017', '012:1:'),
	'Ep': ('1017', '015:'),
	'Ep.': ('1017', '015:'),
	'Consol. ad Marc.': ('1017', '012:6:'),
	'Cons. ad Marc.': ('1017', '012:6:'),
	'Cons. ad Helv.': ('1017', '012:12:'),
	'Cons. ad Polyb.': ('1017', '012:11:'),
	'Cons. Helv.': ('1017', '012:12:'),
	'Cons. Marc.': ('1017', '012:6:'),
	'Cons. Polyb.': ('1017', '012:11:'),
	'Const.': ('1017', '012:2:'),
	'Const. Sap.': ('1017', '012:2:'),
	'Contr': ('1014', '001:'),  # the father...
	'Contr.': ('1014', '001:'),  # the father...
	'Controv.': ('1014', '001:'),  # the father...
	'Exc. Contr.': ('1014', '002:'),  # the father...
	'Exc. Controv.': ('1014', '002:'),  # the father...
	'Excerpt. Contr.': ('1014', '002:'),  # the father...
	'Excerpt. Controv.': ('1014', '002:'),  # the father...
	'Helv.': ('1017', '012:12:'),
	'Herc. Fur.': ('1017', '001:'),
	'Herc Oet.': ('1017', '009:'),
	'Herc. Oet.': ('1017', '009:'),
	'Hipp.': ('1017', '005:'),
	'Hippol.': ('1017', '005:'),
	'Ira,': ('1017', '012:3'),  # note that we just sent I, II, and III to the same place...
	'Lud. Mort. Claud.': ('1017', '011:'),
	'Med.': ('1017', '004:'),
	'Mort. Claud.': ('1017', '011:'),
	'N. Q.': ('1017', '016:'),
	'Oct.': ('1017', '010:'),
	'Octav.': ('1017', '010:'),
	'Ot. Sap.': ('1017', '012:8:'),
	'Oed.': ('1017', '006:'),
	'Oedip': ('1017', '006:'),
	'Oedip.': ('1017', '006:'),
	'Oet.': ('1017', '009:'),
	# 'Orest.': ('1017', '006:'),  # ?!
	'Phaedr.': ('1017', '005:'),
	'Phoen.': ('1017', '003:'),
	'Polyb.': ('1017', '012:11:'),
	'Prov': ('1017', '012:1:'),
	'Prov.': ('1017', '012:1:'),
	'Q. N.': ('1017', '016:'),
	'Suas.': ('1014', '003:'),  # the father...
	'Thyest.': ('1017', '008:'),
	'Tranq.': ('1017', '012:9:'),
	'Tranq. An.': ('1017', '012:9:'),
	'Tranq. Vit.': ('1017', '012:9:'),
	'Troad.': ('1017', '002'),
	'Vit. B.': ('1017', '012:7:'),
	'Vit. Beat.': ('1017', '012:7:'),
}

"""
lingering issue:

lt1017w012  | Dialogi
	de ira1: 3
	de ira2: 4
	de ira3: 5
"""

sallust = {
	'C.': '001',
	'Cat.': '001',
	'J': '002',
	'J.': '002',
	'Jug.': '002',
	'H.': '003',
	'Hist.': '003'
}

suetonius = {
	'aug.': 'Aug',
	'cal.': 'Cal',
	'cl.': 'Cl',
	'dom.': 'Dom',
	'gal.': 'Gal',
	'jul.': 'Jul',
	'nero': 'Nero',
	'otho': 'Otho',
	'tib.': 'Tib',
	'tit.': 'Tit',
	'vesp.': 'Ves',  # the one that breaks the pattern
	'vit.': 'Vit',
}

"""

GREEK

"""

def conditionalworkidswapper(match):
	"""

	sample match[0]
		<bibl n="Perseus:abo:tlg,0011,007:897" default="NO" valid="yes"><author>S.</author> <title>OC</title> 897</bibl>

	match[1]
		0011

	match[2]
		007

	match[3]
		OC

	:param match:
	:return:
	"""

	greekauthorstofix = {'0006': euripides}
	newtext = match[0]

	if match[1] in greekauthorstofix:
		works = greekauthorstofix[match[1]]
		if match[3] in works:
			try:
				item = works[match[3]]
				newtext = re.sub(r'tlg,(....),(...)', r'tlg,\1,'+item[0], match[0])
			except KeyError:
				# print('keyerror for' + match[3])
				pass
		else:
			# print(match[3] + ' not in works of ' + match[1])
			pass
	return newtext


def perseusworkmappingfixer(entrytext: str) -> str:
	"""

	some perseus references are broken; attempt to fix them

	turn something like
		Perseus:abo:tlg,0006,008:2
	into
		Perseus:abo:tlg,0006,041:2

	:param entrytext:
	:return:
	"""

	thumbprint = re.compile(r'<bibl n="Perseus:abo:tlg,(....),(...):.*?<title>(.*?)</title>.*?</bibl>')
	fixentry = re.sub(thumbprint, conditionalworkidswapper, entrytext)

	return fixentry


"""

ROMAN DRAMA

"""

def latindramacitationformatconverter(entrytext: str, dbconnection=None) -> str:
	"""

	plautus is cited by act, etc vs by line

	attempt to fix this...

	:param entrytext:
	:return:
	"""

	needcleanup = False
	if not dbconnection:
		needcleanup = True
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()
	# dbconnection.setautocommit()

	authorstofix = {'phi,0119': 'Plautus',
	                'phi,0134': 'Terence'}

	citationfinder = re.compile(r'(<cit>.*?</cit>)')
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation)))
	locusfinder = re.compile(r'</author>\s(.*?)\s(.*?)</bibl></cit>')
	quotefinder = re.compile(r'<quote lang="la">(.*?)</quote>')

	querytemplate = """
		SELECT level_00_value FROM {t}
			WHERE wkuniversalid = %s and stripped_line ~* %s
	"""

	citations = re.findall(citationfinder, entrytext)

	for au in authorstofix:
		adb = re.sub(r'phi,', 'lt', au)
		targetcitation = re.compile(r'<bibl n="Perseus:abo:{a},(...):(.*?)"[^>]*?>'.format(a=au))
		citationswap = re.compile(r'(<bibl n="Perseus:abo:{a},...:)(.*?)("[^>]*?>)'.format(a=au))

		for c in citations:
			t = re.search(targetcitation, c)
			if t:
				q = re.search(quotefinder, c)
				if q:
					lineval = None
					hit = None
					quote = cleanaccentsandvj(stripaccents(q[1].lower()))
					quote = re.sub(punct, str(), quote)
					wkid = t[1]
					# loc = t[2]

					trialnumber = 0
					for direction in ['reverse', 'forward', 'ends']:
						seeking = quote
						while seeking and not hit:
							trialnumber += 1
							hit = lookforquote(adb, wkid, seeking, querytemplate, dbcursor)
							if not hit:
								seeking = shinkquote(seeking, direction)

					if hit:
						lineval = hit[0]
						# print('success on try #', trialnumber)
						# "success on try # 6" !

					if lineval:
						newcitation = re.sub(locusfinder, r'</author> \1 {lv}</bibl></cit>'.format(lv=lineval), c)
						newcitation = re.sub(citationswap, r'\1ZZZ" rewritten="yes\3', newcitation)
						newcitation = re.sub('ZZZ', lineval, newcitation)
						c = re.escape(c)
						try:
							entrytext = re.sub(c, newcitation, entrytext)
						except re.error:
							# re.error: bad escape \s at position 88
							pass

	if needcleanup:
		dbconnection.connectioncleanup()

	return entrytext


def lookforquote(adb: str, wkid: str, quote: str, querytemplate: str, dbcursor) -> tuple:
	"""

	the search proper

	:param adb:
	:param wkid:
	:param quote:
	:param querytemplate:
	:param dbcursor:
	:return:
	"""

	data = ('{a}w{w}'.format(a=adb, w=wkid), quote)
	# print(querytemplate.format(t=adb), data)
	dbcursor.execute(querytemplate.format(t=adb), data)
	hit = dbcursor.fetchone()

	return hit


def shinkquote(quote: str, direction: str) -> str:
	"""

	sometimes quotes span lines; this hides them from us

	:param quote:
	:return:
	"""

	minimal = 2
	newquote = str()
	qs = quote.split(' ')
	if len(qs) > minimal and direction == 'reverse':
		# newquote = ' '.join(qs[1:-1])
		newquote = ' '.join(qs[:-1])
	elif len(qs) > minimal and direction == 'forward':
		newquote = ' '.join(qs[1:])
	elif len(qs) > minimal and direction == 'ends':
		newquote = ' '.join(qs[-1:1])

	return newquote


"""

MISC LATIN FIXES

"""


def oneofflatinworkremapping(entrytext: str) -> str:
	"""

	hand off some oddballs

	:param entrytext:
	:return:
	"""

	fixers = [fixfrontinus, fixmartial, fixseneca, fixsallust, fixsuetonius, fixvarro]

	fixedentry = entrytext
	for f in fixers:
		fixedentry = f(fixedentry)

	return fixedentry


def fixmartial(entrytext: str) -> str:
	"""

	all of martial has been assigned to work 001

	:param entrytext:
	:return:
	"""

	findmartial = re.compile(r'"Perseus:abo:phi,1294,001:(.*?)"')
	findspectacles = re.compile(r'"Perseus:abo:phi,1294,002:(Spect. )(.*?)"')

	newentry = re.sub(findmartial, r'"Perseus:abo:phi,1294,002:\1" rewritten="yes"', entrytext)
	newentry = re.sub(findspectacles, r'"Perseus:abo:phi,1294,001:\2"', newentry)

	return newentry


def fixfrontinus(entrytext: str) -> str:
	"""


	n="Perseus:abo:phi,1245,001:Aquaed. 104"

	but Aq. is 002

	:param entrytext:
	:return:
	"""

	findaquad = re.compile(r'"Perseus:abo:phi,1245,001:Aquaed\.(.*?)"')

	newentry = re.sub(findaquad, r'"Perseus:abo:phi,1245,002:\1" rewritten="yes"', entrytext)

	return newentry


def fixsallust(entrytext: str) -> str:
	"""

	n="Perseus:abo:phi,0631,001:J. 62:8" --> jugurtha

	:param entrytext:
	:return:
	"""

	findsallust = re.compile(r'"Perseus:abo:phi,0631,001:(.*?)\s(.*?)"')

	newentry = re.sub(findsallust, sallusthelper, entrytext)

	return newentry


def sallusthelper(regexmatch) -> str:
	"""

	work some substitution magic on the sallust match

	the key work is done by the seneca dict() above

	:param regexmatch:
	:return:
	"""

	returntext = regexmatch.group(0)
	work = regexmatch.group(1).strip()
	pasg = regexmatch.group(2)

	sallusttemplate = '"Perseus:abo:phi,0631,{wk}:{loc}" rewritten="yes"'

	try:
		knownsubstitute = sallust[work]
	except KeyError:
		# print('unk sallust: "{w}"'.format(w=work))
		return returntext

	newentry = sallusttemplate.format(wk=knownsubstitute, loc=pasg)

	return newentry



def fixseneca(entrytext: str) -> str:
	"""

	plenty of problems given that StE and StY are at times confused...: 1014 vs 1017

	bad:
		"Perseus:abo:phi,1014,001:Ep. 29"; EM is 1017,015
		"Perseus:abo:phi,1014,001:Tranq. 15"; TQ is 1017,012:9:15
		"Perseus:abo:phi,1014,001:Contr. 1 praef";

	de Ira 1 vs 2 vs 3 remains a problem

	'ib.' remains a problem

	:param entrytext:
	:return:
	"""

	findem = re.compile(r'"Perseus:abo:phi,1014,001:(.*?)(\d.*?)"')

	newentry = re.sub(findem, senecahelper, entrytext)

	return newentry


def senecahelper(regexmatch) -> str:
	"""

	work some substitution magic on the seneca match

	the key work is done by the seneca dict() above

	:param regexmatch:
	:return:
	"""

	returntext = regexmatch.group(0)
	work = regexmatch.group(1).strip()
	pasg = regexmatch.group(2)

	senecatemplate = '"Perseus:abo:phi,{au},{wk}{loc}" rewritten="yes"'

	try:
		knownsubstitute = seneca[work]
	except KeyError:
		# print('unk seneca: "{w}"'.format(w=work))
		return returntext

	newentry = senecatemplate.format(au=knownsubstitute[0], wk=knownsubstitute[1], loc=pasg)

	return newentry


def fixsuetonius(entrytext: str) -> str:
	"""

	"Perseus:abo:phi,1348,001:life=aug.:82" --> "Perseus:abo:phi,1348,001:Aug.:82"

	:param entrytext:
	:return:
	"""

	findlife = re.compile(r'"Perseus:abo:phi,1348,001:life=(.*?)(:.*?)"')

	newentry = re.sub(findlife, suetoniushelper, entrytext)

	return newentry


def suetoniushelper(regexmatch):
	"""

	substitution magic via the suetonius dict()

	:param regexmatch:
	:return:
	"""

	returntext = regexmatch.group(0)
	work = regexmatch.group(1).strip()
	pasg = regexmatch.group(2)

	suetoniustemplate = '"Perseus:abo:phi,1348,001:{wk}{loc}" rewritten="yes"'

	try:
		knownsubstitute = suetonius[work]
	except KeyError:
		# print('unk suetonius: "{w}"'.format(w=work))
		return returntext

	newentry = suetoniustemplate.format(wk=knownsubstitute, loc=pasg)

	return newentry


def fixvarro(entrytext: str) -> str:
	"""

	the DLL citations are wrong:
		"Perseus:abo:phi,0684,001:L. L. 5:section=59"

	RR too:
		"Perseus:abo:phi,0684,001:R. R. 1:32:2"

	lingering issue: 'ibidem'
		"Perseus:abo:phi,0684,001:ib. 3:15:2"

	lingering issue: DNE
		"Perseus:abo:phi,0684,001:Sent. Mor. p. 28"
		"Perseus:abo:phi,0684,001:Fragm. p. 241"

	lingering issue: guaranteed mishit
		"Perseus:abo:phi,0684,001:Sat. Men. 95:10"

	lingering issue: might-be-right-might-not
		"Perseus:abo:phi,0684,001:1:22"
		[is wrong since 'vernum' is in 002 but not in 001]
		vernum,</quote> <bibl n="Perseus:abo:phi,0684,001:33:3"


	:param entrytext:
	:return:
	"""

	finddll = re.compile('"(Perseus:abo:phi,0684,001:)(L. L. )(.*?):(section=)(.*?)"')
	findrr = re.compile('"(Perseus:abo:phi,0684,)(001):(R. R. )(.*?)"')
	findmenn = re.compile('"(Perseus:abo:phi,0684,001:Sat. Menip\. )(.*?)"')

	newentry = re.sub(finddll, r'"\1\3:\5" rewritten="yes"', entrytext)
	newentry = re.sub(findrr, r'"Perseus:abo:phi,0684,002:\4" rewritten="yes"', newentry)
	newentry = re.sub(findmenn, r'"Perseus:abo:phi,0684,011:\2" rewritten="yes"', newentry)

	return newentry



# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from string import punctuation

try:
	from builder.dbinteraction.connection import setconnection
except:
	setconnection = None
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

neposstrings = {
	'Ages.': 'Ag',
	'Alcib.': 'Alc',
	'Arist.': 'Ar',
	# 'Att',
	'Cat.': 'Ca',
	'Cato,': 'Ca',
	'Cato': 'Ca',
	'Chab.': 'Cha',
	'Chabr.': 'Cha',
	'Chabr,': 'Cha',
	# 'Cim',
	# 'Con',
	'Datam.': 'Dat',
	'Dion.': 'Di',
	'Dion,': 'Di',
	'Epam.': 'Ep',
	'Eun.': 'Eum',
	'Eun,': 'Eum',
	'Hamilc.': 'Ham',
	'Hann.': 'Han',
	'Hannib.': 'Han',
	'Iphicr.': 'Iph',
	'Iphic.': 'Iph',
	'Lyt.': 'Lys',
	'Mil.': 'Milt',
	# 'Paus',
	'Pelop.': 'Pel',
	'Ph.': 'Phoc',
	'Regg.': 'Reg',
	# 'Them',
	'Thras.': 'Thr',
	'Tim.': 'Timol',
	# 'Timoth'
}

neposnumbers = {
	'002': 'Them',
	'004': 'Paus',
	'005': 'Cim',
	'006': 'Lys',
	'007': 'Alc',
	'009': 'Con',
	'011': 'Iph',
	'013': 'Timoth',
	'014': 'Dat',
	'015': 'Ep',
	'016': 'Pel',
	'017': 'Ag',
	'018': 'Eum',
	'019': 'Phoc',
	'020': 'Timol',
	'021': 'Reg',
	'022': 'Ham',
	'023': 'Han',
	'025': 'Att',
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
	'Brev. Vit.': ('1017', '012:10:'),
	'Clem.': ('1017', '014:'),
	'de Clem.': ('1017', '014:'),
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

	entriesfound = re.findall(r'<bibl.*?</bibl>', newtext)
	if len(entriesfound) > 1:
		# fix the last entry
		tailtext = entriesfound[-1]
		headtext = re.sub(tailtext, str(), newtext)
		thumbprint = re.compile(r'<bibl n="Perseus:abo:tlg,(....),(...):.*?<title>(.*?)</title>.*?</bibl>')
		tailtext = re.sub(thumbprint, conditionalworkidswapper, tailtext)
		# ok, but what about fixing the other entries that remain...
		try:
			headtext = re.sub(thumbprint, conditionalworkidswapper, headtext)
		except RecursionError:
			# we did our best...
			pass
		newtext = headtext + tailtext
		return newtext

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

	# print(' in:', match[0])
	# print('out:', newtext)

	return newtext


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
						newcitation = re.sub(citationswap, r'\1ZZZ" class="rewritten\3', newcitation)
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

	fixers = [fixciceroverrinesections, fixciceromiscsections, fixfrontinus, fixmartial, fixnepos, fixpropertius,
	          fixseneca, fixsallust, fixsuetonius, fixvarro]

	fixedentry = entrytext
	for f in fixers:
		fixedentry = f(fixedentry)

	return fixedentry


def fixciceroverrinesections(entrytext: str) -> str:
	"""

	this sort of thing is not helpful
		<bibl n="Perseus:abo:phi,0474,005:5:21:section=53" default="NO" valid="yes"><author>id.</author> Verr. 2, 5, 21, § 53</bibl>
		"Perseus:abo:phi,0474,005:5:21:section=53"

	alternate version....

		<bibl n="Perseus:abo:phi,0474,005:13:37" default="NO" valid="yes"><author>Cic.</author> Verr. 1, 13, 37</bibl>

	note that V 1.13.37 should be 1.1.13.37 insteat (and that is still wrong because of the '13')

	:param entrytext:
	:return:
	"""

	findsection = re.compile(r'<bibl n="Perseus:abo:phi,0474,005:(.*?:)section=(.*?)" (.*?)><author>(.*?)</author> Verr\. (.), (.*?)</bibl>')
	altfind = re.compile(r'<bibl n="Perseus:abo:phi,0474,005:(.*?:)(.*?)" (.*?)><author>(.*?)</author> Verr\. (.), (.*?)</bibl>')

	# x = re.findall(findsection, entrytext)
	# if x:
	# 	print(x[0])

	newentry = re.sub(findsection, ciceroverrinehelper, entrytext)
	newentry = re.sub(altfind, ciceroverrinehelper, newentry)

	return newentry


def ciceroverrinehelper(regexmatch) -> str:
	"""

	need to assign the right book to the citation

	the also contains the 'chapter' which we do not use

	in:
		 <bibl n="Perseus:abo:phi,0474,005:5:21:section=53" default="NO" valid="yes"><author>id.</author> Verr. 2, 5, 21, § 53</bibl>

	you get
		re.findall(findsection, a)
		[('5:21:', '53', 'default="NO" valid="yes"', 'id.', '2', '5, 21, § 53')]

	:param regexmatch:
	:return:
	"""

	returntext = regexmatch.group(0)
	passage = regexmatch.group(1)
	section = regexmatch.group(2)
	tail = regexmatch.group(3)
	auth = regexmatch.group(4)
	vbook = regexmatch.group(5)
	vcit = regexmatch.group(6)
	bb = vbook

	if vbook == '1':
		vbook = '1:1'
		bb = '1, 1'

	if len(passage.split(':')) > 1:
		passage = passage.split(':')[0]
		passage = passage + ':'

	verrinetemplate = '<bibl n="Perseus:abo:phi,0474,005:{b}:{p}{s}" {t} class="rewritten"><author>{a}</author> Verr. {bb}, {c}</bibl>'

	newentry = verrinetemplate.format(p=passage, b=vbook, s=section, t=tail, a=auth, bb=bb, c=vcit)

	return newentry


def fixciceromiscsections(entrytext: str) -> str:
	"""

	RUN THE VERRINES FIRST (because it needs 'section=')

	<quote lang="la">omnes de tuā virtute commemorant,</quote> <bibl n="Perseus:abo:phi,0474,058:1:1:13:section=37" default="NO" valid="yes"><author>Cic.</author> Q. Fr. 1, 1, 13, § 37</bibl>

	this should just be 1.1.37

	the problem is confined almost exclusively to lt0474w058

	a couple of items will remain in lt0474w005 (Verr.) [these got broken and will remain broken?]

	a couple in lt0474w047 (Parad. Stoic.)

	:param entrytext:
	:return:
	"""

	sectionfinder = re.compile(r'"Perseus:abo:phi,0474,(...):([^"]*?):section=(.*?)"')

	newentry = re.sub(sectionfinder, ciceromiscsectionhelper, entrytext)

	return newentry


def ciceromiscsectionhelper(regexmatch) -> str:
	"""

	do the heavy lifting for fixciceromiscsections()

	:param regexmatch:
	:return:
	"""

	returntext = regexmatch.group(0)
	thework = regexmatch.group(1)
	passage = regexmatch.group(2)
	section = regexmatch.group(3)

	ps = passage.split(':')
	if len(ps) > 1:
		ps = ps[:-1]
		passage = ':'.join(ps)

	cicsectiontemplate = '"Perseus:abo:phi,0474,{w}:{p}:{s}"'

	newentry = cicsectiontemplate.format(w=thework, p=passage, s=section)
	#print('{a}\t{b}\t{c}'.format(a=newentry, b=passage, c=returntext))

	return newentry


def fixcicerochapters(entrytext: str, disabled=True) -> str:
	"""

	this sort of thing is not helpful

		<bibl "Perseus:abo:phi,0474,015:chapter=19" default="NO" valid="yes"><author>Cic.</author> Sull. 19 <hi rend="ital">fin.</hi></bibl>
		n="Perseus:abo:phi,0474,015:chapter=19"

	"chapter=NN" is only Cicero issue

	the example chosen sends you to Pro Sulla CHAPTER 19 to look for 'sententia',
	but that word appears in SECTIONS 55, 60, and 63...

	the code below will rewrite to give you a valid reference, but it will send you to the wrong place...

	CURRENTLY DISABLED

	RETAIN THE NOTES...

	:param entrytext:
	:return:
	"""

	if disabled:
		return entrytext

	findchapter = re.compile(r'"Perseus:abo:phi,0474,(...):chapter=(.*?)"')

	# x = re.findall(findchapter, entrytext)
	# if x:
	# 	print(x)

	newentry = re.sub(findchapter, r'"Perseus:abo:phi,0474,\1:\2" class="rewritten"', entrytext)

	return newentry


def fixfrontinus(entrytext: str) -> str:
	"""


	n="Perseus:abo:phi,1245,001:Aquaed. 104"

	but Aq. is 002

	:param entrytext:
	:return:
	"""

	findaquad = re.compile(r'"Perseus:abo:phi,1245,001:Aquaed\.(.*?)"')

	newentry = re.sub(findaquad, r'"Perseus:abo:phi,1245,002:\1" class="rewritten"', entrytext)

	return newentry


def fixmartial(entrytext: str) -> str:
	"""

	all of martial has been assigned to work 001

	:param entrytext:
	:return:
	"""

	findmartial = re.compile(r'"Perseus:abo:phi,1294,001:(.*?)"')
	findspectacles = re.compile(r'"Perseus:abo:phi,1294,002:(Spect. )(.*?)"')

	newentry = re.sub(findmartial, r'"Perseus:abo:phi,1294,002:\1" class="rewritten"', entrytext)
	newentry = re.sub(findspectacles, r'"Perseus:abo:phi,1294,001:\2"', newentry)

	return newentry


def fixnepos(entrytext: str) -> str:
	"""

	like many others the work is a string and not a number

		<bibl n="Perseus:abo:phi,0588,001:Arist. 1:4" default="NO" valid="yes"><author>Nep.</author> Arist. 1, 4</bibl>

	but there is another problem: crazy worknumbers

		<bibl n="Perseus:abo:phi,0588,021:2:2" default="NO" valid="yes"><author>Nep.</author> Reg. 2, 2</bibl>

	:param entrytext:
	:return:
	"""

	findnepos = re.compile(r'<bibl n="Perseus:abo:phi,0588,(...):(.*?)\s(.*?)"(.*?)><author>(.*?)</author>\s(.*?)\s(.*?)</bibl>')

	newentry = re.sub(findnepos, neposhelper, entrytext)

	return newentry


def neposhelper(regexmatch) -> str:
	"""

	use dict to substitute

	:param regexmatch:
	:return:
	"""

	returntext = regexmatch.group(0)
	work = regexmatch.group(1)
	life = regexmatch.group(2)
	pasg = regexmatch.group(3)
	tail = regexmatch.group(4)
	auth = regexmatch.group(5)
	wnam = regexmatch.group(6)
	wloc = regexmatch.group(7)

	nepostemplate = '<bibl n="Perseus:abo:phi,0588,{work}:{life}:{loc}" class="rewritten" {tail}><author>{au}</author> {wn} {ll}</bibl>'

	if work == '001':
		# the work is a string and not a number
		try:
			knownsubstitute = neposstrings[life]
		except KeyError:
			# print('unk nepos: "{w}"'.format(w=work))
			return returntext
	else:
		# crazy worknumbers
		# this also means you need to adjust the way '{life}:{loc}' looks too by adding the life name up front: 'Att:...'
		try:
			knownsubstitute = neposnumbers[work]
		except KeyError:
			# print('unk neposnumber: "{w}"\t{wn}'.format(w=work, wn=wnam))
			return returntext
		knownsubstitute = '{ks}:{v}'.format(ks=knownsubstitute, v=life)

	newentry = nepostemplate.format(work='001', life=knownsubstitute, loc=pasg, tail=tail, au=auth, wn=wnam, ll=wloc)

	# if work != '001':
	# 	print(newentry)

	return newentry


def fixpropertius(entrytext: str) -> str:
	"""

	<bibl n="Perseus:abo:phi,1224,001:1:8:29" default="NO"><author>Prop.</author> 1, 8, 29</bibl>

	but propertius is lt0620

	:param entrytext:
	:return:
	"""

	findprop = re.compile(r'("Perseus:abo:phi),1224,(.*?" default="NO")(><author>Prop\.</author>)')

	newentry = re.sub(findprop, r'\1,0620,\2 class="rewritten"\3', entrytext)

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

	sallusttemplate = '"Perseus:abo:phi,0631,{wk}:{loc}" class="rewritten"'

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

	senecatemplate = '"Perseus:abo:phi,{au},{wk}{loc}" class="rewritten"'

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

	suetoniustemplate = '"Perseus:abo:phi,1348,001:{wk}{loc}" class="rewritten"'

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

	finddll = re.compile(r'"(Perseus:abo:phi,0684,001:)(L. L. )(.*?):(section=)(.*?)"')
	findrr = re.compile(r'"(Perseus:abo:phi,0684,)(001):(R. R. )(.*?)"')
	findmenn = re.compile(r'"(Perseus:abo:phi,0684,001:Sat. Menip\. )(.*?)"')

	newentry = re.sub(finddll, r'"\1\3:\5" class="rewritten"', entrytext)
	newentry = re.sub(findrr, r'"Perseus:abo:phi,0684,002:\4" class="rewritten"', newentry)
	newentry = re.sub(findmenn, r'"Perseus:abo:phi,0684,011:\2" class="rewritten"', newentry)

	return newentry


x = """
<head extent="full" lang="greek" opt="n" orth_orig="αἰθήρ">αἰθήρ</head>, <itype lang="greek" opt="n">έροϲ</itype>, in <author>Hom.</author> always ἡ; in <author>Hes.</author> and <gramGrp opt="n"><gram type="dialect" opt="n">Att.</gram></gramGrp> Prose always ὁ; in Lyr. and Trag. mostly <gen lang="greek" opt="n">ὁ</gen>, as always in <author>A.</author>, but <gen lang="greek" opt="n">ἡ</gen> <bibl n="Perseus:abo:tlg,0033,001:1:6" default="NO" valid="yes"><author>Pi.</author> <title>O.</title> 1.6</bibl>, <bibl n="Perseus:abo:tlg,0199,001:8:35" default="NO" valid="yes"><author>B.</author> 8.35</bibl>, <bibl n="Perseus:abo:tlg,0011,004:867" default="NO" valid="yes"><author>S.</author> <title>OT</title> 867</bibl>, and freq. in <author>E.</author>: (<etym lang="greek" opt="n">αἴθω</etym>):—in <author>Hom.</author>, <sense id="n2324.0" n="A" level="1" opt="n"><trans>ether</trans>, the heaven</trans> (wrongly distinguished by <author>Aristarch.</author> from ἀήρ (q.v.) as <trans>upper</trans> from lower <trans>air</trans>); <cit><quote lang="greek">διʼ ἠέροϲ αἰθέρʼ ἵκανεν</quote> <bibl n="Perseus:abo:tlg,0012,001:14:288" default="NO" valid="yes"><title>Il.</title> 14.288</bibl></cit>; [<cit><quote lang="greek">Ζεὺϲ] αἰθέρι ναίων</quote> <bibl n="Perseus:abo:tlg,0012,001:2:412" default="NO" valid="yes">2.412</bibl></cit>, <bibl n="Perseus:abo:tlg,0020,002:18" default="NO" valid="yes"><author>Hes.</author> <title>Op.</title> 18</bibl>; <cit><quote lang="greek">νόμοι διʼ αἰθέρα τεκνωθέντεϲ</quote> <bibl n="Perseus:abo:tlg,0011,004:867" default="NO" valid="yes"><author>S.</author> <title>OT</title> 867</bibl></cit>; <cit><quote lang="greek">αἰθὴρ μὲν ψυχὰϲ ὑπεδέξατο ϲώματα δὲ χθών</quote> <title>IG</title> 1.442</cit>, cf. <bibl n="Perseus:abo:tlg,0006,041:533" default="NO" valid="yes"><author>E.</author> <title>Supp.</title> 533</bibl>; of the <trans>sky</trans>, both cloudless, <cit><quote lang="greek">νήνεμοϲ αἰ.</quote> <bibl n="Perseus:abo:tlg,0012,001:8:556" default="NO" valid="yes"><title>Il.</title> 8.556</bibl></cit>, and clouded, <cit><quote lang="greek">ἐν αἰθέρι καὶ νεφέλῃϲι</quote> <bibl n="Perseus:abo:tlg,0012,001:15:192" default="NO" valid="yes">15.192</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0012,001:16:365" default="NO" valid="yes">16.365</bibl>; freq. in Trag., etc., <bibl n="Perseus:abo:tlg,0085,003:1044" default="NO" valid="yes"><author>A.</author> <title>Pr.</title> 1044</bibl>, <bibl n="Perseus:abo:tlg,0085,003:1088" default="NO" valid="yes">1088</bibl>, <bibl n="Perseus:abo:tlg,0085,002:365" default="NO" valid="yes"><title>Pers.</title> 365</bibl>, <bibl n="Perseus:abo:tlg,0006,050:150" default="NO" valid="yes"><author>E.</author> <title>Ba.</title> 150</bibl>; αἰ. ζοφερόϲ, ἀχλυόειϲ, <bibl n="Perseus:abo:tlg,0001,001:3:1265" default="NO" valid="yes"><author>A.R.</author> 3.1265</bibl>, <bibl n="Perseus:abo:tlg,0001,001:4:927" default="NO" valid="yes">4.927</bibl>; of the fumes of the Cyclops’ mouth, <bibl n="Perseus:abo:tlg,0006,001:410" default="NO" valid="yes"><author>E.</author> <title>Cyc.</title> 410</bibl>. </sense><sense n="2" id="n2324.1" level="3" opt="n"> <trans>air</trans>, <bibl n="Perseus:abo:tlg,1342,001:100:5" default="NO"><author>Emp.</author> 100.5</bibl>. </sense><sense n="3" id="n2324.2" level="3" opt="n"> fifth element, <bibl n="Perseus:abo:tlg,0059,035:981c" default="NO" valid="yes"><author>Pl.</author> <title>Epin.</title> 981c</bibl>, <bibl n="Perseus:abo:tlg,0059,035:984b" default="NO" valid="yes">984b</bibl>, <bibl n="Perseus:abo:tlg,0086,005:270b:22" default="NO"><author>Arist.</author> <title>Cael.</title> 270b22</bibl>; but equivalent to πῦρ, <author>Anaxag.</author> 1,15. </sense><sense n="b" id="n2324.3" level="4" opt="n"> = πῦρ τεχνικόν, <bibl n="Perseus:abo:tlg,1264,001:2:168" default="NO"><author>Chrysipp.Stoic.</author> 2.168</bibl>, cf. <bibl n="Perseus:abo:tlg,0086,028:392a:5" default="NO"><author>Arist.</author> <title>Mu.</title> 392a5</bibl>. </sense><sense n="4" id="n2324.4" level="3" opt="n"> the divine element in the human soul, <bibl n="Perseus:abo:tlg,0638,001:3:34" default="NO"><author>Philostr.</author> <title>VA</title> 3.34</bibl>, cf. <bibl n="Perseus:abo:tlg,0638,001:42" default="NO">42</bibl>. </sense><sense n="II" id="n2324.5" level="2" opt="n"> <trans>clime, region</trans>, <bibl n="Perseus:abo:tlg,0006,002:594" default="NO" valid="yes"><author>E.</author> <title>Alc.</title> 594</bibl> (lyr.).</sense>
"""
y = """
<head extent="full" lang="greek" opt="n" orth_orig="γνωρ-ίζω">γνωρίζω</head>, <tns opt="n">fut.</tns><gramGrp opt="n"><gram type="dialect" opt="n">Att.</gram></gramGrp><foreign lang="greek">-ῐῶ</foreign>: <tns opt="n">pf.</tns> <cit><quote lang="greek">ἐγνώρικα</quote> <bibl n="Perseus:abo:tlg,0059,012:262b" default="NO" valid="yes"><author>Pl.</author> <title>Phdr.</title> 262b</bibl></cit>:—<sense id="n22522.0" n="Α" level="1" opt="n"><trans>make known, point out</trans>, <bibl n="Perseus:abo:tlg,0085,003:487" default="NO" valid="yes"><author>A.</author> <title>Pr.</title> 487</bibl>, <bibl n="Perseus:abo:tlg,0527,011:10:8" default="NO" valid="yes"><author>LXX</author> <title>1 Ki.</title> 10.8</bibl>, al., <bibl n="Perseus:abo:tlg,0031,006:0:22" default="NO" valid="yes"><title>Ep.Rom.</title> 0.22</bibl>:—in this sense mostly <gramGrp opt="n"><gram type="voice" opt="n">Pass.</gram></gramGrp>, <trans>become known</trans>, <bibl n="Perseus:abo:tlg,0059,030:428a" default="NO" valid="yes"><author>Pl.</author> <title>R.</title> 428a</bibl>, <bibl n="Perseus:abo:tlg,0086,001:64b:35" default="NO"><author>Arist.</author> <title>APr.</title> 64b35</bibl>; <cit><quote lang="greek">τὰ γνωριζόμενα μέρη τῆϲ οἰκουμένηϲ</quote> <bibl n="Perseus:abo:tlg,0543,001:2:37:4" default="NO" valid="yes"><author>Plb.</author> 2.37.4</bibl></cit>. </sense><sense n="2" id="n22522.1" level="3" opt="n"> c. acc. pers., <trans>make known</trans>, <cit><quote lang="greek">τινά τινι</quote> <bibl n="Perseus:abo:tlg,0007,013:21" default="NO"><author>Plu.</author> <title>Fab.</title> 21</bibl></cit>; <trans>commend</trans>, <cit><quote lang="greek">τινὰ τῇ βουλῇ ἰϲχυρῶϲ</quote> <bibl n="Perseus:abo:tlg,0551,011:9:6" default="NO" valid="yes"><author>App.</author> <title>Mac.</title> 9.6</bibl></cit>. </sense><sense n="3" id="n22522.2" level="3" opt="n"> <trans>certify</trans> a personʼs <trans>identity</trans>, <bibl n="Perseus:abo:pap,BGU:581:13" default="NO"><title>BGU</title> 581.13</bibl> <date>(ii A. D.)</date>, <bibl n="Perseus:abo:pap,P.Oxy.:1024:18" default="NO"><title>POxy.</title> 1024.18</bibl> <date>(ii A. D.)</date>. </sense><sense n="II" id="n22522.3" level="2" opt="n"> <trans>gain knowledge of, become acquainted with, discover</trans>, c. <mood opt="n">part.</mood>, <cit><quote lang="greek">τοὔργον ὡϲ οὐ γνωριοῖμί ϲου τόδε δόλῳ προϲέρπον</quote> <bibl n="Perseus:abo:tlg,0011,004:538" default="NO" valid="yes"><author>S.</author> <title>OT</title> 538</bibl></cit>; <cit><quote lang="greek">τὰ καλὰ γ. οἱ εὐφυέεϲ πρὸϲ αὐτά</quote> <bibl n="Perseus:abo:tlg,0161,001:56" default="NO"><author>Democr.</author> 56</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0006,002:564" default="NO" valid="yes"><author>E.</author> <title>Alc.</title> 564</bibl>, <bibl n="Perseus:abo:tlg,0003,001:7:44" default="NO" valid="yes"><author>Th.</author> 7.44</bibl>, <bibl n="Perseus:abo:tlg,0086,031:184a:12" default="NO"><author>Arist.</author> <title>Ph.</title> 184a12</bibl>:—<gramGrp opt="n"><gram type="voice" opt="n">Pass.</gram></gramGrp>, <bibl n="Perseus:abo:tlg,0003,001:5:103" default="NO" valid="yes"><author>Th.</author> 5.103</bibl>, <bibl n="Perseus:abo:tlg,0541,001:72" default="NO"><author>Men.</author> 72</bibl>; <foreign lang="greek">γ. περί τι</foreign> or <cit><quote lang="greek">περί τινοϲ</quote> <bibl n="Perseus:abo:tlg,0086,025:1005b:8" default="NO" valid="yes"><author>Arist.</author> <title>Metaph.</title> 1005b8</bibl></cit>, <bibl n="Perseus:abo:tlg,0086,025:1037a:16" default="NO" valid="yes">1037a16</bibl>. </sense><sense n="2" id="n22522.4" level="3" opt="n"> <trans>become acquainted with</trans>, <cit><quote lang="greek">τινά</quote> <bibl n="Perseus:abo:tlg,0059,019:181c" default="NO" valid="yes"><author>Pl.</author> <title>La.</title> 181c</bibl></cit>, <bibl n="Perseus:abo:tlg,0014,035:6" default="NO" valid="yes"><author>D.</author> 35.6</bibl>; <cit><quote lang="greek">τινὰϲ ὁποῖοί τινέϲ εἰϲι</quote> <bibl n="Perseus:abo:tlg,0010,013:28" default="NO" valid="yes"><author>Isoc.</author> 2.28</bibl></cit>:— <gramGrp opt="n"><gram type="voice" opt="n">Pass.</gram></gramGrp>, <foreign lang="greek">ἐγνωριϲμένοι αὐτῷ</foreign> <trans rewritten="phrase">being made acquainted with him</trans>, <trans rewritten="phrase">ibid.; <cit><quote lang="greek">πρόϲ τινοϲ</quote></trans><bibl n="Perseus:abo:tlg,0062,022:5" default="NO"><author>Luc.</author> <title>Tim.</title> 5</bibl></cit>.</sense>
(1 row)
"""

# perseusworkmappingfixer(y)

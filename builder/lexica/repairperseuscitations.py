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

					# if not hit:
					# 	quote = originalquote
					# 	quote = shinkquote(quote, direction='forward')
					# 	while quote and not hit:
					# 		trialnumber += 1
					# 		hit = lookforquote(adb, wkid, quote, querytemplate, dbcursor)
					# 		if not hit:
					# 			quote = shinkquote(quote, direction='forward')

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


def oneofflatinworkremapping(entrytext: str) -> str:
	"""

	hand off some oddballs

	:param entrytext:
	:return:
	"""

	fixentry = fixmartial(entrytext)

	return fixentry


def fixmartial(entrytext: str) -> str:
	"""

	all of martial has been assigned to work 001

	:param entrytext:
	:return:
	"""

	findmartial = re.compile(r'"Perseus:abo:phi,1294,001:')
	findspectacles = re.compile(r'"Perseus:abo:phi,1294,002:(Spect. )(.*?)"')

	newentry = re.sub(findmartial, r'"Perseus:abo:phi,1294,002:', entrytext)
	newentry = re.sub(findspectacles, r'"Perseus:abo:phi,1294,001:\2"', newentry)

	return newentry



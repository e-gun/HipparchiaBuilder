# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from builder.parsers.swappers import avoidregexsafevariants


def convertdate(date, passvalue=0):
	"""

	there are 21915 distinct recorded_date values in the works table
	[q = 'select distinct recorded_date from works order by recorded_date']

	take a string date and try to assign a number to it: IV AD --> 450, etc.

	a very messy way to achieve highly suspect results

	this is IN PROGRESS and likely to remain so for a good while longer

	:param date:
	:return:
	"""
	original = date

	# "Editor's date:  33⟨8⟩/7" --> '33' unless you purge the brackets
	date = re.sub(r'[⟨⟩]', '', date)
	date = avoidregexsafevariants(date)
	numericaldate = 9999

	german = re.compile(r'(n\.|v\.Chr\.)')
	arabic = re.compile(r'\d')
	ordinal = re.compile(r'((\d)st|(\d)nd|(\d)rd|(\d+)th)')
	roman = re.compile(r'[IVX]')
	ages = re.compile(r'aet')

	if re.search(german, date) is not None and passvalue == 0:
		numericaldate = germandate(date)
	elif re.search(arabic, date) is not None and re.search(ordinal, date) is not None and passvalue < 2:
		numericaldate = numberedcenturydate(date, ordinal)
	elif re.search(ages, date) is not None and passvalue < 3:
		numericaldate = aetatesdates(date)
	elif re.search(roman, date) is not None and passvalue < 4:
		numericaldate = romannumeraldate(date)
	elif re.search(arabic, date) is not None and passvalue < 5:
		numericaldate = numericdate(date)

	if numericaldate != 9999:
		if numericaldate == 0:
			numericaldate = 1
		if numericaldate is None:
			numericaldate = 9999

		numericaldate = round(int(numericaldate), 1)
		return numericaldate

	# if we have not returned yet, then only a grab bag should remain: 'späthellenistisch', etc.
	# and so we pass through the old convertdate() code in a desperate last attempt

	numericaldate = datemapper(date)

	# failed all of the tests, right?
	# print(original)

	return numericaldate


def germandate(stringdate):
	"""

	a very large percentage of the German dates will pass through this with OK results

	:param stringdate:
	:return:
	"""

	original = stringdate

	dontcare = re.compile(r'^(Frühjahr |wohl des |wohl noch |wohl |vielleicht noch |vermutlich |etwa |Mitte |frühestens |um |des |ca\. |ca\.|noch |nicht später als |nicht vor |nicht früher als |Wende des |Wende |2\.Drittel )')
	subtract = re.compile(r'^(spätestens 1\.Hälfte |spätestens |am ehesten |nicht später als |kaum später als |term\.ante |1\.Hälfte |1\.Halfte |1\.Drittel |1. Viertel |1\.Viertel |Beginn |\(frühes\) |frühes |fruhes |erste Jahrzehnte |Anfang |Anf\. |Anf |Anf\.|1. H. )')
	tinysubtract = re.compile(r'^(einige Zeit vor |\(kurz\) vor |kurz vor |vor |2. Viertel |2.Viertel )')
	add = re.compile(r'^(nicht früher als |term\.post |nach |letztes Drittel |letztes Viertel |3\. Viertel |3\.Viertel |4. Viertel |2\. Hälfte |2\.Hälfte |2 Hälfte |2\.Hālfte |spätes |ausgehendes |später als |späteres |\(Ende\) |Ende )')
	century = re.compile(r'(Jh\. |Jh\.| Jhdts\. |Jhdt\. )')
	split = re.compile(r'(\d+)[-/](\d+)')
	misleadingmiddles = re.compile(r'(-ca\.|-vor )')
	oder = re.compile(r'(\d+)( od | oder )(\d+)')

	modifier = 1
	midcentury = -50
	fudge = 0

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(misleadingmiddles, '-', stringdate)
	# stringdate = re.sub(collapse,'/', stringdate)

	if re.search(r'v\.Chr\.', stringdate) is not None and re.search(r'n\.Chr\.', stringdate) is not None:
		parts = re.search(r'\d\s?v\.Chr(.*?)\d\s?n\.Chr(.*?)', stringdate)
		try:
			one = int(parts.group(1))
			two = int(parts.group(3))
			numericaldate = ((-1 * one * 100) + (two * 100)) / 2
		except:
			numericaldate = 9999
		return numericaldate
	elif re.search(r'zw.', stringdate) is not None:
		parts = re.search(r'^zw.(\d+)\s?und(\d+)', stringdate)
		if re.search(r'v\.Chr\.', stringdate) is not None:
			modifier = -1
			fudge += 100
		try:
			one = int(parts.group(1))
			two = int(parts.group(2))
			numericaldate = (((-1 * one) + (two)) / 2) * modifier + fudge
		except:
			# AttributeError: 'NoneType' object has no attribute 'group'
			# failed zw. 1 v.Chr. und 4 n.Chr.
			numericaldate = convertdate(original, passvalue=1)
		return numericaldate
	elif re.search(r'v\.Chr\.', stringdate) is not None:
		modifier = -1

	stringdate = re.sub(r'(v\.|n\.)Chr\.', '', stringdate)

	if re.search(subtract, stringdate) is not None:
		stringdate = re.sub(subtract, '', stringdate)
		fudge = -25

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract, '', stringdate)
		fudge = -10

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add, '', stringdate)
		fudge = 25

	if re.search(century, stringdate) is not None:
		stringdate = re.sub(century, '', stringdate)
		modifier = modifier * 100

	re.sub(r'(^\s|\s$)', '', stringdate)

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\.', '', stringdate)

	if re.search(split, stringdate) is not None:
		parts = re.search(split, stringdate)
		one = int(parts.group(1))
		two = int(parts.group(2))
		if modifier < 100:
			numericaldate = ((one + two) / 2) * modifier
		else:
			numericaldate = (((one + two) / 2) * modifier) + fudge
		return numericaldate

	if re.search(oder, stringdate) is not None:
		parts = re.search(oder, stringdate)
		one = int(parts.group(1))
		two = int(parts.group(3))
		if modifier < 100:
			numericaldate = ((one + two) / 2) * modifier
		else:
			numericaldate = (((one + two) / 2) * modifier) + fudge + midcentury
		return numericaldate

	try:
		if abs(modifier) != 1:  # i.e., = 100 or -100
			numericaldate = int(stringdate) * modifier + fudge + midcentury
		else:
			numericaldate = int(stringdate) * modifier + fudge
	except:
		numericaldate = convertdate(original, passvalue=1)

	return numericaldate


def numberedcenturydate(stringdate, ordinalregexfinder):
	"""

	try to parse a date that has something like '5th' in it

	ordinal = re.compile(r'((\d)st|(\d)nd|(\d)rd|(\d+)th)')

	:param stringdate:
	:return:
	"""

	original = stringdate
	modifier = 100
	midcentury = -50
	fudge = 0

	dontcare = re.compile(r'^(prob\. |perh\. |c |c\.|c. |mid-|)|( and later|\?, or later| or later)$')
	subtract = re.compile(r'^(not before |before )')
	tinysubtract = re.compile(r'^(beg\. |beg\.|beg |earlier |early |in |sh\. bef\. mid\. |b:mid- )')
	tinyadd = re.compile(r'^(end |later |late |ex |sh\. aft\. mid\. )')
	add = re.compile(r' or later$')
	eb = re.compile(r'^end (.*?)[/-]beg(\.|) (.*?)')
	embedded = re.compile(r'(\(.*?\d+.*?[ab]c\))')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(eb, r'\1/\3', stringdate)

	if re.search(embedded, stringdate) is not None:
		e = re.search(embedded, stringdate)
		numericaldate = numericdate(e.group(0))
		return numericaldate

	if re.search(subtract, stringdate) is not None:
		stringdate = re.sub(subtract, '', stringdate)
		fudge = -75

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract, '', stringdate)
		fudge = -25

	if re.search(tinyadd, stringdate) is not None:
		stringdate = re.sub(tinyadd, '', stringdate)
		fudge = 25

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add, '', stringdate)
		# note that 75 was not chosen because the candidate did not look right for it
		fudge = 25

	if re.search(r'bc$', stringdate) is not None:
		modifier = modifier * -1
		fudge = fudge + 100
	elif re.search(r'ac$', stringdate) is None and re.search(r'(1st|2nd) half', stringdate) is not None:
		# 2nd half Antonine
		numericaldate = convertdate(original, passvalue=2)
		return numericaldate

	digitfinder = re.findall(ordinalregexfinder, stringdate)
	# [('8th', '', '', '', '8'), ('9th', '', '', '', '9')]

	try:
		seconddigit = [x for x in digitfinder[1][1:] if x]
		seconddigit = int(seconddigit[0])
		twodigit = True
	except:
		twodigit = False

	firstdigit = [x for x in digitfinder[0][1:] if x]
	firstdigit = int(firstdigit[0])

	if twodigit:
		if re.search(r'bc(.*?)ac$', stringdate) is None:
			numericaldate = (((firstdigit + seconddigit) / 2) * modifier) + fudge
			if modifier > 0:
				numericaldate += 50
			else:
				numericaldate -= 50
		else:
			numericaldate = (((firstdigit * -100) + (seconddigit * 100))/2)
	else:
		numericaldate = (firstdigit * modifier) + fudge + midcentury

	if numericaldate == 0:
		numericaldate = 1

	return numericaldate


def aetatesdates(stringdate):
	"""

	aet. Aug -> 10

	:param stringdate:
	:return:
	"""

	original = stringdate
	fudge = 0

	datemapper = {
		'Ant': 150,
		'August fere': 1,
		'Ant/Aur': 160,
		'Ant. Pius': 150,
		'Antoninus Pius': 150,
		'Antonine': 150,
		'Ant. Pius & M. Aur.': 160,
		'Aur': 170,
		'Aur/Carac': 200,
		'Aur/Commod': 160,
		'Carac': 205,
		'Chr': 400,
		'Claud': 50,
		'Claudius': 50,
		'Aug/Claud': 30,
		'Aug/Tib': 10,
		'Claud/Nero': 55,
		'Commod': 185,
		'Dioc': 290,
		'Dom': 90,
		'Flav': 85,
		'Had': 125,
		'Hadriani': 125,
		'Had/Aur': 150,
		'Had/Ant': 155,
		'Hell tard': -1,
		'Hell': -250,
		'Imp tard': 400,
		'imp': 200,
		'Imp': 200,
		'inferior': 1200,
		'Nero': 60,
		'Nerv': 97,
		'Nerv/Tra': 100,
		'TráHad': 115,
		'Rom tard': 250,
		'Rom': 50,
		'tard': 1000,
		'Tib': 25,
		'Tib/Gaii': 35,
		'Gaii': 40,
		'Calig': 40,
		'Tit': 80,
		'Tra': 105,
		'Tra/Had': 115,
		'Ves': 70,
		'Ves/Dom': 80,
		'Augusti': 1,
		'Lycurgi': -350,
		'Macedon': -275,
		'Aug': 1,
		'Rom/Byz': 400,
		'Byz': 700,
		'Byzant': 700,
		'Byzantina': 700,
		'Just': 550,
		'Hell.': -250,
		'Hellen': -250,
		'Hellenistic': -250,
		'Hellenist': -250,
		'Severianae': 210,
		'fin Tib': 35,
		'fin Aug': 10,
		'fin Claud': 50,
		'fin Dom': 95,
		'fin Hell': -1,
		'fin Nero': 65,
		'fin Rom': 325,
		'fin Tra': 115,
		'incert': 2500,
		'init Ant': 155,
		'init Aug': -15,
		'init Byz': 450,
		'init Chr': 350,
		'init Had': 120,
		'init Hell': -250,
		'init Rom': -50,
		'init imp': 50,
		'init imper': 50,
		'med Hell': -150,
	}

	add = re.compile(r'^(p |post )')
	subtr = re.compile(r'^a |^ante ')
	kill = re.compile(r'(\[.*?\]|^c |/p post)')

	stringdate = re.sub(r'(aetate |aetats |aetat |aet )', '', stringdate)
	stringdate = re.sub(kill, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(r'(^\s|\s$)', '', stringdate)

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add, '', stringdate)
		fudge = 25

	if re.search(subtr, stringdate) is not None:
		stringdate = re.sub(subtr, '', stringdate)
		fudge = -25

	try:
		numericaldate = datemapper[stringdate] + fudge
	except:
		numericaldate = convertdate(original, passvalue=3)

	return numericaldate


def romannumeraldate(stringdate):
	"""

	V -> 450

	:param stringdate:
	:return:
	"""

	datemapper = { 'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11,
			'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19}

	original = stringdate
	modifier = 100
	midcentury = -50
	fudge = 0
	numericaldate = 9999

	falsepositive = re.compile(r'(Imp|\d|aet )')
	fixone = re.compile(r'Í')
	fixtwo = re.compile(r'á')

	if re.search(falsepositive, stringdate) is not None:
		numericaldate = convertdate(original, passvalue=4)
		return numericaldate

	stringdate = re.sub(fixone, r'I/', stringdate)
	stringdate = re.sub(fixtwo, r'a/', stringdate)

	dontcare = re.compile(r'^(p med |s |p |c.med s |c med |med s |mid- |mid |fere s )|( ut vid| p|p\?|p)$')
	fi = re.compile(r'^fin (.*?)/init (.*?)')
	# subtract = re.compile()
	tinysubtract = re.compile(r'(^(ante med |ante md |beg\. |beg |a med |early |init/med |init |latest )| p prior$)')
	bigadd = re.compile(r'^(post fin s|post )')
	add = re.compile(r'(^(ante fin |ant fin|ex s |ex |end |med/fin |late |post med s )|(/postea|/paullo post)$)')
	splitter = re.compile(r'([IVX]+)[-/]([IVX]+)')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(fi, r'\1/\2', stringdate)

	stringdate = re.sub(r'\?', '', stringdate)

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract, '', stringdate)
		fudge = -25

	if re.search(r'/init ', stringdate) is not None:
		stringdate = re.sub(tinysubtract, '/', stringdate)
		fudge = -25

	if re.search(bigadd, stringdate) is not None:
		stringdate = re.sub(bigadd, '', stringdate)
		fudge = 75

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add, '', stringdate)
		fudge = 25

	if re.search(r'( bc$|bc$| a$|a$)', stringdate) is not None:
		stringdate = re.sub(r'( bc| BC|bc| sac| ac| a|a)$', '', stringdate)
		modifier = modifier * -1
		fudge = fudge + 100

	if re.search(r'(ac.*?[/-].*?pc|bc.*?[/-].*?ac)$', original) is not None:
		# I sac - I spc
		numerals = re.findall(r'[IVX]+', original)
		digits = [datemapper[n] for n in numerals]
		digits[0] = digits[0] * -1
		numericaldate = (((digits[0] + digits[1]) / 2) * modifier) + fudge
	elif re.search(splitter, stringdate) is not None:
		# II-III spc
		centuries = re.search(splitter, stringdate)
		first = centuries.group(1)
		second = centuries.group(2)
		first = datemapper[first]
		second = datemapper[second]
		if first > second and modifier > 0:
			modifier = modifier * -1
		numericaldate = (((first + second) / 2) * modifier) + fudge + midcentury
	elif re.search(r'[IVX]+', stringdate) is not None:
		numeral = re.search(r'[IVX]+', stringdate)
		try:
			numeral = datemapper[numeral.group(0)]
			numericaldate = (numeral * modifier) + fudge + midcentury
		except:
			# no key
			numericaldate = convertdate(original, passvalue=4)

	if numericaldate == 0:
		numericaldate = 1

	if numericaldate == 9999:
		numericaldate = convertdate(original, passvalue=4)

	return numericaldate


def numericdate(stringdate):
	"""

	post 398/7 -> -390

	DANGER:
		'ac' vs 'a'
		[c.950-978 ac] IS CE
		p c 480-c 450a is BCE

	:param stringdate:
	:return:
	"""

	original = stringdate
	modifier = 1
	fudge = 0
	numericaldate = 9999

	dontcare = re.compile(r'^(p c |p c\.|p |perh c |poss\. |prob\. c\.|prob\. |cAD |AD |c\. |c\.|c )')
	# subtract = re.compile()
	tinysubtract = re.compile(r'^(sh\. bef\. |sh\.bef\. |before |bef\. )')
	littleadd = re.compile(r'^(sh\. aft\. c\.|sh\. aft\. |sh\.aft\. |sh\.aft\.|sht\. after )')
	# add = re.compile(r'')
	splitter = re.compile(r'(\d+)[/-](\d+)')
	bcad = re.compile(r'(\d+) BC-AD (\d+)')
	nearestdecade = re.compile(r'^(post |ante )')
	fix = re.compile(r'⟪⟫\[\]')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(fix, '', stringdate)

	if re.search(r'( bc$|bc$| BC$| a$|a$)', stringdate) is not None:
		modifier = -1

	if re.search(bcad, stringdate) is not None:
		digits = re.search(bcad, stringdate)
		one = int(digits.group(1))* -1
		two = int(digits.group(2))* 1
		numericaldate = (one + two ) / 2
		return numericaldate

	if re.search(splitter, stringdate) is not None:
		digits = re.findall(splitter, stringdate)
		try:
			one = int(digits[0][0])
			two = int(digits[0][1])
			if len(str(one)) != len(str(two)):
				newtwo = ''
				strone = str(one)
				strtwo = str(two)
				for i in range(0, len(strone) - len(strtwo)):
					newtwo += strone[i]
				newtwo += strtwo
				two = int(newtwo)
			numericaldate = (one + two) / 2 * modifier
			return numericaldate
		except:
			# 'AD 199/III spc'
			try:
				one = int(digits[0][0])
				numericaldate = one * modifier
			except:
				print('repass', digits[0][0])
				numericaldate = convertdate(digits[0][0], passvalue=4)

	if re.search(nearestdecade, stringdate) is not None:
		digits = re.search(r'\d+', stringdate)
		year = int(digits.group(0))
		decade = year % 10
		if ('post' in stringdate and modifier == 1) or ('ante' in stringdate and modifier == -1):
			numericaldate = (year + (10 - decade))
		elif ('post' in stringdate and modifier == -1) or ('ante' in stringdate and modifier == 1):
			numericaldate = year - decade
		return numericaldate

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract, '', stringdate)
		fudge = -10

	if re.search(littleadd, stringdate) is not None:
		stringdate = re.sub(littleadd, '', stringdate)
		fudge = 10

	digits = re.search(r'\d+', stringdate)
	year = int(digits.group(0))
	numericaldate = (year * modifier) + fudge

	return numericaldate


def datemapper(stringdate):
	"""

	calculations have failed, just try to grab the string from a list

	:param stringdate:
	:return:
	"""

	original = stringdate
	numericaldate = 9999

	mapper = {
		'1. HÄLFTE 2. JH. V.CHR.': -175,
		'1. HÄLFTE 4. JH. V.CHR.': -375,
		'1. HÄLFTE 4.JH. V.CHR.': -375,
		'ADV. IMP.': 400,
		'AET CHRIST': 400,
		'AET HELL TARD': -1,
		'AET HELL': -250,
		'AET IMP ROM': 200,
		'AET IMP TARD': 400,
		'AET IMP': 200,
		'AET INFERIOR': 1200,
		'AET ROM REC': 300,
		'AET ROM REC/INIT AET BYZ': 350,
		'AET ROM TARD/MEDIEV': 700,
		'ANTONINE': 150,
		'ARCHAIC': -700,
		'ARCHAIC/CLASSICAL': -600,
		'AUGUST': 1,
		'AUGUSTAN': 1,
		'AUGUSTUS': 1,
		'AUGUSTUS/TIBERIUS': 10,
		'AUGUSTUS-TIBERIUS': 10,
		'BYZ.': 700,
		'BYZ': 700,
		'BYZANTINE': 700,
		'BYZANTINISCH': 700,
		'BYZANTISCH': 700,
		'BYZANTINISCHE ZEIT': 700,
		'CAROLINGIAN': 775,
		'CHR': 400,
		'CHR.': 400,
		'CHRIST.': 400,
		'CHRISTL.': 400,
		'CHRISTLICH': 400,
		'CHRISTIAN': 400,
		'CLASSICAL': -425,
		'CLAUDIUS': 50,
		'COMMODUS': 185,
		'CONSTANTINE': 315,
		'DATE': 2500,
		'DOMITIAN': 90,
		'EARLY BYZ.': 450,
		'EARLY BYZANTINE': 450,
		'EARLY CHR.': 350,
		'EARLY CHR': 200,
		'EARLY HELL.': -300,
		'BEG. IMP.': 25,
		'EARLY IMP.': 25,
		'EARLY IMP': 25,
		'EARLY PTOL.': -275,
		'EARLY ROM.': -50,
		'EARLY ROMAN': -50,
		'EARLY-MID. IMP.': 100,
		'EARLY-MIDDLE IMP.': 100,
		'EARLÝMID. IMP.': 100,
		'END 4TH-BEG. 3RD BC': 300,
		'END TRAJAN': 110,
		'FIN AET HELL/IMP': 1,
		'FIN AET HELL/INIT AET IMP': 1,
		'FLAVISCH': 85,
		'FLAVIAN': 85,
		'FRÜHE KAISERZEIT (AUGUSTUS)': 1,
		'FRÜHE KAISERZEIT': 25,
		'FRU+HHELLENISTISCH': -300,
		'FRÜHE RÖMISCHE ZEIT': -50,
		'FRÜHELLENISTISCH': -300,
		'HADRIAN': 125,
		'HADRIANIC-EARLY ANTONINE': 140,
		'HADRIANIC': 125,
		'HADRIANISCH': 125,
		'HADRIANISCHE ZEIT': 125,
		'HELL.-ROM.': -50,
		'HELL.': -250,
		'HELL./FRÜHE KAISERZEIT': -1,
		'HELL./ROM.': -50,
		'HELLENISTIC': -250,
		'HELLENISTISCH': -250,
		'HELLENISTISCHE ZEIT': -250,
		'IA-C 50P': 1,
		'IMP.': 200,
		'IMP': 200,
		'IMPERIAL': 200,
		'INIT AET IMP': 25,
		'IÁAET IMP': 110,
		'JULIO-CLAUDIAN': 25,
		'KAISERZEIT': 100,
		'KAISERZEITLICH': 100,
		'LATE ARCHAIC': -600,
		'LATE BYZ.': 1200,
		'LATE BYZ': 1200,
		'LATE BYZANTINE': 1200,
		'LATE CLASS.': -415,
		'LATE CLASS.-HELL.': -375,
		'LATE HADRIANIC': 135,
		'LATE HADRIANIC OR AFTER': 145,
		'LATE HADRIANIC OR LATER': 145,
		'LATE HADRIANIC-ANTONINE': 155,
		'LATE HELL.-EARLY IMP.': -15,
		'LATE HELL.': -1,
		'LATE HELL./EARLY ROM.': -1,
		'LATE HELL./ROM.': -1,
		'LATE HELL': -1,
		'LATE HELLEN': -1,
		'LATE HELLENIST.': -1,
		'LATE IMP.': 300,
		'LATE IMP': 300,
		'LATE IMPERIAL': 300,
		'LATE PTOL.': -50,
		'LATER IMP.': 300,
		'FIN AET IMP': 300,
		'LETZTES VIERTEL 1. JH.V.CHR.': -15,
		'MARCUS AURELIUS': 170,
		'MED.': 1100,
		'MEROV.': 600,
		'MID. IMP.': 150,
		'MIDDLE BYZ': 700,
		'NERO': 60,
		'PRE-PTOL.': -333,
		'PTOL.': -100,
		'PTOL./ROM.': -20,
		'ROM.': 50,
		'ROM./BYZ.': 600,
		'ROM': 50,
		'ROMAN IMP': 200,
		'ROMAN': 50,
		'ROMANESQUE': 1150,
		'RÖMISCHE ZEIT': 50,
		'RÖMISCHE': 50,
		'RÖMISCH': 50,
		'SPÄTHELLENISTISCH': -1,
		'SPÄTE KAISERZEIT': 300,
		'SPÄTERE KAISERZEIT': 300,
		'TIBERIUS': 25,
		'TITUS': 80,
		'TRAJAN': 105,
		'TRAJAN/HADRIAN': 115,
		'TRAJANIC': 105,
		'VESPASIAN': 70,
		'VORRÖMISCH': -150,
		'VÖRROMISCH': -150,
		'[UNKNOWN]': 2500,
		'?': 2500
	}

	dontcare = re.compile(r'^(prob. |middle |not bef\. |Zeit des |wohl |frühestens |\(hohe\) |)|( od\. .*?| oder .*?| \(od\. .*?)$')

	date = re.sub(r'\?', '', stringdate)
	# date = re.sub(r'\.$', '', date)
	date = re.sub(dontcare, '', date)

	date = date.upper()

	if date in mapper:
		numericaldate = mapper[date]
	else:
		# for debugging...
		# print(original.upper())
		pass

	return numericaldate


"""

select distinct recorded_date from works where converted_date = '9999';

          recorded_date           
----------------------------------
 1.Jh.v.Chr.-1.Jh.n.Chr.
 12 v.Chr.／3 n.Chr.／87 n.Chr.﹖
 2.Jh.n.Chr.﹖ ／ 2.Jh.v.Chr.﹖
 62 n.Chr. ⟦75 v.Chr.⟧
 Anf. 1.Jh.v.Chr.／1.Jh.n.Chr.﹖
 Ant. Pius
 Ant. Pius ﹠ M. Aur.
 Antonine or later
 Antonine or sh.after
 Antoninus Pius﹖
 Arab.﹖
 Byz.／Arab.
 Caligula
 Caracalla﹖
 Chr.／Byz.
 Claudian﹖
 Claudius﹖
 Copt.
 Early Byz
 Early Christ.
 Early Christian
 Early／Mid. Imp.
 Ende Republik／Beg. Kaiserzeit
 Erste Kaiserzeit
 Flavian ❨or earlier❩
 Frankish
 Geometric／Sub-Geometric
 Hadrian or later
 Hadrian, or later
 Hadrianic or Antonine
 Hadrian﹢
 Hell. or later
 Hellenist.
 Herm
 Herodian
 High Imp.
 High Imp.﹖
 IIa-aet Rom﹖
 Ia／aet Imp
 Ia／aet Imp﹖
 Imp.-Byz.
 Kopt.
 Late Chr.
 Late Empire
 Late Hell.／Early Imp.
 Late Hellenist
 Late Imp.-Early Byz.
 Late Ptol.／Rom.
 Late Roman
 Later Chr.
 M. Aur.﹖
 M. Aurelius, or later
 Marcus Aurelius／Commodus
 Mid Byz
 Mid／Late Byz
 Ptol.-Rom.
 Ptol.-Rom.﹖
 Ptol.／Early Imp.
 Ptolemaic
 Rom. or Hell.﹖
 Rom.-Byz.
 Septimius Severus
 Septimius Severus ❨or later❩
 Severus-Gallienus
 Spätzeit﹖
 Theb
 Trajan, or sh. bef.
 Trajanic or later
 Trajanic-Antonine
 Turkish﹖
 Zeit Hadrians﹖ ／ erheblich fru
 ac
 aet Hell／aet Rom
 aet Imp／aet Chr
 aet Rom antiq
 aet Romana
 aet Ves-aet Dom
 aet chr
 aet imp inf
 aet rec
 aet tardae
 aet. imp. Rom.
 aetate Romana
 aetatis infimae
 ante Chr nat﹖
 ante Chr﹖
 archaisch
 archaischer Schriftcharakter
 archaisches﹖
 archaisch﹖
 augusteisch
 augusteische Zeit
 beg Rom imp
 beg. Antonine
 betw. Trajan ﹠ Severus
 early Antonine
 early Antonine or later
 early Byz
 early Hadrianic
 early medieval
 end Hellenist.
 end Ptol.／Rom.
 end Ptol.／beg. Rom.
 end Ptol.❨﹖❩
 erste Kaiserzeit
 forgery﹖
 forgery／mod.﹖
 fruhe bis mittlere Kaiserzeit
 frühbyzantinisch
 frühhellenistisch
 frühhellenistisch﹖
 hellenistisch - spätrömisch
 hellenistisch-frühe Kaiserzeit
 hellenistisch／römisch
 high Imp.
 hohe Kaiserzeit
 hohe hellenistische Zeit
 imp Rom
 init principat
 init❨﹖❩ aet Imp
 kaiserzeitlich／spätrömisch
 late
 late Attic
 late Hadrianic-early Antonine
 late Ptol.-early Rom.﹖
 late Rom.
 late Roman
 late Severan
 late Severan or sh.aft.
 late classic
 late period
 later Severan﹖
 later imperial
 med.／mod.﹖
 medieval
 medieval﹖
 mid Byz
 mittelhellenistisch
 mittlere Kaiserzeit﹖
 mod.
 noch Ende der Republik﹖
 noch hellenistisch﹖
 non post August
 not bef. middle Antonine
 poss. Antonine
 poss. late Hadrianic
 post Hadrian
 post princ Aug
 post-Byz﹖
 post-Hadrianic
 prob. early Antonine
 prob. middle Antonine
 prob. sh.aft. middle Antonine
 relativ spät
 romisch
 römisch ❨Kaiserzeit﹖❩
 römisch ❨eher spät❩
 römisch, christlich﹖
 spät
 spätantik
 spätantik﹖
 späte Republik oder fruhe Kais
 spätere hellenistische Zeit
 späthell. - frühe Kaiserzeit
 spätrömisch
 temp Macedonica
 traianisch-hadrianische Zeit
 ult temp Romano
 unter Augustus
 unter Nerva／Hadrian／Trajan
 vermutlich frühe Kaiserzeit
 wohl erste Kaiserzeit
 wohl noch hellenistisch
 wohl noch römisch
 ziemlich spät
 zw. 1 v.Chr. und 4 n.Chr.
 ﹖
 ⟦Wiligelmo⟧
 ⟦ant.⟧
 ⟦antique⟧
 ⟦forgery⟧
 ⟦frühe Kaiserzeit⟧
 ⟦modern forgery⟧
 ❨spät❩römisch
(184 rows)


"""
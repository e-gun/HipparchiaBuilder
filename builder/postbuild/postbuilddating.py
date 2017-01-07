# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


def convertdate(date, secondpass=False):
	"""

	there are 21584 distinct recorded_date values in the works table
	[q = 'select distinct recorded_date from works order by recorded_date']

	take a string date and try to assign a number to it: IV AD --> 450, etc.

	a very messy way to achieve highly suspect results

	this is IN PROGRESS and likely to remain so for a while longer

	:param date:
	:return:
	"""

	numericaldate = 9999

	originaldate = date

	german = re.compile(r'(n\.|v\.Chr\.)')
	arabic = re.compile(r'\d')
	ordinal = re.compile(r'((\d)st|(\d)nd|(\d)rd|(\d{1,})th)')
	roman = re.compile(r'[IVX]')
	ages = re.compile(r'aet')

	if re.search(german, date) is not None and secondpass == False:
		numericaldate = germandate(date)
	elif re.search(arabic, date) is not None and re.search(ordinal,date) is not None and secondpass == False:
		numericaldate = numberedcenturydate(date, ordinal)
	elif re.search(ages, date) is not None and secondpass == False:
		numericaldate = aetatesdates(date)
	elif re.search(roman, date) is not None and secondpass == False:
		numericaldate = romannumeraldate(date)
	elif re.search(arabic, date) is not None and secondpass == False:
		numericaldate = numericdate(date)

	if numericaldate != 9999:
		numericaldate = round(int(numericaldate), 1)
		return numericaldate

	# if we have not returned yet, then only a grab bag should remain: 'späthellenistisch', etc.
	# and so we pass through the old convertdate() code in a desperate last attempt

	datemapper = {
		'1. Hälfte 2. Jh. v.Chr.': -175,
		'1. Hälfte 4. Jh. v.Chr.': -375,
		'1. Hälfte 4.Jh. v.Chr.': -375,
		'adv. Imp.': 400,
		'Early Byz': 400,
		'Middle Byz': 700,
		'Late Byz': 1200,
		'aet Rom rec/init aet Byz': 350,
		'aet Hell tard': -1,
		'aet Hell': -250,
		'aet Imp tard': 400,
		'aet imp': 200,
		'aet Imp': 200,
		'Early Imp.': 100,
		'aet inferior': 1200,
		'Antonine': 150,
		'archaic': -700,
		'Archaic': -700,
		'Archaic/Classical': -600,
		'August': 1,
		'Augustan': 1,
		'Augustus': 1,
		'early Roman': -50,
		'early Rom.': -50,
		'frühe römische Zeit': -50,
		'Early Byz.': 450,
		'early Byz': 450,
		'early Byz.': 450,
		'Early Byzantine': 450,
		'Early-Mid. Imp.': 100,
		'Early-Middle Imp.': 100,
		'EarlýMid. Imp.': 100,
		'Byz.': 700,
		'Byz': 700,
		'Byzantine': 700,
		'late Byz': 1200,
		'Late Byz.': 1200,
		'Late Byzantine': 1200,
		'byzantinisch': 700,
		'byzantinische Zeit': 700,
		'Chr.': 400,
		'classical': -425,
		'Christ.': 400,
		'early Chr.': 350,
		'christlich': 400,
		'christl.': 400,
		'Classical': -400,
		'aet Christ': 400,
		'Constantine': 315,
		'Carolingian': 775,
		'date': 1500,
		'early Imp.': 25,
		'early imp.': 25,
		'early imp': 25,
		'init aet Imp': 25,
		'frühellenistisch': -300,
		'Early Hell.': -300,
		'Early Ptol.': -275,
		'Early Chr': 200,
		'end 4th-beg. 3rd bc': 300,
		'flavisch': 85,
		'fru+he Kaiserzeit (Augustus?)': 1,
		'fru+he Kaiserzeit (Augustus)': 1,
		'fru+he Kaiserzeit': 25,
		'Fru+he Kaiserzeit': 25,
		'fru+hhellenistisch': -300,
		'Hadrian': 125,
		'Hadrianic-early Antonine': 140,
		'Hadrianic': 125,
		'hadrianisch': 125,
		'hadrianische Zeit': 125,
		'early Hell.': -300,
		'Hell.': -250,
		'Hellenistic': -250,
		'Hell./Rom.': -50,
		'Hell.-Rom.': -50,
		'hellenistisch - spa+tro+misch': 200,
		'hellenistisch-fru+he Kaiserzeit': -100,
		'hellenistisch': -250,
		'hristlich': 400, # the 'c' will have been chopped
		'Ia-c 50p': 1,
		'Julio-Claudian': 25,
		'Kaiserzeit': 100,
		'kaiserzeitlich': 100,
		'late archaic': -600,
		'Late Archaic': -600,
		'Late Hell.-Early Imp.': -15,
		'Late Hell.': -1,
		'late Hell.-early Imp.': -1,
		'late Hell./Rom.': -1,
		'late Hell./early Rom.': -1,
		'hell./frühe Kaiserzeit': -1,
		'late Hellenist.': -1,
		'late Hellen': -1,
		'late Hell': -1,
		'late Hell.': -1,
		'Late Imp.': 300,
		'late Imp.': 300,
		'late imperial': 300,
		'late imp': 300,
		'later Imp.': 300,
		'späte Kaiserzeit': 300,
		'spätere Kaiserzeit': 300,
		'Late Ptol.': -50,
		'letztes Viertel 1. Jh.v.Chr.': -15,
		'Marcus Aurelius': 170,
		'Merov.': 600,
		'med.': 1100,
		'Nero': 60,
		'pre-Ptol.': -333,
		'Ptol.': -100,
		'Ptol./Rom.': -20,
		'römische': 50,
		'römische Zeit': 50,
		'Rom.': 50,
		'Rom./Byz.': 600,
		'Rom': 50,
		'Roman Imp': 200,
		'aet Rom rec': 300,
		'aet imp Rom': 200,
		'aet Rom tard/mediev': 700,
		'Roman': 50,
		'Romanesque': 1150,
		'spa+thell. - fru+he Kaiserzeit': -1,
		'spa+thellenistisch': -25,
		'Tiberius': 25,
		'Titus': 80,
		'Trajan': 105,
		'end Trajan': 110,
		'Trajan/Hadrian': 115,
		'Trajanic': 105,
		'Vespasian': 70,
	}

	dontcare = re.compile(r'^(prob. |middle |not bef\. )')


	date = re.sub(r'\?', '', date)
	#date = re.sub(r'\.$', '', date)
	date = re.sub(dontcare, '', date)

	if date in datemapper:
		numericaldate = datemapper[date]
		return numericaldate

	# print('stillconfused',date)

	numericaldate = round(int(numericaldate),1)

	return numericaldate


def germandate(stringdate):
	"""

	a very large percentage of the German dates will pass through this with OK results

	:param stringdate:
	:return:
	"""

	original = stringdate

	dontcare = re.compile(r'^(Frühjahr |wohl des |wohl noch |wohl |vielleicht noch |vermutlich |etwa |Mitte |frühestens |um |des |ca\. |ca\.|noch |nicht später als |nicht vor |nicht früher als |Wende des |Wende |2\.Drittel )')
	subtract = re.compile(r'^(spätestens |am ehesten |nicht später als |kaum später als |term\.ante |1\.Hälfte |1\.Drittel |1. Viertel |1\.Viertel |Beginn |frühes |fruhes |erste Jahrzehnte |Anf\. |Anf |Anf\.| 1. H.)')
	tinysubtract = re.compile(r'^(einige Zeit vor |\(kurz\) vor |kurz vor |vor |2. Viertel |2.Viertel )')
	add = re.compile(r'^(nicht früher als |term\.post |nach |letztes Drittel |letztes Viertel |3\. Viertel |3\.Viertel |4. Viertel |2\. Hälfte |2\.Hälfte |2 Hälfte |spätes |ausgehendes |späteres |Ende )')
	century = re.compile(r'(Jh\. |Jh\.| Jhdts\. |Jhdt\. )')
	split = re.compile(r'(\d{1,})[-/](\d{1,})')
	misleadingmiddles = re.compile(r'(-ca\.|-vor )')
	# collapse = re.compile(r'( od | oder )')

	modifier = 1
	midcentury = -50
	fudge = 0

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(misleadingmiddles, '-', stringdate)
	# stringdate = re.sub(collapse,'/', stringdate)


	if re.search(r'v\.Chr\.',stringdate) is not None and re.search(r'n\.Chr\.',stringdate) is not None:
		parts = re.search(r'\d\s{0,1}v\.Chr(.*?)\d\s{0,1}n\.Chr(.*?)',stringdate)
		try:
			one = int(parts.group(1))
			two = int(parts.group(3))
			numericaldate = ((-1 * one * 100) + (two * 100)) / 2
		except:
			numericaldate = 9999
		return numericaldate
	elif re.search(r'zw.',stringdate) is not None:
		parts = re.search(r'^zw.(\d{1,})\s{0,1}und(\d{1,})',stringdate)
		if re.search(r'v\.Chr\.', stringdate) is not None:
			modifier = -1
			fudge += 100
		try:
			one = int(parts.group(1))
			two = int(parts.group(2))
			numericaldate = (((-1 * one ) + (two )) / 2) * modifier + fudge
		except:
			# AttributeError: 'NoneType' object has no attribute 'group'
			# failed zw. 1 v.Chr. und 4 n.Chr.
			numericaldate = convertdate(original, secondpass=True)
		return numericaldate
	elif re.search(r'v\.Chr\.',stringdate) is not None:
		modifier = -1

	stringdate = re.sub(r'(v\.|n\.)Chr\.', '', stringdate)

	if re.search(subtract, stringdate) is not None:
		stringdate = re.sub(subtract,'',stringdate)
		fudge = -25

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract,'',stringdate)
		fudge = -10

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add,'',stringdate)
		fudge = 25

	if re.search(century, stringdate) is not None:
		stringdate = re.sub(century, '', stringdate)
		modifier = modifier * 100

	re.sub(r'(^\s|\s$)','',stringdate)

	stringdate = re.sub(dontcare,'', stringdate)
	stringdate = re.sub(r'\.', '', stringdate)

	if re.search(split,stringdate) is not None:
		parts = re.search(split,stringdate)
		one = int(parts.group(1))
		two = int(parts.group(2))
		if modifier < 100:
			numericaldate = ((one + two) / 2) * modifier
		else:
			numericaldate = (((one + two) / 2) * modifier) + fudge
		return numericaldate

	try:
		if abs(modifier) != 1: # i.e., = 100 or -100
			numericaldate = int(stringdate) * modifier + fudge + midcentury
		else:
			numericaldate = int(stringdate) * modifier + fudge
	except:
		numericaldate = convertdate(original, secondpass=True)

	return numericaldate


def numberedcenturydate(stringdate, ordinalregexfinder):
	"""

	try to parse a date that has something like '5th' in it

	ordinal = re.compile(r'((\d)st|(\d)nd|(\d)rd|(\d{1,})th)')

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
	embedded = re.compile(r'(\(.*?\d{1,}.*?[ab]c\))')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(eb, r'\1/\3', stringdate)

	if re.search(embedded, stringdate) is not None:
		e = re.search(embedded, stringdate)
		numericaldate = numericdate(e.group(0))
		return numericaldate

	if re.search(subtract, stringdate) is not None:
		stringdate = re.sub(subtract,'',stringdate)
		fudge = -75

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract,'',stringdate)
		fudge = -25

	if re.search(tinyadd, stringdate) is not None:
		stringdate = re.sub(tinyadd,'',stringdate)
		fudge = 25

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add,'',stringdate)
		# note that 75 was not chosen because the candidate did not look right for it
		fudge = 25

	if re.search(r'bc$',stringdate) is not None:
		modifier = modifier * -1
		fudge = fudge + 100
	elif re.search(r'ac$',stringdate) is None and re.search(r'(1st|2nd) half',stringdate) is not None:
		# 2nd half Antonine
		numericaldate = convertdate(original, secondpass=True)
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

	if twodigit == True:
		if re.search(r'bc(.*?)ac$',stringdate) is None:
			numericaldate = (((firstdigit + seconddigit) / 2) * modifier ) + fudge
			if modifier > 0:
				numericaldate += 50
			else:
				numericaldate -= 50
		else:
			numericaldate = (((firstdigit * -100) + (seconddigit * 100))/2)
	else:
		numericaldate = (firstdigit * modifier) + fudge + midcentury + fudge

	if numericaldate == 0:
		numericaldate = 1

	return numericaldate


def romannumeraldate(stringdate):
	"""

	V -> 450

	:param datestring:
	:return:
	"""

	map = { 'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11,
			'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19}

	original = stringdate
	modifier = 100
	midcentury = -50
	fudge = 0
	numericaldate = -9999

	falsepositive = re.compile(r'(Imp|\d|aet )')
	fixone = re.compile(r'Í')
	fixtwo = re.compile(r'á')

	if re.search(falsepositive, stringdate) is not None:
		numericaldate = convertdate(original, secondpass=True)
		return numericaldate

	stringdate = re.sub(fixone,r'I/',stringdate)
	stringdate = re.sub(fixtwo, r'a/', stringdate)

	dontcare = re.compile(r'^(p med |s |p |c.med s |c med |med s |mid- |mid |fere s )|( ut vid| p|p)$')
	fi = re.compile(r'^fin (.*?)/init (.*?)')
	# subtract = re.compile()
	tinysubtract = re.compile(r'(^(ante med |ante md |beg\. |beg |a med |early |init/med |init |latest )| p prior$|/init )')
	bigadd = re.compile(r'^(post fin s|post )')
	add = re.compile(r'(^(ante fin |ant fin|ex s |ex |end |med/fin |late |post med s )|(/postea|/paullo post)$)')
	splitter = re.compile(r'([IVX]{1,})[-/]([IVX]{1,})')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(fi, r'\1/\2',stringdate)

	stringdate = re.sub(r'\?', '', stringdate)

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract,'',stringdate)
		fudge = -25

	if re.search(bigadd, stringdate) is not None:
		stringdate = re.sub(bigadd,'',stringdate)
		fudge = 75

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add,'',stringdate)
		fudge = 25

	if re.search(r'( bc$|bc$| a$|a$)',stringdate) is not None:
		stringdate = re.sub(r'( bc| BC|bc| sac| ac| a|a)$','',stringdate)
		modifier = modifier * -1
		fudge = fudge + 100

	if re.search(r'(ac.*?[/-].*?pc|bc.*?[/-].*?ac)$',original) is not None:
		# I sac - I spc
		numerals = re.findall(r'[IVX]{1,}',original)
		digits = [map[n] for n in numerals]
		digits[0] = digits[0] * -1
		numericaldate = (((digits[0] + digits[1]) / 2) * modifier) + fudge
	elif re.search(splitter,stringdate) is not None:
		# II-III spc
		centuries = re.search(splitter,stringdate)
		first = centuries.group(1)
		second = centuries.group(2)
		first = map[first]
		second = map[second]
		if first > second:
			modifier = modifier * -1
		numericaldate = (((first + second) / 2) * modifier) + fudge + midcentury
	elif re.search(r'[IVX]{1,}',stringdate) is not None:
		numeral = re.search(r'[IVX]{1,}',stringdate)
		try:
			numeral = map[numeral.group(0)]
			numericaldate = (numeral * modifier) + fudge + midcentury
		except:
			# no key
			numericaldate = convertdate(original, secondpass=True)

	if numericaldate == 0:
		numericaldate = 1

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
	splitter = re.compile(r'(\d{1,})[/-](\d{1,})')
	bcad = re.compile(r'(\d{1,}) BC-AD (\d{1,})')
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
		try:
			digits = re.findall(splitter, stringdate)
			one = int(digits[0][0])
			two = int(digits[0][1])
			numericaldate = (one + two ) / 2 * modifier
			return numericaldate
		except:
			numericaldate = convertdate(original, secondpass=True)

	if re.search(nearestdecade, stringdate) is not None:
		digits = re.search(r'\d{1,}',stringdate)
		year = int(digits.group(0))
		decade = year % 10
		if ('post' in stringdate and modifier == 1) or ('ante' in stringdate and modifier == -1):
			numericaldate = (year + (10 - decade))
		elif ('post' in stringdate and modifier == -1) or ('ante' in stringdate and modifier == 1):
			numericaldate = year - decade
		return numericaldate

	if re.search(tinysubtract, stringdate) is not None:
		stringdate = re.sub(tinysubtract,'',stringdate)
		fudge = -10

	if re.search(littleadd, stringdate) is not None:
		stringdate = re.sub(littleadd,'',stringdate)
		fudge = 10

	digits = re.search(r'\d{1,}', stringdate)
	year = int(digits.group(0))
	numericaldate = (year * modifier) + fudge

	return numericaldate


def aetatesdates(stringdate):
	"""

	aet. Aug -> 10

	:param stringdate:
	:return:
	"""

	original = stringdate
	fudge = 0

	map = {
		'Ant': 150,
		'August fere': 1,
		'Ant/Aur': 160,
		'Aur': 170,
		'Aur/Carac': 200,
		'Aur/Commod': 160,
		'Carac': 205,
		'Chr': 400,
		'Claud': 50,
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

	stringdate = re.sub(r'(aetate |aetats |aetat |aet )','',stringdate)
	stringdate = re.sub(kill, '',stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(r'(^\s|\s$)','',stringdate)

	if re.search(add, stringdate) is not None:
		stringdate = re.sub(add,'',stringdate)
		fudge = 25

	if re.search(subtr, stringdate) is not None:
		stringdate = re.sub(subtr,'',stringdate)
		fudge = -25

	try:
		numericaldate = map[stringdate] + fudge
	except:
		numericaldate = convertdate(original, secondpass=True)

	# print('numericaldate',numericaldate)

	return numericaldate

# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


def convertdate(date, passvalue=0):
	"""

	there are 21584 distinct recorded_date values in the works table
	[q = 'select distinct recorded_date from works order by recorded_date']

	take a string date and try to assign a number to it: IV AD --> 450, etc.

	a very messy way to achieve highly suspect results

	this is IN PROGRESS and likely to remain so for a while longer

	:param date:
	:return:
	"""

	original = date
	numericaldate = 9999

	german = re.compile(r'(n\.|v\.Chr\.)')
	arabic = re.compile(r'\d')
	ordinal = re.compile(r'((\d)st|(\d)nd|(\d)rd|(\d{1,})th)')
	roman = re.compile(r'[IVX]')
	ages = re.compile(r'aet')

	if re.search(german, date) is not None and passvalue == 0:
		numericaldate = germandate(date)
	elif re.search(arabic, date) is not None and re.search(ordinal,date) is not None and passvalue < 2:
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

	datemapper = {
		'1. Hälfte 2. Jh. v.Chr.': -175,
		'1. Hälfte 4. Jh. v.Chr.': -375,
		'1. Hälfte 4.Jh. v.Chr.': -375,
		'adv. Imp.': 400,
		'aet Christ': 400,
		'aet Hell tard': -1,
		'aet Hell': -250,
		'aet imp Rom': 200,
		'aet Imp tard': 400,
		'aet imp': 200,
		'aet Imp': 200,
		'aet inferior': 1200,
		'aet Rom rec': 300,
		'aet Rom rec/init aet Byz': 350,
		'aet Rom tard/mediev': 700,
		'Antonine': 150,
		'archaic': -700,
		'Archaic': -700,
		'Archaic/Classical': -600,
		'August': 1,
		'Augustan': 1,
		'Augustus': 1,
		'Byz.': 700,
		'Byz': 700,
		'Byzantine': 700,
		'byzantinisch': 700,
		'byzantisch': 700,
		'byzantinische Zeit': 700,
		'Carolingian': 775,
		'Chr.': 400,
		'Christ.': 400,
		'christl.': 400,
		'christlich': 400,
		'Classical': -400,
		'classical': -425,
		'Constantine': 315,
		'date': 1500,
		'early Byz.': 450,
		'Early Byz.': 450,
		'Early Byz': 400,
		'early Byz': 450,
		'Early Byzantine': 450,
		'early Chr.': 350,
		'Early Chr': 200,
		'early Hell.': -300,
		'Early Hell.': -300,
		'early imp.': 25,
		'early Imp.': 25,
		'Early Imp.': 100,
		'early imp': 25,
		'Early Ptol.': -275,
		'early Rom.': -50,
		'early Roman': -50,
		'Early-Mid. Imp.': 100,
		'Early-Middle Imp.': 100,
		'EarlýMid. Imp.': 100,
		'end 4th-beg. 3rd bc': 300,
		'end Trajan': 110,
		'flavisch': 85,
		'frühe Kaiserzeit (Augustus)': 1,
		'frühe Kaiserzeit': 25,
		'fru+hhellenistisch': -300,
		'frühe römische Zeit': -50,
		'frühellenistisch': -300,
		'Hadrian': 125,
		'Hadrianic-early Antonine': 140,
		'Hadrianic': 125,
		'hadrianisch': 125,
		'hadrianische Zeit': 125,
		'Hell.-Rom.': -50,
		'Hell.': -250,
		'hell./frühe Kaiserzeit': -1,
		'Hell./Rom.': -50,
		'Hellenistic': -250,
		'hellenistisch': -250,
		'hellenistische Zeit': -250,
		'Ia-c 50p': 1,
		'Imp.': 200,
		'Imp': 200,
		'init aet Imp': 25,
		'Julio-Claudian': 25,
		'Kaiserzeit': 100,
		'kaiserzeitlich': 100,
		'late archaic': -600,
		'Late Archaic': -600,
		'Late Byz.': 1200,
		'late Byz': 1200,
		'Late Byz': 1200,
		'Late Byzantine': 1200,
		'late Class.': -415,
		'late Class.-Hell.': -375,
		'late Hadrianic': 135,
		'late Hadrianic or after': 145,
		'late Hadrianic or later': 145,
		'late Hadrianic-Antonine': 155,
		'late Hell.-early Imp.': -1,
		'Late Hell.-Early Imp.': -15,
		'late Hell.': -1,
		'Late Hell.': -1,
		'late Hell./early Rom.': -1,
		'late Hell./Rom.': -1,
		'late Hell': -1,
		'late Hellen': -1,
		'late Hellenist.': -1,
		'late Imp.': 300,
		'Late Imp.': 300,
		'late imp': 300,
		'late imperial': 300,
		'Late Ptol.': -50,
		'later Imp.': 300,
		'letztes Viertel 1. Jh.v.Chr.': -15,
		'Marcus Aurelius': 170,
		'med.': 1100,
		'Merov.': 600,
		'Middle Byz': 700,
		'Nero': 60,
		'pre-Ptol.': -333,
		'Ptol.': -100,
		'Ptol./Rom.': -20,
		'Rom.': 50,
		'Rom./Byz.': 600,
		'Rom': 50,
		'Roman Imp': 200,
		'Roman': 50,
		'Romanesque': 1150,
		'römische Zeit': 50,
		'römische': 50,
		'römisch': 50,
		'späthellenistisch': -1,
		'späte Kaiserzeit': 300,
		'spätere Kaiserzeit': 300,
		'Tiberius': 25,
		'Titus': 80,
		'Trajan': 105,
		'Trajan/Hadrian': 115,
		'Trajanic': 105,
		'Vespasian': 70,
		'vorrömisch': -150,
		'vörromisch': -150

	}

	dontcare = re.compile(r'^(prob. |middle |not bef\. |Zeit des )')


	date = re.sub(r'\?', '', date)
	#date = re.sub(r'\.$', '', date)
	date = re.sub(dontcare, '', date)

	if date in datemapper:
		numericaldate = datemapper[date]
		return numericaldate


	# failed all of the tests, right?
	print(original)

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
	split = re.compile(r'(\d{1,})[-/](\d{1,})')
	misleadingmiddles = re.compile(r'(-ca\.|-vor )')
	oder = re.compile(r'(\d{1,})( od | oder )(\d{1,})')

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
			numericaldate = convertdate(original, passvalue=1)
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

	if re.search(oder,stringdate) is not None:
		parts = re.search(oder,stringdate)
		one = int(parts.group(1))
		two = int(parts.group(3))
		if modifier < 100:
			numericaldate = ((one + two) / 2) * modifier
		else:
			numericaldate = (((one + two) / 2) * modifier) + fudge + midcentury
		return numericaldate

	try:
		if abs(modifier) != 1: # i.e., = 100 or -100
			numericaldate = int(stringdate) * modifier + fudge + midcentury
		else:
			numericaldate = int(stringdate) * modifier + fudge
	except:
		numericaldate = convertdate(original, passvalue=1)

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
		numericaldate = convertdate(original, passvalue=3)

	# print('numericaldate',numericaldate)

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
	numericaldate = 9999

	falsepositive = re.compile(r'(Imp|\d|aet )')
	fixone = re.compile(r'Í')
	fixtwo = re.compile(r'á')

	if re.search(falsepositive, stringdate) is not None:
		numericaldate = convertdate(original, passvalue=4)
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
		digits = re.findall(splitter, stringdate)
		try:
			one = int(digits[0][0])
			two = int(digits[0][1])
			if len(str(one)) != len(str(two)):
				newtwo = ''
				strone = str(one)
				strtwo = str(two)
				for i in range(0,len(strone) - len(strtwo)):
					newtwo += strone[i]
				newtwo += strtwo
				two = int(newtwo)
			numericaldate = (one + two ) / 2 * modifier
			return numericaldate
		except:
			# 'AD 199/III spc'
			try:
				one = int(digits[0][0])
				numericaldate = one * modifier
			except:
				print('repass',digits[0][0])
				numericaldate = convertdate(digits[0][0], passvalue=4)

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



"""

still clueless re:

(Ende) 1.Jh.v.Chr. / Anf.1.Jh.
(Ende) 1.Jh.v.Chr. / Anf.1.Jh.
(Ende) 3.Jh.n.Chr.
(Ende) 3.Jh.n.Chr.
(frühes) 3.Jh.v.Chr.
(frühes) 3.Jh.v.Chr.
(hohe) Kaiserzeit
(spät)römisch
1.Jh,n.Chr.
1.Jh,n.Chr.
1.Jh.v.Chr. oder später
1.Jh.v.Chr. oder später
1.Jh.v.Chr.-1.Jh.n.Chr.
108-init Ia
108-init Ia
12 v.Chr./3 n.Chr./87 n.Chr.
12.Jh.n.Chr. od. früher
12.Jh.n.Chr. od. früher
15 v.-20 n.Chr.
15 v.-20 n.Chr.
179 oder 175 n.Chr.
179 oder 175 n.Chr.
1st half Antonine
1st half Antonine
1st half Hadrianic
1st half Hadrianic
1st half or midddle Antonine
1st half or midddle Antonine
2. H. 1. Jhdt. v.Chr.
2. H. 1. Jhdt. v.Chr.
2. od. eher 3.Jh.n.Chr.
2. od. eher 3.Jh.n.Chr.
2. oder 3.Jh.n.Chr.
2. oder 3.Jh.n.Chr.
2. oder eher 3.Jh.n.Chr.
2. oder eher 3.Jh.n.Chr.
2.Hālfte 2. Jh.v.Chr.
2.Hālfte 2. Jh.v.Chr.
2.Jh.n.Chr. / 2.Jh.v.Chr.
224/5 ac [II]
224/5 ac [II]
250a-IVp
250a-IVp
250a-IVp
250a-IVp
281-frühe 260er Jahre v.Chr.
281-frühe 260er Jahre v.Chr.
2nd half Antonine
2nd half Antonine
3. od. 2.Jh.v.Chr.
3. od. 2.Jh.v.Chr.
3. oder 2.Jh.v.Chr.
3. oder 2.Jh.v.Chr.
3.Jh.n.Chr. od. später
3.Jh.n.Chr. od. später
30 v.-284 n.Chr.
30 v.-284 n.Chr.
4. od. 3.Jh.v.Chr.
4. od. 3.Jh.v.Chr.
4.Jh.v.Chr. (vor 360 v.Chr.)
4.Jh.v.Chr. (vor 360 v.Chr.)
411 sub XL domi
411 sub XL domi
5. od. 4.Jh.v.Chr.
5. od. 4.Jh.v.Chr.
5. od. 6.Jh.n.Chr.
5. od. 6.Jh.n.Chr.
6. od. 7.Jh.n.Chr.
6. od. 7.Jh.n.Chr.
6./frühes 5.Jh.v.Chr.
6./frühes 5.Jh.v.Chr.
62 n.Chr. [75 v.Chr.]
63 od. 62 v.Chr.
63 od. 62 v.Chr.
63 oder 62 v.Chr.
63 oder 62 v.Chr.
7. - Beg. 5. Jhdt. v.Chr.
7. - Beg. 5. Jhdt. v.Chr.
8.Jh.n.Chr. (vor 730 oder nach 7
8.Jh.n.Chr. (vor 730 oder nach 7

AD 199/III spc
AD 199/III spc
AD 623<hmu_discarded_form>VÍVII spc</hmu_discarded_form>
AD 623<hmu_discarded_form>VÍVII spc</hmu_discarded_form>
Anf. 1.Jh.v.Chr./1.Jh.n.Chr.
Anf. 3.Jh.v.Chr. (um 281 v.Chr.
Anf. 3.Jh.v.Chr. (um 281 v.Chr.
Ant. Pius
Ant. Pius  M. Aur.
Antonine or later
Antonine or sh.after
Antoninus Pius
Arab.
Augustus-Tiberius
Augustus/Tiberius
Augustus/Tiberius
Byz./Arab.
Caligula
Caracalla
Chr./Byz.
Christian
Cladius
Claudian
Claudius
Commodus
Copt.
Domitian
Early Chr.
Early Chr.
Early Christ.
Early Christian
Early Rom.
Early Rom.
Early Roman
Ende 1./Anf. 2. Jh. n.Chr.
Ende 1./Anf. 2. Jh. n.Chr.
Ende 1.Jh.v.Chr./Anf.1.Jh.n.Ch
Ende 1.Jh.v.Chr./Anf.1.Jh.n.Ch
Ende 2./ Anf.1.Jh.v.Chr.
Ende 2./ Anf.1.Jh.v.Chr.
Ende 2./Anf. 3.Jh.n.Chr.
Ende 2./Anf. 3.Jh.n.Chr.
Ende 2./Anf.3.Jh.n.Chr.
Ende 2./Anf.3.Jh.n.Chr.
Ende 4.-Anf. 3. Jh. v.Chr.
Ende 4.-Anf. 3. Jh. v.Chr.
Ende 4.-Anf.3.Jh.v.Chr.
Ende 4.-Anf.3.Jh.v.Chr.
Ende 4./Anf. 3.Jh.v.Chr.
Ende 4./Anf. 3.Jh.v.Chr.
Ende 4./Anf.3.Jh.v.Chr.
Ende 4./Anf.3.Jh.v.Chr.
Ende 4.Jh.v.Chr. od. später
Ende 4.Jh.v.Chr. od. später
Ende 5.-Anfang 7.Jh.n.Chr.
Ende 5.-Anfang 7.Jh.n.Chr.
Ende 5.-Beginn 6. Jhdt. n.Chr.
Ende 5.-Beginn 6. Jhdt. n.Chr.
Ende Republik/Beg. Kaiserzeit
Erste Hälfte 2.Jh.v.Chr.
Erste Hälfte 2.Jh.v.Chr.
Erste Kaiserzeit
Flavian
Flavian (or earlier)
Flavian
Frankish
Frühe Kaiserzeit
Geometric/Sub-Geometric
Hadrian or later
Hadrian+
Hadrian, or later
Hadrianic or Antonine
Hell. or later
Hellenist.
Herm
Herodian
High Imp.
High Imp.
High Imp.
High Imp.
I:c 705-707 ac
I:c 705-707 ac
IIa-aet Rom
IIa-aet Rom
IIp [K.158]
IIp [K.158]
IIÍinit IIa
IIÍinit IIa
IIÍinit IVp
IIÍinit IVp
IV/init IIIa
IV/init IIIa
Imp. (aft. 212 ac)
Imp. (aft. 212 ac)
Imp. (bef. 212 ac)
Imp. (bef. 212 ac)
Imp.-Byz.
Imp.-Byz.
Imperial
Imperial
IÍIa [K.25]
IÍIa [K.25]
IÍinit IIIp
IÍinit IIIp
IÍinit IIIp
IÍinit IIIp
Iáaet Imp
Iáaet Imp
Iáaet Imp
Iáaet Imp
Kaiserzeit (nach 212 n.Chr.)
Kaiserzeit (nach 212 n.Chr.)
Kopt.
Late Chr.
Late Empire
Late Hell./Early Imp.
Late Hell./Early Imp.
Late Hellenist
Late Imp.-Early Byz.
Late Imp.-Early Byz.
Late Ptol./Rom.
Late Roman
Later Chr.
Later Imp.
Later Imp.
M. Aur.
M. Aurelius, or later
Marcus Aurelius/Commodus
Mid Byz
Mid. Imp.
Mid. Imp.
Mid/Late Byz
Mitte oder spateres 3.Jh.v.Chr.
Mitte oder spateres 3.Jh.v.Chr.
Mitte-Ende 4. Jh. v.Chr.
Mitte-Ende 4. Jh. v.Chr.
Ptol.-Rom.
Ptol.-Rom.
Ptol./Early Imp.
Ptol./Early Imp.
Ptolemaic
Rom. or Hell.
Rom.-Byz.
Seleukos II., um 240 v.Chr.
Seleukos II., um 240 v.Chr.
Septimius Severus
Septimius Severus (or later)
Severus-Gallienus
Spätzeit
Theb
Trajan, or sh. bef.
Trajanic or later
Trajanic-Antonine
Turkish
V/init IVa
V/init IVa
V/init IVa
V/init IVa
VIÍinit VIa
VIÍinit VIa
VÍinit Va
VÍinit Va
XIV/init XVp
XIV/init XVp
Zeit Hadrians / erheblich fru
Augustus od. Tiberius
Augustus, vor 2 v.Chr.
Augustus, vor 2 v.Chr.
[(17-)14 v.Chr.]
[(17-)14 v.Chr.]
[18 n.Chr. od. 1 v.-4 n.Chr.]
[18 n.Chr. od. 1 v.-4 n.Chr.]
[18 n.Chr.]
[18 n.Chr.]
[29 v.Chr.]
[29 v.Chr.]
[Wiligelmo]
[ant.]
[antique]
[forgery]
[frühe Kaiserzeit]
[modern forgery]
[unknown]
a IÍinit IIIp
a IÍinit IIIp
ab 1.Jh.n.Chr.
ab 1.Jh.n.Chr.
ac
adv. Imp. (aft. 212 ac)
adv. Imp. (aft. 212 ac)
adv. Imp. (bef. 212 ac)
adv. Imp. (bef. 212 ac)
aet Hell/aet Rom
aet Hell/aet Rom
aet Imp/aet Chr
aet Imp/aet Chr
aet Rom antiq
aet Rom antiq
aet Romana
aet Romana
aet Tráp post
aet Tráp post
aet Ves-aet Dom
aet Ves-aet Dom
aet chr
aet chr
aet imp inf
aet imp inf
aet incert
aet incert
aet rec
aet rec
aet tardae
aet tardae
aet. imp. Rom.
aet. imp. Rom.
aetate Romana
aetate Romana
aetatis infimae
aetatis infimae
ante Chr nat
ante Chr
archaisch
archaisch
archaischer Schriftcharakter
archaisches
augusteisch
augusteische Zeit
beg Rom imp
beg. Antonine
beg. I bc  46 bc
beg. I bc  46 bc
beg. Imp.
beg. Imp.
betw. Trajan  Severus
byzantisch
c 150-init IIIp
c 150-init IIIp
c 212p-med IIIp
c 212p-med IIIp
c fin IIÍinit IIa
c fin IIÍinit IIa
c.160 ac [II]
c.160 ac [II]
c.252/1  IV bc
c.252/1  IV bc
c.300-280  beg. II bc
c.300-280  beg. II bc
c.400 et I p
c.400 et I p
c.989 n.Chr.
c.989 n.Chr.
cAD 248 <hmu_discarded_form>III spc</hmu_discarded_form>
cAD 248 <hmu_discarded_form>III spc</hmu_discarded_form>
ca. 1. Hälfte 2. Jh. v.Chr.
ca. 1. Hälfte 2. Jh. v.Chr.
early Antonine
early Antonine or later
early Hadrianic
early medieval
end Hellenist.
end Ptol.()
end Ptol./Rom.
end Ptol./beg. Rom.
erste Kaiserzeit
etwa v. Anf. d. 2.Jhdts. n.Chr.
etwa v. Anf. d. 2.Jhdts. n.Chr.
fin IIa [K.116(74)]
fin IIa [K.116(74)]
fin IVa-c 250a
fin IVa-c 250a
fin IVa-c 280a
fin IVa-c 280a
fin Ia-c 50p
fin Ia-c 50p
fin aet Hell/Imp
fin aet Hell/Imp
fin aet Hell/init aet Imp
fin aet Hell/init aet Imp
fin aet Imp
fin aet Imp
fin aet Imp
fin aet Imp
forgery
forgerýmod.
fruhe bis mittlere Kaiserzeit
frühaugusteisch (vor 15 v.Chr.
frühaugusteisch (vor 15 v.Chr.
frühbyzantinisch
frühestens späthellenistisch
frühhellenistisch
frühhellenistisch
hellenistisch - spätrömisch
hellenistisch-frühe Kaiserzeit
hellenistisch/römisch
high Imp.
high Imp.
hohe Kaiserzeit
hohe hellenistische Zeit
imp Rom
imperial
init IIÍinit IIa
init IIÍinit IIa
init principat
init() aet Imp
init() aet Imp
kaiserzeitlich/spätrömisch
late
late Attic
late Class.
late Class.-Hell.
late Hadrianic
late Hadrianic or after
late Hadrianic or later
late Hadrianic-Antonine
late Hadrianic-early Antonine
late Ptol.
late Ptol.-early Rom.
late Rom.
late Roman
late Severan
late Severan or sh.aft.
late classic
late period
later Severan
later imperial
letztes Drittel 3.Jh.v.Chr. (wo
letztes Drittel 3.Jh.v.Chr. (wo
med Ia [K.87(14)]
med Ia [K.87(14)]
med V/init IVa
med V/init IVa
med./mod.
medieval
medieval
mid Byz
mid-III  250-200 bc
mid-III  250-200 bc
mittelhellenistisch
mittlere Kaiserzeit
mod.
nach 14 n.Chr
nach 14 n.Chr
nach 85 v.Chr. oder Zeit des Au
nach 85 v.Chr. oder Zeit des Au
noch Ende der Republik
noch hellenistisch
non post August
late Hadrianic
middle Antonine
poss. Antonine
poss. late Hadrianic
post Hadrian
post princ Aug
post-Byz
post-Hadrianic
1st half Antonine
1st half Antonine
2nd half Antonine
2nd half Antonine
early Antonine
late Hadrianic
middle Antonine
sh.aft. middle Antonine
relativ spät
romisch
römisch (Kaiserzeit)
römisch (eher spät)
römisch (nach 212 n.Chr.)
römisch (nach 212 n.Chr.)
römisch, christlich
römisch (nach 212 n.Chr.)
römisch (nach 212 n.Chr.)
s IV/init III
s IV/init III
spät
spätantik
spätantik
späte Republik oder fruhe Kais
spätere hellenistische Zeit
spätes 3. - 7. Jh. n. Chr.
spätes 3. - 7. Jh. n. Chr.
spätes 9./frühes 10.Jh.n.Chr
spätes 9./frühes 10.Jh.n.Chr
spätestens 1.Hälfte 1.Jh.n.Ch
spätestens 1.Hälfte 1.Jh.n.Ch
späthell. - frühe Kaiserzeit
späthellenistisch (od. später
späthellenistisch od. erste Ka
späthellenistisch od. frührö
späthellenistisch od. später
späthellenistisch oder erste K
späthellenistisch oder frühe
spätrömisch
temp Macedonica
tiberisch, um 20 n.Chr.
tiberisch, um 20 n.Chr.
traianisch-hadrianische Zeit
ult temp Romano
um 330 v.Chr. oder früher
um 330 v.Chr. oder früher
unter Augustus
unter NerváHadrian/Trajan
vermutlich frühe Kaiserzeit
wohl erste Kaiserzeit
wohl frühe Kaiserzeit
wohl frühe Kaiserzeit
wohl hellenistisch
wohl kaiserzeitlich
wohl noch 2.Jh.n.
wohl noch 2.Jh.n.
wohl noch hellenistisch
wohl noch römisch
ziemlich spät
zw. 1 v.Chr. und 4 n.Chr.
zw. 129 und 138 n.Chr.
zw. 129 und 138 n.Chr.
zw. 14 und 19 n.Chr.
zw. 14 und 19 n.Chr.
zw. 293 und 305 n.Chr.
zw. 293 und 305 n.Chr.
zw. 49 und 53 n.Chr.
zw. 49 und 53 n.Chr.
"""
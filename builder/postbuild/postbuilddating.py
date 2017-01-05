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

	:param date:
	:return:
	"""

	originaldate = date

	datemapper = {	
		'-IIIp': 250,
		'[unknown]': 1500,
		'1. Ha+lfte 4.Jh. v.Chr.': -375,
		'1. Jh. v.Chr.': -50,
		'1. Jh.n.Chr.': 50,
		'1. Jh. n.Chr.': 50,
		'1./2. Jh. n.Chr.': 100,
		'1.Jh.n.Chr.': 50,
		'1.Jh.v.Chr.': -50,
		'1st ac': 50,
		'1st bc': -50,
		'1st half Antonine': 155,
		'1st/2nd ac': 100,
		'2. Ha+lfte 1. Jh. n.Chr.': 75,
		'2. Jh. v.Chr.': -150,
		'2. Jhdt. n.Chr.': 150,
		'2./1.Jh.n.Chr.': 100,
		'2./1.Jh.v.Chr.': -100,
		'2./3.Jh.n.Chr.': 200,
		'2.Jh.n.Chr.': 150,
		'2.Jh.v.Chr.': -150,
		'2nd ac': 150,
		'2nd bc': -150,
		'2nd/1st': -100,
		'2nd/3rd ac': 200,
		'3. Jh. v.Chr.': -250,
		'3.Jh.n.Chr.': 250,
		'3.Jh.v.Chr.': -250,
		'3rd ac': 250,
		'3rd bc': -250,
		'3rd/2nd bc': -200,
		'3rd/4th ac': 300,
		'4. Jh. v.Chr.': -350,
		'4. Viertel 2. Jh. v.Chr.': -110,
		'4.Jh.n.Chr.': 350,
		'4.Jh.v.Chr.': -350,
		'4th ac': 350,
		'4th bc': -350,
		'4th/3rd bc': -300,
		'4th/3rd': -300,
		'5.Jh.n.Chr.': 450,
		'5.Jh.v.Chr.': -450,
		'5th ac': 450,
		'5th bc': -450,
		'5th c. bc': -450,
		'5th/6th ac': 500,
		'6.Jh.n.Chr.': 550,
		'6.Jh.v.Chr.': -550,
		'6./7.Jh.n.Chr.': 600,
		'6th ac': 550,
		'6th bc': -550,
		'7.Jh.n.Chr.': 650,
		'7.Jh.v.Chr.': -650,
		'7th ac': 650,
		'7th bc': -650,
		'7th/8th ac': 700,
		'8.Jh.n.Chr.': 750,
		'8th ac': 750,
		'8th bc': -750,
		'9.Jh.n.Chr.': 850,
		'9th ac': 850,
		'10./11.Jh.n.Chr.': 1000,
		'10th': 950,
		'11th': 1050,
		'12th': 1150,
		'13th': 1250,
		'14th': 1350,
		'10th ac': 950,
		'11th ac': 1050,
		'12th ac': 1150,
		'13th ac': 1250,
		'14th ac': 1350,
		'15th ac': 1450,
		'adv. Imp.': 400,
		'aet Ant': 145,
		'aet Aug': 1,
		'aet Aug/aet Tib': 15,
		'aet Aug/Claud': 30,
		'aet Aug/Tib': 15,
		'aet Augusti': 1,
		'aet Aur': 170,
		'aet Byz': 700,
		'Early Byz': 400,
		'Middle Byz': 700,
		'Late Byz': 1200,
		'aet Carac': 205,
		'aet Chr': 400,
		'aet Claud': 50,
		'aet Commod': 185,
		'aet Dioc': 290,
		'aet Dom': 90,
		'aet Flav': 85,
		'aet Had': 125,
		'aet Had/Aur': 150,
		'aet Hadriani': 125,
		'aet Hell tard': -1,
		'aet Hell': -250,
		'aet Imp tard': 400,
		'aet imp': 200,
		'aet Imp': 200,
		'Early Imp.': 100,
		'aet inferior': 1200,
		'aet Nero': 60,
		'aet Nerv': 97,
		'aet Rom tard': 100,
		'aet Rom': 50,
		'aet tard': 1000,
		'aet Tib': 25,
		'aet Tib/Gaii': 35,
		'aet Tit': 80,
		'aet Tra': 105,
		'aet Tra/aet Had': 115,
		'aet Ves': 70,
		'aet Ves/aet Dom': 80,
		'aet Ves/Dom': 80,
		'aetat Augusti': 1,
		'aetate Augusti': 1,
		'aetate Hadriani': 125,
		'archaic': -700,
		'Archaic': -700,
		'August': 1,
		'Augustan': 1,
		'Augustus': 1,
		'Byz.': 700,
		'Byz': 700,
		'Byzantine': 700,
		'byzantinisch': 700,
		'byzantinische Zeit': 700,
		'Chr.': 400,
		'Christ.': 400,
		'Classical': -400,
		'aet Christ': 400,
		'Constantine': 315,
		'Carolingian': 775,
		'date': 1500,
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
		'Hell.': -250,
		'Hellenistic': -250,
		'hellenistisch - spa+tro+misch': 200,
		'hellenistisch-fru+he Kaiserzeit': -100,
		'hellenistisch': -250,
		'hristlich': 400, # the 'c' will have been chopped
		'I a': -50,
		'I a/I p': 1,
		'I ac': 50,
		'I bc-I ac': 1,
		'I bc': -50,
		'I p': 50,
		'I sac-Ip': 1,
		'I sac/Ip': 1,
		'I spc': 1,
		'I-II ac': 100,
		'I-II': 100,
		'I-IIa': -100,
		'I-IIIp': 111,
		'I-IIp': 100,
		'I-Vp': 250,
		'I/II ac': 100,
		'I/II': 100,
		'I/IIa': -100,
		'I/IIp': 100,
		'Ia-Ip': 1,
		'Ia': -50,
		'Ia/aet Imp': 25,
		'Ia/Ip': 1,
		'II a': -150,
		'II ac': 150,
		'II bc': -150,
		'II p': 150,
		'II spc ': 150,
		'II spc': 50,
		'II-beg.III ac': 280,
		'II-I a': -100,
		'II-I bc': -100,
		'II-I sac': -100,
		'II-I': -100,
		'II-III ac': 200,
		'II-III': 200,
		'II-IIIp': 200,
		'II-IVp': 300,
		'II/I bc': -100,
		'II/I': -100,
		'II/Ia': -100,
		'II/III ac': 200,
		'II/III spcs': 200,
		'II/III': 200,
		'II/IIIp': 200,
		'II/IV': 300,
		'IIa': -150,
		'III a': -250,
		'III ac': 250,
		'III bc': -250,
		'III p': 250,
		'III sac': -250,
		'III spc': 250,
		'III-Ia': -111,
		'III-II a': -200,
		'III-II bc': -200,
		'III-II': -200,
		'III-IV': 300,
		'III/IV': 300,
		'III/IV ac': 300,
		'III-IVp': 300,
		'III-p': 250,
		'III/II': -200,
		'III/II/Ia': -150,
		'III/IIa': -200,
		'III/IVp': 300,
		'III/VI': 450,
		'IIIa': -250,
		'IIIp': 250,
		'IIp': 150,
		'Imp.': 200,
		'Imp': 200,
		'imperial': 200,
		'Imperial': 200,
		'init aet Hell': -310,
		'Ip': 50,
		'Ip/IIp': 100,
		'IV a': -350,
		'IV ac': 350,
		'IV bc': -350,
		'IV p': 350,
		'IV spc': 350,
		'IV-Ia': -200,
		'IV-IIa': -200,
		'IV-III bc': -300,
		'IV-III': -300,
		'IV-III/II bc': -275,
		'IV-V ac': 400,
		'IV-V': 400,
		'IV-VIp': 450,
		'IV-Vp': 400,
		'IV/III bc': -300,
		'IV/III': -300,
		'IV/IIIa': -300,
		'IV/V': 400,
		'IV/Vp': 400,
		'IVa': -350,
		'IVp': 350,
		'Julio-Claudian': 25,
		'Kaiserzeit': 100,
		'kaiserzeitlich': 100,
		'late archaic': -600,
		'Late Archaic': -600,
		'Late Hell.-Early Imp.': -15,
		'Late Hell.': -1,
		'late Hellenist.': -1,
		'Late Imp.': 250,
		'late Imp.': 400,
		'Late Ptol.': -50,
		'letztes Viertel 1. Jh.v.Chr.': -15,
		'Marcus Aurelius': 170,
		'Merov.': 600,
		'med.': 1100,
		'Nero': 60,
		'pre-Ptol.': -333,
		'Ptol.': -100,
		'Ptol./Rom.': -20,
		'ro+misch': 50,
		'Rom.': 50,
		'Rom./Byz.': 600,
		'Rom': 50,
		'Roman Imp': 200,
		'Roman': 50,
		'Romanesque': 1150,
		'spa+thell. - fru+he Kaiserzeit': -1,
		'spa+thellenistisch': -25,
		'spc I-II': 100,
		'spc II-III': 200,
		'spc II': 150,
		'Tiberius': 25,
		'Titus': 80,
		'Trajan': 105,
		'Trajan/Hadrian': 115,
		'Trajanic': 105,
		'V a': -450,
		'V ac': 450,
		'V bc': -450,
		'V p': 450,
		'V-IV bc': -400,
		'V-IVa': -400,
		'V/IV': -400,
		'V-VI': 500,
		'V-VIp': 500,
		'V/IV bc': -400,
		'V/IVa': -400,
		'V/VIp': 500,
		'V/VII spc': 550,
		'Va': -450,
		'Vespasian': 70,
		'VI ac': 550,
		'VI bc': -550,
		'VI-Ia': -300,
		'VI-IVa': -450,
		'VI-VII': 600,
		'VI-VIIIp': 600,
		'VI-VIIp': 600,
		'VI/V bc': -500,
		'VI/V': -500,
		'VI/Va': -500,
		'VI-V': -500,
		'VI/VIIp': 600,
		'VIa': -550,
		'VII ac': -650,
		'VII-VIIIp': 700,
		'VII-VIIIspc': -700,
		'VII/VIIIp': 700,
		'VIIa': -650,
		'VIII p': 750,
		'VIIIa': -750,
		'VIIIp': 750,
		'VIIp': 650,
		'VIp': 550,
		'Vp': 450,
		'XIp': 1050,
		'XVII-XIX ac': 1800,
	}

	german = re.compile(r'(n\.|v\.Chr\.)')
	arabic = re.compile(r'\d')
	ordinal = re.compile(r'((\d)st|(\d)nd|(\d)rd|(\d{1,})th)')
	roman = re.compile(r'[IVX]')
	ages = re.compile(r'aet')
	digits = re.compile(r'\d')

	gdate = -9999
	ncdate = -9999
	rdate = -9999

	if re.search(german, date) is not None and secondpass == False:
		gdate = germandate(date)
	elif re.search(arabic, date) is not None and re.search(ordinal,date) is not None and secondpass == False:
		ncdate = numberedcenturydate(date, ordinal)
	elif re.search(roman, date) is not None and secondpass == False:
		rdate = romannumeraldate(date)
	elif re.search(ages, date) is not None and secondpass == False:
		adate = aetatesdates(date)
	elif re.search(digits, date) is not None and secondpass == False:
		ddate = numericdate(date)

	# at this point a grab bag should remain: 'späthellenistisch', etc.


	waffles = re.compile(r'(prob\. |\(or later\)|\sor\slater$|\[o\.s\.\]|, or sh\. bef\.(\s|$))')
	uselessspans = re.compile(r'(middle\s|c\.med s\s|c\.\smid\.\s|med\s|mid-|med\ss\s|mid\s|mittlere |Mitte |Zeit des |erste |Erste )')
	approx = re.compile(r'^(um\s|prob\s|poss\.\s|non post |ante fere |term\.post |ca\.\s|\.|)(\s)')
	badslashing = re.compile(r'/(antea|postea|paullo |fru+hestens |wohl noch |vielleicht noch |kaum spa+ter als |in\s)')
	superfluous = re.compile(r'(<hmu_discarded_form>.*?$|^(wohl|Schicht)\s|\[K\.\d{1,}\]|^(s\s|-))')
	unpunctuate = re.compile(r'(\?|\(\?\)|\[|\]|\'|⟪|⟫)')
	ceispositive = re.compile(r'^(AD c |AD -|-cAD|Ad |cAD )')


	# drop things that will only confuse the issue
	date = re.sub(waffles,'',date)
	date = re.sub(ceispositive,'',date)
	date = re.sub(superfluous,'',date)
	date = re.sub(uselessspans,'', date)
	# 'unpunctuate' needs to come after 'superfluous'
	date = re.sub(unpunctuate, '', date)
	date = re.sub(approx,'',date)
	date = re.sub(badslashing, '', date)
	# reformat / preserve a match
	date = re.sub(r'^c.(\d)', r'\1', date)
	date = re.sub(r'^\[(\d{1,} ac)\]', r'\1', date)
	date = re.sub(r'\[(\d{1,})\sac\]',r'\1', date)
	date = re.sub(r'p c\.(\d)',r'\1',date)
	date = re.sub(r' od(er|\.) eher','/',date)
	date = re.sub(r'(.*?)/⟪\d⟫',r'\1',date)
	# swap papyrus BCE info format for one of the inscription BCE info formats
	date = re.sub(r'\sspc$','p', date)
	date = re.sub(r'\ssac$', 'a', date)
	date = re.sub(r'^c([IV])',r'\1',date)


	fudge = 0
	# look out for order of regex: 'ante med' should come before 'ante', etc
	# starts have to come before negmiddles bec of 'bef. mid.' vs. 'sh. bef. mid.'
	starts = re.compile(r'^(c\.init\s|init\ss\s|init/med |init\s|early\s|1\.Ha+lfte|bef\. mid\.\s|beg\.\s|beg\.|beg\s|before\s|in\ss\s|in\s|Anf\.\s|fru+hes )')
	negmiddles = re.compile(r'^(ante fin|ante med|ante|sh\. bef\.|sh\.bef\.|bef\.|ante c|a|fru+hestens)\s')
	shafters = re.compile(r'^(p\spost\sc\s|p\spost\s|sh\. aft\. mid\.\s|sh\.aft\.\s|1\.Viertel\s)')
	shbefores = re.compile(r'^(paullo ante |p ante c |p ante )')
	afters = re.compile(r'^(sh\. aft\.|after|aft\. mid\.|aft\. c.\(\s\)|aft\.|post med s|post c|post|p|2\.Ha+lfte des|med/fin)\s')
	ends = re.compile(r'^(c\.fin\ss\s|fin\ss\s|fin\s|ex s\s|2\.Ha+lfte|end\s|late\s|c\.fin\ss|Ende des |Ende\s|letztes Drittel\s|later\s)')

	if re.search(starts, date) is not None:
		date = re.sub(starts, '', date)
		fudge = -25
	if re.search(negmiddles, date) is not None:
		date = re.sub(negmiddles, '', date)
		fudge = -20
	if re.search(shafters, date) is not None:
		date = re.sub(shafters, '', date)
		fudge = 10
	if re.search(shbefores, date) is not None:
		date = re.sub(shbefores,'',date)
		fudge = -10
	if re.search(afters, date) is not None:
		date = re.sub(afters, '', date)
		fudge = 20
	if re.search(ends, date) is not None:
		date = re.sub(ends, '', date)
		fudge = 25

	# one last blast (or two)
	date = re.sub(r'^s\s','',date)
	date = re.sub(r'/in\s|/fin\s','/',date)

	# elif
	if date in datemapper:
		numericaldate = datemapper[date]
	else:
		# what is one supposed to say about: "193-211, 223-235 or 244-279 ac"?
		# let's just go with our last value (esp. since the BCE info is probably there and only there)
		if len(date.split(',')) > 1:
			date = date.split(',')
			last = len(date) - 1
			date = date[last]
		if len(date.split(' or ')) > 1:
			date = date.split(' or ')
			last = len(date) - 1
			date = date[last]
		if len(date.split(' vel ')) > 1:
			date = date.split(' vel ')
			last = len(date) - 1
			date = date[last]

		modifier = 1
		# '161 ac', '185-170/69 bc'
		BCE = re.compile(r'(\sbc|\sBC|^BC\s|v\.Chr\.)')
		CE = re.compile(r'(\sac|\sAD|^AD\s|n\.Chr\.)')
		if re.search(BCE, date) is not None:
			modifier = -1
		date = re.sub(BCE,'',date)
		date = re.sub(CE, '', date)

		# '357a', '550p'
		BCE = re.compile(r'\da$')
		if re.search(BCE, date) is not None:
			modifier = -1
			date = re.sub(r'a$','',date)
		if re.search(r'\dp$', date) is not None:
			date = re.sub(r'p$', '', date)

		# '357 a', '550 p'
		BCE = re.compile(r'\d\sa$')
		if re.search(BCE, date) is not None:
			modifier = -1
			date = re.sub(r'\sa$','',date)
		if re.search(r'\d\sp$', date) is not None:
			date = re.sub(r'\sp$', '', date)

		# clear out things we won'd use from here on out
		date = re.sub(r'\sbc|\sBC\sac|\sAD','', date)
		# '44/45' ==> '45'
		splityears = re.compile(r'(\d{1,})(/\d{1,})(.*?)')
		if re.search(splityears, date) is not None:
			split = re.search(splityears, date)
			date = split.group(1)
			if int(date[-1]) > int(split.group(2)[1:]):
				# 332/1 is BCE
				modifier = -1
			if int(date[-1]) == 0 and int(split.group(2)[1:]) != 1:
				# 330/1 is CE
				# 330/29 is BCE
				modifier = -1

		if len(date.split('-')) > 1:
			# take the middle of any range you find
			halves = date.split('-')
			first = halves[0]
			second = halves[1]
			if re.search(r'\d', first) is not None and re.search(r'\d', second) is not None:
				first = re.sub(r'\D','',first)
				second = re.sub(r'\D', '', second)
				# note the problem with 100-15 and/or 75-6
				if len(first) > len(second):
					difference = len(first) - len(second)
					second = first[0:difference]+second[(-1*len(second)):]
				first = int(first)
				second = int(second)
				numericaldate = (first + second)/2 * modifier + (fudge * modifier)
			elif re.search(r'\d', first) is not None:
				# you'll get here with something like '172- BC?'
				first = re.sub(r'\D','',first)
				numericaldate = int(first) * modifier + (fudge * modifier)
			else:
				numericaldate = 9999
		elif re.search(r'^\d{1,}\s{1,}\d{1,}$', date) is not None:
			# '86  88'
			halves = date.split(' ')
			first = halves[0]
			numericaldate = int(first) * modifier + (fudge * modifier)
		elif len(date.split(';')) > 1:
			halves = date.split(';')
			first = halves[0]
			second = halves[1]
			if re.search(r'\d', first) is not None and re.search(r'\d', second) is not None:
				first = re.sub(r'\D','',first)
				second = re.sub(r'\D', '', second)
				# note the problem with 100-15 and/or 75-6
				if len(first) > len(second):
					difference = len(first) - len(second)
					second = first[0:difference]+second[(-1*len(second)):]
				first = int(first)
				second = int(second)
				numericaldate = (first + second)/2 * modifier + (fudge * modifier)
			elif re.search(r'\d', first) is not None:
				# you'll get here with something like '172- BC?'
				first = re.sub(r'\D','',first)
				numericaldate = int(first) * modifier + (fudge * modifier)
			else:
				numericaldate = 9000
		elif re.search(r'\d', date) is not None:
			# do me late/last
			# we're just a collection of digits? '47', vel sim?
			try:
				numericaldate = int(date) * modifier + fudge
			except:
				# oops: there are still characters left but it was not in datemapper{}
				numericaldate = 8888
		else:
			numericaldate = 7777

	if numericaldate > 2000:
		if originaldate != '?' and originaldate != '[unknown]':
			# print('\tunparseable date:',originaldate)
			pass

	if gdate != -9999:
		numericaldate = gdate
	elif ncdate != -9999:
		numericaldate = ncdate
	elif rdate != -9999:
		numericaldate = rdate
	else:
		# for debugging
		#numericaldate = -9999
		pass

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
	century = re.compile(r'(Jh\.| Jhdts\. |Jhdt\. )')
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
			print('failed',original)
			numericaldate = -9999
		return numericaldate
	elif re.search(r'zw.',stringdate) is not None:
		parts = re.search(r'^zw.(\d{1,})\s{0,1}und(\d{1,})',stringdate)
		if re.search(r'v\.Chr\.', stringdate) is not None:
			modifier = -1
			fudge += 100
		one = int(parts.group(1))
		two = int(parts.group(2))
		numericaldate = (((-1 * one ) + (two )) / 2) * modifier + fudge
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

	dontcare = re.compile(r'^(prob\. |perh\. |c |c\.|c. )')
	subtract = re.compile(r'^(not before |before )')
	tinysubtract = re.compile(r'^(beg\. |beg\.|beg |earlier |early |in |sh\. bef\. mid\. |b:mid- )')
	tinyadd = re.compile(r'^(end |later |late |ex |sh\. aft\. mid\. )')
	add = re.compile(r' or later$')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)

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
	elif re.search(r'ac$',stringdate) is None:
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
	# subtract = re.compile()
	tinysubtract = re.compile(r'(^(ante med |ante md |beg\. |beg |a med |early |init/med |init |latest )| p prior$|/init )')
	bigadd = re.compile(r'^(post fin s|post )')
	add = re.compile(r'(^(ante fin |ant fin|ex s |ex |end |med/fin |late |post med s )|(/postea|/paullo post)$)')
	splitter = re.compile(r'([IVX]{1,})[-/]([IVX]{1,})')

	stringdate = re.sub(dontcare, '', stringdate)
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


def aetatesdates(stringdate):

	return -9999


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
	midcentury = -50
	fudge = 0
	numericaldate = -9999

	dontcare = re.compile(r'^(p c |p c\.|p |perh c |poss\. |prob\. c\.|prob\. |cAD |AD |c\. |c\.|c )')
	# subtract = re.compile()
	tinysubtract = re.compile(r'^(sh\. bef\. |sh\.bef\. |before |bef\. )')
	littleadd = re.compile(r'^(sh\. aft\. c\.|sh\. aft\. |sh\.aft\. |sh\.aft\.|sht\. after )')
	add = re.compile(r'')
	splitter = re.compile(r'')
	nearestdecade = re.compile(r'^(post |ante )')
	fix = re.compile(r'⟪⟫\[\]')

	stringdate = re.sub(dontcare, '', stringdate)
	stringdate = re.sub(r'\?', '', stringdate)
	stringdate = re.sub(fix, '', stringdate)

	if re.search(r'( bc$|bc$| BC$| a$|a$)', stringdate) is not None:
		modifier = -1

	if re.search(r'(BC.*?[/-].*?pc|bc.*?[/-].*?ac)$',original) is not None:
		# I sac - I spc
		numerals = re.findall(r'[IVX]{1,}',original)
		digits = [map[n] for n in numerals]
		digits[0] = digits[0] * -1
		numericaldate = (((digits[0] + digits[1]) / 2) * modifier) + fudge

	return -9999
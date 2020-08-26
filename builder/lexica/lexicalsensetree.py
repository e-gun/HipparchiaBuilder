# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from builder.lexica.fixtranslationtagging import latintranslationtagrepairs, greektranslationtagrepairs


def findprimarysenses(entrybody: str, minimumcomplexity=2, caponsensestoreturn=4, language='greek') -> list:
	"""

	figure out what the key meanings of an entry are by scanning an entry's hierarchy

	ἔχω is a great test case: 50+ meanings

	<sense id="n60245.0" n="A" level="1" opt="n">
	<sense n="2" id="n60245.1" level="3" opt="n">
	<sense n="3" id="n60245.2" level="3" opt="n">
	...

	sensedict[int(s[1])] = {'label': s[0], 'level': int(s[2]), 'trans': s[3], 'compositelabel': str()}

	:param entrybody:
	:return:
	"""

	if language == 'greek':
		transfinder = re.compile(r'<trans.*?>(.*?)</trans>')
	elif language == 'latin':
		transfinder = re.compile(r'<hi rend="ital".*?>(.*?)</hi>')
	else:
		return list()

	nontransfinder = re.compile(r'(.*?)<bibl')
	sensedict = hierarchicalsensedict(generatesensedict(entrybody, language=language))

	# the latin dictionary's first translation of its first "sense" tends to be morphology notes
	# and the sense tree is warped
	# 0 1 I
	# 1 1 I
	# 2 1 II
	# 3 2 II.A

	try:
		if sensedict[0]['compositelabel'] == sensedict[1]['compositelabel']:
			# sensedict.pop(0)
			sensedict[0]['label'] = 'A'
	except KeyError:
		pass

	firsts = [s for s in sensedict if sensedict[s]['level'] == 1]
	seconds = [s for s in sensedict if sensedict[s]['level'] == 2]
	thirds = [s for s in sensedict if sensedict[s]['level'] == 3]

	# for item in [firsts, seconds, thirds]:
	# 	print(item)

	probing = firsts

	if len(firsts) < minimumcomplexity and len(seconds) < minimumcomplexity and len(thirds) < minimumcomplexity:
		# there is not an interesting hierarchy...
		return list()

	itemone = 0
	if len(firsts) < minimumcomplexity and len(seconds) >= minimumcomplexity:
		try:
			sensedict[0]['label'] = 'A.I'
		except KeyError:
			try:
				sensedict[1]['label'] = 'A.I'
				itemone = 1
			except KeyError:
				return list()
		probing = [itemone] + seconds
	elif len(seconds) < 2 and len(thirds) >= minimumcomplexity:
		try:
			sensedict[0]['label'] = 'I.1'
		except KeyError:
			try:
				sensedict[1]['label'] = 'I.1'
				itemone = 1
			except KeyError:
				return list()
		probing = [itemone] + thirds

	headings = list()

	nonsense = {'Act', 'Adj', 'Nom', 'Prep', 'A', 'Ab', 'Abl', 'Absol', 'Acc. respect.',
	            'Dat', 'Dim', 'Fem', 'Fin', 'Fin.', 'Fut', 'Gen', 'Gen.  plur.', 'Imp',
	            'Inf', 'Init', 'Masc', 'Nom', 'Num', 'Of', 'Part', 'Patr', 'Perf', 'Plur',
	            'Prep', 'Pres', 'Subst', 'Sup', 'Sync', 'Temp', 'V', 'Verb', 'Voc', 'act',
	            'adj', 'nom', 'prep', 'a', 'ab', 'abl', 'absol', 'acc. respect.', 'dat',
	            'dim', 'fem', 'fin', 'fin.', 'fut', 'gen', 'gen. plur.', 'imp', 'inf',
	            'init', 'masc', 'nom', 'num', 'of', 'part', 'patr', 'perf', 'plur', 'prep',
	            'pres', 'subst', 'sup', 'sync', 'temp', 'v', 'verb', 'voc', 'part. perf.',
	            'v. desid. a.', 'adv', 'pron', 'fem.', 'masc.', 'infra', 'neutr.', 'Neutr.',
	            'neutr', 'Neutr', 'a.', 'Prop', 'prop', 'Plur.', 'plur.'}

	for p in probing:
		thistrans = sensedict[p]['trans']
		alltrans = re.findall(transfinder, thistrans)
		alltrans = [a for a in alltrans if a not in nonsense]
		try:
			toptrans = alltrans[0]
		except IndexError:
			toptrans = str()

		if not toptrans:
			try:
				toptrans = re.search(nontransfinder, thistrans).group(1)
			except AttributeError:
				# AttributeError: 'NoneType' object has no attribute 'group'
				toptrans = str()
		toptrans = toptrans.strip()
		toptrans = re.sub(r'[;,:]$', str(), toptrans)
		# there might be two bad chars at the end...
		toptrans = re.sub(r'[;,:]$', str(), toptrans)
		# headings.append('{a}. {b}'.format(a=sensedict[p]['compositelabel'], b=toptrans))
		if toptrans and not re.search(r'^<usg type="style" opt="n">', toptrans):
			headings.append([sensedict[p]['label'], toptrans])

	headings = ['{x}. {y}'.format(x=h[0], y=h[1]) for h in headings]

	if len(headings) > caponsensestoreturn:
		headings = headings[:caponsensestoreturn] + ['...']

	headings = [h.strip() for h in headings if h]
	headings = [h for h in headings if h]

	if len(headings) > 1 and headings[0] == headings[1]:
		headings = headings[1:]

	# try:
	# 	print(headings[0])
	# except:
	# 	pass

	# next happens later...
	# headings = '; '.join(headings)

	return headings


def generatesensedict(entrybody: str, language='greek') -> dict:
	"""

	organize the senses in a preliminary manner

	:param entrybody:
	:return:
	"""

	#  you can get these "firsts" internally, too; but then the whole entry is regular?
	firstsense = re.compile(r'<sense id=".*?\.(\d+)" n="(.*?)" level="(.*?)" opt="[ny]">(.*?)</sense>')
	sensefinder = re.compile(r'<sense n="(.*?)" id=".*?\.(\d+)" level="(.*?)" opt="[ny]">(.*?)</sense>')

	if language == 'greek':
		entrybody = greektranslationtagrepairs(entrybody)
	elif language == 'latin':
		entrybody = latintranslationtagrepairs(entrybody)

	fs = re.findall(firstsense, entrybody)
	if fs:
		fs = [(s[1], s[0], s[2], s[3]) for s in fs]

	ss = re.findall(sensefinder, entrybody)

	# avoid dupes up front if you are at risk of them
	if fs and ss and fs == ss[0]:
		allsenses = ss
	else:
		allsenses = fs + ss

	# ('A', '1', '1', ' (stuff) ')
	# ('I', '2', '2', ' (stuff) ')
	# ('3', '5', '3', ' (stuff) ')
	# ('4', '6', '3', ' (stuff) ')

	sensedict = dict()
	for s in allsenses:
		try:
			sensedict[int(s[1])] = {'label': s[0], 'level': int(s[2]), 'trans': s[3], 'compositelabel': str()}
		except ValueError:
			# ValueError: invalid literal for int() with base 10: 'A'
			# somebody has irregular tags...
			# print('problem at', s)
			return dict()

	return sensedict


def hierarchicalsensedict(sensedict: dict) -> dict:
	"""

	ONLY WORKS FOR GREEK ATM; LATIN IS WONKY

	organize this: A.II.3...

	this means filling out the 'compositelabel' bit.

	sensedict[int(s[1])] = {'label': s[0], 'level': int(s[2]), 'trans': s[3], 'compositelabel': str()}

	not really using this at the moment, but it should probably move into a column in 'language_dictionary'

	the old 'translations' columns can't really be overwritten because it is used for reverse lookups

	this material could/should be pickled into something that can become a HipparchiaServer dbSenseObject on the other end

	:param sensedict:
	:return:
	"""

	tops = [s for s in sensedict if sensedict[s]['level'] == 1]
	seconds = [s for s in sensedict if sensedict[s]['level'] == 2]
	thirds = [s for s in sensedict if sensedict[s]['level'] == 3]
	fourths = [s for s in sensedict if sensedict[s]['level'] == 4]
	fifths = [s for s in sensedict if sensedict[s]['level'] == 5]

	# values = [[str(), str(), str(), str(), str()] for _ in range(len(sensedict))]
	valuesdict = {s: [str(), str(), str(), str(), str()] for s in sensedict}

	iterations = [(0, tops), (1, seconds), (2, thirds), (3, fourths), (4, fifths)]

	for i in iterations:
		valuesdict = arraypaddinghelper(i[0], i[1], valuesdict, sensedict)

	# there is a problem at top-level transitions
	# 35 : A.III.2
	# 36 : A.IV
	# 37 : B
	# 38 : B.IV.2
	# 40 : B.IV.3

	# firsts [1, 37, 51]
	# seconds [2, 17, 33, 36, 42, 45, 49, 57, 58, 60, 61]

	tofix = tops[1:]
	ranges = list()
	for r in range(len(seconds)):
		try:
			ranges.append(range(seconds[r], seconds[r+1]))
		except IndexError:
			# went past end
			pass
		ranges = [list(r) for r in ranges]

	for t in tofix:
		for r in ranges:
			if t in r:
				for item in r:
					if item > t:
						try:
							valuesdict[item][1] = 'I'
						except KeyError:
							# a missing value...
							pass

	for v in valuesdict:
		labellength = sensedict[v]['level']
		valuestouse = valuesdict[v][:labellength]
		sensedict[v]['compositelabel'] = '.'.join(valuestouse)
		# print(v, ':', sensedict[v]['compositelabel'])

	return sensedict


def arraypaddinghelper(arraydepth, topslist, valuesdict, sensedict) -> list:
	"""

	avoid duplicate code... DRY...

	:param variablestuple:
	:param valuesarray:
	:param sensedict:
	:return:
	"""

	try:
		label = sensedict[topslist[0]]['label']
	except IndexError:
		# descended too deep
		return valuesdict

	for v in valuesdict:
		if v in topslist:
			label = sensedict[v]['label']
		valuesdict[v][arraydepth] = label

	return valuesdict

# test = """
# <orth extent="full" lang="la" opt="n">flābellum</orth>, <itype opt="n">i</itype>, <gen opt="n">n.</gen> <lbl opt="n">dim.</lbl> <etym opt="n">flabrum</etym>, <sense id="n18263.0" n="I" level="1" opt="n"><hi rend="ital">a smali fan or fly-flap</hi>.</hi> </sense><sense id="n18263.1" n="I" level="1" opt="n"> <usg type="style" opt="n">Lit.</usg>: <cit><quote lang="la">cape hoc flabellum, et ventulum huic sic facito,</quote> <bibl n="Perseus:abo:phi,0134,003:595" class="rewritten" default="NO" valid="yes"><author>Ter.</author> Eun. 595</bibl></cit>; <bibl default="NO">50</bibl>; <bibl n="Perseus:abo:phi,1294,002:3:82:10" class="rewritten" default="NO"><author>Mart.</author> 3, 82, 10</bibl>; <cit><quote lang="la">for this a peacock's tail was used,</quote> <bibl n="Perseus:abo:phi,0620,001:2:24" default="NO" class="rewritten"><author>Prop.</author> 2, 24</bibl></cit> (3, 18), 11; <bibl default="NO"><author>Hier.</author> Ep. 27, 13</bibl>.—* </sense><sense id="n18263.2" n="II" level="1" opt="n"> <usg type="style" opt="n">Trop.</usg>: <cit><quote lang="la">cujus lingua quasi flabello seditionis, illa tum est egentium concio ventilata,</quote> <trans opt="n"><tr opt="n">an exciter</tr>,</trans> <bibl default="NO"><author>Cic.</author> Fl. 23, 54</bibl></cit>.</sense>
# (1 row)"""
# # from builder.lexica.testentries import testh as test
#
# if re.search(r'[a-z]', test):
# 	l = 'latin'
# else:
# 	l = 'greek'
#
# x = findprimarysenses(test, language=l)
# print(x)
#
# xd = hierarchicalsensedict(generatesensedict(test))
# for x in xd:
# 	print(x, xd[x]['level'], xd[x]['compositelabel'])
#
# print(xd)

# sd = hierarchicalsensedict(generatesensedict(test))
#
# toptwo = [sd[s]['compositelabel'] for s in sd if sd[s]['level'] == 2]
#
# print(toptwo)
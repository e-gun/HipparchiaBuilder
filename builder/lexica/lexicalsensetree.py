# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from builder.lexica.fixtranslationtagging import latintranslationtagrepairs, greektranslationtagrepairs
from builder.lexica.falsepositives import nonsense, falseheads


def findprimarysenses(entrybody: str, minimumcomplexity=2, caponsensestoreturn=4, language='greek') -> list:
	"""

	figure out what the key meanings of an entry are by scanning an entry's hierarchy

	ἔχω is a great test case: 50+ meanings

	<sense id="n60245.0" n="A" level="1" opt="n">
	<sense n="2" id="n60245.1" level="3" opt="n">
	<sense n="3" id="n60245.2" level="3" opt="n">
	...

	sensedict[int(s[1])] = {'label': s[0], 'level': int(s[2]), 'trans': s[3], 'compositelabel': str()}

	the latin dictionary's first translation of its first "sense" tends to be morphology notes
	and the sense tree is warped
	0 1 I
	1 1 I
	2 1 II
	3 2 II.A

	this requires the invocation of 'nonsense' as well as a variety of other dodges

	:param entrybody:
	:return:
	"""

	if language == 'greek':
		transfinder = re.compile(r'<trans.*?>(.*?)</trans>')
	elif language == 'latin':
		transfinder = re.compile(r'<hi rend="ital".*?>(.*?)</hi>')
		minimumcomplexity += 1
	else:
		return list()

	nontransfinder = re.compile(r'(.*?)<bibl')
	sensedict = hierarchicalsensedict(generatesensedict(entrybody, language=language))

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

	# the latin tree is also odd because I will have a dfn but II might only introduce A, B, C...
	if language == 'latin' and len(probing) < minimumcomplexity and len(seconds) >= minimumcomplexity:
		probing = probing + seconds

	headings = list()
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

		while re.search(r'[;,:.]$', toptrans):
			toptrans = re.sub(r'[;,:.]$', str(), toptrans)

		# need to redo this check because 'nontransfidner' may have been invoked
		if toptrans in nonsense:
			toptrans = str()

		for fh in falseheads:
			if re.search(fh, toptrans):
				toptrans = str()

		# headings.append('{a}. {b}'.format(a=sensedict[p]['compositelabel'], b=toptrans))
		if toptrans:
			headings.append([sensedict[p]['label'], toptrans])

	# drop sequential duplicates
	uniqueheadings = list()
	headings.reverse()

	while headings:
		h = headings.pop()
		try:
			if uniqueheadings[-1][1] != h[1]:
				uniqueheadings.append(h)
		except IndexError:
			uniqueheadings.append(h)

	# now you have your (mostly) unique headings...: format for output
	headings = ['{x}. {y}'.format(x=h[0], y=h[1]) for h in uniqueheadings]

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


# from builder.lexica.testentries import testm as test
#
# l = 'latin'
# # l = 'greek'
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
# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import configparser
import csv
import re

try:
	# python3
	import psycopg2
except ImportError:
	# pypy3
	# pypy3 support is EXPERIMENTAL (and unlikely to be actively pursued)
	import psycopg2cffi as psycopg2

from builder import file_io
from builder.parsers.regexsubstitutions import latindiacriticals
from builder.parsers.betacodeescapedcharacters import percentsubstitutes
from builder.parsers.greekcanonfunctions import loadgkcanon
from builder.dbinteraction.db import updatedbfromtemptable

config = configparser.ConfigParser()
config.read('config.ini')
tlg = config['io']['tlg']


def resetbininfo(relativepath, cursor, dbconnection):
	"""

	:param relativepath:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	print('resetting info from the .BIN files')

	bininfo = {
		'genre': 'LIST3CLA.BIN',
		'genre_clx': 'LIST3CLX.BIN',
		'recorded_date': 'LIST3DAT.BIN',
		'epithet': 'LIST3EPI.BIN',
		'gender': 'LIST3FEM.BIN',
		'location': 'LIST3GEO.BIN',
		'canon': 'DOCCAN2.TXT'
	}

	# relativepath = relativepath[:-3]
	genres = buildlabellist(relativepath + bininfo['genre_clx'])
	epithets = buildlabellist(relativepath + bininfo['epithet'])
	locations = buildlabellist(relativepath + bininfo['location'])
	canonfile = relativepath + bininfo['canon']
	dates = buildlabellist(relativepath + bininfo['recorded_date'])
	numdates = convertdatelist(dates)

	cleandates = {}
	for d in dates:
		newdate = re.sub(r'`', '', d)
		cleandates[newdate] = dates[d]

	wipegreekauthorcolumn('genres', cursor, dbconnection)
	# wipegreekauthorcolumn('epithet', cursor, dbconnection)
	wipegreekauthorcolumn('location', cursor, dbconnection)
	wipegreekauthorcolumn('recorded_date', cursor, dbconnection)
	wipegreekauthorcolumn('converted_date', cursor, dbconnection)

	print('\tloading new author column data')
	# dbloadlist(genres, 'genres', cursor, dbconnection)
	dbloadlist(epithets, 'genres', cursor, dbconnection)
	dbloadlist(locations, 'location', cursor, dbconnection)
	dbloadlist(cleandates, 'recorded_date', cursor, dbconnection)
	dbloadlist(numdates, 'converted_date', cursor, dbconnection)

	dbconnection.commit()

	# canoninfo: do this last so that you can reset shortname
	print('\treading canon file')
	loadgkcanon(canonfile)

	return


def npop(numbertopop, listtopop):
	ret = []
	for i in range(0, numbertopop):
		ret.append(listtopop.pop())

	return ret, listtopop


def listoflabels(rbl):
	rv = 999
	labels = []
	heads = []
	head, rbl = npop(4, rbl)
	while rv != 0:
		head, rbl = npop(4, rbl)
		rv = rbl.pop()
		string, rbl = npop(rv, rbl)
		string = intostring(string)
		labels.append(string)
		heads.append(head)

	return labels, heads, rbl


def intostring(listofchars):
	str = ''
	for c in listofchars:
		str += chr(c)

	return str


def grabaunum(bytebundle):
	num, bytebundle = npop(2, bytebundle)
	anum = (num[0] * 256 + num[1]) & int('7fff', 16)  # dec 32767
	anum = '%(n)04d' % {'n': anum}

	return anum, bytebundle


def findlabelbytestart(headerset):
	one = headerset[3]
	two = headerset[2]
	start = (256 * two) + one

	return start


def findbundledauthors(bytebundle):
	bytebundle.reverse()
	authlist = []
	while len(bytebundle) > 4:
		anum, bytebundle = grabaunum(bytebundle)
		poppedbyte = bytebundle.pop()
		if (poppedbyte & 128) or (poppedbyte == 0) and anum != '0000':
			authlist.append(anum)
			bytebundle.append(poppedbyte)
		elif anum != '0000':
			authlist.append(anum)
			bytebundle.append(poppedbyte)
			aworks, bytebundle = findbundledworks(bytebundle)
			if len(aworks) > 0:
				authlist[-1] = (authlist[-1], aworks)
	return authlist


def findbundledworks(bytebundle):
	# nothing really happens here?
	# does that matter?
	worklist = []
	bytememory = 0
	poppedbyte = bytebundle.pop()
	while (poppedbyte & 128 is False) and (poppedbyte != 0):
		print('pb:', poppedbyte)
		if poppedbyte < 32:
			worklist.append(poppedbyte)
			bytememory = poppedbyte
		elif poppedbyte == 32:
			bytebundle.append(poppedbyte)
			print('died with a 32. Bytes remaining =', len(bytebundle))
		elif poppedbyte < 64:
			for work in range(bytememory + 1, poppedbyte & 31):
				worklist.append(work)
			bytememory = 0
		elif poppedbyte < 96:
			print('trouble with a', poppedbyte, '. Bytes remaining =', len(bytebundle))
			high = (poppedbyte & 1) << 8
			poppedbyte = bytebundle.pop()
			bytememory = high + poppedbyte
			worklist.append(bytememory)
		elif poppedbyte == 96:
			poppedbyte = bytebundle.pop()
			for work in range(bytememory + 1, poppedbyte + 1):
				worklist.append(work)
		else:
			print('outside my ken:', poppedbyte, '. Bytes remaining =', len(bytebundle))
			poppedbyte = bytebundle.pop()
	worklist = ['%(n)03d' % {'n': x} for x in worklist]

	return worklist, bytebundle


def cleanlabels(labellist):
	"""
	dates have betacode in them
	"""
	clean = []
	
	percents = re.compile(r'\%(\d{1,3})')
	
	for l in labellist:
		l = re.sub(r'%3%19ae','',l) # Epigrammatici%3%19ae
		l = re.sub(percents, percentsubstitutes, l)
		l = re.sub('^ ', '', l)
		l = re.sub(' $','',l)
		l = re.sub('\*', '', l)
		# l = re.sub('\s', '_', l) # 'Scriptores Erotici' causes problems for HipparchiaServer
		clean.append(l)

	return clean


def buildlabellist(binfilepath):
	binfile = file_io.filereaders.loadbin(binfilepath)
	bl = []
	for byte in binfile:
		bl.append(byte)

	# reverse the list for popping pleasure
	rbl = bl[::-1]

	# get the genres
	labels, heads, trimmedrbl = listoflabels(rbl)
	labels = cleanlabels(labels)
	# a blank entry at the end
	labels = labels[:-1]

	# trim the pile of zeros in the middle
	p = 0
	while p == 0:
		p = trimmedrbl.pop()
	trimmedrbl.append(p)

	# switch direction again
	authinfo = trimmedrbl[::-1]

	labelcount = 0
	labellists = {}
	authlist = []

	# cut at the points indicated by the heads
	authorbytebundles = {}
	count = -1
	for lab in labels:
		count += 1
		firstsnip = findlabelbytestart(heads[count])
		try:
			secondsnip = findlabelbytestart(heads[count + 1])
			if secondsnip == 0:
				secondsnip = len(authinfo)
		except:
			secondsnip = len(authinfo)
		authorbytebundles[lab] = authinfo[firstsnip:secondsnip]

	decodedauthors = {}
	for key in authorbytebundles:
		decodedauthors[key] = findbundledauthors(authorbytebundles[key])

	return decodedauthors


def convertbinfiledates(stringdate):
	"""
	turn 7/6 B.C. into -600

	:param stringdate:
	:return:
	"""

	original = stringdate

	bc = re.compile(r'B\.C\.')
	ad = re.compile(r'A\.D\.')
	dontcare = re.compile(r'\?')
	# oops: need '／' and not '/' because the regex will avoid the normal backslash
	split = re.compile(r'(\d{1,}).*?[–/／].*?(\d{1,})')
	add = re.compile(r'^p\. ')
	subtract = re.compile(r'^a\. ')

	modifier = 1
	fudge = 0
	midcentury = -50
	date = 9999

	stringdate = re.sub(dontcare,'',stringdate)

	if re.search(bc,stringdate) is not None:
		modifier = -1
		fudge += 100

	if re.search(add,stringdate) is not None:
		fudge = 75
		if modifier < 0:
			fudge += 100

	if re.search(subtract,stringdate) is not None:
		fudge = -75

	if re.search(split,stringdate) is not None:
		digits = re.search(split, stringdate)
		one = int(digits.group(1))
		two = int(digits.group(2))

		if re.search(ad,stringdate) is not None and re.search(bc,stringdate) is not None:
			modifier = 1
			fudge -= 50
			one = one * -1

		avg = (one + two) / 2

	try:
		# we were a split
		date = int((avg * modifier * 100) + fudge + midcentury)
	except:
		# we were not a split
		if stringdate == 'Varia':
			date = 2000
		elif stringdate == 'Incertum':
			date = 2500
		else:
			stringdate = re.sub(r'\D','',stringdate)
			date = (int(stringdate) * modifier * 100) + fudge + midcentury

	if date == 0:
		date = 1

	return date


def convertdatelist(datelist):
	# do this before sending dates to dbloadlist
	newdatelist = {}
	for key in datelist:
		k = convertbinfiledates(key)
		newdatelist[k] = []
	for key in datelist:
		k = convertbinfiledates(key)
		newdatelist[k] += datelist[key]

	return newdatelist


def wipegreekauthorcolumn(column, cursor, dbconnection):
	"""

	7504 function calls (7499 primitive calls) in 0.219 seconds

	:param column:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	query = 'SELECT universalid FROM authors WHERE universalid LIKE %s'
	data = ('gr%',)
	cursor.execute(query, data)
	found = cursor.fetchall()

	insertiondict = {f[0]: [None] for f in found}

	updatedbfromtemptable('authors', 'universalid', [column], insertiondict)

	dbconnection.commit()

	return


def dbloadlist(labellist, column, cursor, dbconnection):
	"""

	34525 function calls in 2.983 seconds

	:param labellist:
	:param column:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	for key in labellist:
		for author in labellist[key]:
			query = 'SELECT universalid, {c} FROM authors WHERE universalid LIKE %s'.format(c=column)
			data = ('gr' + author,)
			cursor.execute(query, data)
			if isinstance(key, int) or isinstance(key, float):
				key = str(key)
			found = cursor.fetchall()
			# [('gr0009', 'lyric')]
			try:
				if found[0][0] is not None:
					if found[0][1] is not None:
						newinfo = found[0][1] + ',' + key
						if newinfo[0:1] == ',':
							newinfo = newinfo[1:]
					else:
						newinfo = key
					# irritating to handle Epici/-ae later
					query = 'UPDATE authors SET {c}=%s WHERE universalid=%s'.format(c=column)
					data = (newinfo, 'gr' + author)
					cursor.execute(query, data)
			except:
				pass
	dbconnection.commit()
	return

# epithets is a lot like genres, but not the same
# should probably try to merge the info, but you would need a lookup list since 'Epica' is not 'Epici'


def latinloadcanon(canonfile, cursor):

	percents = re.compile(r'\%(\d{1,3})')
	prefix = 'lt'
	# initial cleanup
	# txt = file_io.filereaders.dirtyhexloader(canonfile)
	txt = file_io.filereaders.highunicodefileload(canonfile)
	txt = re.sub(r'@', r'', txt)
	txt = re.sub(r'█⑧⓪ ', r'', txt)
	txt = re.sub(r'\{.(\d\d\d\d)\.(\d\d\d)\}', r'<authornumber>\1</authornumber><worknumber>\2</worknumber><end>\n',
	             txt)
	txt = re.sub(r'\((.*?)\)', r'<publicationinfo>\1</publicationinfo>', txt)
	txt = re.sub(r'█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ][⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]\s', r'', txt)
	txt = re.sub(r'█⓪\s', r'', txt)
	# txt = parsers.regex_substitutions.replacemarkup(txt)
	# txt = parsers.regex_substitutions.replaceaddnlchars(txt)
	txt = re.sub(r'\&3(.*?)\&', r'<work>\1</work>', txt)
	txt = re.sub(r'</work> <work>', r' ', txt)
	txt = re.sub(r'<publicationinfo>(.*?)<work>(.*?)</work>(.*?)</publicationinfo>', r'<publicationinfo>\1<volumename>\2</volumename>\3</publicationinfo>', txt)
	txt = re.sub(r'\&1(.*?)\&', r'<author>\1</author>', txt)
	txt = re.sub(r'\s\s<author>',r'<author>',txt)
	txt = re.sub(r'<author>(.*?)<publicationinfo>(.*?)</publicationinfo>(.*?)</author>', r'<author>\1(\2)\3</author>', txt)
	txt = re.sub(r'</volumename>.*?ed\.\s(.*?),\s(\d\d\d\d)(</publicationinfo>)',r'</volumename><editor>\1</editor><year>\2</year>\3',txt)
	txt = re.sub('</italic> <italic>', ' ', txt)
	txt = txt.split('\n')
	# linesout(txt, outfile)
	#  <author>L. Annaeus Seneca iunior</author>. <work>Apocolocyntosis</work> <edition><volumename>Seneca: Apocolocyntosis</volumename>, ed. P. T. Eden, 1984</edition>. <authornumber>1017</authornumber><worknumber>011</worknumber><end>
	
	canoninfo = {}
	a = re.compile(r'<authornumber>(.*?)</authornumber>')
	w = re.compile(r'<worknumber>(.*?)</worknumber>')
	l = re.compile(r'(.*?)\s<authornumber>')
	for line in txt:
		author = re.search(a, line)
		work = re.search(w, line)
		contents = re.search(l, line)
		try:
			c = contents.group(1)
		except:
			c = ''
		c = re.sub(percents, percentsubstitutes, c)
		c = latindiacriticals(c)
		c = re.sub(r'`', r'', c)
		try:
			canoninfo[prefix + author.group(1) + 'w' + work.group(1)] = c
		except:
			# blank line at end
			pass
	
	for work in canoninfo:
		query = 'UPDATE works SET publication_info=%s WHERE universalid=%s'
		data = (canoninfo[work],work)
		cursor.execute(query, data)
		
	return


def insertlatingenres(cursor, dbc):
	"""

	we have no pre-rolled association between works and genres

	guess some

	manually insert other [later...]

	:param cursor:
	:return:
	"""

	# First pass: use regex

	q = 'SELECT universalid,title FROM works WHERE universalid LIKE %s ORDER BY universalid '
	d = ('lt%',)
	cursor.execute(q,d)
	works = cursor.fetchall()

	titletranslator = [
		(r'^Ad.*?Epist', 'Epist.'),
		(r'^Epist.*?ad ', 'Epist.'),
		(r'^Atell', 'Comic.'),
		(r'^De Bello', 'Hist.'),
		(r'^De Metris', 'Gramm.'),
		(r'^De Ortho', 'Gramm.'),
		(r'^Declam', 'Orat.'),
		(r'^Pro', 'Orat.'),
		(r'^Vita', 'Biog.'),
		(r'^como', 'Comic.'),
		(r'^Commentar.', 'Hist.'),
		(r'^Commentum', 'Comm.'),
		(r'^Comment\. in', 'Comm.'),
		(r'^Controv', 'Orat.'),
		(r'^[Ee]leg', 'Eleg.'),
		(r'^epigr', 'Epigr.'),
		(r'^epist', 'Epist.'),
		(r'^Epistulae ad', 'Epist.'),
		(r'grammat', 'Gramm.'),
		(r'^[Hh]istor', 'Hist.'),
		(r'^In Verg', 'Comm.'),
		(r'^iurisp', 'Jurisprud.'),
		(r'Metr', 'Gramm.'),
		(r'Medic', 'Med.'),
		(r'^[Mm]im', 'Mim.'),
		(r'^Natur', 'Nat. Hist.'),
		(r'^orat', 'Orat.'),
		(r'^[Pp]allia', 'Comic.'),
		(r'^Paneg', 'Orat.'),
		(r'^praet', 'Trag.'),
		(r'^[Tt]rago', 'Trag.'),
		(r'^[Tt]ogat', 'Comic.'),
	]

	genres = []
	for t in titletranslator:
		for w in works:
			if re.search(t[0], w[1]) is not None:
				genres.append((w[0],t[1]))

	for g in genres:
		q = 'UPDATE works SET workgenre=%s WHERE universalid=%s'
		d = (g[1], g[0])
		cursor.execute(q, d)

	# SELECT * FROM works WHERE universalid LIKE 'lt%' AND workgenre IS NULL ORDER BY title
	# 241 of the 836 will be assigned
	dbc.commit()

	# Second pass: use authorID
	q = 'SELECT universalid FROM works WHERE universalid LIKE %s AND workgenre IS NULL'
	d = ('lt%',)
	cursor.execute(q,d)
	works = cursor.fetchall()
	works = [w[0] for w in works]

	authortranslator = {
		'lt0119': 'Comic.',
		'lt0134': 'Comic.',
		'lt1234': 'Comm.',
		'lt1235': 'Comm.',
		'lt2331': 'Biogr.',
		'lt0914': 'Hist.',
		'lt0631': 'Hist.',
		'lt1215': 'Jurisprud.',
		'lt1377': 'Gramm.',
		'lt3211': 'Gramm.',
	}

	genres = []
	for w in works:
		if w[0:6] in authortranslator:
			genres.append((w,authortranslator[w[0:6]]))

	for g in genres:
		q = 'UPDATE works SET workgenre=%s WHERE universalid=%s'
		d = (g[1], g[0])
		cursor.execute(q, d)

	dbc.commit()

	# third pass: brute force assignment
	with open('./builder/parsers/manual_latin_genre_assignment.csv', encoding='utf-8') as csvfile:
		genrereader = csv.DictReader(csvfile)
		newgenres = [(row['universalid'], row['genre']) for row in genrereader if row['genre']]

	for g in newgenres:
		q = 'UPDATE works SET workgenre=%s WHERE universalid=%s'
		d = (g[1], g[0])
		cursor.execute(q, d)

	dbc.commit()

	return


def citationreformatter(matchgroups):
	"""
	avoid Volumépagéline if you let Volume%3page%3line run through the percentsubstitutes
	:param match:
	:return:
	"""
	core = re.sub(r'%3',r'|',matchgroups.group(2))
	core = core.split('|')
	core.remove('')
	core = '|'.join(core)
	
	substitute = matchgroups.group(1)+core+matchgroups.group(3)
	
	return substitute


def streamout(txt,outfile):
	f = open(outfile, 'w')
	f.write(txt)
	f.close()
	return

# notes..

"""
labels: H-pack
	[1 2 3 4]
	read #4:
		0 --> 'last'
		N --> len of python string

authors: h-pack
	[1 2] --> (& hex 7fff) --> author number in 4-place decimal
	[3 4] --> works
	read #4
		test-for-last, etc

works:
	TBD:
"""

"""
0x0 0x0 0x8 0x0 0x0 0x0 0x0 0x0 0x5 Acta 0x0 0x0 0x0 %0x9 Alchemica0x0 0x0 0x0 0x92 0xb Antholo
giae0x0 0x0 0x0 0xac 0xb Apocalypses0x0 0x0 0x0 0xdd 0x9 Apocrypha0x0 0x0 0x1 90xb A
pologetica0x0 0x0 0x1 0xab 0xb Astrologica0x0 0x0 0x1 0xfb 0xb Astronomi
ca0x0 0x0 0x2 \0x9 Biographa0x0 0x0 0x2 0xf6 0x9 Bucolica 0x0 0x0 0x3 0xa 0x7 Caten

                5  A c t a
00000800000000000541637461200000002509416c6368656d696361000000920b416e74686f6c6f67696165000000
ac0b41706f63616c7970736573000000dd0941706f637279706861000001390b41706f6c6f676574696361000001ab
0b417374726f6c6f67696361000001fb0b417374726f6e6f6d6963610000025c0942696f677261706861000002f6094275636f6c69

"""

"""
the bytes that come before the labels look like this:
>>> print(heads)
[0, 0, 0, 0]
 [0, 0, 0, 56]
 [0, 0, 0, 78]
 [0, 0, 0, 110]
 [0, 0, 0, 142]
 [0, 0, 0, 154]
 [0, 0, 0, 178]
 [0, 0, 0, 188]
 [0, 0, 0, 194]
 [0, 0, 0, 210]
 [0, 0, 2, 2]
 [0, 0, 2, 10]
 [0, 0, 2, 80]
 [0, 0, 2, 218]
 [0, 0, 3, 12]
 [0, 0, 3, 36]
 [0, 0, 3, 66]
 [0, 0, 3, 78]
 [0, 0, 3, 90]
 [0, 0, 3, 98]
 [0, 0, 3, 250]
 [0, 0, 4, 2]
 [0, 0, 6, 174]
 [0, 0, 6, 180]
...
a means of counting: each higher than the last

here is the top of the bytes when we get to the authors
[131, 248, 135, 227, 136, 92, 136, 133, 138, 29, 138, 72, 143, 246, 144, 223, 144, 227, 144,
228, 144, 229, 144, 230, 144, 231, 144, 232, 144, 233, 144, 234, 144, 235, 144, 236, 144, 237,
144, 238, 144, 239, 144, 241, 144, 242, 144, 243, 144, 244, 163, 61, 0, 0, 0, 0, 130, 19, 130,
133, 132, 139, 132, 160, 132, 181, 133, 215, 134, 189, 134, 230, 135, 200, 0, 0, 0, 0, 131, 236]


>>> print(info[50:60])
[163, 61, 0, 0, 0, 0, 130, 19, 130, 133]

so at 56 we find the first byte of the next label: Apologetici

>>> print(info[70:80])
[134, 230, 135, 200, 0, 0, 0, 0, 131, 236]

at 78 we find the first byte of the next label: Astrologici

the value of the second digit is obvious once you see it...
there are no zero-runs from 210 until around 505: [514 + 522]

>>> print(authinfo[505:550])
[1, 135, 2, 135, 3, 0, 0, 0, 0, 130, 16, 130, 17, 0, 0, 0, 0, 128, 2, 128, 212, 128, 213,
128, 214, 128, 217, 128, 232, 128, 236, 128, 239, 128, 242, 128, 243, 128, 245, 128, 246,
128, 247, 128, 249]

and indeed we expected a short run:
 [0, 0, 2, 2]
 [0, 0, 2, 10]

therefore each '1' is worth 256: 2*256 + 2 --> 514

>>> print(labels[10])
Doxographi
>>> print(heads[10])
[0, 0, 2, 2]

there should be two and only two of them:
[130, 16]
[130, 17]
Diogenes knows of only two Doxograph.
	Arius Didymus Doxogr., Physica (fragmenta) (0529: 001)
	Aëtius Doxogr., De placitis reliquiae (Stobaei excerpta) (0528: 001)

and they *should* have sequential ids: 0528 = 130, 16; 0529 = 130, 17

"""


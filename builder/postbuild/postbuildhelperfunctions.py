# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
import configparser

from builder.builder_classes import dbWordCountObject, dbLemmaObject, dbWorkLine
from builder.dbinteraction.db import setconnection

config = configparser.ConfigParser()
config.read('config.ini')

def dictmerger(masterdict, targetdict, label):
	"""

	:param masterdict:
	:param targetdict:
	:return:
	"""

	for item in targetdict:
		if item in masterdict:
			try:
				masterdict[item][label] += targetdict[item][label]
			except:
				masterdict[item][label] = targetdict[item][label]
		else:
			masterdict[item] = {}
			masterdict[item][label] = targetdict[item][label]

	return masterdict


def forceterminalacute(matchgroup):
	"""
	θαμά and θαμὰ need to be stored in the same place

	otherwise you will click on θαμὰ, search for θαμά and get prevalence data that is not what you really wanted

	:param match:
	:return:
	"""

	map = { 'ὰ': 'ά',
			'ὲ': 'έ',
			'ὶ': 'ί',
			'ὸ': 'ό',
			'ὺ': 'ύ',
			'ὴ': 'ή',
			'ὼ': 'ώ',
			'ἂ': 'ἄ',
			'ἒ': 'ἔ',
			'ἲ': 'ἴ',
			'ὂ': 'ὄ',
			'ὒ': 'ὔ',
			'ἢ': 'ἤ',
			'ὢ': 'ὤ',
			'ᾃ': 'ᾅ',
			'ᾓ': 'ᾕ',
			'ᾣ': 'ᾥ',
			'ᾂ': 'ᾄ',
			'ᾒ': 'ᾔ',
			'ᾢ': 'ᾤ',
		}

	substitute = map[matchgroup[1]]
	try:
		# the word did not end with a vowel
		substitute += matchgroup[2]
	except:
		# the word ended with a vowel
		pass

	return substitute


def graballlinesasobjects(db, linerangetuple, cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	if linerangetuple == (-1,-1):
		whereclause = ''
	else:
		whereclause = ' WHERE index >= %s and index <= %s'
		data = (linerangetuple[0], linerangetuple[1])

	query = 'SELECT * FROM ' + db + whereclause

	if whereclause != '':
		cursor.execute(query, data)
	else:
		cursor.execute(query)

	lines = cursor.fetchall()

	lineobjects = [dblineintolineobject(l) for l in lines]

	return lineobjects


def graballcountsasobjects(db,cursor, extrasql=''):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM ' + db + extrasql
	cursor.execute(query)
	lines = cursor.fetchall()

	countobjects = [dbWordCountObject(l[0], l[1], l[2], l[3], l[4], l[5], l[6]) for l in lines]

	return countobjects


def grablemmataasobjects(db, cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM ' + db
	cursor.execute(query)
	lines = cursor.fetchall()

	lemmaobjects = [dbLemmaObject(l[0], l[1], l[2]) for l in lines]

	return lemmaobjects


def createwordcounttable(tablename, extracolumns=False):
	"""
	the SQL to generate the wordcount table
	:param tablename:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	query = 'DROP TABLE IF EXISTS public.' + tablename
	cursor.execute(query)

	query = 'CREATE TABLE public.' + tablename
	query += '( entry_name character varying(64),'
	query += ' total_count integer,'
	query += ' gr_count integer,'
	query += ' lt_count integer,'
	query += ' dp_count integer,'
	query += ' in_count integer,'
	query += ' ch_count integer'
	if extracolumns:
		query += ', frequency_classification character varying(64),'
		query += ' early_occurrences integer,'
		query += ' middle_occurrences integer,'
		query += ' late_occurrences integer'
		if type(extracolumns) == type([]):
			for c in extracolumns:
				query += ', '+c+' integer'
	query += ') WITH ( OIDS=FALSE );'

	cursor.execute(query)

	query = 'GRANT SELECT ON TABLE ' + tablename + ' TO hippa_rd;'
	cursor.execute(query)

	tableletter = tablename[-2:]

	q = 'CREATE UNIQUE INDEX wcindex'+tableletter+' ON '+tablename+' (entry_name)'
	cursor.execute(q)

	dbc.commit()

	return


def dblineintolineobject(dbline):
	"""
	convert a db result into a db object

	basically all columns pushed straight into the object with one twist: 1, 0, 2, 3, ...

	:param dbline:
	:return:
	"""

	# note the [1], [0], [2], order: wkuinversalid, index, level_05_value, ...

	lineobject = dbWorkLine(dbline[1], dbline[0], dbline[2], dbline[3], dbline[4], dbline[5], dbline[6], dbline[7],
	                        dbline[8], dbline[9], dbline[10], dbline[11], dbline[12])

	return lineobject


def cleanwords(word, punct):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
	# strip all non-greek if we are doing greek
	# best do punct before this next one...

	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass

	return word


def makeablankline(work, fakelinenumber):
	"""
	sometimes (like in lookoutsidetheline()) you need a dummy line
	this will build one
	:param work:
	:return:
	"""

	lineobject = dbWorkLine(work, fakelinenumber, '-1', '-1', '-1', '-1', '-1', '-1', '', '', '', '', '')

	return lineobject


def prettyprintcohortdata(label, cohortresultsdict):
	"""
	take some results and print them (for use in one of HipparchiaServer's info pages)

	:return:
	"""

	titles = {'h': 'high', 'l': 'low', 'a': 'average', 'm': 'median', '#': 'count'}

	print()
	print(label)
	for item in ['#', 'h', 'l', 'a', 'm']:
		print('\t'+titles[item]+'\t'+str(int(cohortresultsdict[item])))

	return


def rebasedcounter(decimalvalue, base):
	"""

	return a three character encoding of a decimal number in 'base N'
	designed to allow work names to fit into a three 'digit' space

	:param decimalvalue:
	:return:
	"""

	# base = 36

	if base < 11:
		iterable = range(0, base)
		remap = {i: str(i) for i in iterable}
	elif base < 37:
		partone = {i: str(i) for i in range(0, 10)}
		parttwo = {i: chr(87 + i) for i in range(10, base)}
		remap = {**partone, **parttwo}
	else:
		print('unsupported base value', base, '- opting for base10')
		remap = {i: str(i) for i in range(0, 10)}

	# base = 36
	# {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
	# 10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f', 16: 'g', 17: 'h', 18: 'i', 19: 'j',
	# 20: 'k', 21: 'l', 22: 'm', 23: 'n', 24: 'o', 25: 'p', 26: 'q', 27: 'r', 28: 's', 29: 't',
	# 30: 'u', 31: 'v', 32: 'w', 33: 'x', 34: 'y', 35: 'z'}

	lastdigit = remap[decimalvalue % base]
	remainder = int(decimalvalue / base)
	if remainder > 0:
		seconddigit = remap[remainder % base]
		remainder = int(remainder / base)
		if remainder > 0:
			thirddigit = remap[remainder % base]
		else:
			thirddigit = '0'
	else:
		seconddigit = '0'
		thirddigit = '0'

	rebased = thirddigit + seconddigit + lastdigit

	return rebased


# unused and ok to delete?
def deletetemporarydbs(temprefix):
	"""

	kill off the first pass info now that you have made the second pass

	:param temprefix:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'SELECT universalid FROM works WHERE universalid LIKE %s'
	d = (temprefix+'%',)
	cursor.execute(q, d)
	results = cursor.fetchall()

	authors = []
	for r in results:
		a = r[0]
		authors.append(a[0:6])
	authors = list(set(authors))

	for a in authors:
		dropdb = a
		q = 'DROP TABLE public.'+dropdb
		cursor.execute(q)

	q = 'DELETE FROM authors WHERE universalid LIKE %s'
	d = (temprefix + '%',)
	cursor.execute(q, d)

	q = 'DELETE FROM works WHERE universalid LIKE %s'
	d = (temprefix + '%',)
	cursor.execute(q, d)

	dbc.commit()

	return



"""
prettyprintcohortdata()

greek

full set
	count	113010
	high	3649037
	low	1
	average	794
	median	7

top 250
	count	250
	high	3649037
	low	39356
	average	218482
	median	78551

top 2500
	count	2250
	high	38891
	low	3486
	average	9912
	median	7026

core (not in top 2500; >50 occurrences)
	count	25901
	high	3479
	low	51
	average	466
	median	196

rare (between 50 and 5 occurrences)
	count	32614
	high	50
	low	6
	average	18
	median	15

very rare (fewer than 5 occurrences)
	count	48003
	high	4
	low	1
	average	1
	median	2


latin

full set
	count	27960
	high	244812
	low	1
	average	348
	median	11

top 250
	count	250
	high	244812
	low	5859
	average	19725
	median	10358

top 2500
	count	2250
	high	5843
	low	541
	average	1565
	median	1120

core (not in top 2500; >50 occurrences)
	count	6149
	high	541
	low	51
	average	181
	median	139

rare (between 50 and 5 occurrences)
	count	8095
	high	50
	low	6
	average	19
	median	16

very rare (fewer than 5 occurrences)
	count	10404
	high	4
	low	1
	average	1
	median	2
"""

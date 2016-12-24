# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import configparser
import re
from multiprocessing import Pool

from builder.builder_classes import dbAuthor
from builder.dbinteraction.db import setconnection, dbauthorandworkloader, tablemaker
from builder.parsers.regex_substitutions import latinadiacriticals
from builder.postbuild.postbuilddating import convertdate

"""

the goal is to take an ins or ddp db as built by the standard parser and to break it down into a new set of databases

the original files just heap up various documents inside of larger works, but this means you lose useful access to the
location and date information for each individual document, information that could be used as the basis for a search

for example 'INS0080' ==> 'Black Sea and Scythia Minor'
	w001 is 'IosPE I(2)'
	w002 is 'CIRB'

document01 of w002 has the following associated with it:
	<hmu_metadata_region value="N. Black Sea" />
	<hmu_metadata_city value="Pantikapaion" />
	<hmu_metadata_date value="344-310a" />
	<hmu_metadata_publicationinfo value="IosPE II 1" />

document180 of w002 has the following:
	<hmu_metadata_region value="N. Black Sea" />
	<hmu_metadata_city value="Myrmekion" />
	<hmu_metadata_date value="c 400-350a" />
	<hmu_metadata_publicationinfo value="IosPE IV 294[cf CIRB p.479]" />

What if you wanted to search only documents from Pantikapaion?
What if you wanted to restrict your search to 375BCE?
What if you want to search *all* Greek authors and inscriptions older than 400BCE?

what needs to happen is that the works need to become authors and the documents works
then as works the metadata can be assigned to the relevant fields of the workdb

the results of the first passdb generation are the following:
	there are 24 inscription files that will turn into 24 authors
	463 works will be distributed among these 24 authors

	there are 213 papyrus files that will turn into 213 authors
	516 works will be distributed among these 213 authors

all of this can be safely remapped as dbs with the first two places of the four character author dbname being a hex representation of a number from 1-213.
then the next two places of the author dbname can represent the digits of the old work numbers (which never exceed 99 for any given original author)

things have to happen in several passes
first you need to build the new hybrid authors from authors+works
but you can't fill out 'floruit' yet: you need line 1 of the newwork db
but the new work dbs need to be exctracted from the old work db

level05 = document number (sorta: not always the same as what is asserted at level06)
level01 = face (recto, verso, etc; usually recto: this will result in spammy output unless you use workarounds in HipparchiaServer)
level00 = line

"""


config = configparser.ConfigParser()
config.read('config.ini')

dbconnection = setconnection(config)
cursor = dbconnection.cursor()


def builddbremappers(oldprefix, newprefix):

	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'SELECT universalid FROM authors WHERE universalid LIKE %s ORDER BY universalid ASC'
	d = (oldprefix+'%',)
	cursor.execute(q,d)
	results = cursor.fetchall()

	olddbs = []
	for r in results:
		olddbs.append(r[0])

	aumapper = {}
	counter = -1
	for db in olddbs:
		counter += 1
		hx = hex(counter)
		hx = str(hx[2:])
		if len(hx) == 1:
			hx = '0'+hx
		aumapper[newprefix+hx] = db

	wkmapper = {}
	for key in aumapper.keys():
		q = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
		d = (aumapper[key]+'%',)
		cursor.execute(q, d)
		results = cursor.fetchall()

		counter = 0
		for r in results:
			counter += 1
			hx = hex(counter)
			hx = str(hx[2:])
			if len(hx) == 1:
				hx = '0' + hx
			wkmapper[r[0]] = key+hx

	dbc.commit()

	return aumapper, wkmapper


def compilenewauthors(aumapper, wkmapper):
	"""
	build new author objects by merging the old author and work info

	:param aumapper:
	:param wkmapper:
	:param cursor:
	:return: newauthors
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	newauthors = []

	for key in aumapper.keys():
		author = dbauthorandworkloader(aumapper[key], cursor)
		for w in author.listofworks:
			suffix = ' (' + w.title +')'
			newuniversalid = wkmapper[w.universalid]
			newlanguage = author.language
			if w.title != ' ':
				# the papyri are not very good at setting their titles
				newidxname = re.sub(r'\s{1,}$', '', author.idxname + suffix)
				newakaname = re.sub(r'\s{1,}$', '', author.akaname + suffix)
				newshortname = re.sub(r'\s{1,}$', '', author.shortname + suffix)
				newcleanname = re.sub(r'\s{1,}$', '', author.cleanname + suffix)
			else:
				newidxname = re.sub(r'\s{1,}$', '', author.idxname)
				newcleanname, newshortname, newakaname = newidxname, newidxname, newidxname

			newgenres = author.genres
			newrecdate = author.recorded_date
			newconvdate = author.converted_date
			newlocation = author.location
			newauthor = dbAuthor(newuniversalid, newlanguage, newidxname, newakaname, newshortname, newcleanname, newgenres, newrecdate, newconvdate, newlocation)
			newauthors.append(newauthor)

	dbc.commit()

	return newauthors


def compilenewworks(newauthors, wkmapper):
	"""
	a bulk operation that goes newauthor by newauthor so as to build a collection of works for it
	find all of the individual documents within an old work and turn each document into its own new work

	:param newauthors:
	:param wkmapper:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

	remapper = {}
	for key in wkmapper:
		remapper[wkmapper[key]] = key

	# remapper: {'in0009': 'ZZ0080w009', 'in0014': 'ZZ0080w020', 'in0002': 'ZZ0080w002', ... }

	thework = []

	for a in newauthors:
		db = remapper[a.universalid]
		modifyauthorsdb(a.universalid, a.idxname, cursor)
		thework.append((a, db))
	dbc.commit()

	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelnewworkworker, thework)

	return


def parallelnewworkworker(authoranddbtuple):
	"""

	compile new works in parallel to go faster
	the loop inside of this is where the real speed gains would lie: 'for document in results:...'
	but note how much fun cloneauthor() would be in a multiprocessing environment

	:param authoranddbtuple: (authorobject, dbname)
	:return:
	"""

	a = authoranddbtuple[0]
	db = authoranddbtuple[1]

	dbc = setconnection(config)
	cursor = dbc.cursor()

	print(a.universalid, a.idxname)
	q = 'SELECT DISTINCT level_05_value FROM ' + db + ' ORDER BY level_05_value'
	cursor.execute(q)
	results = cursor.fetchall()

	dbnumber = 0
	for document in results:
		# can't use docname as the dbname because you will find items like 257a or, worse, 1960:4,173)
		docname = document[0]

		dbnumber += 1

		dbstring = rebasedcouter(dbnumber)
		if len(dbstring) == 1:
			dbstring = '00' + dbstring
		elif len(dbstring) == 2:
			dbstring = '0' + dbstring

		q = 'SELECT * FROM ' + db + ' WHERE level_05_value LIKE %s ORDER BY index'
		d = (document[0],)
		cursor.execute(q, d)
		results = cursor.fetchall()

		newdb = a.universalid + 'w' + dbstring
		buidlnewindividualworkdb(newdb, results, cursor)
		updateworksdb(newdb, db, docname, cursor)
		setmetadata(newdb, cursor)
		if dbnumber % 100 == 0:
			dbc.commit()

	dbc.commit()

	return


def rebasedcouter(decimalvalue):
	"""

	return a three character encoding of a decimal number: 'base 36'
	designed to allow work names to fit into a three 'digit' space

	:param decimalvalue:
	:return:
	"""

	remap = { 0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
			  10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f', 16: 'g', 17: 'h', 18: 'i', 19: 'j',
			  20: 'k', 21: 'l', 22: 'm', 23: 'n', 24: 'o', 25: 'p', 26: 'q', 27: 'r', 28: 's', 29: 't',
			  30: 'u', 31: 'v', 32: 'w', 33: 'x', 34: 'y', 35: 'z' }

	base = len(remap)

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

	rebased = thirddigit+seconddigit+lastdigit

	return rebased


def modifyauthorsdb(newentryname, worktitle, cursor):
	"""
	the idxname of something like "ZZ0080" will be "Black Sea and Scythia Minor"
	the title of "in0001" should be set to "Black Sea and Scythia Minor IosPE I(2) [Scythia]"

	:param tempentryname:
	:param newentryname:
	:param worktitle:
	:param cursor:
	:return:
	"""

	idx = worktitle
	clean = worktitle

	if 	newentryname[0:2] == 'dp':
		aka = worktitle
	else:
		aka = re.search(r'\((.*?)\)$', worktitle)
		try:
			aka = aka.group(1)
		except:
			aka = worktitle

	if 	newentryname[0:2] == 'dp':
		short = worktitle
	else:
		short = re.search(r'\[(.*?)\]\)$', worktitle)
		try:
			short = short.group(1)
		except:
			short = aka

	q = 'INSERT INTO authors (universalid, language, idxname, akaname, shortname, cleanname, recorded_date) ' \
			' VALUES (%s, %s, %s, %s, %s, %s, %s)'
	d = (newentryname, 'G', idx, aka, short, clean, 'Varia')
	cursor.execute(q, d)

	# inscription 'authors' can set their location via their idxname
	if newentryname[0:2] == 'in':
		loc = re.search(r'(.*?)\s\(', worktitle)
		q = 'UPDATE authors SET location=%s WHERE universalid=%s'
		d = (loc.group(1),newentryname)
		cursor.execute(q, d)

	return


def buidlnewindividualworkdb(db, results, cursor):
	"""

	send me all of the matching lines from one db and i will build a new workdb with only these lines

	:param docname:
	:param results:
	:return:
	"""

	tablemaker(db, cursor)

	for r in results:
		r = list(r)
		# you need to have '-1' in the unused levels otherwise HipparchiaServer will have trouble building citations
		# level05 has been converted to the dbname, so we can discard it
		# level01 is sometimes used: 'recto', 'verso'
		# this is a problem since irregularly shaped works irritate HipparchiaServer
		# level04 will yield things like: 'face C, right'
		# this material will get merged with level01; but what sort of complications will arise?

		r[1] = '-1' # level05
		if r[5] == '1': # level 01
			r[5] = 'recto'

		for level in [2,3,4]: # levels 04, 03, 02
			if r[level] != '1':
				if level != 4:
					# print('unusual level data:', db,r[0],level,r[level])
					pass
				r[5] = r[level] + ' ' + r[5]
			r[level] = '-1'

		q = 'INSERT INTO ' + db + ' (index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations)' \
											  ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
		d = tuple(r)
		cursor.execute(q, d)

	return


def updateworksdb(newdb, olddb, docname, cursor):
	"""
	the title of "ZZ0080w001" will be "IosPE I(2) [Scythia]"
	the title of "in0001wNNN" should be the same with a document ID suffix: " - 181", etc.
	:param newdb:
	:param docname:
	:param cursor:
	:return:
	"""

	q = 'SELECT title FROM works WHERE universalid = %s'
	d = (olddb,)
	cursor.execute(q, d)
	r = cursor.fetchone()

	if r[0] != ' ':
		newtitle = r[0] + ' - ' + docname
	else:
		# I bet you are a papyrus
		q = 'SELECT idxname FROM authors WHERE universalid = %s'
		d = (newdb[0:6],)
		cursor.execute(q, d)
		r = cursor.fetchone()
		newtitle = r[0] + ' - ' + docname

	q = 'INSERT INTO works (universalid, title) VALUES (%s, %s)'
	d = (newdb, newtitle)
	try:
		cursor.execute(q, d)
	except:
		print('failed to insert work\n\t',d)

	return


def setmetadata(db, cursor):
	"""
	marked_up_line where level_00_value == 1 ought to contain metadata about the document
	example: "<hmu_metadata_provenance value="Oxy" /><hmu_metadata_date value="AD 224" /><hmu_metadata_documentnumber value="10" />[ <hmu_roman_in_a_greek_text>c ̣]</hmu_roman_in_a_greek_text>∙τ̣ε̣[∙4]ε[∙8]"

	:param db:
	:param cursor:
	:return:
	"""

	prov = re.compile(r'<hmu_metadata_provenance value="(.*?)" />')
	date = re.compile(r'<hmu_metadata_date value="(.*?)" />')
	region = re.compile(r'<hmu_metadata_region value="(.*?)" />')
	city = re.compile(r'<hmu_metadata_city value="(.*?)" />')
	textdirection = re.compile(r'<hmu_metadata_texdirection value="(.*?)" />')
	publicationinfo = re.compile(r'<hmu_metadata_publicationinfo value="(.*?)" />')
	additionalpubinfo = re.compile(r'<hmu_metadata_additionalpubinfo value="(.*?)" />')
	stillfurtherpubinfo = re.compile(r'<hmu_metadata_stillfurtherpubinfo value="(.*?)" />')
	reprints = re.compile(r'<hmu_metadata_reprints value="(.*?)" />')
	doc = re.compile(r'<hmu_metadata_documentnumber value="(.*?)" />')

	q = 'SELECT index, marked_up_line, annotations FROM '+db+' ORDER BY index LIMIT 1'
	cursor.execute(q)
	r = cursor.fetchone()
	idx = r[0]
	ln = r[1]
	an = r[2]

	pi = []
	for info in [publicationinfo, additionalpubinfo, stillfurtherpubinfo, reprints]:
		p = re.search(info,ln)
		if p is not None:
			pi.append(p.group(1))
	pi = '; '.join(pi)
	if pi != '':
		pi = '<volumename>'+pi+'<volumename>'

	dt = re.search(date,ln)
	try:
		dt = dt.group(1)
		dt = re.sub(r'(^\s{1,}|\s{1,}$)', '', dt)
	except:
		dt = '[unknown]'

	cd = convertdate(dt)

	pr = re.search(prov, ln)
	try:
		pr = pr.group(1)
	except:
		pr = '[unknown]'
	if pr == '?':
		pr = '[unknown]'

	rg = re.search(region, ln)
	try:
		rg = rg.group(1)
	except:
		rg = '[unknown]'

	ct = re.search(city, ln)
	try:
		ct = ct.group(1)
	except:
		ct = '[unknown]'

	if rg != '[unknown]' and ct != '[unknown]':
		ct = ct + ' ('+rg+')'

	if pr != '[unknown]' and ct != '[unknown]':
		pr = pr + '; ' + ct
	elif pr == '[unknown]' and ct != '[unknown]':
		pr = ct

	if len(pr) > 64:
		pr = pr[0:63]

	for item in [pi, pr, dt]:
		item = latinadiacriticals(item)

	# labels need to be '' and not None because of the way findtoplevelofwork() is coded in HipparchiaServer
	# note that 'face' has been represented by a whitespace: ' '

	q = 'UPDATE works SET publication_info=%s, provenance=%s, recorded_date=%s, converted_date=%s, levellabels_00=%s, ' \
			'levellabels_01=%s, levellabels_02=%s, levellabels_03=%s, levellabels_04=%s, levellabels_05=%s, ' \
			'authentic=%s WHERE universalid=%s'
	d = (pi, pr, dt, cd, 'line', ' ', '', '', '', '', True, db)
	cursor.execute(q,d)

	if db[0:2] == 'in':
		q = 'UPDATE works SET transmission=%s, worktype=%s WHERE universalid=%s'
		d = ('inscription', 'inscription', db)
		cursor.execute(q, d)
	if db[0:2] == 'dp':
		q = 'UPDATE works SET transmission=%s, worktype=%s WHERE universalid=%s'
		d = ('papyrus', 'papyrus', db)
		cursor.execute(q, d)

	# things we put in annotations

	td = re.search(textdirection, ln)
	try:
		td = 'textdirection: '+td.group(1)
	except:
		td = ''

	dn = re.search(doc, ln)
	try:
		dn = 'documentnumber: '+dn.group(1)
	except:
		dn = ''

	if td != '' or dn != '':
		newnotes = []
		for n in [an, td, dn]:
			if n != '':
				newnotes.append(n)
		notes = '; '.join(newnotes)

		q = 'UPDATE '+db+' SET annotations=%s WHERE index=%s'
		d = (notes, idx)
		cursor.execute(q, d)

	return


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

	for r in results:
		dropdb = r[0]
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


# slated for removal


def cloneauthor(authorobject, cursor):
	"""
	copy an author so you can hold more works
	:param authorobject:
	:return:
	"""

	newauthorobject = authorobject
	currentid = authorobject.universalid


	# need to avoid dbname collisions here: remember that the namespace has been compressed into effectively two characters (inXX)
	# 	'in1b05' has more than 1000 entries
	#	'in1b0F' will be its continuation
	#	'in1bAF' will continue in1b0F'
	# it should be impossible for any two authors to generate the same set of continuations
	ending = currentid[-1]
	if 64 < ord(ending) < 91:
		# already in the A-Z range (ie., we are looking at work #2000+!)
		# we can't turn 'in1b0F' into 'in1b0G' because 'in1b06' is capable of generating 'in1b0G'
		# so we increment the '0': 'in1bAF'
		if re.search(r'[0-9a-f]', currentid[-2:-1]) is not None:
			# this is the first time we have done this
			val = int(currentid[-2:-1], 16)
			char = chr(val + 65)
		else:
			# there is an 'A' or such in this position; increment it
			char = chr(ord(currentid[-2:-1]) + 1)
		newid = currentid[:-2] + char + ending
	else:
		# take the last character of the work and push it into an otherwise impossible register
		val = int(ending,16)
		char = chr(val+65) # 0 -> A, 1 -> B, ...
		newid = authorobject.universalid[:-1] + char

	newauthorobject.universalid = newid

	suffix = '(pt. 2)'
	if re.search(r'\(pt\.\s\d{1,}\)$',newauthorobject.idxname) is not None:
		count = re.search(r'\(pt\.\s(\d{1,})\)$',newauthorobject.idxname)
		count = str(int(count.group(1))+1)
		suffix = '(pt. '+count+')'
		# kill off '(pt. 2)' to make way for '(pt. 3)'
		newauthorobject.idxname = newauthorobject.idxname[:-7] + suffix
	else:
		newauthorobject.idxname = newauthorobject.idxname + suffix

	modifyauthorsdb(newauthorobject.universalid, newauthorobject.idxname, cursor)
	print('\t',currentid,' --> ', newauthorobject.universalid)

	return newauthorobject



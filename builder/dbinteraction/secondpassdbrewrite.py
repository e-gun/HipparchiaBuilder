# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re
import configparser
from multiprocessing import Pool
from builder.dbinteraction.db import setconnection, dbauthorloadersubroutine, dbauthorandworkloader, dbauthoradder, tablemaker
from builder.builder_classes import dbAuthor, dbOpus, dbWorkLine

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


def resetauthorsandworksdbs(prefix):
	"""
	clean out any old info before insterting new info
	you have to purge the dbs every time because the names can change between builds

	:param prefix:
	:return:
	"""
	dbc = setconnection(config)
	cursor = dbc.cursor()

	q = 'SELECT universalid FROM works WHERE universalid LIKE %s'
	d = (prefix + '%',)
	cursor.execute(q, d)
	results = cursor.fetchall()

	count = 0
	for r in results:
		count += 1
		q = 'DROP TABLE public.'+r[0]
		cursor.execute(q)
		if count % 500 == 0:
			dbc.commit()

	q = 'DELETE FROM authors WHERE universalid LIKE %s'
	d = (prefix + '%',)
	cursor.execute(q, d)

	q = 'DELETE FROM works WHERE universalid LIKE %s'
	d = (prefix + '%',)
	cursor.execute(q, d)

	dbc.commit()
	return


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
		dbc.commit()
		thework.append((a, db))

	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelnewworkworker, thework)

	return


def parallelnewworkworker(authoranddbtuple):
	"""

	compile new works in parallel to go faster
	but maybe the loop inside of this is where the real speed gains would lie: 'for document in results:...'

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
		# unfortunately you can have more than 1000 documents: see SEG 1–41 [N. Shore Black Sea]
		dbstring = hex(dbnumber)
		dbstring = dbstring[2:]
		if len(dbstring) == 1:
			dbstring = '00' + dbstring
		elif len(dbstring) == 2:
			dbstring = '0' + dbstring

		q = 'SELECT * FROM ' + db + ' WHERE level_05_value LIKE %s ORDER BY index'
		d = (document[0],)
		cursor.execute(q, d)
		results = cursor.fetchall()

		newdb = a.universalid + 'w' + dbstring
		buidlnewindividualworkdb(newdb, results)
		updateworksdb(newdb, db, docname, cursor)
		setmetadata(newdb, cursor)
		dbc.commit()

	return


def modifyauthorsdb(newentryname, worktitle, cursor):
	"""
	the idxname of "ZZ0080" will be "Black Sea and Scythia Minor"
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


def buidlnewindividualworkdb(db, results):
	"""

	send me all of the matching lines from one db and i will build a new workdb with only these lines

	:param docname:
	:param results:
	:return:
	"""

	dbc = setconnection(config)
	cursor = dbc.cursor()

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
					print('unusual level data:', db,r[0],level,r[level])
				r[5] = r[level] + ' ' + r[5]
			r[level] = '-1'

		q = 'INSERT INTO ' + db + ' (index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations)' \
											  ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
		d = tuple(r)
		cursor.execute(q, d)

	dbc.commit()

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
	cursor.execute(q, d)

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


def convertdate(date):
	"""
	take a string date and try to assign a number to it: IV AD --> 450, etc.

	:param date:
	:return:
	"""

	originaldate = date

	datemapper = {
		'[unknown]': 1500,
		'date': 1500,
		'aet tard': 1000,
		'aet inferior': 1200,
		'aet Byz': 700,
		'archaic': -700,
		'Hell.': -250,
		'aet Hell': -250,
		'aet Rom': 50,
		'aet Rom tard': 100,
		'aet Imp tard': 400,
		'aet Chr': 400,
		'aet Imp': 200,
		'aet Carac': 205,
		'aet Aur': 170,
		'aet Ant': 145,
		'aet Had': 125,
		'aet Ves': 70,
		'aet Nero': 60,
		'aet Claud': 50,
		'aet Aug': 1,
		'init aet Hell': -310,
		'Late Hell.': -1,
		'aet Hell tard': -1,
		'Late Imp.': 250,
		'late archaic': -600,
		'I bc': -50,
		'I bc-I ac': 1,
		'Ia/Ip': 1,
		'Ip': 50,
		'I ac': 50,
		'Ia': -50,
		'I-II ac': 100,
		'I-IIa': -100,
		'I-IIp': 100,
		'I-IIIp': 111,
		'III-Ia': -111,
		'I/IIp': 100,
		'II ac': 150,
		'II bc': -150,
		'IIp': 150,
		'IIa': -150,
		'II-I bc': -100,
		'II/Ia': -100,
		'II-III ac': 200,
		'II/IIIp': 200,
		'II-IIIp': 200,
		'II-beg.III ac': 280,
		'II/I bc': -100,
		'III ac': 250,
		'IIIp': 250,
		'IIIa': -250,
		'III bc': -250,
		'III-II bc': -200,
		'III/IIa': -200,
		'III/IVp': 300,
		'IV ac': 350,
		'IV bc': -350,
		'IVp': 350,
		'IVa': -350,
		'IV-III bc': -300,
		'IV/IIIa': -300,
		'IV-III/II bc': -275,
		'IV-V ac': 400,
		'IV/Vp': 400,
		'Ia-Ip': 1,
		'V bc': -450,
		'V ac': 450,
		'Va': -450,
		'Vp': 450,
		'V-IV bc': -400,
		'V/IVa': -400,
		'V-IVa': -400,
		'V/VIp': 500,
		'VI bc': -550,
		'VI/Va': -500,
		'VIa': -550,
		'VIp': 550,
		'VI ac': 550,
		'VI/VIIp': 600,
		'VIIp': 650,
		'VII/VIIIp': 700,
		'XVII-XIX ac': 1800,
	}

	# drop things that will only confuse the issue
	date = re.sub(r'(\?|\(\?\))', '', date)
	date = re.sub(r'med\s','', date)
	date = re.sub(r'^c(\s|)', '', date)
	date = re.sub(r'/(antea|postea|paullo )','', date)

	# swap papyrus BCE info format for one of the inscription BCE info formats
	date = re.sub(r'\sspc$','p', date)
	date = re.sub(r'\ssac$', 'a', date)

	fudge = 0
	if re.search(r'^(ante|a|ante fin)\s', date) is not None:
		date = re.sub(r'^(ante|a|ante fin)\s', '', date)
		fudge = -20
	if re.search(r'^p\spost\s', date) is not None:
		date = re.sub(r'^p\spost\s', '', date)
		fudge = 10
	if re.search(r'^(post|p)\s', date) is not None:
		date = re.sub(r'^(post|p)\s', '', date)
		fudge = 20
	if re.search(r'init\s', date) is not None:
		date = re.sub(r'init\s', '', date)
		fudge = -25
	if re.search(r'^fin\s', date) is not None:
		date = re.sub(r'^fin\s', '', date)
		fudge = 25

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
		BCE = re.compile(r'(\sbc|\sBC|^BC\s)')
		CE = re.compile(r'(\sac|\sAD|^AD\s)')
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

		# clear out things we won'd use from here on out
		date = re.sub(r'^c\s','', date)
		date = re.sub(r'(c\.\s)','', date)
		date = re.sub(r'\sbc|\sBC\sac|\sAD','', date)
		# '44/45' ==> '45'
		splityears = re.compile(r'(\d{1,})(/\d{1,})(.*?)')
		if re.search(splityears, date) is not None:
			split = re.search(splityears, date)
			date = split.group(1)+split.group(3)

		if len(date.split('-')) > 1:
			# take the middle of any range you find
			halves = date.split('-')
			first = halves[0]
			second = halves[1]
			if re.search(r'\d', first) is not None and re.search(r'\d', second) is not None:
				first = re.sub(r'\D','',first)
				first = int(first)
				second = re.sub(r'\D', '', second)
				second = int(second)
				numericaldate = (first + second)/2 * modifier + (fudge * modifier)
			elif re.search(r'\d', first) is not None:
				# you'll get here with something like '172- BC?'
				first = re.sub(r'\D','',first)
				numericaldate = int(first) * modifier + (fudge * modifier)
			else:
				numericaldate = 9999
		elif re.search(r'\d', date) is not None:
			# we're just a collection of digits? '47', vel sim?
			try:
				numericaldate = int(date) * modifier + fudge
			except:
				# oops: maybe we saw something like 'III bc' but it was not in datemapper{}
				numericaldate = 8888
		else:
			numericaldate = 7777

	if numericaldate > 2000:
		print('date -> number:\n\t',originaldate,'\n\t',numericaldate)

	return numericaldate


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



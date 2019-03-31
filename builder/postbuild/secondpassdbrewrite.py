# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re
from multiprocessing import Manager

import psycopg2

from builder.builderclasses import MPCounter, dbAuthor, dbOpus
from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbdataintoobjects import dbauthorandworkloader
from builder.dbinteraction.dbhelperfunctions import authortablemaker
from builder.dbinteraction.dbloading import generatecopystream
from builder.dbinteraction.genericworkerobject import GenericInserterObject
from builder.parsers.swappers import forceregexsafevariants
from builder.postbuild.postbuilddating import convertdate
from builder.wordcounting.wordcounthelperfunctions import rebasedcounter

"""

the goal is to take an ins, ddp, or chr db as built by the standard parser and to break it down into a new set of databases

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
config.read('config.ini', encoding='utf8')


def builddbremappers(oldprefix, newprefix):

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'SELECT universalid FROM authors WHERE universalid LIKE %s ORDER BY universalid ASC'
	d = (oldprefix+'%',)
	dbcursor.execute(q, d)
	results = dbcursor.fetchall()

	olddbs = [r[0] for r in results]

	aumapper = dict()
	counter = -1
	for db in olddbs:
		counter += 1
		hx = hex(counter)
		hx = str(hx[2:])
		if len(hx) == 1:
			hx = '0'+hx
		aumapper[newprefix+hx] = db

	wkmapper = dict()
	for key in aumapper.keys():
		q = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
		d = (aumapper[key]+'%',)
		dbcursor.execute(q, d)
		results = dbcursor.fetchall()

		counter = 0
		for r in results:
			counter += 1
			hx = hex(counter)
			hx = str(hx[2:])
			if len(hx) == 1:
				hx = '0' + hx
			wkmapper[r[0]] = key+hx

	dbconnection.connectioncleanup()

	return aumapper, wkmapper


def compilenewauthors(aumapper, wkmapper):
	"""
	build new author objects by merging the old author and work info

	:param aumapper:
	:param wkmapper:
	:return: newauthors
	"""

	dbcconnection = setconnection()
	dbcursor = dbcconnection.cursor()

	newauthors = list()

	for key in aumapper.keys():
		author = dbauthorandworkloader(aumapper[key], dbcursor)
		for w in author.listofworks:
			suffix = ' ({t})'.format(t=w.title)
			newuniversalid = wkmapper[w.universalid]
			newlanguage = author.language
			if w.title != ' ':
				# the papyri are not very good at setting their titles
				newidxname = re.sub(r'\s+$', '', author.idxname + suffix)
				newakaname = re.sub(r'\s+$', '', author.akaname + suffix)
				newshortname = re.sub(r'\s+$', '', author.shortname + suffix)
				newcleanname = re.sub(r'\s+$', '', author.cleanname + suffix)
			else:
				newidxname = re.sub(r'\s+$', '', author.idxname)
				newcleanname, newshortname, newakaname = newidxname, newidxname, newidxname

			newgenres = author.genres
			newrecdate = author.recorded_date
			newconvdate = author.converted_date
			# "Aegean Islands [general]", "Mysia and Troas [Munich]", "Varia [Sacred Laws]"
			aloc = re.sub(r'\[.*?\]', '', author.location)
			newlocation = aloc
			newauthor = dbAuthor(newuniversalid, newlanguage, newidxname, newakaname, newshortname, newcleanname, newgenres, newrecdate, newconvdate, newlocation)
			newauthors.append(newauthor)

	dbcconnection.connectioncleanup()

	return newauthors


def compilenewworks(newauthors, wkmapper):
	"""
	a bulk operation that goes newauthor by newauthor so as to build a collection of works for it
	find all of the individual documents within an old work and turn each document into its own new work

	:param newauthors:
	:param wkmapper:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	remapper = dict()
	for key in wkmapper:
		remapper[wkmapper[key]] = key

	# remapper: {'in0009': 'ZZ0080w009', 'in0014': 'ZZ0080w020', 'in0002': 'ZZ0080w002', ... }

	thework = list()

	for a in newauthors:
		db = remapper[a.universalid]
		modifyauthorsdb(a.universalid, a.idxname, dbcursor)
		thework.append((a, db))

	thework.reverse()

	dbconnection.connectioncleanup()

	manager = Manager()
	workpile = manager.list(thework)
	newworktuples = manager.list()

	workerobject = GenericInserterObject(parallelnewworkworker, argumentlist=[workpile, newworktuples])
	workerobject.dothework()

	return newworktuples


def registernewworks(newworktuples):
	"""

	you have a list, now register the contents: INSERT into a pre-cleaned works table

	newworktuples = [(newwkid1, oldworkdb1, docname1), (newwkid2, oldworkdb2, docname2), ...]

	note that the notations could be further refactored to trim down on the UPDATES

	:param newworktuples:
	:return:
	"""
	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	workandtitletuplelist = findnewtitles(newworktuples)
	workinfodict = buildnewworkmetata(workandtitletuplelist)

	# workinfodict has ids as keys ('in0006w0lk') and then a dict attached that contains db keys and values: 'title': 'Attica (IG II/III2 3,1 [2789-5219]) - 3536', etc.
	# note that you also have the key 'annotationsatindexvalue' it contains an index value and the notes to insert at that index location
	# it will eventually require q = 'UPDATE '+db+' SET annotations=%s WHERE index=%s'

	# insert new works into the works table: deletetemporarydbs() means that this is INSERT and not UPDATE

	print('registering', len(workinfodict), 'new works')

	count = 0
	for w in workinfodict.keys():
		count += 1
		columns = ['universalid', 'levellabels_00', 'levellabels_01']
		vals = [w, 'line', ' ']  # the whitesapce matters for levellabels_01
		valstring = ['%s', '%s', '%s']
		# set genres: not elegant, but...
		if w[0:2] in ['in', 'ch']:
			columns.append('workgenre')
			vals.append('Inscr.')
			valstring.append('%s')
		if w[0:2] in ['dp']:
			columns.append('workgenre')
			vals.append('Docu.')
			valstring.append('%s')
		for key in workinfodict[w].keys():
			if key != 'annotationsatindexvalue':
				columns.append(key)
				vals.append(workinfodict[w][key])
				valstring.append('%s')
		columns = ', '.join(columns)
		valstring = ', '.join(valstring)
		vals = [forceregexsafevariants(v) for v in vals]
		vals = tuple(vals)

		q = 'INSERT INTO works ( {c} ) VALUES ( {v} ) '.format(c=columns, v=valstring)
		d = vals
		dbcursor.execute(q, d)
		if count % 2500 == 0:
			dbconnection.commit()
	dbconnection.commit()

	print('updating the notations in {w} works'.format(w=len(workinfodict)))

	count = 0
	for w in workinfodict:
		count += 1
		if 'annotationsatindexvalue' in workinfodict[w]:
			db = w[0:6]
			idx = workinfodict[w]['annotationsatindexvalue'][1]
			notes = workinfodict[w]['annotationsatindexvalue'][0]

			q = 'UPDATE {db} SET annotations=%s WHERE index=%s'.format(db=db)
			d = (notes, idx)
			dbcursor.execute(q, d)
		if count % 2500 == 0:
			dbconnection.commit()
		if count % 5000 == 0:
			print('\t', count, 'works updated')

	dbconnection.connectioncleanup()

	return


def findnewtitles(newworktuples):
	"""

	we are building a dictionary of new works

	newworktuples:
		[(newwkid1, oldworkdb1, docname1), (newwkid2, oldworkdb2, docname2), ...]
		[('dp0601w008', 'YY0007', '16'), ('dp0301w007', 'YY0004', '15 rp'), ('dp0201w00f', 'YY0003', '154'), ... ]

	:param newworktuples:
	:return:
	"""

	print('collecting info about new works: building', len(newworktuples), 'titles')

	newworkdict = {t[0]: (t[1], t[2]) for t in newworktuples}
	workandtitletuplelist = list()

	for wk in newworkdict.keys():
		thetitle = newworkdict[wk][1]
		workandtitletuplelist.append((wk, thetitle))

	return workandtitletuplelist


def buildnewworkmetata(workandtitletuplelist):
	"""

	supplement the workinfodict with more information about the works

	:param workandtitletuplelist:
	:return:
	"""

	workinfodict = {w[0]: {'title': w[1]} for w in workandtitletuplelist}

	print('collecting info about new works: metadata')

	count = MPCounter()
	manager = Manager()
	workpile = manager.list(workinfodict.keys())
	metadatalist = manager.list()

	workerobject = GenericInserterObject(buildworkmetadatatuples, argumentlist=[workpile, count, metadatalist])
	workerobject.dothework()

	# manager was not populating the manager.dict()
	# so we are doing this
	# newworkinfodict[wkid]['publication_info'] = pi
	# newworkinfodict[wkid]['provenance'] = pr
	# newworkinfodict[wkid]['recorded_date'] = dt
	# newworkinfodict[wkid]['converted_date'] = cd
	# newworkinfodict[wkid]['transmission'] = tr
	# newworkinfodict[wkid]['worktype'] = ty
	# newworkinfodict[wkid]['annotationsatindexvalue'] = (idx, notes)
	# metadatalist.append((wkid, pi,pr,dt,cd,tr,ty,(notes,idx)))

	resultsdict = {w[0]: {
		'publication_info': w[1],
		'provenance': w[2],
		'recorded_date': w[3],
		'converted_date': w[4],
		'transmission': w[5],
		'worktype': w[6],
		'annotationsatindexvalue': w[7]
		} for w in metadatalist}

	# merge with previous results
	for key in resultsdict.keys():
		resultsdict[key]['title'] = workinfodict[key]['title']

	return resultsdict


def parallelnewworkworker(workpile, newworktuples, dbconnection):
	"""

	compile new works in parallel to go faster
	the loop inside of this is where the real speed gains would lie: 'for document in results:...'

	:param workpile:
	:param newworktuples:
	:return:
	"""

	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()

	while len(workpile) > 0:
		try:
			authoranddbtuple = workpile.pop()
		except IndexError:
			authoranddbtuple = (False, False)

		if authoranddbtuple is not False:
			a = authoranddbtuple[0]
			wkid = authoranddbtuple[1]
			db = wkid[0:6]

			authortablemaker(a.universalid, dbconnection)
			dbconnection.commit()

			q = 'SELECT DISTINCT level_05_value FROM {db} WHERE wkuniversalid=%s ORDER BY level_05_value'.format(db=db)
			d = (wkid,)
			dbcursor.execute(q, d)
			results = dbcursor.fetchall()

			wknum = 0
			for document in results:
				# can't use docname as the thee character dbname because you will find items like 257a or, worse, 1960:4,173)
				wknum += 1
				dbstring = rebasedcounter(wknum, 36)

				if len(dbstring) == 1:
					dbstring = '00' + dbstring
				elif len(dbstring) == 2:
					dbstring = '0' + dbstring

				q = 'SELECT * FROM {db} WHERE (wkuniversalid=%s AND level_05_value=%s) ORDER BY index'.format(db=db)
				d = (wkid, document[0])
				dbcursor.execute(q, d)
				results = dbcursor.fetchall()

				newwkid = a.universalid + 'w' + dbstring
				insertnewworksintonewauthor(newwkid, results, dbcursor)
				docname = document[0]
				newworktuples.append((newwkid, db, docname))

				if wknum % 100 == 0 or wknum == len(results):
					dbconnection.commit()

			try:
				print(a.universalid, a.idxname)
			except UnicodeEncodeError:
				# it is your shell/terminal who is to blame for this
				# UnicodeEncodeError: 'ascii' codec can't encode character '\xe1' in position 19: ordinal not in range(128)
				print(a.universalid)

	return newworktuples


def buildworkmetadatatuples(workpile, commitcount, metadatalist, dbconnection):
	"""

	marked_up_line where level_00_value == 1 ought to contain metadata about the document
	example: "<hmu_metadata_provenance value="Oxy" /><hmu_metadata_date value="AD 224" /><hmu_metadata_documentnumber value="10" />[ <hmu_latin_normal>c ̣]</hmu_latin_normal>∙τ̣ε̣[∙4]ε[∙8]"

	:param workpile:
	:param commitcount:
	:param metadatalist:
	:return:
	"""

	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()

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

	while workpile:
		try:
			wkid = workpile.pop()
		except IndexError:
			wkid = False
			workpile = None

		if wkid:
			commitcount.increment()
			dbconnection.checkneedtocommit(commitcount.value)

			db = wkid[0:6]

			q = 'SELECT index, marked_up_line, annotations FROM {db} WHERE wkuniversalid=%s ORDER BY index LIMIT 1'.format(db=db)
			d = (wkid,)
			dbcursor.execute(q, d)
			try:
				r = dbcursor.fetchone()
			except psycopg2.ProgrammingError:
				# psycopg2.ProgrammingError: no results to fetch
				r = (-999, '', '')

			idx = r[0]
			ln = r[1]
			an = r[2]

			pi = list()
			for info in [publicationinfo, additionalpubinfo, stillfurtherpubinfo, reprints]:
				p = re.search(info, ln)
				if p is not None:
					pi.append(p.group(1))
			pi = '; '.join(pi)
			if pi != '':
				pi = '<volumename>{pi}<volumename>'.format(pi=pi)

			dt = re.search(date, ln)
			try:
				dt = dt.group(1)
				dt = re.sub(r'(^\s+|\s+$)', '', dt)
			except AttributeError:
				dt = '[unknown]'

			cd = convertdate(dt)

			pr = re.search(prov, ln)
			try:
				pr = pr.group(1)
			except AttributeError:
				pr = '[unknown]'
			if pr == '?':
				pr = '[unknown]'

			pr = re.sub(r'(^\s|\s)$', '', pr)

			rg = re.search(region, ln)
			try:
				rg = rg.group(1)
			except AttributeError:
				rg = '[unknown]'

			ct = re.search(city, ln)
			try:
				ct = ct.group(1)
			except AttributeError:
				ct = '[unknown]'

			if rg != '[unknown]' and ct != '[unknown]':
				ct = '{ct} ({rg})'.format(ct=ct, rg=rg)

			if pr != '[unknown]' and ct != '[unknown]':
				pr = '{pr}; {ct}'.format(pr=pr, ct=ct)
			elif pr == '[unknown]' and ct != '[unknown]':
				pr = ct

			if len(pr) > 64:
				pr = pr[0:63]

			# this should already happen in 'citationbuilder.py'
			# pi = forceregexsafevariants(latindiacriticals(pi))
			# pr = forceregexsafevariants(latindiacriticals(pr))
			# dt = forceregexsafevariants(latindiacriticals(dt))

			if db[0:2] in ['in', 'ch']:
				tr = 'inscription'
				ty = 'inscription'
			elif db[0:2] in ['dp']:
				tr = 'papyrus'
				ty = 'papyrus'
			else:
				# but you actually have a big problem if you end up here
				tr = ''
				ty = ''

			# things we put in the annotations to the work itself

			td = re.search(textdirection, ln)
			try:
				td = 'textdirection: {d}'.format(d=td.group(1))
			except AttributeError:
				# 'NoneType' object has no attribute 'group'
				td = ''

			dn = re.search(doc, ln)
			try:
				dn = 'documentnumber: {n}'.format(n=dn.group(1))
			except AttributeError:
				dn = ''

			if td != '' or dn != '':
				newnotes = list()
				for n in [an, td, dn]:
					if n != '':
						newnotes.append(n)
				notes = '; '.join(newnotes)
			else:
				notes = ''

			# managed dict was a hassle; we have to do this in order and remember the order
			if idx != -999:
				metadatalist.append((wkid, pi, pr, dt, cd, tr, ty, (notes, idx)))
	
	return metadatalist


def modifyauthorsdb(newentryname, worktitle, dbcursor):
	"""
	the idxname of something like "ZZ0080" will be "Black Sea and Scythia Minor"
	the title of "in0001" should be set to "Black Sea and Scythia Minor IosPE I(2) [Scythia]"

	:param tempentryname:
	:param newentryname:
	:param worktitle:
	:param dbcursor:
	:return:
	"""

	worktitle = re.sub(r'`', '', worktitle)

	idx = worktitle
	clean = worktitle

	if newentryname[0:2] == 'dp':
		aka = worktitle
	else:
		aka = re.search(r'\((.*?)\)$', worktitle)
		try:
			aka = aka.group(1)
		except AttributeError:
			aka = worktitle

	if newentryname[0:2] == 'dp':
		short = worktitle
	else:
		short = re.search(r'\[(.*?)\]\)$', worktitle)
		try:
			short = short.group(1)
		except AttributeError:
			short = aka

	# do if... else... so that you don't do A then B (and pay the UPDATE price)
	if newentryname[0:2] in ['in', 'ch']:
		# inscription 'authors' can set their location via their idxname
		loc = re.search(r'(.*?)\s\(', worktitle)
		loc = loc.group(1)
		loc = forceregexsafevariants(loc)
		q = 'INSERT INTO authors (universalid, language, idxname, akaname, shortname, cleanname, location, recorded_date) ' \
				' VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
		d = (newentryname, 'G', idx, aka, short, clean, loc, 'Varia')
		dbcursor.execute(q, d)
	else:
		q = 'INSERT INTO authors (universalid, language, idxname, akaname, shortname, cleanname, recorded_date) ' \
				' VALUES (%s, %s, %s, %s, %s, %s, %s)'
		d = (newentryname, 'G', idx, aka, short, clean, 'Varia')
		dbcursor.execute(q, d)

	return


def insertnewworksintonewauthor(newwkuid, results, dbcursor):
	"""

	send me all of the matching lines from one db and i will build a new workdb with only these lines

	a sample result:

	(3166, 'YY0071w007', '411', '1', '1', '1', 'r', '1', '<hmu_metadata_provenance value="Herm nome?" /><hmu_metadata_date value="VII spc" /><hmu_metadata_documentnumber value="25" />☧ ἐὰν ϲχολάϲῃϲ <hmu_unconventional_form_written_by_scribe>ϲχολαϲειϲ</hmu_unconventional_form_written_by_scribe> θέλειϲ ἀπ̣ελθεῖν κα̣ὶ̣ ∙ε∙∙[ <hmu_latin_normal>c ̣ ]</hmu_latin_normal>', '☧ ἐὰν ϲχολάϲῃϲ ϲχολαϲειϲ θέλειϲ ἀπελθεῖν καὶ ∙ε∙∙ c  ', '☧ εαν ϲχολαϲηϲ ϲχολαϲειϲ θελειϲ απελθειν και ∙ε∙∙ c  ', '', '')


	:param newwkuid:
	:param results:
	:param dbcursor:
	:return:
	"""

	db = newwkuid[0:6]

	newdata = generatemodifiedtuples(results, newwkuid)

	separator = '\t'

	newstream = generatecopystream(newdata, separator=separator)

	columns = ('index',
				'wkuniversalid',
				'level_05_value',
				'level_04_value',
				'level_03_value',
				'level_02_value',
				'level_01_value',
				'level_00_value',
				'marked_up_line',
				'accented_line',
				'stripped_line',
				'hyphenated_words',
				'annotations')

	dbcursor.copy_from(newstream, db, sep=separator, columns=columns)

	return


def generatemodifiedtuples(results, newwkuid):
	"""

	:param results:
	:param newwkuid:
	:return:
	"""

	newdata = list()

	for r in results:
		r = list(r)
		# you need to have '-1' in the unused levels otherwise HipparchiaServer will have trouble building citations
		# level05 has been converted to the dbname, so we can discard it
		# level01 is sometimes used: 'recto', 'verso'
		# this is a problem since irregularly shaped works irritate HipparchiaServer
		# level04 will yield things like: 'face C, right'
		# this material will get merged with level01; but what sort of complications will arise?

		r[2] = '-1'  # level05
		if r[6] == '1':  # level 01
			r[6] = 'recto'

		for level in [3, 4, 5]:  # levels 04, 03, 02
			if r[level] != '1':
				if level != 4:
					# print('unusual level data:', db,r[0],level,r[level])
					pass
				r[6] = r[level] + ' ' + r[6]
			r[level] = '-1'

		# r[1] = tmpdbid: 'YY0071w007', vel sim
		# swap this out for newwkuid

		r = r[0:1] + [newwkuid] + r[2:]
		newdata.append(tuple(r))

	return newdata


def assignlanguagetonewworks(dbprefix):
	"""

	look at every work of the format 'inXXXX'

	determine the language of the work

	assign the language to the work

	painful/costly since most dbs are not swapping languages very often

	but the works table needs to know this if you are going to count genre weights properly

	:param dbprefix:
	:return:
	"""

	print('assigning language value to new works')

	dbc = setconnection()
	pgsqlcursor = dbc.cursor()

	q = 'SELECT * FROM works WHERE universalid ~ %s'
	d = ('^{p}'.format(p=dbprefix),)
	pgsqlcursor.execute(q, d)
	results = pgsqlcursor.fetchall()

	workslist = [dbOpus(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13], r[14], r[15], r[16], r[17], r[18], r[19]) for r in results]

	count = 0
	for w in workslist:
		count += 1
		q = 'SELECT stripped_line FROM {w} WHERE wkuniversalid=%s'.format(w=w.universalid[0:6])
		d = (w.universalid,)
		pgsqlcursor.execute(q, d)
		results = pgsqlcursor.fetchall()
		lines = [r[0] for r in results]
		w.language = determineworklanguage(lines)
		if count % 2000 == 0:
			dbc.commit()
		if count % 5000 == 0:
			print('\t{c} works parsed'.format(c=count))

	print('updating works table')
	languagetuplelist = [(w.universalid, w.language) for w in workslist]
	insertlanguagedata(languagetuplelist)

	return


def determineworklanguage(strippedlines):
	"""

	read a collection of lines

	determine their language by figuring out what character set most of the words are encoded in

	chh='abcdefghijklmnopqrstuvwxyz'
	timeit.timeit('sum([1 for l in "Traceback (most recent call last):" if l in chh])', globals=globals(), number=10000)
	0.04032713099149987

	islatin = re.compile(r'[a-z]')
	timeit.timeit('sum([1 for l in "Traceback (most recent call last):" if re.search(islatin, l)])', globals=globals(), number=10000)
	0.6780298129888251

	:param strippedline:
	:return:
	"""

	islatin = 'abcdefghijklmnopqrstuvwxyz'
	isgreek = 'αβψδεφγηιξκλμνοπϙρϲτυωςχθζ'

	greekchars = 0
	latinchars = 0

	for line in strippedlines:
		greekchars += sum([1 for g in line if g in isgreek])
		latinchars += sum([1 for l in line if l in islatin])

	if greekchars > latinchars:
		return 'G'
	else:
		return 'L'


def insertlanguagedata(languagetuplelist):
	"""

	avoid a long run of UPDATE statements: use a tmp table

	boundariestuplelist:
		[(universalid1, language1), (universalid2, language2), ...]


	:param languagetuplelist:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'CREATE TEMP TABLE tmp_works AS SELECT * FROM works LIMIT 0'
	dbcursor.execute(q)

	count = 0
	for l in languagetuplelist:
		count += 1
		q = 'INSERT INTO tmp_works (universalid, language) VALUES ( %s, %s)'
		d = l
		dbcursor.execute(q, d)
		if count % 5000 == 0:
			dbconnection.commit()

	dbconnection.commit()
	q = 'UPDATE works SET language = tmp_works.language FROM tmp_works WHERE works.universalid = tmp_works.universalid'
	dbcursor.execute(q)
	dbconnection.commit()

	q = 'DROP TABLE tmp_works'
	dbcursor.execute(q)

	dbconnection.connectioncleanup()

	return


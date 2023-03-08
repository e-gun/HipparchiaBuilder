# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-23
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import configparser
import re
import time
from multiprocessing import Manager
from os import path
from typing import List

import builder.dbinteraction.dbhelperfunctions
import builder.dbinteraction.dbprepsubstitutions
import builder.parsers.betacodefontshifts
from builder.builderclasses import dbAuthor
from builder.dbinteraction import dbloading
from builder.dbinteraction.connection import setconnection
from builder.dbinteraction.dbhelperfunctions import resetauthorsandworksdbs
from builder.dbinteraction.genericworkerobject import GenericInserterObject
from builder.dbinteraction.versioning import timestampthebuild
from builder.file_io import filereaders
from builder.parsers import idtfiles, parse_binfiles
from builder.parsers.betacodeandunicodeinterconversion import purgehybridgreekandlatinwords, replacegreekbetacode, \
	restoreromanwithingreek
from builder.parsers.betacodeescapedcharacters import replaceaddnlchars
from builder.parsers.betacodefontshifts import greekhmufontshiftsintospans, latinauthorlinemarkupprober, \
	latinfontlinemarkupprober, latinhmufontshiftsintospans, replacegreekmarkup
from builder.parsers.copticsubstitutions import replacecoptic
from builder.parsers.latinsubstitutions import latindiacriticals
from builder.parsers.regexsubstitutions import addcdlabels, cleanuplingeringmesses, colonshift, \
	debughostilesubstitutions, earlybirdsubstitutions, fixhmuoragnizationlinebyline, hexrunner, insertnewlines, \
	lastsecondsubsitutions, replacequotationmarks, totallemmatization, capitalvforcapitalu
from builder.postbuild.postbuildmetadata import buildtrigramindices, findwordcounts, insertfirstsandlasts
from builder.postbuild.secondpassdbrewrite import assignlanguagetonewworks, builddbremappers, compilenewauthors, \
	compilenewworks, insertnewworkdata
from builder.wordcounting.wordcountdbfunctions import deletetemporarydbs
from builder.workers import setworkercount

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')

try:
	cu = config['misc']['capu']
except KeyError:
	cu = 'y'

try:
	su = config['misc']['strictcapu']
except KeyError:
	su = 'n'

fixingcapu = True
strictcap = False

if cu == 'n':
	fixingcapu = False
if su == 'y':
	strictcap = True

authorneedscapufix = ['LAT0914', 'LAT2806']
# see tail of file for how to generate this list via "/testroute"
strictcapu = ['lt1672', 'lt1327', 'lt0490', 'lt0857', 'lt0458', 'lt0430', 'lt0515', 'lt0019', 'lt0524', 'lt2028', 'lt0640', 'lt1266', 'lt0574', 'lt9510', 'lt1221', 'lt0533', 'lt1248', 'lt0454', 'lt0473', 'lt0830', 'lt1236', 'lt1203', 'lt0446', 'lt0686', 'lt0821', 'lt0064', 'lt0582', 'lt0622', 'lt0596', 'lt0926', 'lt0046', 'lt0301', 'lt0845', 'lt0425', 'lt0067', 'lt0128', 'lt1348', 'lt0917', 'lt0408', 'lt0037', 'lt0470', 'lt1294', 'lt0444', 'lt0516', 'lt0631', 'lt1342', 'lt1023', 'lt0109', 'lt1209', 'lt0127', 'lt0661', 'lt0972', 'lt0002', 'lt0097', 'lt0073', 'lt0456', 'lt0448', 'lt2002', 'lt1041', 'lt0929', 'lt1285', 'lt1002', 'lt0460', 'lt0584', 'lt0409', 'lt0034', 'lt0981', 'lt0550', 'lt0085', 'lt0536', 'lt1011', 'lt0428', 'lt0635', 'lt0436', 'lt0727', 'lt0724', 'lt0500', 'lt0537', 'lt0620', 'lt0445', 'lt0025', 'lt0474', 'lt0634', 'lt0423', 'lt1218', 'lt0721', 'lt1339', 'lt0656', 'lt0709', 'lt0324', 'lt9221', 'lt0400', 'lt1363', 'lt1263', 'lt0625', 'lt0893', 'lt0327', 'lt0452', 'lt2302', 'lt0455', 'lt0022', 'lt0996', 'lt1056', 'lt1035', 'lt0615', 'lt0498', 'lt0935', 'lt0413', 'lt1500', 'lt1212', 'lt0932', 'lt0535', 'lt0469', 'lt0088', 'lt0528', 'lt0486', 'lt0911', 'lt0140', 'lt2349', 'lt0836', 'lt1000', 'lt1291', 'lt0526', 'lt0851', 'lt0978', 'lt2331', 'lt0860', 'lt0472', 'lt0130', 'lt2301', 'lt1206', 'lt0487', 'lt0959', 'lt0662', 'lt0043', 'lt0552', 'lt1318', 'lt1380', 'lt0812', 'lt0975', 'lt0682', 'lt1251', 'lt0556', 'lt0560', 'lt0094', 'lt0112', 'lt0512', 'lt1020', 'lt1017', 'lt0684', 'lt0303', 'lt3211', 'lt1351', 'lt0590', 'lt0079', 'lt1245', 'lt0484', 'lt0532', 'lt0541', 'lt1014', 'lt0488', 'lt1297', 'lt0118', 'lt0660', 'lt0451', 'lt0984', 'lt0594', 'lt0104', 'lt0530', 'lt0869', 'lt1044', 'lt0426', 'lt1242', 'lt0416', 'lt9500', 'lt1100']
strictcapu = [re.sub('lt', 'LAT', x) for x in strictcapu]
if strictcap:
	authorneedscapufix += strictcapu

authorneedscapufix = set(authorneedscapufix)


def buildcorpusdbs(corpusname, corpusvars):
	"""

	generic, unified corpus database builder

	will take all files that match a set of criteria and compile them into a set of tables under a given rubric

	[a] reset the corpus tables
	[b] acquire the raw data
	[c] parcel out the work to managedworker as a list of work items apportioned out to N mp jobs
	[d] managedworker() just pops a work item and sends it to addoneauthor()
	[e] addoneauthor() builds an authorobject and then calls thecollectedworksof()
	[f] thecollectedworksof() calls initialworkparsing(), secondaryworkparsing(), and then databaseloading()
	[g] databaseloading() calls dbprepper(), dbauthoradder(), authortablemaker(), and then insertworksintoauthortable()

	:param corpusname:
	:param corpusvars:
	:return:
	"""

	# to skip ahead to resetbininfo() for debugging purposes
	# iamdebugging = False
	# if iamdebugging:
	# 	return

	workercount = setworkercount()

	print('\ndropping any existing', corpusname, 'tables')
	if corpusvars[corpusname]['tmpprefix'] is not None:
		resetauthorsandworksdbs(corpusvars[corpusname]['tmpprefix'], corpusvars[corpusname]['corpusabbrev'])
		# immediately rewrite the table prefix to the first pass only value
		abbrev = corpusvars[corpusname]['tmpprefix']
	else:
		abbrev = corpusvars[corpusname]['corpusabbrev']
		resetauthorsandworksdbs(abbrev, abbrev)

	print()
	print(workercount, 'workers dispatched to build the', corpusname, 'dbs')
	if config['buildoptions']['buildlongestfirst'] == 'y':
		print('building the longest items first')

	dataprefix = corpusvars[corpusname]['dataprefix']
	datapath = corpusvars[corpusname]['datapath']
	lang = corpusvars[corpusname]['languagevalue']

	minfn = corpusvars[corpusname]['minfilenumber']
	maxfn = corpusvars[corpusname]['maxfilenumber']
	exclusions = corpusvars[corpusname]['exclusionlist']

	allauthors = filereaders.findauthors(datapath)
	allauthors = checkextant(allauthors, datapath)

	aa = list(allauthors.keys())
	# prune other dbs
	aa = [x for x in aa if dataprefix in x]
	aa.sort()
	listoftexts = list()
	# aa = []
	for a in aa:
		if minfn < int(a[3:]) < maxfn and int(a[3:]) not in exclusions:
			if lang != 'B':
				listoftexts.append(({a: allauthors[a]}, lang, abbrev, datapath, dataprefix))
			else:
				if re.search(r'Latin', allauthors[a]) is not None:
					listoftexts.append(({a: allauthors[a]}, 'L', abbrev, datapath, dataprefix))
				else:
					listoftexts.append(({a: allauthors[a]}, 'G', abbrev, datapath, dataprefix))

	# now sort by size: do the long ones first

	# thework looks like:
	# ({'LAT9254': '&1Titius&, gram.'}, 'L', 'lt', '../HipparchiaData/latin/', 'LAT'), ({'LAT9500': '&1Anonymi& Epici et Lyrici'}, 'L', 'lt', '../HipparchiaData/latin/', 'LAT'), ({'LAT9505': '&1Anonymi& Comici et Tragici'}, 'L', 'lt', '../HipparchiaData/latin/', 'LAT'), ({'LAT9510': '&1Anonymi& Grammatici'}, 'L', 'lt', '../HipparchiaData/latin/', 'LAT'), ({'LAT9969': '&1Vita& Iuvenalis'}, 'L', 'lt', '../HipparchiaData/latin/', 'LAT')

	if config['buildoptions']['buildlongestfirst'] == 'y':
		sorter = dict()
		count = 0
		for t in listoftexts:
			count += 1
			c = t[0].copy()
			s = path.getsize('{p}{id}.TXT'.format(p=t[3], id=c.popitem()[0]))
			# avoid key collisions by adding a unique fraction to the size
			sorter[s+(1/count)] = t

		# don't reverse the keys because popping from the stack later is itself a reversal
		listoftexts = [sorter[sz] for sz in sorted(sorter.keys())]

	manager = Manager()
	managedwork = manager.list(listoftexts)

	workerobject = GenericInserterObject(managedworker, argumentlist=[managedwork])
	workerobject.dothework()

	return


def remaptables(corpusname, corpusvars):
	"""

	see the comments at secondpassdbrewrite.py for what we are doing and why

	basically INS, DDP, and CHR megafiles are getting broken up into smaller units

	:param corpusname:
	:param corpusvars:
	:return:
	"""

	if corpusvars[corpusname]['tmpprefix'] is not None:
		needsremapping = True
	else:
		needsremapping = False

	if needsremapping:
		tmpprefix = corpusvars[corpusname]['tmpprefix']
		permprefix = corpusvars[corpusname]['corpusabbrev']

		print('\nremapping the', corpusname, 'data: turning works into authors and embedded documents into individual works')
		aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
		newauthors = compilenewauthors(aumapper, wkmapper)
		newworktuples = compilenewworks(newauthors, wkmapper)
		insertnewworkdata(newworktuples)
		assignlanguagetonewworks(permprefix)
		deletetemporarydbs(tmpprefix)

	return


def buildcorpusmetadata(corpusname, corpusvars):
	"""

	now that you have the core data for a corpus, record its metadata

	:param corpusname:
	:param corpusvars:
	:return:
	"""

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	print('\ncompiling metadata for', corpusname, 'dbs')

	workcategoryprefix = corpusvars[corpusname]['corpusabbrev']

	# is there metadata contained in a binfile? if so, load it
	if corpusname == 'latin':
		parse_binfiles.latinloadcanon(corpusvars[corpusname]['datapath'] + corpusvars[corpusname]['dataprefix'] + '9999.TXT', dbcursor)
		parse_binfiles.insertlatingenres(dbconnection)
		dbconnection.commit()
	if corpusname == 'greek':
		parse_binfiles.resetbininfo(corpusvars[corpusname]['datapath'], dbconnection)
		dbconnection.commit()

	# generate the metadata from the data we built
	insertfirstsandlasts(workcategoryprefix)
	dbconnection.commit()
	buildtrigramindices(workcategoryprefix)
	findwordcounts(dbconnection)
	timestampthebuild(workcategoryprefix)

	dbconnection.connectioncleanup()

	return


def managedworker(managedwork, dbconnection):
	"""

	build individual authors in parallel via multiprocessing manager

	doing this via a Pool will break the list into N chunks of identical sizes

	BUT there is a radical disparity between the sizes of authors; the result
	is that with a large number of workers you will see that only 2 or 3 are
	really working in the end: they got stuck with a sequence of 'long' authors
	while some others had runs of short ones

	accordingly this version is signifcantly faster if you have, say, 12 threads
	available to you

	:param managedwork:
	:return:
	"""

	if not dbconnection:
		dbconnection = setconnection()

	while managedwork:
		try:
			thework = managedwork.pop()
		except IndexError:
			thework = None

		if thework:
			result = addoneauthor(thework[0], thework[1], thework[2], thework[3], thework[4], dbconnection)
			msg = re.sub(r'[^\x00-\x7F]+', ' ', result)
			print('\t{msg}'.format(msg=msg))

		r = len(managedwork)
		if r > 0 and not r % 50:
			print('{r} items remain'.format(r=r))

	return


def checkextant(authorlist, datapath):
	"""

	make sure that the names on the list correspond to files that are available

	:param authorlist:
	:param datapath:
	:return:
	"""
	pruneddict = dict()

	for key, value in authorlist.items():
		try:
			open(datapath+key+'.TXT', 'rb')
			pruneddict[key] = value
		except:
			# print(value,'not available:',datapath+key+'.TXT cannot be found.')
			pass

	return pruneddict


def addoneauthor(authordict, language, uidprefix, datapath, dataprefix, dbconnection, debugoutput=False, debugnewlines=True, skipdbload=False):
	"""

	I need an authtab pair within a one-item dict: {'0022':'Marcus Porcius &1Cato&\x80Cato'}
	Then I will go to work and run the full suite

	:param authordict:
	:param language:
	:param uidprefix:
	:param datapath:
	:param dataprefix:
	:param dbconnection:
	:param cursor:
	:return:
	"""

	starttime = time.time()
	(number, name), = authordict.items()
	authorobj = buildauthorobject(number, language, datapath, uidprefix, dataprefix)
	authorobj.addauthtabname(name)
	authorobj.language = language
	thecollectedworksof(authorobj, language, datapath, dbconnection, debugoutput, debugnewlines, skipdbload)
	buildtime = round(time.time() - starttime, 2)
	success = number+' '+authorobj.cleanname+' '+str(buildtime)+'s'
	
	return success


def thecollectedworksof(authorobject: dbAuthor, language: str, datapath: str, dbconnection, debugoutput=False, debugnewlines=True, skipdbload=False):
	"""
	give me a authorobject and i will build you a corpus in three stages
	[a] initial parsing of original files
	[b] secondary parsing of intermediate files
	[c] loading the info into the db

	:return:
	"""
	txt = initialworkparsing(authorobject, language, datapath, debugoutput, debugnewlines)
	txt = secondaryworkparsing(authorobject, txt, debugoutput, debugnewlines)
	if not skipdbload:
		databaseloading(txt, authorobject, dbconnection)
	else:
		print(authorobject.cleanname, 'built but not loaded')

	return


def buildauthorobject(authortabnumber, language, datapath, uidprefix, dataprefix):
	"""

	construct an author object

	example input values
		INS0110
		G
		../HipparchiaData/phi7/
		in
		INS

	here is where you will stand after running this:

	# >>> e = buildauthor('0006','greek','/Volumes/TLG_E/TLG')
	# >>> e.idxname
	# '&1Euripides& Trag.'
	# >>> e.number
	# '0006'
	# >>> e.works
	# [<builder.builder_classes.Opus object at 0x10dff5128>, <builder.builder_classes.Opus object at 0x10dff5198>,...
	# >>> for w in e.works: print(w.title)
	# >>> e.works[1].structure
	# {0: 'line', 1: 'Fragment'}

	:param authortabnumber:
	:param language:
	:param datapath:
	:param uidprefix:
	:param dataprefix:
	:return:
	"""

	with open(datapath+authortabnumber+'.IDT', 'rb') as f:
		authoridt = f.read()

	authorobj = idtfiles.loadauthor(authoridt, language, uidprefix, dataprefix)

	return authorobj


def initialworkparsing(authorobject, language, datapath, debugoutput=False, debugnewlines=True) -> str:
	"""

	grab a raw file and start cleaning it up; the order of files and of items within files usually matters
	for example, do '%20' searches before '%2' searches unless you want to write more regex

	in the end you will have a parsed stream: still no newlines
	greek will be in unicode; the internal formatting will now have pseudotags surrounding it
	mostly done pulling it out of the native format
	seek in the files you can produce at this juncture for 'unhandled' items, etc if you want to make things look prettier later

	:param authorobject:
	:param language:
	:param datapath:
	:return:
	"""

	outputdir = config['io']['outputdir']
	outsuffix = config['io']['debugoutfile']
	filename = '{dir}{af}_1{count}_{fnc}{suffix}'

	thetext = filereaders.highunicodefileload(datapath + authorobject.dataprefix+authorobject.number + '.TXT')

	thisauthor = authorobject.dataprefix+authorobject.number
	if fixingcapu and thisauthor in authorneedscapufix:
		thetext = capitalvforcapitalu(thetext)

	initial = [earlybirdsubstitutions, replacequotationmarks, replaceaddnlchars]
	greekmiddle = [colonshift, replacegreekmarkup, replacecoptic, latinfontlinemarkupprober,
	               replacegreekbetacode, restoreromanwithingreek, greekhmufontshiftsintospans]
	latinmiddle = [latinauthorlinemarkupprober, latindiacriticals, latinhmufontshiftsintospans]
	final = [cleanuplingeringmesses, purgehybridgreekandlatinwords]

	if language == 'G' and authorobject.language == 'G':
		functionlist = initial + greekmiddle + final
	else:
		functionlist = initial + latinmiddle + final

	count = 0
	for f in functionlist:
		thetext = f(thetext)

		if debugoutput:
			count += 1
			fn = filename.format(dir=outputdir, af=authorobject.dataprefix+authorobject.number, count=chr(count+96), fnc=getattr(f, '__name__'), suffix=outsuffix)
			if debugnewlines:
				filereaders.streamout(re.sub(' █', '\n█', thetext), fn)
			else:
				filereaders.streamout(thetext, fn)

	return thetext


def secondaryworkparsing(authorobject, thetext: str, debugoutput=False, debugnewlines=True) -> List[str]:
	"""

	the next big step is turning the datastream into a citeable text
	this requires the magical turning of the hex control codes into tags that will themselves get reparsed
	the datastream is about to start having 'lines' and these are going to be counted and sorted, etc.

	:param authorobject:
	:param thetext:
	:return:
	"""
	outputdir = config['io']['outputdir']
	outsuffix = config['io']['debugoutfile']
	filename = '{dir}{af}_2{count}_{fnc}{suffix}'

	# first: the two-argument function
	thetext = addcdlabels(thetext, authorobject.number)

	if debugoutput:
		count = 1
		fn = filename.format(dir=outputdir, af=authorobject.dataprefix + authorobject.number, count=chr(count + 96), fnc='addcdlabels', suffix=outsuffix)

		if debugnewlines:
			filereaders.streamout(re.sub(' █', '\n█', thetext), fn)
		else:
			filereaders.streamout(thetext, fn)

	# next, the one-argument functions
	functionlist = [hexrunner, lastsecondsubsitutions, debughostilesubstitutions, insertnewlines, fixhmuoragnizationlinebyline, totallemmatization]

	count = 1
	for f in functionlist:
		# note that we are shifting types in the course of this: str -> str; str -> list; list -> list
		thetext = f(thetext)

		if debugoutput:
			if isinstance(thetext, list):
				outputfunction = filereaders.linesout
			else:
				outputfunction = filereaders.streamout
			count += 1
			fn = filename.format(dir=outputdir, af=authorobject.dataprefix+authorobject.number, count=chr(count+96), fnc=getattr(f, '__name__'), suffix=outsuffix)

			if debugnewlines and not isinstance(thetext, list):
				outputfunction(re.sub(' █', '\n█', thetext), fn)
			else:
				outputfunction(thetext, fn)

	return thetext


def databaseloading(dbreadyversion: list, authorobject: dbAuthor, dbconnection):
	"""

	a little more cleaning, then insert this material into the database
	time to hand things off to HipparchiaServer

	:param dbreadyversion:
	:param authorobject:
	:param dbconnection:
	:param cursor:
	:return:
	"""

	dbreadyversion = builder.dbinteraction.dbprepsubstitutions.dbprepper(dbreadyversion)
	# pickle.dump(dbreadyversion, outputfile, open( "wb"))
	builder.dbinteraction.dbhelperfunctions.dbauthoradder(authorobject, dbconnection)
	builder.dbinteraction.dbhelperfunctions.authortablemaker(authorobject.universalid, dbconnection)
	dbloading.insertworksintoauthortable(authorobject, dbreadyversion, dbconnection)

	# to debug return dbreadyversion
	return


"""
	# find authors that have a 'U' in them
	lt = {x for x in authordict if x[0:2] == 'lt'}
	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()
	problematic = list()
	for au in lt:
		q = "select marked_up_line from {x} where marked_up_line like '%U%' limit 1;".format(x=au)
		cursor.execute(q)
		f = cursor.fetchone()
		if f:
			print('{a}\t{b}'.format(a=au, b=f))
			problematic.append(au)
	print('has CAP-U', problematic)
	
"""
# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import configparser
import re
import time
from multiprocessing import Pool

import builder.dbinteraction.dbprepsubstitutions
import builder.parsers.betacodefontshifts
from builder.dbinteraction import db
from builder.file_io import filereaders
from builder.parsers import idtfiles, parse_binfiles
from builder.dbinteraction.db import setconnection, resetauthorsandworksdbs
from builder.postbuild.postbuildmetadata import insertfirstsandlasts, findwordcounts, buildtrigramindices
from builder.dbinteraction.versioning import timestampthebuild
from builder.postbuild.secondpassdbrewrite import builddbremappers, compilenewauthors, compilenewworks, registernewworks
from builder.postbuild.postbuildhelperfunctions import deletetemporarydbs
from builder.workers import setworkercount
from builder.parsers.betacodeescapedcharacters import replaceaddnlchars
from builder.parsers.betacodefontshifts import replacegreekmarkup, replacelatinmarkup
from builder.parsers.betacodeandunicodeinterconversion import replacegreekbetacode, restoreromanwithingreek, purgehybridgreekandlatinwords
from builder.parsers.regex_substitutions import cleanuplingeringmesses, earlybirdsubstitutions, replacelatinbetacode, \
	replacequotationmarks, findromanwithingreek, addcdlabels, hexrunner, lastsecondsubsitutions, debughostilesubstitutions, \
	totallemmatization

config = configparser.ConfigParser()
config.read('config.ini')


def buildcorpusdbs(corpusname, corpusvars):
	"""

	generic, unified corpus database builder

	will take all files that match a set of criteria and compile them into a set of tables under a given rubric

	:param corpusname:
	:return:
	"""

	workercount = setworkercount()

	print('\ndropping any existing', corpusname, 'tables')
	if corpusvars[corpusname]['tmpprefix'] is not None:
		resetauthorsandworksdbs(corpusvars[corpusname]['tmpprefix'], corpusvars[corpusname]['corpusabbrev'])
		# immediately rewrite the table prefix to the first pass only value
		abbrev = corpusvars[corpusname]['tmpprefix']
	else:
		abbrev = corpusvars[corpusname]['corpusabbrev']
		resetauthorsandworksdbs(abbrev, abbrev)

	print('\n',workercount,'workers dispatched to build the', corpusname, 'dbs')

	dataprefix = corpusvars[corpusname]['dataprefix']
	datapath = corpusvars[corpusname]['datapath']
	lang = corpusvars[corpusname]['languagevalue']

	min = corpusvars[corpusname]['minfilenumber']
	max = corpusvars[corpusname]['maxfilenumber']
	exclusions = corpusvars[corpusname]['exclusionlist']

	allauthors = filereaders.findauthors(datapath)
	allauthors = checkextant(allauthors, datapath)

	aa = list(allauthors.keys())
	# prune other dbs
	aa = [x for x in aa if dataprefix in x]
	aa.sort()
	thework = []
	# aa = []
	for a in aa:
		if min < int(a[3:]) < max and int(a[3:]) not in exclusions:
			if lang != 'B':
				thework.append(({a: allauthors[a]}, lang, abbrev, datapath, dataprefix))
			else:
				if re.search(r'Latin', allauthors[a]) is not None:
					thework.append(({a: allauthors[a]}, 'L', abbrev, datapath, dataprefix))
				else:
					thework.append(({a: allauthors[a]}, 'G', abbrev, datapath, dataprefix))

	pool = Pool(processes=workercount)
	pool.map(parallelworker, thework)

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

	if needsremapping == True:
		tmpprefix = corpusvars[corpusname]['tmpprefix']
		permprefix = corpusvars[corpusname]['corpusabbrev']

		print('\nremapping the',corpusname,'data: turning works into authors and embedded documents into individual works')
		aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
		newauthors = compilenewauthors(aumapper, wkmapper)
		newworktuples = compilenewworks(newauthors, wkmapper)
		registernewworks(newworktuples)
		deletetemporarydbs(tmpprefix)

	return


def buildcorpusmetadata(corpusname, corpusvars):
	"""

	now that you have the core data for a corpus, record its metadata

	:param corpusname:
	:param corpusvars:
	:return:
	"""

	dbconnection = setconnection(config)
	cursor = dbconnection.cursor()

	print('\ncompiling metadata for', corpusname, 'dbs')

	workcategoryprefix = corpusvars[corpusname]['corpusabbrev']

	# is there metadata contained in a binfile? if so, load it
	if corpusname == 'latin':
		parse_binfiles.latinloadcanon(corpusvars[corpusname]['datapath'] + corpusvars[corpusname]['dataprefix'] + '9999.TXT', cursor)
		parse_binfiles.insertlatingenres(cursor, dbconnection)
		dbconnection.commit()
	if corpusname == 'greek':
		parse_binfiles.resetbininfo(corpusvars[corpusname]['datapath'], cursor, dbconnection)
		dbconnection.commit()

	# generate the metadata from the data we built
	insertfirstsandlasts(workcategoryprefix, cursor)
	dbconnection.commit()
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)
	timestampthebuild(workcategoryprefix, dbconnection, cursor)
	dbconnection.commit()

	return


def parallelworker(thework):
	dbc = setconnection(config)
	cur = dbc.cursor()
	result = addoneauthor(thework[0], thework[1], thework[2], thework[3], thework[4], dbc, cur)
	print(re.sub(r'[^\x00-\x7F]+', ' ', result))
	dbc.commit()
	del dbc

	return


def checkextant(authorlist,datapath):
	"""
	make sure that the names on the list correspond to files that are available
	"""
	pruneddict = {}
	for key,value in authorlist.items():
		try:
			open(datapath+key+'.TXT', 'rb')
			pruneddict[key] = value
		except:
			# print(value,'not available:',datapath+key+'.TXT cannot be found.')
			pass

	return pruneddict


def addoneauthor(authordict, language, uidprefix, datapath, dataprefix, dbconnection, cursor):
	"""
	I need an authtab pair within a one-item dict: {'0022':'Marcus Porcius &1Cato&\x80Cato'}
	Then I will go to work and run the full suite
	:param authordict:
	:param language: 'greek' or 'latin'
	:param datapath:
	:param dbconnection:
	:param cursor:
	:return:
	"""

	starttime = time.time()
	(number,name), = authordict.items()
	authorobj = buildauthor(number, language, datapath, uidprefix, dataprefix)
	authorobj.addauthtabname(name)
	authorobj.language = language
	thecollectedworksof(authorobj, language, datapath,  dbconnection, cursor)
	buildtime =  round(time.time() - starttime,2)
	success = number+' '+authorobj.cleanname+' '+str(buildtime)+'s'
	
	return success


def thecollectedworksof(authorobject, language, datapath,  dbconnection, cursor):
	"""
	give me a authorobject and i will build you a corpus in three stages
	[a] initial parsing of original files
	[b] secondary parsing of intermediate files
	[c] loading the info into the db

	:return:
	"""
	txt = initialworkparsing(authorobject, language, datapath)
	txt = secondaryworkparsing(authorobject, txt)
	databaseloading(txt, authorobject,  dbconnection, cursor)

	return


def buildauthor(authortabnumber, language, datapath, uidprefix, dataprefix):
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

	:param authortabnumber: something like '0007'
	:param language: 'greek' or 'latin'
	:return: a populated author object
	"""

	authoridt = filereaders.loadidt(datapath+authortabnumber+'.IDT')
	authorobj = idtfiles.loadauthor(authoridt, language, uidprefix, dataprefix)

	return authorobj


def initialworkparsing(authorobject, language, datapath):
	"""
	grab a raw file and start cleaning it up; the order of files and of items within files usually matters
	for example, do '%20' searches before '%2' searches unless you want to write more regex

	in the end you will have a parsed stream: still no newlines
	greek will be in unicode; the internal formatting will now have pseudotags surrounding it
	mostly done pulling it out of the native format
	seek in the files you can produce at this juncture for 'unhandled' items, etc if you want to make things look prettier later

	:param authortabnumber:
	:param language:
	:param datapath:
	:return: a parsed stream
	"""

	txt = filereaders.highunicodefileload(datapath + authorobject.dataprefix+authorobject.number + '.TXT')
	txt = earlybirdsubstitutions(txt)
	txt = replacequotationmarks(txt)
	txt = replaceaddnlchars(txt)
	# now you are about to get a bunch of brackets added to the data via hmu_markup
	if language == 'G' and authorobject.language == 'G':
		# where else/how else to handle colons?
		txt = re.sub(r':','·',txt)
		txt = findromanwithingreek(txt)
		txt = replacegreekmarkup(txt)
		txt = replacelatinmarkup(txt)
		txt = replacegreekbetacode(txt)
		txt = restoreromanwithingreek(txt)
	else:
		txt = replacelatinmarkup(txt)
		txt = replacelatinbetacode(txt)

	# last pass to mitigate the 'αugusto λeone anno χϝι et ξonstantino' problem
	txt = cleanuplingeringmesses(txt)
	txt = purgehybridgreekandlatinwords(txt)

	return txt


def secondaryworkparsing(authorobject, txt):
	"""
	the next big step is turning the datastream into a citeable text
	this requires the magical turning of the hex control codes into tags that will themselves get reparsed
	the datastream is about to start having 'lines' and these are going to be counted and sorted, etc.

	:param parserdata:
	:return:
	"""
	lemmatized = addcdlabels(txt, authorobject.number)
	lemmatized = hexrunner(lemmatized)
	lemmatized = lastsecondsubsitutions(lemmatized)
	lemmatized = debughostilesubstitutions(lemmatized)
	lemmatized = re.sub(r'(<hmu_set_level)', r'\n\1', lemmatized)

	lemmatized = lemmatized.split('\n')
	dbreadyversion = totallemmatization(lemmatized,authorobject)

	return dbreadyversion


def databaseloading(dbreadyversion, authorobject,  dbconnection, cursor):
	"""
	a little more cleaning, then insert this material into the database
	time to hand things off to HipparchiaServer

	:param parserdata:
	:return:
	"""
	dbreadyversion = builder.dbinteraction.dbprepsubstitutions.dbprepper(dbreadyversion)
	# pickle.dump(dbreadyversion, outputfile, open( "wb"))
	db.dbcitationinsert(authorobject, dbreadyversion, cursor, dbconnection)

	# to debug return dbreadyversion
	return

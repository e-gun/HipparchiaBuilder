# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import configparser
import re
import time
from multiprocessing import Pool

import builder.dbinteraction.dbprepsubstitutions
from builder.dbinteraction import db
from builder.file_io import filereaders
from builder.parsers import idtfiles, regex_substitutions, betacode_to_unicode, parse_binfiles
from builder.dbinteraction.db import setconnection

config = configparser.ConfigParser()
config.read('config.ini')


def parallelbuildlatincorpus(latindatapath):
	"""
	the whole enchilada
	you a few shifts in the comments and conditionals will let you build portions instead
	:return:
	"""
	dataprefix = 'LAT'
	alllatinauthors = filereaders.findauthors(latindatapath)
	alllatinauthors = checkextant(alllatinauthors, latindatapath)
	
	al = list(alllatinauthors.keys())
	al = [x for x in al if x[0:3] == dataprefix]
	al = [x for x in al if int(x[3:]) < 9999]
	al.sort()
	thework = []
	# al = []
	
	for a in al:
		thework.append(({a: alllatinauthors[a]}, 'L', 'lt', latindatapath, dataprefix))
	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelworker, thework)
	
	return True


def parallelbuildgreekcorpus(greekdatapath):
	"""
	the whole enchilada
	you a few shifts in the comments and conditionals will let you build portions instead
	:return:
	"""
	dataprefix = 'TLG'
	allgreekauthors = filereaders.findauthors(greekdatapath)
	allgreekauthors = checkextant(allgreekauthors, greekdatapath)
	
	ag = list(allgreekauthors.keys())
	ag = [x for x in ag if x[0:3] == dataprefix]
	ag = [x for x in ag if int(x[3:]) < 9999]
	ag.sort()
	thework = []
	# ag = []
	
	for a in ag:
		thework.append(({a: allgreekauthors[a]}, 'G', 'gr', greekdatapath, dataprefix))
	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelworker, thework)

	return True


def parallelbuildinscriptionscorpus(insdatapath, temporaryprefix):
	"""
	the whole enchilada
	you a few shifts in the comments and conditionals will let you build portions instead
	:return:
	"""
	dataprefix = 'INS'
	allinscriptions = filereaders.findauthors(insdatapath)
	allinscriptions = checkextant(allinscriptions, insdatapath)
	
	ai = list(allinscriptions.keys())
	# prune other dbs
	ai = [x for x in ai if dataprefix in x]
	ai = [x for x in ai if int(x[3:]) < 8000]

	# the bibliographies are
	#   INS8000 Delphi Bibliography [inscriptions] 31.56s
	#   INS9900 Bibliography [Epigr., general] [inscriptions] 1.86s
	#   INS9930 Bibliography [Epigr., Caria] [inscriptions] 21.97s
	#   INS9920 Bibliography [Epigr., Ionia] [inscriptions] 23.66s
	ai.sort()
	thework = []
	# ai = []
	for a in ai:
		if re.search(r'Latin', allinscriptions[a]) is not None:
			thework.append(({a: allinscriptions[a]}, 'L', temporaryprefix, insdatapath, dataprefix))
		else:
			thework.append(({a: allinscriptions[a]}, 'G', temporaryprefix, insdatapath, dataprefix))
	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelworker, thework)
	
	return True


def parallelbuildpapyrusscorpus(papdatapath, temporaryprefix):
	"""
	the whole enchilada
	you a few shifts in the comments and conditionals will let you build portions instead
	:return:
	"""
	dataprefix = 'DDP'
	allpapyri = filereaders.findauthors(papdatapath)
	allpapyri = checkextant(allpapyri, papdatapath)

	ap = list(allpapyri.keys())
	# prune other dbs
	ap = [x for x in ap if dataprefix in x]
	ap.sort()
	thework = []
	# ap = []
	for a in ap:
		if int(a[3:]) < 9999:
			thework.append(({a: allpapyri[a]}, 'G', temporaryprefix, papdatapath, dataprefix))
	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelworker, thework)

	return True


def parallelbuildchristianinscriptions(chrdatapath, temporaryprefix):
	"""
	the whole enchilada
	you a few shifts in the comments and conditionals will let you build portions instead
	:return:
	"""
	dataprefix = 'CHR'
	allchr = filereaders.findauthors(chrdatapath)
	allchr = checkextant(allchr, chrdatapath)

	ac = list(allchr.keys())
	# prune other dbs
	ac = [x for x in ac if dataprefix in x]
	ac.sort()
	thework = []
	# ac = []
	for a in ac:
		if int(a[3:]) < 1000 and int(a[3:]) != 21:
			# CHR0021 Judaica [Hebrew/Aramaic]
			# don't know how to read either language
			if re.search(r'Latin', allchr[a]) is not None:
				thework.append(({a: allchr[a]}, 'L', temporaryprefix, chrdatapath, dataprefix))
			else:
				thework.append(({a: allchr[a]}, 'G', temporaryprefix, chrdatapath, dataprefix))
	pool = Pool(processes=int(config['io']['workers']))
	pool.map(parallelworker, thework)

	return True


def parallelworker(thework):
	dbc = setconnection(config)
	cur = dbc.cursor()
	result = addoneauthor(thework[0], thework[1], thework[2], thework[3], thework[4], dbc, cur)
	print(re.sub(r'[^\x00-\x7F]+', ' ', result))
	dbc.commit()

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
	author = buildauthor(number, language, datapath, uidprefix, dataprefix)
	author.addauthtabname(name)
	author.language = language
	thecollectedworksof(author, language, datapath,  dbconnection, cursor)
	buildtime =  round(time.time() - starttime,2)
	success = number+' '+author.cleanname+' '+str(buildtime)+'s'
	
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
	# concordance.buildconcordances(authorobject.universalid, dbconnection, cursor)

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
	txt = regex_substitutions.earlybirdsubstitutions(txt)
	txt = regex_substitutions.replacequotationmarks(txt)
	txt = regex_substitutions.replaceaddnlchars(txt)
	# now you are about to get a bunch of brackets added to the data via hmu_markup
	if language == 'G' and authorobject.language == 'G':
		# where else/how else to handle colons?
		txt = re.sub(r':','·',txt)
		txt = regex_substitutions.findromanwithingreek(txt)
		txt = regex_substitutions.replacegreekmarkup(txt)
		txt = regex_substitutions.replacelatinmarkup(txt)
		txt = betacode_to_unicode.replacegreekbetacode(txt)
		txt = betacode_to_unicode.restoreromanwithingreek(txt)
	else:
		txt = regex_substitutions.replacelatinmarkup(txt)
		txt = regex_substitutions.replacelatinbetacode(txt)

	# last pass to mitigate the 'αugusto λeone anno χϝι et ξonstantino' problem
	txt = regex_substitutions.cleanuplingeringmesses(txt)
	txt = betacode_to_unicode.purgehybridgreekandlatinwords(txt)

	return txt


def secondaryworkparsing(authorobject, txt):
	"""
	the next big step is turning the datastream into a citeable text
	this requires the magical turning of the hex control codes into tags that will themselves get reparsed
	the datastream is about to start having 'lines' and these are going to be counted and sorted, etc.

	:param parserdata:
	:return:
	"""
	lemmatized = regex_substitutions.addcdlabels(txt, authorobject.number)
	lemmatized = regex_substitutions.hexrunner(lemmatized)
	lemmatized = regex_substitutions.lastsecondsubsitutions(lemmatized)
	lemmatized = regex_substitutions.debughostilesubstitutions(lemmatized)
	lemmatized = re.sub(r'(<hmu_set_level)', r'\n\1', lemmatized)

	lemmatized = lemmatized.split('\n')
	dbreadyversion = regex_substitutions.totallemmatization(lemmatized,authorobject)

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



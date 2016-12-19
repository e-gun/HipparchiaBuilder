# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import time
import configparser
from builder.dbinteraction.db import setconnection
from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatliddellandscott, formatlewisandshort, grammarloader, analysisloader
from builder.dbinteraction.postbuildmetadata import insertfirstsandlasts, findwordcounts, buildtrigramindices
from builder.dbinteraction.secondpassdbrewrite import builddbremappers, compilenewauthors, compilenewworks

config = configparser.ConfigParser()
config.read('config.ini')

buildgreekauthors = config['build']['buildgreekauthors']
buildlatinauthors = config['build']['buildlatinauthors']
buildinscriptions = config['build']['buildinscriptions']
buildpapyri = config['build']['buildpapyri']
buildlex = config['build']['buildlex']
buildgram = config['build']['buildgram']

dbconnection = setconnection(config)
# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = dbconnection.cursor()

tlg = config['io']['tlg']
phi = config['io']['phi']
ins = config['io']['ins']
ddp = config['io']['ddp']

start = time.time()

if buildlatinauthors == 'y':
	workcategoryprefix = 'lt'
	print('building latin dbs')
	corpus_builder.parallelbuildlatincorpus(phi, cursor)
	print('compiling metadata for latin dbs')
	insertfirstsandlasts(workcategoryprefix, cursor, dbconnection)
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)

if buildgreekauthors == 'y':
	workcategoryprefix = 'gr'
	print('building greek dbs')
	corpus_builder.parallelbuildgreekcorpus(tlg, dbconnection, cursor)
	print('compiling metadata for greek dbs')
	insertfirstsandlasts(workcategoryprefix, cursor, dbconnection)
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)

if buildinscriptions == 'y':
	workcategoryprefix = 'ZZ'
	print('building inscription dbs')
	corpus_builder.parallelbuildinscriptionscorpus(ins, workcategoryprefix)
	aumapper, wkmapper = builddbremappers('ZZ', 'in', cursor)
	newauthors = compilenewauthors(aumapper, wkmapper, cursor)
	compilenewworks(newauthors, wkmapper, cursor)
	print('compiling metadata for inscription dbs')
	workcategoryprefix = 'in'
	insertfirstsandlasts(workcategoryprefix, cursor, dbconnection)
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)

if buildpapyri == 'y':
	workcategoryprefix = 'dp'
	print('building papyrus dbs')
	corpus_builder.parallelbuildpapyrusscorpus(ddp)
	print('compiling metadata for papyrus dbs')
	insertfirstsandlasts(workcategoryprefix, cursor, dbconnection)
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)

if buildlex == 'y':
	print('building lexical dbs')
	formatliddellandscott(dbconnection, cursor, '../')
	formatlewisandshort(dbconnection, cursor, '../')

if buildgram == 'y':
	print('building grammar dbs')
	grammarloader('gl', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/greek-analyses.txt', 'greek_morphology', 'g', dbconnection, cursor)
	grammarloader('ll', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/latin-analyses.txt', 'latin_morphology', 'l', dbconnection, cursor)

stop = time.time()
took = round((stop-start)/60, 2)
print('\nBuild took',str(took),'minutes')


# 4 Workers on G&L authors:
# Build took 40.32 minutes


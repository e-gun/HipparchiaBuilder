# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import configparser
import time

from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatliddellandscott, formatlewisandshort, grammarloader, analysisloader
from builder.dbinteraction.db import setconnection
from builder.postbuild.postbuildmetadata import insertfirstsandlasts, findwordcounts, buildtrigramindices
from builder.postbuild.secondpassdbrewrite import builddbremappers, compilenewauthors, compilenewworks, deletetemporarydbs, resetauthorsandworksdbs

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

# note the dbcitationinsert() has a check for the dbprefix that constrains your choice of tmp values here
# if you fail the match, then you will overwrite things like the level05 data that you need later
if buildinscriptions == 'y':
	tmpprefix = 'XX'
	permprefix = 'in'
	print('purging the old inscription dbs')
	resetauthorsandworksdbs(permprefix)
	print('building inscription dbs')
	corpus_builder.parallelbuildinscriptionscorpus(ins, tmpprefix)
	print('remapping the inscription dbs: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	newauthors = compilenewauthors(aumapper, wkmapper)
	compilenewworks(newauthors, wkmapper)
	deletetemporarydbs(tmpprefix)
	print('compiling metadata for inscription dbs')
	insertfirstsandlasts(permprefix, cursor, dbconnection)
	buildtrigramindices(permprefix, cursor)
	findwordcounts(cursor, dbconnection)

if buildpapyri == 'y':
	tmpprefix = 'YY'
	permprefix = 'dp'
	print('purging the old papyrus dbs')
	resetauthorsandworksdbs(permprefix)
	print('building papyrus dbs')
	corpus_builder.parallelbuildpapyrusscorpus(ddp, tmpprefix)
	print('remapping the inscription dbs: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	newauthors = compilenewauthors(aumapper, wkmapper)
	compilenewworks(newauthors, wkmapper)
	deletetemporarydbs(tmpprefix)
	print('compiling metadata for inscription dbs')
	insertfirstsandlasts(permprefix, cursor, dbconnection)
	buildtrigramindices(permprefix, cursor)
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


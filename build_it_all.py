# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import time

from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatliddellandscott, formatlewisandshort, grammarloader, analysisloader
from builder.dbinteraction.db import setconnection, resetauthorsandworksdbs
from builder.postbuild.postbuildmetadata import insertfirstsandlasts, findwordcounts, buildtrigramindices
from builder.postbuild.secondpassdbrewrite import builddbremappers, compilenewauthors, compilenewworks, deletetemporarydbs
from builder.dbinteraction.versioning import timestampthebuild
from builder.parsers import parse_binfiles

config = configparser.ConfigParser()
config.read('config.ini')

buildgreekauthors = config['build']['buildgreekauthors']
buildlatinauthors = config['build']['buildlatinauthors']
buildinscriptions = config['build']['buildinscriptions']
buildpapyri = config['build']['buildpapyri']
buildchristians = config['build']['buildchristians']
buildlex = config['build']['buildlex']
buildgram = config['build']['buildgram']


dbconnection = setconnection(config)
# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = dbconnection.cursor()

tlg = config['io']['tlg']
phi = config['io']['phi']
ins = config['io']['ins']
ddp = config['io']['ddp']
chr = config['io']['chr']

start = time.time()

if buildlatinauthors == 'y':
	workcategoryprefix = 'lt'
	print('building latin dbs')
	corpus_builder.parallelbuildlatincorpus(phi)
	dataprefix = 'LAT'
	parse_binfiles.latinloadcanon(phi + dataprefix + '9999.TXT', cursor)
	dbconnection.commit()
	print('compiling metadata for latin dbs')
	insertfirstsandlasts(workcategoryprefix, cursor)
	dbconnection.commit()
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)
	timestampthebuild(workcategoryprefix, dbconnection, cursor)
	dbconnection.commit()

if buildgreekauthors == 'y':
	workcategoryprefix = 'gr'
	print('building greek dbs')
	corpus_builder.parallelbuildgreekcorpus(tlg)
	parse_binfiles.resetbininfo(tlg, cursor, dbconnection)
	dbconnection.commit()
	print('compiling metadata for greek dbs')
	insertfirstsandlasts(workcategoryprefix, cursor)
	dbconnection.commit()
	buildtrigramindices(workcategoryprefix, cursor)
	findwordcounts(cursor, dbconnection)
	timestampthebuild(workcategoryprefix, dbconnection, cursor)

# note the dbcitationinsert() has a check for the dbprefix that constrains your choice of tmp values here
# if you fail the match, then you will overwrite things like the level05 data that you need later
if buildinscriptions == 'y':
	tmpprefix = 'XX'
	permprefix = 'in'
	print('dropping any existing inscription tables')
	resetauthorsandworksdbs(tmpprefix, permprefix)
	print('building inscription data')
	corpus_builder.parallelbuildinscriptionscorpus(ins, tmpprefix)
	print('remapping the inscription data: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	print('aumapper, wkmapper', aumapper, wkmapper)
	newauthors = compilenewauthors(aumapper, wkmapper)
	compilenewworks(newauthors, wkmapper)
	deletetemporarydbs(tmpprefix)
	print('compiling metadata for inscription dbs')
	insertfirstsandlasts(permprefix, cursor)
	dbconnection.commit()
	buildtrigramindices(permprefix, cursor)
	findwordcounts(cursor, dbconnection)
	timestampthebuild(permprefix, dbconnection, cursor)
	dbconnection.commit()

if buildpapyri == 'y':
	tmpprefix = 'YY'
	permprefix = 'dp'
	print('dropping any existing papyrus tables')
	resetauthorsandworksdbs(tmpprefix, permprefix)
	print('building papyrus data')
	corpus_builder.parallelbuildpapyrusscorpus(ddp, tmpprefix)
	print('remapping the inscription data: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	newauthors = compilenewauthors(aumapper, wkmapper)
	compilenewworks(newauthors, wkmapper)
	deletetemporarydbs(tmpprefix)
	print('compiling metadata for inscription dbs')
	insertfirstsandlasts(permprefix, cursor)
	dbconnection.commit()
	buildtrigramindices(permprefix, cursor)
	findwordcounts(cursor, dbconnection)
	timestampthebuild(permprefix, dbconnection, cursor)
	dbconnection.commit()

if buildchristians == 'y':
	tmpprefix = 'ZZ'
	permprefix = 'ch'
	print('dropping any existing christian inscription tables')
	resetauthorsandworksdbs(tmpprefix, permprefix)
	print('building christian inscription data')
	corpus_builder.parallelbuildchristianinscriptions(chr, tmpprefix)
	print('remapping the inscription data: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	newauthors = compilenewauthors(aumapper, wkmapper)
	compilenewworks(newauthors, wkmapper)
	deletetemporarydbs(tmpprefix)
	print('compiling metadata for inscription dbs')
	insertfirstsandlasts(permprefix, cursor)
	dbconnection.commit()
	buildtrigramindices(permprefix, cursor)
	findwordcounts(cursor, dbconnection)
	timestampthebuild(permprefix, dbconnection, cursor)
	dbconnection.commit()

if buildlex == 'y':
	print('building lexical dbs')
	formatliddellandscott(dbconnection, cursor, '../')
	formatlewisandshort(dbconnection, cursor, '../')
	timestampthebuild('lx', dbconnection, cursor)
	dbconnection.commit()

if buildgram == 'y':
	print('building grammar dbs')
	grammarloader('gl', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/greek-analyses.txt', 'greek_morphology', 'g', dbconnection, cursor)
	grammarloader('ll', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/latin-analyses.txt', 'latin_morphology', 'l', dbconnection, cursor)
	timestampthebuild('lm', dbconnection, cursor)
	dbconnection.commit()

stop = time.time()
took = round((stop-start)/60, 2)
print('\nBuild took',str(took),'minutes')


# 4 Workers on G&L authors:
# Build took 40.32 minutes


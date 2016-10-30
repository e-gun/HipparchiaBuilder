# -*- coding: utf-8 -*-
#!../bin/python
import time
import configparser
from builder.dbinteraction.db import setconnection
from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatliddellandscott, formatlewisandshort, grammarloader, analysisloader
from builder.dbinteraction.postbuildmetadata import insertfirstsandlasts, findwordcounts, buildtrigramindices

config = configparser.ConfigParser()
config.read('config.ini')

buildauthors = config['build']['buildauthors']
buildlex = config['build']['buildlex']
buildgram = config['build']['buildgram']
buildstats = config['build']['buildstats']

dbconnection = setconnection(config)
# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = dbconnection.cursor()

tlg = config['io']['tlg']
phi = config['io']['phi']

start = time.time()

if buildauthors == 'y':
	print('building author and work dbs')
	corpus_builder.parallelbuildcorpus(tlg, phi, dbconnection, cursor)

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

if buildstats == 'y':
	print('compiling statistics')
	insertfirstsandlasts(cursor, dbconnection)
	findwordcounts(cursor, dbconnection)
	buildtrigramindices(cursor)

stop = time.time()
took = round((stop-start)/60, 2)
print('\nBuild took',str(took),'minutes')


# 4 Workers on G&L authors:
# Build took 78.26 minutes

# no concordances:
# Build took 40.32 minutes


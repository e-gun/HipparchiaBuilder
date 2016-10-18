# -*- coding: utf-8 -*-
#!../bin/python
import time
import configparser
from builder.dbinteraction.db import setconnection
from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatliddellandscott, formatlewisandshort, grammarloader, analysisloader
from builder.dbinteraction.postbuildstatistics import insertfirstsandlasts, findwordcounts

buildauthors = True
buildlex = True
buildgram = True
buildstats = True

config = configparser.ConfigParser()
config.read('config.ini')

dbconnection = setconnection(config)
# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = dbconnection.cursor()

tlg = config['io']['tlg']
phi = config['io']['phi']

start = time.time()

if buildauthors == True:
	print('building author and work dbs')
	# remember to set a reasonable number of workers: a virtual box with one core and .5G of RAM does not want 6 workers
	corpus_builder.parallelbuildcorpus(tlg, phi, dbconnection, cursor)

if buildlex == True:
	print('building lexical dbs')
	formatliddellandscott(dbconnection, cursor, '../')
	formatlewisandshort(dbconnection, cursor, '../')

if buildgram == True:
	print('building grammar dbs')
	grammarloader('gl', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/greek-analyses.txt', 'greek_morphology', 'g', dbconnection, cursor)
	grammarloader('ll', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/latin-analyses.txt', 'latin_morphology', 'l', dbconnection, cursor)

if buildstats == True:
	print('compiling statistics')
	insertfirstsandlasts(cursor, dbconnection)
	findwordcounts(cursor, dbconnection)

stop = time.time()
took = round((stop-start)/60, 2)
print('\nBuild took',str(took),'minutes')


# 4 Workers on G&L authors:
# Build took 78.26 minutes



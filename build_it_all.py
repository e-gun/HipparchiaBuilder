# -*- coding: utf-8 -*-
#!../bin/python
import configparser
from builder import dbinteraction
from builder import corpus_builder
from builder.dbinteraction.build_lexica import *


buildauthors = True
buildlex = False
buildgram = False

config = configparser.ConfigParser()
config.read('config.ini')
dbconnection = dbinteraction.db.setconnection(config)
# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = dbconnection.cursor()

tlg = config['io']['tlg']
phi = config['io']['phi']

start = time.time()

if buildauthors == True:
	# remember to set a reasonable number of workers: a virtual box with one core and .5G of RAM does not want 6 workers
	corpus_builder.parallelbuildcorpus(tlg, phi, dbconnection, cursor)
	# corpus_builder.serialbuildcorpus(tlg, phi, dbconnection, cursor)

if buildlex == True:
	formatlewisandshort(dbconnection, cursor, '../')
	formatliddellandscott(dbconnection, cursor, '../')

if buildgram == True:
	grammarloader('gl', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/greek-analyses.txt', 'greek_morphology', 'g', dbconnection, cursor)
	grammarloader('ll', '../HipparchiaData/lexica/', dbconnection, cursor)
	analysisloader('../HipparchiaData/lexica/latin-analyses.txt', 'latin_morphology', 'l', dbconnection, cursor)

stop = time.time()
took = round((stop-start)/60, 2)
print('\nBuild took',str(took),'minutes')


# 4 Workers:
# Build took 78.26 minutes



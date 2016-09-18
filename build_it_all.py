# -*- coding: utf-8 -*-
#!../bin/python
import psycopg2
import configparser
import time
from builder import dbinteraction
from builder import file_io
from builder import parsers
from builder import corpus_builder
from builder.dbinteraction.build_lexica import *

config = configparser.ConfigParser()
config.read('config.ini')

buildauthors = True
buildlex = False
buildgram = False


start = time.time()

dbconnection = dbinteraction.db.setconnection(config)

# dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = dbconnection.cursor()

tlg = config['io']['tlg']
phi = config['io']['phi']

if buildauthors == True:
	corpus_builder.buildcorpus(tlg, phi, dbconnection, cursor)

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

# greek and latin authors
# Build took 235.02 minutes


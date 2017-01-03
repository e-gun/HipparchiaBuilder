# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import time

from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatliddellandscott, formatlewisandshort, grammarloader, analysisloader
from builder.dbinteraction.db import setconnection
from builder.dbinteraction.versioning import timestampthebuild

config = configparser.ConfigParser()
config.read('config.ini')

buildgreekauthors = config['corporatobuild']['buildgreekauthors']
buildlatinauthors = config['corporatobuild']['buildlatinauthors']
buildinscriptions = config['corporatobuild']['buildinscriptions']
buildpapyri = config['corporatobuild']['buildpapyri']
buildchristians = config['corporatobuild']['buildchristians']
buildlex = config['corporatobuild']['buildlex']
buildgram = config['corporatobuild']['buildgram']


dbconnection = setconnection(config)
cursor = dbconnection.cursor()


start = time.time()

corpusvars = {
	'latin':
			{'dataprefix': 'LAT',
			'datapath': config['io']['phi'],
			'tmpprefix': None,
			'corpusabbrev': 'lt',
			'maxfilenumber': 9999,  # canon at 9999
			'minfilenumber': 0,
			'exclusionlist': [],
			'languagevalue': 'L'
			},
	'greek':
			{'dataprefix': 'TLG',
			'datapath': config['io']['tlg'],
			'tmpprefix': None,
			'corpusabbrev': 'gk',
			'maxfilenumber': 9999,
			'minfilenumber': 0,
			'exclusionlist': [],
			'languagevalue': 'G'
			},
	'inscriptions':
			{'dataprefix': 'INS',
			'datapath': config['io']['ins'],
			'tmpprefix': 'XX',
			'corpusabbrev': 'in',
			'maxfilenumber': 8000,  # 8000+ are bibliographies
			'minfilenumber': 0,
			'exclusionlist': [],
			'languagevalue': 'B'
			},
	'papyri':
			{'dataprefix': 'DDP',
			'datapath': config['io']['ddp'],
			'tmpprefix': 'YY',
			'corpusabbrev': 'dp',
			'maxfilenumber': 1000,  # maxval is 213; checklist at 9999
			'minfilenumber': 6,
			'exclusionlist': [],
			'languagevalue': 'B'
			},
	'christians':
			{'dataprefix': 'CHR',
			'datapath': config['io']['chr'],
			'tmpprefix': 'ZZ',
			'corpusabbrev': 'ch',
			'maxfilenumber': 1000,  # maxval is 140; bibliographies at 9900 and 9910
			'minfilenumber': 0,
			'exclusionlist': [21],  # CHR0021 Judaica [Hebrew/Aramaic]; don't know how to read either language
			'languagevalue': 'B'
			}
}

#
# corpora
#

corporatobuild = []

if buildlatinauthors == 'y':
	corporatobuild.append('latin')

if buildgreekauthors == 'y':
	corporatobuild.append('greek')

if buildinscriptions == 'y':
	corporatobuild.append('inscriptions')

if buildpapyri == 'y':
	corporatobuild.append('papyri')

if buildchristians == 'y':
	corporatobuild.append('christians')

for corpusname in corporatobuild:
	corpus_builder.buildcorpusdbs(corpusname, corpusvars)
	corpus_builder.remaptables(corpusname, corpusvars)
	corpus_builder.buildcorpusmetadata(corpusname, corpusvars)


#
# lexica, etc
#

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


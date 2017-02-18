# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import time

from builder import corpus_builder
from builder.dbinteraction.build_lexica import formatgklexicon, formatlatlexicon, grammarloader, analysisloader
from builder.dbinteraction.db import setconnection
from builder.dbinteraction.versioning import timestampthebuild
from builder.postbuild.databasewordcounts import wordcounter, formcounter

config = configparser.ConfigParser()
config.read('config.ini')

buildgreekauthors = config['corporatobuild']['buildgreekauthors']
buildlatinauthors = config['corporatobuild']['buildlatinauthors']
buildinscriptions = config['corporatobuild']['buildinscriptions']
buildpapyri = config['corporatobuild']['buildpapyri']
buildchristians = config['corporatobuild']['buildchristians']
buildlex = config['corporatobuild']['buildlex']
buildgram = config['corporatobuild']['buildgram']
buildcounts = config['corporatobuild']['buildwordcounts']

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
			'corpusabbrev': 'gr',
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
			'maxfilenumber': 5000,  # maxval is 213; checklist at 9999
			'minfilenumber': 0,
			'exclusionlist': [],
			'languagevalue': 'B'
			},
	'christians':
			{'dataprefix': 'CHR',
			'datapath': config['io']['chr'],
			'tmpprefix': 'ZZ',
			'corpusabbrev': 'ch',
			'maxfilenumber': 5000,  # maxval is 140; bibliographies at 9900 and 9910
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
	formatgklexicon()
	formatlatlexicon()
	timestampthebuild('lx', dbconnection, cursor)
	dbconnection.commit()

if buildgram == 'y':
	print('building grammar dbs')
	#grammarloader('greek')
	analysisloader('greek')
	#grammarloader('latin')
	analysisloader('latin')
	timestampthebuild('lm', dbconnection, cursor)
	dbconnection.commit()

if buildcounts == 'y':
	print('building wordcounts by (repeatedly) examining every line of every text in all available dbs: this might take a minute or two...')
	# first draft speed: 2061919 distinct words found; Build took 58.17 minutes
	# mp: Build took 23.17 minutes
	wordcounter()
	# Build took 17.54 minutes
	formcounter()

stop = time.time()
took = round((stop-start)/60, 2)
print('\nBuild took',str(took),'minutes')


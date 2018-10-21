#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import time
from multiprocessing import freeze_support

from builder import corpusbuilder
from builder.dbinteraction.versioning import timestampthebuild
from builder.lexica.buildlexica import analysisloader, formatgklexicon, formatlatlexicon, grammarloader
from builder.wordcounting.databasewordcounts import mpwordcounter, monowordcounter
from builder.wordcounting.wordcountsbyheadword import headwordcounts

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

if __name__ == '__main__':
	freeze_support()

	corporatobuild = list()

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
		corpusbuilder.buildcorpusdbs(corpusname, corpusvars)
		corpusbuilder.remaptables(corpusname, corpusvars)
		corpusbuilder.buildcorpusmetadata(corpusname, corpusvars)


	#
	# lexica, etc
	#

	if buildlex == 'y':
		print('building lexical dbs')
		formatgklexicon()
		formatlatlexicon()
		timestampthebuild('lx')

	if buildgram == 'y':
		print('building grammar dbs')
		grammarloader('greek')
		analysisloader('greek')
		grammarloader('latin')
		analysisloader('latin')
		timestampthebuild('lm')

	if buildcounts == 'y':
		print('building wordcounts by (repeatedly) examining every line of every text in all available dbs: this might take a minute or two...')
		# this can be dangerous if the number of workers is high and the RAM available is not substantial; not the most likely configuration?
		# mpwordcounter() is the hazardous one; if your survive it headwordcounts() will never get you near the same level of resource use
		# mpwordcounter(): Build took 8.69 minutes
		if 0 > 1:
			# does not return counts properly: see notes
			mpwordcounter()
		else:
			monowordcounter()
		headwordcounts()
		# if you do genres, brace yourself: Build took 84.11 minutes

	stop = time.time()
	took = round((stop-start)/60, 2)
	print('\nBuild took', str(took), 'minutes')

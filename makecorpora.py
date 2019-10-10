#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import time
from multiprocessing import freeze_support
from pathlib import Path

try:
	import psutil
except ModuleNotFoundError:
	psutil = None

from builder import corpusbuilder
from builder.configureatlaunch import getcommandlineargs, tobuildaccordingtoconfigfile
from builder.dbinteraction.versioning import timestampthebuild
from builder.lexica.buildlexica import analysisloader, formatgklexicon, formatlatlexicon, grammarloader
from builder.wordcounting.databasewordcounts import monowordcounter
from builder.wordcounting.loadwordcoundsfromsql import wordcountloader
from builder.wordcounting.wordcountsbyheadword import headwordcounts

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')

tobuild = tobuildaccordingtoconfigfile()
commandlineargs = getcommandlineargs()
additionalchecks = [commandlineargs.all, commandlineargs.allbutwordcounts, commandlineargs.allcorpora, commandlineargs.sqlloadwordcounts]
ovverride = {getattr(commandlineargs, k) for k in tobuild.keys() if getattr(commandlineargs, k)}.union({a for a in additionalchecks if a})

if ovverride:
	if commandlineargs.all:
		tobuild = {k: True for k in tobuild.keys()}
	elif commandlineargs.allbutwordcounts:
		tobuild = {k: True for k in tobuild.keys()}
		tobuild['wordcounts'] = False
	elif commandlineargs.allcorpora:
		tobuild = {k: True for k in tobuild.keys()}
		tobuild['wordcounts'] = False
		tobuild['lex'] = False
		tobuild['gram'] = False
	elif commandlineargs.sqlloadwordcounts:
		tobuild = {k: False for k in tobuild.keys()}
		tobuild['wordcounts'] = True
	else:
		tobuild = {k: getattr(commandlineargs, k) for k in tobuild.keys()}

# print([a for a in tobuild if tobuild[a]])

start = time.time()

corpusvars = {
	'latin':
			{'dataprefix': 'LAT',
			'datapath': config['io']['phi'],
			'tmpprefix': None,
			'corpusabbrev': 'lt',
			'maxfilenumber': 9999,  # canon at 9999
			'minfilenumber': 0,
			'exclusionlist': list(),
			'languagevalue': 'L'
			},
	'greek':
			{'dataprefix': 'TLG',
			'datapath': config['io']['tlg'],
			'tmpprefix': None,
			'corpusabbrev': 'gr',
			'maxfilenumber': 9999,
			'minfilenumber': 0,
			'exclusionlist': list(),
			'languagevalue': 'G'
			},
	'inscriptions':
			{'dataprefix': 'INS',
			'datapath': config['io']['ins'],
			'tmpprefix': 'XX',
			'corpusabbrev': 'in',
			'maxfilenumber': 8000,  # 8000+ are bibliographies
			'minfilenumber': 0,
			'exclusionlist': list(),
			'languagevalue': 'B'
			},
	'papyri':
			{'dataprefix': 'DDP',
			'datapath': config['io']['ddp'],
			'tmpprefix': 'YY',
			'corpusabbrev': 'dp',
			'maxfilenumber': 5000,  # maxval is 213; checklist at 9999
			'minfilenumber': 0,
			'exclusionlist': list(),
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

	if tobuild['latinauthors']:
		corporatobuild.append('latin')

	if tobuild['greekauthors']:
		corporatobuild.append('greek')

	if tobuild['inscriptions']:
		corporatobuild.append('inscriptions')

	if tobuild['papyri']:
		corporatobuild.append('papyri')

	if tobuild['christians']:
		corporatobuild.append('christians')

	for corpusname in corporatobuild:
		corpusbuilder.buildcorpusdbs(corpusname, corpusvars)
		corpusbuilder.remaptables(corpusname, corpusvars)
		corpusbuilder.buildcorpusmetadata(corpusname, corpusvars)

	#
	# lexica, etc
	#

	if tobuild['lex']:
		print('building lexical dbs')
		formatgklexicon()
		formatlatlexicon()
		timestampthebuild('lx')

	if tobuild['gram']:
		print('building grammar dbs')
		grammarloader('greek')
		analysisloader('greek')
		grammarloader('latin')
		analysisloader('latin')
		timestampthebuild('lm')

	if tobuild['wordcounts']:
		sqlcounts = False
		try:
			if config['corporatobuild']['loadwordcountsviasql'] == 'y':
				sqlcounts = True
		except KeyError:
			# you have an old config.ini that does not include this option
			print('please set "loadwordcountsviasql" to "y" or "n" under "corporatobuild" in "config.ini"')
			sqlcounts = False
		if commandlineargs.sqlloadwordcounts:
			print('loading wordcounts from sql dumps')
			p = Path(config['wordcounts']['wordcountdir'])
			wordcountloader(p.resolve())
		elif sqlcounts:
			print('loading wordcounts from sql dumps')
			p = Path(config['wordcounts']['wordcountdir'])
			wordcountloader(p.resolve())
		else:
			print('building wordcounts by (repeatedly) examining every line of every text in all available dbs: this might take a minute or two...')
			if psutil:
				installedmem = psutil.virtual_memory().total / 1024 / 1024 / 1024
				requiredmem = 12
				if installedmem < requiredmem:
					badnews = """
				WARNING: 
					c. {r}G RAM is required to build the wordcounts.
					You have {i}G of RAM installed. 
					The counts might fail.
					If they do not fail, the count might be quite slow (because of "swapping")
					[only the viery first set of counts requires the 12G of RAM]
				WARNING
					"""
					print(badnews.format(r=requiredmem, i=installedmem))
			# this can be dangerous if the number of workers is high and the RAM available is not substantial; not the most likely configuration?
			# mpwordcounter() is the hazardous one; if your survive it headwordcounts() will never get you near the same level of resource use
			# mpwordcounter(): Build took 8.69 minutes
			if 0 > 1:
				# does not return counts properly: see notes
				mpwordcounter()
			else:
				# see note on rediswordcounter(): do not use...
				# rediswordcounter()
				monowordcounter()
			headwordcounts()
			# if you do genres, brace yourself: Build took 84.11 minutes

	stop = time.time()
	took = round((stop-start)/60, 2)
	print('\nBuild took', str(took), 'minutes')

#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import gzip
from glob import glob
from subprocess import run

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


def wordcountloader():
	"""

	load the wordcount files from an archives set of wordcounts

	permission problems are likely:
		export PGPASSWORD="HIPPAWRPASSHERE"


	$ psql --clean -U {user-name} -d {desintation_db} -f {dumpfilename.sql}

	:return:
	"""
	try:
		wordcountdir = config['wordcounts']['wordcountdir']
	except KeyError:
		print('"wordcountdir" not set in "config.ini": aborting')
		return

	wordcountfiles = glob(wordcountdir + '*sql.gz')
	tempfile = wordcountdir+'/temp.sql'

	for f in wordcountfiles:
		print('loading', f)
		with gzip.open(f, 'r') as f:
			contents = f.read()
		with open(tempfile, encoding='utf-8', mode='r') as f:
			f.write(contents)
		arguments = list()
		arguments.append('psql')
		arguments.append('--clean')
		arguments.append('-U {u}'.format(u=config['db']['DBUSER']))
		arguments.append('-d {d}'.format(d=config['db']['DBNAME']))
		arguments.append('-f {f}'.format(f=tempfile))
		run(arguments)
		run(['rm', tempfile])
	return

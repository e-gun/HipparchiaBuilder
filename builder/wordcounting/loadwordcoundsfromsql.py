#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import gzip
import os
import re
import subprocess
from pathlib import Path

from builder.dbinteraction.connection import setconnection

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


def wordcountloader(pathtowordcounts: Path):
	"""

	load the wordcount files from an archives set of wordcounts

	permission problems are likely:
		export PGPASSWORD="HIPPAWRPASSHERE"

	$ psql --clean -U {user-name} -d {desintation_db} -f {dumpfilename.sql}

	:return:
	"""
	dbconnection = setconnection(autocommit=True)
	dbcursor = dbconnection.cursor()

	addtoenv = {'PGPASSWORD': config['db']['DBPASS']}
	theenv = {**os.environ, **addtoenv}

	p = pathtowordcounts
	# print('p', p.parts)

	wordcountfiles = sorted(p.glob('*sql.gz'))
	tempfile = p / 'temp.sql'
	tempfile.touch(mode=0o600)

	deltemplate = """
	DROP TABLE {t}
	"""

	for f in wordcountfiles:
		thetable = f.stem
		thetable = re.sub(r'\.sql', '', thetable)
		print('\tloading', thetable)
		try:
			dbcursor.execute(deltemplate.format(t=thetable))
		except:
			# psycopg2.errors.UndefinedTable
			pass

		with gzip.open(f, 'r') as f:
			contents = f.read()
		tempfile.write_text(contents.decode('utf-8'))

		arguments = list()
		arguments.append('psql')
		arguments.append('-U')
		arguments.append('{u}'.format(u=config['db']['DBUSER']))
		arguments.append('-d')
		arguments.append('{d}'.format(d=config['db']['DBNAME']).strip())
		arguments.append('-h')
		arguments.append('{h}'.format(h=config['db']['DBHOST']).strip())
		arguments.append('-p')
		arguments.append('{p}'.format(p=config['db']['DBPORT']).strip())
		arguments.append('-f')
		arguments.append('{f}'.format(f=tempfile))
		subprocess.run(arguments, env=theenv, stdout=subprocess.DEVNULL)
		tempfile.unlink()
	return

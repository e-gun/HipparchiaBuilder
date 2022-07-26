#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
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
from builder.configureatlaunch import getcommandlineargs

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


commandlineargs = getcommandlineargs()

try:
	subprocess.run(['psql', '-V'])
	WIN = str()
except FileNotFoundError:
	WIN = '/Program Files/PostgreSQL/{psq}/bin/psql.exe'.format(psq=commandlineargs.pgversion)
	print('NOTE: assuming PostgreSQL installed at: "{p}"'.format(p=WIN))
	print('but the major version number might be off; be prepared to edit the value of PSQLVERSION at the top of')
	print('"configureatlaunch.py" inside of "/buidler/" AND/OR send the proper version via the command line:')
	print('"./makecorpora.py --pgversion 14 ...')


def archivedsqlloader(pathtosqlarchive: Path):
	"""

	load the wordcount files from an archives set of wordcounts

	also works for the grammar dumps

	note that the name of the dump file has to match the name of the target table or bad things will happen

	permission problems are likely:
		export PGPASSWORD="HIPPAWRPASSHERE"

	$ psql --clean -U {user-name} -d {desintation_db} -f {dumpfilename.sql}

	:return:
	"""
	dbconnection = setconnection(autocommit=True)
	dbcursor = dbconnection.cursor()

	addtoenv = {'PGPASSWORD': config['db']['DBPASS']}
	theenv = {**os.environ, **addtoenv}

	p = pathtosqlarchive
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
		try:
			subprocess.run(arguments, env=theenv, stdout=subprocess.DEVNULL)
		except FileNotFoundError:
			# Windows....
			arguments[0] = WIN
			subprocess.run(arguments, env=theenv, stdout=subprocess.DEVNULL)
		tempfile.unlink()
	return

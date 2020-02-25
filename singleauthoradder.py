#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import argparse
import configparser

from builder.corpusbuilder import addoneauthor, buildauthorobject
from builder.dbinteraction.connection import setconnection
from builder.file_io.filereaders import findauthors
from builder.postbuild.postbuildmetadata import boundaryfinder, calculatewordcounts, insertboundaries, insertcounts
from builder.postbuild.secondpassdbrewrite import builddbremappers, compilenewauthors, compilenewworks, \
	insertnewworkdata
from builder.wordcounting.wordcountdbfunctions import deletetemporarydbs

"""
use this script to build and insert a single author into the database

WARNING: 

at the moment this will harmlessly overwrite TLG and LAT authors

but this script will RUIN any INS, DDP, or CHR database since the remapper will pick
'new' IDs that are certainly already in use: it will start with '0001'.

this can be fixed by dodging builddbremappers() and instead deriving the ids from the extant data

"""
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')

outputdir = config['io']['outputdir']
debugoutfile = config['io']['debugoutfile']
tlg = config['io']['tlg']
phi = config['io']['phi']
ddp = config['io']['ddp']
ins = config['io']['ins']

debugauthor = 'TLG0085'
commandlineparser = argparse.ArgumentParser(description='pick the author to add; default is currently {d}'.format(d=debugauthor))
commandlineparser.add_argument('--au', required=False, type=str, help='set author value [TLG/LAT + NNNN][INS/DDP/CHR work, but this will *damage* the current installation]')
commandlineparser.add_argument('--debugoutput', action='store_true', help='generate the debug files in "{loc}"; add newlines after control sequences'.format(loc=outputdir))
commandlineparser.add_argument('--debugoutputallowlonglines', action='store_true', help='generate the debug files and allow output files with a single (very, very long) line'.format(loc=outputdir))
commandlineparser.add_argument('--skipdbload', action='store_true', help='skip db insertion; just generate the debug files')
commandlineargs = commandlineparser.parse_args()

useoutputfiles = False
usenewlines = False

if commandlineargs.au:
	debugauthor = commandlineargs.au

if commandlineargs.debugoutput:
	useoutputfiles = True
	usenewlines = True

if commandlineargs.debugoutputallowlonglines:
	useoutputfiles = True
	usenewlines = False

if commandlineargs.skipdbload:
	useoutputfiles = True

mapper = {
	'TLG': {'lg': 'G', 'db': tlg, 'uidprefix': 'gr', 'datapath': config['io']['tlg'], 'tmpprefix': None},
	'LAT': {'lg': 'L', 'db': phi, 'uidprefix': 'lt', 'datapath': config['io']['phi'], 'tmpprefix': None},
	'INS': {'lg': 'G', 'db': ins, 'uidprefix': 'in', 'datapath': config['io']['ins'], 'tmpprefix': 'XX'},
	'DDP': {'lg': 'G', 'db': ddp, 'uidprefix': 'dp', 'datapath': config['io']['ddp'], 'tmpprefix': 'YY'},
	'CHR': {'lg': 'G', 'db': chr, 'uidprefix': 'ch', 'datapath': config['io']['chr'], 'tmpprefix': 'ZZ'},
	}

dataprefix = debugauthor[0:3]
lg = mapper[dataprefix]['lg']
db = mapper[dataprefix]['db']
datapath = mapper[dataprefix]['datapath']
uidprefix = mapper[dataprefix]['uidprefix']
remap = mapper[dataprefix]['tmpprefix']

if remap:
	uidprefix = remap

allauthors = findauthors(datapath)
myauthorname = allauthors[debugauthor]
authordict = {debugauthor: myauthorname}

dbc = setconnection(config)
cur = dbc.cursor()
result = addoneauthor(authordict, lg, uidprefix, datapath, dataprefix, dbc, debugoutput=useoutputfiles, debugnewlines=usenewlines, skipdbload=commandlineargs.skipdbload)
print(result)
dbc.commit()

if remap:
	tmpprefix = remap
	permprefix = mapper[dataprefix]['uidprefix']
	print('\nremapping the', debugauthor,'data: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	newauthors = compilenewauthors(aumapper, wkmapper)
	newworktuples = compilenewworks(newauthors, wkmapper)
	insertnewworkdata(newworktuples)
	deletetemporarydbs(tmpprefix)
else:
	a = buildauthorobject(debugauthor, lg, db, uidprefix, dataprefix)
	newauthors = [a]

if not commandlineargs.skipdbload:
	# firsts and lasts
	for a in newauthors:
		print('inserting work db metatata: firsts and lasts')
		query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid DESC'
		data = (a.universalid+'%',)
		cur.execute(query, data)
		results = cur.fetchall()
		uids = [r[0] for r in results]

		boundaries = boundaryfinder(uids)
		insertboundaries(boundaries)

	# wordcounts
	for a in newauthors:
		print('inserting work db metatata: wordcounts')
		query = 'SELECT universalid FROM works WHERE wordcount IS NULL ORDER BY universalid ASC'
		cur.execute(query)
		results = cur.fetchall()
		dbc.commit()

		uids = [r[0] for r in results]

		counts = calculatewordcounts(uids)
		insertcounts(counts)

del dbc

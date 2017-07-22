#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

debugauthor = 'TLG1342'

"""
use this script to build and insert a single author into the database

WARNING: 

at the moment this will harmlessly overwrite TLG and LAT authors

but this script will RUIN any INS, DDP, or CHR database since the remapper will pick
'new' IDs that are certainly already in use: it will start with '0001'.

this can be fixed by dodging builddbremappers() and instead deriving the ids from the extant data

"""

import configparser
from builder.file_io.filereaders import findauthors
from builder.corpus_builder import addoneauthor, buildauthorobject
from builder.dbinteraction.connection import setconnection
from builder.postbuild.secondpassdbrewrite import builddbremappers, compilenewauthors, compilenewworks, registernewworks
from builder.postbuild.postbuildhelperfunctions import deletetemporarydbs
from builder.postbuild.postbuildmetadata import boundaryfinder, insertboundaries, calculatewordcounts, insertcounts

config = configparser.ConfigParser()
config.read('config.ini')

outputdir = config['io']['outputdir']
debugoutfile = config['io']['debugoutfile']
tlg = config['io']['tlg']
phi = config['io']['phi']
ddp = config['io']['ddp']
ins = config['io']['ins']

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
result = addoneauthor(authordict, lg, uidprefix, datapath, dataprefix, dbc, cur)
print(result)
dbc.commit()

if remap:
	tmpprefix = remap
	permprefix = mapper[dataprefix]['uidprefix']
	print('\nremapping the', debugauthor,'data: turning works into authors and embedded documents into individual works')
	aumapper, wkmapper = builddbremappers(tmpprefix, permprefix)
	newauthors = compilenewauthors(aumapper, wkmapper)
	newworktuples = compilenewworks(newauthors, wkmapper)
	registernewworks(newworktuples)
	deletetemporarydbs(tmpprefix)
else:
	a = buildauthorobject(debugauthor, lg, db, uidprefix, dataprefix)
	newauthors = [a]

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
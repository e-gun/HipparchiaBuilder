#!../bin/python
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

debugauthor = 'TLG1304'

"""

use this script to generate output files that show the state of the data as it moves through
the parsing process

"""

import re
import time

from builder import corpus_builder
from builder import dbinteraction
from builder import file_io
from builder import parsers
from builder.dbinteraction.build_lexica import *

config = configparser.ConfigParser()
config.read('config.ini')


def streamout(txt,outfile):
	f = open(outfile, 'w')
	f.write(txt)
	f.close()
	return


def linesout(txt,outfile):
	f = open(outfile, 'w')
	for item in txt:
		f.write("%s\n" % item)
	f.close()
	return

outputdir = config['io']['outputdir']
debugoutfile = config['io']['debugoutfile']
tlg = config['io']['tlg']
phi = config['io']['phi']
ddp = config['io']['ddp']
ins = config['io']['ins']

mapper = {
	'TLG': {'lg': 'G', 'db': tlg, 'uidprefix': 'gr'},
	'LAT': {'lg': 'L', 'db': phi, 'uidprefix': 'lt'},
	'DDP': {'lg': 'G', 'db': ddp, 'uidprefix': 'dp'},
	'INS': {'lg': 'G', 'db': ins, 'uidprefix': 'in'},
	'CHR': {'lg': 'G', 'db': chr, 'uidprefix': 'ch'},
}

dataprefix = debugauthor[0:3]
lg = mapper[dataprefix]['lg']
db = mapper[dataprefix]['db']
uidprefix = mapper[dataprefix]['uidprefix']

htmlthead = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
	<meta http-equiv=content-type content="text/html; charset=UTF-8">
	<title>testing builder output for {a}</title>
</head>
<body>
"""

htmlfoot = """
</body>
</html>
"""


n = debugauthor

start = time.time()

a = corpus_builder.buildauthor(n,lg,db, uidprefix, dataprefix)
txt = file_io.filereaders.highunicodefileload(db+n+'.TXT')
streamout(txt,outputdir+'01a'+debugoutfile)
streamout(re.sub(' █','\n█', txt),outputdir+'01b'+debugoutfile)

txt = parsers.regex_substitutions.earlybirdsubstitutions(txt)
streamout(txt,outputdir+'02a'+debugoutfile)
streamout(re.sub(' █', '\n█', txt), outputdir + '02b' + debugoutfile)

txt = parsers.regex_substitutions.replacequotationmarks(txt)
streamout(txt,outputdir+'03a'+debugoutfile)
streamout(re.sub(' █', '\n█', txt), outputdir + '03b' + debugoutfile)

txt = parsers.betacodeescapedcharacters.replaceaddnlchars(txt)
streamout(txt,outputdir+'04a'+debugoutfile)
streamout(re.sub(' █', '\n█', txt), outputdir + '04b' + debugoutfile)

streamout(txt,outputdir+'05a'+debugoutfile)
streamout(re.sub(' █', '\n█', txt), outputdir + '05b' + debugoutfile)

if lg == 'G' and a.language == 'G':
	txt = parsers.regex_substitutions.findromanwithingreek(txt)
	streamout(txt,outputdir+'06a'+debugoutfile)
	streamout(re.sub(' █', '\n█', txt), outputdir + '06b' + debugoutfile)

	txt = parsers.betacodefontshifts.replacegreekmarkup(txt)
	txt = parsers.betacodefontshifts.replacelatinmarkup(txt)
	streamout(txt,outputdir+'07a'+debugoutfile)
	streamout(re.sub(' █', '\n█', txt), outputdir + '07b' + debugoutfile)

	txt = parsers.betacodeandunicodeinterconversion.replacegreekbetacode(txt)
	streamout(txt,outputdir+'08a'+debugoutfile)
	streamout(re.sub(' █', '\n█', txt), outputdir + '08b' + debugoutfile)

	txt = parsers.betacodeandunicodeinterconversion.restoreromanwithingreek(txt)
	streamout(txt,outputdir+'09a'+debugoutfile)
	streamout(re.sub(' █', '\n█', txt), outputdir + '09b' + debugoutfile)
else:
	txt = parsers.betacodefontshifts.replacelatinmarkup(txt)
	txt = parsers.regex_substitutions.replacelatinbetacode(txt)
	streamout(txt,outputdir+'10a'+debugoutfile)
	streamout(re.sub(' █', '\n█', txt), outputdir + '10b' + debugoutfile)

lemmatized = parsers.regex_substitutions.addcdlabels(txt, a.number)
streamout(lemmatized,outputdir+'11a'+debugoutfile)

lemmatized = parsers.regex_substitutions.hexrunner(lemmatized)
streamout(lemmatized,outputdir+'12a'+debugoutfile)

lemmatized = parsers.regex_substitutions.lastsecondsubsitutions(lemmatized)
streamout(lemmatized,outputdir+'13a'+debugoutfile)

# toggle me if you need to
# lemmatized = parsers.regex_substitutions.debughostilesubstitutions(lemmatized)
lemmatized = re.sub(r'(<hmu_set_level)', r'\n\1', lemmatized)
lemmatized = lemmatized.split('\n')
linesout(lemmatized,outputdir+'14'+debugoutfile)

dbreadyversion = parsers.regex_substitutions.totallemmatization(lemmatized,a)
linesout(dbreadyversion,outputdir+'15'+debugoutfile)

dbreadyversion = dbinteraction.dbprepsubstitutions.dbprepper(dbreadyversion)
linesout(dbreadyversion,outputdir+'16'+debugoutfile)

txt = [ln[2] for ln in dbreadyversion]
linesout(txt,outputdir+'88_'+debugauthor+'.txt')

txt = [ln+'<br \>' for ln in txt]
txt = [htmlthead.format(a=debugauthor)] + txt + [htmlfoot]

linesout(txt,outputdir+'99_'+debugauthor+'.html')

print('textfile generation took:\n\t', str(time.time() - start))
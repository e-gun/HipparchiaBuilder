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
import configparser

from builder.file_io.filereaders import highunicodefileload
from builder.corpus_builder import buildauthorobject
from builder.parsers.betacodeescapedcharacters import replaceaddnlchars
from builder.parsers.betacodefontshifts import replacegreekmarkup, latinfontlinemarkupprober, \
	latinauthorlinemarkupprober, latinhmufontshiftsintospans, greekhmufontshiftsintospans
from builder.parsers.betacodeandunicodeinterconversion import replacegreekbetacode, restoreromanwithingreek, purgehybridgreekandlatinwords
from builder.parsers.regex_substitutions import cleanuplingeringmesses, earlybirdsubstitutions, replacequotationmarks, \
	addcdlabels, hexrunner, lastsecondsubsitutions, debughostilesubstitutions, latindiacriticals, \
	totallemmatization

config = configparser.ConfigParser()
config.read('config.ini')

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


def colonshift(txt):
	return re.sub(r':', '·', txt)


def levelbreak(txt):
	return re.sub(r'(<hmu_set_level)', r'\n\1', txt)


def finalsplit(txt):
	return txt.split('\n')


dataprefix = debugauthor[0:3]
lg = mapper[dataprefix]['lg']
db = mapper[dataprefix]['db']
uidprefix = mapper[dataprefix]['uidprefix']

csslocation = config['io']['serverdir'] + 'server/static/hipparchia_styles.css'

with open(csslocation, 'r') as f:
	css = f.read()

htmlthead = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
	<meta http-equiv=content-type content="text/html; charset=UTF-8">
	<title>testing builder output for {a}</title>
	<style>
	{css}
	</style>
</head>
<body>
"""

htmlfoot = """
</body>
</html>
"""

# functions need to match initialworkparsing() in corpus_builder.py
initial = [earlybirdsubstitutions, replacequotationmarks, replaceaddnlchars]
greekmiddle = [colonshift, replacegreekmarkup, latinfontlinemarkupprober, replacegreekbetacode,
               restoreromanwithingreek, greekhmufontshiftsintospans]
latinmiddle = [latinauthorlinemarkupprober, latindiacriticals, latinhmufontshiftsintospans]
final = [cleanuplingeringmesses, purgehybridgreekandlatinwords]


if lg == 'G':
	initialworkparsing = initial + greekmiddle + final
else:
	initialworkparsing = initial + latinmiddle + final

# functions need to match secondaryworkparsing() in corpus_builder.py
secondaryworkparsing = [
	addcdlabels, hexrunner, lastsecondsubsitutions, debughostilesubstitutions, levelbreak, finalsplit,
	totallemmatization
	]


if lg == 'G':
	functions = {key: val for (key,val) in enumerate(initialworkparsing + secondaryworkparsing)}
else:
	functions = {key: val for (key,val) in enumerate(initialworkparsing + secondaryworkparsing)}

n = debugauthor

start = time.time()

a = buildauthorobject(n, lg, db, uidprefix, dataprefix)
txt = highunicodefileload(db+n+'.TXT')


streamout(txt,outputdir+'aa'+debugoutfile)
streamout(re.sub(' █','\n█', txt),outputdir+'bb'+debugoutfile)

for f in sorted(functions.keys()):
	try:
		txt = functions[f](txt)
	except TypeError:
		txt = functions[f](txt, debugauthor[2:])

	fn = chr(97+f)+'_'+getattr(functions[f], '__name__')

	try:
		streamout(re.sub(' █', '\n█', txt), outputdir + n + '_' + fn + '.txt')
	except TypeError:
		linesout(txt, outputdir + n + '_' + fn + '.txt')

txt = [ln[2] for ln in txt]
linesout(txt,outputdir+'yy_'+debugauthor+'.txt')

txt = [ln+'<br \>' for ln in txt]
txt = [re.sub(r'<hmu_increment_.*? />', '', ln) for ln in txt]
txt = [re.sub(r'<hmu_set_level_.*? />', '', ln) for ln in txt]
txt = [htmlthead.format(a=debugauthor, css=css)] + txt + [htmlfoot]

linesout(txt,outputdir+'zz_'+debugauthor+'.html')

print('textfile generation took:\n\t', str(time.time() - start))

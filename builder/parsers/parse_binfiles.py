# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import csv
import re
import configparser
from multiprocessing import Pool
try:
	# python3
	import psycopg2
except ImportError:
	# pypy3
	# pypy3 support is EXPERIMENTAL (and unlikely to be actively pursued)
	import psycopg2cffi as psycopg2

from builder import file_io
from builder.parsers.betacodeandunicodeinterconversion import replacegreekbetacode
from builder.parsers.regex_substitutions import latindiacriticals
from builder.parsers.betacodeescapedcharacters import percentsubstitutes
from builder.parsers.betacodefontshifts import andsubstitutes

config = configparser.ConfigParser()
config.read('config.ini')
tlg = config['io']['tlg']


def resetbininfo(relativepath, cursor, dbconnection):
	bininfo = {
		'genre': 'LIST3CLA.BIN',
		'genre_clx': 'LIST3CLX.BIN',
		'recorded_date': 'LIST3DAT.BIN',
		'epithet': 'LIST3EPI.BIN',
		'gender': 'LIST3FEM.BIN',
		'location': 'LIST3GEO.BIN',
		'canon': 'DOCCAN2.TXT'
	}

	# relativepath = relativepath[:-3]
	genres = buildlabellist(relativepath + bininfo['genre_clx'])
	epithets = buildlabellist(relativepath + bininfo['epithet'])
	locations = buildlabellist(relativepath + bininfo['location'])
	canonfile = relativepath + bininfo['canon']
	dates = buildlabellist(relativepath + bininfo['recorded_date'])
	numdates = convertdatelist(dates)

	cleandates = {}
	for d in dates:
		newdate = re.sub(r'`', '', d)
		cleandates[newdate] = dates[d]

	wipegreekauthorcolumn('genres', cursor, dbconnection)
	# wipegreekauthorcolumn('epithet', cursor, dbconnection)
	wipegreekauthorcolumn('location', cursor, dbconnection)
	wipegreekauthorcolumn('recorded_date', cursor, dbconnection)
	wipegreekauthorcolumn('converted_date', cursor, dbconnection)

	# dbloadlist(genres, 'genres', cursor, dbconnection)
	dbloadlist(epithets, 'genres', cursor, dbconnection)
	dbloadlist(locations, 'location', cursor, dbconnection)
	dbloadlist(cleandates, 'recorded_date', cursor, dbconnection)
	dbloadlist(numdates, 'converted_date', cursor, dbconnection)

	dbconnection.commit()

	# canoninfo: do this last so that you can reset shortname
	loadgkcanon(canonfile)

	return


def npop(numbertopop, listtopop):
	ret = []
	for i in range(0, numbertopop):
		ret.append(listtopop.pop())

	return ret, listtopop


def listoflabels(rbl):
	rv = 999
	labels = []
	heads = []
	head, rbl = npop(4, rbl)
	while rv != 0:
		head, rbl = npop(4, rbl)
		rv = rbl.pop()
		string, rbl = npop(rv, rbl)
		string = intostring(string)
		labels.append(string)
		heads.append(head)
	return labels, heads, rbl


def intostring(listofchars):
	str = ''
	for c in listofchars:
		str += chr(c)
	return str


def grabaunum(bytebundle):
	num, bytebundle = npop(2, bytebundle)
	anum = (num[0] * 256 + num[1]) & int('7fff', 16)  # dec 32767
	anum = '%(n)04d' % {'n': anum}
	return anum, bytebundle


def findlabelbytestart(headerset):
	one = headerset[3]
	two = headerset[2]
	start = (256 * two) + one

	return start


def findbundledauthors(bytebundle):
	bytebundle.reverse()
	authlist = []
	while len(bytebundle) > 4:
		anum, bytebundle = grabaunum(bytebundle)
		poppedbyte = bytebundle.pop()
		if (poppedbyte & 128) or (poppedbyte == 0) and anum != '0000':
			authlist.append(anum)
			bytebundle.append(poppedbyte)
		elif anum != '0000':
			authlist.append(anum)
			bytebundle.append(poppedbyte)
			aworks, bytebundle = findbundledworks(bytebundle)
			if len(aworks) > 0:
				authlist[-1] = (authlist[-1], aworks)
	return authlist


def findbundledworks(bytebundle):
	# nothing really happens here?
	# does that matter?
	worklist = []
	bytememory = 0
	poppedbyte = bytebundle.pop()
	while (poppedbyte & 128 is False) and (poppedbyte != 0):
		print('pb:', poppedbyte)
		if poppedbyte < 32:
			worklist.append(poppedbyte)
			bytememory = poppedbyte
		elif poppedbyte == 32:
			bytebundle.append(poppedbyte)
			print('died with a 32. Bytes remaining =', len(bytebundle))
		elif poppedbyte < 64:
			for work in range(bytememory + 1, poppedbyte & 31):
				worklist.append(work)
			bytememory = 0
		elif poppedbyte < 96:
			print('trouble with a', poppedbyte, '. Bytes remaining =', len(bytebundle))
			high = (poppedbyte & 1) << 8
			poppedbyte = bytebundle.pop()
			bytememory = high + poppedbyte
			worklist.append(bytememory)
		elif poppedbyte == 96:
			poppedbyte = bytebundle.pop()
			for work in range(bytememory + 1, poppedbyte + 1):
				worklist.append(work)
		else:
			print('outside my ken:', poppedbyte, '. Bytes remaining =', len(bytebundle))
			poppedbyte = bytebundle.pop()
	worklist = ['%(n)03d' % {'n': x} for x in worklist]

	return worklist, bytebundle


def cleanlabels(labellist):
	"""
	dates have betacode in them
	"""
	clean = []
	
	percents = re.compile(r'\%(\d{1,3})')
	
	for l in labellist:
		l = re.sub(r'%3%19ae','',l) # Epigrammatici%3%19ae
		l = re.sub(percents, percentsubstitutes, l)
		l = re.sub('^ ', '', l)
		l = re.sub(' $','',l)
		l = re.sub('\*', '', l)
		# l = re.sub('\s', '_', l) # 'Scriptores Erotici' causes problems for HipparchiaServer
		clean.append(l)

	return clean


def buildlabellist(binfilepath):
	binfile = file_io.filereaders.loadbin(binfilepath)
	bl = []
	for byte in binfile:
		bl.append(byte)

	# reverse the list for popping pleasure
	rbl = bl[::-1]

	# get the genres
	labels, heads, trimmedrbl = listoflabels(rbl)
	labels = cleanlabels(labels)
	# a blank entry at the end
	labels = labels[:-1]

	# trim the pile of zeros in the middle
	p = 0
	while p == 0:
		p = trimmedrbl.pop()
	trimmedrbl.append(p)

	# switch direction again
	authinfo = trimmedrbl[::-1]

	labelcount = 0
	labellists = {}
	authlist = []

	# cut at the points indicated by the heads
	authorbytebundles = {}
	count = -1
	for lab in labels:
		count += 1
		firstsnip = findlabelbytestart(heads[count])
		try:
			secondsnip = findlabelbytestart(heads[count + 1])
			if secondsnip == 0:
				secondsnip = len(authinfo)
		except:
			secondsnip = len(authinfo)
		authorbytebundles[lab] = authinfo[firstsnip:secondsnip]

	decodedauthors = {}
	for key in authorbytebundles:
		decodedauthors[key] = findbundledauthors(authorbytebundles[key])

	return decodedauthors


def convertbinfiledates(stringdate):
	"""
	turn 7/6 B.C. into -600

	:param stringdate:
	:return:
	"""

	original = stringdate

	bc = re.compile(r'B\.C\.')
	ad = re.compile(r'A\.D\.')
	dontcare = re.compile(r'\?')
	split = re.compile(r'(\d{1,}).*?[–/].*?(\d{1,})')
	add = re.compile(r'^p\. ')
	subtract = re.compile(r'^a\. ')

	modifier = 1
	fudge = 0
	midcentury = -50
	date = 9999

	stringdate = re.sub(dontcare,'',stringdate)

	if re.search(bc,stringdate) is not None:
		modifier = -1
		fudge += 100

	if re.search(add,stringdate) is not None:
		fudge = 75
		if modifier < 0:
			fudge += 100

	if re.search(subtract,stringdate) is not None:
		fudge = -75

	if re.search(split,stringdate) is not None:
		digits = re.search(split, stringdate)
		one = int(digits.group(1))
		two = int(digits.group(2))

		if re.search(ad,stringdate) is not None and re.search(bc,stringdate) is not None:
			modifier = 1
			fudge -= 50
			one = one * -1

		avg = (one + two) / 2

	try:
		# we were a split
		date = int((avg * modifier * 100) + fudge + midcentury)
	except:
		# we were not a split
		if stringdate == 'Varia':
			date = 2000
		elif stringdate == 'Incertum':
			date = 2500
		else:
			stringdate = re.sub(r'\D','',stringdate)
			date = (int(stringdate) * modifier * 100) + fudge + midcentury

	if date == 0:
		date = 1

	return date


def convertdatelist(datelist):
	# do this before sending dates to dbloadlist
	newdatelist = {}
	for key in datelist:
		k = convertbinfiledates(key)
		newdatelist[k] = []
	for key in datelist:
		k = convertbinfiledates(key)
		newdatelist[k] += datelist[key]

	return newdatelist


def wipegreekauthorcolumn(column, cursor, dbconnection):
	query = 'SELECT universalid FROM authors WHERE universalid LIKE %s'
	data = ('gr%',)
	cursor.execute(query, data)
	found = cursor.fetchall()

	for find in found:
		query = 'UPDATE authors SET ' + column + '=%s WHERE universalid=%s'
		data = (None, find[0])
		cursor.execute(query, data)

	return


def dbloadlist(labellist, column, cursor, dbconnection):
	for key in labellist:
		for author in labellist[key]:
			query = 'SELECT universalid, {c} FROM authors WHERE universalid LIKE %s'.format(c=column)
			data = ('gr' + author,)
			cursor.execute(query, data)
			if isinstance(key, int) or isinstance(key, float):
				key = str(key)
			found = cursor.fetchall()
			# [('gr0009', 'lyric')]
			try:
				if found[0][0] is not None:
					if found[0][1] is not None:
						newinfo = found[0][1] + ',' + key
						if newinfo[0:1] == ',':
							newinfo = newinfo[1:]
					else:
						newinfo = key
					# irritating to handle Epici/-ae later
					query = 'UPDATE authors SET {c}=%s WHERE universalid=%s'.format(c=column)
					data = (newinfo, 'gr' + author)
					cursor.execute(query, data)
			except:
				pass
	dbconnection.commit()
	return

# epithets is a lot like genres, but not the same
# should probably try to merge the info, but you would need a lookup list since 'Epica' is not 'Epici'


def gkcanoncleaner(txt):
	"""
	tidy up the greek canon file
	:param txt:
	:return:
	"""
	
	# search = r'((█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]{1,2}\s){1,})'
	
	gk = re.compile(r'\$\d{0,1}(.*?)\&')
	
	# author entries
	ae = re.compile(r'█ⓕⓕ\skey\s(\d\d\d\d)(\s█⑧⓪)')
	au = re.compile(r'<authorentry>(\d\d\d\d)</authorentry>(.*?)\n<authorentry>')
	nm = re.compile(r'\snam\s(.*?)(\s█⑧⓪)')
	ep = re.compile(r'\sepi\s(.*?)(\s█⑧⓪)')
	ak = re.compile(r'\sep2\s(.*?)(\s█⑧⓪)')
	ge = re.compile(r'\sgeo\s(.*?)(\s█⑧⓪)')
	gn = re.compile(r'\sgen\s(.*?)(\s█⑧⓪)')
	st = re.compile(r'\ssrt\s(.*?)(\s█⑧⓪)')
	sy = re.compile(r'\ssyn\s(.*?)(\s█⑧⓪)')
	dt = re.compile(r'\sdat\s(.*?)\s(█)')
	cf = re.compile(r'(█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ][⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ])\svid\s(.*?)\s(█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ][⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ])')
	wk = re.compile(r'█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ][⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]\skey\s(\d\d\d\d)\s(\d\d\d)(\s█⑧⓪)')
	
	# work entries
	w = re.compile(r'\swrk\s(.*?)(\s█⑧⓪\scla)')
	cl = re.compile(r'\scla\s(.*?)(\s█⑧⓪)')
	wc = re.compile(r'\swct\s(.*?)(\s█⑧⓪)')
	ct = re.compile(r'\scit\s(.*?)(\s█⑧⓪)')
	xm = re.compile(r'\sxmt\s(.*?)(\s█⑧⓪)')
	ty = re.compile(r'\styp\s(.*?)(\s█⑧⓪)')
	
	# publication info: requires newlines
	pb = re.compile(r'\stit\s(.*?)\n')
	pi = re.compile(r'(<publicationinfo>.*?)\spub\s(.*?)\spla\s(.*?)\spyr\s(.*?)\s')
	vn = re.compile(r'(<publicationinfo>)&3(.*?)&')
	ed = re.compile(r'\sedr\s(.*?)\s(</publicationinfo>)')
	edr = re.compile(r'\sedr\s(.*?)\s█..')
	sr = re.compile(r'\sser\s(.*?)\s(█)')
	rp = re.compile(r'\sryr\s(.*?)(\s█⑧⓪)')
	rpu = re.compile(r'\srpu\s(.*?)(\s█⑧⓪)')
	rpl = re.compile(r'\srpl\s(.*?)(\s█⑧⓪)')
	br = re.compile(r'\sbrk\s(.*?)(\s█⑧⓪)')
	pg = re.compile(r'\spag\s(.*?)<')
	
	# cleanup
	hx = re.compile(r'█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ][⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]')
	bd = re.compile(r'&1(.*?)&')
	it = re.compile(r'&3(.*?)&')
	gk = re.compile(r'\$\d{0,1}')
	
	# the initial substitutions
	# txt = re.sub(gk,parsers.betacode_to_unicode.parsegreekinsidelatin,txt)
	
	txt = re.sub(ae, r'\n<authorentry>\1</authorentry>', txt)
	# txt = re.sub(au, r'<authorentry><authornumber>\1</authornumber>\2</authorentry>\n<authorentry>', txt)
	# 1st pass gets half of them...
	# txt = re.sub(au, r'<authorentry><authornumber>\1</authornumber>\2</authorentry>\n<authorentry>', txt)
	
	# pounds = re.compile(r'\#(\d{1,4})')
	# txt = re.sub(pounds, parsers.regex_substitutions.poundsubstitutes, txt)
	
	# pull out the subsections or an author
	txt = re.sub(nm, r'<name>\1</name>\2', txt)
	txt = re.sub(ep, r'<epithet>\1</epithet>\2', txt)
	txt = re.sub(ak, r'<otherepithets>\1</otherepithets>\2', txt)
	txt = re.sub(sy, r'<aka>\1</aka>\2', txt)
	txt = re.sub(ge, r'<location>\1</location>\2', txt)
	txt = re.sub(dt, r'<date>\1</date>\2', txt)
	txt = re.sub(gn, r'<genre>\1</genre>\2', txt)
	txt = re.sub(st, r'<short>\1</short>\2', txt)
	txt = re.sub(cf, r'\1<crossref>\2</crossref>\3', txt)
	
	# the inset works
	txt = re.sub(wk, r'\n\t<work>\1w\2</work>\3', txt)
	# nuke crossreferences: key nnnn Xnn
	txt = re.sub(r'key \d\d\d\d X\d\d.*?\n<authorentry>', r'\n<authorentry>', txt)
	txt = re.sub(r'crf.*?\n<authorentry>', r'\n<authorentry>', txt)
	# rejoin 'linebreaks'
	txt = re.sub(r'█⑧⓪     ', '', txt)
	
	txt = re.sub(w, r'<workname>\1</workname>\2', txt)
	# will miss one work because of an unlucky hexrun: <work>0058w001</work> █⑧⓪ wrk &1Poliorcetica& █ⓕⓔ █⓪ █⓪ █⓪ █⓪ █⓪ █⓪ █⓪ █⓪ █⓪ █⓪ █ⓔⓕ █⑧⓪ █ⓑ⑨ █ⓑ⑨ █ⓑ⑨ █ⓑ⑧ █ⓕⓕ █ⓔⓕ █⑧① █ⓑ⓪ █ⓑ⓪ █ⓑ① █ⓕⓕ █ⓐ⑧ █ⓑⓐ █⑨① █⑧③ cla Tact. █⑧⓪
	txt = re.sub(cl, r'<workgenre>\1</workgenre>\2', txt)
	txt = re.sub(wc, r'<wordcount>\1</wordcount>\2', txt)
	txt = re.sub(ct, r'<citationformat>\1</citationformat>\2', txt)
	txt = re.sub(xm, r'<meansoftransmission>\1</meansoftransmission>\2', txt)
	txt = re.sub(ty, r'<typeofwork>\1</typeofwork>\2', txt)
	
	# the publication info
	txt = re.sub(pb, r'<publicationinfo>\1</publicationinfo>\n', txt)
	txt = re.sub(pi, r'\1<press>\2</press><city>\3</city><year>\4</year>', txt)
	txt = re.sub(vn, r'\1<volumename>\2</volumename>', txt)
	txt = re.sub(ed, r'<editor>\1</editor>\2', txt)
	txt = re.sub(edr, r'<editor>\1</editor>', txt)
	txt = re.sub(sr, r'<series>\1</series>\2', txt)
	txt = re.sub(rp, r'<yearreprinted>\1</yearreprinted>', txt)
	txt = re.sub(rpu, r'<reprintpress>\1</reprintpress>', txt)
	txt = re.sub(rpl, r'<reprintcity>\1</reprintcity>', txt)
	txt = re.sub(br, r'<pagesintocitations>\1</pagesintocitations>', txt)
	txt = re.sub(pg, r'<pages>\1</pages><', txt)
	
	# cleaning the worknames
	lwn = re.compile(r'</workname>\s{2,}(.*?)\s█⑧⓪')
	txt = re.sub(lwn, r'\1</workname>', txt)
	wnc = re.compile(r'<workname>(.*?)</workname>')
	txt = re.sub(wnc, worknamecleaner, txt)
	# kill 'italics'
	# can't get rid of '&' before you do greek
	txt = re.sub('\&(\d{0,2})', r'', txt)
	
	txt = re.sub(hx, '', txt)
	txt = re.sub(r' █⓪', '', txt)
	
	# txt = re.sub(bd, r'\1', txt)
	# txt = re.sub(gk, r'', txt)
	
	# txt = re.sub(it, r'<italic>\1</italic>', txt)
	# txt = re.sub(r'\s{2,}', r' ',txt)
	# txt = re.sub(r'\s</', r'</', txt)
	# txt = re.sub(r'\t', r'', txt)
	
	percents = re.compile(r'\%(\d{1,3})')
	txt = re.sub(percents, percentsubstitutes, txt)
	txt = re.sub(r'`', r'', txt)
	
	txt = latindiacriticals(txt)
	txt = txt.split('\n')
	# txt = txt[:-1]

	return txt


def worknamecleaner(matchgroup):
	"""
	tricky because greek is not turned off properly
	:param matchgroup:
	:return:
	"""

	try:
		toclean = matchgroup.group(1)
	except:
		print('failed to find a workname to clean')
		toclean = '[unk]'
	
	toclean = re.sub(r'(\&1){0,1}\[2',r'⟪',toclean)
	toclean = re.sub(r'(\&1){0,1}\]2', r'⟫', toclean)
	
	gk = re.compile(r'\$\d{0,1}(.*?)&\d{0,1}')
	if re.search(gk,toclean) is not None:
		g = re.search(gk,toclean)
		g = re.sub(r'_',r'-',g.group(1))
		g = replacegreekbetacode(g)
		toclean = re.sub(gk,g,toclean)
		try:
			cleanedname = re.sub(re.escape(matchgroup.group(1)), toclean, matchgroup.group(0))
		except:
			# bad escape of pattern...
			print('barfed on:',matchgroup.group(1), toclean, matchgroup.group(0))
			cleanedname = matchgroup.group(0)
		
	else:
		cleanedname = matchgroup.group(0)
	
	percents = re.compile(r'\%(\d{1,3})')
	cleanedname = re.sub(percents, percentsubstitutes,cleanedname)
	cleanedname = latindiacriticals(cleanedname)
	cleanedname = re.sub(r'&\d{0,2}(.*?)&\d{0,1}',r'\1',cleanedname)
	cleanedname = re.sub(r'&',r'',cleanedname)
	cleanedname = re.sub(r'\$\d{0,1}', r'', cleanedname)
	cleanedname = re.sub(r'`', r'', cleanedname)
	
	return cleanedname


def loadgkcanon(canonfile):
	"""

	this is suprisingly slow at the end of a build
	there are 8412 of UPDATES to run: parallelize them

	actually, a temp table update is what is really needed...

	:param canonfile:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	#txt = file_io.filereaders.dirtyhexloader(canonfile)
	txt = file_io.filereaders.highunicodefileload(canonfile)
	txt += '\n<authorentry>'

	txt = gkcanoncleaner(txt)
	thework = []
	workers = int(config['io']['workers'])

	for t in txt:
		thework.append(t)
	pool = Pool(processes=workers)
	pool.map(parallelcanonworker, thework)

	return


def parallelcanonworker(thework):
	"""

	speed up loadgkcanon()

	:param thework:
	:return:
	"""

	dbc = psycopg2.connect(user=config['db']['DBUSER'], host=config['db']['DBHOST'],
							port=config['db']['DBPORT'], database=config['db']['DBNAME'],
							password=config['db']['DBPASS'])
	cur = dbc.cursor()

	if thework[0:5] == '<auth':
		modifygkauthordb(thework, cur)
	# pass
	elif thework[0:6] == '\t<work':
		modifygkworksdb(thework, cur)

	dbc.commit()

	return


def modifygkauthordb(newauthorinfo, cursor):
	sh = re.compile(r'<short>(.*?)</short>')
	an = re.compile(r'<authorentry>(.*?)</authorentry>')
	percents = re.compile(r'\%(\d{1,3})')
	au = re.search(an, newauthorinfo)
	
	try:
		a = 'gr' + au.group(1)
	except:
		a = 'zzz'
		
	short = re.search(sh, newauthorinfo)
	try:
		s = re.sub(' {1,}$','',short.group(1))
		s = re.sub(percents, percentsubstitutes, s)
	except:
		s = ''
	
	# try some comparisons: the (flawed) canon data can help to fix the flawed idt data
	query = 'SELECT shortname FROM authors where universalid=%s'
	data = (a,)
	cursor.execute(query, data)
	result = cursor.fetchone()
	
	try:
		r = re.sub(' {1,}$','',result[0])
	except:
		r = ''
	
	if len(r) < 1:
		# print(a,'shortname difference(db/canaon):\n\t',r,'\n\t',s)
		query = 'UPDATE authors SET shortname=%s WHERE universalid=%s'
		data = (s, a)
		cursor.execute(query, data)
	
	return


def modifygkworksdb(newworkinfo, cursor):
	"""
	take a line from the parsed gk canon file and use it to update the works db
	sample: <work>1542w001</work><workname>Fragmenta</workname><workgenre>Phil.</workgenre><meansoftransmission>Q</meansoftransmission><typeofwork>Book</typeofwork><wordcount>10,516</wordcount><citationformat>Fragment/line</citationformat><publicationinfo><italic>Nume/nius. Fragments</italic> <press>Les Belles Lettres </press><city>Paris </city><year>1974</year><pages>42–94, 99–102 </pages><pagesintocitations>$Περὶ τἀγαθοῦ &(frr. 1–22): pp. 1–61</pagesintocitations><pagesintocitations>$Περὶ τῶν παρὰ Πλάτωνι ἀπορρήτων &(fr. 23): pp. 61–62</pagesintocitations><pagesintocitations>$Περὶ τῆϲ τῶν Ἀκαδημαϊκῶν πρὸϲ Πλάτωνα διαϲτάϲεωϲ &(frr.</pagesintocitations>     24–28): pp. 62–80 <pagesintocitations>$Περὶ ἀφθαρϲίαϲ ψυχῆϲ &(fr. 29): p. 80</pagesintocitations><pagesintocitations>Incertorum operum fragmenta (frr. 30–33, 35–51, 53–54, 56–59): pp. 80–94,</pagesintocitations>     99–101 <pagesintocitations>Fragmentum dubium (fr. 60): pp. 101–102</pagesintocitations><editor>des Places, E/.      </authorentry></editor></publicationinfo>
	:param newworkinfo:
	:return:
	"""
	
	# pounds = re.compile(r'\#(\d{1,4})')
	percents = re.compile(r'\%(\d{1,3})')
	ands = re.compile(r'\&(\d{1,2})(.*?)(\&\d{0,1})')
	
	newworkinfo = re.sub(r'\s{2,}', r' ', newworkinfo)
	
	wk = re.compile(r'<work>(.*?)</work>')
	wn = re.compile(r'<workname>(.*?)</workname>')
	gn = re.compile(r'<workgenre>(.*?)</workgenre>')
	mot = re.compile(r'<meansoftransmission>(.*?)</meansoftransmission>')
	typ = re.compile(r'<typeofwork>(.*?)</typeofwork>')
	wc = re.compile(r'<wordcount>(.*?)</wordcount>')
	cf = re.compile(r'<citationformat>(.*?)</citationformat>')
	pi = re.compile(r'<publicationinfo>(.*?)</publicationinfo>')
	
	work = re.search(wk, newworkinfo)
	name = re.search(wn, newworkinfo)
	pub = re.search(pi, newworkinfo)
	genre = re.search(gn, newworkinfo)
	trans = re.search(mot, newworkinfo)
	wtype = re.search(typ, newworkinfo)
	count = re.search(wc, newworkinfo)
	cite = re.search(cf, newworkinfo)
	cite = re.sub(percents, percentsubstitutes, cite.group(1))
	cite = cite.split('/')
	try:
		cite.remove('')
	except:
		pass
	
	# print(work.group(1),':',cite)
	
	try:
		count = int(re.sub(r'[^\d]', '', count.group(1)))
	except:
		count = -1
	
	try:
		n = name.group(1)
		if n[0] == '1':
			# why are these still here?
			n = n[1:]
	except:
		if work.group(1) == '0058w001':
			n = 'Poliorcetica' # 0058w001 does not have a name with this version of the parser....: 'wrk &1Poliorcetica&'
		else:
			# print('no name for',work.group(1))
			n = ''
	
	if re.search(r'\[Sp\.\]',n) is not None:
		authentic = False
	else:
		authentic = True
	
	try:
		p = pub.group(1)
	except:
		p = ''
	
	p = re.sub(percents, percentsubstitutes, p)
	p = re.sub(ands, andsubstitutes, p)
	p = re.sub(r' $', '', p)
	
	try:
		g = genre.group(1)
	except:
		g = ''
		
	g = re.sub(percents, percentsubstitutes, g)
	g = re.sub(r' $', '', g)
	# *Epic., *Hist., ...
	g = re.sub(r'\*', '', g)
	
	try:
		t = trans.group(1)
	except:
		t = ''
	
	try:
		w = wtype.group(1)
	except:
		w = ''
	
	w = re.sub(percents, percentsubstitutes, w)
	w = re.sub(r' $', '', w)
	
	# try some comparisons: the (flawed) canon data can help to fix the flawed idt data
	query = 'SELECT title,levellabels_00 FROM works where universalid=%s'
	data = ('gr' + work.group(1),)
	cursor.execute(query, data)
	result = cursor.fetchone()
	r = result[0]
	
	if r != n and n != '':
		# print(work.group(1), 'db vs canon:\n\t', r, '\n\t', n)
		query = 'UPDATE works SET title=%s WHERE universalid=%s'
		data = (n,'gr' + work.group(1))
		cursor.execute(query, data)
	
	if result[1] == '':
		# yikes: a broken author...
		# should only be one
		#   0656w003 : ['Book', 'section', 'line']
		# print('should insert the following to fix the db:\n\t',work.group(1), ':', cite)
		llinserts = []
		for i in range(0,6):
			try:
				llinserts.append(cite.pop())
			except:
				llinserts.append('')
		query = 'UPDATE works SET levellabels_00=%s, levellabels_01=%s, levellabels_02=%s, levellabels_03=%s, levellabels_04=%s, levellabels_05=%s WHERE universalid=%s'
		data = (llinserts[0],llinserts[1],llinserts[2],llinserts[3],llinserts[4],llinserts[5],'gr' + work.group(1))
		cursor.execute(query, data)
	
	query = 'UPDATE works SET publication_info=%s, workgenre=%s, transmission=%s, worktype=%s, wordcount=%s, authentic=%s WHERE universalid=%s'
	try:
		data = (p, g, t, w, count, authentic, 'gr' + work.group(1))
		cursor.execute(query, data)
	except psycopg2.DatabaseError as e:
		print('Error %s' % e)
	
	return


def latinloadcanon(canonfile, cursor):

	percents = re.compile(r'\%(\d{1,3})')
	prefix = 'lt'
	# initial cleanup
	# txt = file_io.filereaders.dirtyhexloader(canonfile)
	txt = file_io.filereaders.highunicodefileload(canonfile)
	txt = re.sub(r'@', r'', txt)
	txt = re.sub(r'█⑧⓪ ', r'', txt)
	txt = re.sub(r'\{.(\d\d\d\d)\.(\d\d\d)\}', r'<authornumber>\1</authornumber><worknumber>\2</worknumber><end>\n',
	             txt)
	txt = re.sub(r'\((.*?)\)', r'<publicationinfo>\1</publicationinfo>', txt)
	txt = re.sub(r'█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ][⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]\s', r'', txt)
	txt = re.sub(r'█⓪\s', r'', txt)
	# txt = parsers.regex_substitutions.replacemarkup(txt)
	# txt = parsers.regex_substitutions.replaceaddnlchars(txt)
	txt = re.sub(r'\&3(.*?)\&', r'<work>\1</work>', txt)
	txt = re.sub(r'</work> <work>', r' ', txt)
	txt = re.sub(r'<publicationinfo>(.*?)<work>(.*?)</work>(.*?)</publicationinfo>', r'<publicationinfo>\1<volumename>\2</volumename>\3</publicationinfo>', txt)
	txt = re.sub(r'\&1(.*?)\&', r'<author>\1</author>', txt)
	txt = re.sub(r'\s\s<author>',r'<author>',txt)
	txt = re.sub(r'<author>(.*?)<publicationinfo>(.*?)</publicationinfo>(.*?)</author>', r'<author>\1(\2)\3</author>', txt)
	txt = re.sub(r'</volumename>.*?ed\.\s(.*?),\s(\d\d\d\d)(</publicationinfo>)',r'</volumename><editor>\1</editor><year>\2</year>\3',txt)
	txt = re.sub('</italic> <italic>', ' ', txt)
	txt = txt.split('\n')
	# linesout(txt, outfile)
	#  <author>L. Annaeus Seneca iunior</author>. <work>Apocolocyntosis</work> <edition><volumename>Seneca: Apocolocyntosis</volumename>, ed. P. T. Eden, 1984</edition>. <authornumber>1017</authornumber><worknumber>011</worknumber><end>
	
	canoninfo = {}
	a = re.compile(r'<authornumber>(.*?)</authornumber>')
	w = re.compile(r'<worknumber>(.*?)</worknumber>')
	l = re.compile(r'(.*?)\s<authornumber>')
	for line in txt:
		author = re.search(a, line)
		work = re.search(w, line)
		contents = re.search(l, line)
		try:
			c = contents.group(1)
		except:
			c = ''
		c = re.sub(percents, percentsubstitutes, c)
		c = latindiacriticals(c)
		c = re.sub(r'`', r'', c)
		try:
			canoninfo[prefix + author.group(1) + 'w' + work.group(1)] = c
		except:
			# blank line at end
			pass
	
	for work in canoninfo:
		query = 'UPDATE works SET publication_info=%s WHERE universalid=%s'
		data = (canoninfo[work],work)
		cursor.execute(query, data)
		
	return


def insertlatingenres(cursor, dbc):
	"""

	we have no pre-rolled association between works and genres

	guess some

	manually insert other [later...]

	:param cursor:
	:return:
	"""

	# First pass: use regex

	q = 'SELECT universalid,title FROM works WHERE universalid LIKE %s ORDER BY universalid '
	d = ('lt%',)
	cursor.execute(q,d)
	works = cursor.fetchall()

	titletranslator = [
		(r'^Ad.*?Epist', 'Epist.'),
		(r'^Epist.*?ad ', 'Epist.'),
		(r'^Atell', 'Comic.'),
		(r'^De Bello', 'Hist.'),
		(r'^De Metris', 'Gramm.'),
		(r'^De Ortho', 'Gramm.'),
		(r'^Declam', 'Orat.'),
		(r'^Pro', 'Orat.'),
		(r'^Vita', 'Biog.'),
		(r'^como', 'Comic.'),
		(r'^Commentar.', 'Hist.'),
		(r'^Commentum', 'Comm.'),
		(r'^Comment\. in', 'Comm.'),
		(r'^Controv', 'Orat.'),
		(r'^[Ee]leg', 'Eleg.'),
		(r'^epigr', 'Epigr.'),
		(r'^epist', 'Epist.'),
		(r'^Epistulae ad', 'Epist.'),
		(r'grammat', 'Gramm.'),
		(r'^[Hh]istor', 'Hist.'),
		(r'^In Verg', 'Comm.'),
		(r'^iurisp', 'Jurisprud.'),
		(r'Metr', 'Gramm.'),
		(r'Medic', 'Med.'),
		(r'^[Mm]im', 'Mim.'),
		(r'^Natur', 'Nat. Hist.'),
		(r'^orat', 'Orat.'),
		(r'^[Pp]allia', 'Comic.'),
		(r'^Paneg', 'Orat.'),
		(r'^praet', 'Trag.'),
		(r'^[Tt]rago', 'Trag.'),
		(r'^[Tt]ogat', 'Comic.'),
	]

	genres = []
	for t in titletranslator:
		for w in works:
			if re.search(t[0], w[1]) is not None:
				genres.append((w[0],t[1]))

	for g in genres:
		q = 'UPDATE works SET workgenre=%s WHERE universalid=%s'
		d = (g[1], g[0])
		cursor.execute(q, d)

	# SELECT * FROM works WHERE universalid LIKE 'lt%' AND workgenre IS NULL ORDER BY title
	# 241 of the 836 will be assigned
	dbc.commit()

	# Second pass: use authorID
	q = 'SELECT universalid FROM works WHERE universalid LIKE %s AND workgenre IS NULL'
	d = ('lt%',)
	cursor.execute(q,d)
	works = cursor.fetchall()
	works = [w[0] for w in works]

	authortranslator = {
		'lt0119': 'Comic.',
		'lt0134': 'Comic.',
		'lt1234': 'Comm.',
		'lt1235': 'Comm.',
		'lt2331': 'Biogr.',
		'lt0914': 'Hist.',
		'lt0631': 'Hist.',
		'lt1215': 'Jurisprud.',
		'lt1377': 'Gramm.',
		'lt3211': 'Gramm.',
	}

	genres = []
	for w in works:
		if w[0:6] in authortranslator:
			genres.append((w,authortranslator[w[0:6]]))

	for g in genres:
		q = 'UPDATE works SET workgenre=%s WHERE universalid=%s'
		d = (g[1], g[0])
		cursor.execute(q, d)

	dbc.commit()

	# third pass: brute force assignment
	with open('./builder/parsers/manual_latin_genre_assignment.csv', encoding='utf-8') as csvfile:
		genrereader = csv.DictReader(csvfile)
		newgenres = [(row['universalid'], row['genre']) for row in genrereader if row['genre']]

	for g in newgenres:
		q = 'UPDATE works SET workgenre=%s WHERE universalid=%s'
		d = (g[1], g[0])
		cursor.execute(q, d)

	dbc.commit()

	return


def citationreformatter(matchgroups):
	"""
	avoid Volumépagéline if you let Volume%3page%3line run through the percentsubstitutes
	:param match:
	:return:
	"""
	core = re.sub(r'%3',r'|',matchgroups.group(2))
	core = core.split('|')
	core.remove('')
	core = '|'.join(core)
	
	substitute = matchgroups.group(1)+core+matchgroups.group(3)
	
	return substitute


def peekatcanon(workdbname):
	"""
	an emergency appeal to the canon for a work's structure
	:param workname:
	:param worknumber:
	:return:
	"""
	canonfile = tlg[:-3] + 'DOCCAN2.TXT'
	txt = file_io.filereaders.highunicodefileload(canonfile)
	txt += '\n<authorentry>'
	
	citfinder = re.compile(r'.*<citationformat>(.*?)</citationformat>.*')
	
	# regex patterns:
	# careful - structure set to {0: 'Volumépagéline'} [gr0598]
	txt = gkcanoncleaner(txt)
	structure = []
	for line in txt:
		if line[0:6] == '\t<work':
			if re.search(workdbname[2:],line) is not None:
				structure = re.sub(citfinder,r'\1',line)
				# 'Book%3section%3line' has been turned into book/section/line
				# but volume%3 has become "volume + /" which then turns into "volumé"
				structure = re.sub(r'é',r'e/',structure)
				structure = structure.split('/')
				
	structure.reverse()
	
	return structure


def streamout(txt,outfile):
	f = open(outfile, 'w')
	f.write(txt)
	f.close()
	return

# notes..

"""
labels: H-pack
	[1 2 3 4]
	read #4:
		0 --> 'last'
		N --> len of python string

authors: h-pack
	[1 2] --> (& hex 7fff) --> author number in 4-place decimal
	[3 4] --> works
	read #4
		test-for-last, etc

works:
	TBD:
"""

"""
0x0 0x0 0x8 0x0 0x0 0x0 0x0 0x0 0x5 Acta 0x0 0x0 0x0 %0x9 Alchemica0x0 0x0 0x0 0x92 0xb Antholo
giae0x0 0x0 0x0 0xac 0xb Apocalypses0x0 0x0 0x0 0xdd 0x9 Apocrypha0x0 0x0 0x1 90xb A
pologetica0x0 0x0 0x1 0xab 0xb Astrologica0x0 0x0 0x1 0xfb 0xb Astronomi
ca0x0 0x0 0x2 \0x9 Biographa0x0 0x0 0x2 0xf6 0x9 Bucolica 0x0 0x0 0x3 0xa 0x7 Caten

                5  A c t a
00000800000000000541637461200000002509416c6368656d696361000000920b416e74686f6c6f67696165000000
ac0b41706f63616c7970736573000000dd0941706f637279706861000001390b41706f6c6f676574696361000001ab
0b417374726f6c6f67696361000001fb0b417374726f6e6f6d6963610000025c0942696f677261706861000002f6094275636f6c69

"""

"""
the bytes that come before the labels look like this:
>>> print(heads)
[0, 0, 0, 0]
 [0, 0, 0, 56]
 [0, 0, 0, 78]
 [0, 0, 0, 110]
 [0, 0, 0, 142]
 [0, 0, 0, 154]
 [0, 0, 0, 178]
 [0, 0, 0, 188]
 [0, 0, 0, 194]
 [0, 0, 0, 210]
 [0, 0, 2, 2]
 [0, 0, 2, 10]
 [0, 0, 2, 80]
 [0, 0, 2, 218]
 [0, 0, 3, 12]
 [0, 0, 3, 36]
 [0, 0, 3, 66]
 [0, 0, 3, 78]
 [0, 0, 3, 90]
 [0, 0, 3, 98]
 [0, 0, 3, 250]
 [0, 0, 4, 2]
 [0, 0, 6, 174]
 [0, 0, 6, 180]
...
a means of counting: each higher than the last

here is the top of the bytes when we get to the authors
[131, 248, 135, 227, 136, 92, 136, 133, 138, 29, 138, 72, 143, 246, 144, 223, 144, 227, 144,
228, 144, 229, 144, 230, 144, 231, 144, 232, 144, 233, 144, 234, 144, 235, 144, 236, 144, 237,
144, 238, 144, 239, 144, 241, 144, 242, 144, 243, 144, 244, 163, 61, 0, 0, 0, 0, 130, 19, 130,
133, 132, 139, 132, 160, 132, 181, 133, 215, 134, 189, 134, 230, 135, 200, 0, 0, 0, 0, 131, 236]


>>> print(info[50:60])
[163, 61, 0, 0, 0, 0, 130, 19, 130, 133]

so at 56 we find the first byte of the next label: Apologetici

>>> print(info[70:80])
[134, 230, 135, 200, 0, 0, 0, 0, 131, 236]

at 78 we find the first byte of the next label: Astrologici

the value of the second digit is obvious once you see it...
there are no zero-runs from 210 until around 505: [514 + 522]

>>> print(authinfo[505:550])
[1, 135, 2, 135, 3, 0, 0, 0, 0, 130, 16, 130, 17, 0, 0, 0, 0, 128, 2, 128, 212, 128, 213,
128, 214, 128, 217, 128, 232, 128, 236, 128, 239, 128, 242, 128, 243, 128, 245, 128, 246,
128, 247, 128, 249]

and indeed we expected a short run:
 [0, 0, 2, 2]
 [0, 0, 2, 10]

therefore each '1' is worth 256: 2*256 + 2 --> 514

>>> print(labels[10])
Doxographi
>>> print(heads[10])
[0, 0, 2, 2]

there should be two and only two of them:
[130, 16]
[130, 17]
Diogenes knows of only two Doxograph.
	Arius Didymus Doxogr., Physica (fragmenta) (0529: 001)
	Aëtius Doxogr., De placitis reliquiae (Stobaei excerpta) (0528: 001)

and they *should* have sequential ids: 0528 = 130, 16; 0529 = 130, 17

"""


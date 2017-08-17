# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import configparser
import re

from builder import file_io
from builder.builderclasses import loadallauthorsasobjects, loadallworksasobjects
from builder.dbinteraction.db import updatedbfromtemptable
from builder.parsers.betacodeandunicodeinterconversion import replacegreekbetacode
from builder.parsers.betacodeescapedcharacters import percentsubstitutes
from builder.parsers.betacodefontshifts import andsubstitutes
from builder.parsers.latinsubstitutions import latindiacriticals

config = configparser.ConfigParser()
config.read('config.ini')
tlg = config['io']['tlg']


def languagesubstitutes(opentag, foundtext, closetag):
	"""
	tricky because greek is not turned off properly
	:param matchgroup:
	:return:
	"""

	clean = re.sub(r'(\&1){0,1}\[2',r'⟨', foundtext)
	clean = re.sub(r'(\&1){0,1}\]2', r'⟩', clean)

	# need to put the '$' back on at the end because some titles are '$...$3...'
	dollars = re.compile(r'\$(\d{1,2})([^<]*?)(\$\d{0,1})')
	clean = re.sub(dollars, lambda x: replacegreekbetacode(x.group(2))+x.group(3), clean)
	dollarand = re.compile(r'\$(\d{0,1})([^<]*?)&\d{0,1}')
	clean = re.sub(dollarand, lambda x: replacegreekbetacode(x.group(2)), clean)
	# but you have to stop at a stop lest you get 'Aristotelis Ἀθηναίων πολιτεία. τeubner, λeipzig, 1928. (οppermann, η.)'
	# so try to find the next tag
	trailingdollar = re.compile(r'\$(\d{0,1})(.*?)(<)')
	clean = re.sub(trailingdollar, lambda x: replacegreekbetacode(x.group(2))+x.group(3), clean)
	percents = re.compile(r'\%(\d{1,3})')
	clean = re.sub(percents, percentsubstitutes, clean)
	clean = latindiacriticals(clean)
	# if you send font markup into workname you will get lots of gross stuff in the selection boxes
	andand = re.compile(r'&(\d{0,2})(.*?)&\d{0,1}')
	# clean = re.sub(andand,lambda x: andsubstitutes(x.group(1), x.group(2), ''), clean)
	clean = re.sub(andand, r'\2', clean)
	clean = re.sub(r'&',r'',clean)
	clean = re.sub(r'`', r'', clean)
	# clean = hmufontshiftsintospans(clean)

	clean = '{a}{b}{c}'.format(a=opentag, b=clean, c=closetag)

	return clean


def loadgkcanon(canonfile):
	"""

	this is suprisingly slow at the end of a build
	there are 8412 of UPDATES to run

	a temp table update is what is really needed...

	:param canonfile:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	allauthors = loadallauthorsasobjects(config)

	#txt = file_io.filereaders.dirtyhexloader(canonfile)
	txt = file_io.filereaders.highunicodefileload(canonfile)
	txt += '\n<authorentry>'

	txt = gkcanoncleaner(txt)
	authors = [a for a in txt if re.search(r'^<authorentry>',a)]
	authorlines = [temptableauthorline(a, allauthors) for a in authors]
	authordatadict = {a[0]: [a[1]] for a in authorlines if a[1]}
	authorcolumns = ['shortname']

	allworks = loadallworksasobjects(config)
	works = [w for w in txt if re.search(r'^\t<work>', w)]
	worklines = [temptableworkline(l, allworks) for l in works]
	workdatadict = {w[0]: w[1:] for w in worklines}
	workcolumns = [ 'title','language','publication_info','levellabels_00','levellabels_01','levellabels_02',
	                'levellabels_03','levellabels_04','levellabels_05','workgenre','transmission','worktype','provenance',
	                'recorded_date','converted_date','wordcount','firstline','lastline', 'authentic']

	updatedbfromtemptable('authors', 'universalid', authorcolumns, authordatadict)
	updatedbfromtemptable('works', 'universalid', workcolumns, workdatadict)

	return


def gkcanoncleaner(txt):
	"""
	tidy up the greek canon file

	1855546 function calls (1457396 primitive calls) in 3.546 seconds

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

	# cleaning
	lwn = re.compile(r'</workname>\s{2,}(.*?)\s█⑧⓪')
	txt = re.sub(lwn, r'\1</workname>', txt)
	wnc = re.compile(r'(<workname>)(.*?)(</workname>)')
	txt = re.sub(wnc, lambda x: languagesubstitutes(x.group(1), x.group(2), x.group(3)), txt)
	pnc = re.compile(r'(<publicationinfo>)(.*?)(</publicationinfo>)')
	txt = re.sub(pnc, lambda x: languagesubstitutes(x.group(1), x.group(2), x.group(3)), txt)

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


def temptableauthorline(newauthorinfo, allauthors):
	"""

	prepare a line of author data to send to the temporary table

	:param newauthorinfo:
	:return:
	"""

	sh = re.compile(r'<short>(.*?)</short>')
	an = re.compile(r'<authorentry>(.*?)</authorentry>')
	percents = re.compile(r'\%(\d{1,3})')
	au = re.search(an, newauthorinfo)

	try:
		a = 'gr' + au.group(1)
	except:
		a = 'gr0000'

	short = re.search(sh, newauthorinfo)
	try:
		s = re.sub(' {1,}$', '', short.group(1))
		s = re.sub(percents, percentsubstitutes, s)
	except:
		s = ''

	try:
		ao = allauthors[a]
		name = ao.shortname
	except:
		name = ''

	try:
		name = re.sub(' {1,}$', '', name)
	except:
		name = ''

	if len(name) < 1:
		name = s

	return [a, name]


def temptableworkline(newworkinfo, allworks):
	"""
	prepare a line of author data to send to the temporary table

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
			n = 'Poliorcetica'  # 0058w001 does not have a name with this version of the parser....: 'wrk &1Poliorcetica&'
		else:
			# print('no name for',work.group(1))
			n = ''

	if re.search(r'\[Sp\.\]', n) is not None:
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
		tr = trans.group(1)
	except:
		tr = ''

	try:
		wt = wtype.group(1)
	except:
		wt = ''

	wt = re.sub(percents, percentsubstitutes, wt)
	wt = re.sub(r' $', '', wt)

	uid = 'gr' + work.group(1)
	# try some comparisons: the (flawed) canon data can help to fix the flawed idt data
	wo = allworks[uid]

	ti = wo.title
	if ti != n and n != '':
		ti = n

	l0 = wo.levellabels_00
	alllevels = wo.alllevels()

	if l0 == '':
		# yikes: a broken author...
		# should only be one
		#   0656w003 : ['Book', 'section', 'line']
		# print('should insert the following to fix the db:\n\t',work.group(1), ':', cite)
		alllevels = []
		for i in range(0, 6):
			try:
				alllevels.append(cite.pop())
			except:
				alllevels.append('')


	# what we need to match:
	# INSERT INTO tmp_works (universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05,
	# workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, firstline, lastline, authentic)

	# generic values for the data we did not find via this route
	lg = 'G'
	pr = None
	rd = None
	cd = None
	fl = -1
	ll = -1

	newdata = [uid, ti, lg, p]
	for l in alllevels:
		newdata.append(l)
	for data in [g, tr, wt, pr, rd, cd, count, fl, ll, authentic]:
		newdata.append(data)

	return newdata


def peekatcanon(workdbname):
	"""
	an emergency appeal to the canon for a work's structure

	can get rid of this? currently inactive

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
	allauthors = loadallauthorsasobjects(config)
	txt = gkcanoncleaner(txt, allauthors)
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


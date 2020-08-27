# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re

from psycopg2.extras import execute_values as insertlistofvaluetuples

from builder.dbinteraction.connection import setconnection
from builder.lexica.repairperseuscitations import perseusworkmappingfixer
from builder.lexica.fixtranslationtagging import greektranslationtagrepairs
from builder.parsers.betacodeandunicodeinterconversion import cleanaccentsandvj
from builder.parsers.htmltounicode import htmltounicode
from builder.parsers.lexicalparsing import greekwithoutvowellengths, greekwithvowellengths, \
	lsjgreekswapper, translationsummary
from builder.parsers.swappers import forcelunates, superscripterone

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


def mpgreekdictionaryinsert(dictdb: str, entries: list, dbconnection):
	"""

	parser for LOGEION [i.e. H. Dik's edits to Perseus' LSJ]

	work on dictdb entries
	assignable to an mp worker
	insert into db at end

	:param dictdb:
	:param entries:
	:param commitcount:
	:return:
	"""
	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	# places where you can find lang="greek"
	# <foreign>; <orth>; <pron>; <quote>; <gen>; <itype>
	# but there can be a nested tag: you can't convert its contents
	# not clear how much one needs to care: but a search inside a match group could be implemented.

	bodyfinder = re.compile(r'(<div2(.*?)>)(.*?)(</div2>)')
	# <head extent="full" lang="greek" opt="n" orth_orig="θῠγάτηρ">θυγάτηρ</head>
	headfinder = re.compile(r'<head extent="(.*?)" lang="(.*?)" opt="(.*?)" orth_orig="(.*?)">(.*?)</head>')
	# the next will include "rewritten phrase" matches
	# transfinder = re.compile(r'<trans.*?>(.*?)</trans>')
	# this one will not include "rewritten phrase" matches
	transfinder = re.compile(r'<trans>(.*?)</trans>')
	parsedinfofinder = re.compile(r'orig_id="(.*?)" key="(.*?)" type="(.*?)" opt="(.*?)"')

	cleanentryname = re.compile(r'<orth .*?>(.*?)</orth>')

	posfinder = re.compile(r'<pos.*?>(.*?)</pos>')
	prepfinder = re.compile(r'Prep. with')
	conjfinder = re.compile(r'Conj\.,')
	particlefinder = re.compile(r'Particle')
	verbfindera = re.compile(r'<gram type="voice" .*?</gram>')
	verbfinderb = re.compile(r'<tns.*?>(.*?)</tns>')

	# <orth extent="full" lang="greek" opt="n">χύτρ-α</orth>, <gen lang="greek" opt="n">ἡ</gen>,
	nounfindera = re.compile(r'<orth extent=".*?".*?</orth>, <gen.*?>(.*?)</gen>')
	# <orth extent="full" lang="greek" opt="n">βωρεύϲ</orth>, <itype lang="greek" opt="n">εωϲ</itype>, <gen lang="greek" opt="n">ὁ</gen>
	nounfinderb = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?</itype>, <gen.*?>(.*?)</gen>')
	# <orth extent="full" lang="greek" opt="n">βωλο-ειδήϲ</orth>, <itype lang="greek" opt="n">έϲ</itype>,
	twoterminationadjfinder = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?>(.*?)</itype>, <[^g]')
	# <orth extent="full" lang="greek" opt="n">βωμιαῖοϲ</orth>, <itype lang="greek" opt="n">α</itype>, <itype lang="greek" opt="n">ον</itype>,
	threeterminationadjfinder = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?>(.*?)</itype>, <itype .*?>.*?</itype>, <[^g]')

	brevefinder = re.compile(r'&([aeiouAEIOU])breve;')
	macrfinder = re.compile(r'&([aeiouAEIOU])macr;')

	# 500 is c 10% slower than 1000 w/ a SSD: no need to get too ambitious here
	bundlesize = 1000

	qtemplate = """
	INSERT INTO {d} 
		(entry_name, metrical_entry, unaccented_entry, id_number, pos, translations, entry_body)
		VALUES %s"""
	query = qtemplate.format(d=dictdb)

	memory = 0
	while len(entries) > 0:
		# speed up by inserting bundles instead of hundreds of thousands of individual items
		# would be nice to make a sub-function, but note all the compiled regex you need...
		bundelofrawentries = list()
		for e in range(bundlesize):
			try:
				bundelofrawentries.append(entries.pop())
			except IndexError:
				pass

		bundelofcookedentries = list()
		for entry in bundelofrawentries:
			idval = 0
			entry = forcelunates(entry)
			entry = htmltounicode(entry, brevefinder=brevefinder, macrfinder=macrfinder)
			segments = re.search(bodyfinder, entry)
			info = segments.group(2)
			parsedinfo = re.search(parsedinfofinder, info)
			headinfo = re.search(headfinder, entry)

			try:
				idstring = parsedinfo.group(1)
			except AttributeError:
				# no idstring for <div2 id="e)pauri/skw"><head extent="full" lang="greek" opt="n" orth_orig="ἐπαυρίϲκω">ἐπαυρίϲκω</head>, v. ἐπαυρέω. </div2>
				# print('no idstring for', entry)
				# note 'idval' and not 'idstring': we are cutting to the chase...
				idstring = None
				idval = memory + .1

			# <head extent="full" lang="greek" opt="n" orth_orig="θῠγάτηρ">θυγάτηρ</head>
			# headfinder = re.compile(r'<head extent="(.*?)" lang="(.*?)" opt="(.*?)" orth_orig="(.*?)">(.*?)</head>')
			try:
				entryname = headinfo.group(5)
			except AttributeError:
				# <div2 id="crossa)lhmenai" orig_id="n4097a" key="a)lhmenai" type="main" opt="n"><head extent="full" lang="greek" opt="n">ἀλήμεναι</head>, <orth extent="full" lang="greek" opt="n">ἀλῆναι</orth>, v. εἴλω.</div2>
				altheadfinder = re.compile(r'<head extent="(.*?)" lang="(.*?)" opt="(.*?)">(.*?)</head>')
				headinfo = re.search(altheadfinder, entry)
				entryname = headinfo.group(4)
				# print('altheadfinder invoked. yielded {e}'.format(e=entryname))

			# it is possible that the entryname is off:
			# <orth extent="full" lang="greek" opt="n">ἀελλάς</orth>
			# <orth extent="full" lang="greek" opt="n">ἀελλάς</orth>

			entryname = re.sub(cleanentryname, r'\1', entryname)

			metrical = headinfo.group(4)

			try:
				idval = int(re.sub(r'^n', '', idstring))
			except ValueError:
				# you saw something like 'n1234a' instead of 'n1234'
				idstring = (re.sub(r'^n', '', idstring))
				abcval = ord(idstring[-1]) - 96
				idstring = int(idstring[:-1])
				idval = idstring + (.1 * abcval)
				# print('newid', entryname, idstring)
			except TypeError:
				# did the exception above already set idval?
				if not idval:
					print('failed to get id for', entry)

			try:
				body = segments.group(3)
			except AttributeError:
				body = str()
				print('died at', idstring, entry)

			# retag translations
			body = re.sub(r'<i>(.*?)</i>', r'<trans>\1</trans>', body)

			try:
				repair = config['lexica']['repairtranslationtags']
			except KeyError:
				repair = 'y'

			if repair:
				body = greektranslationtagrepairs(body)

			try:
				repair = config['lexica']['repairbadperseusrefs']
			except KeyError:
				repair = 'y'

			if repair == 'y':
				body = perseusworkmappingfixer(body)

			translationlist = re.findall(transfinder, body)
			translationlist = [re.sub(r',$', str(), t.strip()) for t in translationlist]
			# interested in keeping the first two so that we can privilege the primary senses
			# the fixed translations can be fed to the morphology summary translation
			# if you just clean via set() you lose the order...
			firsttwo = translationlist[:2]
			alltrans = set(translationlist)
			translationlist = firsttwo + [t for t in alltrans if t not in firsttwo]
			translations = ' ‖ '.join(translationlist)
			stripped = cleanaccentsandvj(entryname)

			# part of speech stuff
			pos = str()
			calculatepartofspeech = False
			if calculatepartofspeech:
				startofbody = body
				partsofspeech = set(re.findall(posfinder, startofbody))

				if re.findall(conjfinder, startofbody):
					partsofspeech.add('conj.')
				if re.findall(prepfinder, startofbody):
					partsofspeech.add('prep.')
				if re.findall(particlefinder, startofbody):
					partsofspeech.add('partic.')
				nouns = [n for n in re.findall(nounfindera, startofbody) if n in ['ὁ', 'ἡ', 'τό']]
				nouns += [n for n in re.findall(nounfinderb, startofbody) if n in ['ὁ', 'ἡ', 'τό']]
				if nouns:
					partsofspeech.add('subst.')
				adjs = [a for a in re.findall(twoterminationadjfinder, startofbody) if a in ['έϲ', 'εϲ', 'ον', 'όν']]
				adjs += [a for a in re.findall(threeterminationadjfinder, startofbody) if a in ['α', 'ά', 'η', 'ή']]
				if adjs:
					partsofspeech.add('adj.')
				verbs = re.findall(verbfindera, startofbody)
				verbs += re.findall(verbfinderb, startofbody)
				if verbs:
					partsofspeech.add('v.')
				if not partsofspeech and entryname and entryname[-1] == 'ω':
					partsofspeech.add('v.')

				pos = str()
				pos += ' ‖ '.join(partsofspeech)
				pos = pos.lower()

				if len(pos) > 64:
					# parser screwed up and you will be unable to insert
					# ἀλϲοκομέω is the only one at the moment [DEBUG it...]
					pos = str()

			entryname = re.sub(r'(\d+)', superscripterone, entryname)

			if idval % 10000 == 0:
				print('at {n}: {e}'.format(n=idval, e=entryname))

			memory = idval
			bundelofcookedentries.append(tuple([entryname, metrical, stripped, idval, pos, translations, body]))

		# insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

		try:
			insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)
		except:
			# psycopg2.errors.StringDataRightTruncation: value too long for type character varying(64)
			print('could not insert\n')
			for bundle in bundelofcookedentries:
				for b in bundle:
					print(b)

	return


def oldxmlmpgreekdictionaryinsert(dictdb: str, entries: list, dbconnection):
	"""

	greek-lexicon_1999.04.0057.xml version

	Diogenes3 used as the source of the data

	work on dictdb entries
	assignable to an mp worker
	insert into db at end

	:param dictdb:
	:param entries:
	:param commitcount:
	:return:
	"""
	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	# places where you can find lang="greek"
	# <foreign>; <orth>; <pron>; <quote>; <gen>; <itype>
	# but there can be a nested tag: you can't convert its contents
	# not clear how much one needs to care: but a search inside a match group could be implemented.

	bodyfinder = re.compile('(<entryFree(.*?)>)(.*?)(</entryFree>)')
	posfinder = re.compile(r'<pos.*?>(.*?)</pos>')
	prepfinder = re.compile(r'Prep. with')
	conjfinder = re.compile(r'Conj\.,')
	particlefinder = re.compile(r'Particle')
	verbfindera = re.compile(r'<gram type="voice" .*?</gram>')
	verbfinderb = re.compile(r'<tns.*?>(.*?)</tns>')

	bodytrimmer = re.compile(r'(<bibl.*?</bibl>|<gram type="dialect".*?</gram>|<cit.*?</cit>)')

	# <orth extent="full" lang="greek" opt="n">χύτρ-α</orth>, <gen lang="greek" opt="n">ἡ</gen>,
	nounfindera = re.compile(r'<orth extent=".*?".*?</orth>, <gen.*?>(.*?)</gen>')
	# <orth extent="full" lang="greek" opt="n">βωρεύϲ</orth>, <itype lang="greek" opt="n">εωϲ</itype>, <gen lang="greek" opt="n">ὁ</gen>
	nounfinderb = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?</itype>, <gen.*?>(.*?)</gen>')
	# <orth extent="full" lang="greek" opt="n">βωλο-ειδήϲ</orth>, <itype lang="greek" opt="n">έϲ</itype>,
	twoterminationadjfinder = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?>(.*?)</itype>, <[^g]')
	# <orth extent="full" lang="greek" opt="n">βωμιαῖοϲ</orth>, <itype lang="greek" opt="n">α</itype>, <itype lang="greek" opt="n">ον</itype>,
	threeterminationadjfinder = re.compile(r'<orth extent=".*?".*?</orth>, <itype.*?>(.*?)</itype>, <itype .*?>.*?</itype>, <[^g]')

	greekfinder = re.compile(
		'(<(foreign|orth|pron|quote|gen|itype|etym|ref).*?lang="greek".*?>)(.*?)(</(foreign|orth|pron|quote|gen|itype|etym|ref)>)')
	# these arise from nested tags: a more elegant solution would be nice; some other day
	restorea = re.compile(r'<γεν λανγ="γρεεκ" οπτ="ν">(.*?)(</gen>)')
	restoreb = re.compile(r'<προν εχτεντ="φυλλ" λανγ="γρεεκ" οπτ="ν"(.*?)(</pron>)')
	restorec = re.compile(r'<ιτψπε λανγ="γρεεκ" οπτ="ν">(.*?)(</itype>)')

	# 500 is c 10% slower than 1000 w/ a SSD: no need to get too ambitious here
	bundlesize = 1000

	qtemplate = """
	INSERT INTO {d} 
		(entry_name, metrical_entry, unaccented_entry, id_number, pos, translations, entry_body)
		VALUES %s"""
	query = qtemplate.format(d=dictdb)

	idnum = 0
	while len(entries) > 0:
		# speed up by inserting bundles instead of hundreds of thousands of individual items
		# would be nice to make a sub-function, but note all the compiled regex you need...
		bundelofrawentries = list()
		for e in range(bundlesize):
			try:
				bundelofrawentries.append(entries.pop())
			except IndexError:
				pass

		bundelofcookedentries = list()
		for entry in bundelofrawentries:
			if entry[0:10] != "<entryFree":
				pass
			else:
				segments = re.search(bodyfinder, entry)
				try:
					body = segments.group(3)
				except AttributeError:
					body = ''
					print('died at', idnum, entry)
				info = segments.group(2)
				parsedinfo = re.search('id="(.*?)"\skey=(".*?")\stype="(.*?)"\sopt="(.*?)"', info)
				try:
					idnum = parsedinfo.group(1)
					key = parsedinfo.group(2)
					etype = parsedinfo.group(3)  # will go unused
					opt = parsedinfo.group(4)  # will go unused
				except AttributeError:
					# only one greek dictionary entry will throw an exception: n29246
					# print('did not find key at', idnum, entry)
					idnum = 'n29246'
					key = ''
					etype = ''
					opt = ''
				entryname = re.sub(r'"(.*?)"', lambda x: greekwithoutvowellengths(x.group(1)), key.upper())
				entryname = re.sub(r'(\d+)', superscripterone, entryname)
				metrical = re.sub(r'(")(.*?)(")', lambda x: greekwithvowellengths(x.group(2)), key.upper())
				metrical = re.sub(r'(\d+)', superscripterone, metrical)
				metrical = re.sub(r'"', r'', metrical)

				body = re.sub(greekfinder, lsjgreekswapper, body)
				body = re.sub(restorea, r'<gen lang="greek" opt="n">\1\2', body)
				body = re.sub(restoreb, r'<pron extent="full">\1\2', body)
				body = re.sub(restorec, r'<itype lang="greek" opt="n">\1\2', body)

				# 'n1000' --> 1000
				idnum = int(re.sub(r'^n', '', idnum))
				translationlist = translationsummary(entry, 'tr')
				stripped = cleanaccentsandvj(entryname)

				# part of speech stuff
				startofbody = re.sub(bodytrimmer, '', body)
				startofbody = startofbody[:500]
				partsofspeech = set(re.findall(posfinder, startofbody))

				if re.findall(conjfinder, startofbody):
					partsofspeech.add('conj.')
				if re.findall(prepfinder, startofbody):
					partsofspeech.add('prep.')
				if re.findall(particlefinder, startofbody):
					partsofspeech.add('partic.')
				nouns = [n for n in re.findall(nounfindera, startofbody) if n in ['ὁ', 'ἡ', 'τό']]
				nouns += [n for n in re.findall(nounfinderb, startofbody) if n in ['ὁ', 'ἡ', 'τό']]
				if nouns:
					partsofspeech.add('subst.')
				adjs = [a for a in re.findall(twoterminationadjfinder, startofbody) if a in ['έϲ', 'εϲ', 'ον', 'όν']]
				adjs += [a for a in re.findall(threeterminationadjfinder, startofbody) if a in ['α', 'ά', 'η', 'ή']]
				if adjs:
					partsofspeech.add('adj.')
				verbs = re.findall(verbfindera, startofbody)
				verbs += re.findall(verbfinderb, startofbody)
				if verbs:
					partsofspeech.add('v.')
				if not partsofspeech and entryname and entryname[-1] == 'ω':
					partsofspeech.add('v.')

				pos = ''
				pos += ' ‖ '.join(partsofspeech)
				pos = pos.lower()

				if idnum % 10000 == 0:
					print('at {n}: {e}'.format(n=idnum, e=entryname))
				bundelofcookedentries.append(tuple([entryname, metrical, stripped, idnum, pos, translationlist, body]))

		insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

	return


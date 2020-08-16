import configparser
import re

from psycopg2.extras import execute_values as insertlistofvaluetuples

from builder.dbinteraction.connection import setconnection
from builder.lexica.fixtranslationtagging import latintranslationtagrepairs
from builder.lexica.repairperseuscitations import latindramacitationformatconverter, oneofflatinworkremapping
from builder.parsers.htmltounicode import htmltounicode
from builder.parsers.lexica import greekwithvowellengths, latinvowellengths, translationsummary
from builder.parsers.swappers import superscripterone

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


def oldmplatindictionaryinsert(dictdb: str, entries: list, dbconnection):
	"""

	this is the one you should use...

	latin-lexicon_1999.04.0059.xml

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

	bodyfinder = re.compile(r'(<entryFree(.*?)>)(.*?)(</entryFree>)')
	defectivebody = re.compile(r'(<entryFree(.*?)>)(.*?)$')
	greekfinder = re.compile(r'(<foreign lang="greek">)(.*?)(</foreign>)')

	etymfinder = re.compile(r'<etym.*?</etym>')
	badprepfinder = re.compile(r'ith(|out)( | a )<pos opt="n">prep.</pos>')
	posfinder = re.compile(r'<pos.*?>(.*?)</pos>')
	particlefinder = re.compile(r'\. particle')

	qtemplate = """
	INSERT INTO {d} 
		(entry_name, metrical_entry, id_number, entry_key, pos, translations, entry_body)
		VALUES %s"""
	query = qtemplate.format(d=dictdb)

	bundlesize = 1000

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
				# print(entry[0:25])
				pass
			else:
				segments = re.search(bodyfinder, entry)
				try:
					body = segments.group(3)
				except AttributeError:
					# AttributeError: 'NoneType' object has no attribute 'group'
					segments = re.search(defectivebody, entry)
					try:
						body = segments.group(3)
					except AttributeError:
						print('died at', entry)
						body = str()
				info = segments.group(2)
				parsedinfo = re.search('id="(.*?)" type="(.*?)" key="(.*?)" opt="(.*?)"', info)
				idnum = parsedinfo.group(1)
				etype = parsedinfo.group(2)  # will go unused
				key = parsedinfo.group(3)
				opt = parsedinfo.group(4)  # will go unused

				# handle words like abactus which have key... n... opt... where n is the variant number
				# this pattern interrupts the std parsedinfo flow
				metricalentry = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
				metricalentry = re.sub(r' \((\d)\)', superscripterone, metricalentry)
				# kill off the tail if you still have one: fĭber" n="1
				metricalentry = re.sub(r'(.*?)"\s.*?$', r'\1', metricalentry)
				entryname = re.sub('(_|\^)', str(), metricalentry)
				metricalentry = latinvowellengths(metricalentry)

				key = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', key)
				key = re.sub(r' \((\d)\)', superscripterone, key)
				key = latinvowellengths(key)

				# 'n1000' --> 1000
				idnum = int(re.sub(r'^n', str(), idnum))

				# parts of speech
				cleanbody = re.sub(etymfinder, str(), body)
				cleanbody = re.sub(badprepfinder, str(), cleanbody)
				pos = list()
				pos += list(set(re.findall(posfinder, cleanbody)))
				if re.findall(particlefinder, cleanbody):
					pos.append('partic.')
				pos = ' ‖ '.join(pos)
				pos = pos.lower()

				translationlist = translationsummary(entry, 'hi')

				# do some quickie greek replacements
				body = re.sub(greekfinder, lambda x: greekwithvowellengths(x.group(2)), body)

				try:
					repair = config['lexica']['repairtranslationtags']
				except KeyError:
					repair = 'y'

				if repair:
					body = latintranslationtagrepairs(body)

				try:
					repair = config['lexica']['repairbadperseusrefs']
				except KeyError:
					repair = 'y'

				if repair == 'y':
					body = latindramacitationformatconverter(body, dbconnection)
					body = oneofflatinworkremapping(body)
				if idnum % 10000 == 0:
					print('at {n}: {e}'.format(n=idnum, e=entryname))
				bundelofcookedentries.append(tuple([entryname, metricalentry, idnum, key, pos, translationlist, body]))

		insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

	return


def newmplatindictionaryinsert(dictdb: str, entries: list, dbconnection):
	"""

	new latin xml is hopeless? [lat.ls.perseus-eng1.xml]

	the perseus citation are in multiple formats.
	tibullus is wrong: lt0660 vs lt0060
	cicero refs are nonstandard
	horace work numbers have shifted
	...

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

	bodyfinder = re.compile(r'(<entryFree(.*?)>)(.*?)(</entryFree>)')
	defectivebody = re.compile(r'(<entryFree(.*?)>)(.*?)$')
	greekfinder = re.compile(r'(<foreign lang="greek">)(.*?)(</foreign>)')

	etymfinder = re.compile(r'<etym.*?</etym>')
	badprepfinder = re.compile(r'ith(|out)( | a )<pos opt="n">prep.</pos>')
	posfinder = re.compile(r'<pos.*?>(.*?)</pos>')
	particlefinder = re.compile(r'\. particle')

	brevefinder = re.compile(r'&([aeiouAEIOU])breve;')
	macrfinder = re.compile(r'&([aeiouAEIOU])macr;')

	qtemplate = """
	INSERT INTO {d} 
		(entry_name, metrical_entry, id_number, entry_key, pos, translations, entry_body)
		VALUES %s"""
	query = qtemplate.format(d=dictdb)

	bundlesize = 1000

	while len(entries) > 0:
		idval = None
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
			entry = htmltounicode(entry, brevefinder=brevefinder, macrfinder=macrfinder)

			segments = re.search(bodyfinder, entry)
			try:
				body = segments.group(3)
			except AttributeError:
				segments = re.search(defectivebody, entry)
				try:
					body = segments.group(3)
				except AttributeError:
					# died at </div0> </body></text></TEI.2>
					# print('died at', entry)
					break

			try:
				info = segments.group(1)
			except:
				print('failed', body)
				info = str()
			# <entryFree id="n51556" type="main" key="zmaragdachates">
			parsedinfo = re.search('id="(.*?)" type="(.*?)" key="(.*?)"', info)
			try:
				idstring = parsedinfo.group(1)
			except:
				print('died on\n', segments.group(1))
				idstring = str()
			etype = parsedinfo.group(2)  # will go unused
			entryname = parsedinfo.group(3)

			# handle words like abactus which have key... n... opt... where n is the variant number
			# this pattern interrupts the std parsedinfo flow
			metricalentry = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', entryname)
			metricalentry = re.sub(r' \((\d)\)', superscripterone, metricalentry)
			# kill off the tail if you still have one: fĭber" n="1
			metricalentry = re.sub(r'(.*?)"\s.*?$', r'\1', metricalentry)
			entryname = re.sub('(_|\^)', str(), metricalentry)
			metricalentry = latinvowellengths(metricalentry)

			entryname = re.sub(r'(.*?)(\d)"(.*?\d)', r'\1 (\2)', entryname)
			entryname = re.sub(r' \((\d)\)', superscripterone, entryname)
			entryname = latinvowellengths(entryname)

			# 'n1000' --> 1000
			try:
				idval = int(re.sub(r'^n', str(), idstring))
			except ValueError:
				# you saw something like 'n1234a' instead of 'n1234'
				idstring = (re.sub(r'^n', str(), idstring))
				abcval = ord(idstring[-1]) - 96
				idstring = int(idstring[:-1])
				idval = idstring + (.1 * abcval)
				# print('newid', entryname, idstring)

			# parts of speech
			cleanbody = re.sub(etymfinder, str(), body)
			cleanbody = re.sub(badprepfinder, str(), cleanbody)
			pos = list()
			pos += list(set(re.findall(posfinder, cleanbody)))
			if re.findall(particlefinder, cleanbody):
				pos.append('partic.')
			pos = ' ‖ '.join(pos)
			pos = pos.lower()

			translationlist = translationsummary(entry, 'hi')
			# do some quickie greek replacements
			body = re.sub(greekfinder, lambda x: greekwithvowellengths(x.group(2)), body)

			entryname = re.sub(r'(\d+)', superscripterone, entryname)

			if idval % 10000 == 0:
				print('at {n}: {e}'.format(n=idval, e=entryname))

			bundelofcookedentries.append(tuple([entryname, metricalentry, idval, entryname, pos, translationlist, body]))

		insertlistofvaluetuples(dbcursor, query, bundelofcookedentries)

	return

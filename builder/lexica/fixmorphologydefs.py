# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import random
import re

from psycopg2.extras import execute_values as insertlistofvaluetuples

from builder.dbinteraction.connection import setconnection


def analysisrewriter(language: str, xreftranslations: dict, dbconnection=None):
	"""

	the stock translations included with the observed forms can be defective; a rewritten dictionary entry can fix this

	1. grab all of the xref_number values from greek_lemmata [DONE & it sent you here]
	2. associate the first two translations from the dictionary with a xref_number [DONE & it sent you here]
	3. then gobble up all of the greek_morphology entries
	4. then check each '<transl></transl>' inside of all of the possible_dictionary_forms for these entries against the xref_number

	xreftranslations is a dict:

		{xref: translation}

	hipparchiaDB=# select * from greek_morphology where observed_form='πάϲχω';
	 observed_form |  xrefs   | prefixrefs |                                                                  possible_dictionary_forms
	---------------+----------+------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------
	 πάϲχω         | 80650925 |            | <possibility_1>πάϲχω<xref_value>80650925</xref_value><xref_kind>9</xref_kind><transl>have</transl><analysis>pres subj act 1st sg</analysis></possibility_1>+
	               |          |            | <possibility_2>πάϲχω<xref_value>80650925</xref_value><xref_kind>9</xref_kind><transl>have</transl><analysis>pres ind act 1st sg</analysis></possibility_2> +
	               |          |            |

	First Draft MP version with managed list: "Build took 217.69 minutes"

	Dict version: "Build took 7.43 minutes"

	:param grammardb:
	:param xreftranslations:
	:param islatin:
	:param dbconnection:
	:return:
	"""

	if not dbconnection:
		dbconnection = setconnection()

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	# save all work in a list and then update the morph table at the very end to avoid tons of read-and-write
	newmorph = list()

	morphtemplate = 'SELECT observed_form, xrefs, prefixrefs, possible_dictionary_forms FROM {lg}_morphology'.format(lg=language)

	possibilityfinder = re.compile(r'(<possibility_\d>)(.*?)(<xref_value>)(.*?)(</xref_value><xref_kind>.*?</xref_kind><transl>)(.*?)(</transl><analysis>.*?</analysis></possibility_\d{1,}>)')

	randomtableid = str().join([random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(8)])

	temptableupdater = """
		UPDATE {lg}_morphology SET possible_dictionary_forms = tempmorph_{id}.possible_dictionary_forms 
			FROM tempmorph_{id} 
			WHERE 
				{lg}_morphology.observed_form = tempmorph_{id}.observed_form AND
				{lg}_morphology.xrefs = tempmorph_{id}.xrefs """

	# grab all morph...
	dbcursor.execute(morphtemplate)
	entries = dbcursor.fetchall()

	for e in entries:
		# e[0]: observed_form
		# e[1]: xrefs
		# e[2]: prefixrefs
		# e[3]: possible_dictionary_forms
		dictforms = e[3]
		poss = re.findall(possibilityfinder, dictforms)
		newposs = list()
		for p in poss:
			# p[0]: '<possibility_\d>'
			# p[1]: 'lātrōnēs, latro²'
			# p[2]: '<xref_value>'
			# p[3]: '40409805'
			# p[4]: '</xref_value><xref_kind>9</xref_kind><transl>'
			# p[5]: 'a hired servant'
			# p[6]: '</transl><analysis>masc acc pl</analysis></possibility_1>'
			p = list(p)
			try:
				p[5] = xreftranslations[p[3]]
				# 'translation' = xreftranslations['xrval']
				# print('{p} in xrefs'.format(p=p[1]))
			except KeyError:
				# print('KeyError on {p}'.format(p=p[1]))
				# there will be *plenty* of misses
				pass
			newp = str().join(p)
			newposs.append(newp)
		newposs = '\n'.join(newposs)
		newmorph.append((e[0], e[1], e[2], newposs))

	createandloadmorphtemptable(randomtableid, newmorph, dbconnection)

	print('built the new data; now updating the {lg} morphology table with the new values: this can take several minutes'.format(lg=language))
	# this part is plenty slow....
	dbcursor.execute(temptableupdater.format(lg=language, id=randomtableid))

	dbconnection.commit()

	return


def createandloadmorphtemptable(tableid: str, tabledata: list, dbconnection):
	"""

	hipparchiaDB=# \d+ greek_morphology
	                                               Table "public.greek_morphology"
	          Column           |          Type          | Collation | Nullable | Default | Storage  | Stats target | Description
	---------------------------+------------------------+-----------+----------+---------+----------+--------------+-------------
	 observed_form             | character varying(64)  |           |          |         | extended |              |
	 xrefs                     | character varying(128) |           |          |         | extended |              |
	 prefixrefs                | character varying(128) |           |          |         | extended |              |
	 possible_dictionary_forms | text                   |           |          |         | extended |              |

	:param tableid:
	:param tabledata:
	:param dbconnection:
	:return:
	"""

	# print('createandloadmorphtemptable() for dbconnection {u}'.format(u=dbconnection.uniquename))

	dbcursor = dbconnection.cursor()

	tabletemplate = """
	CREATE TEMPORARY TABLE tempmorph_{id}
		( observed_form VARCHAR, xrefs VARCHAR, prefixrefs VARCHAR, possible_dictionary_forms TEXT )
	"""

	qtemplate = 'INSERT INTO tempmorph_{id} (observed_form, xrefs, prefixrefs, possible_dictionary_forms) VALUES %s'

	dbcursor.execute(tabletemplate.format(id=tableid))

	# lat = [x for x in tabledata if x[1] == '40409805']
	# print('lat', lat)

	insertlistofvaluetuples(dbcursor, qtemplate.format(id=tableid), tabledata)

	dbconnection.commit()

	return


def fixgreeklemmatacapitalization():
	"""

	capitalization problem in greek

	greek-analyses.txt:


	*dhmosqenikw=n  {23331729 9 *dhmosqeniko/s      Demosthenic     fem gen pl}{23331729 9 *dhmosqeniko/s   Demosthenic     masc/neut gen pl}
	*dhmosqenikw=s  {23331729 9 *dhmosqeniko/s      Demosthenic     adverbial}
	*dhmosqenikw=|  {23331729 9 *dhmosqeniko/s      Demosthenic     masc/neut dat sg}


	greek-lemmata.txt

	dhmosqe/neios	23331729	dhmosqe/neia (neut nom/voc/acc pl)	dhmosqe/neion (masc acc sg) (neut nom/voc/acc sg)	dhmosqe/neios (masc nom sg)
	dhmosqeniko/s	23331729	dhmosqenika/ (neut nom/voc/acc pl) (fem nom/voc/acc dual) (fem nom/voc sg (doric aeolic))	dhmosqenikai/ (fem nom/voc pl)	dhmosqenikai=s (fem dat pl)	dhmosqenikh/ (fem nom/voc sg (attic epic ionic))	dhmosqenikh/n (fem acc sg (attic epic ionic))	dhmosqenikh=s (fem gen sg (attic epic ionic))	dhmosqenikh=| (fem dat sg (attic epic ionic))	dhmosqeniko/n (masc acc sg) (neut nom/voc/acc sg)	dhmosqeniko/s (masc nom sg)	dhmosqenikoi/ (masc nom/voc pl)	dhmosqenikoi=s (masc/neut dat pl)	dhmosqenikou/s (masc acc pl)	dhmosqenikou= (masc/neut gen sg)	dhmosqenikw=n (fem gen pl) (masc/neut gen pl)	dhmosqenikw=s (adverbial)	dhmosqenikw=| (masc/neut dat sg)


	*d is "Δ"
	d is "δ"

	hipparchiaDB=# select observed_form, xrefs from greek_morphology where observed_form ~* 'ημοϲθενικ';
	observed_form |  xrefs
	---------------+----------
	Δημοϲθενικήν  | 23331729
	Δημοϲθενικά   | 23331729
	Δημοϲθενικῶϲ  | 23331729
	Δημοϲθενικοί  | 23331729
	...

	this can be fixed via "23331729"


	"""

	print('fixing the capitalization problem in the "greek_lemmata" table')

	dbconnection = setconnection()
	dbcursor = dbconnection.cursor()

	q = 'SELECT xrefs, observed_form FROM greek_morphology'
	dbcursor.execute(q)
	items = dbcursor.fetchall()

	# note the problem with .isupper() at the bottom of this page...

	islowercase = {i[0]: i[1].islower() for i in items}

	q = 'SELECT dictionary_entry, xref_number FROM greek_lemmata'
	dbcursor.execute(q)
	items = dbcursor.fetchall()

	fixme = dict()
	for i in items:
		xref = str(i[1])  # nice little type mismatch gotcha...
		word = i[0]
		low = True
		try:
			low = islowercase[xref]
		except KeyError:
			pass
		if not low and '-' not in word:
			# ἐπί-ὤζω should not turn into Ἐπί-ὤζω...
			fixme[word] = word.capitalize()

	tabledata = [(k, fixme[k]) for k in fixme]

	randomtableid = str().join([random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(8)])

	tabletemplate = """
	CREATE TEMPORARY TABLE tempmorph_{id}
		( observed_form VARCHAR, revisedentry VARCHAR )
	"""

	qtemplate = 'INSERT INTO tempmorph_{id} (observed_form, revisedentry) VALUES %s'

	dbcursor.execute(tabletemplate.format(id=randomtableid))
	insertlistofvaluetuples(dbcursor, qtemplate.format(id=randomtableid), tabledata)


	temptableupdater = """
		UPDATE greek_lemmata SET dictionary_entry = tempmorph_{id}.revisedentry
			FROM tempmorph_{id} 
			WHERE 
				greek_lemmata.dictionary_entry = tempmorph_{id}.observed_form"""

	dbcursor.execute(temptableupdater.format(id=randomtableid))

	return


"""

	Python 3.9.5 (default, May  4 2021, 03:36:27)
	
	Greek vs .isupper(): seems like .islower() is properly implemented but that .isupper() is not

	>>> 'ζῳώδηϲ'.islower()
	True
	>>> 'Δημοϲθενικοί'.islower()
	False
	>>> 'Δημοϲθενικοί'.isupper()
	False
	>>> x = 'Ἀεὶ'
	>>> x.islower()
	False
	>>> x.isupper()
	False
	>>> x = 'εἰϲ'
	>>> x.isupper()
	False
	>>> x.islower()
	True
	>>> x = 'ἂν'
	>>> x.islower()
	True
	>>> x.isupper()
	False
	>>> x= 'ὦ'
	>>> x.isupper()
	False
	>>> x.islower()
	True

	>>> x.capitalize()
	'Ὦ'
	>>> 'ἂν'.capitalize()
	'Ἂν'
	
"""

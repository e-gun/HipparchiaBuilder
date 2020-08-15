# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
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

	posfinder = re.compile(r'(<possibility.*?<xref_value>)(.*?)(</xref_value><xref_kind>.*?</xref_kind><transl>)(.*?)(</transl><analysis>.*?</analysis></possibility_\d{1,}>)')

	randomtableid = str().join([random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(8)])

	temptableupdater = """
		UPDATE {lg}_morphology SET possible_dictionary_forms = tempmorph_{id}.possible_dictionary_forms 
			FROM tempmorph_{id} WHERE {lg}_morphology.observed_form = tempmorph_{id}.observed_form"""

	# grab all morph...
	dbcursor.execute(morphtemplate)
	entries = dbcursor.fetchall()

	for e in entries:
		pdf = e[3]
		poss = re.findall(posfinder, pdf)
		newposs = list()
		for p in poss:
			p = list(p)
			try:
				p[3] = xreftranslations[p[1]]
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

	print('built the new data; now updating the {lg} morphology table with the new values: this will take several minutes'.format(lg=language))
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

	insertlistofvaluetuples(dbcursor, qtemplate.format(id=tableid), tabledata)

	dbconnection.commit()

	return

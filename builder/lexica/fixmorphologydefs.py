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

"""

Process Process-4:
Traceback (most recent call last):
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.7/lib/python3.7/multiprocessing/process.py", line 297, in _bootstrap
    self.run()
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.7/lib/python3.7/multiprocessing/process.py", line 99, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/erik/hipparchia_venv/HipparchiaBuilder/builder/lexica/mpgrammarworkers.py", line 316, in mpanalysisrewrite
    dbcursor.execute(temptableupdater.format(lg=language, id=randomtableid))
psycopg2.errors.DeadlockDetected: deadlock detected
DETAIL:  Process 37916 waits for ShareLock on transaction 1286139; blocked by process 37918.
Process 37918 waits for ShareLock on transaction 1286132; blocked by process 37916.
HINT:  See server log for query details.
CONTEXT:  while updating tuple (43409,4) in relation "greek_morphology"

"""


def mpanalysisrewrite(language: str, headwords, dbconnection):
	"""

	the stock translations included with the observed forms can be defective; a rewritten dictionary entry can fix this

	1. grab all of the xref_number values from greek_lemmata [DONE & it sent you here]
	2. associate the first two translations from the dictionary with this headword
	3. then gobble up all of the greek_morphology entries that have this xref
	4. then check each '<transl></transl>' inside of all of the possible_dictionary_forms for these entries

	headwords are a managed list; they come via:

		headwords = [(h, headwords[h], translations[h]) for h in headwords if h in translations]

	a list item is a tuple like:

		(πάϲχω, 80650925, 'have something done to one, suffer')

	'xrefs character varying(128)'

	hipparchiaDB=# select xrefs from greek_morphology where observed_form='δεόντων';
		xrefs
		------------------------------
		23101772, 23091564, 22435783
		(1 row)


	 # https://www.postgresql.org/docs/9.4/queries-values.html

	 CREATE TEMPORARY TABLE tt AS SELECT * FROM
	    (VALUES (1, 1, 1, 1), (2, 2, 2, 2), (3, 3, 3, 3), (4, 4, 4,4)) as t (observed_form,xrefs,prefixrefs,possible_dictionary_forms);

	 hipparchiaDB=# select * from tt;
	  observed_form | xrefs | prefixrefs | possible_dictionary_forms
	 ---------------+-------+------------+---------------------------
	              1 |     1 |          1 |                         1
	              2 |     2 |          2 |                         2
	              3 |     3 |          3 |                         3
	              4 |     4 |          4 |                         4

	:param grammardb:
	:param entries:
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

	# lextemplate = 'SELECT translations FROM {lg}_dictionary WHERE entry_name=%s'.format(lg=language)
	morphtemplate = 'SELECT observed_form, xrefs, prefixrefs, possible_dictionary_forms FROM {lg}_morphology WHERE xrefs ~* %s'.format(lg=language)

	posfinder = re.compile(r'(<possibility.*?<xref_value>)(.*?)(</xref_value><xref_kind>.*?</xref_kind><transl>)(.*?)(</transl><analysis>.*?</analysis></possibility_\d{1,}>)')

	randomtableid = str().join([random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(8)])

	temptableupdater = """
		UPDATE {lg}_morphology SET possible_dictionary_forms = tempmorph_{id}.possible_dictionary_forms 
			FROM tempmorph_{id} WHERE {lg}_morphology.observed_form = tempmorph_{id}.observed_form"""

	while headwords:
		if not len(headwords) % 100:
			print('{h} headwords remain for dbconnection {u}'.format(h=len(headwords), u=dbconnection.uniquename))
		try:
			hw = headwords.pop()
		except IndexError:
			hw = (None, None, None)

		theword = hw[0]
		thexref = str(hw[1])
		try:
			thetrans = re.sub(r'(\w),\W*?$', r'\1', hw[2])  # clean out trailing gunk
		except TypeError:
			# TypeError: expected string or bytes-like object
			thetrans = hw[2]

		dbcursor.execute(morphtemplate, (thexref,))

		entries = dbcursor.fetchall()

		for e in entries:
			pdf = e[3]
			poss = re.findall(posfinder, pdf)
			newposs = list()
			for p in poss:
				p = list(p)
				if p[1] == thexref:
					# print('{w} [{x}]: {a} --> {b}'.format(w=theword, x=thexref, a=p[3], b=thetrans))
					p[3] = thetrans
				newp = str().join(p)
				newposs.append(newp)
			newposs = '\n'.join(newposs)
			newmorph.append((e[0], e[1], e[2], newposs))

	createandloadmorphtemptable(randomtableid, newmorph, dbconnection)
	print('temptableupdater for dbconnection {u}'.format(u=dbconnection.uniquename))
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
	print('createandloadmorphtemptable() for dbconnection {u}'.format(u=dbconnection.uniquename))

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
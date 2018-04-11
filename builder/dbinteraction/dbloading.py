# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import io
import json

from builder.dbinteraction.dbhelperfunctions import workmaker


def insertworksintoauthortable(authorobject, dbreadyversion, dbconnection):
	"""

	run throught the dbreadyversion and put it into the db
	iterate through the works
	problems: some work numbers are incorrect/impossible

	NOTE: before 26 dec 2016 works were stored in their own DBs; this worked quite well, but it yielded a problem when
	the INS and DDP data was finally merged into Hipparchia: suddenly postgresql was working with 190k DBs, and that
	yields a significant scheduler and filesystem problem; the costs were too high

	here is a marked line...
	['1', [('0', '87'), ('1', '1'), ('2', '1'), ('3', '1'), ('4', '1')], "Μή μ' ἔπεϲιν μὲν ϲτέργε, νόον δ' ἔχε καὶ φρέναϲ ἄλληι, ", "Μη μ' επεϲιν μεν ϲτεργε, νοον δ' εχε και φρεναϲ αλληι, "]

	for hypens:
	SELECT * from gr9999w999 WHERE (stripped_line LIKE '%marinam%') OR (hyphenated_words LIKE '%marinam%')

	:param authorobject:
	:param dbreadyversion:
	:param cursor:
	:param dbconnection:
	:return:
	"""

	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	for indexedat in range(len(authorobject.works)):
		# warning: '002' might be the value at work[0]
		workmaker(authorobject, indexedat, dbcursor)

	separator = '\t'

	queryvalues = generatequeryvaluetuples(dbreadyversion, authorobject)

	stream = generatecopystream(queryvalues, separator=separator)

	columns = ('index',
				'wkuniversalid',
				'level_00_value',
				'level_01_value',
				'level_02_value',
				'level_03_value',
				'level_04_value',
				'level_05_value',
				'marked_up_line',
				'accented_line',
				'stripped_line',
				'hyphenated_words',
				'annotations')

	table = authorobject.universalid

	dbcursor.copy_from(stream, table, sep=separator, columns=columns)

	return


def generatequeryvaluetuples(dbreadyversion, authorobject):
	"""

	generates a list of tuples

	this is something you can send to postgres that fits the query template:

		index,
		wkuniversalid,
		level_00_value,
		level_01_value,
		level_02_value,
		level_03_value,
		level_04_value,
		level_05_value,
		marked_up_line,
		accented_line,
		stripped_line,
		hyphenated_words,
		annotations

	i.e., vtemplate = '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

	:return:
	"""

	index = 0

	queryvalues = list()

	for line in dbreadyversion:
		if line[2] == '' or line[2] == ' ':
			# cd resets can produce blanks with bad line numbers, etc
			# this can leave a blank line numbered '5.1' sandwiched between 5.292 and 5.293
			# let's hope nothing with useful info gets skipped...
			pass
		else:
			index += 1
			wn = int(line[0])

			if wn < 10:
				wn = '00' + str(wn)
			elif wn < 100:
				wn = '0' + str(wn)
			else:
				wn = str(wn)

			wkuniversalid = authorobject.universalid + 'w' + wn

			try:
				wk = authorobject.works[authorobject.workdict[wn]]
				wklvs = list(wk.structure.keys())
				wklvs.sort()
				try:
					toplvl = wklvs.pop()
				except IndexError:
					# this does in fact seem to be at the bottom of a certain class of error; and it likely emerges from bad idx parsing: tough
					print('could not find top level; workobject level list is empty: anum={a} wn={w} tit={t}'.format(a=authorobject.universalid, w=wk.worknumber, t=wk.title.format))

				tups = line[1]

				if authorobject.universalid[0:2] in ['ZZ', 'XX', 'YY', 'in', 'dp', 'ch']:
					# level 5 contains useful information for the inscriptions: don't nuke it
					# level00 = line; level01 = face; [gap in levels]; level05 = documentID
					# all of this gets taken care of in secondpassdbrewrite.py
					pass
				else:
					for lvl in range(0, len(tups)):
						if lvl > toplvl:
							# do we want '-1' instead?
							tups[lvl] = (lvl, -1)
				queryvalues.append(tuple([index, wkuniversalid, tups[0][1], tups[1][1], tups[2][1], tups[3][1], tups[4][1], tups[5][1],
						line[2], line[3], line[4], line[5], line[6]]))

				if index == 413 and wkuniversalid == 'gr2762w004':
					print('bugged line', queryvalues[-1])
			except:
				if index < 2:
					# the proper work number will be set real soon now
					pass
				else:
					print('failed to set a work number for db insert: at line', str(index), 'work', wn,
						  'does not fit with', authorobject.idxname)
					ws = json.dumps(wk.structure)
					print('workobject: wn=' + str(wk.worknumber) + ' tit=' + wk.title + ' struct=' + ws)
					# print('compare to the authorobject: ' + authorobject.universalid + ' wks=' + authorobject.works)
					print(line)
				pass

	return queryvalues


def generatecopystream(queryvaluetuples, separator='\t'):
	"""

	postgres inserts much faster via "COPY FROM"

	prepare data to match the psychopg2.copy_from() interface

	copy_from(file, table, sep='\t', null='\\N', size=8192, columns=None)
		Read data from the file-like object file appending them to the table named table.

	see the example at http://initd.org/psycopg/docs/cursor.html:

		f = StringIO("42\tfoo\n74\tbar\n")
		cur.copy_from(f, 'test', columns=('num', 'data'))

	:param queryvaluetuples:
	:return:
	"""

	copystream = io.StringIO()

	for t in queryvaluetuples:
		copystream.write(separator.join([str(x) for x in t]) + '\n')

	copystream.seek(0)

	return copystream

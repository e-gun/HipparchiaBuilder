import io
import json


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


def resultiterator(cursor, chunksize=5000):
	"""

	Yield a generator from fetchmany to keep memory usage down in contrast to

		results = curs.fetchall()

	see: http://code.activestate.com/recipes/137270-use-generators-for-fetching-large-db-record-sets/

	:param cursor:
	:param chunksize:
	:return:
	"""

	while True:
		results = cursor.fetchmany(chunksize)
		if not results:
			break
		for result in results:
			yield result


def authortablemaker(authordbname, dbconnection):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""

	dbcursor = dbconnection.cursor()

	query = 'DROP TABLE IF EXISTS public.{adb}'.format(adb=authordbname)
	dbcursor.execute(query)

	template = """
		CREATE TABLE public.{adb} (
			index integer NOT NULL UNIQUE DEFAULT nextval('{adb}'::regclass),
            wkuniversalid character varying(10) COLLATE pg_catalog."default",
            level_05_value character varying(64) COLLATE pg_catalog."default",
            level_04_value character varying(64) COLLATE pg_catalog."default",
            level_03_value character varying(64) COLLATE pg_catalog."default",
            level_02_value character varying(64) COLLATE pg_catalog."default",
            level_01_value character varying(64) COLLATE pg_catalog."default",
            level_00_value character varying(64) COLLATE pg_catalog."default",
            marked_up_line text COLLATE pg_catalog."default",
            accented_line text COLLATE pg_catalog."default",
            stripped_line text COLLATE pg_catalog."default",
            hyphenated_words character varying(128) COLLATE pg_catalog."default",
            annotations character varying(256) COLLATE pg_catalog."default"
        ) WITH ( OIDS=FALSE );
	"""

	query = template.format(adb=authordbname)

	dbcursor.execute(query)

	query = 'GRANT SELECT ON TABLE {adb} TO hippa_rd;'.format(adb=authordbname)
	dbcursor.execute(query)

	# print('failed to create',workdbname)

	dbconnection.commit()

	return


def tablenamer(authorobject, indexedat):
	"""
	tell me the name of the table we will be working with

	called by: dbauthoradder & workmaker
	:param authorobject:
	:param thework:
	:return:
	"""

	wk = authorobject.works[indexedat]
	nm = authorobject.number
	wn = wk.worknumber

	if wn < 10:
		nn = '00' + str(wn)
	elif wn < 100:
		nn = '0' + str(wn)
	else:
		nn = str(wn)

	pr = authorobject.universalid[0:2]

	workdbname = pr + nm + 'w' + nn

	return workdbname
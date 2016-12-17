# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re
import configparser
from multiprocessing import Pool
from builder.dbinteraction.db import setconnection, dbauthorloadersubroutine, dbauthorandworkloader, dbauthoradder
from builder.builder_classes import dbAuthor, dbOpus, dbWorkLine

"""

the goal is to take an ins or ddp db as built by the standard parser and to break it down into a new set of databases

the original files just heap up various documents inside of larger works, but this means you lose useful access to the
location and date information for each individual document, information that could be used as the basis for a search

for example 'INS0080' ==> 'Black Sea and Scythia Minor'
	w001 is 'IosPE I(2)'
	w002 is 'CIRB'

document01 of w002 has the following associated with it:
	<hmu_metadata_region value="N. Black Sea" />
	<hmu_metadata_city value="Pantikapaion" />
	<hmu_metadata_date value="344-310a" />
	<hmu_metadata_publicationinfo value="IosPE II 1" />

document180 of w002 has the following:
	<hmu_metadata_region value="N. Black Sea" />
	<hmu_metadata_city value="Myrmekion" />
	<hmu_metadata_date value="c 400-350a" />
	<hmu_metadata_publicationinfo value="IosPE IV 294[cf CIRB p.479]" />

What if you wanted to search only documents from Pantikapaion?
What if you wanted to restrict your search to 375BCE?
What if you want to search *all* Greek authors and inscriptions older than 400BCE?

what needs to happen is that the works need to become authors and the documents works
then as works the metadata can be assigned to the relevant fields of the workdb

the results of the first passdb generation are the following:
	there are 24 inscription files that will turn into 24 authors
	463 works will be distributed among these 24 authors

	there are 213 papyrus files that will turn into 213 authors
	516 works will be distributed among these 213 authors

all of this can be safely remapped as dbs with the first two places of the four character author dbname being a hex representation of a number from 1-213.
then the next two places of the author dbname can represent the digits of the old work numbers (which never exceed 99 for any given original author)

things have to happen in several passes
first you need to build the new hybrid authors from authors+works
but you can't fill out 'floruit' yet: you need line 1 of the newwork db
but the new work dbs need to be exctracted from the old work db

"""

config = configparser.ConfigParser()
config.read('config.ini')

dbconnection = setconnection(config)
cursor = dbconnection.cursor()


def builddbremappers(oldprefix, newprefix, cursor):

	q = 'SELECT universalid FROM authors WHERE universalid LIKE %s ORDER BY universalid ASC'
	d = (oldprefix+'%',)
	cursor.execute(q,d)
	results = cursor.fetchall()

	olddbs = []
	for r in results:
		olddbs.append(r[0])

	aumapper = {}
	counter = -1
	for db in olddbs:
		counter += 1
		hx = hex(counter)
		hx = str(hx[2:])
		if len(hx) == 1:
			hx = '0'+hx
		aumapper[newprefix+hx] = db

	wkmapper = {}
	for key in aumapper.keys():
		q = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
		d = (aumapper[key]+'%',)
		cursor.execute(q, d)
		results = cursor.fetchall()

		counter = 0
		for r in results:
			counter += 1
			hx = hex(counter)
			hx = str(hx[2:])
			if len(hx) == 1:
				hx = '0' + hx
			wkmapper[r[0]] = [key+hx]

	return aumapper, wkmapper


def compilenewauthors(aumapper, wkmapper, cursor):
	"""
	build new author objects by merging the old author and work info

	:param aumapper:
	:param wkmapper:
	:param cursor:
	:return: newauthors
	"""

	newauthors = []

	for key in aumapper.keys():
		author = dbauthorandworkloader(aumapper[key], cursor)
		for w in author.listofworks:
			suffix = ' ' + w.title
			newuniversalid = wkmapper[w.universalid]
			newlanguage = author.language
			newidxname = re.sub(r'\s{1,}$', '', author.idxname + suffix)
			newakaname = re.sub(r'\s{1,}$', '', author.akaname + suffix)
			newshortname = re.sub(r'\s{1,}$', '', author.shortname + suffix)
			newcleanname = re.sub(r'\s{1,}$', '', author.cleanname + suffix)
			newgenres = author.genres
			newfloruit = author.floruit
			newlocation = author.location
			newauthor = dbAuthor(newuniversalid, newlanguage, newidxname, newakaname, newshortname, newcleanname, newgenres, newfloruit, newlocation)
			newauthors.append(newauthor)

	return newauthors


def compilenewworks(newauthors, wkmapper):
	"""
	a bulk operation that goes newauthor by newauthor so as to build a collection of works for it
	find all of the individual documents within an old work and turn each document into its own new work

	:param newauthors:
	:param wkmapper:
	:return:
	"""

	for a in newauthors:
		db = wkmapper[a.universalid]
		q = 'SELECT DISTINCT level_01_value FROM %s'
		d = (db,)
		cursor.execute(q, d)
		results = cursor.fetchall()

		for document in results:
			docname = document[0]
			if len(docname) == 1:
				docname = '00'+docname
			elif len(docname) == 2:
				docname = '0' + docname

			q = 'SELECT * FROM %s WHERE level_01_value LIKE %s ORDER BY index'
			d = (db,document[0])
			cursor.execute(q, d)
			results = cursor.fetchall()

			buidlnewworddb(docname, results)

	return


def buidlnewworddb(docname, results):
	"""

	send me all of the matching lines from one db and i will build a new workdb with only these lines

	:param docname:
	:param results:
	:return:
	"""

	pass
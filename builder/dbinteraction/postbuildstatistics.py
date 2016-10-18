# -*- coding: utf-8 -*-
import re

def insertfirstsandlasts(cursor, dbconnection):
	"""
	public.works needs to know
		firstline integer,
        lastline integer,
	:param cursor:
	:return:
	"""
	
	print('inserting work db metatata: first/last lines')
	query = 'SELECT universalid FROM works ORDER BY universalid ASC'
	cursor.execute(query)
	results = cursor.fetchall()
	
	for r in results:
		query = 'SELECT index FROM '+r[0]+' ORDER BY index ASC LIMIT 1'
		cursor.execute(query)
		firstline = cursor.fetchone()
		first = int(firstline[0])
		
		query = 'SELECT index FROM '+r[0]+' ORDER BY index DESC LIMIT 1'
		cursor.execute(query)
		lastline = cursor.fetchone()
		last = int(lastline[0])
		
		query = 'UPDATE works SET firstline=%s, lastline=%s WHERE universalid=%s'
		data = (first,last,r[0])
		cursor.execute(query, data)
		
		dbconnection.commit()
	
	return

def findwordcounts(cursor, dbconnection):
	"""
	if you don't already have an official wordcount, generate one
	:param cursor:
	:return:
	"""
	print('inserting work db metatata: wordcounts')
	query = 'SELECT universalid FROM works WHERE wordcount IS NULL ORDER BY universalid ASC'
	cursor.execute(query)
	results = cursor.fetchall()
	
	for r in results:
		query = 'SELECT COUNT (hyphenated_words) FROM '+r[0]+' WHERE hyphenated_words <> %s'
		data = ('',)
		cursor.execute(query, data)
		hcount = cursor.fetchone()
		
		query = 'SELECT stripped_line FROM '+r[0]+' ORDER BY index ASC'
		cursor.execute(query)
		lines = cursor.fetchall()
		wordcount = 0
		for line in lines:
			words = line[0].split(' ')
			words = [x for x in words if x]
			wordcount += len(words)
			
		totalwords = wordcount - hcount[0]
		
		query = 'UPDATE works SET wordcount=%s WHERE universalid=%s'
		data = (totalwords,r[0])
		cursor.execute(query, data)
		
		dbconnection.commit()
		
	return
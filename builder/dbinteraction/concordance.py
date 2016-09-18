# -*- coding: utf-8 -*-
import re
import string
from builder.parsers.betacode_to_unicode import stripaccents


def findwordsinaline(line):
	theline = re.sub(r'&nbsp;', '', line)
	theline = re.sub(r'(\<.*?\>)' ,r'*snip*\1*snip*' ,theline)
	segments = theline.split('*snip*')
	wordlist = []
	
	# "“απαγορευοντεϲ" can show up because the hyphen column is not clean...
	for seg in segments:
		try:
			if seg[0] == '<':
				pass
			else:
				words = seg.split(' ')
				try:
					words.remove('')
				except:
					# there was no ''
					pass
				for word in words:
					word = cleanwords(word)
					wordlist.append(word)
		
		except:
			# there is no seg[0]: seg = ''
			pass
	
	return wordlist

def cleanwords(word):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""
	punct = re.compile('[%s]' % re.escape(string.punctuation + '’‘·“”—†(«»⸐„'))
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	# a problem that we should not have but do...
	# word = re.sub(r'<hmu_blank_quarter_spaces', '', word)
	word = re.sub(punct, '', word)
	# best do punct before this next one...
	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass
	
	return word


def conctablemaker(concdbname, dbconnection, cursor):
	"""
	SQL prep only
	:param workdbname:
	:param cursor:
	:return:
	"""
	query = 'DROP TABLE IF EXISTS public.' + concdbname
	cursor.execute(query)

	query = 'CREATE TABLE public.' + concdbname
	query += '( '
	query += 'word character varying(128),'
	query += 'stripped_word character varying(128),'
	query += 'loci text'
	query += ' ) WITH ( OIDS=FALSE );'

	cursor.execute(query)

	query = 'CREATE INDEX ' + concdbname + '_word_idx '
	query += 'ON public.' + concdbname
	query += ' USING btree (word);'

	cursor.execute(query)

	query = 'GRANT SELECT ON TABLE ' + concdbname + ' TO hippa_rd;'
	cursor.execute(query)
	dbconnection.commit()

	return


def dbsubmitconcordance(concordance, workuniversalid, dbconnection, cursor):
	concdbname = workuniversalid+'_conc'
	conctablemaker(concdbname, dbconnection, cursor)
	
	terms = list(concordance)
	terms = polytonicsort(terms)
	
	for term in terms:
		if len(term) > 0:
			if concdbname[0] == 'g' and re.search(r'[a-zA-Z]', term[0]) is not None:
				pass
			else:
				strippedterm = stripaccents(term)
				query = 'INSERT INTO '+concdbname+' (word, stripped_word, loci) ' \
				        'VALUES (%s, %s, %s)'
				data = (term, strippedterm, concordance[term])
				cursor.execute(query, data)
	
	dbconnection.commit()
	return
	

def buildconcordances(authorid, dbconnection, cursor):
	
	# find all of the works
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s'
	data = (authorid+'%',)
	cursor.execute(query, data)
	works = cursor.fetchall()
	
	for work in works:
		concordance = {}
		# run through each line of each work
		query = 'SELECT index,marked_up_line,hyphenated_words FROM '+work[0]+' WHERE index > -999'
		cursor.execute(query)
		lines = cursor.fetchall()
		
		previous = ''
		for line in lines:
			# find all of the words in the line
			words = findwordsinaline(line[1])
			if line[2] != '':
				hyphenated = line[2].split(' ')
				try:
					words[-1] = cleanwords(hyphenated[0])
				except:
					words = [cleanwords(hyphenated[0])]

			if previous == 'hyphenated':
				words = words[1:]
				
			words = list(set(words))
	
			for word in words:
				word = word.lower()
				# which is faster: 'if word in concordance:... else...' or 'try... except...' ?
				# same speed, it seems
				try:
					concordance[word] += ' '+str(line[0])
				except:
					concordance[word] = str(line[0])
			
			if line[2] != '':
				previous = 'hyphenated'
			else:
				previous = ''
		
		dbsubmitconcordance(concordance, work[0], dbconnection, cursor)
	
	return


def polytonicsort(unsortedwords):
	# sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	# stripping diacriticals can help this, but then you get words that collide
	# gotta jump through some extra hoops
	
	stripped = []
	for word in unsortedwords:
		if len(word)>0:
			strippedword = stripaccents(word)
			# one modification to stripaccents(): σ for ϲ in order to get the right values
			strippedword = re.sub(r'ϲ',r'σ',strippedword)
			stripped.append(strippedword + '-snip-' + word)
	stripped.sort()
	sorted = []
	for word in stripped:
		cleaned = re.sub(r'(.*?)(-snip-)(.*?)', r'\3', word)
		sorted.append(cleaned)
	
	return sorted


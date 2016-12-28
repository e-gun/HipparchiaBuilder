# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
from multiprocessing import Value
from builder.parsers import regex_substitutions

class Author(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	"""

	def __init__(self, number,language, uidprefix, dataprefix):
		self.number = number
		self.language = language
		self.universalid = uidprefix+number
		self.shortname = ''
		self.cleanname = ''
		self.genre = ''
		self.recorded_date = ''
		self.converted_date = ''
		self.location = ''
		self.works = []
		# sadly we need this to decode what work number is stored where
		self.workdict = {}
		self.name = ''
		self.aka = ''
		self.dataprefix = dataprefix

	def addwork(self, work):
		self.works.append(work)
	
	def addauthtabname(self, name):
		whiteout = re.compile(r'^\s*(.*?)\s*$')
		focus = re.compile('^(.*?)(&1.*?&)')
		nick = re.compile(r'\x80(\w.*?)($)')
		if '$' in name:
			search = re.compile(r'(\$\d{0,2})(.*?)(&)')
			name = re.sub(search, regex_substitutions.doublecheckgreekwithinlatin, name)
			search = r'<hmu_greek_in_a_latin_text>.*?</hmu_greek_in_a_latin_text>'
			name = re.sub(search, regex_substitutions.parsegreekinsidelatin, name)
			name = re.sub(r'<(/|)hmu_greek_in_a_latin_text>', '', name)
		name = re.sub(r'2', '', name)
		name = regex_substitutions.latinadiacriticals(name)
		segments = re.search(focus, name)
		nn = re.search(nick, name)
		
		try:
			g = segments.group(1)
		except:
			g = ''
		
		try:
			gg = segments.group(2)
		except:
			gg = ''
		
		try:
			short = nn.group(1)
			# skip any additional nicknames: Cicero + Tully / Vergil + Virgil
			short = short.split('\x80')
			short = short[0]
		except:
			short = ''
		
		try:
			core = re.sub(r'\s$', '', gg)
		except:
			core = name
		
		if g != '':
			full = core + ', ' + g
		else:
			full = core
			
		full = re.sub(r'[&1]', '', full)
		
		remainder = re.sub(re.escape(g + gg), '', name)
		remainder = re.sub(r'[&1]', '', remainder)
		
		tail = re.sub(short, '', remainder)
		
		short = re.sub(whiteout,r'\1',short)
		tail = re.sub(whiteout,r'\1',tail)
		full = re.sub(whiteout,r'\1',full)
			
		if 'g' in self.universalid:
			if short != '' and len(tail) > 1:
				self.cleanname = short + ' - ' + full + ' (' + tail + ')'
				self.shortname = short
			elif short != '':
				self.cleanname = short + ' - ' + full
				self.shortname = short
			elif len(tail) > 1:
				self.cleanname = full + ' (' + tail + ')'
				self.shortname = full
			else:
				self.shortname = full
				self.cleanname = full
		else:
			if short != '':
				self.cleanname = short + ' - ' + full
				self.shortname = short
			elif len(tail) > 1:
				full = full + ' ' + tail
				self.cleanname = full
				self.shortname = self.cleanname
			else:
				self.cleanname = full
				self.shortname = full
		
		if 'in' in self.universalid:
			self.cleanname = full +' [inscriptions]'
			self.shortname = self.cleanname
		if 'dp' in self.universalid:
			self.cleanname = full + ' [papyri]'
			self.shortname = self.cleanname
			
		self.cleanname = re.sub(r'(^\s|\s$)','',self.cleanname)
		self.shortname = re.sub(r'(^\s|\s$)','',self.shortname)
		
		self.aka = self.shortname
		self.name = self.cleanname


class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	"""

	def __init__(self, universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location):
		self.universalid = universalid
		self.language = language
		self.idxname = idxname
		self.akaname = akaname
		self.shortname = shortname
		self.cleanname = cleanname
		self.genres = genres
		self.recorded_date = recorded_date
		self.converted_date = converted_date
		self.location = location
		self.authornumber = universalid[2:]
		self.listofworks = []
		self.name = akaname
		self.id = universalid

	def earlier(self, other):
		return float(self.converted_date) < other

	def later(self, other):
		return float(self.converted_date) > other

	def atorearlier(self, other):
		return float(self.converted_date) <= other

	def atorlater(self, other):
		return float(self.converted_date) >= other

	def floruitis(self, other):
		return float(self.converted_date) == other

	def floruitisnot(self, other):
		return float(self.converted_date) != other

	def addwork(self, work):
		self.listofworks.append(work)

	def listworkids(self):
		workids = []
		for w in self.listofworks:
			workids.append(w.universalid)

		return workids


class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be important to know exactly what kind of object you are handling
	"""

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02,
				 levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance,
				 recorded_date, converted_date, wordcount, firstline, lastline, authentic):
		self.universalid = universalid
		self.title = title
		self.language = language
		self.publication_info = publication_info
		self.levellabels_00 = levellabels_00
		self.levellabels_01 = levellabels_01
		self.levellabels_02 = levellabels_02
		self.levellabels_03 = levellabels_03
		self.levellabels_04 = levellabels_04
		self.levellabels_05 = levellabels_05
		self.workgenre = workgenre
		self.transmission = transmission
		self.worktype = worktype
		self.provenance = provenance
		self.recorded_date = recorded_date
		self.converted_date = converted_date
		self.wordcount = wordcount
		self.starts = firstline
		self.ends = lastline
		self.authentic = authentic
		self.name = title
		try:
			self.length = lastline - firstline
		except:
			self.length = -1
		self.worknumber = int(universalid[7:])
		self.structure = {}
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '':
				self.structure[idx] = label
		
		availablelevels = 1
		for level in [self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]:
			if level != '' and level is not None:
				availablelevels += 1
		self.availablelevels = availablelevels
		
	def citation(self):
		cit = []
		levels = [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]
		for l in range(0,self.availablelevels):
			cit.append(levels[l])
		cit.reverse()
		cit = ', '.join(cit)
		
		return cit
	
	
class dbWorkLine(object):
	"""
	an object that corresponds to a db line
	"""

	def __init__(self, wkuinversalid, index, level_05_value, level_04_value, level_03_value, level_02_value,
				 level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words,
				 annotations):
		self.wkuinversalid = wkuinversalid[:10]
		self.index = index
		self.l5 = level_05_value
		self.l4 = level_04_value
		self.l3 = level_03_value
		self.l2 = level_02_value
		self.l1 = level_01_value
		self.l0 = level_00_value
		# can remove the regex soon
		# self.accented = re.sub(r'\s$', '', marked_up_line)
		# self.polytonic = re.sub(r'\s$', '', accented_line)
		# self.stripped = re.sub(r'\s$', '', stripped_line)
		self.accented = marked_up_line
		self.polytonic = accented_line
		self.stripped = stripped_line
		self.annotations = annotations
		self.universalid = self.wkuinversalid + '_LN_' + str(index)
		self.hyphenated = hyphenated_words
		if len(self.hyphenated) > 1:
			self.hashyphenated = True
		else:
			self.hashyphenated = False

		if self.accented is None:
			self.accented = ''
			self.stripped = ''

	def locus(self):
		"""
		call me to get a formatted citation
		:param self:
		:return:
		"""
		loc = []
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				loc.append(lvl)
		loc.reverse()
		citation = '.'.join(loc)

		return citation

	def shortlocus(self):
		"""
		try to get a short citation that drops the lvl0 info
		useful for tagging level shifts without constantly seeling 'line 1'
		:return:
		"""
		loc = []
		for lvl in [self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				loc.append(lvl)
		loc.reverse()
		if loc == []:
			citation = self.locus()
		else:
			citation = '.'.join(loc)

		return citation

	def locustuple(self):
		"""
		call me to get a citation tuple in 0-to-5 order
		:return:
		"""
		cit = []
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				cit.append(lvl)
		citationtuple = tuple(cit)

		return citationtuple

	def samelevelas(self, other):
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci have to be from the same work
		:param self:
		:param other:
		:return:
		"""
		if self.wkuinversalid == other.wkuinversalid and self.l5 == other.l5 and self.l4 == other.l4 and self.l3 == other.l3 and self.l2 == other.l2 and self.l1 == other.l1:
			return True
		else:
			return False

	def equivalentlevelas(self, other):
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci do not have to be from the same work
		:param self:
		:param other:
		:return:
		"""
		if self.l5 == other.l5 and self.l4 == other.l4 and self.l3 == other.l3 and self.l2 == other.l2 and self.l1 == other.l1:
			return True
		else:
			return False

	def toplevel(self):
		top = 0
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				top += 1
			else:
				return top

		# should not need this, but...
		return top

	def unformattedline(self):
		"""
		remove markup from contents
		:return:
		"""

		markup = re.compile(r'(\<.*?\>)')
		nbsp = re.compile(r'&nbsp;')

		unformatted = re.sub(markup, r'', self.accented)
		unformatted = re.sub(nbsp, r'', unformatted)

		return unformatted

	def wordcount(self):
		"""
		return a wordcount
		"""

		line = self.stripped
		words = line.split(' ')

		return len(words)

	def wordlist(self, version):
		"""
		return a list of words in the line; will include the full version of a hyphenated last word
		:param version:
		:return:
		"""
		wordlist = []

		if version in ['polytonic', 'stripped']:
			line = getattr(self, version)
			wordlist = line.split(' ')
			wordlist = [w for w in wordlist if w]

		return wordlist

	def allbutlastword(self, version):
		"""
		return the line less its final word
		"""
		allbutlastword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			line = line.split(' ')
			allbutlast = line[:-1]
			allbutlastword = ' '.join(allbutlast)

		return allbutlastword

	def allbutfirstword(self, version):
		"""
		return the line less its first word
		"""
		allbutfirstword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(\<.*?\>)', r'', line)
			line = line.split(' ')
			allbutfirst = line[1:]
			allbutfirstword = ' '.join(allbutfirst)

		return allbutfirstword

	def allbutfirstandlastword(self, version):
		"""
		terun the line lest the first and last words (presumably both are hypenated)
		:param version:
		:return:
		"""
		allbutfirstandlastword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(\<.*?\>)', r'', line)
			line = line.split(' ')
			middle = line[1:-1]
			allbutfirstandlastword = ' '.join(middle)

		return allbutfirstandlastword


class Opus(object):
	"""
		attributes
			authornumber: tlg/phi author number [for debugging, really: an Opus should be inside an Author]
			txtFile: tlg/phi textfile name
			worknumber: work number within the txtFile
			title: work name within the txtFile
			txtFile: the name of the relevant CD-ROM file
			workstartblock: first of several 8k blocks containing our work (do we really need this if we are moving away from the CD files?)
			structure: a dict that gives the hierarchy; {0: 'line', 1: 'section', 2: 'Book'}
	"""

	def __init__(self, authornumber, language, worknumber, title, structure):
		self.authornumber = authornumber
		self.language = language
		self.worknumber = int(worknumber)
		if '$' in title:
			title = regex_substitutions.replacelatinbetacode(title)
			title = re.sub(r'<(/|)hmu_greek_in_a_latin_text>','',title)
			self.title = re.sub(r'(\$|\&|\d)', '', title)
		else:
			self.title = title
		self.structure = structure
		self.contentlist = []
		self.name = title

	def addcontents(self, toplevelobject):
		self.contentlist.append(toplevelobject)

	def __str__(self):
		return self.title


class MPCounter(object):
	def __init__(self):
		self.val = Value('i', 0)
	
	def increment(self, n=1):
		with self.val.get_lock():
			self.val.value += n
	
	@property
	def value(self):
		return self.val.value
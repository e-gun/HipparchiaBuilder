import re
from builder.parsers import idtfiles, betacode_to_unicode, regex_substitutions

class Author(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	"""

	def __init__(self, number,language):
		self.number = number
		self.language = language
		if language == 'G':
			self.universalid = 'gr'+number
		elif language == 'L':
			self.universalid = 'lt' + number
		self.shortname = ''
		self.cleanname = ''
		self.genre = ''
		self.floruit = ''
		self.location = ''
		self.works = []
		# sadly we need this to decode what work number is stored where
		self.workdict = {}
		self.name = ''
		self.aka = ''

	def addwork(self, work):
		self.works.append(work)
	
	def addauthtabname(self, name):
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
		full = re.sub(r'[&1\[]', '', full)
		
		remainder = re.sub(re.escape(g + gg), '', name)
		remainder = re.sub(r'[&1]', '', remainder)
		
		tail = re.sub(short, '', remainder)
		
		if 'g' in self.universalid:
			if short != '' and len(tail) > 1:
				self.cleanname = short + ' - ' + full + ' (' + tail + ')'
			elif short != '':
				self.cleanname = short + ' - ' + full
			elif len(tail) > 1:
				self.cleanname = full + ' (' + tail + ')'
				self.shortname = full
			else:
				self.shortname = full
				self.cleanname = full
		else:
			if short != '':
				self.cleanname = short + ' - ' + full
			elif len(tail) > 1:
				full = full + tail
				self.cleanname = re.sub(r'\s{2,}', r' ', full)
				self.shortname = self.cleanname
			else:
				self.cleanname = full
				self.shortname = full
		self.aka = self.shortname
		self.name = self.cleanname

class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	"""

	def __init__(self, universalid, language, idxname, akaname, shortname, cleanname, genres, birth, death, floruit, location):
		self.universalid = universalid
		self.language = language
		self.idxname = idxname
		self.akaname = akaname
		self.shortname = shortname
		self.cleanname = cleanname
		self.genres = genres
		self.birth = birth
		self.death = death
		self.floruit = floruit
		self.location = location
		self.authornumber = universalid[2:]
		self.listofworks = []
		self.name = akaname
		self.id = universalid

	def addwork(self, work):
		self.listofworks.append(work)


class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be importnat to know exactly what kind of object you are handling
	"""

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05):
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
		self.name = title
		self.worknumber = int(universalid[7:])
		self.structure = {}
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '':
				self.structure[idx] = label


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


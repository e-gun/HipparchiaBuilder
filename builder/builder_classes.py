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
		self.genres = ''
		self.floruit = ''
		self.location = ''
		self.works = []
		# sadly we need this to decode what work number is stored where
		self.workdict = {}
		self.name = ''

	def addwork(self, work):
		self.works.append(work)

	def addauthtabname(self, addauthtabname):
		self.addauthtabname = addauthtabname
		self.shortname = re.sub(r'(.*\d)(.*?)(\&(.{0,}))', r'\2', self.addauthtabname)
		if self.shortname[-1] == ' ':
			self.shortname = self.shortname[:-1]
		try:
			self.name = shortname
		except:
			self.name = addauthtabname
		self.cleanname = re.sub(r'\d','',addauthtabname)
		# hybrid greek-latin names
		if re.search(r'.*?\$(.*?)\&.*?',self.cleanname) != False:
			parts = self.cleanname.split(' ')
			self.cleanname = ''
			for part in parts:
				part += ' '
				if part[0]=='$':
					part = betacode_to_unicode.replacegreekbetacode(part)
				self.cleanname += part
		self.cleanname = regex_substitutions.latinadiacriticals(self.cleanname)
		self.cleanname = re.sub(r'[&$]','',self.cleanname)
		self.cleanname = re.sub(r'(.{0,})\x80.{0,}', r'\1', self.cleanname)
		if re.sub(r'.*\x80(.*?)', r'\1', self.addauthtabname) == self.addauthtabname:
			self.aka = self.cleanname
		else:
			self.aka = re.sub(r'.*\x80(.*?)', r'\1', self.addauthtabname)
		genredict = { 'Epic\.':'epic',
		              'Alchem\.': 'alchemy',
		              'Astrol\.': 'astrology',
		              'Astron\.': 'astronomy',
		              'Biogr\.': 'biography',
		              'Bucol\.': 'bucolic',
		              'Comic\.': 'comedy',
		              'Doxog\.': 'doxography',
		              'Doxogr\.': 'doxography',
		              'Eleg\.': 'elegy',
		              'Epig\.': 'epigram',
		              'Epist\.': 'epistles',
		              'Fab\.': 'fables',
		              'Gramm\.': 'grammar',
		              'Hist\.': 'history',
		              'Iamb\.': 'iamb',
		              'Lexicogr\.': 'lexicography',
		              'Lyr\.': 'lyric',
		              'Math\.': 'mathematics',
		              'Mech\.': 'mechanics',
		              'Med\.': 'medicine',
		              'Mus\.': 'music',
		              'Orat\.': 'oratory',
		              'Paradox\.': 'paradoxography',
		              'Phil\.': 'philosophy',
		              'Poeta': 'poetry',
		              'Rhet\.': 'rhetoric',
		              'Scr\. Eccl\.': 'religion',
		              'Scr\. Erot\.': 'novel',
		              'Soph\.': 'sophistic',
		              'Tact\.': 'tactics',
		              'Theol\.': 'theology',
		              'Trag\.': 'tragedy',
		             }
		self.genre = ''
		for key in genredict:
			if re.search(key,addauthtabname) is not None:
				# be careful on the other end: 'poetry philosophy' needs to be two list items and not one
				self.genre += genredict[key]+' '
		self.genre = self.genre[:-1]


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

	def xmldump(self):
		levlenum = 0
		xml = '<core_work_info>\n'
		xml += '\t<work_number value="' + str(self.worknumber) + '" />\n'
		xml += '\t<work_name value="' + self.title + '" />\n'
		xml +='\t<work_structure>\n'
		for key, val in w.getstructure().items():
			xml += '\t\t<level_'+str(key)+' value="'+val+'"/>\n'
		xml += '\t</work_structure>\n'
		xml += '</core_work_info>\n'
		return xml


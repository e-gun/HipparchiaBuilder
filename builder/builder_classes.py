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
		self.shortname = re.sub(r'(&.*?&).*?',r'\1',self.addauthtabname)
		self.shortname = regex_substitutions.replacelatinbetacode(self.shortname+' █')
		self.shortname = regex_substitutions.latinadiacriticals(self.shortname)
		self.shortname = self.shortname[:-1]
		if self.shortname[-1] == ' ':
			self.shortname = self.shortname[:-1]
		self.shortname = re.sub(r'<(/|)hmu_greek_in_a_latin_text>','', self.shortname)
		self.shortname = re.sub(r'[&$\d]','',self.shortname)
		
		self.shortname = re.sub(r'[\d]', '', self.shortname)
		self.shortname = re.sub(r'\x80(\w.*?)(\s|$)', r' (\1)\2', self.shortname)
		self.shortname = re.sub(r'\x80.*?\)',r')',self.shortname)
		
		if re.sub(r'.*\x80(\w.*?)(\s|$)',r'\1',self.addauthtabname) != self.addauthtabname:
			self.aka = re.sub(r'.*?\x80(\w.*?)(\\|\s|$)',r'\1 ',self.addauthtabname)
			if self.aka[-1] == ' ':
				self.aka = self.aka[:-1]
			self.aka = self.aka.split('\x80')
			self.aka = self.aka[0]
		else:
			self.aka = self.shortname
			
		try:
			self.name = self.shortname
		except:
			self.name = addauthtabname
		
		# should get rid of cleanname some day
		self.cleanname = self.shortname
		


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


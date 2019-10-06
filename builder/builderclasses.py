# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
from multiprocessing import Value
from string import punctuation
from typing import List

from builder.parsers.betacodefontshifts import dollarssubstitutes
from builder.parsers.latinsubstitutions import latindiacriticals
from builder.parsers.regexsubstitutions import tidyupterm


class Author(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read

	CREATE TABLE public.authors
	(
    universalid character(6) COLLATE pg_catalog."default",
    language character varying(10) COLLATE pg_catalog."default",
    idxname character varying(128) COLLATE pg_catalog."default",
    akaname character varying(128) COLLATE pg_catalog."default",
    shortname character varying(128) COLLATE pg_catalog."default",
    cleanname character varying(128) COLLATE pg_catalog."default",
    genres character varying(512) COLLATE pg_catalog."default",
    recorded_date character varying(64) COLLATE pg_catalog."default",
    converted_date character varying(8) COLLATE pg_catalog."default",
    location character varying(128) COLLATE pg_catalog."default"
	)

	"""

	def __init__(self, number,language, uidprefix, dataprefix):
		self.number = number
		self.language = language
		self.universalid = uidprefix+number
		self.shortname = ''
		self.cleanname = ''
		self.genre = ''
		self.recorded_date = ''
		self.converted_date = None
		self.location = ''
		self.works = list()
		# sadly we need this to decode what work number is stored where
		self.workdict = dict()
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
			# cf latinauthordollarshiftparser()
			dollars = name.split('$')
			name = [dollars[0]]
			whichdollar = re.compile(r'^(\d{0,})(.*?)(&|$)')
			appendix = [re.sub(whichdollar, lambda x: dollarssubstitutes(x.group(1), x.group(2), ''), d) for d in
			            dollars[1:]]
			name = ''.join(name + appendix)
			name = re.sub(r'<.*?>', '', name)
		name = re.sub(r'2', '', name)
		name = latindiacriticals(name)
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
		
		short = re.sub(whiteout, r'\1', short)
		tail = re.sub(whiteout, r'\1', tail)
		full = re.sub(whiteout, r'\1', full)
			
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
		self.listofworks = list()
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
		workids = list()
		for w in self.listofworks:
			workids.append(w.universalid)
		return workids


class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be important to know exactly what kind of object you are handling

	CREATE TABLE public.works
	(
    universalid character(10) COLLATE pg_catalog."default",
    title character varying(512) COLLATE pg_catalog."default",
    language character varying(10) COLLATE pg_catalog."default",
    publication_info text COLLATE pg_catalog."default",
    levellabels_00 character varying(64) COLLATE pg_catalog."default",
    levellabels_01 character varying(64) COLLATE pg_catalog."default",
    levellabels_02 character varying(64) COLLATE pg_catalog."default",
    levellabels_03 character varying(64) COLLATE pg_catalog."default",
    levellabels_04 character varying(64) COLLATE pg_catalog."default",
    levellabels_05 character varying(64) COLLATE pg_catalog."default",
    workgenre character varying(32) COLLATE pg_catalog."default",
    transmission character varying(32) COLLATE pg_catalog."default",
    worktype character varying(32) COLLATE pg_catalog."default",
    provenance character varying(64) COLLATE pg_catalog."default",
    recorded_date character varying(64) COLLATE pg_catalog."default",
    converted_date character varying(8) COLLATE pg_catalog."default",
    wordcount integer,
    firstline integer,
    lastline integer,
    authentic boolean
	)

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
		# self.worknumber = int(universalid[7:])
		# con't use int() any longer because ins and ddp numbers count via hex
		self.worknumber = universalid[7:]
		self.structure = dict()
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '' and label != None:
				self.structure[idx] = label

		availablelevels = 1
		for level in [self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04,
		              self.levellabels_05]:
			if level != '' and level is not None:
				availablelevels += 1
		self.availablelevels = availablelevels

	def citation(self):
		if self.universalid[0:2] not in ['in', 'dp', 'ch']:
			cit = []
			levels = [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03,
			          self.levellabels_04, self.levellabels_05]
			for l in range(0, self.availablelevels):
				cit.append(levels[l])
			cit.reverse()
			cit = ', '.join(cit)
		else:
			cit = '(face,) line'

		return cit

	def earlier(self, other):
		return float(self.converted_date) < other

	def later(self, other):
		return float(self.converted_date) > other

	def alllevels(self):
		levels = list()
		for l in [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]:
			levels.append(l)

		return levels


class dbWorkLine(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public.in0207
	(
    index integer NOT NULL DEFAULT nextval('in0207'::regclass),
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
	)

	"""
	grave = 'ὰὲὶὸὺὴὼῒῢᾲῂῲἃἓἳὃὓἣὣἂἒἲὂὒἢὢ'
	acute = 'άέίόύήώΐΰᾴῄῴἅἕἵὅὕἥὥἄἔἴὄὔἤὤ'
	gravetoacute = str.maketrans(grave, acute)
	minimumgreek = re.compile(
		'[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')
	# note the tricky combining marks like " ͡ " which can be hard to spot since they float over another special character
	elidedextrapunct = '\′‵‘·“”„—†⌈⌋⌊∣⎜͙ˈͻ✳※¶§⸨⸩｟｠⟫⟪❵❴⟧⟦→◦⊚𐄂𝕔☩(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚̄⁝͜‖͡⸓͝'
	extrapunct = elidedextrapunct + '’'
	greekpunct = re.compile('[{s}]'.format(s=re.escape(punctuation + elidedextrapunct)))
	latinpunct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

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
		self.accented = marked_up_line
		self.polytonic = accented_line
		self.stripped = stripped_line
		self.annotations = annotations
		self.universalid = '{w}_LN_{i}'.format(w=self.wkuinversalid, i=index)
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
		call me to get a formatted citation: "3.2.1"
		:param self:
		:return:
		"""
		loc = list()

		if self.wkuinversalid[0:2] not in ['in', 'dp', 'ch']:
			for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
				if str(lvl) != '-1':
					loc.append(lvl)
			loc.reverse()
			citation = '.'.join(loc)
		else:
			# papyrus and inscriptions are wonky: usually they have just a recto, but sometimes they have something else
			# only mark the 'something else' version
			if self.l1 != 'recto':
				citation = self.l1 + ' ' + self.l0
			else:
				citation = self.l0

		return citation

	def shortlocus(self):
		"""
		try to get a short citation that drops the lvl0 info: "3.2"
		useful for tagging level shifts without constantly seeling 'line 1'
		:return:
		"""
		loc = list()
		for lvl in [self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1' and (self.wkuinversalid[0:2] not in ['in', 'dp', 'ch'] and lvl != 'recto'):
				loc.append(lvl)
		loc.reverse()
		if not loc:
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

		markup = re.compile(r'(<.*?>)')
		nbsp = re.compile(r'&nbsp;')

		unformatted = re.sub(markup, r'', self.accented)
		unformatted = re.sub(nbsp, r'', unformatted)

		return unformatted

	def showlinehtml(self):
		"""

		make HTML of marked up line visible

		:return:
		"""

		markup = re.compile(r'(\<)(.*?)(\>)')
		left = '<smallcode>&lt;'
		right = '&gt;</smallcode>'

		visiblehtml = re.sub(markup, left + r'\2' + right, self.accented)

		return visiblehtml

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
		wordlist = list()

		if version in ['polytonic', 'stripped']:
			line = getattr(self, version)
			# Non-breaking space needs to go
			line = re.sub(r'\xa0', ' ', line)
			wordlist = line.split(' ')
			wordlist = [w for w in wordlist if w]

		return wordlist

	def indexablewordlist(self) -> List[str]:
		# don't use set() - that will yield undercounts
		polytonicwords = self.wordlist('polytonic')
		polytonicgreekwords = [tidyupterm(w, dbWorkLine.greekpunct).lower() for w in polytonicwords if re.search(dbWorkLine.minimumgreek, w)]
		polytoniclatinwords = [tidyupterm(w, dbWorkLine.latinpunct).lower() for w in polytonicwords if not re.search(dbWorkLine.minimumgreek, w)]
		polytonicwords = polytonicgreekwords + polytoniclatinwords
		# need to figure out how to grab τ’ and δ’ and the rest
		# but you can't say that 'me' is elided in a line like 'inquam, ‘teque laudo. sed quando?’ ‘nihil ad me’ inquit ‘de'
		unformattedwords = set(self.wordlist('marked_up_line'))
		listofwords = [w for w in polytonicwords if w+'’' not in unformattedwords or not re.search(dbWorkLine.minimumgreek, w)]
		elisions = [w+"'" for w in polytonicwords if w+'’' in unformattedwords and re.search(dbWorkLine.minimumgreek, w)]
		listofwords.extend(elisions)
		listofwords = [w.translate(dbWorkLine.gravetoacute) for w in listofwords]
		listofwords = [re.sub('v', 'u', w) for w in listofwords]
		return listofwords

	def wordlistasstring(self):
		s = self.indexablewordlist()
		s = '\t'.join(s)
		return s

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
				line = re.sub(r'(<.*?>)', r'', line)
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
				line = re.sub(r'(<.*?>)', r'', line)
			line = line.split(' ')
			middle = line[1:-1]
			allbutfirstandlastword = ' '.join(middle)

		return allbutfirstandlastword


class dbWordCountObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public."wordcounts_ω"
	(
    entry_name character varying(64) COLLATE pg_catalog."default",
    total_count integer,
    gr_count integer,
    lt_count integer,
    dp_count integer,
    in_count integer,
    ch_count integer
	)

	"""

	def __init__(self, entryname, totalcount, greekcount, latincount, docpapcount, inscriptioncount, christiancount):
		self.entryname = entryname
		self.t = totalcount
		self.g = greekcount
		self.l = latincount
		self.d = docpapcount
		self.i = inscriptioncount
		self.c = christiancount

	def getelement(self, element):
		elements = {
			'total': self.t, 'gr': self.g, 'lt': self.l, 'dp': self.d, 'in': self.i, 'ch': self.c
			}
		try:
			return elements[element]
		except:
			return 0


class dbLemmaObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public.greek_lemmata
	(
	dictionary_entry character varying(64) COLLATE pg_catalog."default",
	xref_number integer,
	derivative_forms text COLLATE pg_catalog."default"
	)

	u/v problem: 'derivative_forms' in latin_lemmata contains a hybrid of u and v; contrast the following

	"evulgo";27913617;"	evulgaret (imperf subj act 3rd sg)	evulgari (pres inf pass)	evulgato (fut imperat act 3rd sg) (fut imperat act 2nd sg) (perf part pass neut abl sg) (perf part pass masc abl sg) (perf part pass neut dat sg) (perf part pass masc dat sg)	evulgatus (perf part (...)"
	"divulgo";24959067;"	diuulgarent (imperf subj act 3rd pl)	diuulgarentur (imperf subj pass 3rd pl)	diuulgaret (imperf subj act 3rd sg)	diuulgata (perf part pass neut nom/voc/acc pl) (perf part pass fem abl sg) (perf part pass fem nom/voc sg)	diuulgati (perf part pass masc nom/ (...)"

	and 'evulgaret' will never be seen by the counter since the word seen in the db is 'euulgaret'

	"""

	def __init__(self, dictionaryentry, xref, derivativeforms):
		self.dictionaryentry = dictionaryentry
		self.xref = xref
		# self.formandidentificationlist = [f for f in derivativeforms.split('\t') if f]
		self.formandidentificationlist = derivativeforms
		self.formlist = [f.split(' ')[0] for f in self.formandidentificationlist]
		self.formlist = [re.sub(r'\'', '', f) for f in self.formlist]
		self.formlist = [re.sub(r'v', 'u', f) for f in self.formlist]

	def getformdict(self):
		fd = dict()
		for f in self.formandidentificationlist:
			key = f.split(' ')[0]
			body = f[len(key)+1:]
			fd[key] = body
		return fd


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
		self.title = title
		self.structure = structure
		self.contentlist = list()
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

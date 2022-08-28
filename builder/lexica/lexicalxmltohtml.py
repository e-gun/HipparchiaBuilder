# -*- coding: utf-8 -*-
"""
    HipparchiaBuilder: compile a database of Greek and Latin texts
    Copyright: E Gunderson 2016-22
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

# all of this stripped brutally from HipparchiaServer and shoved in here in a quick and dirty fashion...
# a number of things toggled off: but good luck finding them all

import re
from typing import List, Dict

from builder.dbinteraction.connection import setconnection

class dbDictionaryEntry(object):
    """
    an object that corresponds to a db line

    CREATE TABLE greek_dictionary (
        entry_name character varying(64),
        metrical_entry character varying(64),
        unaccented_entry character varying(64),
        id_number integer,
        pos character varying(32),
        translations text,
        entry_body text
    );

    CREATE TABLE latin_dictionary (
        entry_name character varying(64),
        metrical_entry character varying(64),
        id_number integer,
        entry_key character varying(64),
        pos character varying(32),
        translations text,
        entry_body text
    );

    Latin only: entry_key
    Greek only: unaccented_entry

    """

    def __init__(self, entry_name, metrical_entry, id_number, pos, translations, entry_body):
        self.entry = entry_name
        self.metricalentry = metrical_entry
        self.id = id_number
        self.translations = translations.split(' ‖ ')
        self.pos = pos.split(' ‖ ')
        self.body = self._spacebetween(self._xmltohtmlquickconversions(entry_body))
        self._deabbreviateauthornames()
        self.xrefspresent = False
        self.xmlhasbeenconverted = False
        self.havesensehierarchy = False
        self.haveclickablelookups = False
        self.nextentryid = -1
        self.preventryid = -1
        self.nextentry = '(none)'
        self.preventry = '(none)'
        self.authorlist = list()
        self.quotelist = list()
        self.senselist = list()
        self.flaggedsenselist = list()
        self.phraselist = list()
        self.flagauthor = None

        if re.search(r'[a-z]', self.entry):
            self.usedictionary = 'latin'
            self.translationlabel = 'hi'
        else:
            self.usedictionary = 'greek'
            self.translationlabel = 'tr'

    @staticmethod
    def isgreek():
        raise NotImplementedError

    @staticmethod
    def islatin():
        raise NotImplementedError

    def runbodyxrefsuite(self):
        # add dictionary clicks to "cf.", etc. in the entry body
        raise NotImplementedError

    def isagloss(self):
        fingerprint = re.compile(r'<author>Gloss\.</author>')
        if re.search(fingerprint, self.body):
            return True
        else:
            return False

    def _deabbreviateauthornames(self):
        afinder = re.compile(r'<author>(.*?)</author>')
        if self.isgreek():
            d = 'greek'
        elif self.islatin():
            d = 'latin'
        self.body = re.sub(afinder, lambda x: self._deabbreviateauthornamewrapper(x.group(1), d), self.body)

    @staticmethod
    def _deabbreviateauthornamewrapper(foundauthor: str, dictionary: str) -> str:
        author = deabbreviateauthors(foundauthor, dictionary)
        wrapper = '<author>{au}</author>'.format(au=author)
        return wrapper

    def generateauthorsummary(self) -> List:
        """

        returns a collection of lists: all authors to be found in an entry

        entryxref allows you to trim 'quotes' that are really just morphology examples

        for example, ἔρχομαι will drop 12 items via this check

        :param fullentry:
        :param lang:
        :param translationlabel:
        :param lemmaobject:
        :return:
        """

        afinder = re.compile(r'<span class="dictauthor">(.*?)</span>')
        authorlist = re.findall(afinder, self.body)
        authorlist = list(set(authorlist))
        notin = ['id.', 'ib.', 'Id.']
        authorlist[:] = [value for value in authorlist if value not in notin]
        authorlist.sort()
        authorlist = [deabbreviateauthors(au, self.usedictionary) for au in authorlist]

        # session['authorssummary']
        if True:
            aa = len(authorlist)
            if aa != 1:
                authorlist = ['{n} authors'.format(n=aa)]
            else:
                authorlist = ['1 author']

        return authorlist

    def generateflaggedsummary(self) -> List:
        listofsenses = self.flaggedsenselist
        listofsenses = [s[0].upper() + s[1:] for s in listofsenses if len(s) > 1]
        listofsenses.sort()
        if True:
            ss = len(listofsenses)
            if ss != 1:
                listofsenses = ['{n} senses'.format(n=ss)]
            else:
                listofsenses = ['1 sense']

        return listofsenses

    def generatesensessummary(self) -> List:
        listofsenses = self.translations
        listofsenses = [s[0].upper() + s[1:] for s in listofsenses if len(s) > 1]
        listofsenses = [s.strip() for s in listofsenses]
        listofsenses = list(set(listofsenses))
        listofsenses.sort()

        # if session['sensesummary']
        if True:
            ss = len(listofsenses)
            if ss != 1:
                listofsenses = ['{n} senses'.format(n=ss)]
            else:
                listofsenses = ['1 sense']

        return listofsenses

    def generatequotesummary(self, lemmaobject=None) -> List:
        qfinder = re.compile(r'<span class="dictquote dictlang_\w+">(.*?)</span>')
        quotelist = re.findall(qfinder, self.body)

        # many of the 'quotes' are really just forms of the word
        # trim these
        if lemmaobject:
            morphologylist = lemmaobject.formlist
        else:
            morphologylist = list()

        quotelist = [x for x in quotelist if x not in morphologylist]
        quotelist = polytonicsort(quotelist)

        # session['quotesummary']
        if True:
            qq = len(quotelist)
            if qq != 1:
                quotelist = ['{n} quotes'.format(n=qq)]
            else:
                quotelist = ['1 quote']

        return quotelist

    def grabheadmaterial(self) -> str:
        """
        find the information at the top of a dictionary entry: used to get the basic info about the word
        :param fullentry:
        :return:
        """

        # after formatting a newline marks the first paragraph of the body
        h = re.search(r'\n', self.body)
        try:
            return self.body[:h.end()]
        except AttributeError:
            return str()

    def grabnonheadmaterial(self) -> str:
        """
        find the information at the top of a dictionary entry: used to get the basic info about the word
        :param fullentry:
        :return:
        """

        # after formatting a newline marks the first paragraph of the body
        h = re.search(r'\n', self.body)
        if not h:
            microentry = '<p></p>\n{b}'.format(b=self.body)
            return microentry

        try:
            return self.body[h.end():]
        except AttributeError:
            return str()

    def insertclickablelookups(self):
        """

        in:
            <bibl n="Perseus:abo:tlg,0019,003:1214" default="NO" valid="yes">

        out:
            <bibl id="perseus/gr0019/003/1214" default="NO" valid="yes">

        :return:
        """

        # first retag the items that should not click-to-browse

        biblios = re.compile(r'(<bibl.*?)(.*?)(</bibl>)')
        bibs = re.findall(biblios, self.body)
        bdict = dict()

        for bib in bibs:
            if 'Perseus:abo' not in bib[1]:
                # OR: if 'Perseus:abo' not in bib[1] and 'urn:cts:latinLit:phi' not in bib[1]:
                head = '<unclickablebibl'
                tail = '</unclickablebibl>'
            else:
                head = bib[0]
                tail = bib[2]
            bdict[str().join(bib)] = head + bib[1] + tail

        # print('here',bdict)
        htmlentry = self.body
        for key in bdict.keys():
            # print('insertclickablelookups(): key =', key)
            # will choke on the following:
            #	<bibl n="Perseus:abo:tlg,0085,011:46a**:16" default="NO" valid="yes"><author>Aeschylus</author> <bibtitle>Dict.</bibtitle> fr. 46a**.16</bibl>
            try:
                htmlentry = re.sub(key, bdict[key], htmlentry)
            except re.error:
                pass

        # now do the work of finding the lookups
        # latin old style: <bibl n="Perseus:abo:phi,0550,001:3:765" default="NO" valid="yes">
        # latin new styleA: <bibl n="urn:cts:latinLit:phi0550.phi001:3:765">
        # latin new styleB: <bibl n="urn:cts:latinLit:phi1276.phi001.perseus-lat1:1:90"><author>Juv.</author> 1, 90</bibl>
        # and there are other oddities to the new style, including arrant author ids
        # accordingly not building with that data at the moment
        tlgfinder = re.compile(r'n="Perseus:abo:tlg,(\d\d\d\d),(\d\d\d):(.*?)"')
        phifinder = re.compile(r'n="Perseus:abo:phi,(\d\d\d\d),(\d\d\d):(.*?)"')
        # diofindera = re.compile(r'n="urn:cts:latinLit:phi(\d\d\d\d)\.phi(\d\d\d):(.*?)"')
        # diofinderb = re.compile(r'n="urn:cts:latinLit:phi(\d\d\d\d)\.phi(\d\d\d)\.perseus-lat\d:(.*?)"')

        clickableentry = re.sub(tlgfinder, r'id="perseus/gr\1/\2/\3"', htmlentry)
        clickableentry = re.sub(phifinder, r'id="perseus/lt\1/\2/\3"', clickableentry)
        # clickableentry = re.sub(diofindera, r'id="perseus/lt\1/\2/\3"', clickableentry)
        # clickableentry = re.sub(diofinderb, r'id="perseus/lt\1/\2/\3"', clickableentry)

        # self.flagauthor and session['authorflagging']
        if False:
            myid = r'id="perseus/{a}'.format(a=self.flagauthor)
            clickableentry = re.sub(myid, r'class="flagged" ' + myid, clickableentry)
        self.body = clickableentry
        self.haveclickablelookups = True
        return

    def constructsensehierarchy(self):
        """
        look for all of the senses of a work in its dictionary entry
        return them as a list of definitions with HTML <p> attributes that set them in their proper hierarchy:
            A ... A1 ... A1b ...
        """

        sensefinder = re.compile(r'<sense.*?/sense>')
        levelfinder = re.compile(r'<sense\s.*?level="(.*?)".*?>')
        numfinder = re.compile(r'<sense.*?\sn="(.*?)".*?>')

        self.body = re.sub(sensefinder, lambda x: self._sensewrapper(x.group(0), levelfinder, numfinder), self.body)
        return

    @staticmethod
    def _sensewrapper(foundsense, levelfinder, numfinder):
        """
        take a "<sense></sense>" and wrap it in a "<p><span></span><sense></sense></p>" blanket

        pass levelfinder, numfinder to avoid re.compile inside a loop

        :param self:
        :return:
        """

        template = """
        <p class="level{pl}">
            <span class="levellabel{lv}">{nm}</span>
            {sn}
        </p>"""

        lvl = re.search(levelfinder, foundsense)
        num = re.search(numfinder, foundsense)

        if not lvl or not num:
            return foundsense

        paragraphlevel = lvl.group(1)

        rewritten = template.format(pl=paragraphlevel, lv=lvl.group(1), nm=num.group(1), sn=foundsense)

        # print('wrappedsense\n', rewritten)

        return rewritten

    def xmltohtmlconversions(self):
        """

        a heavy rewrite of the xml into html

        latintagtypes = {'itype', 'cb', 'sense', 'etym', 'trans', 'tr', 'quote', 'number', 'pos', 'usg', 'bibl', 'hi', 'gen', 'author', 'cit', 'orth', 'pb'}
        greektagtypes = {'itype', 'ref', 'tr', 'quote', 'pos', 'foreign', 'xr', 'gramgrp', 'lbl', 'sense', 'etym', 'gram', 'orth', 'date', 'hi', 'abbr', 'pb', 'biblscope', 'placename', 'bibl', 'title', 'author', 'cit'}

        latinattrtypes = {'extent', 'rend', 'opt', 'lang', 'level', 'id', 'valid', 'type', 'n', 'default'}
        greekattrtypes = {'extent', 'targorder', 'rend', 'opt', 'lang', 'level', 'id', 'type', 'valid', 'n', 'default'}

        built and then abandoned bs4 versions of the various requisite functions
        BUT then learned that bs4 profiles as a *very* slow collection of code:
            'search' and '_find_all' are desperately inefficient
            they make a crazy number of calls and you end up spending 11s on a single large entry

            ncalls  tottime  percall  cumtime  percall filename:lineno(function)
          4961664    0.749    0.000    1.045    0.000 {built-in method builtins.isinstance}
           308972    0.697    0.000    1.375    0.000 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:1792(_matches)
           679678    0.677    0.000    3.214    0.000 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:1766(search)
             6665    0.430    0.000    0.432    0.000 {method 'sub' of 're.Pattern' objects}
           296982    0.426    0.000    2.179    0.000 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:1725(search_tag)
              244    0.352    0.001    3.983    0.016 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:571(_find_all)

        :param string:
        :return:
        """

        tagfinder = re.compile(r'<(.*?)>')
        # notes that dropping 'n' will ruin your ability to generate the sensehierarchy
        dropset = {'default', 'valid', 'extent', 'n', 'opt'}

        propertyfinder = re.compile(r'(\w+)=".*?"')
        pruned = re.sub(tagfinder, lambda x: self._droptagsfromxml(x.group(1), dropset, propertyfinder), self.body)

        preservetags = {'bibl', 'span', 'p', 'dictionaryentry', 'biblscope', 'sense', 'unclickablebibl'}
        pruned = re.sub(tagfinder, lambda x: self._converttagstoclasses(x.group(1), preservetags), pruned)

        closefinder = re.compile(r'</(.*?)>')
        self.body = re.sub(closefinder, lambda x: self._xmlclosetospanclose(x.group(1), preservetags), pruned)

        self.xmlhasbeenconverted = True
        return

    @staticmethod
    def _xmlclosetospanclose(xmlstring: str, leaveuntouched: set) -> str:
        if xmlstring in leaveuntouched:
            newxmlstring = '</{x}>'.format(x=xmlstring)
        else:
            newxmlstring = '</span>'
        return newxmlstring

    @staticmethod
    def _droptagsfromxml(xmlstring: str, dropset: set, propertyfinder) -> str:
        """

        if
            dropset = {opt}
        &
            xmlstring = 'orth extent="full" lang="greek" opt="n"'

        return is
            'orth extent="full" lang="greek"'

        :param xmlstring:
        :param dropset:
        :return:
        """

        components = xmlstring.split(' ')
        combined = [components[0]]
        preserved = [c for c in components[1:] if re.search(propertyfinder, c) and re.search(propertyfinder, c).group(1) not in dropset]
        combined.extend(preserved)
        newxml = '<{x}>'.format(x=' '.join(combined))
        return newxml

    @staticmethod
    def _converttagstoclasses(xmlstring: str, leaveuntouched: set) -> str:
        """
        in:
            <orth extent="full" lang="greek" opt="n">

        out:
            <span class="dictorth dictextent_full dictlang_greek dictopt_n">

        skip all closings: '</orth>'

        be careful about collapsing "id"

        :param xmlstring:
        :return:
        """

        components = xmlstring.split(' ')
        if components[0] in leaveuntouched or components[0][0] == '/':
            newxml = '<{x}>'.format(x=xmlstring)
            # print('passing on', newxml)
            return newxml
        else:
            finder = re.compile(r'(\w+)="(.*?)"')
            combined = ['dict' + components[0]]
            collapsedtags = [re.sub(finder, r'dict\1_\2', t) for t in components[1:]]
            combined.extend(collapsedtags)
        newxml = '<span class="{x}">'.format(x=' '.join(combined))
        return newxml

    @staticmethod
    def _entrywordcleaner(foundword, substitutionstring):
        # example substitute: r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>'
        stripped = stripaccents(foundword)
        newstring = substitutionstring.format(clean=stripped, dirty=foundword)
        # print('entrywordcleaner()', foundword, stripped)
        return newstring

    @staticmethod
    def _spacebetween(string: str) -> str:
        """

        some tages should have a space between them

        _xmltohtmlconversions should be run first unless you want to change the fingerprints

        :param string:
        :return:
        """

        fingerprints = [r'(</author>)(<bibtitle>)',
                        r'(</author>)(<biblScope>)',
                        r'(</bibtitle>)(<biblScope>)',
                        r'(<bibl n=".*?" default="NO">)(<bibtitle>)']
        substitute = r'\1&nbsp;\2'

        for f in fingerprints:
            string = re.sub(f, substitute, string)

        return string

    @staticmethod
    def _xmltohtmlquickconversions(string: str) -> str:
        """

        some xml items should be rewritten, especially if they collide with html

        :param string:
        :return:
        """
        swaps = {'title': 'bibtitle'}

        for s in swaps.keys():
            input = r'<{old}>(.*?)</{old}>'.format(old=s)
            output = r'<{new}>\1</{new}>'.format(new=swaps[s])
            string = re.sub(input, output, string)

        return string


class dbGreekWord(dbDictionaryEntry):
    """

    an object that corresponds to a db line

    differs from Latin in self.language and unaccented_entry

    """

    def __init__(self, entry_name, metrical_entry, id_number, pos, translations, entry_body, unaccented_entry):
        self.language = 'Greek'
        self.unaccented_entry = unaccented_entry
        super().__init__(entry_name, metrical_entry, id_number, pos, translations, entry_body)
        self.entry_key = None
        self.usedictionary = "greek"

    @staticmethod
    def isgreek():
        return True

    @staticmethod
    def islatin():
        return False

    def runbodyxrefsuite(self):
        # modify self.body to add clicks to "cf" words, etc
        if not self.xrefspresent:
            self._greekgreaterthanlessthan()
            self._greekdictionaryentrywrapper('ref')
            self._greekdictionaryentrywrapper('etym')
            self._greeksvfinder()
            self._greekequivalentformfinder()
            self._cffinder()
            self.xrefspresent = True

    def _greekgreaterthanlessthan(self):
        # but this is really a builder problem... [present in v.1.0 and below]
        self.body = re.sub(r'&λτ;', r'&lt;', self.body)
        self.body = re.sub(r'&γτ;', r'&gt;', self.body)

    def _greekirregularvowelquantities(self):
        # also a builder problem: δαμευέϲϲθο_ vs δαμευέϲϲθο̄
        # same story with ε for η in dialects/inscriptions
        # but note that it would take a while to get all of the accent possibilities in there
        pass

    def _greekdictionaryentrywrapper(self, tag):
        """
        sometimes you have "<tag>WORD</tag>" and sometimes you have "<tag>WORD.</tag>"

        note the potential false-positive finds with things like:

            '<etym lang="greek" opt="n">ἀνα-</etym>'

        The tag will generate a hit but the '-' will disqualify it.

        Many tags are a mess in the XML. 'foreign' is used in all sorts of ways, etc.

        bs4 screws things up if you try to use it because it can swap item order:
            in text:    '<ref targOrder="U" lang="greek">γαιών</ref>'
            bs4 return: '<ref lang="greek" targorder="U">γαιών</ref>'

        :return:
        """
        # don't need to strip the accents with a greek word; do need to strip longs and shorts in a latin word
        markupfinder = re.compile(r'(<{t}.*?>)(\w+)(\.?<.*?{t}>)'.format(t=tag))
        self.body = re.sub(markupfinder, r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3', self.body)

    def _greeksvfinder(self):
        fingerprint = r'(<abbr>v\.</abbr> sub <foreign lang="greek">)(\w+)(</foreign>)'
        replacement = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
        self.body = re.sub(fingerprint, replacement, self.body)

    def _greekequivalentformfinder(self):
        fingerprints = [r'(used for <foreign lang="greek">)(\w+)(</foreign>)',
                        r'(Lat. <tr opt="n">)(\w+)(</tr>)']
        replacement = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
        for f in fingerprints:
            self.body = re.sub(f, replacement, self.body)

    def _cffinder(self):
        # such as: <foreign lang="greek">εὐθύϲ</foreign> (q. v.).
        fingerprints = [r'(cf. <foreign lang="greek">)(\w+)(</foreign>)',
                        r'(<foreign lang="greek">)(\w+)(</foreign> \(q\. v\.\))',
                        r'(<lbl opt="n">=</lbl> <ref targOrder="U" lang="greek">)(\w+)(,)',
                        r'(<gram type="dim" opt="n">Dim. of</gram></gramGrp> <foreign lang="greek">)(\w+)(,{0,1}</foreign>)']
        replacement = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
        for f in fingerprints:
            self.body = re.sub(f, replacement, self.body)


class dbLatinWord(dbDictionaryEntry):
    """

    an object that corresponds to a db line

    differs from Greek in self.language and unaccented_entry

    """

    def __init__(self, entry_name, metrical_entry, id_number, pos, translations, entry_body, entry_key):
        self.language = 'Latin'
        self.unaccented_entry = None
        super().__init__(entry_name, metrical_entry, id_number, pos, translations, entry_body)
        self.entry_key = entry_key
        self.usedictionary = "latin"

    @staticmethod
    def isgreek():
        return False

    @staticmethod
    def islatin():
        return True

    def runbodyxrefsuite(self):
        # modify self.body to add clicks to "cf" words, etc
        if not self.xrefspresent:
            self._latinxreffinder()
            self._latinsynonymfinder()
            self.xrefspresent = True

    def _latinxreffinder(self):
        """

        make "balneum" clickable if you are told to "v. balneum"

        sample entries:

            <orth extent="full" lang="la" opt="n">bălĭnĕum</orth>, v. balneum <sense id="n4869.0" n="I" level="1" opt="n"><hi rend="ital">init.</hi></sense>

            <orth extent="full" lang="la" opt="n">balneae</orth>, v. balneum.

        note that the following 's.v.' is not quite the same beast...

            <lbl opt="n">s.v.</lbl> <ref targOrder="U" lang="greek">ἐπευνακταί</ref>

        then we have the following where you need to clean the word before searching:
            <orth extent="full" lang="la" opt="n">fĕrē</orth>, q. v.

        :return:
        """

        sv = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
        fingerprints = [r'(v\. )(\w+)( <sense)',
                    r'(v\. )(\w+)(\.)$',
                    r'(v\. )(\w+)(, [A-Z])',
                    r'(\(cf\. )(\w+)(\))',
                    r'(; cf\. )(\w+)(\))',
                    r'(; cf\.: )(\w+)(\))',
                    r'(\(sc. )(\w+)([,)])',
                    r'(<etym opt="\w">\d\. )(\w+)(, q\. v\.)',
                    r'(from )(\w+)(</etym>)',
                    r'(<etym opt=".">)(\w+)(</etym>)',
                    r'(<etym opt=".">\d\. )(\w+)(</etym>)',
                    r'(<etym opt=".">)(\w+)([;,])',
                    r'(= )(\w+)([., ])',
                    r'(cf\. Gr\. )(\w+)(,)',
                    r'( i\. q\. )(\w+)([),])',
                    r'(pure Lat\.)(\w+)([),])',
                    r'(\(for )(\w+)(, q\. v\.\))'
                    ]
        # xreffinder.append(re.compile(r'<lbl opt="n">(s\.v\.)</lbl> <ref targOrder="U" lang="greek">(\w+)</ref>()'))

        xreffinder = [re.compile(f) for f in fingerprints]
        for x in xreffinder:
            self.body = re.sub(x, sv, self.body)

        findandeaccentuate = re.compile(r'<orth extent="full" lang="\w+" opt="\w">(\w+)</orth>, q. v.')
        qv = r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>, q. v.'

        self.body = re.sub(findandeaccentuate, lambda x: self._entrywordcleaner(x.group(1), qv), self.body)

    def _latinsynonymfinder(self):
        fingerprints = [r'(\(syn\.:{0,} )(.*?)([);])']
        # the next is dangerous because cf. might be a word or a passage: "dux" or "Pliny, Pan 12,1"
        # r'(\(cf\.:{0,} )(.*?)([);])']
        for f in fingerprints:
            self.body = re.sub(f, lambda x: self._entrylistsplitter(x), self.body)

    @staticmethod
    def _entrylistsplitter(matchgroup):
        entrytemplate = r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>'
        head = matchgroup.group(1)
        tail = matchgroup.group(3)

        synonymns = matchgroup.group(2)
        synonymns = synonymns.split(', ')

        substitutes = [entrytemplate.format(clean=stripaccents(s), dirty=s) for s in synonymns]
        substitutes = ', '.join(substitutes)

        newstring = head + substitutes + tail

        return newstring


class lexicalOutputObject(object):
    """

    handle the formatting of a generic dictionary entry

    """

    def __init__(self, thiswordobject, lang):
        self.thiswordobject = thiswordobject
        self.id = thiswordobject.id
        # self.usedictionary = setdictionarylanguage(thiswordobject.entry)
        self.thisheadword = thiswordobject.entry
        # self.headwordprevalence = getobservedwordprevalencedata(self.thisheadword)
        self.entryhead = self.thiswordobject.grabheadmaterial()
        self.entrysprincipleparts = self._buildprincipleparts()
        self.entrydistributions = self._builddistributiondict()
        self.fullenty = self._buildfullentry()
        # next needs previous to fullentry: regex search needs entry body rewrite
        self.authorentrysummary = self._buildauthorentrysummary()
        self.phrasesummary = self._buildphrasesummary()
        self.entrysummary = self._buildentrysummary()
        self.usedictionary = lang

    def _buildentrydistributionss(self) -> str:
        distributions = str()
        return distributions

    def _buildprincipleparts(self) -> str:
        pppts = str()
        return pppts

    def _buildentrysummary(self) -> str:
        blankcursor = None
        entryword = self.thiswordobject
        if not entryword.isagloss():
            # lemmaobject = grablemmataobjectfor(self.usedictionary + '_lemmata', word=entryword.entry, dbcursor=blankcursor)
            # lemmaobject = grablemmataobjectfor('greek_lemmata', word=entryword.entry, dbcursor=blankcursor)
            entryword.authorlist = entryword.generateauthorsummary()
            entryword.senselist = entryword.generatesensessummary()
            # entryword.quotelist = entryword.generatequotesummary(lemmaobject)
            entryword.flaggedsenselist = self.authorentrysummary
            # entryword.phraselist = self.phrasesummary
        # entryword.flaggedsenselist = entryword.generateflaggedsummary()
        # print('entryword.flaggedsenselist', entryword.flaggedsenselist)

        awq = entryword.authorlist + entryword.senselist + entryword.quotelist + entryword.flaggedsenselist + entryword.phraselist
        zero = ['0 authors', '0 senses', '0 quotes', '0 flagged senses', '0 phrases']
        for z in zero:
            try:
                awq.remove(z)
            except ValueError:
                pass

        if len(awq) > 0:
            summary = formatdictionarysummary(entryword)
        else:
            summary = str()
        return summary

    def _buildauthorentrysummary(self) -> List[str]:
        # wo.insertclickablelookups() needs to run before the regex here will work
        wo = self.thiswordobject
        flagged = wo.flagauthor
        if not flagged:
            return list(str())

        # you get a huge mess with the Latin senses that toggle on and off constantly and do not cleanly close anywhere
        """
        <sense id="n10676.3" level="3"> <span class="dicthi dictrend_ital">Sing.</span>, as collective term for the magistracy, <span class="dicthi dictrend_ital">the consuls</span>, when the office is in view rather than the persons: quod populus in se jus dederit, eo consulem usurum; <span class="dictcit"><span class="dictquote dictlang_la">non ipsos (sc. <dictionaryentry id="consules">consules</dictionaryentry>) libidinem ac licentiam suam pro lege habituros,</span> <bibl id="perseus/lt0914/001/3:9:5"><span class="dictauthor">Livy</span> 3, 9, 5</bibl></span> Weissenb. ad loc.: <span class="dictcit"><span class="dictquote dictlang_la">legatisque ad consulem missis,</span> <bibl id="perseus/lt0914/001/21:52:6"><span class="dictauthor">id.</span> 21, 52, 6</bibl></span> Heerw. ad loc.: <span class="dictcit"><span class="dictquote dictlang_la">aliter sine populi jussu nullius earum rerum consuli jus est,</span> <bibl><span class="dictauthor">Sallust</span> C. 29, 3</bibl></span>.—</sense>
        """

        if wo.islatin():
            return list(str())

        # note the sneaky regex; a bit brittle
        # the next only does LSJ entries properly; it catches c. 25% of a Latin entry
        transbodyfinder = re.compile(r'rans">(.*?)</span>(.*?)(</sense>|span class="dictt)')

        senses = re.findall(transbodyfinder, wo.body)
        flaggedsenses = [s[0] for s in senses if re.search(flagged, s[1])]
        flaggedsenses.sort()
        return flaggedsenses

    def _buildphrasesummary(self) -> List[str]:
        phrasefinder = re.compile(r'<span class="dicttrans dictrewritten_phrase">(.*?)</span>')
        phrases = re.findall(phrasefinder, self.thiswordobject.body)
        phrases = list(set(phrases))
        phrases.sort()
        return phrases

    def _builddistributiondict(self) -> str:
        distributions = str()
        return distributions

    def _buildfullentry(self) -> str:
        fullentrystring = '<br /><br />\n<span class="lexiconhighlight">Full entry:</span><br />'
        suppressedmorph = '<br /><br />\n<span class="lexiconhighlight">(Morphology notes hidden)</span><br />'
        w = self.thiswordobject
        w.constructsensehierarchy()
        w.runbodyxrefsuite()
        w.insertclickablelookups()
        # next is optional, really: a good CSS file will parse what you have thus far
        # (HipparchiaServer v.1.1.2 has the old XML CSS)
        w.xmltohtmlconversions()
        segments = list()
        segments.append(w.grabheadmaterial())
        # segments.append(suppressedmorph)
        segments.append(fullentrystring)
        segments.append(w.grabnonheadmaterial())
        fullentry = '\n'.join(segments)
        return fullentry

    def generatelexicaloutput(self, countervalue=None) -> str:
        divtemplate = '<div id="{wd}_{idx}">\n{entry}\n</div>'
        if countervalue:
            headingstr = '<hr /><p class="dictionaryheading" id={wd}_{wordid}>({cv})&nbsp;{ent}'
        else:
            headingstr = '<hr /><p class="dictionaryheading" id={wd}_{wordid}>{ent}'
        metricsstr = '&nbsp;<span class="metrics">[{me}]</span>'
        codestr = '&nbsp;<code>[ID: {wordid}]</code>'
        xrefstr = '&nbsp;<code>[XREF: {xref}]</code>'

        navtemplate = """
		<table class="navtable">
		<tr>
			<td class="alignleft">
				<span class="label">Previous: </span>
				<dictionaryidsearch entryid="{pid}" language="{lg}">{p}</dictionaryidsearch>
			</td>
			<td>&nbsp;</td>
			<td class="alignright">
				<span class="label">Next: </span>
				<dictionaryidsearch entryid="{nid}" language="{lg}">{n}</dictionaryidsearch>
			</td>
		<tr>
		</table>
		"""

        w = self.thiswordobject
        if w.isgreek():
            language = 'greek'
        else:
            language = 'latin'

        outputlist = list()
        outputlist.append(headingstr.format(ent=w.entry, cv=countervalue, wordid=w.id, wd=self.thisheadword))

        if w.metricalentry != w.entry:
            outputlist.append(metricsstr.format(me=w.metricalentry))

        outputlist.append('</p>')

        outputlist.append(self.entrysprincipleparts)
        outputlist.append(self.entrydistributions)
        outputlist.append(self.entrysummary)
        outputlist.append(self.fullenty)

        # outputlist.append(
        #     navtemplate.format(pid=w.preventryid, p=w.preventry, nid=w.nextentryid, n=w.nextentry, lg=language))

        fullentry = '\n'.join(outputlist)

        #fullentry = divtemplate.format(wd=self.thisheadword, idx=findparserxref(w), entry=fullentry)
        fullentry = divtemplate.format(wd=self.thisheadword, idx="", entry=fullentry)
        return fullentry


def formatdictionarysummary(wordentryobject) -> str:
    """

    turn three lists into html formatting for the summary material that will be inserted at the top of a
    dictionary entry

    :param summarydict:
    :return:
    """

    authors = wordentryobject.authorlist
    senses = wordentryobject.senselist
    quotes = wordentryobject.quotelist
    flagged = wordentryobject.flaggedsenselist
    phrases = wordentryobject.phraselist

    labelformultipleitems = '<div class="{cl}"><span class="lexiconhighlight">{lb}</span><br />'
    labelforoneitem = '<span class="{cl}">{item}</span><br />'
    itemtext = '\t<span class="{cl}">({ct})&nbsp;{item}</span><br />'

    sections = {
        'authors': {'items': authors, 'classone': 'authorsummary', 'classtwo': 'authorsum', 'label': 'Citations from'},
        'quotes': {'items': quotes, 'classone': 'quotessummary', 'classtwo': 'quotesum', 'label': 'Quotes'},
        'senses': {'items': senses, 'classone': 'sensesummary', 'classtwo': 'sensesum', 'label': 'Senses'},
        'phrases': {'items': phrases, 'classone': 'phrasesummary', 'classtwo': 'phrasesum', 'label': 'Phrases'},
        'flaggedsenses': {'items': flagged, 'classone': 'quotessummary', 'classtwo': 'quotesum',
                          'label': 'Flagged Senses'},
        }

    outputlist = list()

    summarizing = ['senses', 'phrases', 'authors', 'quotes']

    for section in summarizing:
        sec = sections[section]
        items = sec['items']
        classone = sec['classone']
        classtwo = sec['classtwo']
        label = sec['label']
        if len(items) > 0:
            outputlist.append(labelformultipleitems.format(cl=classone, lb=label))
        if len(items) == 1:
            outputlist.append(labelforoneitem.format(cl=classtwo, item=items[0]))
        else:
            count = 0
            for i in items:
                count += 1
                outputlist.append(itemtext.format(cl=classtwo, item=i, ct=count))
        if len(items) > 0:
            outputlist.append('</div>')

    summarystring = '\n'.join(outputlist)
    summarystring = summarystring + '<br>'

    return summarystring


def findparserxref(wordobject) -> str:
    """

    used in LEXDEBUGMODE to find the parser xrefvalue for a headword

    :param entryname:
    :return:
    """

    dbconnection = setconnection()
    dbcursor = dbconnection.cursor()

    if wordobject.isgreek():
        lang = 'greek'
    else:
        lang = 'latin'

    trimmedentry = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]', '', wordobject.entry)

    q = 'SELECT * FROM {lang}_lemmata WHERE dictionary_entry=%s'.format(lang=lang)
    d = (wordobject.entry,)
    dbcursor.execute(q, d)
    results = dbcursor.fetchall()

    if not results:
        d = (trimmedentry,)
        dbcursor.execute(q, d)
        results = dbcursor.fetchall()

    # it is not clear that more than one item will ever be returned
    # but if that happened, you need to be ready to deal with it
    lemmaobjects = [dbLemmaObject(*r) for r in results]
    xrefs = [str(l.xref) for l in lemmaobjects]

    xrefvalues = ', '.join(xrefs)

    dbconnection.connectioncleanup()

    return xrefvalues


def grablemmataobjectfor(db, dbcursor=None, word=None, xref=None, allowsuperscripts=False):
    """

    send a word, return a lemmaobject

    hipparchiaDB=# select * from greek_lemmata limit 0;
     dictionary_entry | xref_number | derivative_forms
    ------------------+-------------+------------------

    EITHER 'word' should be set OR 'xref' should be set: not both

    at the moment we only use 'word' in both calls to this function:
        hipparchiaobjects/lexicaloutputobjects.py
        hipparchiaobjects/morphanalysisobjects.py

    'allowsuperscripts' because sometimes you are supposed to search under δέω² and sometimes you are not...

    :param db:
    :param dbcursor:
    :param word:
    :param xref:
    :param allowsuperscripts:
    :return:
    """

    dbconnection = None
    if not dbcursor:
        dbconnection = setconnection()
        dbconnection.setautocommit()
        dbcursor = dbconnection.cursor()

    field = str()
    data = None

    if xref:
        field = 'xref_number'
        data = xref

    if word:
        field = 'dictionary_entry'
        data = word

    if not allowsuperscripts:
        data = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]', '', data)

    if not data:
        lo = dbLemmaObject('[programming error: no word or xref set in grablemmataobjectfor()]', -1, '')
        return lo

    q = 'SELECT * FROM {db} WHERE {f}=%s'.format(db=db, f=field)
    d = (data,)

    dbcursor.execute(q, d)
    lem = dbcursor.fetchone()

    try:
        lemmaobject = dbLemmaObject(*lem)
    except TypeError:
        # 'NoneType' object is not subscriptable
        lemmaobject = dbLemmaObject('[entry not found]', -1, '')

    if dbconnection:
        dbconnection.connectioncleanup()

    return lemmaobject


class dbLemmaObject(object):
    """
    an object that corresponds to a db line

    CREATE TABLE public.greek_lemmata (
        dictionary_entry character varying(64) COLLATE pg_catalog."default",
        xref_number integer,
        derivative_forms text COLLATE pg_catalog."default"
    )

    hipparchiaDB=# select count(dictionary_entry) from greek_lemmata;
     count
    --------
     114098
    (1 row)

    hipparchiaDB=# select count(dictionary_entry) from latin_lemmata;
     count
    -------
     38662
    (1 row)

    """

    __slots__ = ('dictionaryentry', 'xref', 'formlist')

    def __init__(self, dictionaryentry, xref, derivativeforms):
        self.dictionaryentry = dictionaryentry
        self.xref = xref
        self.formlist = derivativeforms


def deabbreviateauthors(authorabbr: str, lang: str) -> str:
	"""

	just hand this off to another function via language setting

	:param authorabbr:
	:param lang:
	:return:
	"""

	if lang == 'greek':
		authordict = deabrevviategreekauthors()
	elif lang == 'latin':
		authordict = deabrevviatelatinauthors()
	else:
		authordict = dict()

	if authorabbr in authordict:
		author = authordict[authorabbr]
	else:
		author = authorabbr

	return author


def deabrevviategreekauthors() -> Dict[str, str]:
	"""

	return a decoder dictionary

	copy the the appropriate segment at the top of of greek-lexicon_1999.04.0057.xml into a new file
	[lines 788 to 4767]

	then:

		grep "<item><hi rend=\"bold\">" tlg_authors_and_works.txt > tlg_authorlist.txt
		perl -pi -w -e 's/<\/hi>.*?\[/<\/hi>\[/g;' tlg_authorlist.txt
		perl -pi -w -e 's/<item><hi rend="bold">//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/hi>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<date>.*?<\/date>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<title>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/title>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/item>//g;' tlg_authorlist.txt

	what remains will look like:

		Aelius Dionysius[Ael.Dion.]

	then regex:
		^(.*?)\[(.*?)\]  ==> '\2': '\1',

	then all lines with single quotes and colons are good

		grep ":" tlg_authorlist.txt > tlg_authordict.txt

	there are some key collisions, but you are basically done after you whack those moles

	:param:
	:return: authordict
	"""
	authordict = {
		'Abyd.': 'Abydenus',
		'Acerat.': 'Aceratus',
		'Acesand.': 'Acesander',
		'Achae.': 'Achaeus',
		'Ach.Tat.': 'Achilles Tatius',
		'Acus.': 'Acusilaus',
		'Adam.': 'Adamantius',
		'Ael.': 'Aelianus',
		'Ael.Dion.': 'Aelius Dionysius',
		'Aemil.': 'Aemilianus',
		'Aen.Gaz.': 'Aeneas Gazaeus',
		'Aen.Tact.': 'Aeneas Tacticus',
		'Aesar.': 'Aesara',
		'Aeschin.': 'Aeschines',
		'Aeschin.Socr.': 'Aeschines Socraticus',
		'A.': 'Aeschylus',
		'Aesch.Alex.': 'Aeschylus Alexandrinus',
		'Aesop.': 'Aesopus',
		'Aët.': 'Aëtius',
		'Afric.': 'Africanus, Julius',
		'Agaclyt.': 'Agaclytus',
		'Agatharch.': 'Agatharchides',
		'Agathem.': 'Agathemerus',
		'Agath.': 'Agathias',
		'Agathin.': 'Agathinus',
		'Agathocl.': 'Agathocles',
		'Alb.': 'Albinus',
		'Alc.Com.': 'Alcaeus',
		'Alc.': 'Alcaeus',
		'Alc.Mess.': 'Alcaeus Messenius',
		'Alcid.': 'Alcidamas',
		'Alcin.': 'Alcinous',
		'Alciphr.': 'Alciphro',
		'Alcm.': 'Alcman',
		'Alexand.Com.': 'Alexander',
		'Alex.Aet.': 'Alexander Aetolus',
		'Alex.Aphr.': 'Alexander Aphrodisiensis',
		'Alex.Eph.': 'Alexander Ephesius',
		'Alex.Polyh.': 'Alexander Polyhistor',
		'Alex.Trall.': 'Alexander Trallianus',
		'Alex.': 'Alexis',
		'Alph.': 'Alpheus',
		'Alyp.': 'Alypius',
		'Amips.': 'Amipsias',
		'Ammian.': 'Ammianus',
		'Amm.Marc.': 'Ammianus Marcellinus',
		'Ammon.': 'Ammonius',
		'Anach.': 'Anacharsis',
		'Anacr.': 'Anacreon',
		'Anacreont.': 'Anacreontea',
		'Anan.': 'Ananius',
		'Anaxag.': 'Anaxagoras',
		'Anaxandr.': 'Anaxandrides',
		'Anaxandr.Hist.': 'Anaxandrides',
		'Anaxarch.': 'Anaxarchus',
		'Anaxil.': 'Anaxilas',
		'Anaximand.Hist.': 'Anaximander',
		'Anaximand.': 'Anaximander',
		'Anaximen.': 'Anaximenes',
		'Anaxipp.': 'Anaxippus',
		'And.': 'Andocides',
		'Androm.': 'Andromachus',
		'Andronic.': 'Andronicus',
		'Andronic.Rhod.': 'Andronicus Rhodius',
		'Androt.': 'Androtion',
		'AB': 'Anecdota Graeca',
		'Anecd.Stud.': 'Anecdota Graeca et Latina',
		'Anon.': 'Anonymus',
		'Anon.Lond.': 'Anonymus Londnensis',
		'Anon.Rhythm.': 'Anonymus Rhythmicus',
		'Anon.Vat.': 'Anonymus Vaticanus',
		'Antag.': 'Antagoras',
		'Anthem.': 'Anthemius',
		'Anticl.': 'Anticlides',
		'Antid.': 'Antidotus',
		'Antig.': 'Antigonus Carystius',
		'Antig.Nic.': 'Antigonus Nicaeanus',
		'Antim.': 'Antimachus Colophonius',
		'Antioch.Astr.': 'Antiochus Atheniensis',
		'Antioch.': 'Antiochus',
		'Antioch.Hist.': 'Antiochus',
		'Antip.Sid.': 'Antipater Sidonius',
		'Antip.Stoic.': 'Antipater Tarsensis',
		'Antip.Thess.': 'Antipater Thessalonicensis',
		'Antiph.': 'Antiphanes',
		'Antiphan.': 'Antiphanes Macedo',
		'Antiphil.': 'Antiphilus',
		'Antipho Soph.': 'Antipho Sophista',
		'Antipho Trag.': 'Antipho',
		'Antisth.': 'Antisthenes',
		'Antist.': 'Antistius',
		'Ant.Lib.': 'Antoninus Liberalis',
		'Anton.Arg.': 'Antonius Argivus',
		'Ant.Diog.': 'Antonius Diogenes',
		'Antyll.': 'Antyllus',
		'Anub.': 'Anubion',
		'Anyt.': 'Anyte',
		'Aphth.': 'Aphthonius',
		'Apollinar.': 'Apollinarius',
		'Apollod.Com.': 'Apollodorus',
		'Apollod.Car.': 'Apollodorus Carystius',
		'Apollod.Gel.': 'Apollodorus Gelous',
		'Apollod.': 'Apollodorus',
		'Apollod.Lyr.': 'Apollodorus',
		'Apollod.Stoic.': 'Apollodorus Seleuciensis',
		'Apollonid.': 'Apollonides',
		'Apollonid.Trag.': 'Apollonides',
		'Apollon.': 'Apollonius',
		'Apollon.Cit.': 'Apollonius Citiensis',
		'A.D.': 'Apollonius Dyscolus',
		'Apollon.Perg.': 'Apollonius Pergaeus',
		'A.R.': 'Apollonius Rhodius',
		'Ap.Ty.': 'Apollonius Tyanensis',
		'Apolloph.': 'Apollophanes',
		'Apolloph.Stoic.': 'Apollophanes',
		'Apostol.': 'Apostolius',
		'App.': 'Appianus',
		'Aps.': 'Apsines',
		'Apul.': 'Apuleius',
		'Aq.': 'Aquila',
		'Arab.': 'Arabius',
		'Arar.': 'Araros',
		'Arat.': 'Aratus',
		'Arc.': 'Arcadius',
		'Arcesil.': 'Arcesilaus',
		'Arched.': 'Archedicus',
		'Arched.Stoic.': 'Archedemus Tarsensis',
		'Archemach.': 'Archemachus',
		'Archestr.': 'Archestratus',
		'Arch.': 'Archias',
		'Arch.Jun.': 'Archias Junior',
		'Archig.': 'Archigenes',
		'Archil.': 'Archilochus',
		'Archim.': 'Archimedes',
		'Archimel.': 'Archimelus',
		'Archipp.': 'Archippus',
		'Archyt.Amph.': 'Archytas Amphissensis',
		'Archyt.': 'Archytas Tarentinus',
		'Aret.': 'Aretaeus',
		'Aristaenet.': 'Aristaenetus',
		'Aristag.': 'Aristagoras',
		'Aristag.Hist.': 'Aristagoras',
		'Aristarch.': 'Aristarchus',
		'Aristarch.Sam.': 'Aristarchus Samius',
		'Aristarch.Trag.': 'Aristarchus',
		'Aristeas Epic.': 'Aristeas',
		'Aristid.': 'Aristides',
		'Aristid.Mil.': 'Aristides Milesius',
		'Aristid.Quint.': 'Aristides Quintilianus',
		'Aristipp.': 'Aristippus',
		'AristoStoic.': 'Aristo Chius',
		'Aristobul.': 'Aristobulus',
		'Aristocl.': 'Aristocles',
		'Aristocl.Hist.': 'Aristocles',
		'Aristodem.': 'Aristodemus',
		'Aristodic.': 'Aristodicus',
		'Aristomen.': 'Aristomenes',
		'Aristonym.': 'Aristonymus',
		'Ar.': 'Aristophanes',
		'Aristoph.Boeot.': 'Aristophanes Boeotus',
		'Ar.Byz.': 'Aristophanes Byzantinus',
		'Arist.': 'Aristoteles',
		'Aristox.': 'Aristoxenus',
		'Ar.Did.': 'Arius Didymus',
		'Arr.': 'Arrianus',
		'Artem.': 'Artemidorus Daldianus',
		'Artemid.': 'Artemidorus Tarsensis',
		'Arus.Mess.': 'Arusianus Messius',
		'Ascens.Is.': 'Ascensio Isaiae',
		'Asclep.': 'Asclepiades',
		'Asclep.Jun.': 'Asclepiades Junior',
		'Asclep.Myrl.': 'Asclepiades Myrleanus',
		'Asclep.Tragil.': 'Asclepiades Tragilensis',
		'Ascl.': 'Asclepius',
		'Asp.': 'Aspasius',
		'Astramps.': 'Astrampsychus',
		'Astyd.': 'Astydamas',
		'Ath.': 'Athenaeus',
		'Ath.Mech.': 'Athenaeus',
		'Ath.Med.': 'Athenaeus',
		'Athenodor.Tars.': 'Athenodorus Tarsensis',
		'Atil.Fort.': 'Atilius Fortunatianus',
		'Attal.': 'Attalus',
		'Attic.': 'Atticus',
		'Aus.': 'Ausonius',
		'Autocr.': 'Autocrates',
		'Autol.': 'Autolycus',
		'Autom.': 'Automedon',
		'Axionic.': 'Axionicus',
		'Axiop.': 'Axiopistus',
		'Babr.': 'Babrius',
		'Bacch.': 'Bacchius',
		'B.': 'Bacchylides',
		'Balbill.': 'Balbilla',
		'Barb.': 'Barbucallos',
		'Bass.': 'Bassus, Lollius',
		'Bato Sinop.': 'Bato Sinopensis',
		'Batr.': 'Batrachomyomachia',
		'Beros.': 'Berosus',
		'Besant.': 'Besantinus',
		'Blaes.': 'Blaesus',
		'Boeth.': 'Boethus',
		'Boeth.Stoic.': 'Boethus Sidonius',
		'Brut.': 'Brutus',
		'Buther.': 'Butherus',
		'Cael.Aur.': 'Caelius Aurelianus',
		'Call.Com.': 'Callias',
		'Call.Hist.': 'Callias',
		'Callicrat.': 'Callicratidas',
		'Call.': 'Callimachus',
		'Callinic.Rh.': 'Callinicus',
		'Callin.': 'Callinus',
		'Callistr.Hist.': 'Callistratus',
		'Callistr.': 'Callistratus',
		'Callix.': 'Callixinus',
		'Canthar.': 'Cantharus',
		'Carc.': 'Carcinus',
		'Carm.Aur.': 'Carmen Aureum',
		'Carm.Pop.': 'Carmina Popularia',
		'Carneisc.': 'Carneiscus',
		'Carph.': 'Carphyllides',
		'Caryst.': 'Carystius',
		'Cass.': 'Cassius',
		'Cass.Fel.': 'Cassius Felix',
		'Cat.Cod.Astr.': 'Catalogus Codicum Astrologorum',
		'Ceb.': 'Cebes',
		'Cels.': 'Celsus',
		'Cephisod.': 'Cephisodorus',
		'Cerc.': 'Cercidas',
		'Cercop.': 'Cercopes',
		'Cereal.': 'Cerealius',
		'Certamen': 'Certamen Homeri et Hesiodi',
		'Chaerem.Hist.': 'Chaeremon',
		'Chaerem.': 'Chaeremon',
		'Chamael.': 'Chamaeleon',
		'Epist.Charact.': 'Characteres Epistolici',
		'Chares Iamb.': 'Chares',
		'Chares Trag.': 'Chares',
		'Chariclid.': 'Chariclides',
		'Charis.': 'Charisius',
		'Charixen.': 'Charixenes',
		'Charond.': 'Charondas',
		'Chionid.': 'Chionides',
		'Choeril.': 'Choerilus',
		'Choeril.Trag.': 'Choerilus',
		'Choerob.': 'Choeroboscus',
		'Chor.': 'Choricius',
		'Chrysipp.Stoic.': 'Chrysippus',
		'Chrysipp. Tyan.': 'Chrysippus Tyanensis',
		'Cic.': 'Cicero, M. Tullius',
		'Claudian.': 'Claudianus',
		'Claud.Iol.': 'Claudius Iolaus',
		'Cleaenet.': 'Cleaenetus',
		'Cleanth.Stoic.': 'Cleanthes',
		'Clearch.Com.': 'Clearchus',
		'Clearch.': 'Clearchus',
		'Clem.Al.': 'Clemens Alexandrinus',
		'Cleobul.': 'Cleobulus',
		'Cleom.': 'Cleomedes',
		'Cleon Sic.': 'Cleon Siculus',
		'Cleonid.': 'Cleonides',
		'Cleostrat.': 'Cleostratus',
		'Clidem. vel Clitodem.': 'Clidemus',
		'Clin.': 'Clinias',
		'Clitarch.': 'Clitarchus',
		'Clitom.': 'Clitomachus',
		'Cod.Just.': 'Codex Justinianus',
		'Cod.Theod.': 'Codex Theodosianus',
		'Colot.': 'Colotes',
		'Coluth.': 'Coluthus',
		'Com.Adesp.': 'Comica Adespota',
		'Corinn.': 'Corinna',
		'Corn.Long.': 'Cornelius Longus',
		'Corn.': 'Cornutus',
		'Corp.Herm.': 'Corpus Hermeticum',
		'Crater.': 'Craterus',
		'Crates Com.': 'Crates',
		'Crates Hist.': 'Crates',
		'Crates Theb.': 'Crates Thebanus',
		'Cratin.': 'Cratinus',
		'Cratin.Jun.': 'Cratinus Junior',
		'Cratipp.': 'Cratippus',
		'Crin.': 'Crinagoras',
		'Critias': 'Critias',
		'Crito Com.': 'Crito',
		'Crobyl.': 'Crobylus',
		'Ctes.': 'Ctesias',
		'Cyllen.': 'Cyllenius',
		'Cyran.': 'Cyranus',
		'Cypr.': 'Cypria',
		'Cyr.': 'Cyrilli Glossarium',
		'Cyrill.': 'Cyrillus',
		'Damag.': 'Damagetus',
		'Dam.': 'Damascius',
		'Damian.': 'Damianus',
		'Damoch.': 'Damocharis',
		'Damocr.': 'Damocrates',
		'Damocrit.': 'Damocritus',
		'Damostr.': 'Damostratus',
		'Damox.': 'Damoxenus',
		'Deioch.': 'Deiochus',
		'Demad.': 'Demades',
		'Demetr.': 'Demetrius',
		'Demetr.Com.Nov.': 'Demetrius',
		'Demetr.Com.Vet.': 'Demetrius',
		'Demetr.Apam.': 'Demetrius Apamensis',
		'Demetr.Lac.': 'Demetrius Lacon',
		'Dem.Phal.': 'Demetrius Phalereus',
		'Demetr.Troez.': 'Demetrius Troezenius',
		'Democh.': 'Demochares',
		'Democr.': 'Democritus',
		'Democr.Eph.': 'Democritus Ephesius',
		'Demod.': 'Demodocus',
		'Demonic.': 'Demonicus',
		'Demoph.': 'Demophilus',
		'D.': 'Demosthenes',
		'Dem.Bith.': 'Demosthenes Bithynus',
		'Dem.Ophth.': 'Demosthenes Ophthalmicus',
		'Dercyl.': 'Dercylus',
		'Dexipp.': 'Dexippus',
		'Diagor.': 'Diagoras',
		'Dialex.': 'Dialexeis',
		'Dicaearch.': 'Dicaearchus',
		'Dicaearch.Hist.': 'Dicaearchus',
		'Dicaeog.': 'Dicaeogenes',
		'Did.': 'Didymus',
		'Dieuch.': 'Dieuches',
		'Dieuchid.': 'Dieuchidas',
		'Dig.': 'Digesta',
		'Din.': 'Dinarchus',
		'Dinol.': 'Dinolochus',
		'D.C.': 'Dio Cassius',
		'D.Chr.': 'Dio Chrysostomus',
		'Diocl.': 'Diocles',
		'Diocl.Com.': 'Diocles',
		'Diocl.Fr.': 'Diocles',
		'Diod.Com.': 'Diodorus',
		'Diod.': 'Diodorus',
		'Diod.Rh.': 'Diodorus',
		'Diod.Ath.': 'Diodorus Atheniensis',
		'D.S.': 'Diodorus Siculus',
		'Diod.Tars.': 'Diodorus Tarsensis',
		'Diog.Apoll.': 'Diogenes Apolloniates',
		'Diog.Ath.': 'Diogenes Atheniensis',
		'Diog.Bab.Stoic.': 'Diogenes Babylonius',
		'Diog.': 'Diogenes Cynicus',
		'D.L.': 'Diogenes Laertius',
		'Diog.Oen.': 'Diogenes Oenoandensis',
		'Diog.Sinop.': 'Diogenes Sinopensis',
		'Diogenian.': 'Diogenianus',
		'Diogenian.Epicur.': 'Diogenianus Epicureus',
		'Diom.': 'Diomedes',
		'Dionys.Com.': 'Dionysius',
		'Dionys.': 'Dionysius',
		'Dionys.Trag.': 'Dionysius',
		'Dion.Byz.': 'Dionysius Byzantius',
		'Dion.Calliph.': 'Dionysius Calliphontis filius',
		'Dionys.Eleg.': 'Dionysius Chalcus',
		'D.H.': 'Dionysius Halicarnassensis',
		'Dionys.Stoic.': 'Dionysius Heracleota',
		'Dionys.Minor': 'Dionysius Minor',
		'D.P.': 'Dionysius Periegeta',
		'Dionys.Sam.': 'Dionysius Samius',
		'D.T.': 'Dionysius Thrax',
		'Diophan.': 'Diophanes',
		'Dioph.': 'Diophantus',
		'Diosc.': 'Dioscorides',
		'Diosc.Hist.': 'Dioscorides',
		'Dsc.': 'Dioscorides (Dioscurides)',
		'Diosc.Gloss.': 'Dioscorides Glossator',
		'Diotim.': 'Diotimus',
		'Diotog.': 'Diotogenes',
		'Diox.': 'Dioxippus',
		'Diph.': 'Diphilus',
		'Diph.Siph.': 'Diphilus Siphnius',
		'Diyll.': 'Diyllus',
		'Donat.': 'Donatus, Aelius',
		'Doroth.': 'Dorotheus',
		'Dosiad.': 'Dosiadas',
		'Dosiad.Hist.': 'Dosiades',
		'Dosith.': 'Dositheus',
		'Ecphantid.': 'Ecphantides',
		'Ecphant.': 'Ecphantus',
		'Eleg.Alex.Adesp.': 'Elegiaca Alexandrina Adespota',
		'Emp.': 'Empedocles',
		'1Enoch': 'Enoch',
		'Ephipp.': 'Ephippus',
		'Ephor.': 'Ephorus',
		'Epic.Alex.Adesp.': 'Epica Alexandrina Adespota',
		'Epich.': 'Epicharmus',
		'Epicr.': 'Epicrates',
		'Epict.': 'Epictetus',
		'Epicur.': 'Epicurus',
		'Epig.': 'Epigenes',
		'Epil.': 'Epilycus',
		'Epimenid.': 'Epimenides',
		'Epin.': 'Epinicus',
		'Erasistr.': 'Erasistratus',
		'Eratosth.': 'Eratosthenes',
		'Erinn.': 'Erinna',
		'Eriph.': 'Eriphus',
		'Erot.': 'Erotianus',
		'Eryc.': 'Erycius',
		'Etrusc.': 'Etruscus',
		'Et.Gen.': 'Etymologicum Genuinum',
		'Et.Gud.': 'Etymologicum Gudianum',
		'EM': 'Etymologicum Magnum',
		'Euang.': 'Euangelus',
		'Eubulid.': 'Eubulides',
		'Eub.': 'Eubulus',
		'Euc.': 'Euclides',
		'Eucrat.': 'Eucrates',
		'Eudem.': 'Eudemus',
		'Eudox.': 'Eudoxus',
		'Eudox.Com.': 'Eudoxus',
		'Eumel.': 'Eumelus',
		'Eun.': 'Eunapius',
		'Eunic.': 'Eunicus',
		'Euod.': 'Euodus',
		'Euph.': 'Euphorio',
		'Euphron.': 'Euphronius',
		'Eup.': 'Eupolis',
		'E.': 'Euripides',
		'Euryph.': 'Euryphamus',
		'Eus.Hist.': 'Eusebius',
		'Eus.': 'Eusebius Caesariensis',
		'Eus.Mynd.': 'Eusebius Myndius',
		'Eust.': 'Eustathius',
		'Eust.Epiph.': 'Eustathius Epiphaniensis',
		'Eustr.': 'Eustratius',
		'Euthycl.': 'Euthycles',
		'Eutoc.': 'Eutocius',
		'Eutolm.': 'Eutolmius',
		'Eutych.': 'Eutychianus',
		'Even.': 'Evenus',
		'Ezek.': 'Ezekiel',
		'Favorin.': 'Favorinus',
		'Fest.': 'Festus',
		'Firm.': 'Firmicus Maternus',
		'Fortunat.Rh.': 'Fortunatianus',
		'Gabriel.': 'Gabrielius',
		'Gaet.': 'Gaetulicus, Cn. Lentulus',
		'Gal.': 'Galenus',
		'Gaud.Harm.': 'Gaudentius',
		'Gell.': 'Gellius, Aulus',
		'Gem.': 'Geminus',
		'Gp.': 'Geoponica',
		'Germ.': 'Germanicus Caesar',
		'Glauc.': 'Glaucus',
		'Gloss.': 'Glossaria',
		'Gorg.': 'Gorgias',
		'Greg.Cor.': 'Gregorius Corinthius',
		'Greg.Cypr.': 'Gregorius Cyprius',
		'Hadr.Rh.': 'Hadrianus',
		'Hadr.': 'Hadrianus Imperator',
		'Harmod.': 'Harmodius',
		'Harp.': 'Harpocratio',
		'Harp.Astr.': 'Harpocratio',
		'Hecat.Abd.': 'Hecataeus Abderita',
		'Hecat.': 'Hecataeus Milesius',
		'Hedyl.': 'Hedylus',
		'Hegem.': 'Hegemon',
		'Hegesand.': 'Hegesander',
		'Hegesian.': 'Hegesianax',
		'Hegesipp.Com.': 'Hegesippus',
		'Hegesipp.': 'Hegesippus',
		'Hld.': 'Heliodorus',
		'Heliod.': 'Heliodorus',
		'Heliod.Hist.': 'Heliodorus',
		'Hellad.': 'Helladius',
		'Hellanic.': 'Hellanicus',
		'Hell.Oxy.': 'Hellenica Oxyrhynchia',
		'Hemerolog.Flor.': 'Hemerologium Florentinum',
		'Henioch.': 'Heniochus',
		'Heph.Astr.': 'Hephaestio',
		'Heph.': 'Hephaestio',
		'Heracl.': 'Heraclas',
		'Heraclid.Com.': 'Heraclides',
		'Heraclid.Cum.': 'Heraclides Cumaeus',
		'Heraclid.Lemb.': 'Heraclides Lembus',
		'Heraclid.Pont.': 'Heraclides Ponticus',
		'Heraclid.Sinop.': 'Heraclides Sinopensis',
		'Heraclid.': 'Heraclides Tarentinus',
		'Heraclit.': 'Heraclitus',
		'Herill.Stoic.': 'Herillus Carthaginiensis',
		'Herm.': 'Hermes Trismegistus',
		'Hermesian.': 'Hermesianax',
		'Herm.Hist.': 'Hermias',
		'Herm.Iamb.': 'Hermias',
		'Hermipp.': 'Hermippus',
		'Hermipp.Hist.': 'Hermippus',
		'Hermocl.': 'Hermocles',
		'Hermocr.': 'Hermocreon',
		'Hermod.': 'Hermodorus',
		'Hermog.': 'Hermogenes',
		'Herod.': 'Herodas',
		'Hdn.': 'Herodianus',
		'Herodor.': 'Herodorus',
		'Hdt.': 'Herodotus',
		'Herod.Med.': 'Herodotus',
		'Herophil.': 'Herophilus',
		'Hes.': 'Hesiodus',
		'Hsch.Mil.': 'Hesychius Milesius',
		'Hsch.': 'Hesychius',
		'Hices.': 'Hicesius',
		'Hierocl.': 'Hierocles',
		'Hierocl.Hist.': 'Hierocles',
		'Hieronym.Hist.': 'Hieronymus Cardianus',
		'Him.': 'Himerius',
		'Hipparch.': 'Hipparchus',
		'Hipparch.Com.': 'Hipparchus',
		'Hippias Erythr.': 'Hippias Erythraeus',
		'Hippiatr.': 'Hippiatrica',
		'Hp.': 'Hippocrates',
		'Hippod.': 'Hippodamus',
		'Hippol.': 'Hippolytus',
		'Hippon.': 'Hipponax',
		'Hist.Aug.': 'Historiae Augustae Scriptores',
		'Hom.': 'Homerus',
		'Honest.': 'Honestus',
		'Horap.': 'Horapollo',
		'h.Hom.': 'Hymni Homerici',
		'Hymn.Mag.': 'Hymni Magici',
		'Hymn.Id.Dact.': 'Hymnus ad Idaeos Dactylos',
		'Hymn.Is.': 'Hymnus ad Isim',
		'Hymn.Curet.': 'Hymnus Curetum',
		'Hyp.': 'Hyperides',
		'Hypsicl.': 'Hypsicles',
		'Iamb.': 'Iamblichus',
		'Iamb.Bab.': 'Iamblichus',
		'Ibyc.': 'Ibycus',
		'Il.': 'Ilias',
		'Il.Parv.': 'Ilias Parva',
		'Il.Pers.': 'Iliu Persis',
		'Iren.': 'Irenaeus',
		'Is.': 'Isaeus',
		'Isid.Trag.': 'Isidorus',
		'Isid.Aeg.': 'Isidorus Aegeates',
		'Isid.Char.': 'Isidorus Characenus',
		'Isid.': 'Isidorus Hispalensis',
		'Isig.': 'Isigonus',
		'Isoc.': 'Isocrates',
		'Isyll.': 'Isyllus',
		'Jo.Alex. vel Jo.Gramm.': 'Joannes Alexandrinus',
		'Jo.Diac.': 'Joannes Diaconus',
		'Jo.Gaz.': 'Joannes Gazaeus',
		'J.': 'Josephus',
		'Jul.': 'Julianus Imperator',
		'Jul. vel Jul.Aegypt.': 'Julianus Aegyptius',
		'Jul.Laod.': 'Julianus Laodicensis',
		'Junc.': 'Juncus',
		'Just.': 'Justinianus',
		'Juv.': 'Juvenalis, D. Junius',
		'Lamprocl.': 'Lamprocles',
		'Leo Phil.': 'Leo Philosophus',
		'Leon.': 'Leonidas',
		'Leonid.': 'Leonidas',
		'Leont.': 'Leontius',
		'Leont. in Arat.': 'Leontius',
		'Lesb.Gramm.': 'Lesbonax',
		'Lesb.Rh.': 'Lesbonax',
		'Leucipp.': 'Leucippus',
		'Lex.Mess.': 'Lexicon Messanense',
		'Lex.Rhet.': 'Lexicon Rhetoricum',
		'Lex.Rhet.Cant.': 'Lexicon Rhetoricum Cantabrigiense',
		'Lex.Sabb.': 'Lexicon Sabbaiticum',
		'Lex. de Spir.': 'Lexicon de Spiritu',
		'Lex.Vind.': 'Lexicon Vindobonense',
		'Lib.': 'Libanius',
		'Licymn.': 'Licymnius',
		'Limen.': 'Limenius',
		'Loll.': 'Lollius Bassus',
		'Longin.': 'Longinus',
		'Luc.': 'Lucianus',
		'Lucill.': 'Lucillius',
		'Lyc.': 'Lycophron',
		'Lycophronid.': 'Lycophronides',
		'Lycurg.': 'Lycurgus',
		'Lyd.': 'Lydus, Joannes Laurentius',
		'Lync.': 'Lynceus',
		'Lyr.Adesp.': 'Lyrica Adespota',
		'Lyr.Alex.Adesp.': 'Lyrica Alexandrina Adespota',
		'Lys.': 'Lysias',
		'Lysimachid.': 'Lysimachides',
		'Lysim.': 'Lysimachus',
		'Lysipp.': 'Lysippus',
		'Macar.': 'Macarius',
		'Maced.': 'Macedonius',
		'Macr.': 'Macrobius',
		'Maec.': 'Maecius',
		'Magn.': 'Magnes',
		'Magnus Hist.': 'Magnus',
		'Maiist.': 'Maiistas',
		'Malch.': 'Malchus',
		'Mamerc.': 'Mamercus',
		'Man.': 'Manetho',
		'Man.Hist.': 'Manetho',
		'Mantiss.Prov.': 'Mantissa Proverbiorum',
		'Marcellin.': 'Marcellinus',
		'Marc.Sid.': 'Marcellus Sidetes',
		'Marcian.': 'Marcianus',
		'M.Ant.': 'Marcus Antoninus',
		'Marc.Arg.': 'Marcus Argentarius',
		'Maria Alch.': 'Maria',
		'Marian.': 'Marianus',
		'Marin.': 'Marinus',
		'Mar.Vict.': 'Marius Victorinus',
		'Mart.': 'Martialis',
		'Mart.Cap.': 'Martianus Capella',
		'Max.': 'Maximus',
		'Max.Tyr.': 'Maximus Tyrius',
		'Megasth.': 'Megasthenes',
		'Melamp.': 'Melampus',
		'Melanipp.': 'Melanippides',
		'Melanth.Hist.': 'Melanthius',
		'Melanth.Trag.': 'Melanthius',
		'Mel.': 'Meleager',
		'Meliss.': 'Melissus',
		'Memn.': 'Memnon',
		'Menaechm.': 'Menaechmus',
		'Men.': 'Menander',
		'Men.Rh.': 'Menander',
		'Men.Eph.': 'Menander Ephesius',
		'Men.Prot.': 'Menander Protector',
		'Menecl.': 'Menecles Barcaeus',
		'Menecr.': 'Menecrates',
		'Menecr.Eph.': 'Menecrates Ephesius',
		'Menecr.Xanth.': 'Menecrates Xanthius',
		'Menemach.': 'Menemachus',
		'Menesth.': 'Menesthenes',
		'Menipp.': 'Menippus',
		'Menodot.': 'Menodotus Samius',
		'Mesom.': 'Mesomedes',
		'Metag.': 'Metagenes',
		'Metrod.': 'Metrodorus',
		'Metrod.Chius': 'Metrodorus Chius',
		'Metrod.Sceps.': 'Metrodorus Scepsius',
		'Mich.': 'Michael Ephesius',
		'Mimn.': 'Mimnermus',
		'Mimn.Trag.': 'Mimnermus',
		'Minuc.': 'Minucianus',
		'Mithr.': 'Mithradates',
		'Mnasalc.': 'Mnasalcas',
		'Mnesim.': 'Mnesimachus',
		'Mnesith.Ath.': 'Mnesitheus Atheniensis',
		'Mnesith.Cyz.': 'Mnesitheus Cyzicenus',
		'Moer.': 'Moeris',
		'MoschioTrag.': 'Moschio',
		'Mosch.': 'Moschus',
		'Muc.Scaev.': 'Mucius Scaevola',
		'Mund.': 'Mundus Munatius',
		'Musae.': 'Musaeus',
		'Music.': 'Musicius',
		'Muson.': 'Musonius',
		'Myrin.': 'Myrinus',
		'Myrsil.': 'Myrsilus',
		'Myrtil.': 'Myrtilus',
		'Naumach.': 'Naumachius',
		'Nausicr.': 'Nausicrates',
		'Nausiph.': 'Nausiphanes',
		'Neanth.': 'Neanthes',
		'Nearch.': 'Nearchus',
		'Nech.': 'Nechepso',
		'Neophr.': 'Neophron',
		'Neoptol.': 'Neoptolemus',
		'Nicaenet.': 'Nicaenetus',
		'Nic.': 'Nicander',
		'Nicarch.': 'Nicarchus',
		'Nicoch.': 'Nicochares',
		'Nicocl.': 'Nicocles',
		'Nicod.': 'Nicodemus',
		'Nicol.Com.': 'Nicolaus',
		'Nicol.': 'Nicolaus',
		'Nic.Dam.': 'Nicolaus Damascenus',
		'Nicom.Com.': 'Nicomachus',
		'Nicom.Trag.': 'Nicomachus',
		'Nicom.': 'Nicomachus Gerasenus',
		'Nicostr.Com.': 'Nicostratus',
		'Nicostr.': 'Nicostratus',
		'Nonn.': 'Nonnus',
		'Noss.': 'Nossis',
		'Numen.': 'Numenius Apamensis',
		'Nymphod.': 'Nymphodorus',
		'Ocell.': 'Ocellus Lucanus',
		'Od.': 'Odyssea',
		'Oenom.': 'Oenomaus',
		'Olymp.Alch.': 'Olympiodorus',
		'Olymp.Hist.': 'Olympiodorus',
		'Olymp.': 'Olympiodorus',
		'Onat.': 'Onatas',
		'Onos.': 'Onosander (Onasander)',
		'Ophel.': 'Ophelio',
		'Opp.': 'Oppianus',
		'Orac.Chald.': 'Oracula Chaldaica',
		'Orib.': 'Oribasius',
		'Orph.': 'Orphica',
		'Pae.Delph.': 'Paean Delphicus',
		'Pae.Erythr.': 'Paean Erythraeus',
		'Palaeph.': 'Palaephatus',
		'Palch.': 'Palchus',
		'Pall.': 'Palladas',
		'Pamphil.': 'Pamphilus',
		'Pancrat.': 'Pancrates',
		'Panyas.': 'Panyasis',
		'Papp.': 'Pappus',
		'Parm.': 'Parmenides',
		'Parmen.': 'Parmenio',
		'Parrhas.': 'Parrhasius',
		'Parth.': 'Parthenius',
		'Patrocl.': 'Patrocles Thurius',
		'Paul.Aeg.': 'Paulus Aegineta',
		'Paul.Al.': 'Paulus Alexandrinus',
		'Paul.Sil.': 'Paulus Silentiarius',
		'Paus.': 'Pausanias',
		'Paus.Dam.': 'Pausanias Damascenus',
		'Paus.Gr.': 'Pausanias Grammaticus',
		'Pediasim.': 'Pediasimus',
		'Pelag.Alch.': 'Pelagius',
		'Pempel.': 'Pempelus',
		'Perict.': 'Perictione',
		'Peripl.M.Rubr.': 'Periplus Maris Rubri',
		'Pers.Stoic.': 'Persaeus Citieus',
		'Pers.': 'Perses',
		'Petos.': 'Petosiris',
		'Petron.': 'Petronius',
		'Petr.Patr.': 'Petrus Patricius',
		'Phaedim.': 'Phaedimus',
		'Phaënn.': 'Phaënnus',
		'Phaest.': 'Phaestus',
		'Phal.': 'Phalaecus',
		'Phalar.': 'Phalaris',
		'Phan.': 'Phanias',
		'Phan.Hist.': 'Phanias',
		'Phanocl.': 'Phanocles',
		'Phanod.': 'Phanodemus',
		'Pherecr.': 'Pherecrates',
		'Pherecyd.': 'Pherecydes Lerius',
		'Pherecyd.Syr.': 'Pherecydes Syrius',
		'Philagr.': 'Philagrius',
		'Philem.': 'Philemo',
		'Philem.Jun.': 'Philemo Junior',
		'Philetaer.': 'Philetaerus',
		'Philet.': 'Philetas',
		'Philippid.': 'Philippides',
		'Philipp.Com.': 'Philippus',
		'Phil.': 'Philippus',
		'Philisc.Com.': 'Philiscus',
		'Philisc.Trag.': 'Philiscus',
		'Philist.': 'Philistus',
		'Ph.Epic.': 'Philo',
		'Ph.': 'Philo',
		'Ph.Bybl.': 'Philo Byblius',
		'Ph.Byz.': 'Philo Byzantius',
		'Ph.Tars.': 'Philo Tarsensis',
		'Philoch.': 'Philochorus',
		'Philocl.': 'Philocles',
		'Philod.Scarph.': 'Philodamus Scarpheus',
		'Phld.': 'Philodemus',
		'Philol.': 'Philolaus',
		'Philomnest.': 'Philomnestus',
		'Philonid.': 'Philonides',
		'Phlp.': 'Philoponus, Joannes',
		'Philosteph.Com.': 'Philostephanus',
		'Philosteph.Hist.': 'Philostephanus',
		'Philostr.': 'Philostratus',
		'Philostr.Jun.': 'Philostratus Junior',
		'Philox.': 'Philoxenus',
		'Philox.Gramm.': 'Philoxenus',
		'Philum.': 'Philumenus',
		'Philyll.': 'Philyllius',
		'Phint.': 'Phintys',
		'Phleg.': 'Phlegon Trallianus',
		'Phoc.': 'Phocylides',
		'Phoeb.': 'Phoebammon',
		'Phoenicid.': 'Phoenicides',
		'Phoen.': 'Phoenix',
		'Phot.': 'Photius',
		'Phryn.': 'Phrynichus',
		'Phryn.Com.': 'Phrynichus',
		'Phryn.Trag.': 'Phrynichus',
		'Phylarch.': 'Phylarchus',
		'Phylotim.': 'Phylotimus',
		'Pi.': 'Pindarus',
		'Pisand.': 'Pisander',
		'Pittac.': 'Pittacus',
		'Placit.': 'Placita Philosophorum',
		'Pl.Com.': 'Plato',
		'Pl.': 'Plato',
		'Pl.Jun.': 'Plato Junior',
		'Platon.': 'Platonius',
		'Plaut.': 'Plautus',
		'Plin.': 'Plinius',
		'Plot.': 'Plotinus',
		'Plu.': 'Plutarchus',
		'Poet. de herb.': 'Poeta',
		'Polem.Hist.': 'Polemo',
		'Polem.Phgn.': 'Polemo',
		'Polem.': 'Polemo Sophista',
		'Polioch.': 'Poliochus',
		'Poll.': 'Pollux',
		'Polyaen.': 'Polyaenus',
		'Plb.': 'Polybius',
		'Plb.Rh.': 'Polybius Sardianus',
		'Polycharm.': 'Polycharmus',
		'Polyclit.': 'Polyclitus',
		'Polycr.': 'Polycrates',
		'Polystr.': 'Polystratus',
		'Polyzel.': 'Polyzelus',
		'Pomp.': 'Pompeius',
		'Pomp.Mac.': 'Pompeius Macer',
		'Porph.': 'Porphyrius Tyrius',
		'Posidipp.': 'Posidippus',
		'Posidon.': 'Posidonius',
		'Pratin.': 'Pratinas',
		'Praxag.': 'Praxagoras',
		'Praxill.': 'Praxilla',
		'Priscian.': 'Priscianus',
		'Prisc.Lyd.': 'Priscianus Lydus',
		'Prisc.': 'Priscus',
		'Procl.': 'Proclus',
		'Procop.': 'Procopius Caesariensis',
		'Procop.Gaz.': 'Procopius Gazaeus',
		'Prodic.': 'Prodicus',
		'Promathid.': 'Promathidas',
		'Protag.': 'Protagoras',
		'Protagorid.': 'Protagoridas',
		'Proxen.': 'Proxenus',
		'Psalm.Solom.': 'Psalms of Solomon',
		'Ps.-Callisth.': 'Pseudo-Callisthenes',
		'Ps.-Phoc.': 'Pseudo-Phocylidea',
		'Ptol.': 'Ptolemaeus',
		'Ptol.Ascal.': 'Ptolemaeus Ascalonita',
		'Ptol.Chenn.': 'Ptolemaeus Chennos',
		'Ptol.Euerg.': 'Ptolemaeus Euergetes II',
		'Ptol.Megalop.': 'Ptolemaeus Megalopolitanus',
		'Pythaen.': 'Pythaenetus',
		'Pythag.': 'Pythagoras',
		'Pythag. Ep.': 'Pythagorae et Pythagoreorum Epistulae',
		'Pythocl.': 'Pythocles',
		'Quint.': 'Quintilianus',
		'Q.S.': 'Quintus Smyrnaeus',
		'Rh.': 'Rhetores Graeci',
		'Rhetor.': 'Rhetorius',
		'Rhian.': 'Rhianus',
		'Rhinth.': 'Rhinthon',
		'Rufin.': 'Rufinus',
		'Ruf.': 'Rufus',
		'Ruf.Rh.': 'Rufus',
		'Rutil.': 'Rutilius Lupus',
		'Tull.Sab.': 'Sabinus, Tullius',
		'Sacerd.': 'Sacerdos, Marius Plotius',
		'Sallust.': 'Sallustius',
		'Sannyr.': 'Sannyrio',
		'Sapph.': 'Sappho',
		'Satyr.': 'Satyrus',
		'Scol.': 'Scolia',
		'Scyl.': 'Scylax',
		'Scymn.': 'Scymnus',
		'Scythin.': 'Scythinus',
		'Secund.': 'Secundus',
		'Seleuc.': 'Seleucus',
		'Seleuc.Lyr.': 'Seleucus',
		'Semon.': 'Semonides',
		'Seren.': 'Serenus',
		'Serv.': 'Servius',
		'Sever.': 'Severus',
		'Sext.': 'Sextus',
		'S.E.': 'Sextus Empiricus',
		'Silen.': 'Silenus',
		'Simm.': 'Simmias',
		'Simon.': 'Simonides',
		'Simp.': 'Simplicius',
		'Simyl.': 'Simylus',
		'Socr.Arg.': 'Socrates Argivus',
		'Socr.Cous': 'Socrates Cous',
		'Socr.Rhod.': 'Socrates Rhodius',
		'Socr.': 'Socratis et Socraticorum Epistulae',
		'Sol.': 'Solon',
		'Sopat.': 'Sopater',
		'Sopat.Rh.': 'Sopater',
		'Sophil.': 'Sophilus',
		'S.': 'Sophocles',
		'Sophon': 'Sophonias',
		'Sophr.': 'Sophron',
		'Sor.': 'Soranus',
		'Sosib.': 'Sosibius',
		'Sosicr.': 'Sosicrates',
		'Sosicr.Hist.': 'Sosicrates',
		'Sosicr.Rhod.': 'Sosicrates Rhodius',
		'Sosip.': 'Sosipater',
		'Sosiph.': 'Sosiphanes',
		'Sosith.': 'Sositheus',
		'Sostrat.': 'Sostratus',
		'Sosyl.': 'Sosylus',
		'Sotad.Com.': 'Sotades',
		'Sotad.': 'Sotades',
		'Speus.': 'Speusippus',
		'Sphaer.Hist.': 'Sphaerus',
		'Sphaer.Stoic.': 'Sphaerus',
		'Stad.': 'Stadiasmus',
		'Staphyl.': 'Staphylus',
		'Stat.Flacc.': 'Statyllius Flaccus',
		'Steph.Com.': 'Stephanus',
		'Steph.': 'Stephanus',
		'St.Byz.': 'Stephanus Byzantius',
		'Stesich.': 'Stesichorus',
		'Stesimbr.': 'Stesimbrotus',
		'Sthenid.': 'Sthenidas',
		'Stob.': 'Stobaeus, Joannes',
		'Stoic.': 'Stoicorum Veterum Fragmenta',
		'Str.': 'Strabo',
		'Strato Com.': 'Strato',
		'Strat.': 'Strato',
		'Stratt.': 'Strattis',
		'Suet.': 'Suetonius',
		'Suid.': 'Suidas',
		'Sulp.Max.': 'Sulpicius Maximus',
		'Sus.': 'Susario',
		'Sm.': 'Symmachus',
		'Syn.Alch.': 'Synesius',
		'Syrian.': 'Syrianus',
		'Telecl.': 'Teleclides',
		'Telesill.': 'Telesilla',
		'Telest.': 'Telestes',
		'Ter.Maur.': 'Terentianus Maurus',
		'Ter.Scaur.': 'Terentius Scaurus',
		'Terp.': 'Terpander',
		'Thal.': 'Thales',
		'Theaet.': 'Theaetetus',
		'Theagen.': 'Theagenes',
		'Theag.': 'Theages',
		'Themiso Hist.': 'Themiso',
		'Them.': 'Themistius',
		'Themist.': 'Themistocles',
		'Theocl.': 'Theocles',
		'Theoc.': 'Theocritus',
		'Theodect.': 'Theodectes',
		'Theodorid.': 'Theodoridas',
		'Theod.': 'Theodorus',
		'Theodos.': 'Theodosius Alexandrinus',
		'Thd.': 'Theodotion',
		'Theognet.': 'Theognetus',
		'Thgn.': 'Theognis',
		'Thgn.Trag.': 'Theognis',
		'Thgn.Hist.': 'Theognis Rhodius',
		'Theognost.': 'Theognostus',
		'Theol.Ar.': 'Theologumena Arithmeticae',
		'Theolyt.': 'Theolytus',
		'Theon Gymn.': 'Theon Gymnasiarcha',
		'Theo Sm.': 'Theon Smyrnaeus',
		'Theoph.': 'Theophanes',
		'Theophil.': 'Theophilus',
		'Thphr.': 'Theophrastus',
		'Theopomp.Com.': 'Theopompus',
		'Theopomp.Hist.': 'Theopompus',
		'Theopomp.Coloph.': 'Theopompus Colophonius',
		'Thom.': 'Thomas',
		'Thom.Mag.': 'Thomas Magister',
		'Thrasym.': 'Thrasymachus',
		'Th.': 'Thucydides',
		'Thugen.': 'Thugenides',
		'Thyill.': 'Thyillus',
		'Thymocl.': 'Thymocles',
		'Tib.': 'Tiberius',
		'Tib.Ill.': 'Tiberius Illustrius',
		'Tim.': 'Timaeus',
		'Timae.': 'Timaeus',
		'Ti.Locr.': 'Timaeus Locrus',
		'Timag.': 'Timagenes',
		'Timocl.': 'Timocles',
		'Timocr.': 'Timocreon',
		'Timostr.': 'Timostratus',
		'Tim.Com.': 'Timotheus',
		'Tim.Gaz.': 'Timotheus Gazaeus',
		'Titanomach.': 'Titanomachia',
		'Trag.Adesp.': 'Tragica Adespota',
		'Trophil.': 'Trophilus',
		'Tryph.': 'Tryphiodorus',
		'Tull.Flacc.': 'Tullius Flaccus',
		'Tull.Gem.': 'Tullius Geminus',
		'Tull.Laur.': 'Tullius Laurea',
		'Tymn.': 'Tymnes',
		'Tyrt.': 'Tyrtaeus',
		'Tz.': 'Tzetzes, Joannes',
		'Ulp.': 'Ulpianus',
		'Uran.': 'Uranius',
		'Vel.Long.': 'Velius Longus',
		'Vett.Val.': 'Vettius Valens',
		'LXX': 'Vetus Testamentum Graece redditum',
		'Vit.Philonid.': 'Vita Philonidis Epicurei',
		'Vit.Hom.': 'Vitae Homeri',
		'Vitr.': 'Vitruvius',
		'Xanth.': 'Xanthus',
		'Xenag.': 'Xenagoras',
		'Xenarch.': 'Xenarchus',
		'Xenocl.': 'Xenocles',
		'Xenocr.': 'Xenocrates',
		'Xenoph.': 'Xenophanes',
		'X.': 'Xenophon',
		'X.Eph.': 'Xenophon Ephesius',
		'Zaleuc.': 'Zaleucus',
		'Zelot.': 'Zelotus',
		'ZenoStoic.': 'Zeno Citieus',
		'Zeno Eleat.': 'Zeno Eleaticus',
		'Zeno Tars.Stoic.': 'Zeno Tarsensis',
		'Zen.': 'Zenobius',
		'Zenod.': 'Zenodotus',
		'Zonae.': 'Zonaeus',
		'Zonar.': 'Zonaras',
		'Zon.': 'Zonas',
		'Zopyr.Hist.': 'Zopyrus',
		'Zopyr.': 'Zopyrus',
		'Zos.Alch.': 'Zosimus',
		'Zos.': 'Zosimus',
	}

	return authordict


def deabrevviatelatinauthors() -> Dict[str, str]:
	"""

	the latin dictionary xml does not help you to generate this dict

	:return:
	"""

	authordict = {
		'Amm.': 'Ammianus',
		'Anthol. Lat.': 'Latin Anthology',
		'App.': 'Apuleius',
		'Auct. Her.': 'Rhetorica ad Herennium',
		'Caes.': 'Caesar',
		'Cat.': 'Catullus',
		'Cassiod.': 'Cassiodorus',
		'Cels.': 'Celsus',
		'Charis.': 'Charisius',
		'Cic.': 'Cicero',
		'Col.': 'Columella',
		'Curt.': 'Quintus Curtius Rufus',
		'Dig.': 'Digest of Justinian',
		'Enn.': 'Ennius',
		'Eutr.': 'Eutropius',
		'Fest.': 'Festus',
		'Flor.': 'Florus',
		'Front.': 'Frontinus',
		'Gell.': 'Gellius',
		'Hirt.': 'Hirtius',
		'Hor.': 'Horace',
		'Hyg.': 'Hyginus',
		'Isid.': 'Isidore',
		'Just.': 'Justinian',
		'Juv.': 'Juvenal',
		'Lact.': 'Lactantius',
		'Liv.': 'Livy',
		'Luc.': 'Lucan',
		'Lucr.': 'Lucretius',
		'Macr.': 'Macrobius',
		'Mart.': 'Martial',
		'Nep.': 'Nepos',
		'Non.': 'Nonius',
		'Ov.': 'Ovid',
		'Pall.': 'Palladius',
		'Pers.': 'Persius',
		'Petr.': 'Petronius',
		'Phaedr.': 'Phaedrus',
		'Plaut.': 'Plautus',
		'Plin.': 'Pliny',
		'Prop.': 'Propertius',
		'Quint.': 'Quintilian',
		'Sall.': 'Sallust',
		'Sen.': 'Seneca',
		'Sil.': 'Silius Italicus',
		'Stat.': 'Statius',
		'Suet.': 'Suetonius',
		'Tac.': 'Tacitus',
		'Ter.': 'Terence',
		'Tert.': 'Tertullian',
		'Tib.': 'Tibullus',
		'Val. Fl.': 'Valerius Flaccus',
		'Val. Max.': 'Valerius Maxiumus',
		'Varr.': 'Varro',
		'Vell.': 'Velleius',
		'Verg.': 'Vergil',
		'Vitr.': 'Vitruvius',
		'Vulg.': 'Latin Vulgate Bible'
	}

	return authordict


def unpackcommonabbreviations(potentialabbreviaiton: str, furtherunpack: bool) -> str:
	"""
	turn an abbreviation into its headword: prid -> pridie

	it is important to avoid getting greedy in here: feed this via failed headword indices and the '•••unparsed•••'
	segment that follows

	a vector run has already turned 'm.' into Marcus via cleantext(), so it is safe to turn 'm' into 'mille'

	:param potentialabbreviaiton:
	:param furtherunpack:
	:return:
	"""

	abbreviations = {
		'sal': 'salutem',
		'prid': 'pridie',
		'kal': 'kalendae',
		'pl': 'plebis',
		'hs': 'sestertius',
		'sext': 'sextilis',
		'ian': 'ianuarius',
		'febr': 'februarius',
		'mart': 'martius',
		'apr': 'aprilis',
		'mai': 'maius',
		'quint': 'quintilis',
		'sept': 'september',
		'oct': 'october',
		'nou': 'nouembris',
		'dec': 'december',
		# 'iul': 'Julius',
		'imp': 'imperator',
		'design': 'designatus',
		'tr': 'tribunus',
		't': 'Titus',
		'cn': 'gnaeus',
		'gn': 'gnaeus',
		'q': 'quintus',
		's': 'sextus',
		'p': 'publius',
		'iii': 'tres',
		'iiii': 'quattor',
		'iu': 'quattor',
		'u': 'quinque',
		'ui': 'sex',
		'uii': 'septem',
		'uiii': 'octo',
		'uiiii': 'nouem',
		'ix': 'nouem',
		'x': 'decem',
		'xi': 'undecim',
		'xii': 'duodecim',
		'xiii': 'tredecim',
		'xiiii': 'quattuordecim',
		'xiu': 'quattuordecim',
		'xu': 'quindecim',
		'xui': 'sedecim',
		'xuii': 'septemdecim',
		'xuiii': 'dudeuiginti',
		'xix': 'unodeuiginti',
		'xx': 'uiginti',
		'xxx': 'triginta',
		'xl': 'quadraginta',
		# or is it 'lucius'...?
		# 'l': 'quinquaginta',
		'lx': 'sexaginta',
		'lxx': 'septuaginta',
		'lxxx': 'octoginta',
		'xc': 'nonaginta',
		'cc': 'ducenti',
		'ccc': 'trecenti',
		'cccc': 'quadrigenti',
		'cd': 'quadrigenti',
		'dc': 'sescenti',
		'dcc': 'septigenti',
		'dccc': 'octigenti',
		'cm': 'nongenti',
		'coss': 'consul',
		'cos': 'consul',
		'desig': 'designatus',
		'ser': 'seruius',
		'fab': 'fabius',
		'ap': 'appius',
		'sp': 'spurius',
		'leg': 'legatus',
		'ti': 'tiberius',
		'n.': 'numerius',
		'r': 'res',
		'f': 'filius',
		'mod': 'modius'
	}

	furtherabbreviations = {
		'm': 'mille',
		'c': 'centum',
		'l': 'quinquaginta',
	}

	# the following should be added to the db instead...
	morphsupplements = {
		# a candidate for addition to the dictionary...; cf. poëta
		'xuiri': 'decemuiri',
		'xuiros': 'decemviros',
		'xuiris': 'decemviris',
		# add to morph table... [index to galen helps you grab this]
		'τουτέϲτιν': 'τουτέϲτι',
		'κᾄν': 'ἄν',
		'κᾀν': 'ἄν',
		'κᾀπί': 'ἐπὶ',
		'κᾀκ': 'ἐκ',
		'κᾀξ': 'ἐκ',
		'κᾀνταῦθα': 'ἐνταῦθα',
		'κᾀπειδάν': 'ἐπειδάν',
		'κᾄπειθ': 'ἔπειτα',
		'κᾄπειτα': 'ἔπειτα',
		'κᾄπειτ': 'ἔπειτα',
		'κᾀγώ': 'ἐγώ',
	}

	abbreviations = {**abbreviations, **morphsupplements}

	if furtherunpack:
		abbreviations = {**abbreviations, **furtherabbreviations}

	try:
		word = abbreviations[potentialabbreviaiton]
	except KeyError:
		word = potentialabbreviaiton

	return word

def polytonicsort(unsortedwords: list) -> list:
	"""
	sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	stripping diacriticals can help this, but then you get words that collide
	gotta jump through some extra hoops

		[a] build an unaccented copy of the word in front of the word
		[b] substitute sigmas for lunate sigmas (because lunate comes after omega...)
			θαλαττησ-snip-θαλάττηϲ
		[c] sort the augmented words (where ά and ᾶ only matter very late in the game)
		[d] remove the augment
		[e] return

	:param unsortedwords:
	:return:
	"""

	transtable = buildhipparchiatranstable()

	stripped = [re.sub(r'ϲ', r'σ', stripaccents(word, transtable)) + '-snip-' + word for word in unsortedwords if word]

	stripped = sorted(stripped)

	snipper = re.compile(r'(.*?)(-snip-)(.*?)')

	sortedversion = [re.sub(snipper, r'\3', word) for word in stripped]

	return sortedversion

def buildhipparchiatranstable() -> dict:
	"""

	pulled this out of stripaccents() so you do not maketrans 200k times when
	polytonicsort() sifts an index

	:return:
	"""
	invals = list()
	outvals = list()

	invals.append('ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰά')
	outvals.append('α' * len(invals[-1]))
	invals.append('ἐἑἒἓἔἕὲέ')
	outvals.append('ε' * len(invals[-1]))
	invals.append('ἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐ')
	outvals.append('ι' * len(invals[-1]))
	invals.append('ὀὁὂὃὄὅόὸ')
	outvals.append('ο' * len(invals[-1]))
	invals.append('ὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺ')
	outvals.append('υ' * len(invals[-1]))
	invals.append('ᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧ')
	outvals.append('η' * len(invals[-1]))
	invals.append('ὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ')
	outvals.append('ω' * len(invals[-1]))

	invals.append('ᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ')
	outvals.append('α'*len(invals[-1]))
	invals.append('ἘἙἚἛἜἝΕ')
	outvals.append('ε' * len(invals[-1]))
	invals.append('ἸἹἺἻἼἽἾἿΙ')
	outvals.append('ι' * len(invals[-1]))
	invals.append('ὈὉὊὋὌὍΟ')
	outvals.append('ο' * len(invals[-1]))
	invals.append('ὙὛὝὟΥ')
	outvals.append('υ' * len(invals[-1]))
	invals.append('ᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯΗ')
	outvals.append('η' * len(invals[-1]))
	invals.append('ᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯ')
	outvals.append('ω' * len(invals[-1]))
	invals.append('ῤῥῬ')
	outvals.append('ρρρ')
	invals.append('ΒΨΔΦΓΞΚΛΜΝΠϘΡσΣςϹΤΧΘΖ')
	outvals.append('βψδφγξκλμνπϙρϲϲϲϲτχθζ')

	# some of the vowels with quantities are compounds of vowel + accent: can't cut and paste them into the xformer
	invals.append('vUJjÁÄáäÉËéëÍÏíïÓÖóöÜÚüúăāĕēĭīŏōŭū')
	outvals.append('uVIiaaaaeeeeiiiioooouuuuaaeeiioouu')

	invals = str().join(invals)
	outvals = str().join(outvals)

	transtable = str.maketrans(invals, outvals)

	return transtable


def stripaccents(texttostrip: str, transtable=None) -> str:
	"""

	turn ᾶ into α, etc

	there are more others ways to do this; but this is the fast way
	it turns out that this was one of the slowest functions in the profiler

	transtable should be passed here outside of a loop
	but if you are just doing things one-off, then it is fine to have
	stripaccents() look up transtable itself

	:param texttostrip:
	:param transtable:
	:return:
	"""

	# if transtable == None:
	# 	transtable = buildhipparchiatranstable()

	try:
		stripped = texttostrip.translate(transtable)
	except TypeError:
		stripped = stripaccents(texttostrip, transtable=buildhipparchiatranstable())

	return stripped

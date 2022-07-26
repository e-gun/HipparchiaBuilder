# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


def greektranslationtagrepairs(lexicalentry: str) -> str:
	"""

	you can get 'as' or 'if' or whatever as a translation for a word because the tags can be oddly placed

	exx of botched translation tags

		τοϲοῦτοϲ
		<foreign lang="greek">μεγάθεα τοϲοῦτοι</foreign> <trans>so</trans> big, <bibl n="Perseus:abo:tlg,0016,001:7:103" default="NO" valid="yes">

		πρᾶγμα
		<foreign lang="greek">τὰ π.</foreign> alone, oneʼs <trans>all,</trans> oneʼs <trans>fortunes,</trans> <cit><quote lang="greek">ἐν ᾧπέρ ἐϲτι πάντα μοι

	the real shape is
		</foreign> <trans> ...,</trans>

	the comma is the close

	but note the problems when you look at what a valid version might say:

	τρόποϲ
		OK
			commonly, <trans>way, manner, fashion, guise,</trans> <foreign lang="greek">τρόπῳ τῷ παρεόντι χρεώμενοι</foreign> going on <trans>as we are,</trans> ib.

		Not-OK
			<foreign lang="greek">παντὶ τ.</foreign> <trans>by</trans> all <trans>means,</trans>


	hits for foreigntransbibl look like:
	('<foreign lang="greek">τρόπῳ τῷ παρεόντι χρεώμενοι</foreign> ', 'going on <trans>as we are,</trans> ib.', '<bibl')
	('<foreign lang="greek">κεχώριϲται τοὺϲ τ.</foreign> ', 'in its <trans>ways,</trans> in its <trans>kind,</trans> ', '<bibl')
	('<foreign lang="greek">ἑνί γέ τῳ τ.</foreign> ', '<trans>in</trans> one <trans>way</trans> or other, ', '<bibl')
	('<foreign lang="greek">παντὶ τ.</foreign> ', '<trans>by</trans> all <trans>means,</trans> ', '<bibl')


	another problem comes at the head of an entry:

	<sense id="n79983.0" n="A" level="1" opt="n"><trans>have</trans> something <trans>done to one, suffer</trans>, opp. <trans>do</trans>, <cit><quote lang="greek">ὅϲϲʼ ἔρξαν τʼ ἔπαθόν τε</quote>

	Latin dictionary has the same issue, but different tagging:

		<sense id="n3551.0" n="I" level="1" opt="n"> <hi rend="ital">Of</hi> or <hi rend="ital">from silver</hi>, <hi rend="ital">made of silver</hi> (cf. argentum, I. A.): polubrum, Liv. And. ap. <bibl default="NO"

	:param lexicalentry:
	:return:
	"""

	# opening/closing a tag is a blocker: [^<]
	foreigntransbibl = re.compile(r'(<foreign[^<]*?</foreign>\s)([^<]*?<trans>.*?)(<bibl)')
	# sensetranscit = re.compile(r'(<sense[^<]*?>)(<trans>.*?)(<cit|<auth|<bibl)')
	# A.1 should be the top definition
	sensetranscit = re.compile(r'(<sense id=".*?" n="A" level="1" opt=".">)(<trans>.*?)([.,;:()]|<cit|<auth|<bibl)')

	newlex = re.sub(foreigntransbibl, greektransphrasehelper, lexicalentry)
	newlex = re.sub(sensetranscit, greekuntaggedtransphrasehelper, newlex)

	# might have grabbed and tagged some greek, etc.
	# <trans class="rewritten phrase">humanity</trans>, <trans class="rewritten phrase"><cit><quote lang="greek">ἀπώλεϲαϲ τὸν ἄ.</trans>, <trans class="rewritten phrase">οὐκ ἐπλήρωϲαϲ τὴν ἐπαγγελίαν</quote></trans>
	overzealous = re.compile(r'<trans class="rewritten phrase">(<cit><quote.*?</quote>)</trans>')
	newlex = re.sub(overzealous, r'\1', newlex)

	#  <cit><quote lang="greek">ἀπώλεϲαϲ τὸν ἄ.</trans>, <trans class="rewritten phrase">οὐκ ἐπλήρωϲαϲ τὴν ἐπαγγελίαν</quote>
	overzealous = re.compile(r'(<cit><quote)(.*?)(</quote>)')
	newlex = re.sub(overzealous, overzealoushelper, newlex)

	return newlex


def greekuntaggedtransphrasehelper(regexmatch) -> str:
	"""

	same as next but skip the tagging as "rewritten"

	used at entry heads and so adding the check to strip greek tags
	but these can probably be dropped

	:param regexmatch:
	:return:
	"""

	newtext = greektransphrasehelper(regexmatch, classing=False)
	# newtext = re.sub(r'<foreign lang="greek">(.*?)</foreign>', r'\1', newtext)
	# newtext = re.sub(r'<etym lang="greek">(.*?)</etym>', r'\1', newtext)

	return newtext


def greektransphrasehelper(regexmatch, classing=True) -> str:
	"""

	turn something like
		<trans>in</trans> a <trans>manner,</trans>
	into
		<trans>in a manner,</trans>

	:param regexmatch:
	:return:
	"""

	if classing:
		c = ' rewritten="phrase"'
	else:
		c = str()

	leading = regexmatch.group(1)
	trailing = regexmatch.group(3)
	transgroup = regexmatch.group(2)

	transgroup = re.sub(r'<(|/)trans>', str(), transgroup)
	transgroup = transgroup.split(',')

	transgroup = ['<trans{c}>{t}</trans>'.format(c=c, t=t.strip()) for t in transgroup if t]
	transgroup = ', '.join(transgroup)
	transgroup = re.sub(r'<trans{c}></trans>'.format(c=c), str(), transgroup)

	newtext = leading + transgroup + trailing

	return newtext


def overzealoushelper(regexmatch) -> str:
	"""

	strip out <trans> tags from a block

	:param regexmatch:
	:return:
	"""

	leading = regexmatch.group(1)
	trailing = regexmatch.group(3)
	stripgroup = regexmatch.group(2)

	stripgroup = re.sub(r'<trans class="rewritten phrase">', str(), stripgroup)
	stripgroup = re.sub(r'</trans>', str(), stripgroup)

	newtext = leading + stripgroup + trailing

	return newtext


def latintranslationtagrepairs(lexicalentry: str) -> str:
	"""

	very parallel to the greek version, but the tagging is different

	there is an elegant way to avoid tow near clone functions, but the builder is seldom elegant

	Latin dictionary has the same issue, but different tagging:

		<sense id="n3551.0" n="I" level="1" opt="n"> <hi rend="ital">Of</hi> or <hi rend="ital">from silver</hi>, <hi rend="ital">made of silver</hi> (cf. argentum, I. A.): polubrum, Liv. And. ap. <bibl default="NO"

	:param lexicalentry:
	:return:
	"""

	# I.1 should be the top definition
	sensetranscit = re.compile(r'(<sense id=".*?" n="I" level="1" opt=".">) (<hi rend="ital">.*?)([.,;:()]|<cit|<auth|<bibl)')
	# the version without a whitespace...
	altsense = re.compile(r'(<sense id=".*?" n="I" level="1" opt=".">)(<hi rend="ital">.*?)([.,;:()]|</sense>|<cit|<auth|<bibl)')

	newlex = re.sub(sensetranscit, lainttransphrasehelper, lexicalentry)
	newlex = re.sub(altsense, lainttransphrasehelper, newlex)

	# some punctuation might have gotten on the wrong side of a bracket
	newlex = re.sub(r'<hi rend="ital">,\s', r', <hi rend="ital">', newlex)

	return newlex


falsetrans = {'Act', 'Pass', 'Lit', 'Prop', 'Fig', 'Neutr', 'Trop'}


def lainttransphrasehelper(regexmatch, classing=False) -> str:
	"""

	tricky items like:

		<hi rend="ital">Act., to make something sound, make a noise with, cause to resound</hi>

	this will 'split' on 'Act.'

	:param regexmatch:
	:param classing:
	:return:
	"""

	if classing:
		c = ' rewritten="phrase"'
	else:
		c = str()


	leading = regexmatch.group(1)
	trailing = regexmatch.group(3)
	transgroup = regexmatch.group(2)

	if re.sub(r'<hi rend="ital">', str(), transgroup) in falsetrans:
		t = str()
		while re.search(r'^[.,;:()]', trailing):
			p = re.findall(r'^[.,;:()]', trailing)
			t = t + p[0]
			trailing = re.sub(r'^[.,;:()]', str(), trailing)
		tg = re.sub(r'<hi rend="ital">', str(), transgroup) + '{t}<hi rend="ital">'.format(t=t)
		trailing = re.sub(r'^\.', str(), trailing)
		return leading + tg + trailing

	transgroup = re.sub(r'<hi rend="ital">', str(), transgroup)
	transgroup = re.sub(r'</hi>', str(), transgroup)
	transgroup = transgroup.split(',')

	transgroup = ['<hi rend="ital"{c}>{t}</hi>'.format(c=c, t=t.strip()) for t in transgroup if t]
	transgroup = ', '.join(transgroup)
	transgroup = re.sub(r'<hi rend="ital"{c}></hi>'.format(c=c), str(), transgroup)

	newtext = leading + transgroup + trailing

	return newtext


# from builder.lexica.testentries import testo as test
#
# print(latintranslationtagrepairs(test))

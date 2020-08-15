# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
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
	sensetranscit = re.compile(r'(<sense id=".*?" n="A" level="1" opt=".">)(<trans>.*?)(<cit|<auth|<bibl)')

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
		c = ' class="rewritten phrase"'
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


# tropos = """
# hipparchiaDB=# select entry_body from greek_dictionary where entry_name='τρόποϲ';
# <head extent="full" lang="greek" opt="n" orth_orig="τρόποϲ">τρόποϲ</head>, <gen lang="greek" opt="n">ὁ</gen>, (<etym lang="greek" opt="n">τρέπω</etym>) <sense id="n105531.0" n="A" level="1" opt="n"><trans>turn, direction, way,</trans> <cit><quote lang="greek">διώρυχεϲ παντοίουϲ τρόπουϲ ἔχουϲαι</quote> <bibl n="Perseus:abo:tlg,0016,001:2:108" default="NO" valid="yes"><author>Hdt.</author> 2.108</bibl></cit>; <cit><quote lang="greek">διώρυχαϲ τετραμμέναϲ πάντα τ.</quote> <bibl n="Perseus:abo:tlg,0016,001:1:189" default="NO" valid="yes"><author>Id.</author> 1.189</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0016,001:199" default="NO" valid="yes">199</bibl>: but, </sense><sense n="II" id="n105531.1" level="2" opt="n"> commonly, <trans>way, manner, fashion, guise,</trans> <foreign lang="greek">τρόπῳ τῷ παρεόντι χρεώμενοι</foreign> going on <trans>as we are,</trans> ib.<bibl n="Perseus:abo:tlg,0016,001:97" default="NO" valid="yes">97</bibl>; <cit><quote lang="greek">τ. ὑποδημάτων Κρητικόϲ</quote> <bibl n="Perseus:abo:tlg,0627,010:62" default="NO"><author>Hp.</author> <title>Art.</title> 62</bibl></cit>; <cit><quote lang="greek">πᾶϲ τ. μορφῆϲ</quote> <bibl n="Perseus:abo:tlg,0085,007:192" default="NO" valid="yes"><author>A.</author> <title>Eu.</title> 192</bibl></cit>; <cit><quote lang="greek">τίϲ ὁ τ. τῆϲ ξυμφορᾶϲ;</quote> <bibl n="Perseus:abo:tlg,0011,004:99" default="NO" valid="yes"><author>S.</author> <title>OT</title> 99</bibl></cit>; <cit><quote lang="greek">ἀϲκεῖν τὸν υἱὸν τὸν ἐπιχώριον τ.</quote> <bibl n="Perseus:abo:tlg,0019,011:47" default="NO" valid="yes"><author>Ar.</author> <title>Pl.</title> 47</bibl></cit>; <cit><quote lang="greek">ὁ αὐτόϲ που τ. τέχνηϲ ἰατρικῆϲ ὅϲπερ καὶ ῥητορικῆϲ</quote> <bibl n="Perseus:abo:tlg,0059,012:270b" default="NO" valid="yes"><author>Pl.</author> <title>Phdr.</title> 270b</bibl></cit>; <trans>tenor,</trans> of documents, <bibl n="Perseus:abo:pap,P.Gen.:16:11" default="NO"><title>PGen.</title> 16.11</bibl> <date>(iii A. D.)</date>, etc.: also in <author>Pl.</author>, <foreign lang="greek">κεχώριϲται τοὺϲ τ.</foreign> in its <trans>ways,</trans> in its <trans>kind,</trans> <bibl n="Perseus:abo:tlg,0016,001:4:28" default="NO" valid="yes"><author>Hdt.</author> 4.28</bibl>; <cit><quote lang="greek">ψυχῆϲ τρποι</quote> <bibl n="Perseus:abo:tlg,0059,030:445c" default="NO" valid="yes"><author>Pl.</author> <title>R.</title> 445c</bibl></cit>, etc.; <cit><quote lang="greek">οἱ περὶ τὴν ψυχὴν τ.</quote> <bibl n="Perseus:abo:tlg,0086,014:588a:20" default="NO"><author>Arist.</author> <title>HA</title> 588a20</bibl></cit>:—in various adverbial usages: </sense><sense n="1" id="n105531.2" level="3" opt="n"> dat., <cit><quote lang="greek">τίνι τρόπῳ;</quote> <trans>how?</trans> <bibl n="Perseus:abo:tlg,0085,002:793" default="NO" valid="yes"><author>A.</author> <title>Pers.</title> 793</bibl></cit>, <bibl n="Perseus:abo:tlg,0011,004:10" default="NO" valid="yes"><author>S.</author> <title>OT</title> 10</bibl>, <bibl n="Perseus:abo:tlg,0006,050:1294" default="NO" valid="yes"><author>E.</author> <title>Ba.</title> 1294</bibl>; <cit><quote lang="greek">τῷ τ.;</quote> <bibl n="Perseus:abo:tlg,0011,005:679" default="NO" valid="yes"><author>S.</author> <title>El.</title> 679</bibl></cit>, <bibl n="Perseus:abo:tlg,0006,038:909" default="NO" valid="yes"><author>E.</author> <title>Hipp.</title> 909</bibl>, <bibl n="Perseus:abo:tlg,0006,005:1008" default="NO" valid="yes">1008</bibl>; <cit><quote lang="greek">ποίῳ τ.;</quote> <bibl n="Perseus:abo:tlg,0085,003:763" default="NO" valid="yes"><author>A.</author> <title>Pr.</title> 763</bibl></cit>, etc.; <foreign lang="greek">τοιούτῳ τ., τ. τοιῷδε,</foreign> <bibl n="Perseus:abo:tlg,0016,001:1:94" default="NO" valid="yes"><author>Hdt.</author> 1.94</bibl>, <bibl n="Perseus:abo:tlg,0016,001:3:68" default="NO" valid="yes">3.68</bibl>; <cit><quote lang="greek">ἄλλῳ τ.</quote> <bibl n="Perseus:abo:tlg,0059,012:232b" default="NO" valid="yes"><author>Pl.</author> <title>Phdr.</title> 232b</bibl></cit>, etc.; <foreign lang="greek">ἑνί γέ τῳ τ.</foreign> <trans>in</trans> one <trans>way</trans> or other, <bibl n="Perseus:abo:tlg,0019,011:402" default="NO" valid="yes"><author>Ar.</author> <title>Pl.</title> 402</bibl>, <bibl n="Perseus:abo:tlg,0059,024:96d" default="NO" valid="yes"><author>Pl.</author> <title>Men.</title> 96d</bibl>; <foreign lang="greek">παντὶ τ.</foreign> <trans>by</trans> all <trans>means,</trans> <bibl n="Perseus:abo:tlg,0085,004:301" default="NO" valid="yes"><author>A.</author> <title>Th.</title> 301</bibl> (lyr.), <bibl n="Perseus:abo:tlg,0540,013:25" default="NO" valid="yes"><author>Lys.</author> 13.25</bibl>; <foreign lang="greek">οὐδενὶ τ., μηδενὶ τ.,</foreign> <trans>in</trans> no <trans>wise, by</trans> no <trans>means, on</trans> no <trans>account,</trans> <bibl n="Perseus:abo:tlg,0016,001:4:111" default="NO" valid="yes"><author>Hdt.</author> 4.111</bibl>, <bibl n="Perseus:abo:tlg,0003,001:6:35" default="NO" valid="yes"><author>Th.</author> 6.35</bibl>, <bibl n="Perseus:abo:tlg,0059,003:49a" default="NO" valid="yes"><author>Pl.</author> <title>Cri.</title> 49a</bibl>, etc.; <foreign lang="greek">ἑκουϲίῳ τ.</foreign> willingly, <bibl n="Perseus:abo:tlg,0006,036:751" default="NO" valid="yes"><author>E.</author> <title>Med.</title> 751</bibl>; <foreign lang="greek">τρόπῳ φρενόϲ</foreign> by <trans>way</trans> of intelligence, i.e. in lieu of the intelligence which is lacking to the child, <bibl n="Perseus:abo:tlg,0085,006:754" default="NO" valid="yes"><author>A.</author> <title>Ch.</title> 754</bibl> (s. v.l.): poet. in pl., <cit><quote lang="greek">τρόποιϲι ποίοιϲ;</quote> <bibl n="Perseus:abo:tlg,0011,007:468" default="NO" valid="yes"><author>S.</author> <title>OC</title> 468</bibl></cit>; <foreign lang="greek">τρόποιϲιν οὐ τυραννικοῖϲ</foreign> not after <trans>the fashion</trans> of . . , <bibl n="Perseus:abo:tlg,0085,006:479" default="NO" valid="yes"><author>A.</author> <title>Ch.</title> 479</bibl>; <cit><quote lang="greek">ναυκλήρου τρόποιϲ</quote> <bibl n="Perseus:abo:tlg,0011,006:128" default="NO" valid="yes"><author>S.</author> <title>Ph.</title> 128</bibl></cit>. </sense><sense n="2" id="n105531.3" level="3" opt="n"> abs. in acc., <cit><quote lang="greek">τίνα τρόπον;</quote> <trans>how?</trans> <bibl n="Perseus:abo:tlg,0019,003:170" default="NO" valid="yes"><author>Ar.</author> <title>Nu.</title> 170</bibl></cit>, <bibl n="Perseus:abo:tlg,0019,009:460" default="NO" valid="yes"><title>Ra.</title> 460</bibl>; <foreign lang="greek">τ. τινά</foreign> <trans>in</trans> a <trans>manner,</trans> <bibl n="Perseus:abo:tlg,0006,038:1300" default="NO" valid="yes"><author>E.</author> <title>Hipp.</title> 1300</bibl>, <bibl n="Perseus:abo:tlg,0059,030:432e" default="NO" valid="yes"><author>Pl.</author> <title>R.</title> 432e</bibl>; <foreign lang="greek">τοῦτον τὸν τ., τόνδε τὸν τ.,</foreign> <bibl n="Perseus:abo:tlg,0059,011:199a" default="NO" valid="yes"><author>Id.</author> <title>Smp.</title> 199a</bibl>, <bibl n="Perseus:abo:tlg,0032,006:1:1:9" default="NO" valid="yes"><author>X.</author> <title>An.</title> 1.1.9</bibl>; <cit><quote lang="greek">ὃν τ.</quote> <trans>how,</trans> <bibl n="Perseus:abo:tlg,0081,001:3:8" default="NO"><author>D.H.</author> 3.8</bibl></cit>; <trans>as,</trans> <bibl n="Perseus:abo:tlg,0527,027:41(42).1" default="NO" valid="yes"><author>LXX</author><title>Ps.</title> 41(42).1</bibl>; <cit><quote lang="greek">τ. τὸν αὐτόν</quote> <bibl n="Perseus:abo:tlg,0085,006:274" default="NO" valid="yes"><author>A.</author> <title>Ch.</title> 274</bibl></cit>; <cit><quote lang="greek">πάντα τ.</quote> <bibl n="Perseus:abo:tlg,0019,003:700" default="NO" valid="yes"><author>Ar.</author> <title>Nu.</title> 700</bibl></cit> (lyr.), etc.; <cit><quote lang="greek">μηδένα τ.</quote> <bibl n="Perseus:abo:tlg,0032,002:3:7:8" default="NO" valid="yes"><author>X.</author> <title>Mem.</title> 3.7.8</bibl></cit>; <foreign lang="greek">τὸν μέγαν τ., οὐ ϲμικρὸν τ.,</foreign> <bibl n="Perseus:abo:tlg,0085,004:284" default="NO" valid="yes"><author>A.</author> <title>Th.</title> 284</bibl>,<bibl n="Perseus:abo:tlg,0085,004:465" default="NO" valid="yes">465</bibl>; <cit><quote lang="greek">τὸν Ἀργείων τ.</quote> <bibl n="Perseus:abo:tlg,0033,004:6(5).58" default="NO" valid="yes"><author>Pi.</author> <title>I.</title> 6(5).58</bibl></cit>; <cit><quote lang="greek">Ϲαμιακὸν τ.</quote> <bibl n="Perseus:abo:tlg,0434,001:13" default="NO"><author>Cratin.</author> 13</bibl></cit>; <foreign lang="greek">βάρβαρον τ. </foreign> (<foreign lang="greek">βρόμον</foreign> ex Sch. Schütz) <trans>in</trans> barbarous <trans>guise</trans> or <trans>fashion,</trans> <bibl n="Perseus:abo:tlg,0085,004:463" default="NO" valid="yes"><author>A.</author> <title>Th.</title> 463</bibl>; <foreign lang="greek">πίτυοϲ τρόπον</foreign> <trans>after the manner</trans> of a pine, <bibl n="Perseus:abo:tlg,0016,001:6:37" default="NO" valid="yes"><author>Hdt.</author> 6.37</bibl>; <foreign lang="greek">ὄρνιθοϲ τ.</foreign> <trans>like</trans> a bird, <bibl n="Perseus:abo:tlg,0016,001:2:57" default="NO" valid="yes"><author>Id.</author> 2.57</bibl>, cf. <bibl n="Perseus:abo:tlg,0085,005:49" default="NO" valid="yes"><author>A.</author> <title>Ag.</title> 49</bibl> (anap.), <bibl n="Perseus:abo:tlg,0085,005:390" default="NO" valid="yes">390</bibl> (lyr.), etc.; later, <cit><quote lang="greek">ἐϲ ὄρνιθοϲ τ.</quote> <bibl n="Perseus:abo:tlg,0061,004:1" default="NO"><author>Luc.</author> <title>Halc.</title> 1</bibl></cit>, cf. <trans>Bis Acc.</trans><bibl n="Perseus:abo:tlg,0061,004:27" default="NO">27</bibl>: rarely in pl., <foreign lang="greek">πάνταϲ τρόπουϲ</foreign> in all <trans>ways,</trans> <bibl n="Perseus:abo:tlg,0059,004:94d" default="NO" valid="yes"><author>Pl.</author> <title>Phd.</title> 94d</bibl>. </sense><sense n="3" id="n105531.4" level="3" opt="n"> with Preps., <foreign lang="greek">τὸν ἐγκώμιον ἀμφὶ τρόπον</foreign> in <trans>way</trans> of praise, <bibl n="Perseus:abo:tlg,0033,001:10(11).77" default="NO" valid="yes"><author>Pi.</author> <title>O.</title> 10(11).77</bibl>:—<cit><quote lang="greek">διʼ οὗ τρόπου</quote> <bibl n="Perseus:abo:tlg,0541,001:539:6" default="NO"><author>Men.</author> 539.6</bibl></cit>; <cit><quote lang="greek">διὰ τοιούτου τ.</quote> <bibl n="Perseus:abo:tlg,0060,001:1:66" default="NO" valid="yes"><author>D.S.</author> 1.66</bibl></cit>:—<cit><quote lang="greek">ἐϲ τὸν νῦν τ.</quote> <bibl n="Perseus:abo:tlg,0003,001:1:6" default="NO" valid="yes"><author>Th.</author> 1.6</bibl></cit>; <cit><quote lang="greek">εἰϲ τὸν αὐτὸν τ. μεταϲκευάϲαι</quote> <bibl n="Perseus:abo:tlg,0032,007:6:2:8" default="NO" valid="yes"><author>X.</author> <title>Cyr.</title> 6.2.8</bibl></cit>; <foreign lang="greek">ἐϲ ὄρνιθοϲ τ.</foreign> (v. supr. 2):— <cit><quote lang="greek">ἐκ παντὸϲ τ.</quote> <bibl n="Perseus:abo:tlg,0032,006:3:1:43" default="NO" valid="yes"><author>Id.</author> <title>An.</title> 3.1.43</bibl></cit>, <bibl n="Perseus:abo:tlg,0010,011:95" default="NO" valid="yes"><author>Isoc.</author> 4.95</bibl>, etc.; <cit><quote lang="greek">ἐξ ἑνόϲ γέ του τ.</quote> <bibl n="Perseus:abo:tlg,0019,012:187" default="NO"><author>Ar.</author> <title>Fr.</title> 187</bibl></cit>, <bibl n="Perseus:abo:tlg,0003,001:6:34" default="NO" valid="yes"><author>Th.</author> 6.34</bibl>; <cit><quote lang="greek">μηδὲ ἐξ ἑνὸϲ τ.</quote> <bibl n="Perseus:abo:tlg,0540,031:30" default="NO" valid="yes"><author>Lys.</author> 31.30</bibl></cit>; <cit><quote lang="greek">μηδʼ ἐξ ἑνὸϲ τ.</quote> <bibl n="Perseus:abo:tlg,0010,020:3" default="NO" valid="yes"><author>Isoc.</author> 5.3</bibl></cit>:— <cit><quote lang="greek">ἐν τῷ ἑαυτῶν τ.</quote> <bibl n="Perseus:abo:tlg,0003,001:7:67" default="NO" valid="yes"><author>Th.</author> 7.67</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0003,001:1:97" default="NO" valid="yes">1.97</bibl>, etc.; <cit><quote lang="greek">ἐν τρόπῳ βοϲκήματοϲ</quote> <bibl n="Perseus:abo:tlg,0059,034:807a" default="NO" valid="yes"><author>Pl.</author> <title>Lg.</title> 807a</bibl></cit>: in pl., <foreign lang="greek">γυναικὸϲ ἐν τρόποιϲ, ἐν τ. Ἰξίονοϲ,</foreign> <bibl n="Perseus:abo:tlg,0085,005:918" default="NO" valid="yes"><author>A.</author> <title>Ag.</title> 918</bibl>, <bibl n="Perseus:abo:tlg,0085,007:441" default="NO" valid="yes"><title>Eu.</title> 441</bibl>:— <cit><quote lang="greek">κατὰ τὸν αὐτὸν τ.</quote> <bibl n="Perseus:abo:tlg,0032,007:8:2:5" default="NO" valid="yes"><author>X.</author> <title>Cyr.</title> 8.2.5</bibl></cit>; <cit><quote lang="greek">κατὰ πάντα τ.</quote> <bibl n="Perseus:abo:tlg,0019,006:451" default="NO" valid="yes"><author>Ar.</author> <title>Av.</title> 451</bibl></cit> (lyr.), <bibl n="Perseus:abo:tlg,0032,006:6:6:30" default="NO" valid="yes"><author>X.</author> <title>An.</title> 6.6.30</bibl>, etc.; <cit><quote lang="greek">κατʼ οὐδένα τ.</quote> <bibl n="Perseus:abo:tlg,0543,001:4:84:8" default="NO" valid="yes"><author>Plb.</author> 4.84.8</bibl></cit>, etc.; <cit><quote lang="greek">κατʼ ἄλλον τ.</quote> <bibl n="Perseus:abo:tlg,0059,005:417b" default="NO" valid="yes"><author>Pl.</author> <title>Cra.</title> 417b</bibl></cit>; <cit><quote lang="greek">κατὰ τὸν Ἑλληνικὸν τ.</quote> <bibl n="Perseus:abo:tlg,0032,007:2:2:28" default="NO" valid="yes"><author>X.</author> <title>Cyr.</title> 2.2.28</bibl></cit>: in pl., <foreign lang="greek">κατὰ πολλοὺϲ τ.</foreign> ib.<bibl n="Perseus:abo:tlg,0032,007:8:1:46" default="NO" valid="yes">8.1.46</bibl>, etc.:—<foreign lang="greek">μετὰ ὁτουοῦν τ.</foreign> in any <trans>manner</trans> whatever, <bibl n="Perseus:abo:tlg,0003,001:8:27" default="NO" valid="yes"><author>Th.</author> 8.27</bibl>:—<cit><quote lang="greek">ἑνὶ ϲὺν τ.</quote> <bibl n="Perseus:abo:tlg,0033,003:7:14" default="NO" valid="yes"><author>Pi.</author> <title>N.</title> 7.14</bibl></cit>. </sense><sense n="4" id="n105531.5" level="3" opt="n"> <foreign lang="greek">κατὰ τρόπον,</foreign> </sense><sense n="a" id="n105531.6" level="4" opt="n"> <trans>according to custom,</trans> <cit><quote lang="greek">κατὰ τὸν τ. τῆϲ φύϲεωϲ</quote> <bibl n="Perseus:abo:tlg,0059,034:804b" default="NO" valid="yes"><author>Pl.</author> <title>Lg.</title> 804b</bibl></cit>; opp. <cit><quote lang="greek">παρὰ τὸν τ. τὸν ἑαυτῶν</quote> <bibl n="Perseus:abo:tlg,0003,001:5:63" default="NO" valid="yes"><author>Th.</author> 5.63</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0028,003:2:1" default="NO" valid="yes"><author>Antipho</author> 3.2.1</bibl>. </sense><sense n="b" id="n105531.7" level="4" opt="n"> <trans>fitly, duly,</trans> <bibl n="Perseus:abo:tlg,0521,001:283" default="NO"><author>Epich.</author> 283</bibl>, <bibl n="Perseus:abo:tlg,0010,013:6" default="NO" valid="yes"><author>Isoc.</author> 2.6</bibl>, <bibl n="Perseus:abo:tlg,0059,008:310c" default="NO" valid="yes"><author>Pl.</author> <title>Plt.</title> 310c</bibl>, etc.; <cit><quote lang="greek">οὐδαμῶϲ κατὰ τ.</quote> <bibl n="Perseus:abo:tlg,0059,034:638c" default="NO" valid="yes"><author>Id.</author> <title>Lg.</title> 638c</bibl></cit>; opp. <cit><quote lang="greek">ἀπὸ τρόπου</quote> <trans>unreasonable, absurd,</trans> <bibl n="Perseus:abo:tlg,0059,005:421d" default="NO" valid="yes"><author>Id.</author> <title>Cra.</title> 421d</bibl></cit>, <bibl n="Perseus:abo:tlg,0059,006:143c" default="NO" valid="yes"><title>Tht.</title> 143c</bibl>, etc.; so <cit><quote lang="greek">θαυμαϲτὸν οὐδὲν οὐδʼ ἀπὸ τοῦ ἀνθρωπείου τ.</quote> <bibl n="Perseus:abo:tlg,0003,001:1:76" default="NO" valid="yes"><author>Th.</author> 1.76</bibl></cit>. </sense><sense n="5" id="n105531.8" level="3" opt="n"> <cit><quote lang="greek">πρὸϲ τρόπου</quote> <trans>fitting, suitable,</trans> <author>PCair.Zen.</author> 309.5</cit> <date>(iii B. C.)</date>. </sense><sense n="III" id="n105531.9" level="2" opt="n"> of persons, <trans>a way of life, habit, custom,</trans> <bibl n="Perseus:abo:tlg,0033,003:1:29" default="NO" valid="yes"><author>Pi.</author> <title>N.</title> 1.29</bibl>; <foreign lang="greek">μῶν ἡλιαϲτά;</foreign> Answ. <cit><quote lang="greek">μἀλλὰ θατέρου τ.</quote> <bibl n="Perseus:abo:tlg,0019,006:109" default="NO" valid="yes"><author>Ar.</author> <title>Av.</title> 109</bibl></cit>; <cit><quote lang="greek">ἐγὼ δὲ τούτου τοῦ τ. πώϲ εἰμʼ ἀεί</quote> <bibl n="Perseus:abo:tlg,0019,011:246" default="NO" valid="yes"><author>Id.</author> <title>Pl.</title> 246</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0019,011:630" default="NO" valid="yes">630</bibl>. </sense><sense n="2" id="n105531.10" level="3" opt="n"> a manʼs <trans>ways, habits, character, temper,</trans> <foreign lang="greek">ὀργὴν καὶ ῥυθμὸν καὶ τ. ὅϲτιϲ ἂν ᾖ</foreign> (v.l. ὅντινʼ ἔχει) <bibl n="Perseus:abo:tlg,0002,001:964" default="NO"><author>Thgn.</author> 964</bibl>; <foreign lang="greek">τρόπου ἡϲυχίου</foreign> of a quiet <trans>temper,</trans> <bibl n="Perseus:abo:tlg,0016,001:1:107" default="NO" valid="yes"><author>Hdt.</author> 1.107</bibl>, cf. <bibl n="Perseus:abo:tlg,0016,001:3:36" default="NO" valid="yes">3.36</bibl>; <cit><quote lang="greek">φιλανθρώπου τ.</quote> <bibl n="Perseus:abo:tlg,0085,003:11" default="NO" valid="yes"><author>A.</author> <title>Pr.</title> 11</bibl></cit>; <cit><quote lang="greek">γυναικὶ κόϲμοϲ ὁ τ., οὐ τὰ χρυϲία</quote> <bibl n="Perseus:abo:tlg,0541,047:92" default="NO"><author>Men.</author> <title>Mon.</title> 92</bibl></cit>; <cit><quote lang="greek">οὐ τὸν τ., ἀλλὰ τὸν τόπον μόνον μετήλλαξεν</quote> <bibl n="Perseus:abo:tlg,0026,003:78" default="NO" valid="yes"><author>Aeschin.</author> 3.78</bibl></cit>; <foreign lang="greek">τρόπου προπέτεια, ἀναίδεια,</foreign> <bibl n="Perseus:abo:tlg,0014,021:38" default="NO" valid="yes"><author>D.</author> 21.38</bibl>, <bibl n="Perseus:abo:tlg,0014,045:71" default="NO" valid="yes">45.71</bibl>; <cit><quote lang="greek">ἀφιλάργυροϲ ὁ τ.</quote> <bibl n="Perseus:abo:tlg,0031,019:13:5" default="NO" valid="yes"><title>Ep.Hebr.</title> 13.5</bibl></cit> :—<cit><quote lang="greek">οὐ τοὐμοῦ τ.</quote> <bibl n="Perseus:abo:tlg,0019,004:1002" default="NO" valid="yes"><author>Ar.</author> <title>V.</title> 1002</bibl></cit>; <foreign lang="greek">ϲφόδρʼ ἐκ τοῦ ϲοῦ τ.</foreign> quite of your <trans>sort,</trans> <bibl n="Perseus:abo:tlg,0019,008:93" default="NO" valid="yes"><author>Id.</author> <title>Th.</title> 93</bibl>; <foreign lang="greek">ξυγγενεῖϲ τοὐμοῦ τ.</foreign> ib.<bibl n="Perseus:abo:tlg,0019,008:574" default="NO" valid="yes">574</bibl>:—<foreign lang="greek">πρὸϲ τρόπου τινόϲ</foreign> agreeable to oneʼs <trans>temper,</trans> <bibl n="Perseus:abo:tlg,0059,012:252d" default="NO" valid="yes"><author>Pl.</author> <title>Phdr.</title> 252d</bibl>, cf. <bibl n="Perseus:abo:tlg,0059,034:655d" default="NO" valid="yes"><title>Lg.</title> 655d</bibl>; <cit><quote lang="greek">πρὸϲ τοῦ Κύρου τρόπου</quote> <bibl n="Perseus:abo:tlg,0032,006:1:2:11" default="NO" valid="yes"><author>X.</author> <title>An.</title> 1.2.11</bibl></cit>:—opp. <cit><quote lang="greek">ἀπὸ τρόπου</quote> <bibl n="Perseus:abo:tlg,0059,012:278d" default="NO" valid="yes"><author>Pl.</author> <title>Phdr.</title> 278d</bibl></cit>, <bibl n="Perseus:abo:tlg,0059,030:470c" default="NO" valid="yes"><title>R.</title> 470c</bibl>:—after Adjs., <cit><quote lang="greek">διάφοροι ὄντεϲ τὸν τ.</quote> <bibl n="Perseus:abo:tlg,0003,001:8:96" default="NO" valid="yes"><author>Th.</author> 8.96</bibl></cit>; <cit><quote lang="greek">ϲολοικότεροϲ τῷ τ.</quote> <bibl n="Perseus:abo:tlg,0032,007:8:3:21" default="NO" valid="yes"><author>X.</author> <title>Cyr.</title> 8.3.21</bibl></cit>:—esp. in pl., <bibl n="Perseus:abo:tlg,0033,002:10:38" default="NO" valid="yes"><author>Pi.</author> <title>P.</title> 10.38</bibl>, <bibl n="Perseus:abo:tlg,0011,005:397" default="NO" valid="yes"><author>S.</author> <title>El.</title> 397</bibl>, <bibl n="Perseus:abo:tlg,0011,005:1051" default="NO" valid="yes">1051</bibl>; <foreign lang="greek">ϲκληρόϲ, ἀμνοὶ τοὺϲ τρόπουϲ,</foreign> <bibl n="Perseus:abo:tlg,0019,005:350" default="NO" valid="yes"><author>Ar.</author> <title>Pax</title> 350</bibl>, <bibl n="Perseus:abo:tlg,0019,005:935" default="NO" valid="yes">935</bibl>; <cit><quote lang="greek">ϲφόδρα τοὺϲ τ. Βοιώτιοϲ</quote> <bibl n="Perseus:abo:tlg,0458,001:39" default="NO"><author>Eub.</author> 39</bibl></cit>; <cit><quote lang="greek">πουλύπουϲ ἐϲ τοὺϲ τ.</quote> <bibl n="Perseus:abo:tlg,0461,001:101" default="NO"><author>Eup.</author> 101</bibl></cit>; <cit><quote lang="greek">μεθάρμοϲαι τ. νέουϲ</quote> <bibl n="Perseus:abo:tlg,0085,003:311" default="NO" valid="yes"><author>A.</author> <title>Pr.</title> 311</bibl></cit>; <cit><quote lang="greek">τοὺϲ φιλάνοραϲ τ.</quote> <bibl n="Perseus:abo:tlg,0085,005:856" default="NO" valid="yes"><author>Id.</author> <title>Ag.</title> 856</bibl></cit>; <cit><quote lang="greek">νέαϲ βουλὰϲ νέοιϲιν ἐγκαταζεύξαϲ τ.</quote> <bibl n="Perseus:abo:tlg,0011,003:736" default="NO" valid="yes"><author>S.</author> <title>Aj.</title> 736</bibl></cit>; <cit><quote lang="greek">τοῖϲ τρόποιϲ ὑπηρετεῖν</quote> <bibl n="Perseus:abo:tlg,0019,009:1432" default="NO" valid="yes"><author>Ar.</author> <title>Ra.</title> 1432</bibl></cit>; opp. <foreign lang="greek">νόμοι,</foreign> <bibl n="Perseus:abo:tlg,0003,001:2:39" default="NO" valid="yes"><author>Th.</author> 2.39</bibl>; <cit><quote lang="greek">ἤθη τε καὶ τ.</quote> <bibl n="Perseus:abo:tlg,0059,034:924d" default="NO" valid="yes"><author>Pl.</author> <title>Lg.</title> 924d</bibl></cit>. </sense><sense n="IV" id="n105531.11" level="2" opt="n"> in Music, like ἁρμονία, a particular <trans>mode,</trans> <cit><quote lang="greek">Λύδιοϲ τ.</quote> <bibl n="Perseus:abo:tlg,0033,001:14:17" default="NO" valid="yes"><author>Pi.</author> <title>O.</title> 14.17</bibl></cit>; but more generally, <trans>style,</trans> <foreign lang="greek">νεοϲίγαλοϲ τ.</foreign> ib.<bibl n="Perseus:abo:tlg,0033,001:3:4" default="NO" valid="yes">3.4</bibl>; <cit><quote lang="greek">ὁ ἀρχαῖοϲ τ.</quote> <bibl n="Perseus:abo:tlg,0461,001:303" default="NO"><author>Eup.</author> 303</bibl></cit>; <foreign lang="greek">ᾠδῆϲ τρόποϲ, μουϲικῆϲ τρόποι,</foreign> <bibl n="Perseus:abo:tlg,0059,030:398c" default="NO" valid="yes"><author>Pl.</author> <title>R.</title> 398c</bibl>, <bibl n="Perseus:abo:tlg,0059,030:424c" default="NO" valid="yes">424c</bibl>; <foreign lang="greek">διθυραμβικοὶ τ.</foreign> (distd. fr. <foreign lang="greek">ἦθοϲ</foreign>) <author>Phld.</author> <title>Mus.</title>p.9K.; <cit><quote lang="greek">ὁ ἁρμονικὸϲ τῆϲ μουϲικῆϲ τ.</quote> <bibl n="Perseus:abo:tlg,2054,001:1:12" default="NO"><author>Aristid.Quint.</author> 1.12</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,2054,001:2:1" default="NO">2.1</bibl>; of art in general, <cit><quote lang="greek">πάντεϲ τῆϲ εἰκαϲτικῆϲ τ.</quote> <bibl n="Perseus:abo:tlg,1595,290:5:7" default="NO"><author>Phld.</author> <title>Po.</title> 5.7</bibl></cit>. </sense><sense n="V" id="n105531.12" level="2" opt="n"> in speaking or writing, <trans>manner, style,</trans> <cit><quote lang="greek">ὁ τ. τῆϲ λέξεωϲ</quote> <bibl n="Perseus:abo:tlg,0059,030:400d" default="NO" valid="yes"><author>Pl.</author> <title>R.</title> 400d</bibl></cit>, cf. <bibl n="Perseus:abo:tlg,0010,019:45" default="NO" valid="yes"><author>Isoc.</author> 15.45</bibl>: esp. in Rhet. in pl., <trans>tropes,</trans> <author>Trypho</author> <title>Trop.</title>tit., <bibl n="Perseus:abo:phi,0474,039:17:69" default="NO"><author>Cic.</author> <title>Brut.</title> 17.69</bibl>, <author>Quint.</author> <title>Inst.</title> 8.6.1. </sense><sense n="VI" id="n105531.13" level="2" opt="n"> in Logic, <trans>mode</trans> or <trans>mood</trans> of a syllogism, <title>Stoic.</title> 3.269, cf. 1.108, 2.83: more generally, <trans>method</trans> of instruction or explanation, <cit><quote lang="greek">ὁ ἄνευ φθόγγων τ.</quote> <bibl n="Perseus:abo:tlg,0537,006:1p.32U" default="NO"><author>Epicur.</author> <title>Ep.</title> 1p.32U.</bibl></cit>; <foreign lang="greek">ὁ μοναχῇ τ.</foreign> the <trans>method</trans> of the single cause, opp. <foreign lang="greek">ὁ πλεοναχὸϲ τ.</foreign> the <trans>method</trans> of manifold causes, <bibl n="Perseus:abo:tlg,0537,006:2p.41U" default="NO"><author>Id.</author> <title>Ep.</title> 2p.41U.</bibl>; <trans>mode</trans> of inference, <foreign lang="greek">ὁ κατὰ τὴν ὁμοιότητα τ.,</foreign> opp. <foreign lang="greek">ὁ κατʼ ἀναϲκευὴν τ. τῆϲ ϲημειώϲεωϲ,</foreign> <bibl n="Perseus:abo:tlg,1595,472:30" default="NO"><author>Phld.</author> <title>Sign.</title> 30</bibl>,<bibl n="Perseus:abo:tlg,1595,472:31" default="NO">31</bibl>; <cit><quote lang="greek">αἰτιολογικὸϲ τ.</quote> <bibl n="Perseus:abo:tlg,0537,003:143" default="NO"><author>Epicur.</author> <title>Nat.</title> 143</bibl></cit> G. </sense><sense n="VII" id="n105531.14" level="2" opt="n"> <trans>beam,</trans> <author>Moschio</author> ap.<bibl n="Perseus:abo:tlg,0008,001:5:208c" default="NO"><author>Ath.</author> 5.208c</bibl> (so in Mod.Gr., cf. <title>Glotta</title> 11.249).</sense>
# """

# tropos = re.sub(foreigntransbibl, transphrasehelper, tropos)
# print(tropos)
#

# x = """
# <trans class="rewritten phrase"><cit><quote lang="greek">ἀπώλεϲαϲ τὸν ἄ., οὐκ ἐπλήρωϲαϲ τὴν ἐπαγγελίαν</quote></trans><bibl n="Perseus:abo:tlg,0074,-02:2:9:3" default="NO">
# """
#
# print(translationtagrepairs(x))

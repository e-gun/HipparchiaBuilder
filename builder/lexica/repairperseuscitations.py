# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


test = """
πρόϲπολοϲ     | πρόϲπολοϲ      | προϲπολοϲ        |     89993 |

<head extent="full" lang="greek" opt="n" orth_orig="πρόϲπολοϲ">πρόϲπολοϲ</head>, <gen lang="greek" opt="n">ὁ</gen>, <sense id="n89993.0" n="A" level="1" opt="n"><trans>servant, attendant</trans>, <bibl n="Perseus:abo:tlg,0011,007:897" default="NO" valid="yes"><author>S.</author> <title>OC</title> 897</bibl>, <bibl n="Perseus:abo:tlg,0011,007:1553" default="NO" valid="yes">1553</bibl>, <bibl n="Perseus:abo:tlg,0006,016:106" default="NO" valid="yes"><author>E.</author> <title>Or.</title> 106</bibl>, etc.; <trans>ministering priest</trans>, <bibl n="Perseus:abo:tlg,0085,007:1024" default="NO" valid="yes"><author>A.</author> <title>Eu.</title> 1024</bibl>, <bibl n="Perseus:abo:tlg,0011,007:1053" default="NO" valid="yes"><author>S.</author> <title>OC</title> 1053</bibl> (lyr.); <cit><quote lang="greek">π. θεᾶϲ</quote> <bibl n="Perseus:abo:tlg,0006,008:2" default="NO" valid="yes"><author>E.</author> <title>Supp.</title> 2</bibl></cit>; <foreign lang="greek">π. φόνου</foreign> <trans>minister</trans> of death, <bibl n="Perseus:abo:tlg,0085,004:574" default="NO" valid="yes"><author>A.</author> <title>Th.</title> 574</bibl>; <foreign lang="greek">Λητοῖ π</foreign>. <title>App.Anth.</title> 1.193 (<placeName>Egypt</placeName>): not in Prose, exc. as v.l. for πρόπολοϲ, <bibl n="Perseus:abo:tlg,0016,001:2:63" default="NO" valid="yes"><author>Hdt.</author> 2.63</bibl>. </sense><sense n="2" id="n89993.1" level="3" opt="n"> fem., <foreign lang="greek">Ἀθάναϲ π</foreign>. <bibl n="Perseus:abo:tlg,0199,001:14:2" default="NO" valid="yes"><author>B.</author> 14.2</bibl>; <foreign lang="greek">Βάκχου πρόϲπολοι</foreign>,= <foreign lang="greek">Βάκχαι</foreign>, <bibl n="Perseus:abo:tlg,0203,001:46" default="NO"><author>Limen.</author> 46</bibl>; <trans>handmaid</trans>, <bibl n="Perseus:abo:tlg,0011,004:945" default="NO" valid="yes"><author>S.</author> <title>OT</title> 945</bibl>, <bibl n="Perseus:abo:tlg,0011,007:746" default="NO" valid="yes"><title>OC</title> 746</bibl>, etc.</sense>
"""

"""

sub:  (.*?)  \| (.*?)$
"\1", "\2"

hipparchiaDB=# select universalid,title from works where universalid ~* 'gr0006' order by title asc;
"""

euripides = {
	"Al.": ("035", "Alcestis"),
	"Alc.": ("035", "Alcestis"),
	"Andr.": ("039", "Andromacha"),
	"Ba.": ("050", "Bacchae"),
	"Cyc.": ("034", "Cyclops"),
	"El.": ("042", "Electra"),
	"Epigr.": ("031", "Epigrammata"),
	"U1": ("022", "Epinicium in Alcibiadem (fragmenta)"),
	"Fr.": ("020", "Fragmenta"),
	"U3": ("033", "Fragmenta"),
	"U4": ("029", "Fragmenta"),
	"U5": ("025", "Fragmenta Alexandri"),
	"Antiop.": ("024", "Fragmenta Antiopes"),
	"Hyps.": ("026", "Fragmenta Hypsipyles"),
	"Oen.": ("030", "Fragmenta Oenei"),
	"Phaeth.": ("023", "Fragmenta Phaethontis"),
	"U6": ("032", "Fragmenta Phaethontis incertae sedis"),
	"U7": ("027", "Fragmenta Phrixei (P. Oxy. 34.2685)"),
	"U8": ("028", "Fragmenta fabulae incertae"),
	"U9": ("021", "Fragmenta papyracea"),
	"Hec.": ("040", "Hecuba"),
	"Hel.": ("047", "Helena"),
	"Heracl.": ("037", "Heraclidae"),
	"HF": ("043", "Hercules"),
	"Hipp.": ("038", "Hippolytus"),
	"Ion": ("046", "Ion"),
	"IA": ("051", "Iphigenia Aulidensis"),
	"IT": ("045", "Iphigenia Taurica"),
	"Med.": ("036", "Medea"),
	"Or.": ("049", "Orestes"),
	"Ph.": ("048", "Phoenisae"),
	"Rh.": ("052", "Rhesus"),
	"Supp.": ("041", "Supplices"),
	"Tr.": ("044", "Troiades")
}


"""
re.findall(thumbprint, test)
[('0011', '007', 'OC'), ('0011', '007', 'Or.'), ('0085', '007', 'Eu.'), ('0011', '007', 'OC'), ('0006', '008', 'Supp.'), ('0085', '004', 'Th.'), ('0016', '001', 'OT'), ('0011', '007', 'OC')]

"""

def conditionalswapper(match):
	"""

	sample match[0]
		<bibl n="Perseus:abo:tlg,0011,007:897" default="NO" valid="yes"><author>S.</author> <title>OC</title> 897</bibl>

	match[1]
		0011

	match[2]
		007

	match[3]
		OC

	:param match:
	:return:
	"""
	greek = {'0006': euripides}
	newtext = match[0]

	if match[1] in greek:
		works = greek[match[1]]
		if match[3] in works:
			try:
				item = works[match[3]]
				newtext = re.sub(r'tlg,(....),(...)', r'tlg,\1,'+item[0], match[0])
			except KeyError:
				# print('keyerror for' + match[3])
				pass
		else:
			# print(match[3] + ' not in works of ' + match[1])
			pass
	return newtext


def perseuslookupfixer(entrytext: str) -> str:
	"""

	some perseus references are broken; attempt to fix them

	turn something like
		Perseus:abo:tlg,0006,008:2
	into
		Perseus:abo:tlg,0006,041:2

	:param entrytext:
	:return:
	"""

	thumbprint = re.compile(r'<bibl n="Perseus:abo:tlg,(....),(...):.*?<title>(.*?)</title>.*?</bibl>')
	fixentry = re.sub(thumbprint, conditionalswapper, entrytext)

	return fixentry


# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import psycopg2

from string import punctuation

from builder.parsers.betacodeandunicodeinterconversion import cleanaccentsandvj
from builder.parsers.transliteration import stripaccents
# from builder.dbinteraction.connection import setconnection


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


def conditionalworkidswapper(match):
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

	greekauthorstofix = {'0006': euripides}
	newtext = match[0]

	if match[1] in greekauthorstofix:
		works = greekauthorstofix[match[1]]
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


def citationformatconverter(entrytext: str, dbconnection=None) -> str:
	"""

	plautus is cited by act, etc vs by line

	attempt to fix this...

	:param entrytext:
	:return:
	"""

	if not dbconnection:
		# dbconnection = setconnection()
		dbconnection = psycopg2.connect(user='hippa_wr',
		                                host='127.0.0.1',
		                                port=5432,
		                                database='hipparchiaDB',
		                                password='')

	# dbconnection.setautocommit()

	authorstofix = {'phi,0119': 'Plautus'}
	au = 'phi,0119'
	adb = 'lt0119'

	citationfinder = re.compile(r'(<cit>.*?</cit>)')

	citations = re.findall(citationfinder, entrytext)



	dbcursor = dbconnection.cursor()

	targetcitation = re.compile(r'<bibl n="Perseus:abo:{a},(...):(.*?)"[^>]*?>'.format(a=au))
	citationswap = re.compile(r'(<bibl n="Perseus:abo:{a},...:)(.*?)("[^>]*?>)'.format(a=au))
	locusfinder = re.compile(r'</author>\s(.*?)\s(.*?)</bibl></cit>')
	quotefinder = re.compile(r'<quote lang="la">(.*?)</quote>')
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation)))

	querytemplate = """
		SELECT level_00_value FROM {t}
			WHERE wkuniversalid = %s and stripped_line ~* %s
	"""

	for c in citations:
		lineval = None
		t = re.search(targetcitation, c)
		if t:
			q = re.search(quotefinder, c)
			if q:
				print('c',c)
				quote = cleanaccentsandvj(stripaccents(q[1].lower()))
				quote = re.sub(punct, str(), quote)
				print(quote)
				wkid = t[1]
				loc = t[2]
				print('q: {q}; w: {w}, l: {l}'.format(q=quote, w=wkid, l=loc))
				data = ('{a}w{w}'.format(a=adb, w=wkid), quote)
				# print(querytemplate.format(t=adb), data)
				dbcursor.execute(querytemplate.format(t=adb), data)
				hit = dbcursor.fetchone()
				if hit:
					# print('found', hit[0])
					lineval = hit[0]
					# zz = re.search(locusfinder, c)
					# print(zz.group(0))
					newcitation = re.sub(locusfinder, r'</author>\1 {lv}</bibl></cit>'.format(lv=lineval), c)
					newcitation = re.sub(citationswap, r'\1ZZZ" rewritten="yes\3', newcitation)
					newcitation = re.sub('ZZZ', lineval, newcitation)
					entrytext = re.sub(c, newcitation, entrytext)
				else:
					print('cound not find "{q}"'.format(q=quote))
		if lineval:
			pass

	return entrytext


def perseusworkmappingfixer(entrytext: str) -> str:
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
	fixentry = re.sub(thumbprint, conditionalworkidswapper, entrytext)

	return fixentry


x = """
plautus is cited by act, etc vs by line

 <orth extent="full" lang="la" opt="n">hăbĭto</orth>, <itype opt="n">āvi, ātum, 1</itype> (<sense id="n20088.0" n="I" level="1" opt="n"><hi rend="ital">gen. plur.</hi> of the <hi rend="ital">part. pres.</hi> habitantum, <bibl n="Perseus:abo:phi,0959,006:14:90" default="NO" valid="yes"><author>Ov.</author> M. 14, 90</bibl>), <pos opt="n">v. freq. a.</pos> and <gen opt="n">n.</gen> <etym opt="n">habeo</etym>. </sense><sense id="n20088.1" n="I" level="1" opt="n"> In gen., <hi rend="ital">to have frequently</hi>, <hi rend="ital">to be wont to have</hi> (anteclass. and very rare): epicrocum, Varr. ap. <bibl default="NO"><author>Non.</author> 318, 25</bibl>: <cit><quote lang="la">comas,</quote> <bibl default="NO"><author>id.</author> ib. 27</bibl></cit>.—</sense><sense id="n20088.2" n="II" level="1" opt="n"> In partic., <hi rend="ital">to have possession of</hi>, <hi rend="ital">to inhabit</hi> a place; and more freq. <hi rend="ital">neut.</hi>, <hi rend="ital">to dwell</hi>, <hi rend="ital">abide</hi>, <hi rend="ital">reside</hi>, <hi rend="ital">live</hi> anywhere (the class. signif. of the word; cf.: colo, incolo, commoror). </sense><sense id="n20088.3" n="A" level="2" opt="n"> <usg type="style" opt="n">Lit.</usg> </sense><sense id="n20088.4" n="1" level="3" opt="n"> <hi rend="ital">Act.</hi>: <cit><quote lang="la">centum urbes habitant magnas,</quote> <bibl n="Perseus:abo:phi,0690,003:3:106" default="NO" valid="yes"><author>Verg.</author> A. 3, 106</bibl></cit>: <cit><quote lang="la">silvas,</quote> <bibl n="Perseus:abo:phi,0690,001:6:2" default="NO" valid="yes"><author>id.</author> E. 6, 2</bibl></cit>: <cit><quote lang="la">hoc nemus, hunc collem (deus),</quote> <bibl n="Perseus:abo:phi,0690,003:8:352" default="NO" valid="yes"><author>id.</author> A. 8, 352</bibl></cit>: <cit><quote lang="la">humiles casas,</quote> <bibl n="Perseus:abo:phi,0690,001:2:29" default="NO" valid="yes"><author>id.</author> E. 2, 29</bibl></cit>: <cit><quote lang="la">terras,</quote> <bibl n="Perseus:abo:phi,0959,002:1:66" default="NO" valid="yes"><author>Ov.</author> H. 1, 66</bibl></cit>; <bibl n="Perseus:abo:phi,0959,006:1:195" default="NO" valid="yes"><author>id.</author> M. 1, 195</bibl>: <cit><quote lang="la">pruinas,</quote> <bibl n="Perseus:abo:phi,1035,001:2:177" default="NO"><author>Val. Fl.</author> 2, 177</bibl></cit>: <cit><quote lang="la">locum,</quote> <bibl n="Perseus:abo:phi,1351,001:11" default="NO" valid="yes"><author>Tac.</author> Agr. 11</bibl></cit>; cf. <bibl n="Perseus:abo:phi,0914,001:5:51:3" default="NO" valid="yes"><author>Liv.</author> 5, 51, 3</bibl>. —<hi rend="ital">Pass.</hi>: <cit><quote lang="la">colitur ea pars (urbis) et habitatur frequentissime,</quote> <bibl n="Perseus:abo:phi,0474,005:4:53:section=119" default="NO" valid="yes"><author>Cic.</author> Verr. 2, 4, 53, § 119</bibl></cit>; cf. <bibl n="Perseus:abo:phi,1002,001:1:4:28" default="NO"><author>Quint.</author> 1, 4, 28</bibl>: <cit><quote lang="la">arx procul iis, quae habitabantur,</quote> <bibl n="Perseus:abo:phi,0914,001:24:3:2" default="NO" valid="yes"><author>Liv.</author> 24, 3, 2</bibl></cit>: <cit><quote lang="la">applicata colli habitatur colonia Corinthus,</quote> <bibl n="Perseus:abo:phi,0978,001:4:11" default="NO" valid="yes"><author>Plin.</author> 4, 4, 5, § 11</bibl></cit>; <bibl n="Perseus:abo:phi,0978,001:5:42" default="NO" valid="yes">5, 7, 7, § 42</bibl>: <cit><quote lang="la">Scythiae confinis est regio habitaturque pluribus vicis,</quote> <bibl n="Perseus:abo:phi,0860,001:8:2:14" default="NO"><author>Curt.</author> 8, 2, 14</bibl></cit>: <cit><quote lang="la">nobis habitabitur orbis Ultimus,</quote> <bibl n="Perseus:abo:phi,0959,008:1:1:127" default="NO"><author>Ov.</author> Tr. 1, 1, 127</bibl></cit>: <cit><quote lang="la">tellus Bistoniis habitata viris,</quote> <bibl n="Perseus:abo:phi,0959,006:13:430" default="NO" valid="yes"><author>id.</author> M. 13, 430</bibl></cit>; cf.: <cit><quote lang="la">nec patria est habitata tibi,</quote> <bibl n="Perseus:abo:phi,0959,008:5:3:21" default="NO"><author>id.</author> Tr. 5, 3, 21</bibl></cit>; <bibl n="Perseus:abo:phi,1345,001:2:654" default="NO"><author>Sil.</author> 2, 654</bibl>: <cit><quote lang="la">raris habitata mapalia tectis,</quote> <bibl n="Perseus:abo:phi,0690,002:3:340" default="NO" valid="yes"><author>Verg.</author> G. 3, 340</bibl></cit>; cf.: <cit><quote lang="la">(agellus) habitatus quinque focis,</quote> <bibl default="NO"><author>Hor.</author> Ep. 1, 14, 2</bibl></cit>: <cit><quote lang="la">campi olim uberes magnisque urbibus habitati,</quote> <bibl n="Perseus:abo:phi,1351,004:5:7" default="NO" valid="yes"><author>Tac.</author> H. 5, 7</bibl></cit>: <cit><quote lang="la">quae sit tellus habitanda (sibi), requirit,</quote> <bibl n="Perseus:abo:phi,0959,006:3:9" default="NO" valid="yes"><author>Ov.</author> M. 3, 9</bibl></cit>; cf.: <cit><quote lang="la">cesserunt nitidis habitandae piscibus undae,</quote> <bibl n="Perseus:abo:phi,0959,010:1:74" default="NO"><author>id.</author> ib. 1, 74</bibl></cit>: <cit><quote lang="la">habitandaque fana Apris reliquit et rapacibus lupis,</quote> <bibl n="Perseus:abo:phi,0893,003:16:19" default="NO"><author>Hor.</author> Epod. 16, 19</bibl></cit>: <cit><quote lang="la">proavis habitatas linquere silvas,</quote> <bibl n="Perseus:abo:phi,1276,001:15:152" default="NO"><author>Juv.</author> 15, 152</bibl></cit>.— </sense><sense id="n20088.5" n="2" level="3" opt="n"> <hi rend="ital">Neutr.</hi>: <cit><quote lang="la">in illisce habitat aedibus Amphitruo,</quote> <bibl n="Perseus:abo:phi,0119,001:prol. 97" default="NO" valid="yes"><author>Plaut.</author> Am. prol. 97</bibl></cit>; cf.: <cit><quote lang="la">cujus hic in aediculis habitat decem, ut opinor, milibus,</quote> <bibl n="Perseus:abo:phi,0474,024:7:17" default="NO" valid="yes"><author>Cic.</author> Cael. 7, 17</bibl></cit>: <cit><quote lang="la">in gurgustio,</quote> <bibl n="Perseus:abo:phi,0474,050:1:9:22" default="NO"><author>id.</author> N. D. 1, 9, 22</bibl></cit>: <cit><quote lang="la">in via,</quote> <trans opt="n"><tr opt="n">on the high-road</tr>,</trans> <bibl n="Perseus:abo:phi,0474,035:2:41:106" default="NO" valid="yes"><author>id.</author> Phil. 2, 41, 106</bibl></cit>: <cit><quote lang="la">in Sicilia,</quote> <bibl n="Perseus:abo:phi,0474,005:3:41:section=95" default="NO" valid="yes"><author>id.</author> Verr. 2, 3, 41, § 95</bibl></cit>: <cit><quote lang="la">in arboribus (aves),</quote> <bibl n="Perseus:abo:phi,0978,001:18:363" default="NO" valid="yes"><author>Plin.</author> 18, 35, 87, § 363</bibl></cit>: <cit><quote lang="la">Lilybaei,</quote> <bibl n="Perseus:abo:phi,0474,005:4:18:section=38" default="NO" valid="yes"><author>Cic.</author> Verr. 2, 4, 18, § 38</bibl></cit>: <cit><quote lang="la">lucis opacis,</quote> <bibl n="Perseus:abo:phi,0690,003:6:673" default="NO" valid="yes"><author>Verg.</author> A. 6, 673</bibl></cit>: <cit><quote lang="la">vallibus imis,</quote> <bibl default="NO"><author>id.</author> ib. 3, 110</bibl></cit>: <cit><quote lang="la">casa straminea,</quote> <bibl n="Perseus:abo:phi,1224,001:2:16" default="NO"><author>Prop.</author> 2, 16</bibl></cit> (3, 8), 20; cf.: <cit><quote lang="la">sub terra habitare,</quote> <bibl n="Perseus:abo:phi,0474,050:2:37:95" default="NO"><author>Cic.</author> N. D. 2, 37, 95</bibl></cit>: <cit><quote lang="la">apud aliquem,</quote> <bibl default="NO"><author>id.</author> Ac. 2, 26, 115</bibl></cit>; cf. <bibl n="Perseus:abo:phi,0474,039:90:309" default="NO"><author>id.</author> Brut. 90, 309</bibl>; <bibl n="Perseus:abo:phi,0474,024:21:51" default="NO" valid="yes"><author>id.</author> Cael. 21, 51</bibl>; <bibl n="Perseus:abo:phi,0474,010:12:33" default="NO" valid="yes"><author>id.</author> Clu. 12, 33</bibl>; <bibl n="Perseus:abo:phi,0474,005:2:34:section=83" default="NO" valid="yes"><author>id.</author> Verr. 2, 2, 34, § 83</bibl>: <cit><quote lang="la">cum aliquo,</quote> <bibl default="NO"><author>id.</author> ib. 2, 1, 25</bibl></cit>
"""

x = """
<orth extent="full" lang="la" opt="n">impūrus</orth> (<orth type="alt" extent="full" lang="la" opt="n">inp-</orth>), <itype opt="n">a, um</itype>, <pos opt="n">adj.</pos> <etym opt="n">2. inpurus</etym>, <sense id="n22100.0" n="I" level="1" opt="n"><hi rend="ital">unclean</hi>, <hi rend="ital">filthy</hi>, <hi rend="ital">foul</hi> (cf.: obscenus, spurcus, immundus). </sense><sense id="n22100.1" n="I" level="1" opt="n"> <usg type="style" opt="n">Lit.</usg> (very rare): <cit><quote lang="la">impurae matris prolapsus ab alvo,</quote> <bibl n="Perseus:abo:phi,0959,010:223" default="NO"><author>Ov.</author> Ib. 223</bibl></cit>.—</sense><sense id="n22100.2" n="II" level="1" opt="n"> <usg type="style" opt="n">Trop.</usg>, <hi rend="ital">unclean</hi> (in a moral sense), <hi rend="ital">impure</hi>, <hi rend="ital">defiled</hi>, <hi rend="ital">filthy</hi>, <hi rend="ital">infamous</hi>, <hi rend="ital">abandoned</hi>, <hi rend="ital">vile.</hi> </sense><sense id="n22100.3" n="A" level="2" opt="n"> Of living beings: <cit><quote lang="la">impudens, impurus, inverecundissimus,</quote> <bibl n="Perseus:abo:phi,0119,017:3:2:38" default="NO" valid="yes"><author>Plaut.</author> Rud. 3, 2, 38</bibl></cit>: <cit><quote lang="la">in his gregibus omnes aleatores, omnes adulteri, omnes impuri impudicique versantur,</quote> <bibl n="Perseus:abo:phi,0474,013:2:10:23" default="NO" valid="yes"><author>Cic.</author> Cat. 2, 10, 23</bibl></cit>: <cit><quote lang="la">persona illa lutulenta, impura, invisa,</quote> <bibl n="Perseus:abo:phi,0474,003:7:20" default="NO" valid="yes"><author>id.</author> Rosc. Com. 7, 20</bibl></cit>: <cit><quote lang="la">o hominem impurum!</quote> <bibl n="Perseus:abo:phi,0134,006:2:1:29" default="NO" valid="yes"><author>Ter.</author> Ad. 2, 1, 29</bibl></cit>: impuri cujusdam et ambitiosi sententia,<cb n="IMPU" />  <bibl n="Perseus:abo:phi,0474,052:16:59" default="NO"><author>Cic.</author> Lael. 16, 59</bibl>: <cit><quote lang="la">cum impuris atque immanibus adversariis decertare,</quote> <bibl n="Perseus:abo:phi,0474,043:1:5" default="NO"><author>id.</author> Rep. 1, 5</bibl></cit>: <cit><quote lang="la">(dux) audax, impurus,</quote> <bibl default="NO"><author>id.</author> ib. 1, 44</bibl></cit>: <cit><quote lang="la">impurus et sceleratus,</quote> <bibl n="Perseus:abo:phi,0474,057:9:15" default="NO" valid="yes"><author>id.</author> Att. 9, 15 <hi rend="ital">fin.</hi></bibl></cit>: <cit><quote lang="la">erat hic Corinthia anus haud impura,</quote> <trans opt="n"><tr opt="n">tolerably decent</tr>,</trans> <bibl n="Perseus:abo:phi,0134,002:4:1:16" default="NO" valid="yes"><author>Ter.</author> Heaut. 4, 1, 16</bibl></cit>: <cit><quote lang="la">homo haud impurus,</quote> <bibl n="Perseus:abo:phi,0134,003:2:2:4" default="NO" valid="yes"><author>id.</author> Eun. 2, 2, 4</bibl></cit>: <cit><quote lang="la">libidine omni,</quote> <bibl default="NO"><author>Petr.</author> 81</bibl></cit>.—<hi rend="ital">Comp.</hi>: <cit><quote lang="la">quis illo qui maledicit impurior?</quote> <bibl n="Perseus:abo:phi,0474,035:3:6:15" default="NO" valid="yes"><author>Cic.</author> Phil. 3, 6, 15</bibl></cit>.— <hi rend="ital">Sup.</hi>: omnium non bipedum solum, sed etiam quadrupedum impurissimus, Auct. Or. pro Dom. 18, 48.—</sense><sense id="n22100.4" n="B" level="2" opt="n"> Of inanim. and abstr. things: <cit><quote lang="la">lingua,</quote> <bibl n="Perseus:abo:phi,1014,001:Ep. 87" default="NO"><author>Sen.</author> Ep. 87 <hi rend="ital">med.</hi></bibl></cit>: <cit><quote lang="la">animus,</quote> <bibl n="Perseus:abo:phi,0631,001:C. 15:4" default="NO" valid="yes"><author>Sall.</author> C. 15, 4</bibl></cit>: <cit><quote lang="la">mores,</quote> <bibl n="Perseus:abo:phi,0472,001:108:2" default="NO" valid="yes"><author>Cat.</author> 108, 2</bibl></cit>: <cit><quote lang="la">adulterium,</quote> <bibl n="Perseus:abo:phi,0472,001:66:84" default="NO" valid="yes"><author>id.</author> 66, 84</bibl></cit>: <cit><quote lang="la">historia,</quote> <bibl n="Perseus:abo:phi,0959,008:2:416" default="NO"><author>Ov.</author> Tr. 2, 416</bibl></cit>: <cit><quote lang="la">medicamina, i. e. venena,</quote> <bibl n="Perseus:abo:phi,1242,001:2:20" default="NO"><author>Flor.</author> 2, 20</bibl></cit>: <cit><quote lang="la">quid impurius, quam retinuisse talem (adulteram),</quote> <bibl n="Perseus:abo:phi,1002,001:9:2:80" default="NO"><author>Quint.</author> 9, 2, 80</bibl></cit>. —Hence, <pos opt="n">adv.</pos>: <orth extent="full" lang="la" opt="n">impūrē</orth> (acc. to II.), <hi rend="ital">impurely</hi>, <hi rend="ital">basely</hi>, <hi rend="ital">shamefully</hi>, <hi rend="ital">vilely</hi>: <cit><quote lang="la">impure atque flagitiose vivere,</quote> <bibl n="Perseus:abo:phi,0474,048:3:11:38" default="NO"><author>Cic.</author> Fin. 3, 11, 38</bibl></cit>: <cit><quote lang="la">multa facere impure atque taetre,</quote> <bibl n="Perseus:abo:phi,0474,053:1:29:6" default="NO"><author>id.</author> Div. 1, 29, 6</bibl></cit>: <cit><quote lang="la">atque intemperanter facere,</quote> <bibl n="Perseus:abo:phi,0474,035:2:21:50" default="NO" valid="yes"><author>id.</author> Phil. 2, 21, 50</bibl></cit>: <cit><quote lang="la">a quo impurissime haec nostra fortuna despecta est,</quote> <bibl n="Perseus:abo:phi,0474,057:9:12:2" default="NO" valid="yes"><author>id.</author> Att. 9, 12, 2</bibl></cit>.</sense>
"""
citationformatconverter(x)

"""

hipparchiaDB=# select * from lt0119 where wkuniversalid = 'lt0119w001' limit 1;

"""
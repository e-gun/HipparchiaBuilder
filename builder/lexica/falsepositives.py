# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

"""

the latin dictionary tags conflate grammar notes and translations

'part' is quite dangerous...

"""

# regen after random edits: list(set([x[0].upper()+x[1:] for x in nonsense] + [x[0].lower()+x[1:] for x in nonsense]))
nonsense = {'A', 'A.', 'Ab', 'Abl', 'Abl.', 'Absol', 'Acc.  respect.', 'Acc. respect.', 'Act', 'Adj', 'Adv', 'Comp',
            'Comp.', 'Conj', 'Dat', 'Dep', 'Dim', 'Fem', 'Fem.', 'Fin', 'Fin.', 'Fut', 'Gen', 'Gen.  plur.',
            'Gen. plur.', 'Imp', 'Impers', 'Impers.', 'Inf', 'Inf.  fut. act.', 'Inf. pass', 'Infra', 'Init',
            'Masc', 'Masc.', 'Ne', 'Neutr', 'Neutr.', 'Nom', 'Num', 'Of', 'P.  a. as subst.', 'P. a.  assubst.',
            'Part', 'Part. perf.', 'Patr', 'Perf', 'Perf.', 'Perf.  part', 'Perf. part', 'Pers', 'Plur', 'Plur.',
            'Prep', 'Pres', 'praes.', 'Pron', 'Prop', 'Puperf', 'Subj', 'Subst', 'Subst.', 'Sup', 'Sync', 'Temp', 'Tempp',
            'Tempp press', 'Ut', 'V', 'V. dep. n.', 'V. desid. a.', 'Verb', 'Verb. fin.', 'Verb. finit', 'Voc',
            'a', 'a.', 'ab', 'abl', 'abl.', 'absol', 'acc.  respect.', 'acc. respect.', 'act', 'adj', 'adv', 'comp',
            'comp.', 'conj', 'dat', 'dep', 'dim', 'ex', 'fem', 'fem.', 'fin', 'fin.', 'fut', 'gen', 'gen.', 'gen.  plur.',
            'gen. sing', 'gen. plur.', 'imp', 'impers', 'impers.', 'imperf', 'inf', 'inf.  fut. act.', 'inf. pass', 'infra', 'init',
            'masc', 'masc.', 'ne', 'neutr', 'neutr.', 'nom', 'num', 'of', 'p.  a. as subst.', 'p. a.  assubst.',
            'part', 'part. perf.', 'patr', 'perf', 'perf.', 'perf.  part', 'perf. part', 'pers', 'plur', 'plur.',
            'prep', 'pres', 'praes', 'pron', 'prop', 'puperf', 'subj', 'subst', 'subst.', 'sup', 'sync', 'temp', 'tempp',
            'tempp press', 'ut', 'v', 'v. dep. n.', 'v. dep', 'v. desid. a.', 'verb', 'verb. fin.', 'verb. finit', 'voc'}


heads = ['In gen', 'Prop', 'sync', 'Fig']
heads = [r'^{h}\.'.format(h=h) for h in heads]
heads = heads + [r'^<gramGrp opt="n">', r'^<hi rend="ital">', r'^Act.<hi rend="ital">', r'With <pos opt="n">',
                 r'^<usg type="style" opt="n">', r'^Quantity:', r'^Adv.:', r'^Lyr.', r'^in early Greek']
falseheads = [re.compile(h) for h in heads]
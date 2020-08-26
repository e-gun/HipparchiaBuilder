# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

"""

the latin dictionary tags conflate grammar notes and translations

'part' is quite dangerous...

"""

# regen after random edits: set([x[0].upper()+x[1:] for x in nonsense] + [x[0].lower()+x[1:] for x in nonsense])
nonsense = {'A', 'A.', 'Ab',  'Abl', 'Absol', 'Acc. respect.',  'Act', 'Adj', 'Adv', 'Comp', 'Conj', 'Dat', 'Dep', 'Dim',
            'Fem',  'Fem.', 'Fin',  'Fin.', 'Fut',  'Gen', 'Gen.  plur.', 'Gen.  plur.', 'Imp',  'Inf', 'Inf.  fut. act.',
            'Infra', 'Init',  'Masc', 'Masc.',  'Ne',  'Neutr', 'Neutr.',  'Nom',  'Num', 'Of',  'P. a.  assubst.',
            'Part', 'Part. perf.', 'Patr', 'Perf',  'Perf. part', 'Pers', 'Plur', 'Plur.', 'Prep', 'Pres', 'Pron',  'Prop',
            'Subst',  'Subst.', 'Sup',  'Sync',  'Temp', 'Tempp',  'Tempp press',  'Ut', 'V',  'V. desid. a.',
            'Verb', 'Voc',  'a', 'a.',  'ab', 'abl',  'absol', 'acc.  respect.', 'act',  'adj', 'adv',
            'comp', 'conj', 'dat', 'dep',  'dim', 'fem', 'fem.', 'fin',  'fin.', 'fut', 'gen', 'gen.  plur.', 'gen. plur.',
            'imp',  'inf', 'inf.  fut. act.',  'infra', 'init',  'masc', 'masc.',  'ne', 'neutr',  'neutr.', 'nom',
            'num', 'of', 'p.  a. as subst.', 'part',  'part. perf.', 'patr', 'perf', 'perf.  part', 'pers', 'plur',
            'plur.', 'prep',  'pres', 'pron',  'prop', 'subst',  'subst.', 'sup',  'sync', 'temp',  'tempp', 'tempp press',
            'ut', 'v', 'v. desid. a.', 'verb', 'voc', 'puperf', 'subj', 'Subj', 'v. dep. n.', 'impers', 'Impers'}

heads = [r'In gen', r'Prop', 'sync']
heads = ['(^|^\s){h}\.'.format(h=h) for h in heads]
falseheads = [re.compile(h) for h in heads]
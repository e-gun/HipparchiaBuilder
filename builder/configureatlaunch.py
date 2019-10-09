# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import argparse
import configparser


def getcommandlineargs():
	"""
	what, if anything, was passed to "run.py"?
	:return:
	"""

	commandlineparser = argparse.ArgumentParser(description='available overrides to "config.ini" for "makecorpora.py"; setting any override means that *only* what is explicitly requested will be built')

	commandlineparser.add_argument('--all', action='store_true', help='build absolutely everything [this will ignore any other values you set on the command line]')
	commandlineparser.add_argument('--allbutwordcounts', action='store_true', help='everything other than the wordcounts')
	commandlineparser.add_argument('--allcorpora', action='store_true', help='all texts, but no lexica, grammar, or wordcounts')
	commandlineparser.add_argument('--latinauthors', action='store_true', help='build the database of Latin authors')
	commandlineparser.add_argument('--greekauthors', action='store_true', help='build the database of Greek authors')
	commandlineparser.add_argument('--inscriptions', action='store_true', help='build the database of (mostly Greek) inscriptions')
	commandlineparser.add_argument('--papyri', action='store_true', help='build the database of documentary papyri')
	commandlineparser.add_argument('--christians', action='store_true', help='build the database of Christian era inscriptions')
	commandlineparser.add_argument('--lex', action='store_true', help='build the lexica')
	commandlineparser.add_argument('--gram', action='store_true', help='build the grammatical parsing databases')
	commandlineparser.add_argument('--buildwordcounts', action='store_true', help='build the wordcounts manually')
	commandlineparser.add_argument('--loadwordcounts', action='store_true', help='load the wordcounts from HipparchiaLexicalData')
	commandlineargs = commandlineparser.parse_args()

	return commandlineargs


def tobuildaccordingtoconfigfile():

	config = configparser.ConfigParser()
	config.read('config.ini', encoding='utf8')

	tobuild = dict()

	dbs = ['latinauthors', 'greekauthors', 'inscriptions', 'papyri',
	       'christians', 'lex', 'gram', 'wordcounts']

	for db in dbs:
		if config['corporatobuild']['build'+db] == 'y':
			tobuild[db] = True
		else:
			tobuild[db] = False

	return tobuild


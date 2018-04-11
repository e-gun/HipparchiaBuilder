# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from os import cpu_count

config = configparser.ConfigParser()
config.read('config.ini')


def setworkercount():
	"""

	return the number of workers to use

	:return:
	"""

	if config['io']['autoconfigworkercount'] != 'yes':
		workercount = int(config['io']['workers'])
	else:
		workercount = int(cpu_count() / 2) + 1

	return workercount

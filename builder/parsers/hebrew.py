# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

def replacehebrew(texttoclean):
	"""

	inactive: it looks like there are TWO Hebrew words in all of the G&L data.

	See TLG2934:

		<hmu_fontshift_greek_hebrew>SRNYH &pro$</hmu_fontshift_greek_hebrew>
		<hmu_fontshift_greek_hebrew>'DNYH</hmu_fontshift_greek_hebrew>


	:param texttoclean:
	:return:
	"""

	insethebrew = re.compile(r'(<hmu_fontshift_hebrew>)(.*?)(</hmu_fontshift_hebrew>)')

	return texttoclean
# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from builder.parsers.swappers import highunicodetohex
from builder.parsers import regex_substitutions


def citationbuilder(hexsequence):
	"""
	NOTE: this function expects a call from re.sub and so you need a match.group()

	parse the sequence of bytes for instructions on how to build a citatation
	"0xab 0x82 0xff 0x9f 0xe1 0xff" ==> <set_level_2_to_383>\n<set_level_1_to_a>\n

	this is very fiddly since each instruction requires different actions upon the data
	that follows; furthermore 'level6' is its own world of metadata rather than being a
	simple hierarchy like level00==>verse# and level01==>poem# and level02==>book#

	everything happens byte-by-byte: that means that if you botch one set of instructions
	you will be left with the wrong bytesequence going forward and the next 'instruction'
	is likely to be a piece of the previous set of information; this makes debugging rough
	since garbage at location B can result from troubles at location A.

	this is perhaps the most important bit of the builder and I never could have coded it if
	P. J. Heslin had not released the source code to Diogenes:

		https://community.dur.ac.uk/p.j.heslin/Software/Diogenes/

	I shudder to think how long it took him to figure out the way to read the bytes and nybbles
	properly. Without his efforts Hipparchia would not have been possible.

	:param hexsequence:
	:return: fullcitation
	"""

	hexsequence = hexsequence.group(0)
	hexsequence = highunicodetohex(hexsequence)
	hexsequence = re.split(r'█', hexsequence)
	hexsequence.reverse()
	hexsequence.pop()
	fullcitation = ''

	while (len(hexsequence) > 0):
		# left is the first digit and the level marker: 0x8N, 0x9N, 0xAN
		# 8 --> level00; 9 --> level01; A--> level02; ...
		# right is the "action to take"
		try:
			instructions = hexsequence.pop()
			textlevel, action = nybbler(instructions)
		except:
			textlevel = 6
			action = -1

		# print('textlevel, action', textlevel, action)
		if textlevel < 6:
			# you will get 'level 7' with an 'ff' which really means 'stop parsing'
			if action == 0:
				fullcitation += '\n<hmu_increment_level_{tl}_by_1 />'.format(tl=textlevel)
			elif (action > 0) and (action < 8):
				fullcitation += '<hmu_set_level_{tl}_to_{a} />'.format(tl=textlevel, a=action)
			elif action == 8:
				citation, hexsequence = nyb08(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel,c=citation)
			elif action == 9:
				citation, hexsequence = nyb09(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			elif action == 10:
				citation, hexsequence = nyb10(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			elif action == 11:
				citation, hexsequence = nyb11(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			elif action == 12:
				citation, hexsequence = nyb12(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			elif action == 13:
				citation, hexsequence = nyb13(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			elif action == 14:
				citation, hexsequence = nyb14(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			elif action == 15:
				citation, hexsequence = nyb15(hexsequence)
				fullcitation += '<hmu_set_level_{tl}_to_{c} />'.format(tl=textlevel, c=citation)
			else:
				# impossible to reach this
				fullcitation += '<hmu_unhandled_right_byte_value_{a} />'.format(a=action)
		elif textlevel == 6:
			fullcitation, hexsequence = levelsixparsing(action, fullcitation, hexsequence)

	return fullcitation


#
# a collection of tiny byte-by-byte cases that is closely attached to citationbuilder
# was useful when originally coding, but easily refactored if you decide that this is all bug free...
#

def nybbler(singlehexval):
	"""
	take a character and split it into two chunks of info: 'textlevel' on left and 'action' on right
	:param singlehexstring:
	:return: textlevel, action
	"""
	
	intval = int(singlehexval, 16)
	textlevel = (intval & int('70', 16)) >> 4
	action = (intval & int('0f', 16))
	
	return textlevel, action


def nyb08(hexsequence):
	# 8 -> read 7 bits of next number [& int('7f', 16)]
	if len(hexsequence) > 0:
		citation = str(int(hexsequence.pop(),16) & int('7f', 16))
	else:
		citation = '[unk_nyb_08]'

	return citation, hexsequence


def nyb09(hexsequence):
	#   9 -> read a number and then a character
	if len(hexsequence) > 0:
		citation = str(int(hexsequence.pop(), 16) & int('7f', 16))
	else:
		citation = '[unk_nyb_09]'
	if len(hexsequence) > 0:
		popped = hexsequence.pop()
		if int(popped, 16) != int('ff', 16):
			citation += chr(int(popped, 16) & int('7f', 16))

	return citation, hexsequence


def nyb10(hexsequence):
	# 10 -> read a number and then an ascii string
	if len(hexsequence) > 0:
		citation = str(int(hexsequence.pop(), 16) & int('7f', 16))
		stop = False
		while hexsequence and stop == False:
			popped = hexsequence.pop()
			if int(popped,16) != int('ff',16):
				citation += chr(int(popped, 16) & int('7f', 16))
			else:
				stop = True
	else:
		citation = '[unk_nyb_10]'

	return citation, hexsequence


def nyb11(hexsequence):
	# 11 -> next two bytes are a 14 bit number
	if len(hexsequence) > 1:
		firstbyte = int(hexsequence.pop(),16) & int('7f', 16)
		secondbyte = int(hexsequence.pop(),16) & int('7f', 16)
		citation = str((firstbyte << 7) + secondbyte)
	else:
		citation = '[unk_nyb_11]'
		hexsequence = []
	return citation, hexsequence


def nyb12(hexsequence):
	# 12 -> a 2-byte number, then a character
	citation = ''
	if len(hexsequence) > 0:
		firstbyte = int(hexsequence.pop(),16) & int('7f', 16)
	else:
		citation += '[unk_nyb_12a]'
	if len(hexsequence) > 0:
		secondbyte = int(hexsequence.pop(),16) & int('7f', 16)
		citation = str((firstbyte << 7) + secondbyte)
	else:
		citation += '[unk_nyb_12b]'
	if len(hexsequence) > 0:
		citation += chr(int(hexsequence.pop(), 16) & int('7f', 16))
	else:
		citation += '[unk_nyb_12c]'
	return citation, hexsequence


def nyb13(hexsequence):
	# 13 -> a 2-byte number, then a string
	citation = ''
	if len(hexsequence) > 0:
		firstbyte = int(hexsequence.pop(),16) & int('7f', 16)
	else:
		citation += '[unk_nyb_13a]'
	if len(hexsequence) > 0:
		secondbyte = int(hexsequence.pop(),16) & int('7f', 16)
		citation = str((firstbyte << 7) + secondbyte)
	else:
		citation += '[unk_nyb_13b]'

	if len(hexsequence) > 0:
		string, hexsequence = nyb15(hexsequence)
		citation += string
	else:
		citation += '[unk_nyb_13b]'

	return citation, hexsequence


def nyb14(hexsequence):
	# 14 -> append a char to the counter number
	# this will not work properly right now: merely replacing, not appending; need to find a test case
	# gellius has one. somewhere...
	citation = ''
	if len(hexsequence) > 0:
		citation += chr(int(hexsequence.pop(), 16) & int('7f', 16))
	else:
		citation += '[unk_nyb_14]'

	return citation, hexsequence


def nyb15(hexsequence):
	# 15 -> an ascii string follows
	citation = ''
	stop = False
	while hexsequence and stop == False:
		popped = hexsequence.pop()
		if int(popped, 16) != int('ff', 16):
			citation += chr(int(popped, 16) & int('7f', 16))
		else:
			stop = True

	return citation, hexsequence


#
# because level6 is its own world
#


def levelsixparsing(action, fullcitation, hexsequence):
	metadata = {}
	metadatacategories = {
		0: 'newauthor',
		1: 'newwork',
		2: 'workabbrev',
		3: 'authabbrev',
		97: 'region', # 'a'
		98: 'city', # 'b'
		99: 'notes', # 'c' (will be textdirection in INS/DDP)
		100: 'date', # 'd'
		101: 'publicationinfo', # 'e'
		102: 'additionalpubinfo', # 'f'
		103: 'stillfurtherpubinfo', # 'g'
		108: 'provenance', # 'l'
		114: 'reprints', # 'r'
		116: 'unknownmetadata116', # 't'
		122: 'documentnumber' # 'z'
		}

	try:
		category = int(hexsequence.pop(), 16) & int('7f', 16)
	except:
		category = ''
	if action == 0:
		if category == 1:
			fullcitation += '\n<hmu_increment_work_number_by_1 />'
		citation = ''
	elif 0 < action < 8:
		citation, hexsequence = nyb15(hexsequence)
	elif action == 8:
		citation, hexsequence = nyb08(hexsequence)
	elif action == 9:
		citation, hexsequence = nyb09(hexsequence)
	elif action == 10:
		citation, hexsequence = nyb10(hexsequence)
	elif action == 11:
		citation, hexsequence = nyb11(hexsequence)
	elif action == 12:
		citation, hexsequence = nyb12(hexsequence)
	elif action == 13:
		citation, hexsequence = nyb13(hexsequence)
	elif action == 14:
		citation, hexsequence = nyb14(hexsequence)
	elif action == 15:
		citation, hexsequence = nyb15(hexsequence)
	else:
		citation = ''

	metadata[metadatacategories[category]] = citation

	for key in metadata.keys():
		# should actually only be one key, but we don't know which one it is in advance
		if len(metadata[key]) > 0:
			v = regex_substitutions.replaceaddnlchars(metadata[key])
			v = re.sub(r'`','', v)
			# print('<hmu_metadata_{k} value="{v}" />'.format(k=key,v=v))
			fullcitation += '<hmu_metadata_{k} value="{v}" />'.format(k=key,v=v)

	return fullcitation, hexsequence

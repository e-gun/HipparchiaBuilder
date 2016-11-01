# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re

from builder.parsers.swappers import highunicodetohex


def citationbuilder(hexsequence):
	"""
	NOTE: expects a call from re.sub and so you need a match.group()
	parse the sequence of bytes for instructions on how to build a citatation
	"0xab 0x82 0xff 0x9f 0xe1 0xff" ==> <set_level_2_to_383>\n<set_level_1_to_a>\n
	:param hexsequence:
	:return: fullcitation
	"""

	hexsequence = hexsequence.group(0)
	# old format:
	#hexsequence = re.split(r'0x', hexsequence)
	# new format
	hexsequence = highunicodetohex(hexsequence)
	hexsequence = re.split(r'█', hexsequence)
	hexsequence.reverse()
	hexsequence.pop()
	fullcitation = ''
	while (len(hexsequence)>0):
		# left is the first digit and the level marker: 0x8N, 0x9N, 0xAN
		# right is the "action to take"
		textlevel,action = nybbler(hexsequence.pop())
		if textlevel < 5:
			# you will get 'level 7' with an 'ff' which really means 'stop parsing'
			if action == 0:
				fullcitation += '\n<hmu_increment_level_'+str(textlevel)+'_by_1 />'
			elif (action > 0) and (action < 8):
				fullcitation += '<hmu_set_level_'+str(textlevel)+'_to_'+str(action)+' />'
			elif action == 8:
				citation, hexsequence = nyb08(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			elif action == 9:
				citation, hexsequence = nyb09(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			elif action == 10:
				citation, hexsequence = nyb10(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			elif action == 11:
				citation, hexsequence = nyb11(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			elif action == 12:
				citation, hexsequence = nyb12(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			elif action == 13:
				citation, hexsequence = nyb13(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			elif action == 14:
				citation, hexsequence = nyb14(hexsequence)
				# this was producing some crazy results that did not match the Diogenes Base.pm description of nybble14
				# it looks like strings were following: so send things to nyb15 as an experiment
				# the string that emerges is a locus that tells you the source of a cited text...
				# these were all false positives because texlevel 6 was not handled properly
				# citation, hexsequence = nyb14b(hexsequence)
				# fullcitation += '<cited_at value="' + citation + '" />'
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'

			elif action == 15:
				citation, hexsequence = nyb15(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation+' />'
			else:
				fullcitation += '<hmu_unhandled_right_byte_value_'+str(action)+' />'
		elif textlevel == 6:
			if action == 15:
				# coming up is a string that tells you the ancient citation that gives us this material
				# i have no idea what the next byte does...
				# Diogenes is confused too?
				citation, hexsequence = level06action15(hexsequence)
				citation = re.sub(r'\&\d{0,1}', '', citation)
				fullcitation += '<hmu_annotations value="' + citation + '" />'
			elif action == 8:
				# stuff that was confusing the parser: tempting to just toss it
				# diogenes callis it 'redundant info (?)' and 'a-z levels'
				# typically looks like a two-byte counter of some sort: '0xfa 0xaf', '0xfa 0xb0', '0xfa 0xb1',...
				# but in debugging Cicero's letters you can get the followsing sequence of actions:
				# [a] <hmu_increment_level_2_by_1 />
				# [b] <hmu_set_level_1_to_sa />
				# [c] 'level 6, action 8' and then material that will decode to 'zolin Tusculanoodex. Oct. aut in. Nov. 5' if you let it...
				# this is 'level z=25' + two annotations
				
				# just skip
				#hexsequence = ''
				
				# or...
				citation, hexsequence = level06action08(hexsequence)
				fullcitation += '<hmu_supplementary_level_info value="'+ citation + '" />'

			elif action == 11:
				# again, just junking things: this might easily break stuff
				# always three
				hexsequence = ''
			elif action == 5:
				# this one is mysterious...
				# action 5 at lvl6 with a hexsequence of size 23 ['fa ', '82 ', 'fa ', 'eb ', 'ff ', 'cd ', 'b0 ', 'b6 ', 'a0 ', 'ac ', 'b7 ', 'b5 ', 'b2 ', 'a0 ', 'a6 ', 'ae ', 'f4 ', 'f5 ', 'e1 ', 'e5 ', 'c8 ', 'ae ', 'f2 ']
				# action 5 at lvl6 with a hexsequence of size 19 ['fa ', '82 ', 'fa ', 'eb ', 'ff ', 'cd ', 'b0 ', 'b6 ', 'a0 ', 'ac ', 'b7 ', 'b5 ', 'b2 ', 'a0 ', 'a6 ', 'ae ', 'f4 ', 'f5 ', 'e1 ']
				# we actually botched something before this point, though
				hexsequence = hexsequence[:-2]
			else:
				# level06popper(10, hexsequence)
				# drop everything until you see 'ff' again
				hexsequence = level06kludger(hexsequence)
				# print('citation builder got confused by',debugme)

	return fullcitation


#
# a collection of tiny byte-by-byte cases that is closely attached to citationbuilder
# was useful when originally coding, but easily refactored if you decide that this is all bug free...
#

def nybbler(singlehexstring):
	"""
	take a character and split it into two chunks of info: 'textlevel' on left and 'action' on right
	:param singlehexstring:
	:return: textlevel, action
	"""
	intval = int(singlehexstring, 16)
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
	# trouble popping off an empty stack with this one
	# kludge is just to soldier on...
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
	for h in hexsequence:
		popped = hexsequence.pop()
		if int(popped, 16) != int('ff', 16):
			citation += chr(int(popped, 16) & int('7f', 16))
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
			# is our problem not stopping when we see 'ff'?
			citation += chr(int(popped, 16) & int('7f', 16))
		else:
			stop = True
	return citation, hexsequence


#
# this too was pared off to help with debugging the core logic of the citationbuilder
#


def level06action08(hexsequence):
	# a single ascii char to assign an a-z level [?]
	# then a value [?]
	popped = hexsequence.pop()
	citation = chr(int(popped, 16) & int('7f', 16))
	citation += str(int(hexsequence.pop(), 16) & int('7f', 16))
	
	return citation, hexsequence

def level06action15(hexsequence):
	# this does not correspond to what Diogenes said you should do, but it does yield results...
	# not popping this one...
	hexsequence.reverse()
	citation = ''
	stopper = 0
	try:
		while hexsequence[stopper] != 'ff ':
			stopper += 1
			citation += chr(int(hexsequence[stopper], 16) & int('7f', 16))
		citation = citation[:-1]
		hexsequence = hexsequence[stopper+1:]
	except:
		# passed an empty hexsequence?
		pass
	citation = re.sub(r'\&\d{0,1}', '', citation)
	hexsequence.reverse()
	return citation, hexsequence


def level06popper(popcount, hexsequence):
	if len(hexsequence)< popcount:
		hexsequence = []
	else:
		popcount = popcount * -1
		hexsequence = hexsequence[:popcount]
	return hexsequence


def level06kludger(hexsequence):
	# something went wrong; run ahead to the next 'ff'
	while len(hexsequence)>0:
		if hexsequence.pop() != 'ff ':
			pass
	return hexsequence




# debug cicero's letters and frr
# search = r'((0x[0-9a-f]{1,2}\s){1,})'
# testhex = '0x9a 0x87 0xa8 0xe6 0xf2 0xa9 0xff 0xef 0xe3 0xc9 0xf5 0xec 0xae 0xa0 0xd6 0xe9 0xe3 0xf4 0xef 0xf2 0xa0 0xa6 0xb3 0xd2 0xae 0xcc 0xae 0xcd 0xae 0xa6 0xa0 0xb3 0xb9 0xb7 0xc8 0xe1 0xec 0xed 0xff 0xe3 0xfa'
#
# cit = re.sub(search, citationbuilder, testhex)
# print(cit)

# this yields: <hmu_set_level_0_to_1100-11 />
# cf. <hmu_set_level_0_to_256-25 />
# Aristophanes is full of this stuff: the line number is correct, then '-NN' where NN increments across plays
# not clear what is being communicated by that info

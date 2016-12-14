# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: generate a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re

from builder.parsers.swappers import highunicodetohex
from builder.parsers import regex_substitutions

def citationbuilder(hexsequence):
	fullcitation = testcitationbuilder(hexsequence)

	return fullcitation


def testcitationbuilder(hexsequence):
	"""
	NOTE: expects a call from re.sub and so you need a match.group()
	parse the sequence of bytes for instructions on how to build a citatation
	"0xab 0x82 0xff 0x9f 0xe1 0xff" ==> <set_level_2_to_383>\n<set_level_1_to_a>\n
	:param hexsequence:
	:return: fullcitation
	"""
	
	hexsequence = hexsequence.group(0)
	# old format:
	# hexsequence = re.split(r'0x', hexsequence)
	# new format
	hexsequence = highunicodetohex(hexsequence)
	hexsequence = re.split(r'█', hexsequence)
	hexsequence.reverse()
	hexsequence.pop()
	fullcitation = ''
	while (len(hexsequence) > 0):
		# left is the first digit and the level marker: 0x8N, 0x9N, 0xAN
		# right is the "action to take"
		try:
			instructions = hexsequence.pop()
			textlevel, action = nybbler(instructions)
		except:
			textlevel = 6
			action = -1
		
		#print('textlevel, action', textlevel, action)
		if textlevel < 6:
			# you will get 'level 7' with an 'ff' which really means 'stop parsing'
			if action == 0:
				fullcitation += '\n<hmu_increment_level_' + str(textlevel) + '_by_1 />'
			elif (action > 0) and (action < 8):
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + str(action) + ' />'
			elif action == 8:
				citation, hexsequence = nyb08(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			elif action == 9:
				citation, hexsequence = nyb09(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			elif action == 10:
				citation, hexsequence = nyb10(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			elif action == 11:
				citation, hexsequence = nyb11(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			elif action == 12:
				citation, hexsequence = nyb12(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			elif action == 13:
				citation, hexsequence = nyb13(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			elif action == 14:
				citation, hexsequence = nyb14(hexsequence)
				# this was producing some crazy results that did not match the Diogenes Base.pm description of nybble14
				# it looks like strings were following: so send things to nyb15 as an experiment
				# the string that emerges is a locus that tells you the source of a cited text...
				# these were all false positives because texlevel 6 was not handled properly
				# citation, hexsequence = nyb14b(hexsequence)
				# fullcitation += '<cited_at value="' + citation + '" />'
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			
			elif action == 15:
				citation, hexsequence = nyb15(hexsequence)
				fullcitation += '<hmu_set_level_' + str(textlevel) + '_to_' + citation + ' />'
			else:
				fullcitation += '<hmu_unhandled_right_byte_value_' + str(action) + ' />'
		elif textlevel == 6:
			# if you watch the actions <15 work you will see that this is a counter
			# here's how to do that
			#   citation, hexsequence = nyb15(hexsequence)
			#	fullcitation += '<hmu_supplementary_level_info_'+str(action)+' value="' + citation + '" />'
			#
			# the main thing to appreciate is that the first document of a new work will come out as:
			#   <hmu_supplementary_level_info_1 value="z" />
			# the next document is 2z
			# then we count 3-7z.
			# then z8zx08, 8zx09 (i.e., 8z\t), ...
			# after 8 you jump to 11
			# at 11 this is how you count: z\x01\x00, z\x01\x01, z\x01\x02...
			
			if action == 0:
				print('action: 60')
				# quickdecode(hexsequence)
				try:
					next = hexsequence.pop()
				except:
					next = ''
				if next == '81':
					fullcitation += '\n<hmu_increment_work_number_by_1 />'
					print('increment_work_number')
				else:
					hexsequence.append(next)
			elif 0 < action < 8:
				citation, hexsequence = nyb15(hexsequence)
				if citation == 'z':
					fullcitation += '<hmu_assert_document_number_'+str(action)+ ' />'
				else:
					print('action6',str(action),'not followed by a "z" but by',citation)
			elif action == 8:
				citation, hexsequence = level06action08(hexsequence)
				if citation[0] == 'z':
					fullcitation += '<hmu_assert_document_number_' + citation[1:] + ' />'
				else:
					print('action6',str(action),'not followed by a "z" but by',citation)
			elif action == 11:
				citation, hexsequence = level06action11(hexsequence)
				if citation[0] == 'z':
					fullcitation += '<hmu_assert_document_number_' + citation[1:] + ' />'
				else:
					print('action6',str(action),'not followed by a "z" but by',citation)
			elif action == 12:
				citation, hexsequence = level06action12(hexsequence)
				print('a12',citation)
				fullcitation += '<hmu_lvl6_action12 value="' + citation + '" />'
			elif action == 14:
				citation, hexsequence = level06action14(hexsequence)
				print('a14',citation)
				fullcitation += '<hmu_lvl6_action14 value="' + citation + '" />'
			elif action == 15:
				metadata, hexsequence = documentmetatata(hexsequence)
				# metadata = re.sub(r'\&\d{0,1}', '', metadata)
				fullcitation += metadata
			else:
				# level06popper(10, hexsequence)
				# drop everything until you see 'ff' again
				# hexsequence = level06kludger(hexsequence)
				citation, hexsequence = nyb15(hexsequence)
				fullcitation += '<hmu_supplementary_level_info_'+str(action)+' value="' + citation + '" />'
				# print('citation builder got confused by (level) (action) (hex):', textlevel, action, hexsequence)
				# quickdecode(hexsequence)
	
	return fullcitation


def workingcitationbuilder(hexsequence):
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
		if textlevel < 6:
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
	if len(hexsequence) == 2:
		popped = hexsequence.pop()
		citation = chr(int(popped, 16) & int('7f', 16))
		citation += str(int(hexsequence.pop(), 16) & int('7f', 16))
	else:
		print('l6a8 did not receive 2 bytes. instead saw:',hexsequence)
		citation = ' '

	return citation, hexsequence


def level06action11(hexsequence):
	# z + next two bytes are a 14 bit number
	if len(hexsequence) > 2:
		firstbyte = chr(int(hexsequence.pop(), 16) & int('7f', 16))
		secondbyte = int(hexsequence.pop(),16) & int('7f', 16)
		thridbyte = int(hexsequence.pop(),16) & int('7f', 16)
		citation = firstbyte + str((secondbyte << 7) + thridbyte)
	else:
		citation = '[failed_level06action11]'
		hexsequence = []
	return citation, hexsequence


def level06action12(hexsequence):
	"""
	passthrough to another function
	:param hexsequence:
	:return:
	"""

	# looks like you are seeing a run of 3 or 4:
	# ['e1 ', '82 ', 'fa ', 'eb ', 'ff ', 'e5 ', 'ef ', 'f0 ', 'b1 ', '81 ', 'e4 ']


	print('12', hexsequence)
	citation, hexsequence = nyb12(hexsequence)
	popped = hexsequence.pop()
	citation += chr(int(popped, 16) & int('7f', 16))
	# citation, hexsequence = nyb15(hexsequence)
	print('a12', citation)

	return citation, hexsequence


def level06action14(hexsequence):
	"""
	passthrough to another function
	:param hexsequence:
	:return:
	"""

	# two?
	# 'fa ', 'e1 ', 'ff '
	# citation, hexsequence = nyb14(hexsequence)
	citation, hexsequence = nyb11(hexsequence)
	print('a14', citation, hexsequence)
	
	return citation, hexsequence


def level06action15(hexsequence):
	hexsequence.reverse()
	citation = ''
	while len(hexsequence) > 1:
		item = hexsequence.pop()
		if item != 'ff':
			citation += chr(int(item, 16) & int('7f', 16))
		else:
			break
	
	citation = regex_substitutions.replaceaddnlchars(citation)
	hexsequence.reverse()


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


def documentmetatata(hexsequence):
	message = ''
	# quickdecode(hexsequence)
	metadata = {}
	metadata['annotations'] = ''
	try:
		popped = hexsequence.pop()
		# print(chr(int(popped, 16) & int('7f', 16)))
		if int(popped, 16) & int('7f', 16) == 0:
			metadata['newauthor'], hexsequence = nyb15(hexsequence)
		elif int(popped, 16) & int('7f', 16) == 1:
			metadata['newwork'], hexsequence = nyb15(hexsequence)
		elif int(popped, 16) & int('7f', 16) == 2:
			metadata['workabbrev'], hexsequence = nyb15(hexsequence)
		elif int(popped, 16) & int('7f', 16) == 3:
			metadata['authabbrev'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'a':
			# popped = 'e1'
			metadata['region'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'b':
			# popped = 'e2'
			metadata['city'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'c':
			# popped = 'e3'
			metadata['textdirection'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'd':
			# popped = 'e4'
			metadata['date'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'e':
			# popped = 'e5'
			metadata['publicationinfo'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'l':
			metadata['provenance'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 't':
			metadata['unkownmetadata'], hexsequence = nyb15(hexsequence)
		elif chr(int(popped, 16) & int('7f', 16)) == 'r':
			metadata['reprints'], hexsequence = nyb15(hexsequence)
		else:
			# we were reading a string
			m, hexsequence = nyb15(hexsequence)
			if len(m) > 0:
				metadata['annotations'] += m
		for key in metadata.keys():
			# should actually only be one key, but we don't know which one it is in advance
			if len(metadata[key]) > 0:
				message += '<hmu_metadata_' + key + ' value="' + regex_substitutions.replaceaddnlchars(metadata[key]) + '" />'
	except:
		# passed an empty hexsequence?
		pass

	return message, hexsequence

# testing

def quickdecode(hexsequence):
	decode = ''
	for h in hexsequence:
		decode += chr(int(h, 16) & int('7f', 16))
	print('hx\n\t', hexsequence, '\n\t', decode)
	
	return



# debug cicero's letters and frr
# search = r'((0x[0-9a-f]{1,2}\s){1,})'
# testhex = '0x9a 0x87 0xa8 0xe6 0xf2 0xa9 0xff 0xef 0xe3 0xc9 0xf5 0xec 0xae 0xa0 0xd6 0xe9 0xe3 0xf4 0xef 0xf2 0xa0 0xa6 0xb3 0xd2 0xae 0xcc 0xae 0xcd 0xae 0xa6 0xa0 0xb3 0xb9 0xb7 0xc8 0xe1 0xec 0xed 0xff 0xe3 0xfa'
#
#search = r'((█[⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ]{1,2}\s){1,}'
#testhex = '█ⓔⓕ █⑧⓪ █ⓑ⓪ █ⓑ⓪ █ⓑ⑤ █ⓑ⓪ █ⓕⓕ █ⓔⓕ █⑧① █ⓑ⓪ █ⓑ⓪ █ⓑ① █ⓕⓕ █ⓔⓕ █⑧② █ⓕⓕ █ⓔⓕ █⑧③ █ⓓ⓪ █ⓒ⑥ █ⓔ① █ⓕ⑨ █ⓕⓕ █ⓓⓐ █⑧ⓑ █ⓐ⓪ █ⓕ② █ⓕ⓪ █ⓕⓕ █⑧① █ⓔⓕ █ⓔⓒ █ⓓ④ █ⓔ⑧ █ⓔ⑤ █ⓔ① █ⓔ④ █ⓕⓕ █ⓔⓕ █ⓔ④ █ⓔ③ █ⓑ① █ⓑ① █ⓑ⑤ █ⓐ⓪ █ⓒ② █ⓒ③ █ⓕⓕ █ⓔⓕ █ⓕ④ █ⓕⓕ █ⓔⓕ █ⓕ② █ⓒⓓ █ⓒ③ █ⓔ⑧ █ⓕ② █ⓐ⓪ █ⓑ① █ⓑ④ █ⓕⓕ '
#cit = re.sub(search, citationbuilder, testhex)
#print(cit)

# this yields: <hmu_set_level_0_to_1100-11 />
# cf. <hmu_set_level_0_to_256-25 />
# Aristophanes is full of this stuff: the line number is correct, then '-NN' where NN increments across plays
# not clear what is being communicated by that info

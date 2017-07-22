# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from builder.builder_classes import Author, Opus
from builder.parsers.betacodeescapedcharacters import replaceaddnlchars
from builder.parsers.betacodefontshifts import latinauthorlinemarkupprober
from builder.parsers.regex_substitutions import latindiacriticals


def loadauthor(idtfiledatastream, language, uidprefix, dataprefix):
	"""
	read and IDT file's contents and extract author and work info for it
	this is done via a byte-by-byte walk

	this is messy and there are some holes in the logic, but not anywhere that matters?
	specifically, we shifted away from relying on the IDT data all that much

	note, for example the calls to idthexparser() which never get made because, if they did,
	you would soon find out that that function is broken...

	:param idtfiledatastream:
	:param language
	:return: authorobject
	"""

	bytecount = -1
	leveldict = {}

	for byte in range(0, len(idtfiledatastream) - 1):
		# avoid allowing bytecount to get bigger than l and then attempting to read o[bytelcount]
		# but we are attempting to do without the index adjustment problem from the perl
		bytecount += 1

		if bytecount >= len(idtfiledatastream) - 1:
			break

		if idtfiledatastream[bytecount] == 0:
			# allegedly an EOF test via 0x00, but there are a lot of zeroes in the file
			# it's just that the skipping around is supposed to dodge them before you hit one late in the game
			# does anything bad happen if you just pass to the end?
			# print "break at", bytecount
			# break
			pass
		elif (idtfiledatastream[bytecount] == 1) or (idtfiledatastream[bytecount] == 2):
			# subsection = 0
			bytecount = bytecount + 3
			firstbyte = idtfiledatastream[bytecount] << 8
			bytecount += 1
			startblock = firstbyte + idtfiledatastream[bytecount]
			bytecount += 1
			if idtfiledatastream[bytecount] == 239:
				bytecount += 1
				level = idtfiledatastream[bytecount] & int('7f', 16)
				bytecount += 1
				string = getasciistring(idtfiledatastream, bytecount)
				bytecount = bytecount + len(string)
				if level == 0:
					authornumber = string
					# lastwork = 0
					bytecount += 1
					if (idtfiledatastream[bytecount] == 16) and (idtfiledatastream[bytecount + 1] == 0):
						# 0x10 + 0x00 says an author name is coming
						# the length of that name is stored in the next byte
						worklist = []
						bytecount = bytecount + 2
						authorname = getpascalstr(idtfiledatastream, bytecount)
						authorobject = Author(authornumber, language, uidprefix, dataprefix)
						authorobject.idxname = authorname
						bytecount = bytecount + len(authorname)
					else:
						print("Author number apparently was not followed by author name: ", bytecount, " = ",
						      idtfiledatastream[bytecount])
						break
				elif level == 1:
					worknumber = string
					bytecount += 1
					if (idtfiledatastream[bytecount] == 16) and (idtfiledatastream[bytecount + 1] == 1):
						# 0x10 + 0x01 says a work name is coming
						# the length of that name is stored in the next byte
						bytecount += 2
						workname = getpascalstr(idtfiledatastream, bytecount)
						bytecount = bytecount + len(workname)
						grabitall = re.compile(r'(.*?)($)')
						#workname = cleanworkname(workname)
						workname = latinauthorlinemarkupprober(workname, grabber=grabitall)
						workname = replaceaddnlchars(workname)
						# <hmu_fontshift_greek_normal>, etc. might still be in here
						workname = re.sub(r'<.*?>', '', workname)
						workname = latindiacriticals(workname)
						# not going to use this block info
						workstartblock = startblock
						# skipped some code for CIV texts
						bytecount += 1
						# a small number of works seem to wind up one byte short of the '17'
						# some even fall two bytes short...
						# this is no longer true? had been an issue with the pre-mature parsing of words
						# print(workname, '\n\tbcc',idtfiledatastream[bytecount], idtfiledatastream[bytecount+1], idtfiledatastream[bytecount+2])
						if idtfiledatastream[bytecount] != 17 and idtfiledatastream[bytecount+1] == 17:
							bytecount += 1
							print(authornumber,authorname,'\n\twarning: idtparser skipped 1 byte inside of',workname,'in order to find its structure')
						elif idtfiledatastream[bytecount] != 17 and idtfiledatastream[bytecount+2] == 17:
							bytecount += 2
							print(authornumber,authorname,'\n\twarning: idtparser skipped 2 bytes inside of', workname, 'in order to find its structure')
						while idtfiledatastream[bytecount] == 17:
							# ick: a while-loop that might not exit properly, but we need to descend to sublevels
							# each one is set off with an 0x11 at its head
							depth, levellabel = findlabelsforlevels(idtfiledatastream, bytecount)
							leveldict[depth] = levellabel
							bytecount = bytecount + len(levellabel) + 3
						bytecount -= 1
						worklist.append(Opus(authorobject, language, worknumber, workname, leveldict))
						authorobject.addwork(worklist[-1])
						authorobject.workdict[worknumber] = len(authorobject.works)-1
						leveldict = {}
					else:
						print("Work number apparently was not followed by work: ", bytecount, " = ",
						      idtfiledatastream[bytecount])
					# skipped some documentary papyrii code: looks like the kludge is 'set level label 5 to level label 0'
					# print('0->5:',worknumber,bytecount)
				elif level == 2:
					# coded but inactive in the perl
					print("I made it to level 2: sub-works. Will need some more coding.")
			else:
				# not clear that we care at all about this / it's consequences
				# work names that get 'shortened' by one bye because you turn E/ into 'é' seem to kick this up
				print(authornumber,authorname,'\n\twarning: I see a new author or a new work but it is not followed after 5 bytes by EF. bytecount is: ',
				      bytecount)
				pass
		elif (idtfiledatastream[bytecount] == 3):
			# starting blocks for top-level subsections
			# almost none of this matters to us: just keep the bytecount right
			# print(bytecount, " yields a hit with", idtfiledatastream[bytecount])
			if idtfiledatastream[bytecount + 3] == 8:
				block = (idtfiledatastream[bytecount + 1] << 8) + idtfiledatastream[bytecount + 2]
			else:
				print(authornumber,authorname,'\n\twarning: New section not followed by beginning ID. Byetecount is:',bytecount)
			bytecount += 4
			if idtfiledatastream[bytecount] >> 7:
				leftval, offset = idthexparser(idtfiledatastream, bytecount, idtfiledatastream[bytecount] >> 7)
				bytecount += offset
		elif (idtfiledatastream[bytecount] == 10):
			bytecount += 1
			if idtfiledatastream[bytecount] >> 7:
				leftval, offset = idthexparser(idtfiledatastream, bytecount, idtfiledatastream[bytecount] >> 7)
				bytecount += offset
			# not sure what we are doing with this yet...
			# diogenes is keeping track of blocks with this code
			# currentblock += 1
		elif (idtfiledatastream[bytecount] == 11) or (idtfiledatastream[bytecount] == 13):
			# ignored exceptions
			bytecount += 2

	# a kudge to force the inscriptions and papyri to conform to our model
	if authorobject.universalid[0:2] in ['in', 'dp']:
		for w in authorobject.works:
			w.structure = {0: 'line', 1: 'document'}
		

	return authorobject


# support functions

def getasciistring(filearray, offset):
	# Subroutine to get a string from filearray until a \xff is hit,
	# returns a string and you will need to update bytecount by the length of that string to skip ahead again
	asciistring = ''
	for c in range(offset, len(filearray)):
		if filearray[c] == 255:
			break
		asciistring += chr(filearray[c] & int('7f', 16))
	return asciistring


def getpascalstr(filearray, offset):
	# Subroutine to extract pascal-style strings with the length byte first
	pascalstr = ''
	strLen = filearray[offset]
	offset += 1
	for c in range(offset, offset + strLen):
		pascalstr += chr(filearray[c])
	return pascalstr


def idthexparser(filearray, offset, code):
	"""

	BROKEN FUNCTION: SHOULD BE REMOVED

	hexrunner is smarter? but how much value is there in merging the code?

	parse a non-ascii bookmark that sets or increments one of the counters that keep track of what line, chapter, book, etc. we are currently at
	the perl function retruns all sorts of random things at various junctures if various conditions are met: a fairly unclean function
	things you might return to worry about:
		a new bytecount position
	   the newLeftvalue
	at the moment we return a tuple with these, but more things are afoot than that?

	*plenty* of this code is actually broken, but you never hit the parts that call unimported libraries and uninitialized variables

	this function should be deleted; but if loadauthor() ever called it, you would want to see the error messages

	:param filearray:
	:param offset:
	:param code:
	:return: a tuple - see above
	"""

	# left nybble: usually gives the level of the counter being modified.
	# right nybble: dictates the form of the upcoming data (when > 8).
	left = (code & int('70', 16)) >> 4
	right = code & int('0f', 16)

	# 7 is EOB, EOF, or end of string, and should not be encountered here.
	# 6 (apart from 0xef as end of string, which is handled elsewhere) seems
	# to have been used in newer PHI disks ( >v.5.3 -- eg. Ennius).  The
	# earlier disks don't have this info, and it doesn't add much, so
	# we might consider throwing it away (see below, where is is used).
	# 5 is the top level counter for the DDP disks.

	newbytecountoffset = 0

	if left == 7:
		# These bytes are found in some versions of the PHI disk (eg. Phaedrus)
		# God knows what they mean.  phi2ltx says they mark the beginning and
		# end of an "exception".
		if (code == '\xf8') or (code == '\xf9'):
			return
		else:
			sys.exit('The parser is confused')
	if left == 6:
		# This is redundant info (?), since earlier versions of the
		# disks apparently omit it and do just fine.
		# This are the a -- z levels: encoded ascii!!
		# [skipped some stuff the was commented out]

		# throwing info away
		newbytecountoffset = 1
		if (right == 8) or (right == 10):
			newbytecountoffset += 1
		if (right == 9) or (right == 11) or (right == 13):
			newbytecountoffset += 2
		if (right == 12):
			newbytecountoffset += 3
		if (right == 9) or (right == 11) or (right == 13):
			print("found junk")
			junk = getasciistring(filearray, offset + newbytecountoffset)
			newbytecountoffset += len(junk)

	# NB. All lower levels go to one when an upper one changes.
	# In some texts (like Catullus on the older PHI disks),
	# lower level counters are assumed to go to one, rather than
	# to disappear when higher levels chang

	# this is going to be tricky to translate:
	#   $left and map $self->{level}{$_} = 1, (0 .. ($left - 1));

	newLeftval = None

	if right == 0:
		print("right is 0 and I should do something about that")
	elif (right > 0) and (right < 8):
		newLeftval = right
	elif right == 8:
		# next byte; number only
		newbytecountoffset += 1
		newLeftval = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
	elif right == 9:
		# a number and then a character
		newbytecountoffset += 1
		newLeftval = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newbytecountoffset += 1
		newLeftval += chr(idtfiledatastream[offset + newbytecountoffset] & int('7f', 16))
	elif right == 10:
		# a number + a string
		newbytecountoffset += 1
		newLeftval = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newbytecountoffset += 1
		newLeftval += idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
	elif right == 11:
		# a 14 bit number is inside the next two bytes [!]
		newbytecountoffset += 1
		firstbyte = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newbytecountoffset += 1
		secondbyte = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newLeftval = (firstbyte << 7) + secondbyte
	elif right == 12:
		# a two-byte number + a character
		newbytecountoffset += 1
		firstbyte = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newbytecountoffset += 1
		secondbyte = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newLeftval = (firstbyte << 7) + secondbyte
		newbytecountoffset += 1
		newLeftval += idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
	elif right == 13:
		# a two-byte number + a string
		newbytecountoffset += 1
		firstbyte = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newbytecountoffset += 1
		secondbyte = idtfiledatastream[offset + newbytecountoffset] & int('7f', 16)
		newLeftval = (firstbyte << 7) + secondbyte
		newbytecountoffset += 1
		string = getasciistring(idtfiledatastream, bytecount + newbytecountoffset)
		newLeftval += string
		newbytecountoffset += len(string)
	elif right == 14:
		# only append a char to the (unincremented) counter
		# this has probably been misimplimented: will need to find a place where it happens
		newbytecountoffset += 1
		newLeftval = chr(idtfiledatastream[offset + newbytecountoffset] & int('7f', 16))
	elif right == 15:
		# a string comes next
		newbytecountoffset += 1
		newLeftval = getasciistring(idtfiledatastream, bytecount + newbytecountoffset)
		newbytecountoffset += len(newLeftval)
	else:
		sys.exit('Impossible value for right: ', right)

	# newLeftval = None
	# newbytecountoffset = None

	return newLeftval, newbytecountoffset


def findlabelsforlevels(filearray, offset):
	# a new level starts with '\x11'
	newbytecountoffset = 1
	depth = filearray[offset + newbytecountoffset]
	newbytecountoffset += 1
	levellabel = getpascalstr(filearray, offset + newbytecountoffset)
	return depth, levellabel

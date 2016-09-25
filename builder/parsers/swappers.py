def highunicodetohex(highunicode):
	"""
	detransform the hexruns
	:param highunicode:
	:return:
	"""
	outvals = u'0123456789abcdef'
	invals = u'⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ'
	hexsequence = highunicode.translate(str.maketrans(invals, outvals))
	
	return hexsequence


def hutohxgrouper(matchgroup):
	x = matchgroup.group(0)
	x = highunicodetohex(x)
	
	return x

def hextohighunicode(twocharhexstring):
	"""
	detransform the hexruns
	:param twocharhexstring:
	:return:
	"""
	invals = u'0123456789abcdef'
	outvals = u'⓪①②③④⑤⑥⑦⑧⑨ⓐⓑⓒⓓⓔⓕ'
	transformed = twocharhexstring.translate(str.maketrans(invals, outvals))
	
	return transformed


def bitswapchars(valuelist):
	"""
	remove the mask from a char
	:param valuelist:
	:return:
	"""
	ascii = ''
	for hv in valuelist:
		ascii += chr(int(hv, 16) & int('7f', 16))
	return ascii
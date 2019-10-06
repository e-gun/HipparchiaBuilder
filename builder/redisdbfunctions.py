# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import pickle
from multiprocessing import current_process
from typing import List

from click import secho

from builder.workers import setworkercount

try:
	import redis
except ImportError:
	if current_process().name == 'MainProcess':
		secho('redis unavailable', fg='bright_black')
	redis = None

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf8')


class NullRedis(object):
	def __init__(self):
		pass

	class client():
		def Redis(self):
			pass


if not redis:
	redis = NullRedis()


class PooledRedisBorg(object):
	"""

	set up a connection pool to redis

	we are preventing the destruction of the link to avoid startup costs
	[unfortunately this is not actually yielding increased speed]

	will always use the first item in a list with only one element

	"""

	_pool = list()

	def __init__(self):
		if not PooledRedisBorg._pool:
			poolsize = setworkercount() + 2
			dbid = config['redis']['redisdbid']
			if config['redis']['redisport'] != 0:
				port = config['redis']['redisport']
				redishost = config['redis']['redishost']
				redisconnection = redis.ConnectionPool(host=redishost, port=port, db=dbid, max_connections=poolsize)
			else:
				sock = config['redis']['redissocket']
				redisconnection = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=sock, db=dbid, max_connections=poolsize)
			PooledRedisBorg._pool.append(redisconnection)
			# print('initialized PooledRedisBorg')
		self.pool = PooledRedisBorg._pool[0]
		self.connection = redis.Redis(connection_pool=self.pool)


def establishredisconnection() -> redis.client.Redis:
	"""

	make a connection to redis

	:return:
	"""

	# do it the simple way
	# dbid = config['redis']['redisdbid']
	# if config['redis']['redisport'] != 0:
	# 	port = config['redis']['redisport']
	# 	redisconnection = redis.Redis(host='localhost', port=port, db=dbid)
	# else:
	# 	sock = config['redis']['redissocket']
	# 	redisconnection = redis.Redis(unix_socket_path=sock, db=dbid)

	# do it the borg way
	redisobject = PooledRedisBorg()

	redisconnection = redisobject.connection

	return redisconnection


def buildrediswordlists(wordlistdictionary: dict):
	"""

	k, v is:
		lineuniversalid, listofwords

	rc.type(1): b'set'
	rc.smembers(1): {b'0', b'2', b'1'}
	decode what you retrieve: {x.decode() for x in z}

	:param listofsearchlocations:
	:param searchid:
	:return:
	"""
	print('buildrediswordlists()')
	rc = establishredisconnection()

	keys = wordlistdictionary.keys()
	for k in keys:
		rc.sadd(k, wordlistdictionary[k])

	rc.close()

	return


def deleterediswordlists(keylist):
	rc = establishredisconnection()
	rc.delete(*keylist)
	rc.close()
	return


def buildrediskeylists(uidpiles: list, workers: int):
	print('buildrediskeylists()')
	rc = establishredisconnection()
	# comes as itertools.zip_longest
	uidpiles = list(uidpiles)
	for i in range(workers):
		# don't push a None
		thispile = [x for x in uidpiles[i] if x]
		pilename = 'uidpile_{i}'.format(i=i)
		rc.rpush(pilename, *thispile)

	rc.close()

	return


def deleterediskeylists(workers: int):
	rc = establishredisconnection()
	names = list()
	for i in range(workers):
		pilename = 'uidpile_{i}'.format(i=i)
		names.append(pilename)

	rc.delete(*names)

	rc.close()

	return


def loadredisresults(searchid):
	"""

	search results were passed to redis

	grab and return them

	:param searchid:
	:return:
	"""

	redisfindsid = '{id}_findslist'.format(id=searchid)
	rc = establishredisconnection()
	finds = rc.lrange(redisfindsid, 0, -1)
	# foundlineobjects = [dblineintolineobject(pickle.loads(f)) for f in finds]
	foundlineobjects = [pickle.loads(f) for f in finds]
	return foundlineobjects

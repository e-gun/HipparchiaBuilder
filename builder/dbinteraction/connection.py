# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2
import psycopg2.pool as connectionpool
import threading
import random
import configparser

from builder.workers import setworkercount

config = configparser.ConfigParser()
config.read('config.ini')


def oldsetconnection(config, autocommit=False):
	dbconnection = psycopg2.connect(user=config['db']['DBUSER'], host=config['db']['DBHOST'],
									port=config['db']['DBPORT'], database=config['db']['DBNAME'],
									password=config['db']['DBPASS'])

	if autocommit:
		dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	return dbconnection

def setconnection(autocommit=False, simple=False):
	"""

	set a connection...

	ConnectionObject() derived from HipparchiaServer and shoehorned into the Builder code

	:param config:
	:param autocommit:
	:return:
	"""

	if not simple:
		c = ConnectionObject(readonlyconnection=False, ctype='rw')
	else:
		c = SimpleConnectionObject(readonlyconnection=False, ctype='rw')

	if autocommit:
		c.setautocommit()

	return c


class GenericConnectionObject(object):
	"""

	generic template for the specific connection types

	provides the basic functions less the actual connection and the
	specific connectioncleanup()

	"""

	MPCOMMITCOUNT = 200
	DBUSER = config['db']['DBUSER']
	DBHOST = config['db']['DBHOST']
	DBPORT = config['db']['DBPORT']
	DBNAME = config['db']['DBNAME']
	DBPASS = config['db']['DBPASS']

	def __init__(self, autocommit, readonlyconnection):
		# note that only autocommit='autocommit' will make a difference
		self.autocommit = autocommit
		self.readonlyconnection = readonlyconnection
		self.commitcount = GenericConnectionObject.MPCOMMITCOUNT
		# used for the key for getconn() and putconn(); but unneeded if PersistentConnectionPool
		# also useful to have on hand for debugging
		self.uniquename = self.uniquetablename()
		# the next two must get filled out when the actual connection is made
		self.dbconnection = None
		self.curs = None

	def uniquetablename(self):
		return ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(12)])

	def setautocommit(self):
		# other possible values are:
		# psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
		# psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
		# psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
		# psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	def getautocommit(self):
		return getattr(self.dbconnection, 'autocommit')

	def setdefaultisolation(self):
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)

	def cursor(self):
		return self.curs

	def commit(self):
		getattr(self.dbconnection, 'commit')()

	def close(self):
		return getattr(self, 'connectioncleanup')()

	def setreadonly(self, value):
		assert value in [True, False], 'setreadonly() accepts only "True" or "False"'
		self.commit()
		getattr(self.dbconnection, 'set_session')(readonly=value, autocommit=True)

	def getreadonly(self):
		getattr(self.dbconnection, 'readonly')

	def connectionisclosed(self):
		return self.dbconnection.closed

	def checkneedtocommit(self, commitcountervalue):
		# commitcountervalue is an MPCounter?
		try:
			v = commitcountervalue.value
		except AttributeError:
			v = commitcountervalue
		if v % self.commitcount == 0:
			try:
				getattr(self.dbconnection, 'commit')()
			except psycopg2.DatabaseError:
				# psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
				# will return often-but-not-always '2' as the status: i.e., STATUS_IN_TRANSACTION
				print(self.uniquename, 'failed its commit()')
				status = self.dbconnection.get_transaction_status()
				print('\tConnectionObject {me} status is {s}'.format(me=self.uniquename, s=status))
		return

	def connectioncleanup(self):
		raise NotImplementedError


class PooledConnectionObject(GenericConnectionObject):
	"""

	there can be serious threading issues if you use this:

	a connection must be assigned to each worker *before* you join the MP jobs

	otherwise the different threads will not share the connections properly and you will end
	up with a lot of closed/broken connections

	psycopg connection status values.
		STATUS_SETUP = 0
		STATUS_READY = 1
		STATUS_BEGIN = 2
		STATUS_SYNC = 3  # currently unused
		STATUS_ASYNC = 4  # currently unused
		STATUS_PREPARED = 5

	# This is a useful mnemonic to check if the connection is in a transaction
		STATUS_IN_TRANSACTION = STATUS_BEGIN

	some error messages if you misthread:
		xgkhgwsadbuu - Process-3 failed to commit()
		PooledConnectionObject xgkhgwsadbuu - Process-3 status is 2
		DatabaseError for <cursor object at 0x13ba55428; closed: 0> @ Process-3

	"""

	_pools = dict()

	def __init__(self, autocommit='defaultisno', readonlyconnection=True, ctype='rw'):
		super().__init__(autocommit, readonlyconnection)
		self.cytpe = ctype
		if not PooledConnectionObject._pools:
			# initialize the borg
			# note that poolsize is implicitly a claim about how many concurrent users you imagine having
			poolsize = setworkercount() + 2

			# three known pool types; simple should be faster as you are avoiding locking
			pooltype = connectionpool.SimpleConnectionPool
			# pooltype = connectionpool.ThreadedConnectionPool
			# pooltype = connectionpool.PersistentConnectionPool

			# [A] 'ro' pool
			kwds = {'user': GenericConnectionObject.DBUSER,
			        'host': GenericConnectionObject.DBHOST,
			        'port': GenericConnectionObject.DBPORT,
			        'database': GenericConnectionObject.DBNAME,
			        'password': GenericConnectionObject.DBPASS}

			readonlypool = pooltype(poolsize, poolsize * 2, **kwds)

			# [B] 'rw' pool
			readandwritepool = pooltype(poolsize, poolsize * 2, **kwds)

			PooledConnectionObject._pools['ro'] = readonlypool
			PooledConnectionObject._pools['rw'] = readandwritepool

		assert self.cytpe in ['ro', 'rw'], 'connection type must be either "ro" or "rw"'
		self.pool = PooledConnectionObject._pools[self.cytpe]

		if self.cytpe == 'rw':
			self.readonlyconnection = False

		if threading.current_thread().name == 'vectorbot':
			# the vectobot lives in a thread and it will exhaust the pool
			self.simpleconnectionfallback()
		else:
			try:
				self.dbconnection = self.pool.getconn(key=self.uniquename)
			except psycopg2.pool.PoolError:
				# the pool is exhausted: try a basic connection instead
				# but in the long run should probably make a bigger pool/debug something
				print('PoolError: fallback to SimpleConnectionObject()')
				self.simpleconnectionfallback()

		if self.autocommit == 'autocommit':
			self.setautocommit()

		self.setreadonly(self.readonlyconnection)
		self.curs = getattr(self.dbconnection, 'cursor')()

	def simpleconnectionfallback(self):
		# print('SimpleConnectionObject', self.uniquename)
		c = SimpleConnectionObject(autocommit=self.autocommit, readonlyconnection=self.readonlyconnection,
		                           ctype=self.cytpe)
		self.dbconnection = c.dbconnection
		self.connectioncleanup = c.connectioncleanup

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		:param cursor:
		:param dbconnectiononnection:
		:return:
		"""

		self.commit()
		self.dbconnection.set_session(readonly=False)
		self.setdefaultisolation()
		self.pool.putconn(self.dbconnection, key=self.uniquename)
		# print('connection returned to pool:', self.uniquename)

		return


class SimpleConnectionObject(GenericConnectionObject):
	"""

	open a connection to the db

	mirror psycopg2 methods

	add connectioncleanup() to the mix

	"""

	def __init__(self, autocommit='defaultisno', readonlyconnection=True, ctype='rw'):
		super().__init__(autocommit, readonlyconnection)
		assert ctype in ['ro', 'rw'], 'connection type must be either "ro" or "rw"'
		if ctype != 'rw':
			u = GenericConnectionObject.DBUSER
			p = GenericConnectionObject.DBPASS
		else:
			u = GenericConnectionObject.DBUSER
			p = GenericConnectionObject.DBPASS
			self.readonlyconnection = False

		self.dbconnection = psycopg2.connect(user=u,
		                                     host=GenericConnectionObject.DBHOST,
		                                     port=GenericConnectionObject.DBPORT,
		                                     database=GenericConnectionObject.DBNAME,
		                                     password=p)

		if self.autocommit == 'autocommit':
			self.setautocommit()

		self.setreadonly(self.readonlyconnection)
		self.curs = getattr(self.dbconnection, 'cursor')()

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		this overkill is mostly a legacy of the FreeBSD bug-hunt

		:param cursor:
		:param dbconnectiononnection:
		:return:
		"""

		self.commit()

		getattr(self.curs, 'close')()
		del self.curs

		getattr(self.dbconnection, 'close')()
		del self.dbconnection
		# print('deleted connection', self.uniquename)

		return


if 0 > 1:
	class ConnectionObject(SimpleConnectionObject):
		pass
else:
	class ConnectionObject(PooledConnectionObject):
		pass

# -*- coding: utf-8 -*-
"""
	HipparchiaBuilder: compile a database of Greek and Latin texts
	Copyright: E Gunderson 2016-23
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from multiprocessing import Process
from multiprocessing.managers import ListProxy

from builder.dbinteraction.connection import icanpickleconnections, setconnection
from builder.workers import setworkercount


class GenericInserterObject(object):

	def __init__(self, targetfunction, argumentlist=None):
		self.workercount = setworkercount()
		self.targetfunction = targetfunction
		self.argumentlist = argumentlist
		assert self.argumentlist is not None, "Failed to pass an argumentlist to GenericInserterObject()"
		assert isinstance(self.argumentlist, list), "Failed to pass argumentlist as a list() to GenericInserterObject()"
		managedlistpresent = {a for a in self.argumentlist if isinstance(a, ListProxy)}
		assert len(managedlistpresent) != 0, "Failed to pass a managed list inside of the argumentlist passed to GenericInserterObject()"

		if not icanpickleconnections():
			self.connections = [None for _ in range(self.workercount)]
			self.cleanup = self._nocleanup
		else:
			self.connections = {i: setconnection() for i in range(self.workercount)}
			self.cleanup = self._cleanup

	def dothework(self):
		argumentttuples = [tuple(self.argumentlist + [self.connections[i]]) for i in range(self.workercount)]
		jobs = [Process(target=self.targetfunction, args=argumentttuples[i]) for i in range(self.workercount)]

		for j in jobs:
			j.start()
		for j in jobs:
			j.join()

		self.cleanup()

	def _cleanup(self):
		for c in self.connections:
			self.connections[c].connectioncleanup()

	def _nocleanup(self):
		pass

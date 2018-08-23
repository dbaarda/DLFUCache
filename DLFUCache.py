"""Decaying LFU Cache Class

This is a basic implementation of a decaying LFU caching class, as documented at;

http://minkirri.apana.org.au/wiki/DecayingLFUCacheExpiry

Author  : Donovan Baarda <abo@minkirri.apana.org.au>
License : LGPL
Download: ftp://minkirri.apana.org.au/~abo/projects/DLFUCache/

Requires: time, UserDict,
        PQueue      (by Andrew Snare <ajs@cs.monash.edu.au>),

Usage:


Where:

"""
import collections
from PQueue import DictPQueue

class DLFUCache(collections.MutableMapping):

  def __init__(self, size, msize=None, T=4.0):
    if msize is none:
      msize = size
    self.size = size
    self.msize = msize
    self.data = {}
    self.cqueue = DictPqueue()
    self.mqueue = DictPqueue()
    self.C = 1.0
    self.T = T * size
    self.M = (self.T + 1.0) / self.T
    self.reset_stats()

  def reset_stats(self):
    self.get_count = 0
    self.set_count = 0
    self.del_count = 0
    self.hit_count = 0
    self.mhit_count = 0

  def _setmqueue(self, k, p):
    if len(self.mqueue) == self.msize:
      self.pqueue.swapitem(k, p)
    elif self.msize > 0:
      self.mqueue[k] = p

  def _setcqueue(self, k, p):
    if len(self.cqueue) == self.size:
      mink, minp = self.cqueue.swapitem(k, p)
      self._setmqueue(mink, minp)
      del self.data[k]
    else:
      self.cqueue[k] = p

  def __getitem__(self, key):
    self.get_count += 1
    # Exponentially grow increment C.
    self.C *= self.M
    # If C has reached 2, exponentially decay C and all counts back to 1.0.
    if self.C >= 2.0:
      decay = 1.0 / self.C
      self.cqueue.mult(decay)
      self.mqueue.mult(decay)
      self.C = 1.0
    if key in self.cqueue:
      self.cqueue[key] += self.C
      self.hit_count += 1
    elif key in self.mqueue:
      self.mqueue[key] += self.C
      self.mhit_count += 1
    else:
      self._setmqueue(key, self.C)
    return self.data[key]

  def __setitem__(self, key, value):
    if key in self.mqueue:
      k, p = self.mqueue.pullitem(key)
      self._setcqueue(k, p)
    elif key not in self.cqueue:
      self._setcqueue(key, self.C)
    self.data[key] = value

  def __delitem__(self, key):
    self.data.pop(key)
    k, p = self.cqueue.pullitem(key)
    self._setmqueue(k, p)

  def __iter__(self):
    return iter(self.data)

  def __len__(self):
    return len(self.data)

  def getcount(self, key):
    if key in self.cqueue:
      return self.cqueue[key] / self.C
    if key in self.mqueue:
      return self.mqueue[key] / self.C
    return 0.0

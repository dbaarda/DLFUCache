"""ARC Cache Class

This is a basic implementation of an ARC caching class.

Author  : Donovan Baarda <abo@minkirri.apana.org.au>
License : LGPL
Download: http://minkirri.apana.org.au/~abo/projects/DLFUCache/
          https://github.com/dbaarda/DLFUCache
"""
import collections
import itertools
from collections import abc


class ARCCache(abc.MutableMapping):
  """ARC Cache

  This implements the ARC cache reference algorithm modified to be a
  look-aside cache with separate get/set/del operations. This changes
  some of the invariants about the lengths of b1/t1/t2/b2 since
  entries can be deleted from a full cache. The reference algorithm is
  documented in;

  http://www2.cs.uh.edu/~paris/7360/PAPERS03/arcfast.pdf

  Attributes:
    size : the number of entries in the cache.
    p: the learned target size of t1.
    t1,t2: OrderedDicts containing cached data.
    b1,b2: OrderedDict shadow entries (contains None).
    get_count: The count of get operations.
    set_count: The count of set operations.
    del_count: The count of del operations.
    hit_count: The count of cache hits.
    mhit_count: The count of metadata (b1 + b2) hits.

  Properties:
    hit_rate: The hit_rate for cache entries.
    mhit_rate: The hit_rate for extra metadata.
  """

  def __init__(self, size):
    self.size = size
    self.p = 0
    self.t1 = collections.OrderedDict()
    self.b1 = collections.OrderedDict()
    self.t2 = collections.OrderedDict()
    self.b2 = collections.OrderedDict()
    self.reset_stats()

  def clear(self):
    self.p = 0
    self.t1.clear()
    self.b1.clear()
    self.t2.clear()
    self.b2.clear()
    self.reset_stats()

  def reset_stats(self):
    self.get_count = 0
    self.set_count = 0
    self.del_count = 0
    self.hit_count = 0
    self.mhit_count = 0

  @property
  def hit_rate(self):
    """The cache contents hit rate."""
    if 0 < self.get_count:
      return self.hit_count / self.get_count
    return nan

  @property
  def mhit_rate(self):
    """The extra metadata hit rate."""
    if 0 < self.get_count:
      return self.mhit_count / self.get_count
    return nan

  def _replace(self, key):
    """Evict an item out of the cache for replacement by key."""
    # If T1 + T2 is not full (possible from deletes), do nothing.
    if len(self.t1) + len(self.t2) < self.size:
      return
    # T1 longer than p or equal to p and key in B2 or T2 empty.
    if (len(self.t1) > self.p) or (0 < len(self.t1) == self.p and key in self.b2) or not self.t2:
      oldk, _ = self.t1.popitem(False)
      self.b1[oldk] = None
    # T1 shorter than p or equal to p and key not in b2 and T2 not empty.
    else:
      oldk, _ = self.t2.popitem(False)
      self.b2[oldk] = None

  def __getitem__(self, key):
    self.get_count += 1
    # Get the value from T1 or T2 or raise KeyError for a miss.
    if key in self.t1:
      value = self.t1.pop(key)
    else:
      value = self.t2.pop(key)
    self.hit_count += 1
    # Move the entry to the end of T2.
    self.t2[key] = value
    return value

  def __setitem__(self, key, value):
    self.set_count += 1
    # if the key is in t1 or t2, just update them.
    if key in self.t1:
      self.t1[key] = value
    elif key in self.t2:
      self.t2[key] = value
    # A b1 hit, move to end of t2.
    elif key in self.b1:
      self.mhit_count += 1
      self.p = min(self.size, self.p + max(len(self.b2) // len(self.b1), 1))
      self._replace(key)
      self.b1.pop(key)
      self.t2[key] = value
    # A b2 hit, move to end of t2,
    elif key in self.b2:
      self.mhit_count += 1
      self.p = max(0, self.p - max(len(self.b1) // len(self.b2), 1))
      self._replace(key)
      self.b2.pop(key)
      self.t2[key] = value
    else:
      self._replace(key)
      # L1 full, pop an entry off b1.
      if len(self.t1) + len(self.b1) == self.size:
        # Note: b1 cannot be empty after replace if L1 is full.
        self.b1.popitem(False)
      # L1+L2 full, pop an entry of b2.
      elif len(self.b1) + len(self.t1) + len(self.t2) + len(self.b2) == 2 * self.size:
        # Note: b2 cannot be empty if L1+L2 is full and L1 is not.
        self.b2.popitem(False)
      self.t1[key] = value

  def __delitem__(self, key):
    if key in self.t1:
      self.t1.pop(key)
      self.b1[key] = None
    else:
      self.t2.pop(key)
      self.b2[key] = None

  def __iter__(self):
    return itertools.chain(iter(self.t1), iter(self.t2))

  def __len__(self):
    return len(self.t1) + len(self.t2)

  def __repr__(self):
    return "%s(size=%s)" % (self.__class__.__name__, self.size)

  def __str__(self):
    return "%r: gets=%i hit=%5.3f mhit=%5.3f p=%d b1=%d t1=%d t2=%d b2=%d" % (
        self, self.get_count, self.hit_rate, self.mhit_rate, self.p,
        len(self.b1), len(self.t1), len(self.t2), len(self.b2))

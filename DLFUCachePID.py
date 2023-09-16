"""Decaying LFU Cache Class

This is a basic implementation of a decaying LFU caching class, as
documented at;

http://minkirri.apana.org.au/wiki/DecayingLFUCacheExpiry

Author  : Donovan Baarda <abo@minkirri.apana.org.au>
License : LGPL
Download: http://minkirri.apana.org.au/~abo/projects/DLFUCache/
          https://github.com/dbaarda/DLFUCache

Requires:
"""
from collections import abc

# Infinity, used to set T decay timeconstant for no decay.
inf = float('inf')
# NaN, used for things like hitrate with zero gets.
nan = float('nan')


class DLFUCache(abc.MutableMapping):
  """Decaying LFU Cache

  Attributes:
    size : the number of entries in the cache.
    msize: the number of extra metadata entries to keep.
    data: the underlying cache dict.
    C: The per-access count increment value.
    T: The per-size-accesses decay timeconstant.
    M: The exponential growth multiplier for C.
    cpid: The cache min_count pid controller.
    mpid: The extra metadata min_count pid controller.
    get_count: The count of get operations.
    set_count: The count of set operations.
    del_count: The count of del operations.
    hit_count: The count of cache hits.
    mhit_count: The count of metadata hits.
    count_sum: the sum of all cache entry counts
    mcount_sum: the sum of all extra metadata counts.
    count_sum2: The sum of the square of all cache entry counts.
    mcount_sum2: the sum of the square of all extra metadata counts.

  Properties:
    count_min: The minimum count value for cache entries.
    count_avg: The average of count values for cache entries.
    count_var: The variance of count values for cache entries.
    count_dev: The stddev of count values for cache entries.
    hit_rate: The hit_rate for cache entries.
    mcount_min: The minimum count value for extra metadata.
    mcount_avg: The average of count values for extra metadata.
    mcount_var: The variance of count values for extra metadata.
    mcount_dev: The stddev of count values for extra metadata.
    mhit_rate: The hit_rate for extra metadata.
    thit_count: The total count of cache+metadata hits.
    tsize: The total number of entries in the cache+metadata.
    tcount_min: The minimum count value for cache+metadata entries.
    tcount_sum: The sum of all cache+metatdata entry counts.
    tcount_sum2: The sum of the square of all cache+metadata entry counts.
    tcount_avg: The average of count values for cache+metadata.
    tcount_var: The variance of count values for cache+metadata.
    tcount_dev: The stddev of count values for cache+metadata.
    thit_rate: The hit_rate for cache+metadata.
  """

  def __init__(self, size, msize=None, T=4.0):
    if msize is None:
      msize = size
    self.size = size
    self.msize = msize
    self.T = T
    if T == 0.0:
      # Behave like LRU with all counts decayed to zero.
      self.M = inf
    elif T == inf:
      # Behave like LFU with no exponential decay of counts.
      self.M = 1.0
    else:
      # Behave like DLFU with exponentail decay of counts.
      self.M = (T*size + 1.0) / (T*size)
    self.data = {}
    self.clear()

  def clear(self):
    self.data.clear()
    self.cnum = 0
    self.mnum = 0
    self.C = 1.0
    self.count_sum = 0.0
    self.mcount_sum = 0.0
    self.count_sum2 = 0.0
    self.mcount_sum2 = 0.0
    self.cpid = PIDController.ZiglerNichols(cls, 1.0, self.T*self.size/4)
    self.mpid = PIDController.ZiglerNichols(cls, 1.0, self.T*self.size/4)
    self.last_get = 0
    self.reset_stats()

  def reset_stats(self):
    self.get_count = 0
    self.set_count = 0
    self.del_count = 0
    self.hit_count = 0
    self.mhit_count = 0

  @property
  def _cqueue_min(self):
    """The cqueue minimum value."""
    return self.cpid.output

  @property
  def _mqueue_min(self):
    """The mqueue minimum value."""
    if self.msize:
      return self.mpid.output
    return nan

  @property
  def _tqueue_min(self):
    """The total queue minimum value."""
    return self._mqueue_min if self.msize else self._cqueue_min

  @property
  def tsize(self):
    """The total number of entries in cache+metadata."""
    return self.size + self.msize

  @property
  def thit_count(self):
    """The total number of cache+metadata hits."""
    return self.hit_count + self.mhit_count

  @property
  def tcount_sum(self):
    """The sum of all cache+metadata entry counts."""
    return self.count_sum + self.mcount_sum

  @property
  def tcount_sum2(self):
    """The sum of the squares of all cache+metadata entry counts."""
    return self.count_sum2 + self.mcount_sum2

  @property
  def count_min(self):
    """The cache contents minimum access count."""
    return self._cqueue_min / self.C

  @property
  def mcount_min(self):
    """The extra metadata minimum access count."""
    return self._mqueue_min / self.C

  @property
  def tcount_min(self):
    """The extra metadata minimum access count."""
    return self._tqueue_min / self.C

  @property
  def count_avg(self):
    """The cache contents access count average."""
    return self.count_sum / (self.C * self.size)

  @property
  def mcount_avg(self):
    """The extra metadata access count average."""
    return self.mcount_sum / (self.C * self.msize) if self.msize else nan

  @property
  def tcount_avg(self):
    """The total cache+metadata access count average."""
    return self.tcount_sum / (self.C * self.tsize)

  @property
  def count_var(self):
    """The cache contents access count variance."""
    return self.count_sum2 / (self.C**2 * self.size) - self.count_avg**2

  @property
  def mcount_var(self):
    """The extra metadata access count variance."""
    return self.mcount_sum2 / (self.C**2 * self.msize) - self.mcount_avg**2 if self.msize else nan

  @property
  def tcount_var(self):
    """The total cache+metadata access count variance."""
    return self.tcount_sum2 / (self.C**2 * self.tsize) - self.tcount_avg**2

  @property
  def count_dev(self):
    """The cache contents access count stddev."""
    return self.count_var**0.5

  @property
  def mcount_dev(self):
    """The extra metadata access count stddev."""
    return self.mcount_var**0.5

  @property
  def tcount_dev(self):
    """The total cache+metadata access count stddev."""
    return self.tcount_var**0.5

  @property
  def hit_rate(self):
    """The cache contents hit rate."""
    return self.hit_count / self.get_count if self.get_count else nan

  @property
  def mhit_rate(self):
    """The extra metadata hit rate."""
    return self.mhit_count / self.get_count if self.get_count else nan

  @property
  def thit_rate(self):
    """The total cache+metadata hit rate."""
    return self.thit_count / self.get_count if self.get_count else nan

  def _incentry(self, key, count, data):
    """Increment the access count of an entry."""
    if self.T:
      # For non-LRU increment decaying count and sums.
      p = self.C
      newcount = count + p
      if data:
        self.count_sum += p
        self.count_sum2 += newcount**2 - count**2
      else:
        self.mcount_sum += p
        self.mcount_sum2 += newcount**2 - count**2
    else:
      # For LRU pre-decay counts to zero and use C as the score.
      newcount = self.C
    self.data[key] = (newcount, data)

  def _delentry(self, key, count, data):
    """Delete and decrement count sums for an entry."""
    if self.T:
      # For non-LRU decrement decaying count sums.
      if data:
        self.cnum -= 1
        self.count_sum -= count
        self.count_sum2 -= count**2
      else:
        self.mnum -= 1
        self.mcount_sum -= count
        self.mcount_sum2 -= count**2
    del self.data[key]

  def _addentry(self, key, count, data):
    """Add and increment count sums for an entry."""
    if self.T:
      # For non-LRU increment decaying count sums.
      if data:
        self.cnum += 1
        self.count_sum += count
        self.count_sum2 += count**2
      else:
        self.mnum += 1
        self.mcount_sum += count
        self.mcount_sum2 += count**2
    self.data[key] = (count, data)

  def _decayall(self):
    """Apply decay to all counts."""
    # Skip decaying already zeroed counts for LRU.
    if self.T:
      # Exponentially grow C O(1) instead of decaying all entries O(N).
      self.C *= self.M
      # If C has become too big, exponentially decay C and all counts back to 1.0.
      if self.C >= 1.0e100:
        decay = 1.0 / self.C
        for key, (count, data) in self.data.items():
          self.data[key] = (count*decay, data)
        self.count_sum *= decay
        self.mcount_sum *= decay
        decay2 = decay * decay
        self.count_sum2 *= decay2
        self.mcount_sum2 *= decay2
        self.C = 1.0
    else:
      # For LRU we just increment C.
      self.C += 1

  def _evictall(self):
    if self.cnum < self.size and self.mnum < self.msize:
      return
    if self.T:
       cmin = self.cpid.output * self.C
       mmin = self.mpid.output * self.C
    else:
      cmin = self.C - self.cpid.output*self.size
      mmin = self.C - self.mpid.output*self.tsize
    # Setup lists to collect metadata and data entries to delete.
    mdel,cdel = [],[]
    for key, (count, data) in self.data.items():
      if count < mmin:
        # score to low to keep metadata, add to metadata delete list.
        mdel.append((key, count, data))
      elif count < cmin and data is not None:
        # score to low to keed data, add to data delete list.
        cdel.append(key, count, data)
    # delete entries in metadata delete list.
    for d in mdel:
      self._delentry(*d)
    # move entries in data delete list to metadata.
    for d in cdel:
        self._delentry(*d)
        self._addentry(*d)
    # Update pid controllers for next evict cycle.
    dt = self.get_count - self.last_get
    merror = 0.95 - self.mnum/self.msize
    cerror = 0.95 - self.cnum/self.size
    self.mpid.Update(merror,dt)
    self.cpid.Update(cerror,dt)
    self.last_get = self.get_count
    
  def __getitem__(self, key):
    self.get_count += 1
    if key in self.data:
      count, data = self.data[key]
      self._incentry(key, count, data)
    else:
      count, data = self.C, None
      self._addentry(key, count, data)
    self._decayall()
    if data is None:
      raise KeyError(key)
    return data

  def __setitem__(self, key, value):
    self.set_count += 1
    if key in self.data:
       count, data = self.data[key]
       self._delentry(key, count, data)
    else:
      count = self.C
    self._addentry(key, count, value)
    self._evictall()

  def __delitem__(self, key):
    count, data = self.data[key]
    if data is None:
      raise KeyError(key)
    # Move the entry to a metadata entry.
    self._delentry(count,data)
    self._addentry(count,None)

  def __iter__(self):
    return iter(self.data)

  def __len__(self):
    return len(self.data)

  def getcount(self, key):
    """Get the access count for a cache entry."""
    count, _ = self.data.get(key, (0.0, None))
    return count / self.C if self.T else 0.0

  def __repr__(self):
    return "%s(size=%s, msize=%s, T=%3.1f)" % (
        self.__class__.__name__, self.size, self.msize, self.T)

  def __str__(self):
    return "%r: gets=%i hit=%5.3f avg=%5.3f var=%5.3f min=%5.3f mhit=%5.3f mavg=%5.3f mvar=%5.3f mmin=%5.3f" % (
        self, self.get_count, self.hit_rate, self.count_avg, self.count_var, self.count_min,
        self.mhit_rate, self.mcount_avg, self.mcount_var, self.mcount_min)

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
import collections
from PQueue import PQueueHeapq, PQueueLRU
from PIDController import PIDController, LowPassFilter

# Infinity, used to set T decay timeconstant for no decay.
inf = float('inf')
# NaN, used for things like hitrate with zero gets.
nan = float('nan')


class DLFUCache(collections.MutableMapping):
  """Decaying LFU Cache

  Attributes:
    size : the number of entries in the cache.
    msize: the number of extra metadata entries to keep.
    data: the underlying cache dict.
    C: The per-access count increment value.
    T: The per-size-accesses decay timeconstant.
    M: The exponential growth multiplier for C.
    cqueue: The cache priority queue.
    mqueue: The extra metadata priority queue.
    get_count: The count of get operations.
    set_count: The count of set operations.
    del_count: The count of del operations.
    hit_count: The count of cache hits.
    mhit_count: The count of metadata hits.
    csum: the sum of all cache entry counts
    msum: the sum of all extra metadata counts.
  """

  def __init__(self, size, msize=None, T=4.0):
    if msize is None:
      msize = size
    self.size = size
    self.msize = msize
    self.data = {}
    self.C = 1.0
    self.T = T
    if self.T*size <= 1.0:
      # Behave like LRU with no exponential decay of counts.
      self.M = 1.0
      PQueue = PQueueLRU
    elif T == inf:
      # Behave like LFU with no exponential decay of counts.
      self.M = 1.0
      PQueue = PQueueHeapq
    else:
      # Behave like DLFU with exponentail decay of counts.
      self.M = (self.T*size + 1.0) / (self.T*size)
      PQueue = PQueueHeapq
    self.cqueue = PQueue()
    self.mqueue = PQueue()
    self.reset_stats()
    self.csum = 0.0
    self.msum = 0.0

  def reset_stats(self):
    self.get_count = 0
    self.set_count = 0
    self.del_count = 0
    self.hit_count = 0
    self.mhit_count = 0

  @property
  def count_avg(self):
    """The cache contents average access count."""
    return self.csum / (self.C * self.size)

  @property
  def mcount_avg(self):
    """The extra metadata average access count."""
    if self.msize > 0:
      return self.msum / (self.C * self.msize)
    return nan

  @property
  def hit_rate(self):
    """The cache contents hit rate."""
    if self.get_count > 0:
      return float(self.hit_count) / self.get_count
    return nan

  @property
  def mhit_rate(self):
    """The extra metadata hit rate."""
    if self.get_count > 0:
      return float(self.mhit_count) / self.get_count
    return nan

  def _inccqueue(self, key):
    """Increment the access count of a cqueue entry."""
    self.cqueue[key] += self.C
    self.csum += self.C

  def _incmqueue(self, key):
    """Increment the access count of a mqueue entry."""
    self.mqueue[key] += self.C
    self.msum += self.C

  def _setmqueue(self, k, p):
    """Set the access count of a new mqueue entry."""
    if len(self.mqueue) < self.msize:
      # Just add a new entry.
      self.mqueue[k] = p
      self.msum += p
    elif self.mqueue:
      # Flush an old entry out.
      mink, minp = self.mqueue.swapitem(k, p)
      self.msum += p - minp

  def _setcqueue(self, k, p):
    """Set the access count of a new cqueue entry."""
    if len(self.cqueue) < self.size:
      # Just add a new entry.
      self.cqueue[k] = p
      self.csum += p
    else:
      # Cascade a flushed entry to the mqueue.
      mink, minp = self.cqueue.swapitem(k, p)
      self._setmqueue(mink, minp)
      self.csum += p - minp
      del self.data[mink]

  def _movcqueue(self, k):
    """Move a cqueue entry to the mqueue."""
    # Cascade the removed entry to the mqueue.
    k, p = self.cqueue.popitem(k)
    self.csum -= p
    self._setmqueue(k, p)

  def _movmqueue(self, k):
    """Move an mqueue entry to the cqueue."""
    # Cascade the removed entry to the mqueue.
    k, p = self.mqueue.popitem(k)
    self.msum -= p
    self._setcqueue(k, p)

  def _decayall(self):
    """Apply decay to all counts."""
    # Exponentially grow C O(1) instead of decaying all entries O(N).
    self.C *= self.M
    # If C has become too big, exponentially decay C and all counts back to 1.0.
    if self.C >= 1.0e100:
      decay = 1.0 / self.C
      self.cqueue.scale(decay)
      self.mqueue.scale(decay)
      self.csum *= decay
      self.msum *= decay
      self.C = 1.0

  def __getitem__(self, key):
    self.get_count += 1
    self._decayall()
    if key in self.cqueue:
      # Cache hit.
      self.hit_count += 1
      self._inccqueue(key)
    elif key in self.mqueue:
      # Meta hit.
      self.mhit_count += 1
      self._incmqueue(key)
    else:
      # Cache miss.
      self._setmqueue(key, self.C)
    return self.data[key]

  def __setitem__(self, key, value):
    self.set_count += 1
    if key in self.mqueue:
      # Move the entry from the mqueue to the cqueue.
      self._movmqueue(key)
    elif key not in self.cqueue:
      # Add a new entry to the cqueue.
      self._setcqueue(key, self.C)
    self.data[key] = value

  def __delitem__(self, key):
    # Move entry from the cqueue to the mqueue.
    self._movcqueue(key)
    self.data.pop(key)

  def __iter__(self):
    return iter(self.data)

  def __len__(self):
    return len(self.data)

  def getcount(self, key):
    """Get the access count for a cache entry."""
    if key in self.cqueue:
      return self.cqueue[key] / self.C
    if key in self.mqueue:
      return self.mqueue[key] / self.C
    return 0.0

  def __repr__(self):
    return "%s(size=%s, msize=%s, T=%s)" % (
        self.__class__.__name__, self.size, self.msize, self.T)

  def __str__(self):
    return "%r: gets=%i hit=%5.3f mhit=%5.3f avg=%5.3f mavg=%5.3f" % (
        self, self.get_count, self.hit_rate, self.mhit_rate, self.count_avg,
        self.mcount_avg)


class ADLFUCache(DLFUCache):
  """An Adaptive Decaying LFU Cache."""

  def __init__(self, size, msize=None):
    super(ADLFUCache, self).__init__(size, msize, 8.0)
    self.lpf = LowPassFilter(size/8.0)
    self.pid = PIDController.StandardForm(1.0, 2.0*size, size/2.0, 0.0)

  def __getitem__(self, key):
    # Get the low-pass filtered count.
    count = self.lpf.update(self.getcount(key)+1.0)
    mean = self.count_avg
    # Note 0 <= count <= T*size, 0 <= mean <= T.
    # This gives error in the range of almost -1 to 1.
    error = (count - mean)/(count + mean + 0.001)
    control = self.pid.update(error, 1.0)
    print self.pid, self
    # Transform the pid control output into 0.0 <= T < 40.0 and T=4.0 when control=0.0.
    self.T = 5.0 * (1.0 + control) / (1.25 - control)
    self.M = (self.T*self.size + 1.0) / (self.T*self.size)
    ret = super(ADLFUCache, self).__getitem__(key)

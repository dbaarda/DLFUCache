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
    count_sum: the sum of all cache entry counts
    mcount_sum: the sum of all extra metadata counts.
    count_sum2: The sum of the square of all cache entry counts.
    mcount_sum2: the sum of the square of all extra metadata counts.
  """

  def __init__(self, size, msize=None, T=4.0):
    if msize is None:
      msize = size
    self.size = size
    self.msize = msize
    self.data = {}
    self.C = 1.0
    self.T = T
    T *= size
    if T == 0.0:
      # Behave like LRU with no exponential decay of counts.
      self.M = 1.0
      PQueue = PQueueLRU
    elif T == inf:
      # Behave like LFU with no exponential decay of counts.
      self.M = 1.0
      PQueue = PQueueHeapq
    else:
      # Behave like DLFU with exponentail decay of counts.
      self.M = (T + 1.0) / T
      PQueue = PQueueHeapq
    self.cqueue = PQueue()
    self.mqueue = PQueue()
    self.reset_stats()
    self.count_sum = 0.0
    self.mcount_sum = 0.0
    self.count_sum2 = 0.0
    self.mcount_sum2 = 0.0

  def reset_stats(self):
    self.get_count = 0
    self.set_count = 0
    self.del_count = 0
    self.hit_count = 0
    self.mhit_count = 0

  @property
  def count_min(self):
    """The cache contents minimum access count."""
    if self.size == len(self.cqueue):
      return self.cqueue.peekitem()[1] / self.C
    return 0.0

  @property
  def mcount_min(self):
    """The extra metadata minimum access count."""
    if 0 < self.msize == len(self.mqueue):
      return self.mqueue.peekitem()[1] / self.C
    return 0.0

  @property
  def count_avg(self):
    """The cache contents access count average."""
    return self.count_sum / (self.C * self.size)

  @property
  def mcount_avg(self):
    """The extra metadata access count average."""
    if 0 < self.msize:
      return self.mcount_sum / (self.C * self.msize)
    return nan

  @property
  def count_var(self):
    """The cache contents access count variance."""
    return self.count_sum2 / (self.C**2 * self.size) - self.count_avg**2

  @property
  def mcount_var(self):
    """The extra metadata access count variance."""
    if 0 < self.msize:
      return self.mcount_sum2 / (self.C**2 * self.msize) - self.mcount_avg**2
    return nan

  @property
  def hit_rate(self):
    """The cache contents hit rate."""
    if 0 < self.get_count:
      return float(self.hit_count) / self.get_count
    return nan

  @property
  def mhit_rate(self):
    """The extra metadata hit rate."""
    if 0 < self.get_count:
      return float(self.mhit_count) / self.get_count
    return nan

  def _inccqueue(self, key):
    """Increment the access count of a cqueue entry."""
    old_count = self.cqueue[key]
    self.cqueue[key] += self.C
    self.count_sum += self.C
    self.count_sum2 += self.cqueue[key]**2 - old_count**2

  def _incmqueue(self, key):
    """Increment the access count of a mqueue entry."""
    old_count = self.mqueue[key]
    self.mqueue[key] += self.C
    self.mcount_sum += self.C
    self.mcount_sum2 += self.mqueue[key]**2 - old_count**2

  def _setmqueue(self, k, p):
    """Set the access count of a new mqueue entry."""
    if len(self.mqueue) < self.msize:
      # Just add a new entry.
      self.mqueue[k] = p
      self.mcount_sum += p
      self.mcount_sum2 += p*p
    elif self.mqueue:
      # Flush an old entry out.
      mink, minp = self.mqueue.swapitem(k, p)
      self.mcount_sum += p - minp
      self.mcount_sum2 += p*p - minp*minp

  def _setcqueue(self, k, p):
    """Set the access count of a new cqueue entry."""
    if len(self.cqueue) < self.size:
      # Just add a new entry.
      self.cqueue[k] = p
      self.count_sum += p
      self.count_sum2 += p*p
    else:
      # Cascade a flushed entry to the mqueue.
      mink, minp = self.cqueue.swapitem(k, p)
      self._setmqueue(mink, minp)
      self.count_sum += p - minp
      self.count_sum2 += p*p - minp*minp
      del self.data[mink]

  def _movcqueue(self, k):
    """Move a cqueue entry to the mqueue."""
    # Cascade a cqueue entry down to the mqueue.
    k, p = self.cqueue.popitem(k)
    self.count_sum -= p
    self.count_sum2 -= p*p
    self._setmqueue(k, p)

  def _movmqueue(self, k):
    """Move an mqueue entry to the cqueue."""
    # Cascade an mqueue entry up to the cqueue.
    k, p = self.mqueue.popitem(k)
    self.mcount_sum -= p
    self.mcount_sum2 -= p*p
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
      self.count_sum *= decay
      self.mcount_sum *= decay
      decay2 = decay * decay
      self.count_sum2 *= decay2
      self.mcount_sum2 *= decay2
      self.C = 1.0

  def __getitem__(self, key):
    self.get_count += 1
    self._decayall()
    if key in self.cqueue:
      # Cache hit.
      self.hit_count += 1
      self._inccqueue(key)
    elif key in self.mqueue:
      # Metadata hit.
      self.mhit_count += 1
      self._incmqueue(key)
    elif self.mcount_min <= 1.0 or self.T == 0.0:
      # Cache miss.
      self._setmqueue(key, self.C)
    return self.data[key]

  def __setitem__(self, key, value):
    self.set_count += 1
    # Bypass the cache if the count is too low and not running as LRU.
    if not (self.count_min <= (self.getcount(key) or 1.0) or self.T == 0.0):
      return
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
    return "%s(size=%s, msize=%s, T=%3.1f)" % (
        self.__class__.__name__, self.size, self.msize, self.T)

  def __str__(self):
    return "%r: gets=%i hit=%5.3f avg=%5.3f var=%5.3f mhit=%5.3f mavg=%5.3f mvar=%5.3f" % (
        self, self.get_count, self.hit_rate, self.count_avg, self.count_var,
        self.mhit_rate, self.mcount_avg, self.mcount_var)


class ADLFUCache(DLFUCache):
  """An Adaptive Decaying LFU Cache."""

  def __init__(self, size, msize=None):
    super(ADLFUCache, self).__init__(size, msize, 8.0)
    self.lpf = LowPassFilter(size/8.0)
    self.pid = PIDController.ZiglerNichols(1.0, size/2.0)
    self.dt = 0.0

  def _setT(self, T):
    #self.C *= self.T / T
    self.T = T
    self.M = (T*self.size + 1.0) / (T*self.size)

  def __getitem__(self, key):
    self.dt+=1.0
    if key in self.cqueue:
      # Get best expected average count (when access patterns match counts).
      mean2 = self.count_sum2 / (self.count_sum * self.C)
      # Get the average count (evenly distributed access patterns).
      mean = self.count_avg
      # set the target 75% of the way between mean and mean2.
      target = 0.75 * mean + 0.25 * mean2
      # Get the low-pass filtered average count.
      count = self.lpf.update(self.getcount(key), self.dt)
      # Note 0 <= count <= T*size, 0 <= mean <= T.
      # This gives error in the range of almost -1 to 1.
      error = (count - target)/(count + target + 0.001)
      control = self.pid.update(error, self.dt)
      # Transform the pid control output into 0.0 < T < inf and T=8.0 when control=0.0.
      T = 4.0 * (1.1 + control) / (1.1 - control)
      self._setT(T)
      self.dt = 0.0
      #print '%6d' % key, self, self.lpf, mean2, self.pid
    ret = super(ADLFUCache, self).__getitem__(key)

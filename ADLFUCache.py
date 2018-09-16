"""Adaptive Decaying LFU Cache Class

This is a basic implementation of an adaptive DLFU caching class,
which dynamically adjusts the T decay timeconstant to optimize cache
hitrates. The DLFU cache this is based on is documented at;

http://minkirri.apana.org.au/wiki/DecayingLFUCacheExpiry

Author  : Donovan Baarda <abo@minkirri.apana.org.au>
License : LGPL
Download: http://minkirri.apana.org.au/~abo/projects/DLFUCache/
          https://github.com/dbaarda/DLFUCache

"""
from DLFUCache import DLFUCache
from PIDController import PIDController, LowPassFilter

class ADLFUCache(DLFUCache):
  """An Adaptive Decaying LFU Cache."""

  def __init__(self, size, msize=None):
    super(ADLFUCache, self).__init__(size, msize, 8.0)
    self.slow_lpf = LowPassFilter(2.0*size)
    self.fast_lpf = LowPassFilter(size/2.0)
    self.pid = PIDController.ZiglerNichols(8.0, size/2.0)
    self.dt = 0.0

  def _setT(self, T):
    self.C *= self.T / T
    self.T = T
    self.M = (T*self.size + 1.0) / (T*self.size)

  def __getitem__(self, key):
    self.dt = 1.0
    count = self.getcount(key) / self.T
    slow = self.slow_lpf.update(count, self.dt)
    fast = self.fast_lpf.update(count, self.dt)
    error = (fast - slow) # / (fast + slow)
    control = self.pid.update(error, self.dt)
    # Transform the pid control output into 0.0 < T < inf and T=8.0 when control=0.0.
    T = 2.0 * (1.1 + control) / (1.1 - control)
    self._setT(T)
    #print "%6d" % key, self, fast, slow, self.pid
    ret = super(ADLFUCache, self).__getitem__(key)

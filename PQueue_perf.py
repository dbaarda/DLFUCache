#!/usr/bin/python
from timeit import timeit
from PQueue import *

NMax = 2**16

# Setup for primary cache testing.
csetup = """from __main__ import %(Q)s
i, n, c = 0, %(n)s, %(c)s
T, I = (n + 4.0)/n, n/c
data = [(j,T**j) for j in range(n)]
q = %(Q)s(data)
q.C = 1.0
def chit(i):
  q[i] += q.C
  q.C *= T
def mhit(i):
  k, v = q.swapitem(i+n, 1.5*q.C)
  q.C *= T
def miss(i):
  k, v = q.swapitem(i+n, q.C)
  q.C *= T
"""

# Setup for metadata cache testing.
msetup = """from __main__ import %(Q)s
i, n, c = 0, %(n)s, %(c)s
T, I = (n + 4.0)/n, n/c
data = [(j,T**(j-n)) for j in range(n)]
q = %(Q)s(data)
q.C = 1.0
def chit(i):
  q.C *= T
def mhit(i):
  q[i] += q.C
  v = q.pop(i)
  q[n+i] = q.C
  q.C *= T
def miss(i):
  q.swapitem(n+i, q.C)
  q.C *= T
"""

def testq(name, size=1000, count=1000):
  s = csetup % dict(Q=name, n=size, c=count)
  # Hit, inc(mid). This does hit increments for values min through max.
  th = timeit('chit(i); i += I', s, number=count)
  # Miss, min = swap(mid). This swaps out the min for a new fresh hit.
  tm = timeit('miss(i); i += I', s, number=count)
  # set(min). This sets the min entry to the min value.
  t0 = timeit('q[0] = 0', s, number=count)
  # set(max). This sets a max entry to the max value.
  tn = timeit('q[n] = n', s, number=count)
  # primary cache performance.
  tc =  timeit('chit(i); mhit(i+1); chit(i+2); miss(i+3); i += I', s, number=count)
  # meta cache performance.
  s = msetup % dict(Q=name, n=size, c=count)
  ts =  timeit('chit(i); mhit(i+1); chit(i+1); miss(i+3); i += I', s, number=count)
  print '%5d %-12s th=%6.3f tm=%6.3f t0=%6.3f tn=%6.3f tc=%6.3f ts=%6.3f' % (size, name, th, tm, t0, tn, tc, ts)

queues = 'Vect Deque Heapq DList LRU'.split()

size = 1024*4
while size <= NMax:
  for Q in ('PQueue%s' % q for q in queues):
    testq(Q, size)
  print
  size *= 2

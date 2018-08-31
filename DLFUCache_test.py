#!/usr/bin/python
import random
import math
from DLFUCache import *

def get(c, i):
  try:
    return c[i]
  except KeyError:
    c[i] = i

def sweep(c, n, o=0):  
  for i in xrange(n):
    for j in xrange(i+1):
      get(c, j+o)
  print c
  c.reset_stats()

def expdist(c, n, median, offset=0, lambd=1.0):
  """Do n fetches using a exponetial distribution.
  
  Half the fetches will be less than median. A large lambd
  gives more localization.
  """
  random.seed(7)
  mult = median*lambd / math.log(2)
  for i in xrange(n):
    v = int(random.expovariate(lambd)*mult)+offset
    get(c, v)
  print c
  c.reset_stats()
  
N = 100
C = 100 * N

for T in (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, inf):
  print "T = %f" % T
  c = DLFUCache(N, T=T)
  expdist(c, C, N)
  expdist(c, C, N, N)
  expdist(c, C, 2*N)
  expdist(c, C, N/2, 2*N)
  #sweep(c, 3*N)
  #sweep(c, 3*N, N)
  #sweep(c, 3*N)
  #sweep(c, 3*N, 3*N)


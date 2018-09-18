#!/usr/bin/python
"""Tests for DLFUCache.

For testing we use an integer cache key between 0 and MAXK.

The access sequences are done using a variety of generator expressions
designed to simulate various kinds of access patterns.

"""
import itertools
import math
import random
from DLFUCache import *


# Default maximum cache key value.
MAXK = 1<<32


def get(cache, key):
  """Get and set-on-miss cache accesses."""
  try:
    return cache[key]
  except KeyError:
    cache[key] = key


def reflect(v, minv, maxv):
  "Reflect a value back between limits min <= v < max."""
  if v < minv:
    return 2*minv - v
  if v >= maxv:
    return 2*maxv - v - 2
  return v


def cycle(*gens):
  """Combines multiple access generators by cycling through them."""
  for g in itertools.cycle(gens):
    yield g.next()


def expo(median, offset=0):
  """Exponential distribution access generator."""
  lambd = math.log(2)/median
  while True:
    yield int(random.expovariate(lambd) + offset)


def walk(variance, start=0, minv=0, maxv=MAXK):
  """Stochastic "gaussian walk" access generator."""
  mu = start
  sigma = variance**0.5
  while True:
    mu = reflect(random.gauss(mu, sigma), minv, maxv)
    yield int(mu)


def scan(start=0, step=1, minv=0, maxv=MAXK):
  """Linear scan access generator."""
  value = start
  while True:
    yield int(value)
    value += step
    if value > maxv:
      value = minv


def jump(median, duration, start=0.0, step=2.0):
  """Jumping expo access generator."""
  offset = start*median
  while True:
    for i in itertools.islice(expo(median, offset), duration):
      yield i
    offset += step*median


def mixed(size):
  """A nasty mixture of access generators."""
  g1 = expo(size)
  g2 = jump(size, 20*size)
  g3 = walk(2*size)
  g4 = scan()
  return cycle(g1, g2, g3, g4)


def runtest(name, cache, gen, count=1000):
  """Do count accesses using an access generator."""
  random.seed(7)
  cache.clear()
  for key in itertools.islice(gen, count):
    get(cache, key)
  print name, cache


if __name__ == '__main__':
  N = 1000
  C = 100 * N
  for T in (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, inf):
    for M in (0, N/2, N, 2*N):
      cache = DLFUCache(N, M, T)
      runtest("expo", cache, expo(N), C)
      runtest("walk", cache, walk(2*N), C)
      runtest("jump", cache, jump(N, 20*N), C)
      runtest("mixed", cache, mixed(N/2), C)

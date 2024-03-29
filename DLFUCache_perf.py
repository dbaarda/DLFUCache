#!/usr/bin/pypy3
"""Tests for DLFUCache.

For testing we use an integer cache key between 0 and MAXK.

The access sequences are done using a variety of generator expressions
designed to simulate various kinds of access patterns.

"""
import itertools
import math
import random
from DLFUCache import *
from ARCCache import *


# Default maximum cache key value.
MAXK = 1<<32


def get(cache, key):
  """Get and set-on-miss cache accesses."""
  try:
    return cache[key]
  except KeyError:
    cache[key] = key


def wrap(v, minv, maxv):
  "Wrap a value around between limits min <= v < max."""
  if v < minv:
    return v + (maxv - minv)
  if v >= maxv:
    return v - (maxv - minv)
  return v


def cycle(*gens):
  """Combines multiple access generators by cycling through them."""
  for g in itertools.cycle(gens):
    yield next(g)


def expo(median, offset=0):
  """Exponential distribution access generator."""
  lambd = math.log(2)/median
  while True:
    yield int(random.expovariate(lambd) + offset)


def walk(variance, start=MAXK//2, minv=0, maxv=MAXK):
  """Stochastic "gaussian walk" access generator."""
  mu = start
  sigma = variance**0.5
  while True:
    mu = wrap(random.gauss(mu, sigma), minv, maxv)
    yield int(mu)


def scan(start=0, step=1, minv=0, maxv=MAXK):
  """Linear scan access generator."""
  value = start
  while True:
    yield int(value)
    value = wrap(value+step, minv, maxv)


def jump(median, start=0, dist=4, wait=16):
  """Jumping expo access generator."""
  offset = start
  duration = int(wait * median)
  while True:
    for i in itertools.islice(expo(median, offset), duration):
      yield i
    offset += dist*median


def wave(median, start=0, step=0.25, minv=0, maxv=MAXK):
  """Sliding expo wave access generator."""
  egen=expo(median)
  sgen=scan(start, step, minv, maxv)
  while True:
    yield wrap(next(sgen) - next(egen), minv, maxv)


def mixed(size):
  """A nasty mixture of access generators."""
  g1 = expo(size)
  g2 = jump(size, start=4*size)
  g3 = wave(size//2, start=8*size)
  g4 = scan()
  return cycle(g1, g2, g3, g4)


def runtest(name, cache, gen, count=1000):
  """Do count accesses using an access generator."""
  random.seed(7)
  cache.clear()
  for key in itertools.islice(gen, count):
    get(cache, key)
  print(name, cache)
  return cache.hit_rate


def alltests(cache, N, C):
  e = runtest("expo", cache, expo(N), C)
  j = runtest("jump", cache, jump(N), C)
  s = runtest("wave", cache, wave(N//2), C)
  w = runtest("walk", cache, walk(2*N), C)
  m = runtest("mixed", cache, mixed(N//4), C)
  return e,j,s,w,m


if __name__ == '__main__':
  N = 1024
  C = 128 * N
  for T in (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, inf):
    for M in (0, N//2, N, 2*N):
      cache = DLFUCache(N, M, T)
      alltests(cache, N, C)
  cache = ARCCache(N)
  alltests(cache, N, C)

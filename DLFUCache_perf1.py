#!/usr/bin/python3 -O
"""Tests for DLFUCache.

For testing we use an integer cache key between 0 and MAXK.

The access sequences are done using a variety of generator expressions
designed to simulate various kinds of access patterns.
"""
from DLFUCache_perf import *
from DLFUCache import *
from ARCCache import *

import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt


Ts = [0.0, 1.0, 2.0, 4.0, 8.0, 16.0, inf, 'ARC']
Cs = ['LRU', '1.0', '2.0', '4.0', '8.0', '16.0', 'LFU', 'ARC']
Ns = [64<<n for n in range(8)]
Ms = range(0, 2049, 256)
loads = ['expo', 'jump', 'walk', 'mixed']


def get_label(T):
  return Cs[Ts.index(T)]


def get_cache(N, M, T):
  if T == 'ARC':
    return ARCCache(N)
  return DLFUCache(N, M, T)


def add_results(results, N, M, T, D, hits):
  for load, hit in zip(loads, hits):
    key = (load, N, M, T, D)
    results[key] = hit


def allloadtests(results, N, M, T, D, C):
  if ('expo', N, M, T, D) not in results:
    # Reuse ARC results for M=0 since ARC doesn't vary with M.
    if T == 'ARC' and ('expo', N, 0, T, D) in results:
      hits = (results[(load, N, 0, T, D)] for load in loads)
    else:
      cache = get_cache(N, M, T)
      hits = alltests(cache, D, C)
      # Set ARC results for M=0 since ARC doesn't vary with M.
      if T == 'ARC' and M != 0:
        add_results(results, N, 0, T, D, hits)
    add_results(results, N, M, T, D, hits)


def allcachetests(results, N, M, D, I):
  C = I * D
  for T in Ts:
    allloadtests(results, N, M, T, D, C)


def saveplt(filename, title, xlabel, ticks, labels=None):
  labels = labels or [str(n) for n in ticks]
  plt.title(title)
  plt.xlabel(xlabel)
  plt.ylabel('hit rate')
  plt.xticks(ticks, labels)
  plt.grid()
  plt.legend()
  plt.savefig(filename)
  plt.cla()


def RunLoads(results, I):
  """Plot how loads vary with dist and cache size."""
  for N in Ns:
    allcachetests(results, N, N, N, I)
  for load in loads:
    for T in Ts:
      hits = [results[(load, N, N, T, N)] for N in Ns]
      plt.plot(Ns, hits, label=get_label(T))
    plt.xscale('log')
    saveplt('load-%s.svg' % load, '%s load vs dist&cache size' % load,
            'dist and size', Ns)


def RunMsizes(results, I):
  """Plot how caches vary with msize."""
  N=1024
  for M in Ms:
    allcachetests(results, N, M, N, I)
  for load in loads:
    for T in Ts:
      hits = [results[(load, N, M, T, N)] for M in Ms]
      plt.plot(Ms, hits, label=get_label(T))
    saveplt('msize-%s.svg' % load, '%s load vs cache msize' % load, 'msize', Ms)


def RunSizes(results, I):
  """Plot how caches vary with size."""
  D = 1024
  for N in Ns:
    allcachetests(results, N, N, D, I)
  for load in loads:
    for T in Ts:
      hits = [results[(load, N, N, T, D)] for N in Ns]
      plt.plot(Ns, hits, label=get_label(T))
    plt.xscale('log')
    saveplt('size-%s.svg' % load, '%s load vs cache size' % load, 'size', Ns)


def RunTs(results, I):
  """Plot how caches vary with T."""
  N = 1024
  allcachetests(results, N, N, N, I)
  for load in loads:
    hits = [results[(load, N, N, T, N)] for T in Ts[:-1]]
    plt.plot(hits, label='DLFU')
    hits = [results[(load, N, N, 'ARC', N)]] * len(hits)
    plt.plot(hits, label='ARC')
    saveplt('Ts-%s.svg' % load, '%s load vs T' % load, 'T',
            range(len(hits)), Cs[:-1])


if __name__ == '__main__':
  I = 128
  results = {}
  RunTs(results, I)
  RunMsizes(results, I)
  RunSizes(results, I)
  RunLoads(results, I)

================
DLFUCache README
================

Introduction
============

A Decaying Least Frequently Used Cache implementation.

This is a Python implementation of a Decaying LFU cache as described
in http://minkirri.apana.org.au/wiki/DecayingLFUCacheExpiry.

This is like LFU but adds an exponential decay to the entry's
reference count so that it represents the number of references in the
past T*size cache accesses. It also keeps access history for more
entries than fit in the cache, so they can accumulate additional
history even if they are removed from the cache.

Contents
========

============ ======================================================
Name         Description
============ ======================================================
README.rst   This file.
LICENSE      Copyright and licencing details.
DESIGN.rst   Design details and description.
PQueue.py    Python priority queue implementations.
DLFUCache.py Python DLFU cache implementation.
============ =======================================================

Credits
=======

I (Donovan Baarda) had the idea of using an exponentially decaying
access count after looking at code for the linux bcache SSD caching of
HDDs. I then found references to LFRU which is basically the same
thing except they didn't seem to realize it was an exponentially
decaying count, and the various implications/implementations of that.
I had inklings that retaining history for more entries than the cache
could hold would be useful, and then seeing how ARC did this in
conjuction with the LFRU presentation convinced me it was crucial for
better DLFU cache performance.

http://u.cs.biu.ac.il/~wiseman/2os/2os/os2.pdf
  A nice summary of cache algorithms.

http://s3.amazonaws.com/cramster-resource/1025_n_9029.ppt
  A presentation of LRFU

Install
=======

Just copy the *.py files where you want to use them.

Usage
=====

A DLFUCache can be used just like a dictionary. It will raise KeyError
for cache misses. Values can be added to the cache, and when it is
full the least frequently accessed entry in the last T*size accesses
will be expired out of the cache.

>>> from DLFUCache import DLFUCache
>>> cache = DLFUCache(size=1000, T=4.0)
>>> try:
      value = cache[key]
    except KeyError:
      value = MyFetch(key)
      cache[key] = value

The timeconstant T argument lets you tune the decay period for the
access counts. Setting T=float(inf) makes the cache behave like an LFU
cache (the counts are never decayed) with the addition that counts are
retained for more entries than are kept in the cache. Setting T=0.0
makes the cache behave like a pure LRU cache, and counts never
accumulate.

Support
=======

Documentation
-------------

http://minkirri.apana.org.au/wiki/DecayingLFUCacheExpiry
  Early thoughts and history on developing this.

http://gitup.com/dbaarda/DLFUCache
  The project github site

Discussion
----------

Feel free to email me abo@minkirri.apana.org.au if you want to discuss
this, or file an issue on github if you want to discuss ideas publicly.

Reporting Problems
------------------

File an issue on the github site.


Development
===========

This is initially just a reference Python implementation for doing
proof of concept and performance analysis work. Eventually I plan to
write an optimized C version.


Design
======

See DESIGN.rst for the design details and description.


Plans
=====

This needs tests and some decent performance analysis.

Once the cache performance is better understood, an optimized version
in C should be written to give better cpu performance information.


History
=======

See github for the commit history.

----

http://github.com/dbaarda/DLFUCache
$Id: README.rst,v 69a01169087f 2014/11/27 00:12:55 abo $

=============================
DLFUCache Performance Results
=============================

Testing
=======

Testing cache performance can be done using real-world usage tests, or
synthetic simulation tests. Real-world tests have the advantage of
being representative of the particular real-world use-case, but can be
unrepresentative of other real-world use-cases and are much harder to
analyse. Synthetic tests can specifically target known corner-cases
and are much easier to analyse, making it possible to more accurately
assess the performance and make comparisons.

Tests need to use access patterns with a range larger than the cache
size, otherwise the cache just fills with all the accessed entries and
the cache expiry policy is not exercised. Synthetic access patterns
should use working sets/ranges sized as multiples of the cache size.
In order to make variations in performance easy to see and to measure
the cache expiry policy, the access pattern size should be chosen to
give hitrates around the 50% mark. This is the point where a cache is
being stressed, but still functioning.

We use the following syntetic access patterns for doing cache
performance testing, using access pattern ranges that are scaled
relative to the cache size.

Expo
----

This is random access using an exponential distribution. This
represents a typical task with a working set of entries that are of
varying popularity.

The settings are the median and an optional offset (used for "jump"
below). The median setting gives the size of the working set, where
50% of all accesses will be in the range 0 -> median (before applying
offset). So setting median to the cache size means the best possible
hitrate will be 50%.

This access pattern should strongly favour LFU caches, where long-term
past access history is the best hint of future access patterns.

Note in real-world workloads similar to this the access pattern will
not be a neat exponential distribution, and the most popular entries
will not be at the start of the access range but will be scattered.
However, if you sort the entries by popularity they will have a
distribution similar to an exponential distribution, and for caches
the ordering of the entries is not important, so this is fairly
representative of these kinds of workload.

Walk
----

This is a random stochastic walk using a normal distribution. This
represents the idealistic case of a task wandering through data in a
way where locality is the only thing that matters. The walk "wraps
around" past the min and max values for the entry range (default:
minv=0, maxv=MAXK).

The settings are the variance and an optional start value (default:
start=MAXK/2). The variance affects how fast/far the walk will wander.
There is a one-sigma (68%) chance that it wanders less than
sqrt(variance*N) distance every N iterations. So setting the variance
to the cache size means there is a one-sigma chance (68%) it wanders
less than cache-size distance every cache-size number of accesses.

This access pattern should strongly favour LRU caches, where
short-term past access history is the best hint for future access
patterns.

Jump
----

This is a random access using an exponential distribution that
periodically "jumps" to a new location. This represents running
different tasks with different working sets sequentially.

The settings are the expo distribution's median, duration between
jumps, and optional start and step median multipliers for the jumping
expo distribution's offset (default:start=0.0, step=4.0). The default
step means that each jump has very little overlap with the previous
jump at the tail end of its distribution.

This access pattern should favour a mixture of LFU and LRU, with LFU
working well between jumps, but LRU working better immediately after
each jump.

Scan
----

This is a linear scan walking through all entries. This is completely
uncachable, and is mainly of interest for testing how badly caching
algorithms are hurt by this access pattern.

There are optional settings for the start and step (default: start=0,
step=1), and it will wrap around between min and max values (default:
minv=0, maxv=MAXK). The defaults mean it will not wrap within the test
timescales used.

This access pattern is known to cause problems for LRU, and LFU does a
much better job of ignoring these accessess.

mixed
-----

A mixture of expo, jump, walk, and scan patterns running at the same
time. This represents a long-running background task with a working
set, a sequence of short-running tasks with different working sets, a
long-running task doing a random walk, and a long-running scan, all
running at once.

The only setting is the size, used to set the median and variance of
the expo, jump, and walk patterns.

Results
=======


Summary
-------

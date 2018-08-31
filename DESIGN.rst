================
DLFUCache DESIGN
================

.. contents:: **Contents**

Design Overview
===============

Inspirations and Origins
------------------------

The linux bcache code started me thinking that a decaying access count
would probably work well. LRU, LFU, LRFU, and ARC all helped shape my
thoughts on this.

LRFU is basically the same thing except;

1) The decay is expressed as a timeconstant T multiple of the cache
size. This means the entry's counts are the exponentially decaying sum
of the number of references in the past T*size cache accesses.

2) Cache entries need only a decaying count and don't need atime.
Entry's counts are not decayed on every increment or compare, instead
the increment amount C for each reference exponentially grows.
Periodically (amortized O(1)) the increment amount and every entry's
count is scaled back to C=1.0 to avoid overflowing. This is equivalent
to decaying every entry's count but avoids the O(N) cost. The actual
count for any entry can be calculated at any time as count/C.

3) We keep count history for more entries than are kept in the cache.
This ensures that count history for entries is not lost when they
expire from the cache, giving expired new entries a chance to
accumulate enough reference history to "stick" in the cache next time.

In practice this behaves like a mixture of LRU and LFU, with the
T timeconstant tuning which one it is closer to. Large T (long
timeconstant, very slow decay) behave more like LFU, with T=inf being
identical to LFU. Small T (short timeconstant, fast decay) behaves
like LRU, with T <1/size being equivalent to LRU.

Design Philosophy
-----------------

At this stage it's mostly experimenting and proof of concept.

General Architecture
--------------------

The Python implementation looks like a Python dict with a size limit,
with entries expiring from the cache when it gets full.

This implementation needs a priority queue for ordering cache pages to
find lowest count, and another priority queue of just metadata for
history of popular pages not in the cache.

For Python we avoid optimization tricks like using integer fractions
to keep it simple. They probably have limited or no benefit in an
interpreted language anyway.

Design Details
==============

Cache Operations
----------------

The following refers to pqueue operations on entries with priorities
of min, mid, or max value. Where the entry is affects the O() of heap
operations. Operations O() are shown as average/worst or
average?optimal where optimal might be common for things like
short moves or dlist cursors being close.

========== =================== =========== ========== ===========
Operation  Steps               binheap     cdlist     deque
========== =================== =========== ========== ===========
cachehit    c.movedn(mid)      O(1)/O(lnN) O(N)?O(1)  O(N)?O(1)
metahit     m.movedn(mid)      O(1)/O(lnN) O(N)?O(1)  O(N)?O(1)
totalmiss   m.swap(max,min)    O(lnN)      O(N)?O(1)  O(1)
cacheset    m.pull(max)        O(1)        O(1)       O(1)
            c.swap(mid,min)    O(lnN)      O(N)?O(1)  O(N)
            m.push(max)        O(1)        O(1)       O(1)
========== =================== =========== ========== ===========

Note that the operations on the meta pqueue consist of;

* moving a mid entry down to the end.
* pulling a max entry from the end.
* pushing a max entry to the end.
* swaping a min entry out for a max entry.

Note that this operates entirely at the queue ends except for moving
a mid entry to the end.  A binheap is O(lnN) for the last operation.
These are all O(1) for a dlist, and can be simplified as a simple
FIFO.

The operations on the cache pqueue consist of:

* moving a mid entry down a bit (small move?)
* swaping a min entry out for a mid entry (near min?)

These are O(1) and O(lnN) for a binheap, and O(N) for a dlist. However, it is
possible that adding a cursor to the dlist could make this approach
O(1). If the first operation is always a small move relative to the
spread of values in the queue, it could be much cheaper than O(N).
Similarly, the min entry swapped in is always going to be a metahit or
totalmiss that should have a value dominated by the recent +1.0, so
they should always end up being inserted close to the last insert
pointed at by the cursor.

If we assume a cache hitrate of 50% and a metahit rate of 25%, we are
going to have 50% each for the two operations. My gut feeling is a
binheap is the better option, and O(1) is not achievable for a cdlist.

PQueue Implementations
----------------------

Possible implementations.

* binheap - a normal binary heap implementation.
* cdlist - a doubly-linked-list with an insert cursor to speed up
  inserts near the same place.
* vector - a normal array
* dqueue - A double ended queue implemented either like Python's
  dqueue (linked list of fixed sized buffers), or a circular buffer.

Possible simplifications
------------------------

* fifo - push/pull operate on the end of the list, moveup/movedn implemented
  as just moving to the front/end of the list. This gives LRU
  behaviour, which is fine for the meta pqueue.

PQueue API
----------

This is an API that can work for a variety of different pqueue
implementations (heap, array, dlist, etc), and provides a low level
sequence-like view of a priority queue.

The init() can take any combination of arguments that work for
creating dicts. We use pull() for extracting the top item to avoid
confusion with any implementation's pop(). The swap() operation is
equivalent to a pull() and push() but can be more efficient for some
implementations.

We use `k,v` for items added/taken from the queue, and `e` to refer to
entries on the queue. The 'e' instance uniquely refers to a particular
entry added to the queue and will not change until it is removed. It
is possible (but not advisable) to push multiple items with the same
key. We use the folling argument shorthand for the API definition;

q - a pqueue instance
e - an entry list [v,k,...]
k - an item key
v - an item priority
k,v- a key,priority item in the pqueue.

========================= =========================================
Operation                 Descrition
========================= =========================================
q.init({k:v,...})         Init using dict() style args.
q.peek([e])->k,v          Get the top or an entry's item.
q.push(k,v)->e            Push an item in and return the entry.
q.pull([e])->k,v          Pull the top or an entry's item out.
q.swap(k,v,[e2])->e,k2,v2 Swap k,v->e in and e2->k2,v2 out.
iter(q) -> e,...          Iterate through all the entries.
========================= =========================================

DictPQueue API
--------------

This gives an API that looks like a dict mapping entries (k) to
priorities (v).

It is possible to directly access and manipulate the underlying
q.pqueue to eg iterate through and update all priorities, but you must
ensure the correct pqueue order is maintained.

============================= =========================================
Operation                     Description
============================= =========================================
q.init({k:v,...})             Initialize using dict() style args.
q.peekitem([k])->k,v          Get the top or a particular item.
q.popitem([k])->k,v           Pop the top or a particular item.
q.pushitem(k, v)              Push or replace an item.
q.swapitem(k,v,[k2])->k2,v2   Fast q.popitem(k2); q.pushitem(k,v)
q.scale(m)                    Rescale all priorities v=v*m
v = q[k]                      Equivalent to _,v = q.peekitem(k)
q[k] = v                      Equivalent to q.pushitem(k,v)
del q[k]                      Equivalent to q.popitem(k)
q.pop([k]) -> v               Equivalent to _,v = q.popitem(k)
iter(q) -> k,...              Iterate keys in arbitrary order.
============================= =========================================

Cache API
---------

The decay timeconstant is expressed as a multiple of the total cache
size, so the decaying access count represents the number of accesses
in the past T * size accesses.

Rather than exponentially decay all the entries access counts every
reference, the increment per access C is exponentially grown from 1.0.
When C reaches 2.0 it and all entries are decayed, ammortizing the
decay to O(1) per lookup. At any time the decayed count for any entry
can be calculated as count/C.

============================= =========================================
Operation                     Description
============================= =========================================
c.init(size, T)
d = c[k]
c[k] = d
del c[k]
c.size
c.C
C.T
C.get_count
C.set_count
C.del_count
C.hit_count
C.mhit_count
============================= =========================================

Thoughts on DLists
------------------

Dlists are traditionally implemented with a next/prev pointer per
element. However, particularly on 64bit architectures, pointers are
huge! If your dlist is just uint32 priorities then your overheads
are 4x as big as your data.

Memory locality matters a lot. Spreading your data over 5x the memory
because of 4x pointer overheads means hurting your CPU cache.

Pythons deque uses a linked list of 64 entry buckets to avoid the
pointer overheads, but sacrifices the ability to cheaply insert/remove
in the middle. This could be added by including a count per bucket and
doing bucket-splitting/merging, but it gets complicated. However, this
is probably a good compromise for pointer overheads.

Another option is put all the dlist entries in an array and use array
indexes instead of pointers. For a dlist of upto 64K entries you can
use uint16 indexes which are 1/4 the size of a pointer. For a dlist
with upto 4G entries a uint32 index is still 1/2 the size of a 64bit
pointer. Having all the dlist entries together in an array also helps
with memory locality.

If searching up/down a sorted list for inserting, locality will matter
even more, so it's worth only putting the compared value in the dlist
array entries, and using another array for additional element details
keyed with the same index. This way you scan through elements
containing only the data needed to find the desired index, then access
the element using that index in another array.

For smallish N < 10K it would not surprise me if a binheap outperforms
a pointer implemented dlist for all operations because of the memory
overheads/locality problems.

----

http://project/url/DESIGN
$Id: DESIGN,v 65b64de6b1e1 2014/01/20 02:32:20 abo $

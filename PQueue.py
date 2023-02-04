import collections
import heapq
import bisect
from collections import abc


class PQueueVect(abc.MutableMapping):
  """A PQueue implemented using Python's list."""

  __marker = object()

  def __init__(self, *args, **kwargs):
    self.queue = self._queue(*args, **kwargs)
    self.data = dict((e[1], e) for e in self.queue)

  def __getitem__(self, key):
    return self.data[key][0]

  def __setitem__(self, key, value):
    d = self.data
    if key in d:
      entry, _, _ = self._swap(key, value, d[key])
    else:
      entry = self._push(key, value)
    d[key] = entry

  def __delitem__(self, key):
    self._pull(self.data.pop(key))

  def __iter__(self):
    return iter(self.data)

  def __len__(self):
    return len(self.data)

  def clear(self):
    self.data.clear()
    self.queue = self._queue()

  def peekitem(self, key=__marker):
    """peekitem() -> key, value."""
    if key is self.__marker:
      return self._peek()
    else:
      return self.peek(self.data[key])

  def popitem(self, key=__marker):
    """popitem([key]) -> key, value."""
    d = self.data
    if key is self.__marker:
      try:
        key, value = self._pull()
      except IndexError:
        raise KeyError
      del d[key]
      return key, value
    else:
      return self._pull(d.pop(key))

  def swapitem(self, key, value, oldkey=__marker):
    """swapitem(key, value, [oldkey]) -> oldkey, oldvalue."""
    d = self.data
    if oldkey is self.__marker:
      entry, oldkey, oldvalue = self._swap(key, value)
    else:
      entry, oldkey, oldvalue = self._swap(key, value, d[oldkey])
    del d[oldkey]
    d[key] = entry
    return oldkey, oldvalue

  def scale(self, mult):
    """scale(mult)."""
    for e in self.queue:
      e[0] *= mult

  def _queue(self, *args, **kwargs):
    """_queue(*args, **kwargs) -> queue."""
    return sorted([v, k] for k,v in dict(*args, **kwargs).items())

  def _peek(self, entry=None):
    """_peek([entry]) -> key, value."""
    value, key = entry or self.queue[0]
    return key, value

  def _push(self, key, value):
    """_push(key, value) -> entry."""
    entry = [value, key]
    bisect.insort(self.queue, entry)
    return entry

  def _pull(self, entry=None):
    """_pull([entry]) -> key, value."""
    q = self.queue
    if entry:
      del q[bisect.bisect(q, entry) - 1]
    else:
      entry = q.pop(0)
    return entry[1], entry[0]

  def _swap(self, key, value, oldentry=None):
    """_swap(key, value, [oldentry]) -> entry, oldkey, oldvalue."""
    oldkey, oldvalue = self._pull(oldentry)
    entry = self._push(key, value)
    return entry, oldkey, oldvalue


class PQueueDeque(PQueueVect):
  """A PQueue implemented using Pythons deque."""

  def _queue(self, *args, **kwargs):
    return collections.deque(
        sorted([v, k] for k,v in dict(*args, **kwargs).items()))

  def _insert(self, i, e):
    q = self.queue
    q.rotate(-i)
    q.appendleft(e)
    q.rotate(i)

  def _push(self, key, value):
    """push(key, value) -> entry."""
    entry = [value, key]
    self._insert(bisect.bisect(self.queue, entry), entry)
    return entry

  def _pull(self, entry=None):
    """_pull([entry]) -> key, value."""
    q = self.queue
    if entry:
      del q[bisect.bisect(q, entry) - 1]
    else:
      entry = q.popleft()
    return entry[1], entry[0]


class Deleted(object):
  """A Class for deleted objects that compares less than anything.

  We need this for "deleted" sentinel markers in pqueue entries to prevent
  TypeError exceptions comparing entries with the same priority. It also
  ensures deleted entries with the same priority float to the top where they
  can be removed.
  """
  def __lt__(self, other):
    return True

  def __gt__(self, other):
    return False


class PQueueHeapqD(PQueueVect):
  """A PQueue implemented using Python's heapq with deletion markers."""

  __deleted = Deleted()

  def _peek(self, entry=None):
    """_peek([entry]) -> key, value."""
    q = self.queue
    value, key = entry or q[0]
    while key is self.__deleted:
      heapq.heappop(q)
      value, key = q[0]
    return key, value

  def _push(self, key, value):
    """_push(key, value) -> entry."""
    entry = [value, key]
    heapq.heappush(self.queue, entry)
    return entry

  def _pull(self, entry=None):
    """_pull([entry]) -> key, value."""
    if entry:
      value, key = entry
      entry[1] = self.__deleted
    else:
      # Suck out any deleted items.
      self._peek()
      value, key = heapq.heappop(self.queue)
    return key, value

  def _swap(self, key, value, oldentry=None):
    """_swap(key, value, [oldentry]) -> entry, oldkey, oldvalue."""
    if oldentry:
      oldkey, oldvalue = self._pull(oldentry)
      entry = self._push(key, value)
    else:
      entry = [value, key]
      # Suck out any deleted items.
      self._peek()
      oldvalue, oldkey = heapq.heapreplace(self.queue, entry)
    return entry, oldkey, oldvalue


# These are basic heap functions that assume entries are in the form
# [key, value, index], where index is the entry's index in the heap.

def _shiftup(heap, entry):
  """Shift an entry up into the right position."""
  pos = entry[2]
  # Shift the parents down until we find the right position.
  while pos > 0:
    parentpos = (pos - 1) >> 1
    parent = heap[parentpos]
    if entry[0] >= parent[0]:
      break
    # move the parent down.
    parent[2] = pos
    heap[pos] = parent
    # Go up to the next parent.
    pos = parentpos
  # The node at pos is empty now, Put entry there.
  heap[pos] = entry
  entry[2] = pos

def _shiftdn(heap, entry):
  """Shift an entry down into the right position."""
  pos = entry[2]
  n = len(heap)
  # Shift the smaller child up until we find the right position.
  childpos = 2 * pos + 1  # leftmost child position
  while childpos < n:
    # Set childpos to index of smaller child.
    rightpos = childpos + 1
    if rightpos < n and heap[childpos][0] > heap[rightpos][0]:
      childpos = rightpos
    child = heap[childpos]
    if entry[0] <= child[0]:
      break
    # Move the smaller child up.
    child[2] = pos
    heap[pos]= child
    # Go down to the next child.
    pos = childpos
    childpos = 2 * pos + 1
  # The node at pos is empty now, put entry there.
  entry[2] = pos
  heap[pos] = entry


class PQueueHeapq(PQueueVect):
  """A PQueue implemented using a binheap with entries containing their index."""

  def _queue(self, *args, **kwargs):
    """_queue(*args, **kwargs) -> queue."""
    heap = [[v, k, i] for i,(k,v) in enumerate(dict(*args, **kwargs).items())]
    for i in reversed(range(len(heap)//2)):
      _shiftdn(heap, heap[i])
    return heap

  def _peek(self, entry=None):
    """_peek([entry]) -> key, value."""
    value, key, _ = entry or self.queue[0]
    return key, value

  def _push(self, key, value):
    """_push(key, value) -> entry."""
    heap = self.queue
    # Put the new entry at the end and shift it up.
    entry = [value, key, len(heap)]
    heap.append(entry)
    _shiftup(heap, entry)
    return entry

  def _pull(self, entry=None):
    """_pull([entry]) -> key, value."""
    heap = self.queue
    entry = entry or heap[0]
    last = heap.pop()
    value, key, pos = entry
    if last is not entry:
      # Put last at the entry's position and shift it into place.
      last[2] = pos
      heap[pos] = last
      if value < last[0]:
        _shiftdn(heap, last)
      else:
        _shiftup(heap, last)
    return key, value

  def _swap(self, key, value, oldentry=None):
    """_swap(key, value, [oldentry]) -> entry, oldkey, oldvalue."""
    heap = self.queue
    entry = oldentry or heap[0]
    oldvalue, oldkey, _ = entry
    # Set the entry and shift it into place.
    entry[0], entry[1] = value, key
    if oldvalue < value:
      _shiftdn(heap, entry)
    else:
      _shiftup(heap, entry)
    return entry, oldkey, oldvalue


class PQueueDList(PQueueVect):
  """A PQueue implemented using a DList."""

  def _queue(self, *args, **kwargs):
    """_queue(*args, **kwargs) -> queue."""
    return CDList(*args, **kwargs)

  def _peek(self, entry=None):
    """_peek([entry]) -> key, value."""
    return self.queue.peek(entry)

  def _push(self, key, value):
    """_push(key, value) -> entry."""
    return self.queue.push(key, value)

  def _pull(self, entry=None):
    """_pull([entry]) -> key, value."""
    return self.queue.pull(entry)


class PQueueLRU(PQueueDList):
  """LRU with PQueue compatible interface.

  It doesn't really care about priorities except on initialization.
  Setting entries or doing swapitem() will add/move them to the end of
  the queue.
  """

  def _push(self, key, value):
    entry = self.queue.newentry(key, value)
    self.queue.insert(entry)
    return entry


class CDList(abc.Container, abc.Iterable, abc.Sized):
  """A doubly linked list with cursor for sorted inserts.

  Each dlist entry is a list of [value, key, next, prev]. The dlist is
  implemented as a circular dlist with a sentinel entry that marks the
  beginning/end of the list.
  """

  def __init__(self, *args, **kwargs):
    self.count = 0
    # Create a sentinel entry for the start/end of the circular dlist.
    s = self.newentry(None, None)
    s[2] = s[3] = self.sentinel = self.cursor = s
    for e in sorted(self.newentry(k,v) for k,v in dict(*args, **kwargs).items()):
      self.insert(e)

  def __contains__(self, value):
    for entry in self:
      if entry == value:
        return True
    return False

  def __len__(self):
    return self.count

  def __iter__(self):
    next = self.sentinel[2]
    while next is not self.sentinel:
      yield next
      next = next[2]

  def __reversed__(self):
    prev = self.sentinel[3]
    while prev is not self.sentinel:
      yield prev
      prev = prev[3]

  def newentry(self, k, v):
    return [v, k, None, None]

  def insert(self, entry, pos=None):
    """Insert entry into dlist before pos."""
    # Set pos to the sentinal if unspecified.
    pos = pos or self.sentinel
    # Get the entries after/before the insertion point.
    next, prev = pos, pos[3]
    # Update the entry before and after.
    prev[2] = next[3] = entry
    # Update the entry and count.
    entry[2], entry[3] = next, prev
    self.count += 1

  def remove(self, entry):
    """Remove an entry from the dlist."""
    next, prev = entry[2], entry[3]
    # Update the cursor.
    if entry is self.cursor:
      self.cursor = next
    # Update the entry before and after.
    prev[2], next[3] = next, prev
    # Update the entry and count.
    entry[2] = entry[3] = None
    self.count -= 1

  def insort(self, entry, pos=None):
    """Insert entry into sorted dlist, with optional pos hint."""
    # Set sentinel equal to entry to stop scans at the sentinel.
    self.sentinel[0] = entry[0]
    # Scan from the sentinel if pos not specified.
    pos = pos or self.sentinel
    # Scan backwards from pos for a smaller or equal entry.
    pos = pos[3]
    while pos[0] > entry[0]:
      pos = pos[3]
    # Scan forwards from pos for greater or equal entry.
    pos = pos[2]
    while pos[0] < entry[0]:
      pos = pos[2]
    # Insert before greater or equal entry.
    self.insert(entry, pos)

  def peek(self, entry=None):
    entry = entry or self.sentinel[2]
    return entry[1], entry[0]

  def push(self, key, value):
    entry = self.newentry(key, value)
    self.insort(entry, self.cursor)
    self.cursor = entry
    return entry

  def pull(self, entry=None):
    entry = entry or self.sentinel[2]
    if entry is self.sentinel:
      raise IndexError('pull() from empty DList')
    self.remove(entry)
    return entry[1], entry[0]

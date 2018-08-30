import collections
import heapq
import bisect


class PQueueVect(collections.MutableMapping):
  """A PQueue implemented using Pythons list."""

  __marker = object()

  def __init__(self, *args, **kwargs):
    self.data = dict(*args, **kwargs)
    self.queue = self._queue(self.data)
    self.data.update((e[1], e) for e in self.queue)

  def __getitem__(self, key):
    return self.data[key][0]

  def __setitem__(self, key, value):
    d = self.data
    if d.has_key(key):
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

  def peekitem(self):
    """peekitem() -> key, value."""
    return self._peek()

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
      return self._pull(d,pop(key))

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
    return sorted([v, k] for k,v in dict(*args, **kwargs).iteritems())

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
        sorted([v, k] for k,v in dict(*args, **kwargs).iteritems()))

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


class PQueueHeapq(PQueueVect):
  """A PQueue implemented using Pythons heapq."""

  __deleted = object()

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


class CDList(collections.Container, collections.Iterable, collections.Sized):
  """A doubly linked list with cursor for sorted inserts."""

  def __init__(self, *args, **kwargs):
    self.count = 0
    self.next = None
    self.last = None
    self.cursor = None
    for e in sorted(self.newentry(k,v) for k,v in dict(*args, **kwargs).iteritems()):
      self.insert(e)

  def __contains__(self, value):
    for entry in self:
      if entry == value:
        return True
    return False

  def __len__(self):
    return self.count

  def __iter__(self):
    next = self.next
    while next:
      yield next
      next = next[2]

  def __reversed__(self):
    prev = self.last
    while prev:
      yield prev
      prev = prev[3]

  def newentry(self, k, v):
    return [v, k, None, None]

  def insert(self, entry, pos=None):
    """Insert entry into dlist before pos."""
    # Get the entires after/before the insertion point.
    next = pos
    if pos:
      prev = pos[3]
    else:
      prev = self.last
    # Update the entry before.
    if prev:
      prev[2] = entry
    else:
      self.next = entry
    # Update the entry after.
    if next:
      next[3] = entry
    else:
      self.last = entry
    # Update the entry and count.
    entry[2], entry[3] = next, prev
    self.count += 1

  def remove(self, entry):
    """Remove an entry from the dlist."""
    next, prev = entry[2], entry[3]
    # Update the cursor.
    if entry is self.cursor:
      self.cursor = next
    # Update the entry before.
    if prev:
      prev[2] = next
    else:
      self.next = next
    # Update the entry after.
    if next:
      next[3] = prev
    else:
      self.last = prev
    # Update the entry and count.
    entry[2] = entry[3] = None
    self.count -= 1

  def insort(self, entry, pos=None):
    """Insert entry into sorted dlist, with optional pos hint."""
    # Scan from the end if pos not specified.
    pos = pos or self.last
    # Scan backwards from pos for a smaller or equal entry.
    while pos and pos[0] > entry[0]:
      pos = pos[3]
    # Adjust pointer to insertion point after smaller or equal entry.
    if pos:
      pos = pos[2]
    else:
      pos = self.next
    # Scan forwards from pos for greater or equal entry.
    while pos and pos[0] < entry[0]:
      pos = pos[2]
    self.insert(entry, pos)

  def peek(self, entry=None):
    entry = entry or self.next
    return entry[1], entry[0]

  def push(self, key, value):
    entry = self.newentry(key, value)
    self.insort(entry, self.cursor)
    self.cursor = entry
    return entry

  def pull(self, entry=None):
    entry = entry or self.next
    if not entry:
      raise IndexError('pull() from empty DList')
    self.remove(entry)
    return entry[1], entry[0]

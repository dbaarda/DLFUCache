import collections
import heapq
import bisect


class PQueueBase(collections.Sized, collections.Iterable, collections.Container):
  """Priority Queue base class.

  This is a base class for a priority queue. It assumes all entries
  are [value, key, ...] lists, where the end values are implementation
  specific. The newentry() method can be used to create new entries.

  Additional methods sort(), move(), peek(), push(), pull(), and swap()
  will get the sequence into and maintain the correct priority
  order.
  """

  def __init__(self, *args, **kwargs):
    for k, v in dict(*args, **kwargs):
      self.push(self.newentry(k, v)

  def __contains__(self, value):
    for v in self:
      if v == value:
        return True
    return False

  def newentry(self, k, v):
    raise NotImplementedError

  def sort(self):
    raise NotImplementedError

  def move(self, entry):
    raise NotImplementedError

  def peek(self):
    raise NotImplementedError

  def push(self, entry):
    raise NotImplementedError

  def pull(self, entry=None):
    raise NotImplementedError

  def swap(self, entry, oldentry=None):
    if oldentry is None:
      oldentry = self.peek()
    self.pull(oldentry)
    self.push(entry)
    return oldentry


class PQueueList(collections.MutableSequence, PQueueBase):
  """Priority Queue implemented as a sorted list.

  This is a MutableSequence with additional methods for using it as a
  priority queue. It assumes all entries are [value, key, index]
  lists, where the index is the index of the entry in the sequence.
  This makes the index() operation O(1).

  All the normal list methods operate unchanged except they will
  ensure that the entries index values are updated to reflect their
  position in the list. They do NOT enforce any sort of ordering
  within the list, and can be used by subclasses to manipulate the
  list into the desired order while maintaining the correct index
  entries. There is also a reindex() helper method that can be used to
  set the indexes for a range of entries that can be used by
  subclasses after manipulating self.data directly.
  """

  def __init__(self, *args, **kwargs):
    self.data = [[v, k, i] for (i, (k, v)) in enumerate(
        dict(*args, **kwargs).iteritems())]
    self.sort()

  def __getitem__(self, index):
    return self.data[index]

  def __setitem__(self, index, value):
    self.data[index] = value
    value[2] = index

  def __delitem__(self, index):
    del self.data[index]
    self.reindex(index)

  def __len__(self):
    return len(self.data)

  def insert(self, index, value):
    self.data.insert(index, value)
    self.reindex(index)

  def index(self, value):
    return value[2]

  def reindex(self, i=0, j=None):
    if j is None:
      j = len(self.data)
    for i in xrange(i, j):
      self.data[i][2] = i

  def newentry(self, k, v):
    return [v, k, -1]

  def sort(self):
    sort(self.data)
    self.reindex()

  def move(self, entry):
    index = entry[2]
    if index and entry[0] < self.data[index-1][0]:
        newindex = bisect.bisect_left(self.data, entry, hi=index)
    else:
        newindex = bisect.bisect_left(self.data, entry, lo=index)
    if index < newindex:
      self.data.insert(index, entry)
      del self.data[index]
      self.reindex(index, newindex)
    elif newindex < index:
      del self.data[index]
      self.data.insert(newindex, entry)
      self.reindex(newindex, index+1)

  def peek(self):
    return self.data[0]

  def push(self, entry):
    bisect.insort_left(self, entry)

  def pull(self, entry=None):
    if entry is None:
      return self.pop(0)
    return self.pop(entry[2])

  def swap(self, entry, oldentry=None):
    if oldentry is None:
      oldentry = self.data[0]
    index = oldentry[2]
    self[index] = entry
    self.move(entry)
    return oldentry


class PQueueHeap(PQueueList):

  def sort(self):
    heapq.heapify(self)

  def move(self, entry):
    index = entry[2]
    # if it is not the top, try and move it up.
    if index > 0:
      heapq._siftdown(self, 0, index)
    # If it didn't move up, try to move it down.
    if self.data[index] is entry:
      heapq._siftup(self, index)

  def push(self, entry):
    heapq.heappush(self, entry)

  def pull(self, entry=None):
    if entry is None:
      return heapq.heappop(self)
    lastentry = self.data.pop()
    if self.data:
      return self.swap(lastentry, entry)
    return lastentry


class PQueueDList(PQueueBase):

  def __init__(self, *args, **kwargs):
    self.count = 0
    self.cursor = None
    self.next = None
    self.last = None
    super(PQueueDList, self).__init__(*args, **kwargs)

  def __len__(self):
    return self.count

  def __iter__(self):
    next = self.next
    while next:
      yield next
      next = next[2]

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
      self.last is prev
    # Update the entry and count.
    entry[2] = entry[3] = None
    self.count -= 1

  def newentry(self, k, v):
    return [v, k, None, None]

  def sort(self):
    # This is insert sort, which is O(N^2) average but approaches O(N)
    # for already sorted data.
    pos = self.next
    while pos:
      entry = pos[2]
      if entry:
        self.move(entry)
      pos = pos[2]

  def move(self, entry):
    pos = entry[3]
    self.remove(entry)
    # Scan backwards from pos for a smaller or equal entry.
    while pos and pos[0] > entry[0]:
      pos = pos[3]
    # Adjust pointer back to insertion point.
    if pos:
      pos = pos[2]
    else:
      pos = self.next
    # Scan forwards from pos for greater or equal entry.
    while pos and pos[0] < entry[0]:
      pos = pos[2]
    self.insert(entry, pos)

  def peek(self):
    return self.next

  def push(self, entry):
    self.insert(entry, self.cursor)
    self.move(entry)
    self.cursor = entry

  def pull(self, entry=None):
    if entry is None:
      entry = self.next
    self.remove(entry)
    return entry


class PQueueFIFO(PQueueBase):
  """FIFO with PQueue compatible interface.
  
  It doesn't really care about priorities except on initialization.
  Doing push()/pull() behaves like a normal FIFO. Doing move() will
  move the entry to the end of the queue. Doing swap() will append the
  entry to the end of the queue and remove the oldentry.
  
  Operations only affecting the ends of the queue are O(1). Doing
  pull(), move() or swap() on elements in the middle of the queue are
  O(N), and cost about the same as insert() or del on the the front of
  a list.
  """
  def __init__(self, *args, **kwargs):
    self.data = deque(sorted([v,k] for (k,v) in dict(*args, **kwargs).items()))
  
  def insert(self, i, e):
    self.data.rotate(-i)
    self.data.appendleft(e)
    self.data.rotate(i)

  def newentry(self, k, v):
    return [v, k]

  def sort(self):
    pass

  def move(self, entry):
    self.data.remove(entry)
    self.data.append(entry)

  def peek(self):
    return self.data[0]

  def push(self, entry):
    self.data.append(entry)

  def pull(self, entry=None):
    if entry:
      self.data.remove(entry)
      return entry
    return self.data.popleft()

                
class DictPQueue(collections.MutableMapping):

  __marker = object()

  PQueueClass = PQueueHeap

  def __init__(self, *args, **kwargs):
    self.data = dict(*args, **kwargs)
    self.pqueue = self.PQueueClass(self.data.items())
    self.data.update((e[1], e) for e in self.heap)

  def __getitem__(self, key):
    return self.data[key][0]

  def __setitem__(self, key, value):
    if key in self.data:
       entry = self.data[key]
       entry[0] = value
       self.pqueue.move(entry)
    else:
      entry = self.pqueue.newentry(key, value)
      self.d[key] = entry
      self.pqueue.push(entry)

  def __delitem__(self, key):
    entry = self.data.pop(key)
    self.pqueue.pull(entry)

  def __iter__(self):
    return iter(self.data)

  def __len__(self):
    return len(self.data)

  def peek(self):
    self.pqueue.peek()[1]

  def pull(self):
    return self.pullitem()[1]

  def peekitem(self, key=__marker):
    if key is __marker:
      entry = self.pqueue.peek()
    else:
      entry = self.data[key]
    return entry[1], entry[0]

  def pushitem(self, key, value):
    self[key] = value

  def pullitem(self, key=__marker):
    if key is __marker:
      entry = self.pqueue.pull()
    else:
      entry = self.pqueue.pull(self.data[key])
    del self.data[entry[1]]
    return entry[1], entry[0]

  def swapitem(self, key, value, oldkey=__marker):
    if key in self:
      del self[key]
    entry = self.pqueue.newentry(key, value)
    if oldkey == __marker:
      oldentry = self.pqueue.swap(entry)
    else:
      oldentry = self.pqueue.swap(entry, self.data[oldkey])
    del self.data[oldkey]
    self.data[key] = entry
    return oldentry[1], oldentry[0]

  def scale(self, mult):
    for e in self.pqueue:
      e[0] *= mult


import typing
import queue
import dataclasses

import sys
sys.path.append('..')
import conproc

@dataclasses.dataclass(order=True)
class Item:
    priority: int = 0

def assert_devin(items: typing.List[Item]):
    q = conproc.PriorityQueue()
    for i in items:
        q.put(i, i.priority)
    assert([q.get() for _ in range(q.size())] == list(sorted(items)))

def test_priorityqueue():
    test1 = [Item(1) for _ in range(100)]
    test2 = [Item(i) for i in range(100)]
    test3 = [Item(j) for i in range(100) for j in [i]*10]
    all_tests = test1 + test2 + test3

    # MAKE SURE DEVIN IS WORKING WELL!!
    assert_devin(all_tests)

def test_multi():
    test1 = [Item(1) for _ in range(100)]
    test2 = [Item(i) for i in range(100)]
    test3 = [Item(j) for i in range(100) for j in [i]*10]
    tests = [test1, test2, test3]
    
    mpq = conproc.PriorityMultiQueue()
    for i, ts in enumerate(tests):
        for t in ts:
            mpq.put(t, t.priority, i)
            
    # get the different channels
    for i, ts in enumerate(tests[::-1]):
        channel = len(tests) - i - 1
        queue_items = [mpq.get(channel) for _ in range(mpq.size(channel))]
        assert(queue_items == list(sorted(ts)))

    for chan, ts in enumerate(tests):
        for t in ts:
            mpq.put(t, t.priority, chan)
            assert(mpq.get(chan) == t)
            


if __name__ == '__main__':
    test_priorityqueue()
    test_multi()


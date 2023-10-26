
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


if __name__ == '__main__':
    test_priorityqueue()


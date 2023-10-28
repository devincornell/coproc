
import time
import typing

import sys
sys.path.append('..')
import coproc

import dataclasses 

import datetime
import multiprocessing
import tqdm
import time

def wait_square(x):
    if x % 2 == 0:
        time.sleep(0.01)
    return x**2

def square(x):
    return x**2

def test_lazy_pool():
    vs = list(range(10))
    p = coproc.LazyPool(5, verbose=True)
    result = p.map(square, vs)
    print(result)
    assert(result == [v**2 for v in vs])
    time.sleep(0.1)
    
    print('unordered')
    vsq = set(v**2 for v in vs)
    results = set(p.map_unordered(wait_square, vs))
    assert(vsq == results)

if __name__ == '__main__':
    test_lazy_pool()






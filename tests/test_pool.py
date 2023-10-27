
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

def test_pool():
    vs = list(range(10))
    with coproc.Pool(5, verbose=True) as m:
        result = m.map(wait_square, vs)
        print(result)
        assert(result == [v**2 for v in vs])
        
        vsq = set(v**2 for v in vs)
        for r in m.map_unordered(wait_square, vs):
            assert(r in vsq)
            print(r)
        
    

if __name__ == '__main__':
    test_pool()






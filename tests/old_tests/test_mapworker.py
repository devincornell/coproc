
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

def square(x):
    return x**2


def test_mapworker():
    vs = list(range(10))
    v = 10
    
    with coproc.MapWorker(verbose=True) as m:
        assert(m.available() == 0)
        m.update_user_func(square)
        m.send(v)
        
        print(m.remaining())
        
        assert(m.remaining() == 1)
        time.sleep(0.1)
        assert(m.available() == 1)
        assert(m.receive() == square(v))
        
        [m.send(v) for v in vs]
        assert(m.remaining() == len(vs))
        time.sleep(0.1)
        assert(m.available() == len(vs))
        for v in vs:
            assert(m.receive() == square(v))
    

if __name__ == '__main__':
    test_mapworker()





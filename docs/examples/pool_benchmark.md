# Benchmark Comparison `Pool`

Where `coproc` was designed for situations where you want to maintain persistent, stateful processes, the `conproc.Pool` interface essentially emulates the behavior of `multiprocessing.Pool` in order to benchmark the performance of the underlying `WorkerResource` and `PriorityMessenger` systems.

***RESULTS***: similar performance except when thread tasks are small and numerous, in which case `coproc` is much slower.


```python
import sys
sys.path.append('..')
import coproc
import multiprocessing
```


```python
import time
def square(v):
    time.sleep(0.05)
    return v**2

def map_square(vs, pool):
    return pool.map(square, vs)

n = 3
values = list(range(100))
cp = coproc.LazyPool(n)

#map_square(values, cp)
#map_square(values, cp)
#map_square(values, cp)
#map_square(values, cp)
#%timeit map_square(values, cp)
with coproc.Pool(n) as p:
    %time map_square(values, cp)
    %time map_square(values, p)
```

    CPU times: user 1.59 s, sys: 108 ms, total: 1.69 s
    Wall time: 1.74 s
    CPU times: user 1.55 s, sys: 116 ms, total: 1.66 s
    Wall time: 1.71 s


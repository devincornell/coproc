import time
import typing

import sys
sys.path.append('..')
import conproc

import dataclasses 

import datetime
import multiprocessing
import tqdm

def test_monitor_process():
    pass

def test_monitor():
    with conproc.Monitor(snapshot_seconds=0.05) as m:
        a = list()
        for i in tqdm.tqdm(range(int(1e6))):
            i
            a.append(i)
        try:
            result = m.get_stats()
        except BrokenPipeError as e:
            exit()
    print(result.num_stats)
    
    import os
    os.makedirs('tmp', exist_ok=True)
    result.save_stats_plot('tmp/test.png')
    #os.unlink('tmp')

if __name__ == '__main__':
    test_monitor_process()
    test_monitor()



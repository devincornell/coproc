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
    
    import os
    os.makedirs('tmp', exist_ok=True)
    
    with conproc.Monitor(snapshot_seconds=0.05) as m:
        a = list()
        for i in tqdm.tqdm(range(int(1e8))):
            i
            a.append(i)
            if i > 0 and i % 10000 == 0:
                if i % 100000 == 0:
                    m.add_note(f'Note {i}')
                try:
                    result = m.get_stats()
                except BrokenPipeError as e:
                    exit()
                if result.has_results:
                    result.save_stats_plot('tmp/test.png', verbose=False)
                    
        print(result.num_stats)
    
    
    #os.unlink('tmp')

if __name__ == '__main__':
    test_monitor_process()
    test_monitor()



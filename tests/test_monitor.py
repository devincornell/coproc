import time
import typing

#import sys
#sys.path.append('..')
import concurrent
import dataclasses 

import datetime
import multiprocessing
import tqdm

def test_monitor_process():
    pass

def test_monitor():
    with concurrent.Monitor(snapshot_seconds=0.1) as m:
        a = list()
        for i in tqdm.tqdm(range(int(1e7))):
            i
            a.append(i)
        try:
            result = m.get_stats()
        except BrokenPipeError as e:
            exit()
    print(result.num_stats)
    result.save_stats_plot('test.png')
        

if __name__ == '__main__':
    test_monitor_process()
    test_monitor()



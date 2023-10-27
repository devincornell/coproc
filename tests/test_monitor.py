import time
import typing

import sys
sys.path.append('..')
import coproc

import dataclasses 

import datetime
import multiprocessing
import tqdm

def test_monitor_process():
    pass

def test_monitor():
    
    import os
    os.makedirs('tmp', exist_ok=True)
    
    # ask the monitor to regularly save the plot
    monitor = coproc.Monitor(
        snapshot_seconds=0.01,
        fig_fname='tmp/test.png',
        save_fig_freq=5,
    )
    
    with monitor as m:
        a = list()
        for i in tqdm.tqdm(range(int(1e2))):
            a.append(i)
            
            if i % 20 == 0:
                m.add_note(f'Note {i}')
                
                # ask the monitor to save the stats plot
                m.save_stats_plot(f'tmp/test.png', verbose=False)
                
                # move stats to this process then save as image here
                try:
                    result = m.get_stats()
                except BrokenPipeError as e:
                    exit()
                if result.has_results:
                    result.save_stats_plot('tmp/test.png', verbose=False)
        
        result = m.get_stats()
        print(result.num_stats)
    
    
    #os.unlink('tmp')

if __name__ == '__main__':
    test_monitor_process()
    test_monitor()



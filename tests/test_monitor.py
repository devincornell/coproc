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

def test_thread(dump_freq: int):
    l = list()
    for i in range(int(1e8)):
        l.append(i)
        if i > 0 and i % int(dump_freq) == 0:
            l = list()


def test_monitor_process():

    monitor = coproc.Monitor(
        snapshot_seconds=0.01, 
        fig_path='tmp/test_parallel.png',
        log_path='tmp/test_parallel.log'
    )

    with monitor as m:
        time.sleep(0.1)
        m.add_note('starting workers')
        with multiprocessing.Pool(4) as p:
            m.update_child_processes()
            p.map(test_thread, [1e5, 2e5, 3e5, 4e5])
        
        m.add_note('finished workers')
        
        l = list()
        for i in tqdm.tqdm(range(int(1e8)), ncols=80):
            l.append(i)
            if i > 0 and i % int(3e7) == 0:
                m.add_note('emptying list', 'dumping all memory', do_print=False)
                l = list()

        stats = m.get_stats()
    stats.save_memory_plot('tmp/test_parallel.png', font_size=8)

def test_monitor_simple():
        
    with coproc.Monitor(verbose=True) as m:
        for i in range(2):
            m.add_note('hello world')
            m.add_note('holla')
            stats = m.get_stats()
            assert(len(stats.notes) == 2*(i+1))
            m.save_memory_plot('tmp/test.png')
    #return
    # ask the monitor to regularly save the plot
    monitor = coproc.Monitor(
        snapshot_seconds=0.5,
        fig_path='tmp/test1.png',
        save_fig_freq=5,
        verbose = False,
    )
    
    with monitor as m:
        a = list()
        for i in tqdm.tqdm(range(int(1e2))):
            a.append(i)
            
            if i % 20 == 0:
                m.add_note(f'Note {i}')
                
                # ask the monitor to save the stats plot
                m.save_memory_plot(f'tmp/test.png', verbose=False)
                
                # move stats to this process then save as image here
                result = m.get_stats()

                if result.has_results:
                    result.save_memory_plot('tmp/test.png', verbose=False)
        time.sleep(1)
        
        result = m.get_stats()
        print(result.num_stats)
    
    
    #os.unlink('tmp')

if __name__ == '__main__':
    
    test_monitor_simple()
    test_monitor_process()


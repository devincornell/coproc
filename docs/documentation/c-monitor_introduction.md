# Introduction to `Monitor`

The `Monitor` object is used to create a concurrent process that will monitor the host process memory and cpu usage, record notes, and plot current progress as needed.


```python
import sys
sys.path.append('..')
import coproc
```

## Receiving Stats Client-side

In this example, I open the monitor and it runs while the inner code is executing. The monitor routinely checks for memory usage, and every so often sends a note to the monitor that is recorded. Uing `get_stats()` we can retrieve the statistics and plot it using `get_stats_plot()`. Notice that the notes appear in the figure.


```python
import time
import tqdm
with coproc.Monitor(snapshot_seconds=0.01) as m:
        
    l = list()
    for i in tqdm.tqdm(range(int(1e6)), ncols=80):
        l.append(i)
        if i > 0 and i % int(3e5) == 0:
            m.add_note('dump', 'dumping all memory', do_print=True)
            l = list() # dump memory
            
            stats = m.get_stats()
            p = stats.plot_memory(font_size=5)
            p.draw()
```

      0%|                                               | 0/1000000 [00:00<?, ?it/s]

     22%|██████▍                      | 221137/1000000 [00:00<00:00, 2211208.68it/s]

    dump; new_note.details='dumping all memory'


     60%|██████████████████            | 600001/1000000 [00:00<00:00, 596357.84it/s]

    dump; new_note.details='dumping all memory'


    100%|█████████████████████████████| 1000000/1000000 [00:01<00:00, 798758.80it/s]

    dump; new_note.details='dumping all memory'


    


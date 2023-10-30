# CoProc Python Package

`pip install --upgrade git+https://github.com/devincornell/coproc.git@main`

This module provides building blocks for running stateful, concurrent processes with specialized functionality that require back-and-forth communication with the host process. The building blocks essentially wrap pairs of processes and duplex pipes for efficient and complex communication. I have also built several useful 

For an introduction, see examples/introduction.ipynb.

![Explanatory diagram.](https://storage.googleapis.com/public_data_09324832787/coproc_diagram2.svg)

Building blocks:

+ `WorkerResource`: manage concurrent processes and the pipes they use to communicate. 
+ `WorkerResourcePool`: emulates behavior of `multiprocessing.Pool` but with priority queue.
+ `PriorityMessenger`: used by worker resource to manage multi-channel priority queues for communication between processes.

Useful applications:

+ `Monitor`: higher-level concurrent process for monitoring and reporting on other processes.





### `WorkerResource` and `PriorityMessenger` Examples

Use `WorkerResource` to manage a single concurrent process. In this example, `EchoProcess` simply echoes back received data.

```
import dataclasses

@dataclasses.dataclass
class EchoProcess(coproc.BaseWorkerProcess):
    '''Simply echoes back received data.'''
    verbose: bool = False
    def __call__(self):
        while True:
            try:
                data = self.messenger.receive_blocking()
            except coproc.ResourceRequestedClose:
                break
            
            if self.verbose: print(f'EchoProcess received: {data}')
            
            self.messenger.send_reply(data)
            
            if self.verbose: print(f'EchoProcess sent: {data}')

with coproc.WorkerResource(EchoProcess) as worker:
    worker.messenger.send_request('Hello, world!')
    print(worker.messenger.receive_blocking())
    
```

Instead of using `WorkerResource`'s context manager, you can also use `WorkerResource.start()` and `WorkerResource.terminate()` directly within a custom object.

```
@dataclasses.dataclass
class EchoResource:
    verbose: bool = False
    resource: coproc.WorkerResource = dataclasses.field(default_factory=lambda: coproc.WorkerResource(EchoProcess))
    
    def __enter__(self) -> coproc.PriorityMessenger:
        self.resource.start(verbose=self.verbose)
        return self
    
    def __exit__(self, *args):
        self.resource.terminate()
        
    def apply(self, data):
        self.messenger.send_request(data)
        return self.messenger.receive_blocking()
    
    @property
    def messenger(self):
        return self.resource.messenger

with EchoResource(verbose=True) as w:
    print(w.apply('Hello, world!'))

```

### `Monitor` Examples

```
import multiprocessing
import tqdm

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

```

![Monitor output example.](https://storage.googleapis.com/public_data_09324832787/monitor_ex2.png)


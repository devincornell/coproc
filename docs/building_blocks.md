
# Building Blocks

`coproc` is essentially a set of building blocks for working with processes. Here I demonstrate how these objects work together. See the documentation for more elaborate explanations.

+ `WorkerResource`: manage concurrent processes and the pipes they use to communicate using a messenger. See examples/introduction.ipynb for more.

+ `PriorityMessenger`: used by worker resource to manage multi-channel priority queues for communication between processes. See examples/messenger_introduction.ipynb for more.

+ `WorkerResourcePool`: maintains set of identical worker resources that can process data in a way that is similar to `multiprocessing.Pool`.

### High-level objects:

+ `Monitor`: create concurrent process for monitoring and reporting on other processes. Write to logs, generate reports, and 

### `WorkerResource` and `PriorityMessenger` Examples

Use `WorkerResource` to manage a single concurrent process. In this example, `EchoProcess` simply echoes back received data.

```python
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

```python
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

```python
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


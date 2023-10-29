# CoProc Python Package

`pip install --upgrade git+https://github.com/devincornell/coproc.git@main`

This module provides building blocks for running stateful concurrent processes.

For an introduction, see examples/introduction.ipynb.

These are the primary components:

+ `WorkerResource`: manage concurrent processes and the pipes they use to communicate. 
+ `PriorityMessenger`: handles multi-channel priority queue for communication between processes.
+ `Monitor`: higher-level concurrent process for monitoring and reporting on other processes.
+ `Pool`: emulates behavior of `multiprocessing.Pool` but with priority queue.


![Explanatory diagram.](https://storage.googleapis.com/public_data_09324832787/coproc_diagram2.svg)

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
import time
with coproc.Monitor(snapshot_seconds=0.01) as m:
    for _ in range(10):
        m.add_note('hi')
        time.sleep(0.1)
    stats = m.get_stats()
stats.get_stats_plot(font_size=10)
```

![Monitor output example.](https://storage.googleapis.com/public_data_09324832787/monitor_ex1.png)


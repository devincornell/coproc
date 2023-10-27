# coproc

This module provides an building blocks for running stateful concurrent processes.



These are the primary components:

+ `WorkerResource`: manage concurrent processes and the pipes they use to communicate. 
+ `PriorityMessenger`: handles multi-channel priority queue for communication between processes.
+ `Monitor`: higher-level concurrent process for monitoring and reporting on other processes.
+ `Pool`: emulates behavior of `multiprocessing.Pool` but with priority queue.


```
@dataclasses.dataclass
class EchoProcess(coproc.BaseWorkerProcess):
    '''Simply echoes back received data.'''
    def __call__(self):
        while True:
            try:
                data = self.messenger.receive_blocking()
            except coproc.ResourceRequestedClose:
                break
            self.messenger.send_reply(data)

with coproc.WorkerResource(EchoProcess) as worker:
    worker.messenger.send_request('Hello, world!')
    print(worker.messenger.receive_blocking())
```


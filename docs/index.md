# Introduction

`coproc` provides building blocks for running stateful, concurrent, and specialized worker processes that require back-and-forth communication. The name comes from the combination of "cooperative" and "process" - `coproc` makes it easier to create specialized processes that cooperate to solve a single task.

## Design

+ In `coproc`, we refer to the main process of a Python script as the _host_, and any daeomon processes it creates as _worker_ processes. 

+ The host maintains a `WorkerResource` object which includes the child process and a pipe for transmitting information, as well as a `PriorityMessenger` that manages communications across the channel. 

+ `WorkerProcess` exists on the worker side, and maintains the processes state and main event loop. The worker process also includes a `PriorityMessenger` that is used to communicate with the host process.

The following diagram shows how the host and worker work together: they each maintain `PriorityMessenger` objects that support multi-channel priority messaging designs.

![Explanatory diagram.](https://storage.googleapis.com/public_data_09324832787/coproc_diagram2.svg)

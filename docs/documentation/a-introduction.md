# Overview

In this notebook, I demonstrate use of the most basic building blocks of `conproc`: `WorkerResource` and `PriorityQueue`.



```python
import sys
sys.path.append('../')
import coproc
```

## `WorkerResource` and Managing Worker Processes

The `WorkerResource` object is the most basic tool for working with concurrent processes. It manages both `Process` and `Pipe` objects wrapped in multi-channel priority queues with robust messaging support. The most common use case is to create a `WorkerResource` object and then manage the resource using a wrapper object. While it does have a built-in context manager for starting and ending the process, you will probably want to create your own outer context manager using the basic `.start()`, `.stop()`, and `.join()` methods.

The `WorkerResource` constructor accepts a class that is used to manage the process. That class' `__init__` method will be called in the host process with a single `PriorityMessenger` argument, and you may pass additional keyword arguments through the `.start()` method. The resulting instance will then be passed to the process for the duration of the `__call__` method, which does not accept any arguments on its own - you must pass any relevant data through the constructor when starting the process.

The following class maintains the state of an example worker process. As long as it is alive, it will simply receive data and echo the data back to the host process. Notice that `__init__` accepts the messenger and an additional optional parameter. The messenger is passed automatically, whereas the keyword arguments are passed through the `.start()` method. I will discuss the `.receive_blocking()` and `.send_norequest()` methods in more detail later in the messaging section.


```python
import os
    
def custom_echo_process(messenger: coproc.PriorityMessenger, verbose: bool = False):
    '''Main process loop.'''
    if verbose: print(f'Starting process {os.getpid()}')
    
    while True:
        # wait until a new message is received
        data = messenger.receive_blocking()
        if verbose: print(f'process {os.getpid()} received: {data}')
        
        # send the same data back
        messenger.send_norequest(data)

resource = coproc.WorkerResource(custom_echo_process)
resource
```




    WorkerResource(target=<function custom_echo_process at 0x785515c40ea0>, messenger_type=<class 'coproc.messenger.prioritymessenger.PriorityMessenger'>, method=None, _proc=None, _messenger=None)



You can see here that the `verbose` argument is passed through start.


```python
import time

resource.start(verbose=True)
time.sleep(0.1)
resource.terminate()

# wait for process to terminate
while resource.is_alive():
    pass

resource.start()
time.sleep(0.1)
resource.terminate()
```

    Starting process 1005612


#### Context Managers

The resource should always be used in some type of context manager, and we can use the built-in context manager for simple applications. The downside to this is that you cannot pass any arguments to `.start()`.


```python
with coproc.WorkerResource(custom_echo_process) as w:
    print(type(w))
```

    <class 'coproc.worker_resource.worker_resource.WorkerResource'>


Typically it will be better to create your own wrapper objects for cleaner interfaces. Here I use a dataclass that creates a `WorkerResource` in the constructor and provide the most basic context management.


```python
import typing
import dataclasses

@dataclasses.dataclass
class EchoResource:
    verbose: bool = False
    resource: coproc.WorkerResource = dataclasses.field(default_factory=lambda: coproc.WorkerResource(custom_echo_process))
    
    def __enter__(self) -> typing.Self:
        self.resource.start(verbose=self.verbose)
        return self
    
    def __exit__(self, *args):
        self.resource.terminate()

    @property
    def messenger(self) -> coproc.PriorityMessenger:
        '''Expose the messenger to the user.'''
        return self.resource.messenger

with EchoResource(verbose=True) as w:
    print(w)
```

    EchoResource(verbose=True, resource=WorkerResource(target=<function custom_echo_process at 0x785515c40ea0>, messenger_type=<class 'coproc.messenger.prioritymessenger.PriorityMessenger'>, method=None, _proc=<ForkProcess name='ForkProcess-4' pid=1005619 parent=1005583 started>, _messenger=PriorityMessenger(pipe=<multiprocessing.connection.Connection object at 0x785515c7f510>, queue=PriorityMultiQueue(queues={}), request_ctr=RequestCtr(requests=Counter(), replies=Counter(), sent=Counter(), received=Counter()))))


# Messaging Between Processes: `PriorityMessenger` and `MultiMessenger`

The `coproc` messengers are wrappers around standard `multiprocessing.Pipe` objects that create an interface for exchange between processes. There are two primary messenger types that can be used for communications: `PriorityMessenger` and `MultiMessenger`. While they both support the request and channel interfaces, only `PriorityMessenger` supports priorities, as the name would imply. 


### Sending Messages

**Basic communication.**
    + `send_norequest()` sends a message without expecting a reply. This is the most basic method for sending data between processes. Specify `channel_id` to send to a specific channel (`None` by default, which is actually a valid channel). The simplest use of messager would be to to send messages back and forth using `send_norequest()`. This is most similar to `pipe.send()` and `pipe.recv()` except that it manages multiple channels (see next section).

1. **Channels.** Every message is associated with a channel, which can be any hashable object. 
    + You can specify the channel using the `channel_id` parameter of most send/receive functions, and the default is `None` - itself a valid, hashable channel id which you may use by default.

2. **Requests.** Using special request and reply methods enables the messenger to track the number of requests sent and replies received so that it can wait for replies to a specific set of requests.
    + The requesting process would use `send_request()` to send a request, and the other process would use `send_reply()` so that the requesting process knows that the message is a reply.
    + Note that the request tracking happens on a per-channel basis, so you can send multiple requests on different channels and wait for replies to each set of requests.
    + `send_request()` will send a message while also incrementing the count of requested messages for the given channel.
    + `send_reply()` will send a message while also incrementing the count of received replies for the recipient channel.

3. **Priorities.** By default, the `PriorityMessenger` looks for a `priority` attribute on any messages being sent, and will sort the messages into a priority queue, rather than a standard fifo queue. If the sent item does not have this attribute, by default it is set to `-inf`.

4. **Special Messages.** There are several types of special messages that bypass the channel and priority queue interface - they are handled as soon as the messages are received (which occurs when any receive function is called), prior to placement in the queue.
    + `send_error()` will send an exception object to the other messenger that will then be raised directly in the recipient process. I recommend using custom exceptions for this behavior.
    + `send_close_request()` will send a message that directly raises a `ResourceRequestedClose` exception in the recipient process. Catch this exception in your processes to handle a shutdown. You may want to use this in conjunction with the `.join()` method, which waits for the process to finish.

### Receiving Messages

Any time one of the following receive methods is called, data will be transferred from the `multiprocessing.Pipe` into the message queue. The following diagram shows the basic flow of data from the pipe to the receive methods.

![Messenger Diagram](https://storage.googleapis.com/public_data_09324832787/messaging_interface.svg)

The receive method you use depends on the desigred behavior.

+ `available()` loads data from pipe into the queue, and returns the number of available messages on the specified channel. 
+ `receive_available()` calls `available()` and returns all available messages if there are any. Otherwise, returns an empty list.
+ `receive_blocking()` blocks until a message is received on the specified channel, then returns the message.
+ `receive_remaining()` yields replies on the specified channel until all outstanding requests have been replied to.


```python
with EchoResource(verbose=True) as w:
    w.resource.messenger.send_norequest('hello')
    print(w.messenger.receive_blocking())
```

    Starting process 1005620
    process 1005620 received: hello
    hello


#### Requests

The messenger also has support for handling messages that act as requests and replies. Alternatively, you may use a combination of `.send_request` (on the host side) and `.send_reply` (on the worker side) to send requests that are expected to have replies. You can check the number of remaining messages using `.remaining()`, and call `.receive_remaining()` to block while retrieving all remaining messages. You, the client, must manually manage the request-reply pattern, but this is intended to be used as a way of keeping track of how many messages are expected to be received.


```python
def another_echo_process(messenger: coproc.PriorityMessenger):
    '''Main process loop.'''
    while True:
        data = messenger.receive_blocking()
        messenger.send_reply(data)
            
with coproc.WorkerResource(another_echo_process) as w:
    print(w.messenger.remaining())
    w.messenger.send_request('hello')
    print(w.messenger.remaining())
    print(w.messenger.receive_blocking())
    print(w.messenger.remaining())
    
    [w.messenger.send_request(i) for i in range(3)]
    w.messenger.remaining()
    for d in w.messenger.receive_remaining():
        print(d)
```

    0
    1
    hello
    0
    0
    1
    2


#### Message Availability

When juggling between receiving messages and other tasks, it is often helpful to retrieve all messages that are available in the queue at a given point in time. Check how many messages have been received using `.available()` and retrieve available messages using `.receive_available()` instead of `.receive_blocking()`.


```python
with coproc.WorkerResource(another_echo_process) as w:
    print(w.messenger.available())
    w.messenger.send_request('hello')
    print(w.messenger.available())
    time.sleep(0.1) # wait for process to reply
    print(w.messenger.available())
    print(w.messenger.receive_available())
```

    0
    0
    1
    ['hello']


#### Custom Messages and Priorities

The `PriorityMessenger` includes a priority system which you can use by creating custom message types. It determines the priority of a message by looking for a `priority` attribute on the data being passed. Here I create two types of messages, each with a different priority - note that lower priority value means it will be returned first. This follows the behavior of the `queue.PriorityQueue`.


```python
@dataclasses.dataclass
class WarningMessage:
    message: str
    priority: int = 0 # higher priority

@dataclasses.dataclass
class DataMessage:
    data: int
    priority: int = 1 # lower priority
    
def athird_echo_process(messenger: coproc.PriorityMessenger):
    '''Main process loop.'''
    while True:
        num = messenger.receive_blocking()
        messenger.send_reply(DataMessage(num))
        if num < 0:
            messenger.send_norequest(WarningMessage('negative number'))
    
with coproc.WorkerResource(athird_echo_process) as w:
    w.messenger.send_request(1)
    time.sleep(0.1)
    print(w.messenger.receive_available())
    
    # notice the warning appears in the queue first
    w.messenger.send_request(-1)
    time.sleep(0.1)
    print(w.messenger.receive_available())
```

    [DataMessage(data=1, priority=1)]
    [WarningMessage(message='negative number', priority=0), DataMessage(data=-1, priority=1)]


#### Message Channels

In more complicated situations, there may be cases when you want to communicate on separate messaging channels. Fortunately, `PriorityMessenger` can also handle that, as most methods accept a `channel_id` parameter that is defaulted to `None`. The `channel_id` can be any hashable object, so `None` is actually the channel being communicated on for most of the previous examples. Each channel keeps track of its own request/receive counts, and each can make a blocking receive until they receive the expected message. In this way, the channels essentially operate as separate pipes.

In the following example, I use a single channel for data sent from the host to the client process, and two channels for data sent from the client to the host. Whereas the `DATA` channel is used to transmit regular data synchronously between the processes, `WARNING` is used to transmit data asynchronously from the client process to the host. Note that we use the same channel for the bidirectional communication from the host to the client process because we are taking advantage of the request interface.


```python
import enum
class Channels(enum.Enum):
    DATA = 1
    WARNING = 2

def afourth_echo_process(messenger: coproc.PriorityMessenger):
    while True:
        try:
            data = messenger.receive_blocking(Channels.DATA)
        except coproc.ResourceRequestedClose:
            break
        
        if len(data) < 10:
            # send a message on the warning channel
            messenger.send_norequest(f'warning: data must be positive', Channels.WARNING)
        
        # either way, echo result
        messenger.send_reply(data, Channels.DATA)


def receive_print_warnings(message: str, messenger: coproc.PriorityMessenger) -> str:
    messenger.send_request(message, Channels.DATA)
    print(f'{messenger.remaining(Channels.DATA)=}')
    
    data = messenger.receive_blocking(Channels.DATA)
    print(f'{messenger.remaining(Channels.DATA)=}')
    
    for warning in messenger.receive_available(Channels.WARNING):
        print(warning)
        
    return data

with coproc.WorkerResource(afourth_echo_process) as w:
    print(receive_print_warnings('hello', w.messenger))
    print(receive_print_warnings('world', w.messenger))
    print(receive_print_warnings('hello world!', w.messenger))
```

    messenger.remaining(Channels.DATA)=1
    messenger.remaining(Channels.DATA)=0
    warning: data must be positive
    hello
    messenger.remaining(Channels.DATA)=1
    messenger.remaining(Channels.DATA)=0
    warning: data must be positive
    world
    messenger.remaining(Channels.DATA)=1
    messenger.remaining(Channels.DATA)=0
    hello world!


#### System Messages

There are two special types of messages that will be prioritized over all other messages: sending errors using `send_error()` (typically sent from worker process) and sending a termination signal using `send_close_request()` (typically sent by the host process). The `send_error()` message will send a signal that raises the sent exception on the client side, and `send_close_request()` will raise a `ResourceRequestedClose` exception on the worker side. You will need to handle these cases on both sides of the pipe.


```python
def afifth_echo_process(messenger: coproc.PriorityMessenger):
    while True:
        try:
            data = messenger.receive_blocking()
        except coproc.ResourceRequestedClose:
            break            
        if data >= 0:
            messenger.send_reply(data)
        else:
            messenger.send_error(ValueError('data must be positive'))



with coproc.WorkerResource(afifth_echo_process) as w:
    
    # regular request/reply
    w.messenger.send_request(1)
    print(w.messenger.receive_blocking())
    
    # this request will elicit an error
    w.messenger.send_request(-1)
    try:
        print(w.messenger.receive_blocking())
    except ValueError as e:
        print(type(e), e)
        
    w.messenger.send_close_request()
    w.join()
    time.sleep(0.5)
    print(w.is_alive())
```

    NoneType: None


    1
    <class 'ValueError'> data must be positive
    False


`WorkerResource` and `PriorityMessenger` serve as essential building blocks for building interfaces to concurrent processes, including some that appear as part of this package. See the documentation for examples of those.

## An Inspirational Example

The following example shows a process dedicated to controlling a process which prints to the screen. It is a particularly good example because it does something that would not be possible in a single process nor using map functions as part of the multiprocessing package.


```python
@dataclasses.dataclass
class StartPrinting:
    pass

@dataclasses.dataclass
class StopPrinting:
    pass

@dataclasses.dataclass
class ChangePrintBehavior:
    print_frequency: int
    print_char: str
    
@dataclasses.dataclass
class Receipt:
    pass
```


```python
class AlreadyPrintingError(Exception):
    '''Raised when user requests start but process is already printing.'''

class AlreadyNotPrintingError(Exception):
    '''Raised when user requests stop but process is already not printing.'''
```


```python
import typing

@dataclasses.dataclass
class PrintingProcess:
    print_frequency: int # these must be set at worker start
    print_char: str
    keep_printing: bool # this can optionally be set
    
    def __call__(self, messenger: coproc.PriorityMessenger):
        print(f'{self.keep_printing=}')
        while True:
            try:
                # if we're not printing, keep waiting for a new message
                msgs = messenger.receive_available()#blocking = not self.keep_printing)
            except IndexError:
                msgs = []
                
            for msg in msgs:
                self.handle_message(messenger, msg)
                
            if self.keep_printing:
                print(self.print_char, end='', flush=True)
                time.sleep(self.print_frequency)
    
    def handle_message(self, messenger: coproc.PriorityMessenger, msg: typing.Union[StartPrinting, StopPrinting, ChangePrintBehavior]):
        if isinstance(msg, StartPrinting):
            if self.keep_printing:
                messenger.send_error(AlreadyPrintingError())
            self.keep_printing = True
            
        elif isinstance(msg, StopPrinting):
            if not self.keep_printing:
                messenger.send_error(AlreadyNotPrintingError())
            self.keep_printing = False
            
        elif isinstance(msg, ChangePrintBehavior):
            self.print_frequency = msg.print_frequency
            self.print_char = msg.print_char
            
        else:
            # process should die in this case
            messenger.send_error(NotImplementedError(f'Unknown message type: {type(msg)}'))
        
        messenger.send_reply(Receipt())

```


```python
@dataclasses.dataclass
class PrintProcessController:
    messenger: coproc.PriorityMessenger
    def start_printing(self):
        self.messenger.send_request(StartPrinting())
        return self.messenger.receive_blocking() # wait for receipt
    
    def stop_printing(self):
        self.messenger.send_request(StopPrinting())
        return self.messenger.receive_blocking() # wait for receipt
    
    def change_behavior(self, print_frequency: int, print_char: str):
        self.messenger.send_request(ChangePrintBehavior(print_frequency, print_char))
        return self.messenger.receive_blocking() # wait for receipt

class Printer:
    
    def __init__(self, print_frequency: int, print_char: str, start_printing: bool = False):
        target = PrintingProcess(
            print_frequency = print_frequency, 
            print_char = print_char, 
            keep_printing = start_printing
        )
        self.resource = coproc.WorkerResource(target=target)
        
    def __enter__(self) -> PrintProcessController:
        self.resource.start()
        return PrintProcessController(self.resource.messenger)
    
    def __exit__(self, *args):
        self.resource.terminate()
```


```python
with Printer(print_frequency=0.05, print_char='x', start_printing=False) as p:
    print('\n----')
    time.sleep(0.2) # shouldnot be printing
    print('\n----')
    p.start_printing()
    print('\n----')
    time.sleep(0.2) # should be printing
    print('\n----')
    p.change_behavior(0.01, 'y')
    print('\n----')
    time.sleep(0.2) # should be printing
    p.stop_printing()
    time.sleep(0.2) # should not be printing
    
    try: # this error is being sent by the printer process
        p.stop_printing()
    except AlreadyNotPrintingError:
        print('Already not printing! oh well.')
```

    self.keep_printing=False


    
    ----
    
    ----
    
    ----
    xxxxyyyyyyyyyyyyyyyyyyy
    ----
    
    ----


    NoneType: None


    Already not printing! oh well.


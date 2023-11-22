# Messaging Between Processes

## `PriorityMessenger` and `MultiMessenger`

The `coproc` messengers are wrappers around standard `multiprocessing.Pipe` objects that create an interface for exchange between processes. There are two primary messenger types that can be used for communications: `PriorityMessenger` and `MultiMessenger`. While they both support the request and channel interfaces, only `PriorityMessenger` supports priorities, as the name would imply. 

The diagram below shows how both the host and worker processes maintain separate messengers that allow them to communicate together. While I imagine that some of the messenger features will be most often used on one side or the other (for example, the request/reply interface), the messages are identical.

![Overview diagram.](https://storage.googleapis.com/public_data_09324832787/coproc_diagram2.svg)

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

![Messenger Diagram](https://storage.googleapis.com/public_data_09324832787/messaging_interface2.svg)

The receive method you use depends on the desigred behavior.

+ `available()` loads data from pipe into the queue, and returns the number of available messages on the specified channel. 
+ `receive_available()` calls `available()` and returns all available messages if there are any. Otherwise, returns an empty list.
+ `receive_blocking()` blocks until a message is received on the specified channel, then returns the message.
+ `receive_remaining()` yields replies on the specified channel until all outstanding requests have been replied to.

# Example Usage

Now I will give some examples for how to use the messenger interface.


```python
import sys
sys.path.append('../')
import coproc

import dataclasses
import time
```

## Choosing a Messenger

While messengers can be used by themselves, they can be managed by `WorkerResource` objects by passing them to the `messenger_type` parameter of the constructor. See how `WorkerResource` creates two messengers: one for the host process and one for the worker process.


```python
@dataclasses.dataclass
class ExampleProcess:
    messenger: coproc.PriorityMessenger
    
    def __call__(self):
        print(f'process messenger: {self.messenger}')

worker = coproc.WorkerResource(
    worker_process_type =  ExampleProcess,
    messenger_type = coproc.PriorityMessenger,
)
with worker as w:
    time.sleep(1)
    print(f'resource messenger: {w.messenger}')
```

    process messenger: PriorityMessenger(pipe=<multiprocessing.connection.Connection object at 0x7f3991f16c10>, queue=PriorityMultiQueue(queues={}), request_ctr=RequestCtr(requests=Counter(), replies=Counter(), sent=Counter(), received=Counter()))
    resource messenger: PriorityMessenger(pipe=<multiprocessing.connection.Connection object at 0x7f394a08f880>, queue=PriorityMultiQueue(queues={}), request_ctr=RequestCtr(requests=Counter(), replies=Counter(), sent=Counter(), received=Counter()))


## Messenger Interface

Now I will give some examples for using the messenger interface.

#### Send/receive and Channels

In this example you can see how we send and receive the most basic messages messages on two separate channels over the same pipe. We use the `send_norequest()` method to send data to the other side, and specify the `channel_id` parameter of most send/receive methods to specify the channel.


```python
CHANNEL_A = 1
CHANNEL_B = 2

@dataclasses.dataclass
class EchoProcess1:
    messenger: coproc.PriorityMessenger
    def __call__(self):
        while True:
            print(f'awaiting messages')
            self.messenger.await_available()
            print(f'some messages were found')
            for data in self.messenger.receive_available(CHANNEL_A):
                self.messenger.send_norequest(data, CHANNEL_A)
            
            for data in self.messenger.receive_available(CHANNEL_B):
                self.messenger.send_norequest(data, CHANNEL_B)
            
            #data = self.messenger.receive_blocking()
            #print(f'worker received: {data}')
            #self.messenger.send_norequest(data)

with coproc.WorkerResource(EchoProcess1) as w:
    print(f'{w.messenger.available()=}')
    print(w.messenger.send_norequest('hello', channel_id=CHANNEL_A))
    print(w.messenger.send_norequest('hi', channel_id=CHANNEL_B))
    time.sleep(0.1) # wait for process to return it
    
    print(f'{w.messenger.available()=}')
    print(f'{w.messenger.receive_blocking(CHANNEL_A)=}')
    print(f'{w.messenger.receive_blocking(CHANNEL_B)=}')
```

    awaiting messages
    some messages were found
    awaiting messages
    w.messenger.available()=0
    None
    None
    w.messenger.available()=0
    w.messenger.receive_blocking(CHANNEL_A)='hello'
    w.messenger.receive_blocking(CHANNEL_B)='hi'


#### Request Interface

In this example, I use `send_request()` and `send_reply()` to send and receive messages synchronously. The messenger will track the number of requests sent, and we can use `receive_remaining()` to wait for all expected replies to be received.


```python
@dataclasses.dataclass
class EchoProcess2(coproc.BaseWorkerProcess):
    def __call__(self):
        while True:
            data = self.messenger.receive_blocking()
            self.messenger.send_reply(data)
            
with coproc.WorkerResource(EchoProcess2) as w:
    print(f'{w.messenger.remaining()=}')
    print(f'{w.messenger.send_request("hello")=}')
    print(f'{w.messenger.remaining()=}')
    time.sleep(0.1)
    print(f'{w.messenger.receive_blocking()=}')
    print(f'{w.messenger.remaining()=}')
    
    print(f'sending {[w.messenger.send_request(i) for i in range(3)]}')
    print(f'{w.messenger.remaining()=}')
    for d in w.messenger.receive_remaining():
        print(d)
```

    w.messenger.remaining()=0
    w.messenger.send_request("hello")=None
    w.messenger.remaining()=1
    w.messenger.receive_blocking()='hello'
    w.messenger.remaining()=0
    sending [None, None, None]
    w.messenger.remaining()=3
    0
    1
    2


#### Priority Interface

We can set the priority of messages by adding a `priority` attribute to the message - we used simple wrapper objects here to accomplish that. Notice that the process accesses the higher priority objects first.

Note that the default priority is `-inf`, so any message without a priority will be sent to the back of the queue. In this example, we send messages with different priorities and see how they are received in order.


```python
@dataclasses.dataclass
class PrintProcess(coproc.BaseWorkerProcess):
    def __call__(self):
        while True:
            for data in self.messenger.receive_available():
                #self.messenger.send_reply(data)
                print(data)
            time.sleep(1)

@dataclasses.dataclass
class HighPriorityMessage:
    text: str
    priority: int = 0 # lower is more improtant

@dataclasses.dataclass
class LowPriorityMessage:
    text: str
    priority: int = 1 # lower is more improtant
            
with coproc.WorkerResource(PrintProcess, coproc.PriorityMessenger) as w:
    for i in range(3):
        w.messenger.send_norequest(LowPriorityMessage(f'low {i}'))
        w.messenger.send_norequest(HighPriorityMessage(f'high {i}'))
        
    time.sleep(0.1) # wait for process to finish. Should I use join here?
```

    HighPriorityMessage(text='high 0', priority=0)
    HighPriorityMessage(text='high 1', priority=0)
    HighPriorityMessage(text='high 2', priority=0)
    LowPriorityMessage(text='low 0', priority=1)
    LowPriorityMessage(text='low 1', priority=1)
    LowPriorityMessage(text='low 2', priority=1)


#### Special Messages

In this last example I demonstrate use of the special messages. The `send_error()` method sends an exception object to the other process, which will be raised directly in the other process. The `send_close_request()` method sends a message that raises a `ResourceRequestedClose` exception in the other process. This is useful for shutting down the process.


```python
@dataclasses.dataclass
class PrintProcess2(coproc.BaseWorkerProcess):
    def __call__(self):
        while True:
            try:
                message = self.messenger.await_available()
                results = self.messenger.receive_available()
            except coproc.ResourceRequestedClose as e:
                self.messenger.send_error(ValueError('process was closed successfully'))
                break # exits the process naturally
            for data in results:
                print(data)
            
with coproc.WorkerResource(PrintProcess2) as w:
    w.messenger.send_norequest('message 1')
    w.messenger.send_close_request()
    
    try:
        w.messenger.await_available()
    except ValueError as e:
        print('successfully caught value error sent from process')
        
    time.sleep(0.1) # wait for process to finish. Should I use join here?
```

    Traceback (most recent call last):
      File "/tmp/ipykernel_1047367/3808203598.py", line 6, in __call__
        message = self.messenger.await_available()
      File "/DataDrive/projects/coproc/examples/../coproc/messenger/multimessenger.py", line 121, in await_available
        self._receive_and_handle()
      File "/DataDrive/projects/coproc/examples/../coproc/messenger/multimessenger.py", line 133, in _receive_and_handle
        self._handle_message(msg)
      File "/DataDrive/projects/coproc/examples/../coproc/messenger/multimessenger.py", line 147, in _handle_message
        raise ResourceRequestedClose(f'Resource requested that this process close.')
    coproc.messenger.exceptions.ResourceRequestedClose: Resource requested that this process close.


    successfully caught value error sent from process


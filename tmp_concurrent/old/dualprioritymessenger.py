from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import queue

from .messages import PayloadType, MessageFromProcessType, MessageToProcessType, MessageFromProcess, MessageToProcess, SubmitData, Close, ReplyData, UserfuncError
from .exceptions import ResourceRequestedClose, MessageNotRecognizedError

def get_dual_priority_messenger_pair(**kwargs) -> typing.Tuple[PriorityProcessMessenger, PriorityResourceMessenger]:
    resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
    return (
        PriorityProcessMessenger(pipe=process_pipe, **kwargs),
        PriorityResourceMessenger(pipe=resource_pipe, **kwargs),
    )

@dataclasses.dataclass
class BasePriorityMessenger(typing.Generic[PayloadType]):
    pipe: multiprocessing.connection.Connection
    queue: queue.PriorityQueue[typing.Union[MessageFromProcess, MessageToProcess]] = dataclasses.field(default_factory=queue.PriorityQueue)
    sent: int = 0
    received: int = 0

    def queue_size(self) -> int:
        return self.queue.qsize()
    
    def receive_available(self) -> typing.Generator[PayloadType]:
        '''Blocking receive of all data from pipe in a generator.'''
        while self.available():
            yield self.receive_data()

    def receive_remaining(self) -> typing.Generator[PayloadType]:
        '''Blocking receive of all data from pipe in a generator.'''
        while self.remaining() > 0:
            yield self.receive_data()
    
    def available(self) -> bool:
        '''Check if data has been sent here already.'''
        return self.pipe.poll() or not self.queue.empty()
    
    def remaining(self) -> int:
        '''Count the number of data messages sent vs the number received.'''
        return self.sent - self.received
    
    def receive_data(self, blocking: bool = True) -> PayloadType:
        raise NotImplementedError(f'{self.__class__.__name__} must implement receive_data()')

    def receive_message(self, blocking: bool = True) -> typing.Union[MessageFromProcess, MessageToProcess]:
        '''Blocking receive of data from pipe to queue and return next item.'''
        while self.pipe.poll() or (self.queue.empty() and blocking):
            #print(f'<{blocking=}/{self.pipe.poll()=}/{self.queue.empty()=}', end='', flush=True)
            print(f'<', end='', flush=True)
            msg: MessageFromProcess = self.pipe_recv()
            print(f'{msg=}>', end='', flush=True)
            self.queue.put_nowait(msg)
            blocking = False
        #print(f'{self.queue.qsize()=}, {self.queue.get_nowait()=}')
        return self.queue.get_nowait()
    
    def pipe_recv(self) -> MessageFromProcess:
        '''Receive data from pipe.'''
        try:
            return self.pipe.recv()
        except (EOFError, BrokenPipeError):
            raise BrokenPipeError(f'Tried to receive data when pipe was broken.')

@dataclasses.dataclass
class PriorityResourceMessenger(BasePriorityMessenger, typing.Generic[PayloadType]):
    sent: int = 0
    received: int = 0
    
    ############### Sending ###############
    def request_data_multiple(self, data: typing.Iterable[PayloadType]) -> None:
        '''Blocking send of multiple data to pipe.'''
        for d in data:
            self.request_data(d)

    def request_data(self, data: PayloadType) -> None:
        '''Blocking send of data to pipe.'''
        self.pipe.send(SubmitData(data))
        self.sent += 1
        
    def request_close(self) -> None:
        '''Blocking send of close message to pipe.'''
        return self.pipe.send(Close())
    
    ############### receiving ###############    
    def receive_data(self, blocking: bool = True) -> PayloadType:
        '''Blocking receive of data from pipe.'''
        msg: MessageFromProcess = self.receive_message(blocking=blocking)
        
        # handle message in different ways
        if msg.mtype is MessageFromProcessType.REPLY_DATA:
            self.received += 1
            return msg.payload
        elif msg.mtype is MessageFromProcessType.USERFUNC_ERROR:
            raise msg.exception
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')


@dataclasses.dataclass
class PriorityProcessMessenger(BasePriorityMessenger, typing.Generic[PayloadType]):
    
    ############### Sending ###############
    def reply_data_multiple(self, data: typing.Iterable[PayloadType]) -> None:
        '''Blocking send of multiple data to pipe.'''
        for d in data:
            self.reply_data(d)
    
    def reply_data(self, data: PayloadType):
        '''Blocking send of data to pipe.'''
        self.pipe.send(ReplyData(data))
        self.sent += 1
        
    def reply_error(self, exception: BaseException):
        '''Blocking send of close message to pipe.'''
        self.pipe.send(UserfuncError(exception))
        
    ############### Receiving ###############
    def receive_data(self, blocking: bool = True) -> PayloadType:
        '''Blocking receive of data from pipe.'''
        msg: MessageToProcess = self.receive_message(blocking=blocking)
        
        if msg.mtype is MessageToProcessType.SUBMIT_DATA:
            self.received += 1
            return msg.payload
        
        elif msg.mtype is MessageToProcessType.CLOSE:
            raise ResourceRequestedClose(f'The worker resource requested that this thread close.')
        
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')
        
        
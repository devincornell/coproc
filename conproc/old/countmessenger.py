
from __future__ import annotations
import typing
import dataclasses
import multiprocessing
from .messages import PayloadType, MessageFromProcessType, MessageToProcessType, MessageFromProcess, MessageToProcess, SubmitData, Close, ReplyData, UserfuncError
from .errors import *


def get_basic_messenger_pair(**kwargs) -> typing.Tuple[BasicProcessMessenger, BasicResourceMessenger]:
    resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
    return (
        BasicProcessMessenger(pipe=process_pipe, **kwargs),
        BasicResourceMessenger(pipe=resource_pipe, **kwargs),
    )

class MessageNotRecognizedError(BaseException):
    pass

@dataclasses.dataclass
class BaseMessenger(typing.Generic[PayloadType]):
    pipe: multiprocessing.Pipe

    def poll(self) -> bool:
        '''Poll pipe for messages.'''
        return self.pipe.poll()

@dataclasses.dataclass
class CountResourceMessenger(BaseMessenger):
    sent: int = 0
    received: int = 0
    
    def remaining(self) -> int:
        return self.sent - self.received
    
    def send_data(self, data: PayloadType):
        '''Blocking send of data to pipe.'''
        self.pipe.send(SubmitData(data))
        self.sent += 1
        
    def request_close(self):
        '''Blocking send of close message to pipe.'''
        self.pipe.send(Close())
    
    def receive_data(self) -> PayloadType:
        '''Blocking receive of data from pipe.'''
        try:
            msg: MessageFromProcess = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            raise BrokenPipeError(f'Tried to receive data when pipe was broken.')

        # handle message in different ways
        if msg.mtype is MessageFromProcessType.REPLY_DATA:
            self.received += 1
            return msg.data
        elif msg.mtype is MessageFromProcessType.USERFUNC_ERROR:
            raise msg.exception
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')

import queue

@dataclasses.dataclass
class QueueProcessMessenger(BaseMessenger):
    '''Messenger on process side.'''
    queue: queue.PriorityQueue = dataclasses.field(default_factory=queue.PriorityQueue)
    
    def send_reply(self, data: PayloadType):
        '''Blocking send of data to pipe.'''
        self.pipe.send(ReplyData(data))
    
    def send_error(self, exception: Exception):
        '''Blocking send of close message to pipe.'''
        self.pipe.send(UserfuncError(exception))
        
    def receive_data(self) -> PayloadType:
        '''Blocking receive of data from pipe.'''
        try:
            msg: MessageToProcess = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            #raise BrokenPipeError(f'Tried to receive data when pipe was broken.')
            exit()
        
        if msg.mtype is MessageToProcessType.SUBMIT_DATA:
            return msg.data
        
        elif msg.mtype is MessageToProcessType.CLOSE:
            exit()
        



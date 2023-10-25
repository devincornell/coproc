from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection

from .messages import SendPayloadType, RecvPayloadType, MessageFromProcessType, MessageToProcessType, MessageFromProcess, MessageToProcess, SubmitData, Close, ReplyData, UserfuncError
from .exceptions import ResourceRequestedClose, MessageNotRecognizedError


def get_messenger_pair(**kwargs) -> typing.Tuple[ProcessMessenger, ResourceMessenger]:
    resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
    return (
        ProcessMessenger(pipe=process_pipe, **kwargs),
        ResourceMessenger(pipe=resource_pipe, **kwargs),
    )

@dataclasses.dataclass
class BaseMessenger(typing.Generic[SendPayloadType, RecvPayloadType]):
    pipe: multiprocessing.connection.Connection

    def available(self) -> bool:
        '''Poll pipe for messages.'''
        return self.pipe.poll()

@dataclasses.dataclass
class ResourceMessenger(BaseMessenger, typing.Generic[SendPayloadType, RecvPayloadType]):
    sent: int = 0
    received: int = 0
    
    ############### Sending ###############
    def request_data_multiple(self, data: typing.Iterable[SendPayloadType]) -> None:
        '''Blocking send of multiple data to pipe.'''
        for d in data:
            self.request_data(d)

    def request_data(self, data: SendPayloadType) -> None:
        '''Blocking send of data to pipe.'''
        self.pipe.send(SubmitData(data))
        self.sent += 1        
    
    def request_close(self) -> None:
        '''Blocking send of close message to pipe.'''
        return self.pipe.send(Close())
    
    
    ############### receiving ###############
    def receive_remaining(self) -> typing.Generator[RecvPayloadType]:
        '''Blocking receive of all data from pipe in a generator.'''
        while self.remaining() > 0:
            yield self.receive_data()
    
    def remaining(self) -> int:
        return self.sent - self.received
    
    def receive_data(self) -> RecvPayloadType:
        '''Blocking receive of data from pipe.'''
        try:
            msg: MessageFromProcess = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            raise BrokenPipeError(f'Tried to receive data when pipe was broken.')

        # handle message in different ways
        if msg.mtype is MessageFromProcessType.REPLY_DATA:
            self.received += 1
            return msg.payload
        elif msg.mtype is MessageFromProcessType.USERFUNC_ERROR:
            raise msg.exception
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')


@dataclasses.dataclass
class ProcessMessenger(BaseMessenger, typing.Generic[SendPayloadType, RecvPayloadType]):
    def reply_data(self, data: SendPayloadType):
        '''Blocking send of data to pipe.'''
        self.pipe.send(ReplyData(data))
        
    def reply_error(self, exception: BaseException):
        '''Blocking send of close message to pipe.'''
        self.pipe.send(UserfuncError(exception))
        
    def receive_data(self) -> RecvPayloadType:
        '''Blocking receive of data from pipe.'''
        try:
            msg: MessageToProcess = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            raise BrokenPipeError(f'Tried to receive data when pipe was broken.')
        
        if msg.mtype is MessageToProcessType.SUBMIT_DATA:
            return msg.payload
        
        elif msg.mtype is MessageToProcessType.CLOSE:
            raise ResourceRequestedClose(f'The worker resource requested that this thread close.')
        
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')
        
        
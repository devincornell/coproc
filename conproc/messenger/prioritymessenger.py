from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import queue
import traceback 

from .messages import SendPayloadType, RecvPayloadType, Message, MessageType, DataMessage, EncounteredErrorMessage, CloseRequestMessage
from .exceptions import ResourceRequestedClose, MessageNotRecognizedError
from .priorityqueue import PriorityQueue

import collections

@dataclasses.dataclass
class PriorityMessenger(typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Handles messaging to/from a multiprocessing pipe.'''
    pipe: multiprocessing.connection.Connection
    queue: PriorityQueue[Message] = dataclasses.field(default_factory=PriorityQueue)
    sent_requests: int = 0
    received_replies: int = 0
    
    @classmethod
    def new(cls, pipe: multiprocessing.connection.Connection, **kwargs) -> PriorityMessenger:
        '''Return new messenger with new pipe.'''
        return cls(pipe=pipe, **kwargs)
    
    @classmethod
    def make_pair(cls, **kwargs) -> typing.Tuple[PriorityMessenger, PriorityMessenger]:
        '''Return (process, resource) pair of messengers'''
        resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
        return (
            cls(pipe=process_pipe, **kwargs),
            cls(pipe=resource_pipe, **kwargs),
        )

    ############### Request/reply interface ###############
    def send_request_multiple(self, data: typing.Iterable[SendPayloadType]) -> None:
        '''Blocking send of multiple data to pipe.'''
        for d in data:
            self.send_request(d)

    def send_request(self, data: SendPayloadType) -> None:
        '''Send data that does require replies.'''
        self._send_message(DataMessage(data, request_reply=True, is_reply=False))
        self.sent_requests += 1
        
    def send_reply(self, data: RecvPayloadType) -> None:
        '''Send data that acts as a reply to a request.'''
        self._send_message(DataMessage(data, request_reply=False, is_reply=True))
    
    ############### Sending ###############
    def send_data_noreply(self, data: SendPayloadType) -> None:
        '''Send data that does not requre a reply.'''
        self._send_message(DataMessage(data, request_reply=False, is_reply=False))
        
    def send_close_request(self) -> None:
        '''Blocking send of close message to pipe.'''
        return self._send_message(CloseRequestMessage())
    
    def send_error(self, exception: BaseException, print_trace: bool = True):
        '''Blocking send of close message to pipe.'''
        #if print_trace:
        traceback.print_exc() # it'd be better to do this on receive side
        self._send_message(EncounteredErrorMessage(exception))
        
    def _send_message(self, msg: Message) -> None:
        return self.pipe.send(msg)
    
    ############### receive methods ###############
    def receive_remaining(self) -> typing.Generator[RecvPayloadType]:
        '''Receive until the requested number of results have been received.'''
        while self.remaining() > 0:
            yield self.receive_data()
            
    def receive_available(self) -> typing.List[RecvPayloadType]:
        '''Receive all results that this process has received as of now.'''
        datas = list()
        while self.available():
            datas.append(self.receive_data())
        return datas
    
    def receive_data(self, blocking: bool = True) -> RecvPayloadType:
        '''Blocking receive of data from pipe.'''
        return self._receive_message(blocking=blocking).payload
        
    def _receive_message(self, blocking: bool = True) -> DataMessage:
        '''Return next data object from the pipe, handling other messages before.'''
        msg: Message = self._receive_message_raw(blocking=blocking)
        
        # handle message in different ways
        if msg.mtype is MessageType.DATA_PAYLOAD:
            msg: DataMessage
            if msg.is_reply:
                self.received_replies += 1
            return msg
        elif msg.mtype is MessageType.ENCOUNTERED_ERROR:
            msg: EncounteredErrorMessage
            ex = msg.exception
            raise msg.exception
        elif msg.mtype is MessageType.CLOSE_REQUEST:
            msg: CloseRequestMessage
            raise ResourceRequestedClose(f'Resource requested that this process close.')
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')

    def _receive_message_raw(self, blocking: bool = True) -> Message:
        '''Blocking receive of data from pipe to queue and return next item.'''
        while self.pipe.poll() or (self.queue.empty() and blocking):
            msg: Message = self._pipe_recv()
            self.queue.put(msg, msg.priority)
            blocking = False
        return self.queue.get()

    def _pipe_recv(self) -> Message:
        '''Receive data from pipe.'''
        try:
            return self.pipe.recv()
        except (EOFError, BrokenPipeError):
            raise BrokenPipeError(f'Tried to receive data when pipe was broken.')

    ############### Check on pipe, queue, and send/receive counts ###############
    def available(self) -> bool:
        '''Check if data is in the pipe or queue.'''
        return self.pipe.poll() or not self.queue.empty()
    
    def remaining(self) -> int:
        '''Number of results requested but not received.'''
        return self.sent_requests - self.received_replies
    
    def queue_size(self) -> int:
        '''Current size of queue.
        NOTE: NOT remaining messsages to process. Can't tell 
        '''
        return self.queue.size()
    
    def pipe_poll(self) -> bool:
        return self.pipe.poll()




from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import queue
import traceback 

from .messages import SendPayloadType, RecvPayloadType, Message, MessageType, DataMessage, EncounteredErrorMessage, CloseRequestMessage
from .exceptions import ResourceRequestedClose, MessageNotRecognizedError
#from .priorityqueue import PriorityQueue
from .prioritymultiqueue import PriorityMultiQueue, ChannelID

import collections

import enum
class ChannelNotSetSentinel(enum.Enum):
    CHANNEL_NOT_SET = enum.auto()

CHANNEL_NOT_SET = ChannelNotSetSentinel.CHANNEL_NOT_SET
'''Used as default for channel parameter.'''

@dataclasses.dataclass
class RequestCtr:
    requests: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    replies: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    
    def remaining(self, channel_id: ChannelID) -> int:
        return self.requests[channel_id] - self.replies[channel_id]
    
    def sent_request(self, channel_id: ChannelID):
        self.requests[channel_id] += 1
        
    def received_reply(self, channel_id: ChannelID):
        self.replies[channel_id] += 1
    

@dataclasses.dataclass
class PriorityMessenger(typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Handles messaging to/from a multiprocessing pipe with prioritization and message channels.'''
    pipe: multiprocessing.connection.Connection
    queue: PriorityMultiQueue[Message] = dataclasses.field(default_factory=PriorityMultiQueue)
    request_ctr: RequestCtr = dataclasses.field(default_factory=RequestCtr)
        
    @classmethod
    def new_pair(cls, **kwargs) -> typing.Tuple[PriorityMessenger, PriorityMessenger]:
        '''Return (process, resource) pair of messengers connected by a duplex pipe.'''
        resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
        return (
            cls(pipe=process_pipe, **kwargs),
            cls(pipe=resource_pipe, **kwargs),
        )

    ############### Request/reply interface ###############
    def send_request_multiple(self, data: typing.Iterable[SendPayloadType], channel_id: ChannelID = None) -> None:
        '''Blocking send of multiple data to pipe.'''
        for d in data:
            self.send_request(d, channel_id=channel_id)
        
    def send_request(self, data: SendPayloadType, channel_id: ChannelID = None) -> None:
        '''Send data that requires a reply.'''
        self.send_data_message(data, request_reply=True, is_reply=False, channel_id=channel_id)
        
    def send_reply(self, data: RecvPayloadType, channel_id: ChannelID = None) -> None:
        '''Send data that acts as a reply to a request.'''
        self.send_data_message(data, request_reply=False, is_reply=True, channel_id=channel_id)
    
    def send_norequest(self, data: SendPayloadType, channel_id: ChannelID = None) -> None:
        '''Send data that does not requre a reply.'''
        self.send_data_message(data, request_reply=False, is_reply=False, channel_id=channel_id)
    
    ############### Sending various message types ###############
    def send_data_message(self, payload: SendPayloadType, request_reply: bool, is_reply: bool, channel_id: ChannelID = None) -> None:
        '''Send data message.'''
        if request_reply:
            self.request_ctr.sent_request(channel_id)
        self._send_message(DataMessage(payload=payload, request_reply=request_reply, is_reply=is_reply, channel_id=channel_id))
        
    def send_close_request(self) -> None:
        '''Blocking send of close message to pipe.'''
        return self._send_message(CloseRequestMessage())
    
    def send_error(self, exception: BaseException, print_trace: bool = True):
        '''Blocking send of close message to pipe.'''
        traceback.print_exc() # it'd be better to do this on receive side, but idk
        self._send_message(EncounteredErrorMessage(exception))
        
    def _send_message(self, msg: Message) -> None:
        return self.pipe.send(msg)
                
    #################### Receive all messages we are waiting on ####################
    def receive_remaining(self, channel_id: ChannelID = None) -> typing.Generator[RecvPayloadType]:
        '''Receive until the requested number of results have been received.'''
        for m in self.receive_messages_remaining(channel_id=channel_id):
            yield m.payload
            
    def receive_messages_remaining(self, channel_id: ChannelID = None) -> typing.Generator[DataMessage]:
        while self.remaining(channel_id) > 0:
            yield self.receive_message_blocking(channel_id=channel_id)
    
    #################### Wait until we receive the next relevant message ####################
    def receive_blocking(self, channel_id: ChannelID = None) -> RecvPayloadType:
        '''Blocking receive payload from next data message of this channel.'''
        return self.receive_message_blocking(channel_id=channel_id).payload
    
    def receive_message_blocking(self, channel_id: ChannelID = None) -> DataMessage:
        '''Receive until receiving a message with the given channel, then return it.'''
        while self.pipe.poll() or self.queue.empty(channel_id=channel_id):
            msg: Message = self._pipe_recv()
            self._handle_message(msg)
        return self.pop_from_queue(channel_id=channel_id)
    
    #################### Asynchronous availability methods ####################
    def receive_available(self, channel_id: ChannelID = None) -> typing.List[RecvPayloadType]:
        '''Receive currently available messanges.'''
        return [m.payload for m in self.receive_available_messages(channel_id=channel_id)]
        
    def receive_available_messages(self, channel_id: ChannelID = None) -> typing.List[DataMessage]:
        available = list()
        while self.available(channel_id=channel_id):
            available.append(self.pop_from_queue(channel_id=channel_id))
        return available
    
    def available(self, channel_id: ChannelID = None) -> int:
        '''Number of data available in pipe at this time.'''
        self._receive_and_handle_available_messages()
        return self.queue.size(channel_id=channel_id)
    
    def pop_from_queue(self, channel_id: ChannelID = None) -> RecvPayloadType:
        '''Pop the next item from the queue.'''
        msg = self.queue.get(channel_id=channel_id)
        if msg.is_reply:
            self.request_ctr.received_reply(msg.channel_id)
        return msg
    
    #################### Low-level message handling ####################
    def _receive_and_handle_available_messages(self) -> None:
        '''Receive all data from pipe and place into queue.'''
        while self.pipe.poll():
            msg: Message = self._pipe_recv()
            self._handle_message(msg)
        
    def _handle_message(self, msg: Message):
        '''Take appropriate action for message type. If data, add to queue.'''
        if msg.mtype is MessageType.DATA_PAYLOAD:
            self.queue.put(msg, msg.priority, msg.channel_id)
            
        elif msg.mtype is MessageType.ENCOUNTERED_ERROR:
            ex = msg.exception
            # NOTE: print exception stack trace here instead of send side in the future
            raise msg.exception
        
        elif msg.mtype is MessageType.CLOSE_REQUEST:
            msg: CloseRequestMessage
            raise ResourceRequestedClose(f'Resource requested that this process close.')
        else:
            raise MessageNotRecognizedError(f'Message of type {msg.mtype} not recognized.')

    def _pipe_recv(self) -> Message:
        '''Receive data from pipe.'''
        try:
            return self.pipe.recv()
        except (EOFError, BrokenPipeError):
            raise BrokenPipeError(f'Tried to receive data when pipe was broken.')

    ############### Check on pipe, queue, and send/receive counts ###############    
    def remaining(self, channel_id: ChannelID = None) -> int:
        '''Number of results requested but not received.'''
        return self.request_ctr.remaining(channel_id)
    
    def queue_size(self, channel_id: ChannelID = None) -> int:
        '''Current size of queue.'''
        return self.queue.size(channel_id=channel_id)
    
    def pipe_poll(self) -> bool:
        '''Check if any items are in the pipe.'''
        return self.pipe.poll()




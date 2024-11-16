from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import queue
import traceback 

from .messages import SendPayloadType, RecvPayloadType, Message, MessageType, DataMessage, EncounteredErrorMessage, CloseRequestMessage
from .exceptions import ResourceRequestedClose, MessageNotRecognizedError
from .queue import PriorityMultiQueue, ChannelID
from .multimessenger import MultiMessenger

import collections



@dataclasses.dataclass
class PriorityMessenger(MultiMessenger, typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Handles messaging to/from a multiprocessing pipe with prioritization and message channels.'''
    queue: PriorityMultiQueue[Message] = dataclasses.field(default_factory=PriorityMultiQueue)
        
    ############################ utilities ############################
    @classmethod
    def new_pair(cls, **kwargs) -> typing.Tuple[PriorityMessenger, PriorityMessenger]:
        '''Return (process, resource) pair of messengers connected by a duplex pipe.'''
        resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
        return (
            cls(pipe=process_pipe, **kwargs),
            cls(pipe=resource_pipe, **kwargs),
        )

    ############################ Sending messages ############################
    def send_request_multiple(self, data: typing.Iterable[SendPayloadType], channel_id: ChannelID = None, priority: float = float('inf')) -> None:
        '''Blocking send of multiple data to pipe.'''
        for d in data:
            self.send_request(d, channel_id=channel_id, priority=priority)
        
    def send_request(self, data: SendPayloadType, channel_id: ChannelID = None, priority: float = float('inf')) -> None:
        '''Send data that requires a reply.'''
        self.send_data_message(data, request_reply=True, is_reply=False, channel_id=channel_id, priority=priority)
        
    def send_reply(self, data: SendPayloadType, channel_id: ChannelID = None, priority: float = float('inf')) -> None:
        '''Send data that acts as a reply to a request.'''
        self.send_data_message(data, request_reply=False, is_reply=True, channel_id=channel_id, priority=priority)
    
    def send_norequest(self, data: SendPayloadType, channel_id: ChannelID = None, priority: float = float('inf')) -> None:
        '''Send data that does not requre a reply.'''
        self.send_data_message(data, request_reply=False, is_reply=False, channel_id=channel_id, priority=priority)


    ############################ Receiving messages ############################
    def _queue_put(self, msg: Message) -> None:
        '''Put message into queue.'''
        self.queue.put(msg, msg.priority, msg.channel_id)


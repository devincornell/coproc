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
        
    @classmethod
    def new_pair(cls, **kwargs) -> typing.Tuple[PriorityMessenger, PriorityMessenger]:
        '''Return (process, resource) pair of messengers connected by a duplex pipe.'''
        resource_pipe, process_pipe = multiprocessing.Pipe(duplex=True, **kwargs)
        return (
            cls(pipe=process_pipe, **kwargs),
            cls(pipe=resource_pipe, **kwargs),
        )

    def _queue_put(self, msg: Message) -> None:
        '''Put message into queue.'''
        self.queue.put(msg, msg.priority, msg.channel_id)


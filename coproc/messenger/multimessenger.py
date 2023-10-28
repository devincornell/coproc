from __future__ import annotations
import dataclasses
import typing
import multiprocessing

from .prioritymessenger import PriorityMessenger
from .queue import MultiQueue, PriorityMultiQueue
from .messages import Message

@dataclasses.dataclass
class MultiMessenger(PriorityMessenger):
    '''Follows PriorityMessenger but does not use priority.
        Importantly, this precludes the possibility of 
    '''
    queue: MultiQueue[Message] = dataclasses.field(default_factory=MultiQueue)
    
    @classmethod
    def new_pair(cls, **kwargs) -> typing.Tuple[MultiMessenger, MultiMessenger]:
        '''Return (process, resource) pair of messengers connected by a duplex pipe.'''
        return super().new_pair(**kwargs)
    
    def _queue_put(self, msg: Message) -> None:
        '''Put message into queue. Does not include priority.'''
        self.queue.put(msg, msg.channel_id)

    
    
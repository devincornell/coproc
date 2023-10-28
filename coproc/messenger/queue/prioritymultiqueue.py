import typing
import dataclasses
import collections

from .priorityqueue import PriorityQueue, ItemType
from .multiqueue import MultiQueue, ChannelID

@dataclasses.dataclass
class PriorityMultiQueue(MultiQueue, typing.Generic[ItemType]):
    '''Wraps multiple queues that each handle separate channels.'''
    queues: typing.Dict[typing.Hashable, PriorityQueue[ItemType]] = dataclasses.field(default_factory=dict)
    
    ############## Basic Put/Get ##############    
    def put(self, item: ItemType, priority: float, channel_id: ChannelID):
        '''Put a new item on the queue.'''
        self.queues.setdefault(channel_id, PriorityQueue())
        return self[channel_id].put(item, priority)
            

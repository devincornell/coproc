import typing
import dataclasses
import collections

from .priorityqueue import PriorityQueue, ItemType

@dataclasses.dataclass
class PriorityMultiQueue(typing.Generic[ItemType]):
    '''Wraps multiple queues that each handle separate channels.'''
    pqueues: typing.Dict[typing.Hashable, PriorityQueue[ItemType]] = dataclasses.field(default_factory=dict)
    
    ############## Basic Put/Get ##############
    def get(self, channel_id: int) -> ItemType:
        '''Get the next item from the queue.'''
        try:
            return self[channel_id].get()
        except KeyError as e:
            raise IndexError('Cannot pop from empty queue') from e
    
    def put(self, item: ItemType, priority: float, channel_id: int):
        '''Put a new item on the queue.'''
        self.pqueues.setdefault(channel_id, PriorityQueue())
        return self[channel_id].put(item, priority)
        
    ############## check size and whether empty ##############
    def empty(self, channel_id: int) -> bool:
        return channel_id not in self.pqueues or self[channel_id].empty()
    
    def size(self, channel_id: int) -> int:
        try:
            return self[channel_id].size()
        except KeyError as e:
            return 0
    
    ############## dunder ##############
    def __getitem__(self, channel_id: int) -> PriorityQueue[ItemType]:
        '''Get corresponding piority queue.'''
        return self.pqueues[channel_id]
        
    def __contains__(self, channel_id: int) -> bool:
        '''Check if the channel currently exists in the dict.'''
        return channel_id in self.pqueues

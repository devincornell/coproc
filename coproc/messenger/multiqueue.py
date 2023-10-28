import dataclasses
import collections
import typing

from .messages import Message
#from .prioritymessenger import PriorityMessenger, ChannelID
from .prioritymultiqueue import PriorityMultiQueue, ChannelID

ItemType = typing.TypeVar('ItemType')

@dataclasses.dataclass
class BasicQueue(typing.Generic[ItemType]):
    '''Wrapper for collections.dequeue'''
    queue: collections.deque[ItemType] = dataclasses.field(default_factory=collections.deque)
    
    def get(self) -> ItemType:
        # NOTE: need to benchmark popleft vs appendleft
        return self.queue.popleft()
    
    def put(self, item: ItemType):
        self.queue.append(item)
        
    def empty(self) -> bool:
        return len(self.queue) == 0
    
    def size(self) -> int:
        return len(self.queue)

@dataclasses.dataclass
class MultiQueue(PriorityMultiQueue, typing.Generic[ItemType]):
    '''Similar to priority messenger, but does not include priority.'''
    queues: typing.Dict[typing.Hashable, BasicQueue[ItemType]] = dataclasses.field(default_factory=dict)
    
    ############## Basic Put/Get ##############
    def get(self, channel_id: ChannelID) -> ItemType:
        '''Get the next item from the queue.'''
        try:
            return self[channel_id].get()
        except KeyError as e:
            raise IndexError('Cannot pop from empty queue') from e
    
    def put(self, item: ItemType, channel_id: ChannelID):
        '''Put a new item on the queue.'''
        self.queues.setdefault(channel_id, BasicQueue())
        return self[channel_id].put(item)
        
    ############## check size and whether empty ##############
    def empty(self, channel_id: ChannelID) -> bool:
        return channel_id not in self.queues or self[channel_id].empty()
    
    def size(self, channel_id: ChannelID) -> int:
        try:
            return self[channel_id].size()
        except KeyError as e:
            return 0
    
    ############## dunder ##############
    def __getitem__(self, channel_id: ChannelID) -> BasicQueue[ItemType]:
        '''Get corresponding piority queue.'''
        return self.queues[channel_id]
        
    def __contains__(self, channel_id: ChannelID) -> bool:
        '''Check if the channel currently exists in the dict.'''
        return channel_id in self.queues






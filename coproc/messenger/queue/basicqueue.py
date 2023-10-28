
import collections
import typing
import dataclasses

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
    
    
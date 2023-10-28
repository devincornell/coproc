import typing
import dataclasses
import collections

ItemType = typing.TypeVar('ItemType')

@dataclasses.dataclass
class PriorityQueue(typing.Generic[ItemType]):
    queues: typing.Dict[float, collections.deque[ItemType]] = dataclasses.field(default_factory=dict)
    current_priority: typing.Optional[float] = None
    ct: int = 0
    
    def put(self, item: ItemType, priority: float):
        # NOTE: adding a priority should be rare
        if priority not in self.queues:
            self.queues[priority] = collections.deque()
            self.queues = {k:v for k,v in sorted(self.queues.items(), key=lambda x: x[0])}
            
        self.queues[priority].appendleft(item)
        self.ct += 1
        
        # the queue will have at least one element
        if self.current_priority is None or priority < self.current_priority:
            self.current_priority = priority
        
    def get(self) -> ItemType:
        '''Get next item in queue. Raises IndexError if empty.'''
        if self.current_priority is None:
            raise IndexError('Cannot pop from empty queue')
        cq = self.current_queue
        v = cq.pop()
        self.ct -= 1
        
        if not len(cq):
            self.current_priority = self._get_lowest_priority()
        
        return v
    
    @property
    def current_queue(self) -> collections.deque:
        try:
            return self.queues[self.current_priority]
        except KeyError as e:
            raise IndexError('Cannot pop from empty queue') from e
        
    def _get_lowest_priority(self) -> typing.Optional[float]:
        '''Get the lowest priority queue that has items.'''
        for p,q in self.queues.items():
            if len(q):
                return p
        return None
    
    def empty(self) -> bool:
        return self.ct == 0
            
    def size(self) -> int:
        return self.ct
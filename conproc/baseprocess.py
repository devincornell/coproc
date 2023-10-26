import dataclasses

from .messenger import PriorityMessenger

@dataclasses.dataclass
class BaseProcess:
    '''Base class with constructor that accepts a priority messenger.
        You may use this when creating minimal process functions.
    '''
    messenger: PriorityMessenger



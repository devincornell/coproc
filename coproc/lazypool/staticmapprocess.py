from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

from ..baseworkerprocess import BaseWorkerProcess
#from .messenger import PriorityMessenger
from ..messenger import ResourceRequestedClose, SendPayloadType, RecvPayloadType
#from .messenger import PriorityMessenger, MultiMessenger

@dataclasses.dataclass
class SliceMessage:
    ind: slice
    
@dataclasses.dataclass
class MapResultMessage:
    ind: slice
    results: SendPayloadType
    
    @property
    def start(self):
        return self.ind.start

@dataclasses.dataclass
class StaticMapProcess(BaseWorkerProcess, typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Stores items at init and receives slice messages .'''
    worker_target: typing.Callable[[SendPayloadType], RecvPayloadType]
    items: typing.List[SendPayloadType]
    verbose: bool = False
    
    def __call__(self):
        pid = multiprocessing.current_process().pid
        if self.verbose: print(f'starting {pid}')
        
        while True:
            try:
                slice_msg: SliceMessage = self.messenger.receive_blocking()
                if self.verbose: print(f'{pid} <<-- {slice_msg}')
            except ResourceRequestedClose:
                break
                
            try:
                # apply map func to each element
                results = list()
                for item in self.items[slice_msg.ind]:
                    results.append(self.worker_target(item))
                    
                # return results chunk
                self.messenger.send_reply(MapResultMessage(slice_msg.ind, results))
                if self.verbose: print(f'{pid} -->> {results}')
                                        
            except BaseException as e:
                self.messenger.send_error(e)
                if self.verbose: print(f'{pid} -->> {type(e)}')



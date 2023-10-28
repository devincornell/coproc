
from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

#from .baseworkerprocess import BaseWorkerProcess
#from .messenger import PriorityMessenger
#from .messenger import ResourceRequestedClose, DataMessage, SendPayloadType, RecvPayloadType, PriorityMessenger
from .messenger import PriorityMessenger, MultiMessenger
from .workerresource import WorkerResource
from .mapworker import MapWorkerProcess, MapDataMessage, UpdateUserFuncMessage, SendPayloadType, RecvPayloadType

class OldPool:
    def __init__(self, n: int, verbose: bool = False, messenger_type: typing.Type[PriorityMessenger] = PriorityMessenger):
        self.workers = list()
        for _ in range(n):
            w = WorkerResource(
                worker_process_type = MapWorkerProcess,
                messenger_type=messenger_type,
            )
            self.workers.append(w)
        
        self.start_kwargs = {
            'verbose': verbose,
        }
        
    def __enter__(self) -> Pool:
        self.start()
        return self
    
    def __exit__(self, *args):
        self.terminate(check_alive=False)
            
    def __iter__(self):
        return iter(self.workers)
    
    ################### Mapping ###################
    def map(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.List[SendPayloadType]) -> typing.Iterable[RecvPayloadType]:
        '''Get results in order as a list.'''
        return [m.payload for m in sorted(self._map_messages(func, datas), key=lambda m: m.order)]
    
    def map_unordered(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.Iterable[SendPayloadType]) -> typing.Iterable[RecvPayloadType]:
        '''Return results as they become available.'''
        return (m.payload for m in self._map_messages(func, datas))
    
    def _map_messages(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.Iterable[SendPayloadType]) -> typing.Generator[MapDataMessage]:
        '''Most general map function - returns unordered list of result messages.'''
        self.update_user_func(func)
        
        # get remaining data to submit
        data_iter = enumerate(datas)
        remaining_to_send = 0
        
        # send initial data to get process started
        #print('send initial')
        for w in self.workers:
            i, d = next(data_iter)
            #print('initial_sending:', d)
            w.messenger.send_request(MapDataMessage(d, i))
        
        # keep feeding until there is no more data to feed
        #print('feeder loop')
        finished = False
        while not finished:
            for w in self.workers:
                for m in w.messenger.receive_available():
                    try:
                        i, d = next(data_iter)
                        w.messenger.send_request(MapDataMessage(d, i))
                        #print('subsequent_sending:', d)
                        yield m
                    except StopIteration:
                        finished = True
                        yield m
                        break
                
                if finished:
                    break
                            
        # receive all remaining messages
        #print('wait on remaining')
        for w in self:
            for m in w.messenger.receive_remaining():
                yield m
    
    def update_user_func(self, target: typing.Callable[[SendPayloadType], RecvPayloadType]):
        '''Update the user function that is called on each data message.'''
        self._apply_to_workers(lambda w: w.messenger.send_norequest(UpdateUserFuncMessage(target)))
    
    ################### Stopping and starting ###################
    def start(self, **kwargs):
        self._apply_to_workers(lambda w: w.start(**{**self.start_kwargs, **kwargs}))
    
    def join(self):
        self._apply_to_workers(lambda w: w.messenger.send_close_request())
        self._apply_to_workers(lambda w: w.join())
        
    def terminate(self, check_alive: bool = True):
        self._apply_to_workers(lambda w: w.terminate(check_alive=check_alive))

    ################### manipulating workers ###################
    def _apply_to_workers(self, func: typing.Callable[[WorkerResource]]):
        return [func(w) for w in self.workers]




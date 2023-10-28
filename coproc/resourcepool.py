
from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

#from .baseworkerprocess import BaseWorkerProcess
#from .messenger import PriorityMessenger
#from .messenger import ResourceRequestedClose, DataMessage, SendPayloadType, RecvPayloadType, PriorityMessenger
from .messenger import PriorityMessenger, MultiMessenger, ChannelID, SendPayloadType, RecvPayloadType
#from .workerresource import WorkerResource
#from .baseworkerprocess import BaseWorkerProcess
from .mapworker2 import MapWorkerProcess2, SliceMessage, MapResultMessage
from .workerresourcepool import WorkerResourcePool    


class Pool2(typing.Generic[SendPayloadType, RecvPayloadType]):
    def __init__(self, n: int, verbose: bool = False):
        self.pool = WorkerResourcePool.new(n, MapWorkerProcess2, MultiMessenger)
        self.start_kwargs = {
            'verbose': verbose,
        }
        
    def __enter__(self) -> ResourcePool:
        #self.start() #NOTE: instead, this should start when a map function is called
        return self
    
    def __exit__(self, *args):
        self.pool.terminate(check_alive=False)
            
    def __iter__(self):
        return iter(self.pool)
    
    ################### New Mapping ###################
    def map(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.List[SendPayloadType], chunksize: int = 1) -> typing.List[RecvPayloadType]:
        results_iter = self.map_unordered(func, datas, chunksize=chunksize)
    
    def map_unordered(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.List[SendPayloadType], chunksize: int = 1) -> typing.Generator[RecvPayloadType]:
        '''Get results in order as a list.'''
        map_results = list(self._map_base(func, datas, chunksize=chunksize))
        
        for mrm in self._map_messages(func, slices):
            for r in mrm.results:
                yield r
    
    def _map_base(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.List[SendPayloadType], chunksize: int = 1) -> typing.Generator[MapResultMessage]:
        self.pool.set_start_kwargs(
            worker_target=func, 
            items=datas, 
            **self.start_kwargs
        )
        slices = iter([SliceMessage(s) for s in self.chunk_size_slice(chunksize)])
        for mrm in self._map_messages(func, slices):
            yield mrm
    
    ################### Old Mapping ###################
    #def map(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.List[SendPayloadType]) -> typing.List[RecvPayloadType]:
    #    '''Get results in order as a list.'''
    #    return [m.payload for m in sorted(self._map_messages(func, datas), key=lambda m: m.order)]
    
    #def map_unordered(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.Iterable[SendPayloadType]) -> typing.Iterable[RecvPayloadType]:
    #    '''Return results as they become available.'''
    #    self.update_user_func(func)
    #    data_iter = enumerate(datas)
    #    return (m.payload for m in self._map_messages(func, datas))
    
    #def _map_messages(self, func: typing.Callable[[SendPayloadType], RecvPayloadType], datas: typing.Iterable[SendPayloadType]) -> typing.Generator[MapDataMessage]:
    #    '''Most general map function - returns unordered list of result messages.'''
    #    data_iter = enumerate(datas)
    #    self._map_messages
        
    #def update_user_func(self, target: typing.Callable[[SendPayloadType], RecvPayloadType]):
    #    '''Update the user function that is called on each data message.'''
    #    self._apply_to_workers(lambda w: w.messenger.send_norequest(UpdateUserFuncMessage(target)))
    
    ################### Stopping and starting ###################
    #@staticmethod
    #def chunk(elements: Iterable, /, chunk_size: int = None, num_chunks: int = None) -> List[Iterable]:
    #    '''Break elements into chunks determined by chunk_kwargs sent to .chunk_slice().
    #    '''
    #    slices = chunk_slice(len(elements), chunk_size=chunk_size, num_chunks=num_chunks)
    #    return [elements[s] for s in slices]

    @staticmethod
    def chunk_size_slice(chunk_size: int) -> List[Iterable]:
        '''Break elements into chunks of size chunk_size.
        '''
        num_chunks = n // chunk_size + (1 if (n % chunk_size) > 0 else 0)
        return return [slice(*slice(i*chunk_size, (i+1)*chunk_size).indices(n)) for i in range(num_chunks)]
    
    @staticmethod
    def num_chunk_slice(num_chunks: int) -> List[Iterable]:
        '''Break elements into num_chunks chunks.
        '''
        chunk_size = n // num_chunks + (1 if (n % num_chunks) > 0 else 0)
        return return [slice(*slice(i*chunk_size, (i+1)*chunk_size).indices(n)) for i in range(num_chunks)]

    @staticmethod
    def chunk_slice_depric(n: int, /, chunk_size: int = None, num_chunks: int = None) -> List[slice]:
        '''Create slices for chunks of an array of size n.
            NOTE: Now split into two methods
        '''
        if (chunk_size is None and num_chunks is None) or \
            (chunk_size is not None and num_chunks is not None):
            raise ValueError('Exactly one of chunk_size or num_chunks should be specified.')

        # determine number of chunks
        if chunk_size is not None:
            num_chunks = n // chunk_size + (1 if (n % chunk_size) > 0 else 0)
        
        # determine chunk size
        elif num_chunks is not None:
            chunk_size = n // num_chunks + (1 if (n % num_chunks) > 0 else 0)
        
        return [slice(*slice(i*chunk_size, (i+1)*chunk_size).indices(n)) for i in range(num_chunks)]


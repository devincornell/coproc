
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
from .mapworker import MapWorkerProcess, SliceMessage, MapResultMessage
from .workerresourcepool import WorkerResourcePool    


class Pool(typing.Generic[SendPayloadType, RecvPayloadType]):
    def __init__(self, n: int, verbose: bool = False):
        self.pool = WorkerResourcePool.new(n, MapWorkerProcess, MultiMessenger)
        self.start_kwargs = {
            'verbose': verbose,
        }
        
    def __enter__(self) -> Pool:
        #self.start() #NOTE: instead, this should start when a map function is called
        return self
    
    def __exit__(self, *args):
        #self.pool.terminate(check_alive=False)
        pass
            
    def __iter__(self):
        return iter(self.pool)
    
    ################### New Mapping ###################
    def map(self, 
        func: typing.Callable[[SendPayloadType], RecvPayloadType], 
        datas: typing.List[SendPayloadType], 
        chunksize: int = 1
    ) -> typing.List[RecvPayloadType]:
        return [r for m in sorted(self.map_unordered(func, datas, chunksize=chunksize)) for m in m.results]
    
    def map_unordered(self, 
        func: typing.Callable[[SendPayloadType], RecvPayloadType], 
        datas: typing.List[SendPayloadType], 
        chunksize: int = 1,
        channel_id: ChannelID = None,
    ) -> typing.Generator[RecvPayloadType]:
        '''Get results in order as a list.'''
        map_results = list(self._map_base(func, datas, chunksize=chunksize))
        
        for mrm in self._map_base(func, slices, chunksize=chunksize, channel_id=channel_id):
            for r in mrm.results:
                yield r
    
    def _map_base(self, 
        func: typing.Callable[[SendPayloadType], RecvPayloadType], 
        datas: typing.List[SendPayloadType], 
        chunksize: int = 1,
        channel_id: ChannelID = None,
    ) -> typing.Generator[MapResultMessage]:
        '''Initialize worker targets, create data slices, and '''
        self.pool.set_start_kwargs(
            worker_target=func, 
            items=datas, 
            **self.start_kwargs
        )
        slices = iter([SliceMessage(s) for s in self.chunk_size_slice(len(datas), chunksize)])
        with self.pool as pool:
            for mrm in pool._map_messages(func, slices, channel_id=channel_id):
                yield mrm
    
    @staticmethod
    def chunk_size_slice(n: int, chunk_size: int) -> typing.List[Iterable]:
        '''Break elements into chunks of size chunk_size.
        '''
        num_chunks = n // chunk_size + (1 if (n % chunk_size) > 0 else 0)
        return [slice(*slice(i*chunk_size, (i+1)*chunk_size).indices(n)) for i in range(num_chunks)]
    

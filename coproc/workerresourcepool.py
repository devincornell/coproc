from __future__ import annotations
import typing
import dataclasses

from .legacy_worker_resource import LegacyWorkerResource, BaseWorkerProcess
from .messenger import PriorityMessenger, SendPayloadType, RecvPayloadType, ChannelID


@dataclasses.dataclass
class WorkerResourcePool:
    workers: typing.List[LegacyWorkerResource]
    start_kwargs: typing.Dict[str, typing.Any]
    
    @classmethod
    def new(cls, 
        n: int, 
        worker_process_type: typing.Type[BaseWorkerProcess], 
        messenger_type: typing.Type[PriorityMessenger], 
        **start_kwargs: typing.Dict[str, typing.Any]
    ) -> WorkerResourcePool:
        '''Create new workerResources and track start kwargs.'''
        workers = list()
        for _ in range(n):
            workers.append(LegacyWorkerResource(
                worker_process_type = worker_process_type,
                messenger_type = messenger_type,
            ))
        return cls(workers, start_kwargs)
    
    
    ################### dunder ###################
    def __enter__(self):
        self.start(**self.start_kwargs)
        return self

    def __exit__(self, *args):
        self.terminate(check_alive=False)
        
    def __iter__(self):
        return iter(self.workers)
    
    ################### set attribtues ###################
    def set_start_kwargs(self, **kwargs):
        '''Change process start kwargs after constructing.'''
        self.start_kwargs = kwargs
    
    ################### Stopping and starting ###################
    def start(self, **kwargs):
        self.apply_to_workers(lambda w: w.start(**{**self.start_kwargs, **kwargs}))
    
    def join(self):
        self.apply_to_workers(lambda w: w.messenger.send_close_request())
        self.apply_to_workers(lambda w: w.join())
        
    def terminate(self, check_alive: bool = True):
        self.apply_to_workers(lambda w: w.terminate(check_alive=check_alive))
        
    def is_alive(self) -> bool:
        return all(self.apply_to_workers(lambda w: w.is_alive()))
    
    def wait_until_dead(self):
        '''Wait until all workers are dead.'''
        while self.is_alive():
            pass

    ################### manipulating workers ###################
    def apply_to_workers(self, func: typing.Callable[[LegacyWorkerResource], typing.Any]):
        return [func(w) for w in self.workers]
    
    ################### message sending/receiving ###################
    def map_messages(self, 
        data_iter: typing.Iterable[SendPayloadType],
        channel_id: ChannelID = None,
    ) -> typing.Generator[RecvPayloadType]:
        '''Feed data_iter to workers and receive results as soon as they are done.'''
        # send initial data to get process started
        #print('send initial')
        for w in self.workers:
            w.messenger.send_request(next(data_iter), channel_id=channel_id)
        
        # keep feeding until there is no more data to feed
        #print('feeder loop')
        finished = False
        while not finished:
            for w in self.workers:
                for m in w.messenger.receive_available(channel_id=channel_id):
                    try:
                        w.messenger.send_request(next(data_iter), channel_id=channel_id)
                        yield m
                    except StopIteration:
                        yield m
                        finished = True
                        break
                
                if finished:
                    break
                            
        # receive all remaining messages
        for w in self.workers:
            for m in w.messenger.receive_remaining(channel_id=channel_id):
                yield m

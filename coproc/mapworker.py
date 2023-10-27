from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

from .baseworkerprocess import BaseWorkerProcess
#from .messenger import PriorityMessenger
from .messenger import ResourceRequestedClose, DataMessage, SendPayloadType, RecvPayloadType, PriorityMessenger
from .workerresource import WorkerResource


class MapMessage:
    pass

@dataclasses.dataclass
class UpdateUserFuncMessage(MapMessage):
    '''Send generic data to the other end of the pipe, using priority of sent messsage.
    NOTE: this is designed to allow users to access benefits of user-defined queue.
    '''
    user_func: typing.Callable[[SendPayloadType], RecvPayloadType]
    priority: float = 0.0 # lower priority is more important
    
@dataclasses.dataclass(order=False)
class MapDataMessage(MapMessage):
    payload: SendPayloadType = dataclasses.field(compare=False)
    order: int = 0
    priority: float = 0.0

class WorkerTargetNotSetError(BaseException):
    pass

@dataclasses.dataclass
class MapWorkerProcess(BaseWorkerProcess, typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Simply receives data, processes it using worker_target, and sends the result back immediately.'''
    worker_target: typing.Callable[[SendPayloadType], RecvPayloadType] = None
    verbose: bool = False
    
    def __call__(self):
        pid = multiprocessing.current_process().pid
        
        if self.verbose: print(f'starting {pid}')
        
        while True:
            try:
                msg = self.messenger.receive_blocking()
                if self.verbose: print(f'{pid} <<-- {msg}')
            except ResourceRequestedClose:
                exit()
            
            if isinstance(msg, UpdateUserFuncMessage):
                self.worker_target = msg.user_func
                
            elif isinstance(msg, MapDataMessage):
                if self.worker_target is None:
                    ex = WorkerTargetNotSetError('worker target not set. send '
                        'UpdateUserFuncMessage first.')
                    self.messenger.send_error(ex)
                    
                try:
                    result = self.worker_target(msg.payload)
                    dm = MapDataMessage(result, order=msg.order, priority=msg.priority)
                    self.messenger.send_reply(dm)
                    if self.verbose: print(f'{pid} -->> {result}')
                                           
                except BaseException as e:
                    self.messenger.send_error(e)
                    if self.verbose: print(f'{pid} -->> {type(e)}')
                    
            else:
                raise NotImplementedError(f'unknown message type: {msg}')

@dataclasses.dataclass
class MapMessenger:
    messenger: PriorityMessenger
        
    def available(self) -> int:
        return self.messenger.available()
    
    def remaining(self) -> int:
        return self.messenger.remaining()
        
    def receive(self) -> RecvPayloadType:
        '''Receive a single data message.'''
        return self.messenger.receive_blocking().payload
        
    def send(self, data: SendPayloadType):
        '''Send a single data message.'''
        self.messenger.send_request(MapDataMessage(data))
        
    def update_user_func(self, target: typing.Callable):
        '''Update the user function that is called on each data message.'''
        self.messenger.send_norequest(UpdateUserFuncMessage(target))

class MapWorker:
    def __init__(self, verbose: bool = False):
        self.res = WorkerResource(
            worker_process_type = MapWorkerProcess,
        )
        self.start_kwargs = {
            'verbose': verbose,
        }
    def __enter__(self):
        self.res.start(**self.start_kwargs)
        return MapMessenger(self.res.messenger)
    
    def __exit__(self, *args):
        self.res.terminate(check_alive=False)



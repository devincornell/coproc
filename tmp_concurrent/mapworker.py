from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

from .workerprocess import BaseWorkerProcess, SendPayloadType, RecvPayloadType
#from .messenger import PriorityMessenger
from .messenger import ResourceRequestedClose, DataMessage
from .workerresource import WorkerResource
from .messenger import PriorityMessenger

# idk why
import enum
class MapMessageType(enum.Enum):
    DATA = enum.auto()
    UPDATE_USER_FUNC = enum.auto()
    
# kinda like an enum
DATA = 1
UPDATE_USER_FUNC = 2

@dataclasses.dataclass
class UpdateUserFuncMessage:
    '''Send generic data to the other end of the pipe, using priority of sent messsage.
    NOTE: this is designed to allow users to access benefits of user-defined queue.
    '''
    user_func: typing.Callable[[SendPayloadType], RecvPayloadType]
    priority: float = 0.0 # lower priority is more important
    mtype: MapMessageType = MapMessageType.UPDATE_USER_FUNC
    
@dataclasses.dataclass
class DataMessage:
    payload: SendPayloadType
    priority: float = 0.0
    mtype: MapMessageType = MapMessageType.DATA


class WorkerTargetNotSetError(BaseException):
    pass

@dataclasses.dataclass
class MapWorkerProcess(BaseWorkerProcess, typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Simply receives data, processes it using worker_target, and sends the result back immediately.'''
    worker_target: typing.Callable[[SendPayloadType], RecvPayloadType] = None
    messages_received: int = 0
    verbose: bool = False
    def __call__(self):
        '''Main event loop for the process.
        '''
        print(f'starting main loop')
        # main receive/send loop
        while True:
            try:
                msg = self.messenger.receive_data()
            except ResourceRequestedClose:
                exit()
            if self.verbose: print(f'recv [{self.messages_received}]-->>', msg)
            #if self.verbose: print(f'{self.worker_target=}, {msg.mtype}, {MapMessageType.UPDATE_USER_FUNC=}')
            self.messages_received += 1
            if msg.mtype is MapMessageType.UPDATE_USER_FUNC:
                self.worker_target = msg.user_func
                if self.verbose: print('updated map function: ', self.worker_target)
            else:
                if self.worker_target is None:
                    self.messenger.send_error(WorkerTargetNotSetError('worker target not set'))
                try:
                    result = self.worker_target(msg)
                    if self.verbose: print(f'send <<--', msg)
                    #if self.verbose: print(f'{self.__class__.__name__} sending reply: {result}')
                    self.messenger.send_reply(result)
                except Exception as e:
                    self.messenger.send_error(e)

@dataclasses.dataclass
class MapMessengerInterface:
    messenger: PriorityMessenger
        
    def apply_async(self, target: typing.Callable, data: typing.Iterable[typing.Any]) -> typing.List[typing.Any]:
        self.messenger.send_data_noreply(UpdateUserFuncMessage(target))
        self.messenger.request_multiple([DataMessage(d) for d in data])
        
    def receive(self) -> typing.Generator[RecvPayloadType]:
        for msg in self.messenger.receive_remaining():
            yield msg.payload

class MapWorker:
    def __init__(self):
        self.res = WorkerResource(
            worker_process_type = MapWorkerProcess,
        )
    def __enter__(self):
        self.res.start()
        return MapMessengerInterface(self.res.messenger)
    def __exit__(self, *args):
        #self.res.messenger.send_close_request()
        self.res.terminate(check_alive=False)


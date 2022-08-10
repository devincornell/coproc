import collections
import dataclasses
import gc
import multiprocessing
import os
from multiprocessing import Lock, Pipe, Pool, Process, Value
from typing import Any, Callable, Dict, Iterable, List, NewType, Tuple, Union

from .errors import *
from .messages import (MessageType, BaseMessage, DataPayloadMessage, SigCloseMessage, StatusRequestMessage)
from .workerstatus import WorkerStatus
from .workerprocess import WorkerProcess

@dataclasses.dataclass
class WorkerResource:
    '''Manages a worker process and pipe to it.'''
    target: Callable
    method: str = 'forkserver'
    gcollect: bool = False
    start_on_init: bool = False
    verbose: bool = False

    def __post_init__(self):
        ctx = multiprocessing.get_context(self.method)
        self.pipe, worker_pipe = Pipe(duplex=True)
        self.proc = ctx.Process(
            target=WorkerProcess(
                pipe = worker_pipe, 
                target = self.target, 
                gcollect = self.gcollect,
                verbose = self.verbose, 
            ), 
        )

        # start worker if requested
        if self.start_on_init:
            self.start()
    
    #def __repr__(self):
    #    return f'{self.__class__.__name__}(pid={self.pid}]'
    
    def __enter__(self):
        if not self.is_alive():
            self.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.join()
    
    def __del__(self):
        if self.verbose: print(f'{self}.__del__ was called!')
        self.terminate(check_alive=False)

    ############### Main interface methods ###############
    def poll(self) -> bool: 
        '''Check if worker sent anything.
        '''
        return self.pipe.poll()

    def execute(self, data: Any):
        '''Send data to worker and blocking return result upon reception.
        '''
        self.send_data(data)
        return self.recv_data()

    def recv_data(self) -> Any:
        '''Receive raw data from user function.'''
        return self.recv().data
    
    def send_data(self, data: Any, **kwargs) -> None:
        '''Send any data to worker process to be handled by user function.'''
        return self.send_payload(DataPayloadMessage(data, **kwargs))

    #def update_userfunc(self, func: Callable, *args, **kwargs):
    #    '''Send a new UserFunc to worker process.
    #    '''
    #    return self.send_payload(UserFunc(func, *args, **kwargs))

    def get_status(self) -> WorkerStatus:
        '''Blocking request status update from worker.
        '''
        self.send_payload(StatusRequestMessage())
        return self.recv()

    ############### Pipe interface ###############

    def send_payload(self, payload: BaseMessage) -> None:
        '''Send a Message (DataPayloadMessage or otherwise) to worker process.
        '''
        if not self.proc.is_alive():
            raise WorkerIsDeadError('.send_payload()', self.proc.pid)
        
        if self.verbose: print(f'{self} sending: {payload}')
        
        try:
            return self.pipe.send(payload)
        
        except BrokenPipeError:
            raise WorkerDiedError(self.proc.pid)

    def recv(self) -> DataPayloadMessage:
        '''Return received DataPayload or raise exception.
        '''
        try:
            payload = self.pipe.recv()
            if self.verbose: print(f'{self} received: {payload}')
        
        except (BrokenPipeError, EOFError, ConnectionResetError):
            if self.verbose: print('caught one of (BrokenPipeError, EOFError, ConnectionResetError)')
            raise WorkerDiedError(self.proc.pid)
        
        try:
            getattr(payload, 'mtype')
        except AttributeError:
            raise ResourceReceivedUnidentifiedMessage(f'Resource for worker {self.status.pid} received unidentified message: {payload}.')

        
        # handle incoming data
        #if isinstance(payload, DataPayload) or isinstance(payload, WorkerStatusMessage):
        if payload.mtype in (MessageType.DATA, MessageType.WORKER_STATUS):
            return payload

        #elif isinstance(payload, WorkerError):
        elif payload.mtype in (MessageType.USERFUNC_ERROR, MessageType.WORKER_ERROR):
            #self.terminate(check_alive=True)
            raise payload.exception
        
        else:
            raise ResourceReceivedUnidentifiedMessage(f'WorkerResource {self.pid} received unidentified message from process: {payload}')
    
    ############### Process interface ###############
    @property
    def pid(self):
        '''Get process id from worker.'''
        return self.proc.pid
    
    def is_alive(self, *arsg, **kwargs):
        '''Get status of process.'''
        return self.proc.is_alive(*arsg, **kwargs)
    
    def start(self):
        '''Start the process, throws WorkerIsAliveError if already alive.'''
        if self.proc.is_alive():
            raise WorkerIsAliveError(f'Worker {self.pid} cannot be started because it is already alive.')
        return self.proc.start()
    
    def join(self, check_alive=True):
        '''Send SigCloseMessage() to Worker and then wait for it to die.'''
        if check_alive and not self.proc.is_alive():
            raise WorkerIsDeadError(f'Worker {self.pid} cannot be joined because it is not alive.')
        try:
            self.pipe.send(SigCloseMessage())
        except BrokenPipeError:
            pass
        return self.proc.join()

    def terminate(self, check_alive=True):
        '''Send terminate signal to worker.'''
        if check_alive and not self.proc.is_alive():
            raise WorkerIsDeadError(f'Worker {self.pid} cannot be terminated because it is not alive.')
        #return self.proc.terminate()
        #try:
        #    self.pipe.send(SigCloseMessage())
        #except BrokenPipeError:
        #    pass
        
        try:
            return self.proc.terminate()
        except AttributeError as e:
            print('This WorkerResource has no process (proc attribute).')
            pass

#class WorkerPool(list):
#
#    ############### Worker Creation ###############
#    def is_alive(self): 
#        return len(self) > 0 and all([w.is_alive() for w in self])
#    
#    def start(self, num_workers: int, *args, func: Callable = None, **kwargs):
#        if self.is_alive():
#            raise ValueError('This WorkerPool already has running workers.')
#        
#        # start each worker
#        for ind in range(num_workers):
#            self.append(WorkerResource(ind, *args, func=func, **kwargs))
#        
#        return self
#
#    def update_userfunc(self, userfunc: Callable):
#        return [w.update_userfunc(userfunc) for w in self]
#
#    ############### Low-Level Process Operations ###############
#    def join(self):
#        [w.join() for w in self]
#        self.clear()
#    
#    def terminate(self): 
#        [w.terminate() for w in self]
#        self.clear()




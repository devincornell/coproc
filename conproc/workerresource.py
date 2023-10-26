from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

from .baseworkerprocess import BaseWorkerProcess
from .messenger import PriorityMessenger, SendPayloadType, RecvPayloadType

class WorkerIsAlreadyAliveError(BaseException):
    '''Used when trying to start a worker that is already alive.'''

class WorkerIsAlreadyDeadError(BaseException):
    '''Used when trying to stop a worker that is already stopped.'''

class WorkerIsDeadError(BaseException):
    '''Used when accessing a resource that only exists when the worker is alive.'''


@dataclasses.dataclass
class WorkerResource(typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Simplest worker resource.'''
    worker_process_type: typing.Type[BaseWorkerProcess]
    method: typing.Optional[typing.Literal['forkserver', 'spawn', 'fork']] = None
    _proc: typing.Optional[multiprocessing.Process] = None
    _messenger: typing.Optional[PriorityMessenger] = None

    @classmethod
    def new(cls, 
        worker_process_type: typing.Type[BaseWorkerProcess], 
        method: typing.Optional[typing.Literal['forkserver', 'spawn', 'fork']] = None,
    ) -> WorkerResource:
        return cls(
            worker_process_type = worker_process_type,
            method = method,
        )
    
    ############### Dunder ###############
    def __enter__(self) -> WorkerResource:
        '''Starts worker with no parameters and returns it.'''
        try:
            self.start()
        except WorkerIsAlreadyAliveError as e:
            raise WorkerIsAlreadyAliveError(f'Cannot enter context when worker is already alive: {self.pid=}') from e
        return self
    
    def __exit__(self, *args):
        self.terminate()
            
    ############### Message Queue Functionality ###############
    # NOTE: all of these methods were used - access messenger directly to send/receive
        
    ############### Process interface (handles process exceptions, etc) ###############
    @property
    def pid(self):
        '''Get process id from worker.'''
        return self.proc.pid
        
    def start(self, **worker_kwargs,):
        '''Start the process, throws WorkerIsAliveError if already alive.'''
        if self.is_alive():
            raise WorkerIsAlreadyAliveError(f'Worker {self.pid} cannot be started because it is already alive.')
        self.reset_process(**worker_kwargs)
        return self.proc.start()
    
    def join(self, check_alive=True):
        '''Request that the process close and then wait for it to die.'''
        if check_alive and not self.is_alive():
            raise WorkerIsAlreadyDeadError(f'Worker {self.pid} cannot be joined because it is not alive.')
        self.messenger.receive_available() # receive in case errors should be thrown
        try:
            self.messenger.send_close_request()
        except (EOFError, BrokenPipeError) as e:
            pass
        return self.proc.join()

    def terminate(self, check_alive=True):
        '''Send terminate signal to worker.'''
        if check_alive and not self.proc.is_alive():
            raise WorkerIsAlreadyDeadError(f'Worker {self.pid} cannot be terminated because it is not alive.')
        try:
            self.messenger.send_close_request()
        except (EOFError, BrokenPipeError) as e:
            pass
        return self.proc.terminate()

    def is_alive(self, *arsg, **kwargs):
        '''Get status of process.'''
        return self.process_exists() and self.proc.is_alive(*arsg, **kwargs)
    
    ############### Maintaining Worker Processes ###############
    def check_process_exists(self):
        '''Check if process exists, and if not, raise error.'''
        if not self.process_exists():
            raise ValueError(f'Process or messenger are None: {self.proc=}, {self.messenger=}')
        return self.proc
    
    def process_exists(self) -> bool:
        '''True if this resource has a process and messenger.'''
        return self._proc is not None and self._messenger is not None
    
    def reset_process(self, **worker_kwargs):
        '''Reset the process, but keep the messenger.'''
        if self.process_exists() and self.is_alive():
            self.terminate()
        self._messenger, self._proc = self.new_pair(**worker_kwargs)
    
    def new_pair(self, 
        **worker_kwargs,
    ) -> typing.Tuple[PriorityMessenger, multiprocessing.context.ForkServerContext]:
        '''Get a messenger, process pair. Best to refresh the whole thing.'''
        ctx: multiprocessing.context.ForkServerContext = multiprocessing.get_context(method=self.method)
        process_messenger, resource_messenger = PriorityMessenger.make_pair()
        target = self.worker_process_type(
            messenger = process_messenger, 
            **worker_kwargs,
        )
        return (
            resource_messenger,
            ctx.Process( # type: ignore
                target = target, 
            )
        )
        
    @property
    def proc(self) -> multiprocessing.Process:
        '''Get process.'''
        if self._proc is None:
            raise WorkerIsDeadError(f'This resource does not have a working process: {self._proc=}')
        return self._proc
    
    @property
    def messenger(self) -> PriorityMessenger:
        '''Get messenger.'''
        if self._messenger is None:
            raise WorkerIsDeadError(f'This resource does not have a working messenger: {self._messenger=}')
        return self._messenger
    
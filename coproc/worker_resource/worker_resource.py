from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

from ..messenger import PriorityMessenger, SendPayloadType, RecvPayloadType

from .errors import WorkerIsAlreadyAliveError, WorkerIsAlreadyDeadError, WorkerIsDeadError
from .worker_process_wrapper import WorkerProcessWrapper

@dataclasses.dataclass
class WorkerResource(typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Manages a process and messenger for communicating with it.'''
    target: typing.Callable[[PriorityMessenger], None]
    messenger_type: typing.Type[PriorityMessenger] = PriorityMessenger
    method: typing.Optional[typing.Literal['forkserver', 'spawn', 'fork']] = None
    _proc: typing.Optional[multiprocessing.Process] = None
    _messenger: typing.Optional[PriorityMessenger] = None
    
    ############### Dunder ###############
    def __enter__(self) -> typing.Self:
        '''Starts worker with no parameters and returns it.'''
        try:
            self.start()
        except WorkerIsAlreadyAliveError as e:
            raise WorkerIsAlreadyAliveError(f'Cannot enter context when worker is already alive: {self.pid=}') from e
        return self
    
    def __exit__(self, *args):
        self.terminate(check_alive=False)
            
    ############### Message Queue Functionality ###############
    # NOTE: all of these methods were used - access messenger directly to send/receive
        
    ############### Process interface (handles process exceptions, etc) ###############
    @property
    def pid(self):
        '''Get process id from worker.'''
        return self.proc.pid
        
    def start(self, **worker_kwargs):
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
    ) -> typing.Tuple[PriorityMessenger, multiprocessing.Process]:
        '''Get a messenger, process pair. Best to refresh the whole thing.'''
        ctx: multiprocessing.context.ForkServerContext = multiprocessing.get_context(method=self.method)
        process_messenger, resource_messenger = self.messenger_type.new_pair()
        return (
            resource_messenger,
            ctx.Process(
                target = WorkerProcessWrapper(
                    target=self.target, 
                    messenger=process_messenger, 
                    worker_kwargs = worker_kwargs,
                ), 
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
    
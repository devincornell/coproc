
from __future__ import annotations
import typing
import dataclasses
import multiprocessing

from .basicworkerresource import BasicWorkerResource
from .messenger import PayloadType
from .errors import *


class BasicWorker(typing.Generic[PayloadType]):
    def __init__(self, worker_target: typing.Callable[[PayloadType],PayloadType], method: str = 'forkserver'):
        self.worker_target = worker_target
        self.resource: BasicWorkerResource = BasicWorkerResource.new(
            worker_target = worker_target,
            method = method,
        )

    def send(self, data: PayloadType):
        '''Send data to worker.'''
        self.resource.send(data)
        
    def receive(self) -> PayloadType:
        '''Receive data from worker. BLOCKING.'''
        return self.resource.receive()

    #################### Context and Destructor Dunders ####################
    def __enter__(self):
        if not self.resource.is_alive():
            self.resource.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.resource.terminate(check_alive=False)
    
    def __del__(self):
        #self.terminate(check_alive=False)
        pass



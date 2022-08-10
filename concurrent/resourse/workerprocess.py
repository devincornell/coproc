import collections
import dataclasses
import gc
import multiprocessing
import os
import traceback
from multiprocessing import Lock, Pipe, Pool, Process, Value
from typing import Any, Callable, Dict, Iterable, List, Tuple
import datetime

#from .errors import (UnidentifiedMessageReceivedError,
#                         WorkerHasNoUserFunctionError, WorkerIsDeadError)
from .errors import *
from .messages import (MessageType, DataPayloadMessage, UserFuncErrorMessage, WorkerErrorMessage, WorkerStatusMessage)

from .workerstatus import WorkerStatus
import time


@dataclasses.dataclass
class WorkerProcess:
    '''Basic worker meant to be run in a process.'''
    pipe: multiprocessing.Pipe
    target: Callable
    gcollect: bool = False
    verbose: bool = False
    status: WorkerStatus = None#dataclasses.field(default_factory=WorkerStatus)
    
    def __post_init__(self):
        self.status = WorkerStatus.new_status(os.getpid(), datetime.datetime.now())

    def __repr__(self):
        return f'{self.__class__.__name__}[{self.status.pid}]'

    def __call__(self):
        '''Call when opening the process.
        '''
        
        # main receive/send loop
        while True:

            # wait to receive data
            try:
                #if self.status_tracking: start = time.time()
                with self.status.time_wait() as t:
                    payload = self.recv()
                #if self.status_tracking: self.status.time_waiting += time.time() - start
            except (EOFError, BrokenPipeError):
                exit(1)
                
            try:
                getattr(payload, 'mtype')
            except AttributeError:
                exception = ProcessReceivedUnidentifiedMessage(f'Worker {self.status.pid} received unidentified message: {payload}.')
                self.send(WorkerErrorMessage(exception))


            # kill worker
            #if isinstance(payload, SigClose):
            if payload.mtype == MessageType.CLOSE:
                exit(1)

            # process received data payload
            #elif isinstance(payload, DataPayload):
            elif payload.mtype == MessageType.DATA:
                self.execute_and_send(payload)
            
            # return status of worker
            #elif isinstance(payload, StatusRequest):
            elif payload.mtype == MessageType.STATUS_REQUEST:
                self.status.update_uptime()
                self.send(WorkerStatusMessage(self.status))
            
            else:
                exception = ProcessReceivedUnidentifiedMessage(f'Worker {self.status.pid} received unidentified message: {payload}.')
                self.send(WorkerErrorMessage(exception))

    def execute_and_send(self, payload: DataPayloadMessage):
        '''Execute the provide function on the payload (modifies in-place), and return it.
        '''            
        # update pid and apply userfunc
        payload.pid = self.status.pid
        
        # try to execute function and raise any errors
        try:
            #if self.status_tracking: start = time.time()
            with self.status.time_work() as t:
                payload.data = self.target(payload.data)
            #if self.status_tracking:
            #    self.status.time_working += time.time() - start
            #    self.status.jobs_finished += 1
        except BaseException as e:
            self.send(UserFuncErrorMessage(e))
            traceback.print_exc()
            return

        # send result back to WorkerResource
        self.send(payload)
        
        # garbage collect if needed
        if self.gcollect:
            gc.collect()
        

    ############## Basic Send/Receive ##############

    def recv(self):
        if self.verbose: print(f'{self} waiting to receive')
        payload = self.pipe.recv()
        if self.verbose: print(f'{self} received: {payload}')
        return payload

    def send(self, data: Any):
        if self.verbose: print(f'{self} sending: {data}')
        return self.pipe.send(data)


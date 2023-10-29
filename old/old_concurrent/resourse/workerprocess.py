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
from .messages import (valid_process_recv_message_types, BaseMessage, MessageType, DataPayloadMessage, UserFuncErrorMessage, WorkerErrorMessage, WorkerStatusMessage)

from .workerstatus import WorkerStatus
from .messenger import Messenger
import time


@dataclasses.dataclass
class WorkerProcess:
    '''Basic worker meant to be run in a process.'''
    target: Callable
    pipe: multiprocessing.Pipe
    gcollect: bool = False
    verbose: bool = False
    
    def __post_init__(self):
        self.status = WorkerStatus.new_status(os.getpid(), datetime.datetime.now())
        self.messenger = Messenger(self.pipe, valid_process_recv_message_types, self.status.time_wait())

    def __call__(self):
        '''Call when opening the process.
        '''
        
        # main receive/send loop
        while True:

            # wait to receive data (and check for any other messages)
            try:
                message = self.messenger.get_next_message()
            except UnidentifiedMessageReceived as e:
                raise ProcessReceivedUnidentifiedMessage(f'Worker process {self.status.pid} received unidentified message: {e.message}')
            
            if message.mtype == MessageType.DATA:
                self.execute_and_send(message)
                
            elif message.mtype == MessageType.CLOSE:
                exit(1)
            
            # return status of worker
            elif message.mtype == MessageType.STATUS_REQUEST:
                self.status.update_uptime()
                self.messenger.send_message(WorkerStatusMessage(self.status))
            
            else:
                raise MessageTypeNotHandledError(f'{self.__class__.__name__} did not handle message of type {message.mtype}.')
            

    def execute_and_send(self, payload: DataPayloadMessage):
        '''Execute the provide function on the payload (modifies in-place), and return it.
        '''            
        # update pid and apply userfunc
        payload.pid = self.status.pid
        
        # send Resource any errors that were encountered
        try:
            with self.status.time_work() as t:
                payload.data = self.target(payload.data)
        except BaseException as e:
            self.messenger.send_message(UserFuncErrorMessage(e))
            traceback.print_exc()
            return

        self.messenger.send_message(payload)

        if self.gcollect:
            gc.collect()


    ############## Basic Send/Receive ##############
    #def recv_next_data(self) -> DataPayloadMessage:
    #    '''Will empty the incoming pipe and process non-data messages first.'''
    #    while True:
    #        
    #        # if no more messages to receive and the queue has some data in it
    #        if not self.poll_message() and len(self.data_queue) > 0:
    #            return self.data_queue.pop()
    #        
    #        # potentially blocking call    
    #        message = self.recv_message()
#
    #        # process received data payload
    #        if message.mtype == MessageType.DATA:
    #            #self.execute_and_send(message)
    #            self.data_queue.appendleft(message)
    #            
    #        # kill worker
    #        elif message.mtype == MessageType.CLOSE:
    #            exit(1)
    #        
    #        # return status of worker
    #        elif message.mtype == MessageType.STATUS_REQUEST:
    #            self.status.update_uptime()
    #            self.send_message(WorkerStatusMessage(self.status))
    #        
    #        else:
    #            exception = ProcessReceivedUnidentifiedMessage(f'Worker {self.status.pid} received unidentified message: {message}.')
    #            self.send_message(WorkerErrorMessage(exception))
#
    #def recv_message(self) -> BaseMessage:
    #    '''Receives the next message from the pipe. Blocking!'''
    #    if self.verbose: print(f'{self} waiting to receive')
    #    payload = self.pipe.recv()        
    #    
    #    # wait to receive data
    #    try:
    #        with self.status.time_wait() as t:
    #            message = self.pipe.recv()
    #    except (EOFError, BrokenPipeError):
    #        exit(1)
    #        
    #    try:
    #        getattr(message, 'mtype')
    #    except AttributeError:
    #        exception = ProcessReceivedUnidentifiedMessage(f'Worker {self.status.pid} received unidentified message: {message}.')
    #        self.send_message(WorkerErrorMessage(None, exception))
#
    #    if self.verbose: print(f'{self} received: {payload}')
#
    #    return payload
#
    #def send_message(self, message: BaseMessage):
    #    if self.verbose: print(f'{self} sending: {message}')
    #    return self.pipe.send(message)
    #
    #def poll_message(self) -> bool:
    #    '''Check if WorkerResource sent anything yet.
    #    '''
    #    return self.pipe.poll()

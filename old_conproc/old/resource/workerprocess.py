import collections
import dataclasses
import gc
import multiprocessing
import os
import traceback
from multiprocessing import Lock, Pipe, Pool, Process, Value
from typing import Any, Callable, Dict, Iterable, List, Tuple
import datetime
import typing

#from .errors import (UnidentifiedMessageReceivedError,
#                         WorkerHasNoUserFunctionError, WorkerIsDeadError)
from ..errors import *
from .messages import (valid_process_recv_message_types, BaseMessage, MessageType, DataPayloadMessage, UserFuncErrorMessage, WorkerErrorMessage, WorkerStatusMessage)

from .messages import MessageToProcessType, MessageToResourceType

from .workerstatus import WorkerStatus
from .messenger import Messenger, MessagePriority
import time


@dataclasses.dataclass
class BaseWorkerProcess:
    '''Lowest-level worker process interface. Handles only basic Messenger functionality.'''
    messenger: Messenger
    message_handler: typing.Callable[[typing.Any], typing.Any]
    
    @classmethod
    def new_process(cls, 
        pipe: multiprocessing.Pipe,
        message_prioritizer: typing.Callable[[BaseMessage], MessagePriority],
        message_handler: typing.Callable[[typing.Any], typing.Any], 
    ):
        worker_proc: cls = cls(
            messenger = Messenger(
                pipe=pipe, 
                message_prioritizer=message_prioritizer,
            ),
            message_handler = message_handler,
            status = WorkerStatus.current_status(),
        )
        return worker_proc
        
class SimpleWorkerProcess(BaseWorkerProcess):
    '''Use when maintaining state outside of __call__. Function called every time a message is received.'''

    def __call__(self):
        '''Main event loop for the process.
        '''
        # main receive/send loop
        while True:
            msg = self.messenger.get_next_message()
            result = self.message_handler(msg)
            self.messenger.send_message(result)

class MessengerWorkerProcess(BaseWorkerProcess):
    '''Use when maintaining state inside of __call__. Function lives for lifetime of the process.'''
                
    def __call__(self):
        '''Main event loop for the process.
        '''
        return self.message_handler(self.messenger)


class DataWorkerProcess(BaseWorkerProcess):
    def __call__(self):
        '''Main event loop for the process.
        '''
        # main receive/send loop
        while True:
            msg = self.messenger.get_next_message()
            if msg.mtype is MessageToProcessType.DATA:
                result = self.message_handler(msg)
                self.messenger.send_message(result)
            elif msg.mtype is MessageToProcessType.STATUS_REQUEST:
                pass
                self.messenger.send_message()



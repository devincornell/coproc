from __future__ import annotations
import collections
import dataclasses
import multiprocessing
import os
from multiprocessing import Lock, Pipe, Pool, Process, Value
from typing import Any, Callable, Dict, Iterable, List
import gc
from .errors import *
import datetime
import enum
from .workerstatus import WorkerStatus


class MessageType(enum.Enum):
    DATA = enum.auto()
    CLOSE = enum.auto()
    STATUS_REQUEST = enum.auto()
    USERFUNC_ERROR = enum.auto()
    WORKER_ERROR = enum.auto()
    WORKER_STATUS = enum.auto()
    
valid_resource_recv_message_types = set(
    MessageType.DATA,
    MessageType.STATUS_REQUEST,
    MessageType.CLOSE,
)
valid_process_recv_message_types = set(
    MessageType.DATA,
    MessageType.WORKER_STATUS,
    MessageType.USERFUNC_ERROR,
    MessageType.WORKER_ERROR,
)

class BaseMessage:
    #mtype: MessageType
    pass

@dataclasses.dataclass
class DataPayloadMessage(BaseMessage):
    '''For passing data to/from Workers.'''
    #__slots__ = ['data', 'ind', 'pid', 'mtype']
    request_id: int
    data: Any = dataclasses.field(compare=False)
    ind: int = 0
    pid: int = None
    priority: int = 1
    mtype: MessageType = MessageType.DATA
    

class SigCloseMessage(BaseMessage):
    '''WorkerResource tells process to end.'''
    request_id: int
    priority: int = 1
    mtype: MessageType = MessageType.CLOSE


################################# Worker Encounters Error #################################
@dataclasses.dataclass
class WorkerErrorMessage(BaseMessage):
    '''Sent from Worker to WorkerResource when any worker exception is passed 
    (not userfunc).
    '''
    request_id: int
    exception: BaseException
    priority: int = 1
    mtype: MessageType = MessageType.WORKER_ERROR

@dataclasses.dataclass
class UserFuncErrorMessage(BaseMessage):
    '''Passes exception from user function to main thread (and lets it know 
        there was an error with the user function).
    '''
    request_id: int
    exception: BaseException
    priority: int = 1
    mtype: MessageType = MessageType.USERFUNC_ERROR


################################# Getting Status Information #################################
@dataclasses.dataclass
class StatusRequestMessage(BaseMessage):
    '''Resource asks process for their present status.'''
    request_id: int
    priority: int = 1
    mtype: MessageType = MessageType.STATUS_REQUEST

@dataclasses.dataclass
class WorkerStatusMessage(BaseMessage):
    '''Process sends status to resource.'''
    request_id: int
    status: WorkerStatus
    priority: int = 1
    mtype: MessageType = MessageType.WORKER_STATUS


################################# DEPRIC Change User Function on the Fly #################################

class UserFunc(BaseMessage):
    '''Contains a user function and data to be passed to it when calling.
    Sent to a process upon init and when function should be changed.
    '''
    __slots__ = ['func', 'args', 'kwargs']
    def __init__(self, func: Callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        argstr = ', '.join(self.args)
        kwargstr = ', '.join([f'{k}={v}' for k,v in self.kwargs.items()])
        return f'{self.__class__.__name__}({self.func.__name__}(x, {argstr}, {kwargstr}))'

    def execute(self, data: Any):
        '''Call function passing *args and **kwargs.
        '''
        if self.func is None:
            raise WorkerHasNoUserFunctionError()
        return self.func(data, *self.args, **self.kwargs)


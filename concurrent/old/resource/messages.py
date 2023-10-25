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
from .messenger import MessagePriority, BaseMessage

class MessageToProcessType(enum.Enum):
    DATA = enum.auto()
    STATUS_REQUEST = enum.auto()
    CLOSE = enum.auto()

class MessageToResourceType(enum.Enum):
    DATA = enum.auto()
    STATUS_REPORT = enum.auto()
    USERFUNC_ERROR = enum.auto()
    WORKER_ERROR = enum.auto()

#class MessageType(enum.Enum):
#    DATA = enum.auto()
#    CLOSE = enum.auto()
#    STATUS_REQUEST = enum.auto()
#    USERFUNC_ERROR = enum.auto()
#    WORKER_ERROR = enum.auto()
#    WORKER_STATUS = enum.auto()
#    
#valid_process_recv_message_types = set(
#    MessageType.DATA,
#    MessageType.STATUS_REQUEST,
#    MessageType.CLOSE,
#)
#valid_resource_recv_message_types = set(
#    MessageType.DATA,
#    MessageType.WORKER_STATUS,
#    MessageType.USERFUNC_ERROR,
#    MessageType.WORKER_ERROR,
#)

#class BaseMessage:
#    #mtype: MessageType
#    pass

################## Messages to processes from Resource ##################

class MessageToProcess(BaseMessage):
    pass

@dataclasses.dataclass
class DataToProcessMessage(MessageToProcess):
    '''For passing data to/from Workers.'''
    #__slots__ = ['data', 'ind', 'pid', 'mtype']
    request_id: int
    data: Any = dataclasses.field(compare=False)
    ind: int = 0
    pid: int = None
    priority: int = MessagePriority.LOW
    mtype: MessageToProcessType = MessageToProcessType.DATA

@dataclasses.dataclass
class StatusRequestMessage(MessageToProcess):
    '''Resource asks process for their present status.'''
    request_id: int
    priority: int = MessagePriority.MAX
    mtype: MessageToProcessType = MessageToProcessType.STATUS_REQUEST

class SigCloseMessage(MessageToProcess):
    '''WorkerResource tells process to end.'''
    request_id: int
    priority: int = MessagePriority.MAX
    mtype: MessageToProcessType = MessageToProcessType.CLOSE


################## Messages to resource from Process ##################

class MessageToResource(BaseMessage):
    pass
    
@dataclasses.dataclass
class DataToResourceMessage(MessageToResource):
    '''For passing data to/from Workers.'''
    #__slots__ = ['data', 'ind', 'pid', 'mtype']
    request_id: int
    data: Any = dataclasses.field(compare=False)
    ind: int = 0
    pid: int = None
    priority: int = 1
    mtype: MessageToResourceType = MessageToResourceType.DATA

@dataclasses.dataclass
class WorkerStatusMessage(MessageToResource):
    '''Process sends status to resource.'''
    request_id: int
    status: WorkerStatus
    priority: int = 1
    mtype: MessageToResourceType = MessageToResourceType.WORKER_STATUS

@dataclasses.dataclass
class WorkerErrorMessage(MessageToResource):
    '''Sent from Worker to WorkerResource when any worker exception is passed 
    (not userfunc).
    '''
    request_id: int
    exception: BaseException
    priority: int = 1
    mtype: MessageToResourceType = MessageToResourceType.WORKER_ERROR

@dataclasses.dataclass
class UserFuncErrorMessage(MessageToResource):
    '''Passes exception from user function to main thread (and lets it know 
        there was an error with the user function).
    '''
    request_id: int
    exception: BaseException
    priority: int = 1
    mtype: MessageToResourceType = MessageToResourceType.USERFUNC_ERROR


################################# DEPRIC Change User Function on the Fly #################################

class UserFunc(MessageToProcess):
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


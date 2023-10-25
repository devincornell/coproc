from __future__ import annotations
import typing
import dataclasses
import enum


SendPayloadType = typing.TypeVar('SendPayloadType')
RecvPayloadType = typing.TypeVar('RecvPayloadType')

class Message:
    '''Base class for messages containing priority comparisons.'''
    priority: float
    
    def __lt__(self, other: Message) -> bool:
        return self.priority < other.priority
    
    def __le__(self, other: Message) -> bool:
        return self.priority <= other.priority
    
    def __gt__(self, other: Message) -> bool:
        return self.priority > other.priority
    
    def __ge__(self, other: Message) -> bool:
        return self.priority >= other.priority
    
    #def __eq__(self, other: Message) -> bool:
    #    return self.priority == other.priority
    
    #def __ne__(self, other: Message) -> bool:
    #    return self.priority != other.priority

##################### Generic Messages #####################

class MessageType(enum.Enum):
    DATA_PAYLOAD = enum.auto()
    CLOSE_REQUEST = enum.auto()
    ENCOUNTERED_ERROR = enum.auto()
    
@dataclasses.dataclass
class CloseRequestMessage(Message):
    '''Request that the other end of the pipe close.'''
    priority: float = float('-inf') # lower priority is more important
    mtype: MessageType = MessageType.CLOSE_REQUEST
    
@dataclasses.dataclass
class EncounteredErrorMessage(Message):
    exception: BaseException
    priority: float = float('-inf') # lower priority is more important
    mtype: MessageType = MessageType.ENCOUNTERED_ERROR
    
@dataclasses.dataclass
class DataMessage(Message):
    '''Send generic data to the other end of the pipe, using priority of sent messsage.
    NOTE: this is designed to allow users to access benefits of user-defined queue.
    '''
    payload: typing.Union[SendPayloadType, RecvPayloadType]
    request_reply: bool # whether to request a reply or not
    is_reply: bool # whether this is a reply to a request
    request_id: typing.Hashable = None # id of request. ignored if not reply or not requesting reply
    mtype: MessageType = MessageType.DATA_PAYLOAD
    
    @property
    def priority(self) -> float:
        try:
            return self.payload.priority
        except AttributeError:
            return float('inf')


##################### Messages from Resource to Process #####################

class MessageToProcessType(enum.Enum):
    SUBMIT_DATA = enum.auto()
    CLOSE = enum.auto()
    
class MessageToProcess(Message):
    priority: float
    mtype: MessageToProcessType

@dataclasses.dataclass
class Close(MessageToProcess):
    priority: float = float('-inf') # lower priority is more important
    mtype: MessageToProcessType = MessageToProcessType.CLOSE

@dataclasses.dataclass
class SubmitData(MessageToProcess):
    payload: SendPayloadType
    mtype: MessageToProcessType = MessageToProcessType.SUBMIT_DATA
    
    @property
    def priority(self) -> float:
        try:
            return self.payload.priority
        except AttributeError:
            return float('inf')

##################### Messages from Process to Resource #####################

class MessageFromProcessType(enum.Enum):
    REPLY_DATA = enum.auto()
    USERFUNC_ERROR = enum.auto()

class MessageFromProcess(Message):
    priority: float
    mtype: MessageFromProcessType

@dataclasses.dataclass
class UserfuncError(MessageFromProcess):
    exception: BaseException
    priority: float = float('-inf') # lower priority is more important
    mtype: MessageFromProcessType = MessageFromProcessType.USERFUNC_ERROR

@dataclasses.dataclass
class ReplyData(MessageFromProcess, typing.Generic[RecvPayloadType]):
    payload: RecvPayloadType
    mtype: MessageFromProcessType = MessageFromProcessType.REPLY_DATA
    
    @property
    def priority(self) -> float:
        try:
            return self.payload.priority
        except AttributeError:
            return float('inf')
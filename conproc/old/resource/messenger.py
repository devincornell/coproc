from __future__ import annotations

import dataclasses
import collections
import multiprocessing
import typing

from .errors import *
#from .workerstatus import WorkerStatus

class WorkerDiedError(BaseException):
    pass

class TimerPlaceholder:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

import enum
class MessagePriority(enum.Enum):
    MAX = enum.auto()
    HIGH = enum.auto()
    LOW = enum.auto()

class BaseMessage:
    '''Placeholder for message type.'''
    pass

@dataclasses.dataclass
class Messenger:
    '''Manages sending/receiving messages with simplified priority queue. 
    '''
    pipe: multiprocessing.Pipe

    message_prioritizer: typing.Callable[[BaseMessage], MessagePriority] = lambda x: MessagePriority.LOW

    timer_ctx_manager: typing.Any = dataclasses.field(default_factory=TimerPlaceholder)
    message_queue: collections.deque = dataclasses.field(default_factory=collections.deque)
    priority_queue: collections.deque = dataclasses.field(default_factory=collections.deque)

    @classmethod
    def dummy_pair(cls, message_prioritizer: typing.Callable[[BaseMessage], MessagePriority]) -> typing.Tuple[Messenger, Messenger]:
        p1, p2 = multiprocessing.Pipe(duplex=True)
        return Messenger(p1, message_prioritizer), Messenger(p2, message_prioritizer)

    ################################### Helpful Properties ###################################
    @property
    def queue_size(self):
        '''Get size of the message queue.'''
        return len(self.message_queue) + len(self.priority_queue)

    ################################### Queue Management ###################################
    def messages_available(self) -> bool:
        return self.poll_message() or self.queue_size > 0

    def get_next_message(self) -> BaseMessage:
        '''Handles receiving messages
        '''
        while True:
            if not self.poll_message() and self.queue_size > 0:
                return self.next_in_queue()

            message, priority = self.recv_with_priority()
            if priority is MessagePriority.MAX:
                return message
            else:
                self.add_to_queue(message, priority)
                

    def next_in_queue(self) -> BaseMessage:
        '''Gets next in priority or regular queue. Could be extended to full priority queue.
        '''
        if len(self.priority_queue):
            return self.priority_queue.pop()
        else:
            return self.message_queue.pop()

    def add_to_queue(self, message: BaseMessage, priority: MessagePriority):
        '''Handles regular and priority queues - could be extended to full priority queue system
        '''
        if priority is MessagePriority.HIGH:
            self.priority_queue.appendleft(message)
        else:
            self.message_queue.appendleft(message)
        

    ################################### Low-Level Send/Receive ###################################
    def poll_message(self) -> bool:
        '''Check if WorkerResource sent anything yet.
        '''
        return self.pipe.poll()
    
    def send_message(self, message: BaseMessage):
        return self.pipe.send(message)

    def recv_with_priority(self) -> typing.Tuple[BaseMessage, MessagePriority]:
        msg = self.recv_message()
        priority = self.message_prioritizer(msg)
        priority in MessagePriority # raises TypeError if message doesn't work
        return msg, priority

    def recv_message(self) -> BaseMessage:
        '''Receives the next message from the pipe. Blocking!'''
        try:
            with self.timer_ctx_manager as t:
                # this is blocking
                message = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            # the process died - handle better
            raise WorkerDiedError(f'Worker process died.')
        
        return message

    






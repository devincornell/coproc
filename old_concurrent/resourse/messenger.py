import dataclasses
import collections
import multiprocessing
import typing

from .errors import *
from .messages import MessageType, BaseMessage, DataPayloadMessage, WorkerStatusMessage
from .workerstatus import WorkerStatus

class EmptyTimer:
    def __enter__(self):
        return self
    def __exit__(self):
        pass

@dataclasses.dataclass
class Messenger:
    '''Manages sending/receiving messages on both Resource and Process side.
    This class is needed to manage a data queue so that both sides can prioritize messages.
    '''
    pipe: multiprocessing.Pipe
    valid_msg_types: typing.Set[MessageType]
    timer_ctx_manager: typing.Any = dataclasses.field(default_factory=EmptyTimer)
    data_queue: collections.deque = dataclasses.field(default_factory=collections.deque)

    ################################### Helpful Properties ###################################
    @property
    def queue_size(self):
        '''Get size of the message queue.'''
        return len(self.data_queue)

    ################################### Low-Level Send/Receive ###################################
    def get_next_message(self, ignore_data: bool = False) -> DataPayloadMessage:
        '''Will empty the incoming pipe and return non-data messages first.
        Args:
            ignore_data: True if user wants to get the next non-data message, while 
                queueing remaining data.
            request_id: id of the data object to look out for. When the messenger
                receives a message with that ID, it will share it immediately, otherwise
                it will keep adding to the data queue.
        '''
        while True:
            # if no more messages to receive and the queue has some data in it
            if not self.poll_message() and len(self.data_queue) > 0 and not ignore_data:
                return self.data_queue.pop()
            
            # potentially blocking call    
            message = self.recv_message()

            # add to the queue to prioritize messages over data
            if message.mtype == MessageType.DATA:
                self.data_queue.appendleft(message)
            else:
                return message
    
    ################################### Low-Level Send/Receive ###################################
    def poll_message(self) -> bool:
        '''Check if WorkerResource sent anything yet.
        '''
        return self.pipe.poll()
    
    def send_message(self, message: BaseMessage):
        return self.pipe.send(message)

    def recv_message(self) -> BaseMessage:
        '''Receives the next message from the pipe. Blocking!'''
        try:
            with self.timer_ctx_manager as t:
                # this is blocking
                message = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            exit(1)
            
        try:
            if message.mtype not in self.valid_msg_types:
                raise UnidentifiedMessageReceived(message)
        except AttributeError:
            raise UnidentifiedMessageReceived(message)

        return message

    






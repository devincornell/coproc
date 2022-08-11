import dataclasses
import collections
import multiprocessing
import typing

from .errors import *
from .messages import MessageType, BaseMessage, DataPayloadMessage, WorkerStatusMessage
from .workerstatus import WorkerStatus

@dataclasses.dataclass
class MessageHandler:
    '''Manages sending/receiving messages on both Resource and Process side.
    This class is needed to manage a data queue so that both sides can prioritize messages.
    '''
    pipe: multiprocessing.Pipe
    valid_msg_types: typing.Set[MessageType]
    data_queue: collections.deque = dataclasses.field(default_factory=collections.deque)

    ################################### Low-Level Send/Receive ###################################
    def get_next_message(self) -> DataPayloadMessage:
        '''Will empty the incoming pipe and return non-data messages first.'''
        while True:
            
            # if no more messages to receive and the queue has some data in it
            if not self.poll_message() and len(self.data_queue) > 0:
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
        
        # wait to receive data
        try:
            #with self.status.time_wait() as t:
            message = self.pipe.recv()
        except (EOFError, BrokenPipeError):
            exit(1)
            
        try:
            if message.mtype not in self.valid_msg_types:
                raise UnidentifiedMessageReceived()
        except AttributeError:
            raise UnidentifiedMessageReceived()
            #exception = ProcessReceivedUnidentifiedMessage(f'Worker {self.status.pid} received unidentified message: {message}.')
            #self.send_message(WorkerErrorMessage(None, exception))

        return message

    






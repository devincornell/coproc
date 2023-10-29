from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context

from .messenger import PriorityMessenger, SendPayloadType, RecvPayloadType, ResourceRequestedClose, DataMessage, MessageType



@dataclasses.dataclass
class BaseWorkerProcess(typing.Generic[SendPayloadType, RecvPayloadType]):
    messenger: PriorityMessenger

@dataclasses.dataclass
class SimpleWorkerProcess(BaseWorkerProcess, typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Simply receives data, processes it using worker_target, and sends the result back immediately.'''
    worker_target: typing.Callable[[SendPayloadType], RecvPayloadType]
    def __call__(self):
        '''Main event loop for the process.
        '''
        # main receive/send loop
        while True:
            try:
                msg = self.messenger.receive_data()
            except ResourceRequestedClose:
                exit()
            
            try:
                result = self.worker_target(msg)
            except Exception as e:
                self.messenger.send_error(e)
            
            print(f'{self.__class__.__name__} sending reply: {result}')
            self.messenger.send_reply(result)

@dataclasses.dataclass
class RawSimpleWorkerProcess(BaseWorkerProcess):
    '''Simply receives raw message, processes it using worker_target, and sends the result back immediately.'''
    worker_target: typing.Callable[[DataMessage], typing.Any]
    def __call__(self):
        '''Main event loop for the process.
        '''
        # main receive/send loop
        while True:
            msg = self.messenger.receive_message()
            try:
                result = self.worker_target(msg)
            except ResourceRequestedClose:
                exit()
            except Exception as e:
                self.messenger.send_error(e)
            self.messenger.send_reply(result)


@dataclasses.dataclass
class RawWorkerProcess(BaseWorkerProcess):
    '''Worker target receives messenger to use as needed.'''
    worker_target: typing.Callable[[PriorityMessenger], typing.Any]
    def __call__(self):
        '''Main event loop for the process.
        '''
        # main receive/send loop
        return self.worker_target(self.messenger)
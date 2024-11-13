
import dataclasses

import time
import typing

import sys
sys.path.append('..')
import coproc


def echo_test(v: typing.Any) -> typing.Any:
    print('echoing', v)
    return v

    
import os

#class EchoProcess(coproc.BaseWorkerProcess):
#    '''Process that sends back the same data it receives.'''
#    
#    def __call__(self):
#        '''Main process loop.'''
#        print(f'Starting process {os.getpid()}')
#        while True:
#            data_msg = self.messenger.receive_message_blocking()
#            print(f'process {os.getpid()} received: {data_msg.payload}')
#            if data_msg.request_reply:
#                self.messenger.send_reply(data_msg.payload)
#            else:
#                self.messenger.send_norequest(data_msg.payload)

import time

def echo_process(messenger: coproc.PriorityMessenger):
    '''Process that sends back the same data it receives.'''
    print(f'Starting process {os.getpid()}')
    while True:
        data_msg = messenger.receive_message_blocking()
        print(f'process {os.getpid()} received: {data_msg.payload}')
        if data_msg.request_reply:
            messenger.send_reply(data_msg.payload)
        else:
            messenger.send_norequest(data_msg.payload)



def test_workerresource_basic():
    
    with coproc.WorkerResource(echo_process) as w:
        v = 'Hello, world!'
        w.messenger.send_norequest(v)
        assert(v == w.messenger.receive_blocking())
        
        n = 10
        for i in range(n):
            w.messenger.send_norequest(i)
            print(f'{w.messenger.available()=} {w.messenger.remaining()=}')
        assert(w.messenger.remaining() == 0)
        time.sleep(0.3)
        assert(w.messenger.available() == n)
        assert(w.messenger.receive_available() == list(range(n)))
        
        for i in range(n):
            w.messenger.send_request(i)
            assert(w.messenger.remaining() == i + 1)
        assert(w.messenger.remaining() == n)
        time.sleep(0.3)
        assert(w.messenger.available() == n)
        result = list(w.messenger.receive_remaining())
        print(result)
        assert(result == list(range(n)))
        
if __name__ == '__main__':
    #test_echo()
    #test_custom_process()
    test_workerresource_basic()
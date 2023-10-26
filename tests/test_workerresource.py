
import dataclasses

import time
import typing

import sys
sys.path.append('..')
import conproc


def test_custom_process():
    print(f'============ starting mapworker =============')
    k = 0
    with conproc.MapWorker() as w:
        w.apply_async(echo_test, range(10))
        for i in w.receive():
            print(f'{i=}')
            assert(i == k)
            k += 1

def echo_test(v: typing.Any) -> typing.Any:
    print('echoing', v)
    return v

def UNUSED():
    res = conproc.WorkerResource(
        worker_process_type = conproc.SimpleWorkerProcess,
    )
    res.start(worker_target=echo_test)
    res.messenger.request_multiple(range(10))
    
    time.sleep(0.01)
    print(f'{res.messenger.available()=} {res.messenger.remaining()=}')
    
    for i in res.messenger.receive_remaining():
        #print(f'{res.messenger.available()=} {res.messenger.remaining()=}')
        print(f'{i=}')
    res.join()
    
    print(f'static start/stop')
    res.start(worker_target=echo_test)
    res.messenger.send_request_multiple(range(10))
    val = 0
    for i in res.messenger.receive_remaining():
        assert(i == val)
        val += 1
        
    res.join()
    
    
import os

class EchoProcess(conproc.BaseWorkerProcess):
    '''Process that sends back the same data it receives.'''
    
    def __call__(self):
        '''Main process loop.'''
        print(f'Starting process {os.getpid()}')
        while True:
            data_msg = self.messenger.receive_message_blocking()
            print(f'process {os.getpid()} received: {data_msg.payload}')
            if data_msg.request_reply:
                self.messenger.send_reply(data_msg.payload)
            else:
                self.messenger.send_norequest(data_msg.payload)

import time

def test_workerresource_basic():
    
    with conproc.WorkerResource(EchoProcess) as w:
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
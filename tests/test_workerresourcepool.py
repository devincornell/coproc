
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

@dataclasses.dataclass
class EchoProcess(coproc.BaseWorkerProcess):
    '''Process that sends back the same data it receives.'''
    verbose: bool
    
    def __call__(self):
        '''Main process loop.'''
        pid = os.getpid()
        if self.verbose: print(f'Starting process {pid}')
        while True:
            data_msg = self.messenger.receive_message_blocking()
            if self.verbose: print(f'{pid=} <<-- {data_msg.payload}')
            if data_msg.request_reply:
                self.messenger.send_reply(data_msg.payload)
            else:
                self.messenger.send_norequest(data_msg.payload)
            if self.verbose: print(f'{pid=} -->> {data_msg.payload}')

import time

def square(x):
    return x**2
    
    
def test_pool_basic():

    n = 4
    v = 'hello world'
    vs = list(range(100))
    pool = coproc.WorkerResourcePool.new(n, EchoProcess, coproc.MultiMessenger, verbose=True)
    print(pool)
    assert(not pool.is_alive())
    with pool as p:
        assert(p.is_alive())
        p.apply_to_workers(lambda w: w.messenger.send_request(v))
        result = p.apply_to_workers(lambda w: w.messenger.receive_blocking())
        assert(result == [v]*n)
        
        # make sure map messages works
        results = set(p.map_messages(iter(vs)))
        print(results)
        assert(results == set(vs))
        
    time.sleep(0.1)
    assert(not pool.is_alive())
    try:
        pool.terminate(check_alive=True)
        raise Exception('should have raised WorkerIsAlreadyDeadError')
    except coproc.WorkerIsAlreadyDeadError:
        pass
        
        
if __name__ == '__main__':
    #test_echo()
    #test_custom_process()
    test_pool_basic()
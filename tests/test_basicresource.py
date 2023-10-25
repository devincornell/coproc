import time
import typing

#import sys
#sys.path.append('..')
import concurrent
import dataclasses 



def test_custom_process():
        
    
    print(f'============ starting mapworker =============')
    k = 0
    with concurrent.MapWorker() as w:
        w.apply_async(echo_test, range(10))
        for i in w.receive():
            print(f'{i=}')
            assert(i == k)
            k += 1



def echo_test(v: typing.Any) -> typing.Any:
    print('echoing', v)
    return v

def test_echo():
    res = concurrent.WorkerResource(
        worker_process_type = concurrent.SimpleWorkerProcess,
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
    res.messenger.request_multiple(range(10))
    val = 0
    for i in res.messenger.receive_remaining():
        assert(i == val)
        val += 1
        
    res.join()
    

if __name__ == '__main__':
    test_echo()
    test_custom_process()
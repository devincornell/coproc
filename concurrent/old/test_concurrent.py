import time
import multiprocessing

import sys
sys.path.append('..')
import concurrent
#import pydevin


def test_messenger():
    
    # attach the two messengers
    m1, m2 = concurrent.Messenger.dummy_pair(
        lambda x: concurrent.MessagePriority.HIGH if x == 'HIGH' else concurrent.MessagePriority.LOW
    )

    assert(not m1.messages_available())
    m1.send_message('hi!')
    assert(not m1.messages_available())
    assert(m2.messages_available())
    assert('hi!' == m2.get_next_message())
    assert(not m2.messages_available())
    
    for i in range(10):
        m2.send_message(i)
    assert(not m2.messages_available())
    assert(m1.messages_available())
    
    i = 0
    while m1.messages_available():
        m = m1.get_next_message()
        print(m)
        assert(m == i)
        i += 1

    # test the priority aspect
    for i in range(10):
        m1.send_message(i)
    m1.send_message('HIGH')
    assert(m2.get_next_message() == 'HIGH')
    assert(m2.messages_available())

    i = 0
    while m2.messages_available():
        m = m2.get_next_message()
        print(m)
        assert(m == i)
        i += 1

    print('finished messenger test')
    
def test1():
    def square(a: float):
        return a**2
    
    resource = concurrent.WorkerResource.start_simpleworker(square)
    print(resource)
    assert(resource.is_alive())
    resource.join()
    assert(not resource.is_alive())
    resource.start()
    assert(resource.is_alive())
    try:
        resource.start()
    except concurrent.WorkerIsAliveError:
        pass
    else:
        raise AssertionError()
    
    with concurrent.WorkerResource(square) as w:
        print(w.execute(5))
        print(w.get_status())
        time.sleep(1)
        print(w.get_status())


if __name__ == '__main__':
    test_messenger()
    test1()



import time
import typing

import concurrent


class MyProcess:
    '''This class will receive lists of numbers from the client.'''
    def __init__(self):
        '''This will only run on the resource side - will not run in process.'''
        self.is_setup = False
        
    def setup(self):
        '''This will happen when the setup is complete.'''
        self.sums = list()
        self.is_setup = True
    
    def execute(self, numbers: typing.List[int]):
        '''This will execute every time the process receives data.'''
        self.sums.append(sum(numbers))
        print('#'*10, 'Worker Process', '#'*10, f'\n{self.sums}\n', '#'*30)
        return self.sums[-1]
    
    def __call__(self, data: typing.Any):
        '''This will be executed by WorkerProcess.'''
        if not self.is_setup:
            self.setup()
        return self.execute(data)
            
    
def test3():

    import enum
    
    class Color(enum.Enum):
        RED = enum.auto()
        BLUE = enum.auto()
    
    print(Color.RED in Color)
    
    exit()
    with concurrent.WorkerResource(MyProcess()) as w:
        
        # send and receive synchronously
        print(w.execute([1, 2, 3]))
        print(w.execute([1, 2, 5]))
        print(w.execute([1, 2, 8]))
        
        w.send_data([1, 2, 8])
        w.send_data([1, 2, 8])
        w.send_data([1, 2, 8])
        
        print(w.get_status().efficiency())
        print(w.recv_data())
        print(w.recv_data())
        print(w.recv_data())
        
        print(w.get_status().efficiency())

        
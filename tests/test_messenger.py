import time
import multiprocessing
import pathlib
import json

import sys
sys.path.append('..')
import conproc

#import pydevin
def test_messenger():
        
    # attach the two messengers
    pm, rm = conproc.PriorityMessenger.make_pair()
    assert(rm.remaining() == 0)
    assert(not pm.available())
    
    # send resource -> process
    v = 'hi'
    rm.send_request(v)
    assert(rm.remaining() == 1)
    assert(not rm.available())
    assert(pm.available())
    assert(pm.receive_data() == v)
    assert(not pm.available())
    assert(rm.remaining() == 1)
    
    # send process -> resource
    pm.send_reply(v)
    assert(rm.available())
    assert(rm.remaining() == 1)
    assert(rm.receive_data() == v)
    assert(not rm.available())
    assert(rm.remaining() == 0)
    
    # handle requests to close the pipe
    rm.send_close_request()
    assert(rm.remaining() == 0) # not sure I care about this, but it does capture current behavior
    assert(pm.available())
    try:
        pm.receive_data()
        raise Exception('should not have gotten here')
    except conproc.ResourceRequestedClose as e:
        print(e)
    
    assert(not rm.available())
    pm.send_error(ValueError('test error was successful'))
    assert(rm.available())
    try:
        rm.receive_data()
        raise Exception('should not have gotten here')
    except ValueError as e:
        print(e)
    
    # handle other test    
    vs = [1,2,3]
    rm.send_request_multiple(vs)
    assert(rm.remaining() == len(vs))
    assert(not rm.available())
    for v in vs:
        assert(pm.available())
        assert(pm.receive_data() == v)
    assert(not pm.available())
    [pm.send_reply(v) for v in vs]
    assert(rm.available())
    assert(rm.remaining() == len(vs))
    for tv,v in zip(vs, rm.receive_remaining()):
        assert(tv == v)
    assert(not rm.available())
    assert(rm.remaining() == 0)
    
    print(f'test messenger passed')
    
import dataclasses
@dataclasses.dataclass(order=True)
class TestClassGreater:
    s: str
    i: int = 10
    
@dataclasses.dataclass(order=True)
class TestClassLesser:
    s: str
    i: int = 5
    
    
@dataclasses.dataclass
class MessengerTester:
    proc_msngr: conproc.PriorityMessenger
    res_msngr: conproc.PriorityMessenger
    
    def test(self, proc_available: bool, res_available: bool, proc_remaining: int, res_remaining: int):
        assert(self.res_msngr.available() is res_available)
        assert(self.proc_msngr.available() is proc_available)
        assert(self.res_msngr.remaining() == res_remaining)
        assert(self.proc_msngr.remaining() == proc_remaining)
        
    def print(self):
        print(f'{self.proc_msngr.available()=}, {self.res_msngr.available()=}, {self.proc_msngr.remaining()=}, {self.res_msngr.remaining()=}')


class TestError(BaseException):
    pass

def test_priority_messenger():
    proc_msngr, res_msngr = conproc.PriorityMessenger.make_pair()
    tester = MessengerTester(proc_msngr, res_msngr)
    v = 1
    vs = [1, 2, 3]
    
    print(f'\n================== Testing simple send/receive ==================')
    tester.test(False, False, 0, 0)
    
    res_msngr.send_data_noreply(v)
    tester.test(True, False, 0, 0)
    
    assert(proc_msngr.receive_data() == v)
    tester.test(False, False, 0, 0)
    
    print(f'\n================== Testing request/reply ==================')
    res_msngr.send_request(v)
    tester.test(True, False, 0, 1)
    
    results = proc_msngr.receive_available()
    tester.test(False, False, 0, 1)
    assert(len(results) == 1)
    assert(results[0] == v)
    
    proc_msngr.send_reply(results[0])
    tester.test(False, True, 0, 1)
    assert(res_msngr.receive_data() == v)
    tester.test(False, False, 0, 0)
    
    res_msngr.send_request_multiple(vs)
    print(res_msngr.remaining())
    tester.test(True, False, 0, len(vs))
    assert(proc_msngr.receive_available() == vs)
    assert(res_msngr.remaining() == len(vs))
    [proc_msngr.send_reply(v) for v in vs]
    assert(res_msngr.remaining() == len(vs))
    assert(res_msngr.receive_available() == vs)
    tester.print()
    assert(res_msngr.remaining() == 0)
    
    if False: # NEED TO DO THIS BUT GOT LAZY
        # process echoes available data
        for i, r in enumerate(proc_msngr.receive_available()):
            print(i, r)
            tester.test(False, False, 0, len(vs))
            proc_msngr.send_reply(r)
            tester.test(False, True, 0, len(vs))
            assert(res_msngr.receive_data() == r)
            print(res_msngr.remaining(), i, len(vs)-i-1)
            tester.test(False, False, 0, len(vs)-i-1)
            
    tester.print()
    tester.test(False, False, 0, 0)
        
    # resource receives all expected data
    for i, v in enumerate(res_msngr.receive_remaining()):
        assert(v == vs[0])

    print(f'\n================== Testing close/error ==================')
    res_msngr.send_close_request()
    assert(proc_msngr.available())
    try:
        proc_msngr.receive_available()
        raise Exception('should not have gotten here')
    except conproc.ResourceRequestedClose:
        pass
    
    res_msngr.send_error(TestError('test error'))
    try:
        proc_msngr.receive_data()
        raise Exception('should not have gotten here')
    except TestError:
        pass
    

if __name__ == '__main__':
    test_messenger()
    test_priority_messenger()
    
    
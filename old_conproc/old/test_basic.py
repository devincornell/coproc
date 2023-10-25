import time
import multiprocessing
import pathlib
import json

import sys
sys.path.append('..')
import concurrent
#import pydevin


def read_file(fpath: pathlib.Path) -> str:
    with fpath.open('r') as f:
        return f.read()
    
def test_basic():
    fpaths = pathlib.Path('tests').rglob('*.py')
    with concurrent.BasicWorker(read_file) as w:
        for fpath in fpaths:
            w.send(fpath)
    
        results = list()
        for _ in range(len(fpaths)):
            results.append(w.receive())
        
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
    test_basic()


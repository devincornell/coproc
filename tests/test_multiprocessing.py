import multiprocessing
import time


import dataclasses
import pathlib

import enum
class CloseRequestType(enum.Enum):
    CLOSE_REQUEST = enum.auto()
    def __repr__(self):
        return "CLOSE_REQUEST"

CLOSE_REQUEST = CloseRequestType.CLOSE_REQUEST
'''Represents a missing Value.'''


class TmpPath:
    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
    def __enter__(self):
        return self.path
    def __exit__(self, *args):
        self.path.unlink(missing_ok=True)

import typing

@dataclasses.dataclass
class LoggerProcess:
    log_path: pathlib.Path
    logs: typing.List[str] = dataclasses.field(default_factory=list)
    
    def __call__(self, msg: str):
        '''Process input data.'''
        if msg is CLOSE_REQUEST:
            return self
        self.logs.append(msg)
        with self.log_path.open('a') as f:
            f.write(msg)
            f.write('\n')
        print(f'{self.logs=}')
        return msg
    
@dataclasses.dataclass
class Logger:
    log_path: pathlib.Path
    processes: int = 1
    pool: multiprocessing.Pool = None
    target_func: LoggerProcess = None
    
    def __post_init__(self):
        self.log_path = pathlib.Path(self.log_path)
        self.target_func = LoggerProcess(self.log_path)
    
    def log(self, msg: str):
        '''Process input data.'''
        return self.pool.apply_async(self.target_func, args=(msg,)).get()
    
    def close(self):
        return self.log(CLOSE_REQUEST)
    
    def __enter__(self):
        if self.pool is None:
            self.pool = multiprocessing.Pool(self.processes)
        return self
    
    def __exit__(self, *args):
        if self.pool is not None:
            self.pool.close()
            self.pool.join()
            self.pool = None

if __name__ == '__main__':
    
    #logger = LoggerProcess(pathlib.Path('test.log'))
    fn = pathlib.Path('test.log')
    #with TmpPath(fn) as fn:
    with Logger(fn) as logger:
        logger.log('hello')
        logger.log('wtf is up')
        print(logger.log('another'))
        logger_proc = logger.close()
            
    print(logger_proc)
    
    # do IO while returning resuls from various threads
    #with multiprocessing.Pool(3) as p:
    #    for r in p.imap_unordered(fake_io_thread, [1, 2, 3]):
    #        print(r)
    
    


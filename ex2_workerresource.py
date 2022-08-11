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
            
    
if __name__ == '__main__':
    
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
        
        
        
        
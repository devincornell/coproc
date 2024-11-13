class WorkerIsAlreadyAliveError(BaseException):
    '''Used when trying to start a worker that is already alive.'''

class WorkerIsAlreadyDeadError(BaseException):
    '''Used when trying to stop a worker that is already stopped.'''

class WorkerIsDeadError(BaseException):
    '''Used when accessing a resource that only exists when the worker is alive.'''

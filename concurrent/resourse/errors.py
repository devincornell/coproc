class WorkerResourceBaseException(BaseException):
    pass
#    def __init__(self, *args, **kwargs):
#        super().__init__(self.message, *args, **kwargs)



############################# Worker Resource Errors #############################

class WorkerDiedError(WorkerResourceBaseException):
    pass

class WorkerIsDeadError(WorkerResourceBaseException):
    pass

class WorkerIsAliveError(WorkerResourceBaseException):
    pass

class UnidentifiedMessageReceived(WorkerResourceBaseException):
    pass#message = f'Worker received an invalid message.'

class ProcessReceivedUnidentifiedMessage(UnidentifiedMessageReceived):
    pass#message = 'This WorkerProcess received an unidentified message.'

class ResourceReceivedUnidentifiedMessage(UnidentifiedMessageReceived):
    pass#message = 'This WorkerResource received an unidentified message.'


class UserFuncRaisedException(Exception):
    def __init__(self, userfunc_exception, *args, **kwargs):
        self.userfunc_exception = userfunc_exception
        super().__init__(*args, **kwargs)


############################# Worker Pool Errors #############################

class NoWorkersAvailable(WorkerResourceBaseException):
    message = 'This WorkerPool has no available resources. Either use as context manager or call .start().'

############################# DEPRICATED #############################

class WorkerHasNoUserFunctionError(WorkerResourceBaseException):
    message = (f'Worker was not provided with a function. '
            'Either provide a function when the worker is created '
            'or update the worker\'s function using '
            '.update_userfunc().')








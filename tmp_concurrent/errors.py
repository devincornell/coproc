

class WorkerResourceBaseException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(self.message, *args, **kwargs)
    #def __str__(self):
    #    return f'{self.__class__.__name__}'
    #def __str__(self):
    #    return f'{self.message}'

class NoWorkersAvailable(WorkerResourceBaseException):
    message = 'This WorkerPool has no available resources. Either use as context manager or call .start().'

class WorkerDiedError(WorkerResourceBaseException):
    message = f'Worker died before finishing.'

class WorkerIsDeadError(WorkerResourceBaseException):
    message = f'Worker is already closed.'

class WorkerIsAliveError(WorkerResourceBaseException):
    message = f'Cannot start worker because it is already alive.'

class UnidentifiedMessageReceivedError(WorkerResourceBaseException):
    message = f'Worker received an invalid message.'

class WorkerResourceReceivedUnidentifiedMessage(WorkerResourceBaseException):
    message = 'This WorkerResource received an unidentified message.'

class WorkerHasNoUserFunctionError(WorkerResourceBaseException):
    message = (f'Worker was not provided with a function. '
            'Either provide a function when the worker is created '
            'or update the worker\'s function using '
            '.update_userfunc().')

class UserFuncRaisedException(Exception):
    def __init__(self, userfunc_exception, *args, **kwargs):
        self.userfunc_exception = userfunc_exception
        super().__init__(*args, **kwargs)

#no_function_error_msg = ('Worker {pid} was not provided '
#    'with a function. Either provide a function when '
#    'the worker is created or send a NewFunction via '
#    'the pipe.')


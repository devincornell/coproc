from __future__ import annotations
import dataclasses
import datetime
import os

@dataclasses.dataclass
class WorkerStatus:
    '''Allow worker to keep track of its own status.'''
    pid: int
    start_ts: datetime.datetime
    waiting_time: datetime.timedelta = None
    working_time: datetime.timedelta = None
    jobs_finished: int = 0
    uptime: int = None # to be updated before sending

    @classmethod
    def new(cls, pid: int):
        status: cls = cls(
            pid = os.getpid(),
            start_ts = datetime.datetime.now(),
            waiting_time = datetime.timedelta(seconds=0),
            working_time = datetime.timedelta(seconds=0),
        )
        return status
        
    @classmethod
    def current_status(cls) -> WorkerStatus:
        return cls.new_status(os.getpid(), datetime.datetime.now())

    @classmethod
    def new_status(cls, pid: int, start_ts: datetime.datetime) -> WorkerStatus:
        '''Construct a new WorkerStatus object.'''
        return cls(pid, start_ts)
    
    #################### Context Managers for Timing Work/Wait ####################
    def time_wait(self) -> WaitTimer:
        '''Open context manager for timing wait.'''
        return WaitTimer(self)

    def time_work(self) -> WorkTimer:
        '''Open context manager for timing work.'''
        return WorkTimer(self)

    def update_uptime(self) -> datetime.datetime:
        self.uptime = datetime.datetime.now() - self.start_ts

    #################### Get Stats ####################
    def efficiency(self) -> float:
        '''Work time divided by work+wait time.'''
        working_sec = self.working_time.total_seconds()
        return working_sec / (working_sec + self.waiting_time.total_seconds())

    def total_efficiency(self) -> float:
        '''Work time divided by uptime.'''
        return self.working_time.total_seconds() / self.uptime.total_seconds()

    def sec_per_job(self):
        return self.working_time.total_seconds() / self.jobs_finished

################################# Context Managers for Timing/Job Counting #################################

@dataclasses.dataclass
class StatusTimer:
    '''Context manager to support workerstatus.'''
    wstatus: WorkerStatus
    start: datetime.datetime = None
    def __enter__(self):
        '''Start the timer.'''
        self.start = datetime.datetime.now()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        raise NotImplementedError('__exit__() should be defined for this timer.')
    
    def get_diff(self):
        return (datetime.datetime.now() - self.start)

    
class WorkTimer(StatusTimer):
    def __exit__(self, exc_type, exc_value, exc_tb):
        '''Stop the timer and add data to WorkerStatus.'''
        self.wstatus.working_time += self.get_diff()
        self.wstatus.jobs_finished += 1
        
class WaitTimer(StatusTimer):
    def __exit__(self, exc_type, exc_value, exc_tb):
        '''Stop the timer and add data to WorkerStatus.'''
        self.wstatus.waiting_time += self.get_diff()
        
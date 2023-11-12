from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd
import datetime
import psutil
import os
import time

from ..messenger import ResourceRequestedClose, PriorityMessenger
#from ..workerresource import WorkerResource

from .monitormessenger import SubmitNoteMessage, RequestStatsMessage, StatsDataMessage, UpdateChildProcessesMessage, RequestSaveMemoryFigureMessage
from .statsresult import StatsResult
import pathlib

@dataclasses.dataclass
class MonitorWorkerProcess:
    '''Simply receives data, processes it using worker_target, and sends the result back immediately.'''
    pid: int
    include_children: bool
    snapshot_seconds: float
    messenger: PriorityMessenger
    log_path: pathlib.Path
    fig_path: pathlib.Path
    save_fig_freq: int
    processes: typing.List[psutil.Process] = dataclasses.field(default_factory=list)
    notes: typing.List[Note] = dataclasses.field(default_factory=list)
    stats: typing.List[Stat] = dataclasses.field(default_factory=list)
    verbose: bool = False
    
    def __call__(self):
        '''Main event loop for the process.
        '''
        if self.verbose: print(os.getpid(), 'starting monitor worker process')
        #try:
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.fig_path is not None:
            self.fig_path.parent.mkdir(parents=True, exist_ok=True)
        
        # add at least two capture windows to make future stuff work
        last_mem = 0
        self.stats += [
            Stat.capture_window(
                process = self.root_process(), 
                capture_time = datetime.timedelta(seconds=self.snapshot_seconds),
            ),
            Stat.capture_window(
                process = self.root_process(), 
                capture_time = datetime.timedelta(seconds=self.snapshot_seconds),
            ),
        ]
        
        self.processes = self.get_processes()
        
        # main receive/send loop
        msg = None
        finished = False # not used yet
        while not finished:
            try:
                msgs = self.messenger.receive_available()
            except ResourceRequestedClose:
                if self.verbose: print(f'[{self.messenger.messages_received()}] <<--', 'requested close')
                #time.sleep(3)
                finished = True
                break
            
            for msg in msgs:
                if self.verbose: print(f'recv [{self.messenger.messages_received()}] <<--', msg)
                
                if isinstance(msg, SubmitNoteMessage):
                    new_note = Note(
                        pid = self.root_process().pid,
                        note = msg.note,
                        details = msg.details,
                        do_label=msg.do_label,
                        do_log = msg.do_log,
                        memory_usage = last_mem,
                        ts = msg.ts,
                    )
                    
                    self.notes.append(new_note)
                    if self.log_path is not None:
                        with self.log_path.open('a') as f:
                            f.write(new_note.long_log_str())
                
                
                elif isinstance(msg, RequestStatsMessage):
                    reply_msg = StatsDataMessage(self.stats_result())
                    self.messenger.send_reply(reply_msg)
                    if self.verbose: print(f'sent [{self.messenger.messages_received()}] -->>', reply_msg)
                
                elif isinstance(msg, RequestSaveMemoryFigureMessage):
                    self.stats_result().save_memory_plot(
                        msg.fname, 
                        **msg.save_kwargs
                    )
                    
                elif isinstance(msg, UpdateChildProcessesMessage):
                    self.processes = self.get_processes()
                
                else:
                    raise NotImplementedError(f'unknown message type: {msg.mtype}')
            
            finished_capture = False
            while not finished_capture:
                #try:
                for p in self.processes:
                    try:
                        stat = Stat.capture_window(
                            process = p, 
                            capture_time = datetime.timedelta(seconds=self.snapshot_seconds)
                        )
                        self.stats.append(stat)
                        if p.pid == self.pid:
                            last_mem = stat.memory_usage
                        finished_capture = True
                    except (MemoryInfoNotAvailableError, psutil.NoSuchProcess) as e:
                        self.processes = self.get_processes()
                        
                #except psutil.NoSuchProcess as e:
                #    # get only processes that exist and try again
                #    self.proceses = self.get_processes()
                
                
            if self.fig_path is not None:
                if len(self.stats) > 0 and len(self.stats) % self.save_fig_freq == 0:
                    self.stats_result().save_memory_plot(self.fig_path, verbose=False)
    
        #except BaseException as e:
        #    print(f'Error in MonitorWorkerProcess: {e}')
        #    self.messenger.send_error(e)
        if self.verbose: print(f'[{os.getpid()}] exited naturally')
    
    def get_processes(self, include_monitor: bool = False) -> typing.List[psutil.Process]:
        exclude_pid = set() if include_monitor else set([os.getpid()])
        
        root_process = self.root_process()
        processes = [root_process]
        
        if self.include_children:
            processes += [c for c in root_process.children(recursive=True) if c.pid not in exclude_pid]
        return processes
    
    def root_process(self) -> psutil.Process:
        return psutil.Process(self.pid)
    
    def stats_result(self) -> StatsResult:
        return StatsResult(
            notes=self.notes,
            stats=self.stats,
        )
    
@dataclasses.dataclass
class Note:
    '''Manages notes sent from host to worker to be logged/saved.'''
    pid: int
    note: str
    details: typing.Optional[str]
    do_label: bool
    do_log: bool
    memory_usage: int
    ts: datetime.datetime
    
    def log_str(self) -> str:
        return f'{self.ts.isoformat()}: {self.note}; details={self.details}\n'
    
    def long_log_str(self, show_ts: bool=True, show_delta: bool=True, show_mem: bool=True) -> str:
        
        # helper to get a default value
        get_default = lambda x,y: x if x is not None else y
        
        if show_ts:
            ts_str = f"{self.ts.strftime('%m/%d %H:%M:%S')}/"
        else:
            ts_str = ''

        if show_mem:
            mem_usage = f"{self.format_memory(self.memory_usage):>9}/"
        else:
            mem_usage = ''

        return f'{ts_str}{mem_usage}: {self.note}; details={self.details}\n'

    
    def asdict(self) -> typing.Dict[str, float]:
        return dataclasses.asdict(self)

    @staticmethod
    def format_memory(num_bytes: int, decimals: int = 2):
        ''' Get string representing memory quantity with correct units.
        '''
        if num_bytes >= 1e9:
            return f'{num_bytes/1e9:0.{decimals}f} GB'
        elif num_bytes >= 1e6:
            return f'{num_bytes/1e6:0.{decimals}f} MB'
        elif num_bytes >= 1e3:
            return f'{num_bytes*1e3:0.{decimals}f} kB'
        else:
            return f'{num_bytes:0.{decimals}f} Bytes'

class MemoryInfoNotAvailableError(BaseException):
    pass
    
@dataclasses.dataclass
class Stat:
    '''Records memory and cpu usage of target process.'''
    pid: int
    start_ts: datetime.datetime
    end_ts: datetime.datetime
    memory_info: psutil.pmem
    cpu: float
            
    @classmethod
    def capture_window(cls, process: psutil.Process, capture_time: datetime.timedelta):
        max_memory = 0
        max_info = None
        
        is_first = True
        start = datetime.datetime.utcnow()
        while is_first or (datetime.datetime.utcnow() - start < capture_time):
            memory_info = process.memory_info()
            
            if memory_info.rss > max_memory:
                max_memory = memory_info.rss
                max_info = memory_info
            is_first = False
        
        if max_info is None:
            raise MemoryInfoNotAvailableError(f'memory info not available: returned {process.memory_info()}')
        
        return cls(
            pid = process.pid,
            start_ts=start, 
            end_ts=datetime.datetime.utcnow(),
            memory_info=max_info,
            cpu=process.cpu_percent(),
        )
        
    def asdict(self) -> typing.Dict[str, float]:
        return dict(
            pid = self.pid,
            start_ts = self.start_ts,
            end_ts = self.end_ts,
            memory_usage = self.memory_usage,
            cpu = self.cpu,
        )
        
    
    @property
    def memory_usage(self):
        return self.memory_info.rss



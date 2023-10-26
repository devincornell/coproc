from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

from ..messenger import ResourceRequestedClose, PriorityMessenger
from ..workerresource import WorkerResource

from .monitormessenger import MonitorMessengerInterface, MonitorMessageType, SubmitNoteMessage, RequestStatsMessage, StatsDataMessage
from .statsresult import StatsResult

import datetime




import os



@dataclasses.dataclass
class Note:
    pid: int
    text: str
    ts: datetime.datetime
    memory_usage: int
    
    @classmethod
    def now(cls, process: psutil.Process, text: str, memory_usage: int):
        return cls(
            pid = process.pid,
            text=text, 
            ts=datetime.datetime.now(),
            memory_usage = memory_usage, # process.memory_info().rss
        )
    
    def asdict(self) -> typing.Dict[str, float]:
        return dataclasses.asdict(self)
    
import psutil
    
@dataclasses.dataclass
class Stat:
    pid: int
    start_ts: datetime.datetime
    end_ts: datetime.datetime
    memory_info: psutil.pmem
    cpu: float
            
    @classmethod
    def capture_window(cls, process: psutil.Process, capture_time: datetime.timedelta):
        max_memory = 0
        max_info = None
        
        start = datetime.datetime.utcnow()
        while datetime.datetime.utcnow() - start < capture_time:
            memory_info = process.memory_info()
            if memory_info.rss > max_memory:
                max_memory = memory_info.rss
                max_info = memory_info
        
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

@dataclasses.dataclass
class MonitorWorkerProcess:
    '''Simply receives data, processes it using worker_target, and sends the result back immediately.'''
    pid: int
    include_children: bool
    snapshot_seconds: float
    messenger: PriorityMessenger
    processes: typing.List[psutil.Process] = dataclasses.field(default_factory=list)
    notes: typing.List[Note] = dataclasses.field(default_factory=list)
    stats: typing.List[Stat] = dataclasses.field(default_factory=list)
    verbose: bool = False
    messages_received: int = 0
    
    def __call__(self):
        '''Main event loop for the process.
        '''
        print(f'starting main loop')
        
        self.stats.append(Stat.capture_window(
            process = self.root_process(), 
            capture_time = datetime.timedelta(seconds=self.snapshot_seconds),
        ))
        
        self.processes = self.get_processes()
        
        # main receive/send loop
        msg = None
        while True:
            
            try:
                msgs = self.messenger.receive_available()
            except ResourceRequestedClose:
                exit()
            
            for msg in msgs:
                if self.verbose: print(f'recv [{self.messages_received}]-->>', msg)
                if msg.mtype == MonitorMessageType.ADD_NOTE:
                    self.notes.append(Note.now(self.root_process(), msg.note, self.stats[-1].memory_usage))
                elif msg.mtype == MonitorMessageType.REQUEST_STATS:
                    self.messenger.send_reply(
                        StatsDataMessage(self.stats_result())
                    )
                else:
                    raise NotImplementedError(f'unknown message type: {msg.mtype}')
                    
                msg = None
            
            for p in self.processes:
                self.stats.append(Stat.capture_window(
                    process = p, 
                    capture_time = datetime.timedelta(seconds=self.snapshot_seconds)
                ))
    
    def get_processes(self) -> typing.List[psutil.Process]:
        root_process = self.root_process()
        processes = [root_process]
        
        if self.include_children:
            processes += [c for c in root_process.children(recursive=True)]
        return processes
    
    def root_process(self) -> psutil.Process:
        return psutil.Process(self.pid)
    
    def stats_result(self) -> StatsResult:
        return StatsResult(
            notes=self.get_notes_df(),
            stats=self.get_stats_df(),
        )
    
    def get_notes_df(self) -> pd.DataFrame:
        df = pd.DataFrame([n.asdict() for n in self.notes])
        if df.shape[0] > 0:
            df['monitor_time'] = df['ts'] - df['ts'].min()
            df['monitor_minutes'] = df['monitor_time'].map(lambda td: td.total_seconds()/60)
        return df
    
    def get_stats_df(self) -> pd.DataFrame:
        df = pd.DataFrame([s.asdict() for s in self.stats])
        if df.shape[0] > 0:
            df['monitor_time'] = df['end_ts'] - df['end_ts'].min()
            df['monitor_minutes'] = df['monitor_time'].map(lambda td: td.total_seconds()/60)
        return df
    
    @staticmethod
    def time_bin(dt: datetime.datetime, time_resolution: datetime.timedelta) -> datetime.datetime:
        return dt.timestamp()/time_resolution.total_seconds()

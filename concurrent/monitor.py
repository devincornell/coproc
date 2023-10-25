from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

from .workerprocess import BaseWorkerProcess, SendPayloadType, RecvPayloadType
#from .messenger import PriorityMessenger
from .messenger import ResourceRequestedClose, DataMessage
from .workerresource import WorkerResource
from .messenger import PriorityMessenger

# idk why
import enum
class MonitorMessageType(enum.Enum):
    ADD_NOTE = enum.auto()
    REQUEST_STATS = enum.auto()
    STATS_DATA = enum.auto()

class MonitorMessage:
    mtype: MonitorMessageType
    priority: float

@dataclasses.dataclass
class SubmitNoteMessage(MonitorMessage):
    '''Send generic data to the other end of the pipe, using priority of sent messsage.
    NOTE: this is designed to allow users to access benefits of user-defined queue.
    '''
    note: str
    priority: float = 0.0 # lower priority is more important
    mtype: MonitorMessageType = MonitorMessageType.ADD_NOTE
    
@dataclasses.dataclass
class RequestStatsMessage(MonitorMessage):
    priority: float = 0.0
    mtype: MonitorMessageType = MonitorMessageType.REQUEST_STATS
    
@dataclasses.dataclass
class StatsDataMessage(MonitorMessage):
    '''Send collected data to main process.'''
    notes: typing.List[Note]
    stats: typing.List[Stat]
    priority: float = 0.0
    mtype: MonitorMessageType = MonitorMessageType.STATS_DATA
    
#@dataclasses.dataclass
#class DataMessage(MonitorMessage):
#    payload: SendPayloadType
#    priority: float = 0.0
#    mtype: MonitorMessageType = MonitorMessageType.DATA

import datetime

@dataclasses.dataclass
class Note:
    text: str
    ts: datetime.datetime
    
    @classmethod
    def now(self, text: str):
        return self(text=text, ts=datetime.datetime.now())
    
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
class MonitorWorkerProcess(BaseWorkerProcess, typing.Generic[SendPayloadType, RecvPayloadType]):
    '''Simply receives data, processes it using worker_target, and sends the result back immediately.'''
    pid: int
    include_children: bool
    snapshot_seconds: float
    processes: typing.List[psutil.Process] = dataclasses.field(default_factory=list)
    notes: typing.List[Note] = dataclasses.field(default_factory=list)
    stats: typing.List[Stat] = dataclasses.field(default_factory=list)
    verbose: bool = False
    
    def __call__(self):
        '''Main event loop for the process.
        '''
        print(f'starting main loop')
        self.processes = self.get_processes()
        # main receive/send loop
        msg = None
        while True:
            try:
                msg = self.messenger.receive_data(blocking=False)
                if self.verbose: print(f'recv [{self.messages_received}]-->>', msg)
            except IndexError:
                #if self.verbose: print(f'[{self.pid}] no more messages')
                pass
            except ResourceRequestedClose:
                exit()
                
            if msg is not None:
                if msg.mtype == MonitorMessageType.ADD_NOTE:
                    self.notes.append(Note.now(msg.note))
                elif msg.mtype == MonitorMessageType.REQUEST_STATS:
                    self.messenger.send_reply(
                        StatsDataMessage(
                            notes=self.get_notes_df(),
                            stats=self.get_stats_df(),
                        )
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
        root_process = psutil.Process(self.pid)
        processes = [root_process]
        
        if self.include_children:
            processes += [c for c in root_process.children(recursive=True)]
        return processes

    
    def get_notes_df(self) -> pd.DataFrame:
        
        df = pd.DataFrame([n.asdict() for n in self.notes])
        if df.shape[0] == 0:
            return df
        
        #df['time_bin'] = df['ts'].map(lambda dt: self.time_bin(dt, time_resolution))
        #df['time_bin'] -= df['time_bin'].min()
        df['monitor_time'] = df['end_ts'] - df['end_ts'].min()
        df['monitor_minutes'] = df['monitor_time'].map(lambda td: td.total_seconds()/60)
        return df
    
    def get_stats_df(self) -> pd.DataFrame:
        df = pd.DataFrame([s.asdict() for s in self.stats])
        #df['time_bin'] = df['ts'].map(lambda dt: self.time_bin(dt, time_resolution))
        #df['pid'] = df.index.get_level_values('pid')
        #df['time_bin'] = df.index.get_level_values('time_bin')
        df['monitor_time'] = df['end_ts'] - df['end_ts'].min()
        df['monitor_minutes'] = df['monitor_time'].map(lambda td: td.total_seconds()/60)
        return df
    
    @staticmethod
    def time_bin(dt: datetime.datetime, time_resolution: datetime.timedelta) -> datetime.datetime:
        return dt.timestamp()/time_resolution.total_seconds()

import matplotlib.pyplot as plt
import plotnine

@dataclasses.dataclass
class StatsResult:
    stats: pd.DataFrame
    notes: pd.DataFrame
    
    @property
    def num_stats(self):
        return self.stats.shape[0]
    
    @property
    def num_notes(self):
        return self.notes.shape[0]
    
    def save_stats_plot(self, filename: str):
        #print(self.stats.columns)
        #print(self.stats)
        self.stats['memory_usage_gb'] = self.stats['memory_usage'] / 1e9
        p = (plotnine.ggplot(self.stats) 
            + plotnine.aes(x='monitor_minutes', y='memory_usage_gb', group='pid') + plotnine.geom_line()
            + plotnine.ggtitle(f'Memory Usage')
            + plotnine.labs(x='Time (minutes)', y='Memory Usage (GB)')
        )
        p.save(filename)
        return p
        
    def save_stats_pyplot(self, filename: str):
        fig, ax = plt.subplots()
        self.stats.plot(ax=ax)
        fig.savefig(filename)
        plt.close(fig)
        return fig

@dataclasses.dataclass
class MonitorMessengerInterface:
    messenger: PriorityMessenger
    
    def get_stats(self) -> typing.Tuple[pd.DataFrame,pd.DataFrame]:
        self.messenger.request_data(RequestStatsMessage())
        status_data: StatsDataMessage = self.messenger.receive_data(blocking=True)
        return StatsResult(
            stats = status_data.stats,
            notes = status_data.notes,
        )

import os

class Monitor:
    def __init__(self, pid: int = None, include_children: bool = True, snapshot_seconds: float = 0.5):
        self.snapshot_seconds = snapshot_seconds
        self.pid = pid if pid is not None else os.getpid()
        self.include_children = include_children
        self.res = WorkerResource(
            worker_process_type = MonitorWorkerProcess,
        )
    def __enter__(self):
        self.res.start(
            pid=self.pid, 
            include_children = self.include_children,
            snapshot_seconds = self.snapshot_seconds,
        )
        return MonitorMessengerInterface(self.res.messenger)
    
    def __exit__(self, *args):
        self.res.terminate(check_alive=False)


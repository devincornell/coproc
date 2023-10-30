from __future__ import annotations
import datetime
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

from .statsresult import StatsResult

if typing.TYPE_CHECKING:
    from ..messenger import PriorityMessenger
    from .monitor import Note, Stat

#import enum
#class MonitorMessageType(enum.Enum):
#    ADD_NOTE = enum.auto()
#    REQUEST_STATS = enum.auto()
#    STATS_DATA = enum.auto()
#    REQUEST_SAVE_FIG = enum.auto()

class MonitorMessage:
    #mtype: MonitorMessageType
    priority: float

@dataclasses.dataclass
class SubmitNoteMessage(MonitorMessage):
    '''Send generic data to the other end of the pipe, using priority of sent messsage.
    NOTE: this is designed to allow users to access benefits of user-defined queue.
    '''
    note: str
    details: str
    do_log: bool
    ts: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.now)
    priority: float = 0.0 # lower priority is more important
    #mtype: MonitorMessageType = MonitorMessageType.ADD_NOTE
    
@dataclasses.dataclass
class RequestStatsMessage(MonitorMessage):
    '''Host requests stats from worker.'''
    priority: float = 0.0
    #mtype: MonitorMessageType = MonitorMessageType.REQUEST_STATS
    
@dataclasses.dataclass
class StatsDataMessage(MonitorMessage):
    '''Worker sends collected data to host process.'''
    result: StatsResult
    priority: float = 0.0
    
    def __str__(self):
        return f'StatsDataMessage(stats={self.result.num_stats}, notes={self.result.num_notes})'
    #mtype: MonitorMessageType = MonitorMessageType.STATS_DATA

@dataclasses.dataclass
class RequestSaveMemoryFigureMessage(MonitorMessage):
    '''Host requests worker to save figure.'''
    fname: str
    include_notes: bool
    font_size: int
    save_kwargs: typing.Dict[str, typing.Any]
    priority: float = 0.0
    #mtype: MonitorMessageType = MonitorMessageType.REQUEST_SAVE_FIG
    
@dataclasses.dataclass
class UpdateChildProcessesMessage(MonitorMessage):
    '''Worker requests host to identify child processes.'''
    priority: float = 0.0
    


@dataclasses.dataclass
class MonitorMessengerInterface:
    '''Host-side interface for managing messages to/from worker process.'''
    messenger: PriorityMessenger
    
    def add_note(self, note: str, details: str = None, do_log: bool = True, do_print: bool = False):
        '''Send note to monitor.'''
        new_note = SubmitNoteMessage(
            note=note,
            details=details if details is not None else '',
            do_log=do_log,
        )
        self.messenger.send_norequest(new_note)
        if do_print:
            print(f'{new_note.note}; {new_note.details=}')
        
    def save_memory_plot(self, fname: str, font_size: int = 5, include_notes: bool = True, **save_kwargs):
        '''Request that monitor process save memory usage plot'''
        self.messenger.send_norequest(RequestSaveMemoryFigureMessage(
            fname=fname, 
            font_size=font_size,
            include_notes=include_notes,
            save_kwargs=save_kwargs,
        ))

    def get_stats(self) -> StatsResult:
        self.messenger.send_request(RequestStatsMessage())
        status_data: StatsDataMessage = self.messenger.receive_blocking()
        return status_data.result

    def update_child_processes(self):
        self.messenger.send_norequest(UpdateChildProcessesMessage())

from __future__ import annotations
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

import enum
class MonitorMessageType(enum.Enum):
    ADD_NOTE = enum.auto()
    REQUEST_STATS = enum.auto()
    STATS_DATA = enum.auto()
    REQUEST_SAVE_FIG = enum.auto()

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
    result: StatsResult
    priority: float = 0.0
    mtype: MonitorMessageType = MonitorMessageType.STATS_DATA

@dataclasses.dataclass
class RequestSaveFigureMessage(MonitorMessage):
    fname: str
    save_kwargs: typing.Dict[str, typing.Any]
    priority: float = 0.0
    mtype: MonitorMessageType = MonitorMessageType.REQUEST_SAVE_FIG

@dataclasses.dataclass
class MonitorMessengerInterface:
    messenger: PriorityMessenger
    
    def add_note(self, text: str):
        self.messenger.send_norequest(SubmitNoteMessage(note=text))
        
    def save_stats_plot(self, fname: str, **save_kwargs):
        self.messenger.send_norequest(RequestSaveFigureMessage(fname=fname, save_kwargs=save_kwargs))

    def get_stats(self) -> StatsResult:
        self.messenger.send_request(RequestStatsMessage())
        status_data: StatsDataMessage = self.messenger.receive_blocking()
        return status_data.result

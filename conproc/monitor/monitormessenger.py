from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

from .statusresult import StatsResult

if typing.TYPE_CHECKING:
    from ..messenger import PriorityMessenger
    from .monitor import Note, Stat

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

@dataclasses.dataclass
class MonitorMessengerInterface:
    messenger: PriorityMessenger
    
    def get_stats(self) -> StatsResult:
        self.messenger.send_request(RequestStatsMessage())
        status_data: StatsDataMessage = self.messenger.receive_data(blocking=True)
        return StatsResult(
            stats = status_data.stats,
            notes = status_data.notes,
        )


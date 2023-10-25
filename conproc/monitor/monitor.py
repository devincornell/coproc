from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

from .monitorprocess import MonitorWorkerProcess
from ..workerresource import WorkerResource
from .monitormessenger import MonitorMessengerInterface


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


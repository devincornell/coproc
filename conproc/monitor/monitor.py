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
    def __init__(self, 
        pid: int = None, 
        include_children: bool = True, 
        snapshot_seconds: float = 0.25,
        fig_fname: str = None,
        save_fig_freq: int = 10,
    ):
        #self.snapshot_seconds = snapshot_seconds
        #self.pid = pid if pid is not None else os.getpid()
        #self.include_children = include_children
        self.start_kwargs = dict(
            pid = pid if pid is not None else os.getpid(), 
            include_children = include_children,
            snapshot_seconds = snapshot_seconds,
            fig_fname = fig_fname,
            save_fig_freq = save_fig_freq,
        )
        self.res = WorkerResource(
            worker_process_type = MonitorWorkerProcess,
        )
    def __enter__(self):
        self.res.start(**self.start_kwargs)
        return MonitorMessengerInterface(self.res.messenger)
    
    def __exit__(self, *args):
        self.res.terminate(check_alive=False)


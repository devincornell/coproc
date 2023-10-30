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
import pathlib

class Monitor:
    def __init__(self, 
        pid: int = None, 
        snapshot_seconds: float = 0.25,
        include_children: bool = True, 
        log_path: pathlib.Path = None,
        fig_path: pathlib.Path = None,
        save_fig_freq: int = 10,
        verbose: bool = False,
    ):
        # all passed to the worker process before starting
        self.start_kwargs = dict(
            pid = pid if pid is not None else os.getpid(), 
            include_children = include_children,
            snapshot_seconds = snapshot_seconds,
            log_path = pathlib.Path(log_path) if log_path is not None else None,
            fig_path = pathlib.Path(fig_path) if fig_path is not None else None,
            save_fig_freq = save_fig_freq,
            verbose = verbose,
        )
        self.res = WorkerResource(
            worker_process_type = MonitorWorkerProcess,
        )
    def __enter__(self):
        self.res.start(**self.start_kwargs)
        return MonitorMessengerInterface(self.res.messenger)
    
    def __exit__(self, *args):
        self.res.terminate(check_alive=False)


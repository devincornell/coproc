from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

import matplotlib.pyplot as plt
import plotnine

if typing.TYPE_CHECKING:
    #from ..messenger import PriorityMessenger
    from .monitorprocess import Note, Stat

@dataclasses.dataclass
class StatsResult:
    #stats: pd.DataFrame
    #notes: pd.DataFrame
    stats: typing.List[Stat]
    notes: typing.List[Note]
    
    def notes_df(self):
        '''Return notes as a dataframe.'''
        df = pd.DataFrame([n.asdict() for n in self.notes if n.do_label])
        if df.shape[0] > 0:
            df['monitor_time'] = df['ts'] - df['ts'].min()
            df['monitor_minutes'] = df['monitor_time'].map(lambda td: td.total_seconds()/60)
        return df
    
    def stats_df(self):
        '''Return stats as a dataframe.'''
        df = pd.DataFrame([s.asdict() for s in self.stats])
        if df.shape[0] > 0:
            df['monitor_time'] = df['end_ts'] - df['end_ts'].min()
            df['monitor_minutes'] = df['monitor_time'].map(lambda td: td.total_seconds()/60)
        return df
    
    @property
    def has_results(self):
        return self.num_stats > 0
    
    @property
    def num_stats(self):
        return len(self.stats)
    
    @property
    def num_notes(self):
        return len(self.notes)
    
    def save_memory_plot(self, filename: str, font_size: int = 5, include_notes: bool = True, **save_kwargs):
        '''Save plot of memory usage with notes.'''
        p = self.plot_memory(font_size=font_size, include_notes=include_notes)
        p.save(str(filename), **save_kwargs)
        return p
    
    def plot_memory(self, font_size: int = 5, include_notes: bool = True):
        '''Plot memory usage against time, adding notes.'''
        stats_df = self.stats_df()
        stats_df['memory_usage_gb'] = stats_df['memory_usage'] / 1e9
        p = (plotnine.ggplot(stats_df) 
            + plotnine.aes(x='monitor_minutes', y='memory_usage_gb', group='pid') 
            + plotnine.geom_line()
            + plotnine.ggtitle(f'Memory Usage')
            + plotnine.labs(x='Time (minutes)', y='Memory Usage (GB)')
        )
        
        if include_notes and self.num_notes > 0:
            notes_df = self.notes_df()
            notes_df['memory_usage_gb'] = notes_df['memory_usage'] / 1e9
            p = (p 
                + plotnine.geom_label(
                    data = notes_df,
                    mapping = plotnine.aes(
                        x='monitor_minutes', 
                        y='memory_usage_gb', 
                        label='note'
                    ),
                    size=font_size,
                )
            )
        return p
        

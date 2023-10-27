from __future__ import annotations
import typing
import dataclasses
import multiprocessing
import multiprocessing.connection
import multiprocessing.context
import pandas as pd

import matplotlib.pyplot as plt
import plotnine

@dataclasses.dataclass
class StatsResult:
    stats: pd.DataFrame
    notes: pd.DataFrame
    
    @property
    def has_results(self):
        return self.num_stats > 0
    
    @property
    def num_stats(self):
        return self.stats.shape[0]
    
    @property
    def num_notes(self):
        return self.notes.shape[0]
    
    def get_stats_plot(self, font_size: int = 5):
        self.stats['memory_usage_gb'] = self.stats['memory_usage'] / 1e9
        p = (plotnine.ggplot(self.stats) 
            + plotnine.aes(x='monitor_minutes', y='memory_usage_gb', group='pid') + plotnine.geom_line()
            + plotnine.ggtitle(f'Memory Usage')
            + plotnine.labs(x='Time (minutes)', y='Memory Usage (GB)')
        )
        
        if True and self.num_notes > 0:
            self.notes['memory_usage_gb'] = self.notes['memory_usage'] / 1e9
            p = (p 
                + plotnine.geom_label(
                    data = self.notes,
                    mapping = plotnine.aes(x='monitor_minutes', y='memory_usage_gb', label='text'),
                    size=font_size,
                )
            )
        return p
        
    def save_stats_plot(self, filename: str, font_size: int = 5, **kwargs):
        p = self.get_stats_plot(font_size=font_size)
        p.save(filename)
        return p
        
    def save_stats_pyplot(self, filename: str):
        fig, ax = plt.subplots()
        self.stats.plot(ax=ax)
        fig.savefig(filename)
        plt.close(fig)
        return fig

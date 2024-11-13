import typing
import dataclasses
from ..messenger import PriorityMessenger


@dataclasses.dataclass
class WorkerProcessWrapper:
    target: typing.Callable[[PriorityMessenger], None]
    messenger: PriorityMessenger
    worker_kwargs: dict[str,typing.Any]

    def __call__(self):
        return self.target(self.messenger, **self.worker_kwargs)

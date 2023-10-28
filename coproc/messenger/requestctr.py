import collections
import dataclasses
import typing

from .queue import ChannelID


@dataclasses.dataclass
class RequestCtr:
    requests: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    replies: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    
    def remaining(self, channel_id: ChannelID) -> int:
        return self.requests[channel_id] - self.replies[channel_id]
    
    def sent_request(self, channel_id: ChannelID):
        self.requests[channel_id] += 1
        
    def received_reply(self, channel_id: ChannelID):
        self.replies[channel_id] += 1
    


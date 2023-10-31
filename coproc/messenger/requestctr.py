import collections
import dataclasses
import typing

from .queue import ChannelID


@dataclasses.dataclass
class RequestCtr:
    '''Counter stats for messages.'''
    requests: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    replies: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    sent: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    received: collections.Counter[ChannelID] = dataclasses.field(default_factory=collections.Counter)
    
    ##################### Getting values #####################
    def remaining(self, channel_id: ChannelID) -> int:
        return self.requests[channel_id] - self.replies[channel_id]
    
    def replies_received(self, channel_id: ChannelID) -> int:
        return self.replies[channel_id]
    
    def requests_sent(self, channel_id: ChannelID) -> int:
        return self.requests[channel_id]
    
    def messages_sent(self, channel_id: ChannelID) -> int:
        return self.sent[channel_id]
    
    def messages_received(self, channel_id: ChannelID) -> int:
        return self.received[channel_id]
    
    ##################### Setting values #####################
    
    def sent_request(self, channel_id: ChannelID):
        self.requests[channel_id] += 1
        #self.sent_message(channel_id)
        
    def received_reply(self, channel_id: ChannelID):
        self.replies[channel_id] += 1
        #self.received_message(channel_id)
        
    def sent_message(self, channel_id: ChannelID):
        self.sent[channel_id] += 1
        
    def received_message(self, channel_id: ChannelID):
        self.received[channel_id] += 1
    


from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .rcp_app import WebTransportStreamReadEvent , WebTransportStreamWriteEvent

class Writer(ABC):
    "Webtransport Stream Writer"
    def __init__(self):
        self._closed:bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    @abstractmethod
    async def write(self,event:WebTransportStreamWriteEvent) -> None:
        """Write events to stream"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Stop and close writing on stream"""
        ...


class Reader(ABC):
    "Webtransport Stream Reader"
    def __init__(self):
        self._closed:bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed
 
    @abstractmethod
    async def read(self,event:WebTransportStreamWriteEvent) -> WebTransportStreamReadEvent:
        """read events from stream"""
        ...
 
    @abstractmethod
    async def close(self) -> None:
        """Stop and close writing on stream"""
        ...
        
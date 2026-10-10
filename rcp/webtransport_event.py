from __future__ import annotations

from .types import (
    WebTransportConnectionEventType,
    WebTransportUnidirectionalStreamEventType,
    WebTransportBidirectionalStreamEventType,
    WebTransportDatagramEventType,
    WebTransportDataEventType,
)

from collections.abc import Iterable
from typing import Literal, NotRequired, TypedDict


Headers = Iterable[tuple[bytes, bytes]]


# WebTransport session events

class WebTransportSessionAccept(TypedDict):
    """Indicates that the WebTransport session has been accepted."""
    type: Literal[WebTransportConnectionEventType.ACCEPT]
    headers: NotRequired[Headers]


class WebTransportSessionReject(TypedDict):
    """Indicates that the WebTransport session has been rejected."""
    type: Literal[WebTransportConnectionEventType.REJECT]
    status: int


class WebTransportSessionClose(TypedDict):
    """Indicates that the local endpoint is closing the session."""
    type: Literal[WebTransportConnectionEventType.CLOSE]
    error_code: NotRequired[int]
    reason: NotRequired[str | None]


class WebTransportSessionDisconnect(TypedDict):
    """Indicates that the session has been disconnected."""
    type: Literal[WebTransportConnectionEventType.DISCONNECT]
    code: int
    reason: NotRequired[str | None]


# WebTransport unidirectional stream events

class WebTransportClientUnidirectionalStreamStarted(TypedDict):
    """Fires when a client-initiated unidirectional stream starts.

    Provides a reader for receiving data from the client.
    """
    type: Literal[WebTransportUnidirectionalStreamEventType.CLIENT]
    reader: None


class WebTransportCreateServerUnidirectionalStream(TypedDict):
    """Requests the creation of a server-initiated unidirectional
    stream and provides a writer for sending data to the client
    without requiring a client request.
    """
    type: Literal[WebTransportUnidirectionalStreamEventType.SERVER]


# WebTransport bidirectional stream events

class WebTransportClientBidirectionalStreamStarted(TypedDict):
    """Fires when a client-initiated bidirectional stream starts.

    Provides a reader and a writer for receiving and sending data.
    """
    type: Literal[WebTransportBidirectionalStreamEventType.CLIENT]
    reader: None
    writer: None


class WebTransportCreateServerBidirectionalStream(TypedDict):
    """Requests the creation of a server-initiated bidirectional
    stream and provides a reader and a writer for receiving and
    sending data.
    """
    type: Literal[WebTransportBidirectionalStreamEventType.SERVER]


# WebTransport stream data events

class WebTransportDataReceived(TypedDict):
    """Fires when data is received from the client on a stream.

    Must be emitted only by stream readers.
    """
    type: Literal[WebTransportDataEventType.RECEIVED]
    data: bytes


class WebTransportDataSend(TypedDict):
    """Fires when the application requests that data be sent
    to the client on a server-writable stream.

    Must be emitted only by stream writers.
    """
    type: Literal[WebTransportDataEventType.SEND]
    data: bytes


# WebTransport datagram events

class WebTransportDatagramReceived(TypedDict):
    """Fires when a datagram is received from the client."""
    type: Literal[WebTransportDatagramEventType.RECEIVED]
    data: bytes


class WebTransportDatagramSend(TypedDict):
    """Fires when the application requests that a datagram
    be sent to the client.
    """
    type: Literal[WebTransportDatagramEventType.SEND]
    data: bytes

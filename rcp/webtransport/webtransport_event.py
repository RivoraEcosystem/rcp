from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

from ..types import (
    WebTransportBidirectionalStreamEventType,
    WebTransportConnectionEventType,
    WebTransportDataEventType,
    WebTransportDatagramEventType,
    WebTransportStreamTerminationEventType,
    WebTransportUnidirectionalStreamEventType,
)

if TYPE_CHECKING:
    from .webtransport_stream_utils import (
        WebTransportStreamReceiveCallable,
        WebTransportStreamSendCallable,
    )


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
    """Requests that the WebTransport session be closed."""

    type: Literal[WebTransportConnectionEventType.CLOSE]
    error_code: NotRequired[int]
    reason: NotRequired[str | None]


class WebTransportSessionDisconnect(TypedDict):
    """Notifies the application that the client has disconnected."""

    type: Literal[WebTransportConnectionEventType.DISCONNECT]
    code: int
    reason: NotRequired[str | None]


# WebTransport unidirectional stream events


class WebTransportClientUnidirectionalStreamStarted(TypedDict):
    """Fires when a client-initiated unidirectional stream starts.

    Provides a receiver and sender for receiving data in events from the client.
    """

    type: Literal[WebTransportUnidirectionalStreamEventType.CLIENT]
    receiver: WebTransportStreamReceiveCallable
    sender: WebTransportStreamSendCallable


class WebTransportCreateServerUnidirectionalStream(TypedDict):
    """Requests the creation of a server-initiated unidirectional
    stream and provides a (receiver,sender) tuple for sending data in events to the client
    without requiring a client request.
    """

    type: Literal[WebTransportUnidirectionalStreamEventType.SERVER]


# WebTransport bidirectional stream events


class WebTransportClientBidirectionalStreamStarted(TypedDict):
    """Fires when a client-initiated bidirectional stream starts.

    Provides a receiver and a sender for receiving and sending data in events.
    """

    type: Literal[WebTransportBidirectionalStreamEventType.CLIENT]
    receiver: WebTransportStreamReceiveCallable
    sender: WebTransportStreamSendCallable


class WebTransportCreateServerBidirectionalStream(TypedDict):
    """Requests the creation of a server-initiated bidirectional
    stream and provides a (receiver,sender) tuple for receiving and
    sending data in events.
    """

    type: Literal[WebTransportBidirectionalStreamEventType.SERVER]


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


# WebTransport stream data events


class WebTransportDataReceived(TypedDict):
    """Fires when data is received from the client on a stream.

    Must be emitted only by stream receivers.
    """

    type: Literal[WebTransportDataEventType.RECEIVED]
    data: bytes
    receiving_ended: NotRequired[bool]


class WebTransportDataSend(TypedDict):
    """Fires when the application requests that data be sent
    to the client on a server-writable stream.

    Must be emitted only by stream senders.
    """

    type: Literal[WebTransportDataEventType.SEND]
    data: bytes
    sending_ended: NotRequired[bool]


# WebTransport stream termination and direction-control events


class WebTransportStreamDisconnected(TypedDict):
    """Fires when the stream has been terminated in both directions, or in its
    available direction for a unidirectional stream.

    The error code is 0 when termination had no error.
    """

    type: Literal[WebTransportStreamTerminationEventType.DISCONNECT]
    error_code: NotRequired[int]


class WebTransportStreamClose(TypedDict):
    """Requests termination of the stream in both directions, or in its
    available direction for a unidirectional stream.

    The error code is 0 when termination has no error.
    """

    type: Literal[WebTransportStreamTerminationEventType.CLOSE]
    error_code: NotRequired[int]


class WebTransportStreamStopReceive(TypedDict):
    """Requests sending to stop on the application's receiving side.

    The error code is 0 when stopping has no error.
    """

    type: Literal[WebTransportStreamTerminationEventType.STOP_RECEIVE]
    error_code: NotRequired[int]


class WebTransportStreamSendingStopped(TypedDict):
    """Fires when the client requested stopping on the application's sending side.

    The error code is 0 when stopping had no error.
    """

    type: Literal[WebTransportStreamTerminationEventType.SENDING_STOPPED]
    error_code: NotRequired[int]

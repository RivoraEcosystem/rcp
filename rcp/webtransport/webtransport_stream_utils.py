from collections.abc import Awaitable, Callable

from .webtransport_event import (
    WebTransportDataReceived,
    WebTransportDataSend,
    WebTransportStreamClose,
    WebTransportStreamDisconnected,
    WebTransportStreamSendingStopped,
    WebTransportStreamStopReceive,
)

WebTransportStreamReceiveEvents = (
    WebTransportDataReceived
    | WebTransportStreamDisconnected
    | WebTransportStreamSendingStopped
)

WebTransportStreamSendEvents = (
    WebTransportDataSend | WebTransportStreamClose | WebTransportStreamStopReceive
)

WebTransportStreamReceiveCallable = Callable[
    [], Awaitable[WebTransportStreamReceiveEvents]
]

WebTransportStreamSendCallable = Callable[
    [WebTransportStreamSendEvents], Awaitable[None]
]

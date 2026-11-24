from collections.abc import Awaitable, Callable

from .webtransport_event import WebTransportDatagramReceived, WebTransportDatagramSend

WebTransportDatagramReceiveEvents = WebTransportDatagramReceived
WebTransportDatagramSendEvents = WebTransportDatagramSend
WebTransportDatagramReceiveCallable = Callable[
    [], Awaitable[WebTransportDatagramReceiveEvents]
]
WebTransportDatagramSendCallable = Callable[
    [WebTransportDatagramSendEvents], Awaitable[None]
]

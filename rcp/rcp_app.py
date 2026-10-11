from .events import (
    HTTPRequestEvent,
    HTTPResponseDebugEvent,
    HTTPResponseStartEvent,
    HTTPResponseBodyEvent,
    HTTPResponseTrailersEvent,
    HTTPDisconnectEvent,
    LifespanStartupEvent,
    LifespanShutdownEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupFailedEvent,
    LifespanShutdownCompleteEvent,
    LifespanShutdownFailedEvent
)
from .webtransport_event import (
    WebTransportDatagramReceived,
    WebTransportClientBidirectionalStreamStarted,
    WebTransportClientUnidirectionalStreamStarted,
    WebTransportSessionDisconnect,
    WebTransportDatagramSend,
    WebTransportCreateServerBidirectionalStream,
    WebTransportCreateServerUnidirectionalStream,
    WebTransportSessionClose,
    WebTransportSessionReject,
    WebTransportSessionAccept,
    WebTransportDataReceived,
    WebTransportDataSend
)
from .scopes import (
    HTTPScope,
    LifespanScope
)
from collections.abc import Callable, Awaitable
from .stream_utils import Writer , Reader

Scope = HTTPScope | LifespanScope

LifespanReceiveEvents = (
    LifespanStartupEvent
    | LifespanShutdownEvent
)

LifespanSendEvents = (
    LifespanStartupCompleteEvent
    | LifespanStartupFailedEvent
    | LifespanShutdownCompleteEvent
    | LifespanShutdownFailedEvent
)

HTTPReceiveEvents = (
    HTTPRequestEvent
    | HTTPDisconnectEvent
)

HTTPSendEvents = (
    HTTPResponseStartEvent
    | HTTPResponseBodyEvent
    | HTTPResponseTrailersEvent
    | HTTPDisconnectEvent
    | HTTPResponseDebugEvent
)

WebtransportReceiveEvent = (
    WebTransportDatagramReceived
    |WebTransportClientBidirectionalStreamStarted
    |WebTransportClientUnidirectionalStreamStarted
    |WebTransportSessionDisconnect
)

WebtransportSendEvent = (
    WebTransportDatagramSend
    |WebTransportCreateServerBidirectionalStream
    |WebTransportCreateServerUnidirectionalStream
    |WebTransportSessionClose
    |WebTransportSessionReject
    |WebTransportSessionAccept
)

WebTransportStreamReadEvent = (
    WebTransportDataReceived
)

WebTransportStreamWriteEvent = (
    WebTransportDataSend
)

RCPReceiveEvent = (
    HTTPReceiveEvents
    |LifespanReceiveEvents
    |WebtransportReceiveEvent
)

RCPSendEvent = (
    HTTPSendEvents
    |LifespanSendEvents
    |WebtransportSendEvent
)

RCPReceiveCallable = Callable[[], Awaitable[RCPReceiveEvent]]
RCPSendCallable = Callable[[RCPSendEvent], Awaitable[None|tuple[Writer,Reader]]]

RCPApplication = Callable[
    [Scope, RCPReceiveCallable, RCPSendCallable]
    , Awaitable[None]
]

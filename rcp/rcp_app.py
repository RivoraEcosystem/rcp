from collections.abc import Awaitable, Callable

from .http.events import (
    HTTPDisconnectEvent,
    HTTPRequestEvent,
    HTTPResponseBodyEvent,
    HTTPResponseDebugEvent,
    HTTPResponseStartEvent,
    HTTPResponseTrailersEvent,
)    
from .lifespan.events import (
    LifespanShutdownCompleteEvent,
    LifespanShutdownEvent,
    LifespanShutdownFailedEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupEvent,
    LifespanStartupFailedEvent,
)

from .scopes import HTTPScope, LifespanScope, WebTransportScope
from .webtransport.webtransport_stream_utils import Reader, Writer
from .webtransport.webtransport_event import (
    WebTransportClientBidirectionalStreamStarted,
    WebTransportClientUnidirectionalStreamStarted,
    WebTransportCreateServerBidirectionalStream,
    WebTransportCreateServerUnidirectionalStream,
    WebTransportDatagramReceived,
    WebTransportDatagramSend,
    WebTransportSessionAccept,
    WebTransportSessionClose,
    WebTransportSessionDisconnect,
    WebTransportSessionReject,
)

Scope = HTTPScope | LifespanScope | WebTransportScope

LifespanReceiveEvents = LifespanStartupEvent | LifespanShutdownEvent

LifespanSendEvents = (
    LifespanStartupCompleteEvent
    | LifespanStartupFailedEvent
    | LifespanShutdownCompleteEvent
    | LifespanShutdownFailedEvent
)

HTTPReceiveEvents = HTTPRequestEvent | HTTPDisconnectEvent

HTTPSendEvents = (
    HTTPResponseStartEvent
    | HTTPResponseBodyEvent
    | HTTPResponseTrailersEvent
    | HTTPDisconnectEvent
    | HTTPResponseDebugEvent
)

WebtransportReceiveEvent = (
    WebTransportDatagramReceived
    | WebTransportClientBidirectionalStreamStarted
    | WebTransportClientUnidirectionalStreamStarted
    | WebTransportSessionDisconnect
)

WebtransportSendEvent = (
    WebTransportDatagramSend
    | WebTransportCreateServerBidirectionalStream
    | WebTransportCreateServerUnidirectionalStream
    | WebTransportSessionClose
    | WebTransportSessionReject
    | WebTransportSessionAccept
)

RCPReceiveEvent = HTTPReceiveEvents | LifespanReceiveEvents | WebtransportReceiveEvent

RCPSendEvent = HTTPSendEvents | LifespanSendEvents | WebtransportSendEvent

RCPReceiveCallable = Callable[[], Awaitable[RCPReceiveEvent]]
RCPSendCallable = Callable[
    [RCPSendEvent], Awaitable[None | Writer | tuple[Writer, Reader]]
]

RCPApplication = Callable[[Scope, RCPReceiveCallable, RCPSendCallable], Awaitable[None]]

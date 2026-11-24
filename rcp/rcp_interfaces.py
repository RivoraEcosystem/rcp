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
from .webtransport.webtransport_event import (
    WebTransportClientBidirectionalStreamStarted,
    WebTransportClientUnidirectionalStreamStarted,
    WebTransportCreateServerBidirectionalStream,
    WebTransportCreateServerUnidirectionalStream,
    WebTransportSessionAccept,
    WebTransportSessionClose,
    WebTransportSessionDisconnect,
    WebTransportSessionReject,
)
from .webtransport.webtransport_stream_utils import (
    WebTransportStreamReceiveCallable,
    WebTransportStreamSendCallable,
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
    WebTransportClientBidirectionalStreamStarted
    | WebTransportClientUnidirectionalStreamStarted
    | WebTransportSessionDisconnect
)

WebtransportSendEvent = (
    WebTransportCreateServerBidirectionalStream
    | WebTransportCreateServerUnidirectionalStream
    | WebTransportSessionClose
    | WebTransportSessionReject
    | WebTransportSessionAccept
)

RCPReceiveEvent = HTTPReceiveEvents | LifespanReceiveEvents | WebtransportReceiveEvent

RCPSendEvent = HTTPSendEvents | LifespanSendEvents | WebtransportSendEvent

RCPReceiveCallable = Callable[[], Awaitable[RCPReceiveEvent]]
RCPSendCallable = Callable[
    [RCPSendEvent],
    Awaitable[
        None | tuple[WebTransportStreamReceiveCallable, WebTransportStreamSendCallable]
    ],
]

RCPApplication = Callable[[Scope, RCPReceiveCallable, RCPSendCallable], Awaitable[None]]

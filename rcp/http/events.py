from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, NotRequired, TypedDict

from ..types import (
    HTTPConnectionEventType,
    HTTPResponseEventType,
)

Headers = Iterable[tuple[bytes, bytes]]


class HTTPRequestEvent(TypedDict):
    type: Literal[HTTPConnectionEventType.REQUEST]
    body: bytes
    more_body: bool


class HTTPResponseDebugEvent(TypedDict):
    type: Literal[HTTPResponseEventType.DEBUG]
    info: dict[str, object]


class HTTPResponseStartEvent(TypedDict):
    type: Literal[HTTPResponseEventType.START]
    status: int
    headers: NotRequired[Headers]
    trailers: NotRequired[bool]


class HTTPResponseBodyEvent(TypedDict):
    type: Literal[HTTPResponseEventType.BODY]
    body: bytes
    more_body: NotRequired[bool]


class HTTPResponseTrailersEvent(TypedDict):
    type: Literal[HTTPResponseEventType.TRAILERS]
    headers: Headers
    more_trailers: bool


class HTTPDisconnectEvent(TypedDict):
    type: Literal[HTTPConnectionEventType.DISCONNECT]
    reason: NotRequired[str]
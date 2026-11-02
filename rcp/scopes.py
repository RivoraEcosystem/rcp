from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, NotRequired, TypedDict

from .methods import RequestMethod
from .rcp import RCP
from .scheme import HTTPScheme
from .types import HTTPVersions, ScopeType

Headers = Iterable[tuple[bytes, bytes]]


class HTTPScope(TypedDict):
    type: Literal[ScopeType.HTTP]
    rcp: RCP
    http_version: HTTPVersions
    method: RequestMethod
    scheme: HTTPScheme
    authority: str | None
    path: str
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: Headers
    client: tuple[str, int] | None
    server: tuple[str, int | None] | None
    state: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, dict[object, object]]]


class LifespanScope(TypedDict):
    type: Literal[ScopeType.LIFESPAN]
    rcp: RCP
    state: NotRequired[dict[str, Any]]


class WebTransportScope(TypedDict):
    type: Literal[ScopeType.WEBTRANSPORT]
    rcp: RCP
    http_version: Literal[HTTPVersions.HTTP3]
    method: RequestMethod
    scheme: HTTPScheme
    authority: str | None
    path: str
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: Headers
    client: tuple[str, int] | None
    server: tuple[str, int | None] | None
    state: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, dict[object, object]]]

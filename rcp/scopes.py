from __future__ import annotations

from .types import ScopeType, HTTPVersions
from .methods import RequestMethod
from typing import NotRequired ,Any, Literal, TypedDict
from collections.abc import Iterable
from .rcp import RCP
from .scheme import HTTPScheme

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
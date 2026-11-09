from typing import Literal, TypedDict

from ..types import LifespanEventType


class LifespanStartupEvent(TypedDict):
    type: Literal[LifespanEventType.STARTUP]


class LifespanShutdownEvent(TypedDict):
    type: Literal[LifespanEventType.SHUTDOWN]


class LifespanStartupCompleteEvent(TypedDict):
    type: Literal[LifespanEventType.STARTUP_COMPLETE]


class LifespanStartupFailedEvent(TypedDict):
    type: Literal[LifespanEventType.STARTUP_FAILED]
    message: str


class LifespanShutdownCompleteEvent(TypedDict):
    type: Literal[LifespanEventType.SHUTDOWN_COMPLETE]


class LifespanShutdownFailedEvent(TypedDict):
    type: Literal[LifespanEventType.SHUTDOWN_FAILED]
    message: str

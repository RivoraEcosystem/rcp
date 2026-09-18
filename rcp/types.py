from enum import StrEnum
    
# Scope types used when creating a new scope.
class ScopeType(StrEnum):
    HTTP = "http"
    LIFESPAN = "lifespan"
    
    # Reserved for future RCP versions
    WEBTRANSPORT = "webtransport"

# HTTP events sent after the HTTP scope is created.
class HTTPConnectionEventType(StrEnum):
    REQUEST = "http.request"
    DISCONNECT = "http.disconnect"

# HTTP response event types.
class HTTPResponseEventType(StrEnum):
    START = "http.response.start"
    BODY = "http.response.body"
    TRAILERS = "http.response.trailers"
    DEBUG = "http.response.debug"

# Lifespan event types.
class LifespanEventType(StrEnum):
    STARTUP = "lifespan.startup"
    SHUTDOWN = "lifespan.shutdown"
    STARTUP_COMPLETE = "lifespan.startup.complete"
    STARTUP_FAILED = "lifespan.startup.failed"
    SHUTDOWN_COMPLETE = "lifespan.shutdown.complete"
    SHUTDOWN_FAILED = "lifespan.shutdown.failed"

# HTTP protocol versions used by RCP.
class HTTPVersions(StrEnum):
    HTTP3 = "3"
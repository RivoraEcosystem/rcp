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

# Webtransport Session Lifespan events
class WebTransportConnectionEventType(StrEnum):
    ACCEPT = "webtransport.accept"
    REJECT = "webtransport.reject"
    CLOSE = "webtransport.close"
    DISCONNECT = "webtransport.disconnect"

# Webtransport unidirectional stream events
class WebTransportUnidirectionalStreamEventType(StrEnum):
    CLIENT = "webtransport.unidirectional.client" # client side unidirectional stream started
    SERVER = "webtransport.unidirectional.server" # create server side unidirectional stream

# Webtransport bidirectional stream events
class WebTransportBidirectionalStreamEventType(StrEnum):
    CLIENT = "webtransport.bidirectional.client" # client side bidirectional stream started
    SERVER = "webtransport.bidirectional.server" # create server side bidirectional stream

# Webtransport Datagram events 
class WebTransportDatagramEventType(StrEnum):
    RECEIVE = "webtransport.datagram.receive"
    SEND = "webtransport.datagram.send"

# Webtransport stream message event 
class WebTransportMessageEventType(StrEnum):
    RECEIVE = "webtransport.message.receive"
    SEND = "webtransport.message.send"
    
# HTTP protocol versions used by RCP.
class HTTPVersions(StrEnum):
    HTTP3 = "3"
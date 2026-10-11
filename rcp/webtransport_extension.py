from .types import (
    WebTransportDatagramEventType,
    WebTransportDataEventType,
    WebTransportUnidirectionalStreamEventType,
    WebTransportBidirectionalStreamEventType,
    WebTransportConnectionEventType
)

WEBTRANSPORT_EXTENSION = {
    "webtransport": {
        "features": {
            "datagrams": True,
            "unidirectional_streams": True,
            "bidirectional_streams": True,
        },
        "send_event_type": {
            WebTransportDatagramEventType.SEND: True,
            WebTransportBidirectionalStreamEventType.SERVER: True,
            WebTransportUnidirectionalStreamEventType.SERVER: True,
            WebTransportConnectionEventType.CLOSE: True,
            WebTransportConnectionEventType.REJECT: True,
            WebTransportConnectionEventType.ACCEPT: True,
        },
        "receive_event_type": {
            WebTransportDatagramEventType.RECEIVED: True,
            WebTransportBidirectionalStreamEventType.CLIENT: True,
            WebTransportUnidirectionalStreamEventType.CLIENT: True,
            WebTransportConnectionEventType.DISCONNECT: True,
        },
        "stream_event": {
            WebTransportDataEventType.RECEIVED: True,
            WebTransportDataEventType.SEND: True,
        },
    }
}
# WebTransport Guide

> **Development status:** RCP is currently in Alpha and is not considered stable while WebTransport is under development. HTTP/3 events are stable; WebTransport events may change during development.

WebTransport support is defined by **RCP version 2.0** and must only be used with RCP version 2.0.

```python
{
    "version": RCPVersions.VERSION_2,
}
```

* A `webtransport` scope must carry `scope["rcp"]["version"] == RCPVersions.VERSION_2`.
* A server that implements only RCP 1.0 must not create WebTransport scopes.
* WebTransport events, streams, readers, and writers must not be used in RCP 1.0 applications.
* RCP 2.0 includes everything defined by RCP 1.0.

WebTransport runs over HTTP/3. The session is established with an HTTP/3 Extended CONNECT request whose `:protocol` pseudo-header is `webtransport`. The server processes `:protocol` using `H3_EXTENSION_PSEUDO_HEADERS`.

A WebTransport session provides:

| Feature                | Description                                                   |
| ---------------------- | ------------------------------------------------------------- |
| Datagrams              | Unreliable, unordered messages in both directions.            |
| Unidirectional streams | Reliable ordered streams carrying data in one direction.      |
| Bidirectional streams  | Reliable ordered streams carrying data in both directions.    |

---

## WebTransport Session Isolation

Each WebTransport session has its own:

* WebTransport scope
* receive and send events
* datagrams
* streams, stream readers, and stream writers
* session lifecycle
* disconnect state

Events and streams belonging to one session must not be delivered to another session.

The termination of one session must not terminate unrelated sessions or HTTP streams on the same QUIC connection.

```text
                    QUIC Connection
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   HTTP/3 request   WebTransport      WebTransport
                      Session A         Session B
          │                │                │
          ▼                ▼                ▼
    HTTP Scope       WebTransport     WebTransport
                        Scope A          Scope B
                           │                │
                  ┌────────┼────────┐       ▼
                  ▼        ▼        ▼   Application
               Datagrams Streams  Readers/
                                  Writers
```

---

## WebTransport Event Types

Event type strings are defined by the following enums:

```python
class WebTransportConnectionEventType(StrEnum):
    ACCEPT = "webtransport.accept"
    REJECT = "webtransport.reject"
    CLOSE = "webtransport.close"
    DISCONNECT = "webtransport.disconnect"


class WebTransportUnidirectionalStreamEventType(StrEnum):
    CLIENT = "webtransport.unidirectional.client"
    SERVER = "webtransport.unidirectional.server"


class WebTransportBidirectionalStreamEventType(StrEnum):
    CLIENT = "webtransport.bidirectional.client"
    SERVER = "webtransport.bidirectional.server"


class WebTransportDatagramEventType(StrEnum):
    RECEIVED = "webtransport.datagram.received"
    SEND = "webtransport.datagram.send"


class WebTransportDataEventType(StrEnum):
    RECEIVED = "webtransport.data.received"
    SEND = "webtransport.data.send"
```

### Events at a glance

Events exchanged through `receive` and `send`:

| Direction                | Event                                              | Type string                            |
| ------------------------ | -------------------------------------------------- | -------------------------------------- |
| Server → Application     | `WebTransportDatagramReceived`                     | `webtransport.datagram.received`       |
| Server → Application     | `WebTransportClientUnidirectionalStreamStarted`    | `webtransport.unidirectional.client`   |
| Server → Application     | `WebTransportClientBidirectionalStreamStarted`     | `webtransport.bidirectional.client`    |
| Server → Application     | `WebTransportSessionDisconnect`                    | `webtransport.disconnect`              |
| Application → Server     | `WebTransportSessionAccept`                        | `webtransport.accept`                  |
| Application → Server     | `WebTransportSessionReject`                        | `webtransport.reject`                  |
| Application → Server     | `WebTransportSessionClose`                         | `webtransport.close`                   |
| Application → Server     | `WebTransportDatagramSend`                         | `webtransport.datagram.send`           |
| Application → Server     | `WebTransportCreateServerUnidirectionalStream`     | `webtransport.unidirectional.server`   |
| Application → Server     | `WebTransportCreateServerBidirectionalStream`      | `webtransport.bidirectional.server`    |

Events exchanged through stream readers and writers (not through `receive` / `send`):

| Direction                | Event                          | Type string                    |
| ------------------------ | ------------------------------ | ------------------------------ |
| Reader → Application     | `WebTransportDataReceived`     | `webtransport.data.received`   |
| Application → Writer     | `WebTransportDataSend`         | `webtransport.data.send`       |

The corresponding type aliases are:

```python
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

WebTransportStreamReadEvent = WebTransportDataReceived
WebTransportStreamWriteEvent = WebTransportDataSend
```

---

## WebTransport Session Events

### `WebTransportSessionAccept`

Sent by the application to accept the session.

```python
{
    "type": "webtransport.accept",
    "headers": [
        (b"x-example", b"value"),
    ],
}
```

| Field     | Description                                |
| --------- | ------------------------------------------ |
| `type`    | Event type.                                |
| `headers` | Optional response headers.                 |

The server completes the WebTransport handshake when it receives this event. Response headers follow the [Response Header Validation](http3.md#response-header-validation) rules.

### Receive and send before acceptance

Before acceptance, the application may send only `webtransport.accept` or `webtransport.reject`. The server must raise an error if it receives any other event before acceptance. The application may call `receive()` before acceptance, and the server must continue delivering available receive events. Stream readers may be used before acceptance, but stream writers may not; readers follow the same lifecycle rules as `receive()`, and writers follow the same rules as `send()`, subject to the event types each interface allows.

`webtransport.accept` may be sent only once. A second accept is a protocol violation and the server must raise an error.

### `WebTransportSessionReject`

Sent by the application to reject the session.

```python
{
    "type": "webtransport.reject",
    "status": 403,
}
```

| Field    | Description                                              |
| -------- | -------------------------------------------------------- |
| `type`   | Event type.                                              |
| `status` | HTTP status code returned for the rejected session.      |

After sending `webtransport.reject`, the application must return and must not send any further events. The session does not exist and no further events are exchanged. If the application sends another event after rejection, the server must raise an error.

### `WebTransportSessionClose`

Sent by the application to request that the session be closed.

```python
{
    "type": "webtransport.close",
    "error_code": 0,
    "reason": "Done",
}
```

| Field        | Description                                |
| ------------ | ------------------------------------------ |
| `type`       | Event type.                                |
| `error_code` | Optional application error code.           |
| `reason`     | Optional human-readable close reason.      |

When the server handles this event it closes the session and all of its streams. Every stream reader and writer belonging to the session must be marked closed.

**Note:** A server must treat the `error_code` in `webtransport.close` as the session's error code. It must not interpret it as a stream close or reset code and must pass it as the application error code when closing the session.

### `WebTransportSessionDisconnect`

Sent by the server to notify the application that the client has disconnected.

```python
{
    "type": "webtransport.disconnect",
    "code": 0,
    "reason": "Client closed the session",
}
```

| Field    | Description                                   |
| -------- | --------------------------------------------- |
| `type`   | Event type.                                   |
| `code`   | Close code associated with the disconnect.    |
| `reason` | Optional disconnect reason.                   |

After this event the session is over. The application should stop processing it and the server must mark every remaining reader and writer of the session as closed.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

Whenever a WebTransport session closes, the server must deliver `webtransport.disconnect` to the application. If the application is still waiting in `receive()`, that call must return the disconnect event.

After `webtransport.disconnect` has been delivered, the session is closed and the application should stop sending events or writing to stream writers. If it continues to call `send()` or `Writer.write()`, the server must raise an exception. A subclass of `OSError` is recommended but not required. Applications should handle this exception; servers must be prepared to catch it and must not log it as an error.

---

## WebTransport Datagrams

### `WebTransportDatagramReceived`

Sent by the server when a datagram arrives from the client.

```python
{
    "type": "webtransport.datagram.received",
    "data": b"...",
}
```

### `WebTransportDatagramSend`

Sent by the application to send a datagram to the client.

```python
await send(
    {
        "type": "webtransport.datagram.send",
        "data": b"...",
    }
)
```

Datagrams are unreliable and unordered. The server may drop a datagram it cannot deliver.

---

## WebTransport Streams

WebTransport streams are not delivered as a single event stream through `receive`. Instead, the server exposes each stream through a **Reader** and/or a **Writer**:

| Stream kind                   | Started by | How the application gets it                                  | Reader | Writer |
| ----------------------------- | ---------- | ------------------------------------------------------------ | ------ | ------ |
| Client unidirectional stream  | Client     | `webtransport.unidirectional.client` event (via `receive`)   | Yes    | No     |
| Client bidirectional stream   | Client     | `webtransport.bidirectional.client` event (via `receive`)    | Yes    | Yes    |
| Server unidirectional stream  | Server     | Return value of `send` for `webtransport.unidirectional.server` | No  | Yes    |
| Server bidirectional stream   | Server     | Return value of `send` for `webtransport.bidirectional.server`  | Yes | Yes    |

```text
Client unidirectional:     Client ───────▶ Server        (application reads)
Server unidirectional:     Server ───────▶ Client        (application writes)
Bidirectional:             Client ◀──────▶ Server        (application reads and writes)
```

Each stream has its own independent reader and/or writer. Closing or resetting one stream must not affect other streams or the session.

---

## Reader and Writer

RCP provides two abstract base classes, `Reader` and `Writer`.

```python
from rcp import Reader, Writer
```

**RCP defines the interface only. The server must provide the implementation.** For every WebTransport stream, the server must create a concrete subclass of `Reader` and/or `Writer` built on top of its own QUIC/HTTP/3 stream handling and give it to the application.

### `Writer`

```python
class Writer(ABC):
    "Webtransport Stream Writer"

    def __init__(self):
        self._closed: bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    @abstractmethod
    async def write(self, event: WebTransportStreamWriteEvent) -> None:
        """Write events to stream"""

    @abstractmethod
    async def close(self) -> None:
        """Stop and close writing on stream"""
```

| Member              | Description                                                                     |
| ------------------- | ------------------------------------------------------------------------------- |
| `is_closed`         | `True` once the writer can no longer be written to.                             |
| `write(event)`      | Sends a `WebTransportDataSend` event on the stream.                             |
| `close()`           | Stops and closes writing on the stream.                                         |

`write` accepts only `WebTransportDataSend` events:

```python
await writer.write(
    {
        "type": "webtransport.data.send",
        "data": b"Hello",
    }
)
```

### `Reader`

```python
class Reader(ABC):
    "Webtransport Stream Reader"

    def __init__(self):
        self._closed: bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    @abstractmethod
    async def read(self) -> WebTransportStreamReadEvent:
        """read events from stream"""

    @abstractmethod
    async def close(self) -> None:
        """Stop and close reading on stream"""
```

| Member              | Description                                                                     |
| ------------------- | ------------------------------------------------------------------------------- |
| `is_closed`         | `True` once the reader can no longer deliver data.                              |
| `read()`            | Reads from the stream and returns a `WebTransportDataReceived` event.           |
| `close()`           | Stops and closes reading on the stream.                                         |

Read events have the form:

```python
{
    "type": "webtransport.data.received",
    "data": b"...",
}
```

### The `is_closed` property

`is_closed` reflects the real state of the stream. The server **must** set the internal `_closed` flag to `True` when:

* the application calls `close()` on the reader or writer,
* the client finishes or resets its side of the stream,
* the client disconnects,
* the WebTransport session is closed or disconnected (`webtransport.close` / `webtransport.disconnect`),
* the underlying QUIC connection is lost.

Applications should check `is_closed` to find out whether a stream is still usable:

```python
while not reader.is_closed:
    event = await reader.read()
    ...
```

Writing to or reading from a closed stream is an error and the server should raise an appropriate exception.

WebTransport streams are handled within the application task started for the session. Applications should catch exceptions raised by `Reader` and `Writer` operations, as well as by stream handlers, at the stream boundary. Otherwise, an unhandled exception may propagate to the session application task, causing the server to potentially treat the stream error as a session-level error, cancel the task, and close the WebTransport session.

### Event direction rules

* `WebTransportDataReceived` is emitted **only by stream readers**.
* `WebTransportDataSend` is consumed **only by stream writers**.
* Neither event is delivered through `receive` or accepted through `send`.

---

## Client-Initiated Streams

### `WebTransportClientUnidirectionalStreamStarted`

Fires when the client starts a unidirectional stream. The server provides a **reader**.

```python
{
    "type": "webtransport.unidirectional.client",
    "reader": reader,
}
```

| Field    | Description                                               |
| -------- | --------------------------------------------------------- |
| `type`   | Event type.                                               |
| `reader` | A server-implemented `Reader` for data sent by the client. |

### `WebTransportClientBidirectionalStreamStarted`

Fires when the client starts a bidirectional stream. The server provides a **reader and a writer**.

```python
{
    "type": "webtransport.bidirectional.client",
    "reader": reader,
    "writer": writer,
}
```

| Field    | Description                                                    |
| -------- | -------------------------------------------------------------- |
| `type`   | Event type.                                                    |
| `reader` | A server-implemented `Reader` for data sent by the client.     |
| `writer` | A server-implemented `Writer` for data sent to the client.     |

---

## Server-Initiated Streams

The application can open streams toward the client at any time after the session is accepted, without any client request. It does this by sending a create-stream event. The server starts the stream and returns its usable endpoint or endpoints from `send`: a `Writer` for a unidirectional stream, or a `(Writer, Reader)` tuple for a bidirectional stream.

### `WebTransportCreateServerUnidirectionalStream`

```python
writer = await send(
    {
        "type": "webtransport.unidirectional.server",
    }
)
```

When the server receives this event it must:

1. Open a new server-initiated **unidirectional** stream on the session.
2. Create a `Writer` implementation on top of that stream.
3. Return the `Writer` from `send`.
4. Keep `writer.is_closed` accurate. In particular it must become `True` if the client disconnects, resets the stream, or the session ends.

A unidirectional server stream has no reader.

### `WebTransportCreateServerBidirectionalStream`

```python
writer, reader = await send(
    {
        "type": "webtransport.bidirectional.server",
    }
)
```

When the server receives this event it must:

1. Open a new server-initiated **bidirectional** stream on the session.
2. Create a `Writer` and a `Reader` implementation on top of that stream.
3. Return them from `send` as `(writer, reader)`, matching `tuple[Writer, Reader]` in `RCPSendCallable`.
4. Keep `writer.is_closed` and `reader.is_closed` accurate. Both must become `True` if the client disconnects, resets the stream, or the session ends.

---

## WebTransport Extension

RCP provides the `WEBTRANSPORT_EXTENSION` constant:

```python
from rcp import WEBTRANSPORT_EXTENSION
```

```python
WEBTRANSPORT_EXTENSION = {
    "webtransport": {
        "features": {
            "datagrams": True,
            "unidirectional_streams": True,
            "bidirectional_streams": True,
        },
    }
}
```

### Purpose

The extension is intended for **servers that are not RCP servers but support the RCP WebTransport implementation**. Such a server advertises through the `extensions` field of its scope that applications may use RCP's WebTransport events, readers, and writers. Native RCP 2.0 servers expose WebTransport through the `webtransport` scope instead and do not need the extension.

```python
scope["extensions"] = {
    **scope.get("extensions", {}),
    **WEBTRANSPORT_EXTENSION,
}
```

### Fields

| Key        | Description                                                                          |
| ---------- | ------------------------------------------------------------------------------------ |
| `features` | Supported WebTransport features: datagrams, unidirectional and bidirectional streams. |

### Checking for support

An application should check the extension before using WebTransport on a non-RCP server:

```python
extension = scope.get("extensions", {}).get("webtransport")

if extension and extension["features"]["datagrams"]:
    ...
```

A server must only set a feature to `True` when it actually supports it, and must follow every rule in this document for the features it advertises (including server-implemented readers and writers).

An application must treat any feature field missing from the `features` mapping as `False`.

A server may advertise support for any subset of the three features. An application must not use a feature the server has not advertised. If the application attempts to use an unsupported stream feature, the server must raise an error, close the session, and close all streams associated with that session. The application must handle the error at the stream boundary, as described in [Reader and Writer](#reader-and-writer). If the application sends a datagram when datagram support was not advertised, the server must raise an error, close the session, and close all streams associated with that session.

---

## WebTransport Example

### Datagram echo

```python
async def app(scope, receive, send):
    if scope["type"] != "webtransport":
        return

    await send({"type": "webtransport.accept"})

    while True:
        event = await receive()

        if event["type"] == "webtransport.datagram.received":
            await send(
                {
                    "type": "webtransport.datagram.send",
                    "data": event["data"],
                }
            )

        elif event["type"] == "webtransport.disconnect":
            return
```

### Streams

```python
import asyncio

async def echo(reader, writer):
    while not reader.is_closed and not writer.is_closed:
        event = await reader.read()
        await writer.write(
            {
                "type": "webtransport.data.send",
                "data": event["data"],
            }
        )
    await writer.close()


async def app(scope, receive, send):
    if scope["type"] != "webtransport":
        return

    await send({"type": "webtransport.accept"})

    # Server-initiated unidirectional stream: send returns the Writer.
    writer = await send(
        {"type": "webtransport.unidirectional.server"}
    )
    await writer.write(
        {"type": "webtransport.data.send", "data": b"welcome"}
    )
    await writer.close()

    while True:
        event = await receive()

        if event["type"] == "webtransport.bidirectional.client":
            asyncio.create_task(echo(event["reader"], event["writer"]))

        elif event["type"] == "webtransport.disconnect":
            return
```

---

## WebTransport Error Codes

The current WebTransport draft does not define an error-code mapping. Servers must provide their own mapping.


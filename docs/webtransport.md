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
* WebTransport events, streams, receivers, and senders must not be used in RCP 1.0 applications.
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
* streams, stream receiver and sender callables
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
               Datagrams Streams  Receivers/
                                  Senders
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


class WebTransportStreamTerminationEventType(StrEnum):
    CLOSE = "webtransport.stream.close"
    DISCONNECT = "webtransport.stream.disconnect"
    STOP_RECEIVE = "webtransport.stream.stop_receive"
    SENDING_STOPPED = "webtransport.stream.sending_stopped"
```

### Events at a glance

Events exchanged through `receive` and `send`:

| Direction                | Event                                              | Type string                            |
| ------------------------ | -------------------------------------------------- | -------------------------------------- |
| Server → Application     | `WebTransportClientUnidirectionalStreamStarted`    | `webtransport.unidirectional.client`   |
| Server → Application     | `WebTransportClientBidirectionalStreamStarted`     | `webtransport.bidirectional.client`    |
| Server → Application     | `WebTransportSessionDisconnect`                    | `webtransport.disconnect`              |
| Application → Server     | `WebTransportSessionAccept`                        | `webtransport.accept`                  |
| Application → Server     | `WebTransportSessionReject`                        | `webtransport.reject`                  |
| Application → Server     | `WebTransportSessionClose`                         | `webtransport.close`                   |
| Application → Server     | `WebTransportCreateServerUnidirectionalStream`     | `webtransport.unidirectional.server`   |
| Application → Server     | `WebTransportCreateServerBidirectionalStream`      | `webtransport.bidirectional.server`    |

Events exchanged through stream receivers and senders (not through `receive` / `send`):

| Direction                | Event                          | Type string                    |
| ------------------------ | ------------------------------ | ------------------------------ |
| Stream receiver → Application | `WebTransportDataReceived` | `webtransport.data.received` |
| Stream receiver → Application | `WebTransportStreamDisconnected` | `webtransport.stream.disconnect` |
| Stream receiver → Application | `WebTransportStreamSendingStopped` | `webtransport.stream.sending_stopped` |
| Application → Stream sender | `WebTransportDataSend` | `webtransport.data.send` |
| Application → Stream sender | `WebTransportStreamClose` | `webtransport.stream.close` |
| Application → Stream sender | `WebTransportStreamStopReceive` | `webtransport.stream.stop_receive` |

The corresponding type aliases are:

```python
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

WebTransportStreamReceiveEvents = (
    WebTransportDataReceived
    | WebTransportStreamDisconnected
    | WebTransportStreamSendingStopped
)

WebTransportStreamSendEvents = (
    WebTransportDataSend
    | WebTransportStreamClose
    | WebTransportStreamStopReceive
)

WebTransportStreamReceiveCallable = Callable[
    [], Awaitable[WebTransportStreamReceiveEvents]
]
WebTransportStreamSendCallable = Callable[
    [WebTransportStreamSendEvents], Awaitable[None]
]
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

Before acceptance, the application may send only `webtransport.accept` or `webtransport.reject`. The server must raise an error if it receives any other event through `send()`.

The application may call `receive()` before acceptance. The server must continue delivering available receive events. Stream receiver callables may also be used before acceptance, but stream sender callables may not.

Datagram receive callables follow the receive lifecycle and must deliver available datagrams when called, including before session acceptance. Datagram send callables follow the send lifecycle and must raise an error if used before acceptance.

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

When the server handles this event it closes the session and all of its streams. Every stream receiver and sender belonging to the session must be closed.

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

After this event the session is over. The application should stop processing it and the server must mark every remaining stream receivers and senders of the session closed.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

Whenever a WebTransport session closes, the server must deliver `webtransport.disconnect` to the application. If the application is still waiting in `receive()`, that call must return the disconnect event.

After `webtransport.disconnect` has been delivered, the session is closed and the application should stop sending events or calling stream senders. If the client disconnects and the application continues to call `send()`, a stream sender, or the datagram send callable, the server must raise an exception. A subclass of `OSError` is recommended but not required. Applications should handle this exception; servers must be prepared to catch it and must not log it as an error.

---

## WebTransport Datagrams

### `WebTransportDatagramReceived`

Returned by the datagram receive callable when a datagram arrives from the client.

Datagram events are exchanged only through `WebTransportScope.datagram_callables`. They are not exchanged through the general `receive()` or `send()` callables.

```python
{
    "type": "webtransport.datagram.received",
    "data": b"...",
}
```

### `WebTransportDatagramSend`

Passed to the datagram send callable to send a datagram to the client.

```python
await datagram_send({"type": "webtransport.datagram.send", "data": b"..."})
```

`WebTransportScope.datagram_callables` is an optional tuple:

```python
datagram_receive, datagram_send = scope["datagram_callables"]
```

The receive callable comes first, followed by the send callable. The server must include the field only when it supports datagrams.

When `WEBTRANSPORT_EXTENSION` advertises datagram support, the field must be present if `features["datagrams"]` is `True`. It must be absent if that feature is `False` or missing. A mismatch is a server error and must be raised.

#### Callable event types

The datagram receive callable takes no arguments and returns only `WebTransportDatagramReceived`.

The datagram send callable accepts only `WebTransportDatagramSend` and returns `None`. Neither callable may handle other event types.

#### Datagram lifecycle

The receive callable follows the lifecycle rules of `receive()`. The server must deliver available datagrams whenever it is awaited, including before the session is accepted.

The send callable follows the lifecycle rules of `send()`. Sending before the session is accepted is an error, and the server must raise it.

The application continues to receive `webtransport.disconnect` through the general `receive()` callable. The datagram receive callable must not return that event.

After the client disconnects or the session is rejected, the application must stop datagram operations. If it calls the datagram send callable after the client disconnects, the server must raise an exception. A subclass of `OSError` is recommended but not required; the server should catch it without logging it as an error, following the rule for `send()` and a stream sender above.

Datagrams are unreliable and unordered. The server may drop a datagram it cannot deliver.

---

## WebTransport Streams

Each WebTransport stream has a **receiver callable** and a **sender callable**. A receiver takes no arguments and returns the next event from the stream. A sender accepts one event and returns `None`. These stream-specific callables are separate from the session `receive` and `send` callables.

| Stream kind | Started by | How the application gets the callables | Available direction |
| --- | --- | --- | --- |
| Client unidirectional | Client | `webtransport.unidirectional.client` via `receive()` | Client to server |
| Client bidirectional | Client | `webtransport.bidirectional.client` via `receive()` | Both directions |
| Server unidirectional | Server | `(receiver, sender)` returned by `send()` for `webtransport.unidirectional.server` | Server to client |
| Server bidirectional | Server | `(receiver, sender)` returned by `send()` for `webtransport.bidirectional.server` | Both directions |

Each stream has its own receiver and sender. Closing or resetting a stream does not affect other streams or the session.

### Stream receiver and sender callables

`WebTransportStreamReceiveCallable` takes no arguments and returns one event from `WebTransportStreamReceiveEvents`. `WebTransportStreamSendCallable` accepts one event from `WebTransportStreamSendEvents` and returns `None`.

The receiver follows the lifecycle rules of the session `receive` callable, and the sender follows the lifecycle rules of the session `send` callable. Receivers must deliver available events when called before the session is accepted. Calling a sender before acceptance must raise an error. After client disconnect, calling a sender must raise an exception; an `OSError` subclass is recommended. Applications should catch these exceptions, and servers should not log them as errors.


### `WebTransportDataReceived`

Returned by the stream receiver when data arrives on the application's receiving direction.

```python
{
    "type": "webtransport.data.received",
    "data": b"...",
    "receiving_ended": False,
}
```

| Field | Type | Description |
| --- | --- | --- |
| `type` | `Literal["webtransport.data.received"]` | Event type. |
| `data` | `bytes` | Received stream data. |
| `receiving_ended` | `bool`, optional | `True` when FIN has been received on the peer's sending direction, indicating no more data will arrive in this direction. |

### `WebTransportDataSend`

Passed to the stream sender to send data on the application's sending direction.

```python
{
    "type": "webtransport.data.send",
    "data": b"...",
    "sending_ended": False,
}
```

| Field | Type | Description |
| --- | --- | --- |
| `type` | `Literal["webtransport.data.send"]` | Event type. |
| `data` | `bytes` | Data to send on the stream. |
| `sending_ended` | `bool`, optional | When `True`, the sender sets FIN on this sending direction to indicate that no more data will be sent. |

### `WebTransportStreamDisconnected`

Returned by the stream receiver after the stream has terminated in both directions, or in the available direction of a unidirectional stream.

```python
{
    "type": "webtransport.stream.disconnect",
    "error_code": 0,
}
```

| Field | Type | Description |
| --- | --- | --- |
| `type` | `Literal["webtransport.stream.disconnect"]` | Event type. |
| `error_code` | `int`, optional | Application error code associated with stream termination. If omitted, the server reports `0`, meaning no error. |

### `WebTransportStreamClose`

Passed to the stream sender to request termination in both directions, or in the available direction of a unidirectional stream.

```python
{
    "type": "webtransport.stream.close",
    "error_code": 0,
}
```

| Field | Type | Description |
| --- | --- | --- |
| `type` | `Literal["webtransport.stream.close"]` | Event type. |
| `error_code` | `int`, optional | Application error code to use when terminating/resetting the stream. If omitted, the server uses `0`, meaning no error. |

### `WebTransportStreamStopReceive`

Passed to the stream sender to request that the peer stop sending on the application's receiving direction.

```python
{
    "type": "webtransport.stream.stop_receive",
    "error_code": 0,
}
```

| Field | Type | Description |
| --- | --- | --- |
| `type` | `Literal["webtransport.stream.stop_receive"]` | Event type. |
| `error_code` | `int`, optional | Application error code to use when stopping the peer's sending direction. If omitted, the server uses `0`, meaning no error. |

### `WebTransportStreamSendingStopped`

Returned by the stream receiver when the client requests that sending stop on the application's sending direction.

```python
{
    "type": "webtransport.stream.sending_stopped",
    "error_code": 0,
}
```

| Field | Type | Description |
| --- | --- | --- |
| `type` | `Literal["webtransport.stream.sending_stopped"]` | Event type. |
| `error_code` | `int`, optional | Application error code supplied by the client for stopping this direction. If omitted, the server reports `0`, meaning no error. |

Applications may include `error_code` in `webtransport.stream.close` and `webtransport.stream.stop_receive` to supply the application error code used for the stream termination, reset, or stop. If a sender event omits `error_code`, the server must use `0`, meaning no error. The receiver reports the error code supplied by the peer in `webtransport.stream.disconnect` or `webtransport.stream.sending_stopped`; if the peer supplied no code, the server must report `0`.

### Events allowed for each stream direction

For a **client-initiated unidirectional stream**, the receiver may return `webtransport.data.received` and `webtransport.stream.disconnect`. It must not return `webtransport.stream.sending_stopped`, because the application has no sending direction on this stream. The sender accepts `webtransport.stream.close` and `webtransport.stream.stop_receive`. Both events close the only available direction of this unidirectional stream and are equivalent for it.

For a **server-initiated unidirectional stream**, the receiver may return `webtransport.stream.disconnect` and `webtransport.stream.sending_stopped`. Both events indicate that the server-to-client sending direction has closed. The sender accepts `webtransport.data.send` and `webtransport.stream.close`; it must not accept `webtransport.stream.stop_receive`, because this stream has no server-side receiving direction.

For a **bidirectional stream**, the receiver may return all three receive events: `webtransport.data.received`, `webtransport.stream.disconnect`, and `webtransport.stream.sending_stopped`. The sender accepts all three send events: `webtransport.data.send`, `webtransport.stream.close`, and `webtransport.stream.stop_receive`.

### Client-Initiated Streams

#### `WebTransportClientUnidirectionalStreamStarted`

Fires when the client starts a unidirectional stream. The event provides `receiver` and `sender` callables:

```python
{
    "type": "webtransport.unidirectional.client",
    "receiver": receiver,
    "sender": sender,
}
```

The receiver delivers `webtransport.data.received` and `webtransport.stream.disconnect`. The sender accepts `webtransport.stream.close` and `webtransport.stream.stop_receive`; both close the only available direction.

#### `WebTransportClientBidirectionalStreamStarted`

Fires when the client starts a bidirectional stream and provides both callables:

```python
{
    "type": "webtransport.bidirectional.client",
    "receiver": receiver,
    "sender": sender,
}
```

The receiver returns the three receive-side events and the sender accepts the three send-side events listed above.

### Server-Initiated Streams

The application creates a server-initiated stream by sending its create-stream event through the session `send` callable. The server starts the stream and returns `(receiver, sender)` in that order for every server-initiated stream, including unidirectional streams.

#### `WebTransportCreateServerUnidirectionalStream`

```python
receiver, sender = await send({"type": "webtransport.unidirectional.server"})
```

The returned `(receiver, sender)` callables provide both stream endpoints. The receiver may return `webtransport.stream.disconnect` and `webtransport.stream.sending_stopped`. The sender accepts `webtransport.data.send` and `webtransport.stream.close`. It must not accept `webtransport.stream.stop_receive`, because the stream has no server-side receiving direction. Its receiver may return `webtransport.stream.disconnect` and `webtransport.stream.sending_stopped`; both indicate that the sending direction has closed.

#### `WebTransportCreateServerBidirectionalStream`

```python
receiver, sender = await send({"type": "webtransport.bidirectional.server"})
```

The returned receiver and sender accept the full three-event receive and send sets for a bidirectional stream.

### Stream and session lifecycle

Stream receivers and senders share the lifecycle rules of the session `receive` and `send` callables, respectively. A receiver must deliver available stream events when called before the session is accepted. A sender called before acceptance must raise an error. After client disconnect, calling a sender must raise an `OSError` or subclass. The application should catch this exception, and the server should not log it as an error. A stream ending or resetting closes that stream's callables without affecting other streams or the session. Closing or disconnecting the session closes all of its streams.

Errors raised by a stream receiver or sender are specific to that stream. Stream handlers run within the task used for the `RCPApplication` session, so an unhandled stream error can propagate to the application task. A server may mistake it for a session-level error and end the task, which can close the entire WebTransport session. Applications should catch stream operation errors at the stream handler boundary and handle them without letting them escape into the session task.

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

The extension is intended for **servers that are not RCP servers but support the RCP WebTransport implementation**. Such a server advertises through the `extensions` field of its scope that applications may use RCP's WebTransport events, stream receivers, and stream senders. Native RCP 2.0 servers expose WebTransport through the `webtransport` scope instead and do not need the extension.

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

A server must only set a feature to `True` when it actually supports it, and must follow every rule in this document for the features it advertises (including server-implemented receivers and senders).

An application must treat any feature field missing from the `features` mapping as `False`.

When a server advertises datagrams with this extension, `scope["datagram_callables"]` must be present exactly when `features["datagrams"]` is `True`. If the feature is `False` or missing, the field must be absent. A mismatch is a server error and must be raised.

A server may advertise support for any subset of the three features. An application must not use a feature the server has not advertised.

If the application attempts to use an unsupported stream feature, the server must raise an error, close the session, and close all streams associated with that session. The application must handle the error at the stream boundary, as described in [stream receiver and sender callables](#stream-receiver-and-sender-callables).

If the application attempts to send a datagram when datagram support was not advertised, the server must raise an error, close the session, and close its streams.

---

## WebTransport Example

### Datagram echo

```python
import asyncio

async def app(scope, receive, send):
    if scope["type"] != "webtransport":
        return

    datagram_receive, datagram_send = scope["datagram_callables"]
    await send({"type": "webtransport.accept"})

    async def echo_datagrams():
        while True:
            event = await datagram_receive()
            await datagram_send(
                {"type": "webtransport.datagram.send", "data": event["data"]}
            )

    datagram_task = asyncio.create_task(echo_datagrams())
    try:
        while True:
            event = await receive()
            if event["type"] == "webtransport.disconnect":
                return
    finally:
        datagram_task.cancel()
```

### Streams

```python
import asyncio

async def echo(receiver, sender):
    while True:
        event = await receiver()
        if event["type"] in {
            "webtransport.stream.disconnect",
            "webtransport.stream.sending_stopped",
        }:
            return
        if event["type"] == "webtransport.data.received":
            await sender(
                {
                    "type": "webtransport.data.send",
                    "data": event["data"],
                }
            )


async def app(scope, receive, send):
    if scope["type"] != "webtransport":
        return

    await send({"type": "webtransport.accept"})

    receiver, sender = await send(
        {"type": "webtransport.unidirectional.server"}
    )
    await sender({"type": "webtransport.data.send", "data": b"welcome"})
    await sender({"type": "webtransport.stream.close", "error_code": 0})

    while True:
        event = await receive()
        if event["type"] == "webtransport.bidirectional.client":
            asyncio.create_task(echo(event["receiver"], event["sender"]))
        elif event["type"] == "webtransport.disconnect":
            return
```
---

## WebTransport Error Codes

The current WebTransport draft does not define an error-code mapping. Applications must define and use their own mapping for application errors. When an application omits an error code, the server must assume error code `0` to indicate that there was no error. When the peer omits a code reported by a receive-side stream event, the server must report `0` as well.


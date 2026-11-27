# Rivora Contract Protocol (RCP)

RCP defines a common contract between applications, frameworks, and servers, so each can be built and updated separately. It describes how HTTP requests, WebTransport sessions, application lifecycles, and protocol events are represented through scopes, receive events, and send events.

It is optimized around HTTP/3 and QUIC. The HTTP/3 rules are defined in [RFC 9114](https://datatracker.ietf.org/doc/html/rfc9114).

| Protocol version | Capabilities                                          |
| ---------------- | ----------------------------------------------------- |
| `1.0`            | HTTP/3, QUIC, lifespan, extensions                    |
| `2.0`            | Everything in `1.0` plus **WebTransport**             |

---

# Architecture

RCP sits between an application framework and a server.

```text
Application
     ↓
 Framework
     ↓
    RCP
     ↓
   Server
     ↓
HTTP/3 / QUIC
```

The protocol separates application logic from the underlying server and transport implementation.

A typical HTTP request flow is:

```text
Client
   ↓
Server
   ↓
Receive HTTP/3 request
   ↓
Validate HTTP/3 fields
   ↓
Extract HTTP/3 pseudo-headers
   ↓
Create RCP HTTP Scope
   ↓
Call RCP Application
   ↓
Application receives Events
   ↓
Application sends Events
   ↓
Server validates response events
   ↓
Server sends HTTP/3 response
   ↓
Client
```

A typical WebTransport session flow (RCP 2.0) is:

```text
Client
   ↓
Server
   ↓
Receive HTTP/3 Extended CONNECT request (:protocol = webtransport)
   ↓
Validate HTTP/3 fields and pseudo-headers
   ↓
Create RCP WebTransport Scope (RCP 2.0)
   ↓
Call RCP Application
   ↓
Application sends webtransport.accept (or webtransport.reject)
   ↓
Server completes the WebTransport handshake
   ↓
Datagrams and streams are exchanged through events,
stream receivers, and stream senders
   ↓
webtransport.close / webtransport.disconnect
```

The server is responsible for translating between HTTP/3 (or WebTransport) and the RCP interface.

---

# Design Goals

RCP is designed around the following goals:

* HTTP/3-first architecture
* QUIC-based transport
* Strong typing
* Minimal application interface
* Framework and server separation
* Streaming request and response bodies
* Application lifespan management
* Explicit connection-disconnect signaling
* HTTP/3 header and pseudo-header handling
* Forward compatibility through HTTP extensions
* WebTransport support (RCP 2.0): datagrams, unidirectional streams, and bidirectional streams
* Server-implemented stream receivers and senders

---

# Installation

```bash
pip install rivora-rcp
```

---

# Core Concepts

RCP applications use three components:

* `scope`
* `receive`
* `send`

An RCP application has the following interface:

```python
async def app(scope, receive, send):
    ...
```

The application is asynchronous.

The server provides the scope and the `receive` and `send` callables to the application.

---

# Application Interface

The RCP application contract is:

```python
RCPApplication = Callable[
    [Scope, RCPReceiveCallable, RCPSendCallable],
    Awaitable[None],
]
```

where:

```python
Scope = HTTPScope | LifespanScope | WebTransportScope

RCPReceiveCallable = Callable[[], Awaitable[RCPReceiveEvent]]

RCPSendCallable = Callable[
    [RCPSendEvent],
    Awaitable[None | tuple[WebTransportStreamReceiveCallable, WebTransportStreamSendCallable]],
]
```

`send` returns `None` for other events and `(receiver, sender)` callables for every server-initiated stream.

A complete application is therefore an awaitable callable receiving:

```text
scope
receive
send
```

## `scope`

The scope contains metadata describing the HTTP request, WebTransport session, or lifespan context.

## `receive`

`receive` is an asynchronous callable used by the application to receive events from the server.

```python
event = await receive()
```

For HTTP connections, the application can receive request body events and disconnect events.

For WebTransport sessions (RCP 2.0), the application can receive client-started streams and session disconnect events through `receive()`. Datagrams use the dedicated `datagram_callables` pair in `WebTransportScope`; they are not sent through `receive()` or `send()`.

For lifespan, the application receives startup and shutdown events.

## `send`

`send` is an asynchronous callable used by the application to send events to the server.

```python
await send(event)
```

The server is responsible for validating and translating these events into the underlying HTTP/3, WebTransport, or lifecycle operation.

For most events, `send` returns `None`. For every event that creates a server-initiated WebTransport stream, `send` returns `(receiver, sender)` in that order. See [Server-Initiated Streams](#server-initiated-streams).

---

# RCP Application Lifecycle

RCP defines the lifecycle between the server and application.

An application invocation is asynchronous and remains under the control of the RCP lifecycle until the application completes or the server signals termination through an appropriate event.

A server **must not arbitrarily cancel the application awaitable or task** as a mechanism for normal HTTP connection or WebTransport session termination.

For an HTTP connection, the server signals termination by sending:

```python
{
    "type": "http.disconnect",
}
```

For a WebTransport session, the server signals termination by sending:

```python
{
    "type": "webtransport.disconnect",
    "code": 0,
}
```

The application should respond to these events and terminate its processing when appropriate.

The server may use `reason` to provide additional disconnect information:

```python
{
    "type": "http.disconnect",
    "reason": "Connection closed",
}
```

The `reason` field is optional.

---

# Scopes

A scope contains information known when the HTTP request, WebTransport session, or application context is created.

## HTTP Scope

```python
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
```

### Fields

| Field          | Description                                                 |
| -------------- | ----------------------------------------------------------- |
| `type`         | Scope type.                                                 |
| `rcp`          | RCP version information.                                    |
| `http_version` | HTTP protocol version.                                      |
| `method`       | HTTP request method.                                        |
| `scheme`       | Request scheme, such as `http` or `https`.                  |
| `authority`    | Value extracted from the HTTP/3 `:authority` pseudo-header. |
| `path`         | Decoded request path.                                       |
| `raw_path`     | Original request path bytes.                                |
| `query_string` | Raw query string bytes.                                     |
| `root_path`    | Application mounting root path.                             |
| `headers`      | Regular HTTP request headers.                               |
| `client`       | Client address and port, when available.                    |
| `server`       | Server address and port, when available.                    |
| `state`        | Request/application state.                                  |
| `extensions`   | Optional protocol extensions.                               |

---

## WebTransport Scope

Available in **RCP 2.0 only**.

```python
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
    datagram_callables: NotRequired[
        tuple[WebTransportDatagramReceiveCallable, WebTransportDatagramSendCallable]
    ]
```

### Fields

| Field          | Description                                                                 |
| -------------- | --------------------------------------------------------------------------- |
| `type`         | Always `ScopeType.WEBTRANSPORT` (`"webtransport"`).                   |
| `rcp`          | RCP version information. The version must be `RCPVersions.VERSION_2`.       |
| `http_version` | Always `HTTPVersions.HTTP3`. WebTransport is only defined over HTTP/3.      |
| `method`       | The method of the session-establishing request (Extended `CONNECT`).        |
| `scheme`       | Request scheme, such as `https`.                                            |
| `authority`    | Value extracted from the HTTP/3 `:authority` pseudo-header.                 |
| `path`         | Decoded session path.                                                       |
| `raw_path`     | Original session path bytes.                                                |
| `query_string` | Raw query string bytes.                                                     |
| `root_path`    | Application mounting root path.                                             |
| `headers`      | Regular HTTP request headers of the session-establishing request.           |
| `client`       | Client address and port, when available.                                    |
| `server`       | Server address and port, when available.                                    |
| `state`        | Session/application state (a copy of the lifespan state).                   |
| `extensions`   | Optional protocol extensions.                                               |
| `datagram_callables` | Optional tuple of datagram receive and send callables, present only when datagrams are supported. |

The `:protocol` pseudo-header of the Extended CONNECT request (`webtransport`) is consumed by the server to select the WebTransport scope and must not appear in `scope["headers"]`.

---

# HTTP/3 Stream Isolation

HTTP/3 multiplexes multiple independent streams over a single QUIC connection.

Each HTTP request stream is independent of the other HTTP request streams.

RCP therefore creates a separate HTTP scope for each HTTP/3 request stream.

```text
                    QUIC Connection
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
      HTTP/3 Stream    HTTP/3 Stream    HTTP/3 Stream
           1                2                3
          │                │                │
          ▼                ▼                ▼
      RCP Scope 1       RCP Scope 2       RCP Scope 3
          │                │                │
          ▼                ▼                ▼
      Application      Application      Application
```

Each stream has its own:

* HTTP scope
* request body events
* response events
* stream lifecycle
* disconnect state

Events belonging to one HTTP/3 stream must not be delivered to another stream.

The termination of one HTTP/3 stream must not terminate unrelated HTTP/3 streams on the same QUIC connection.

This allows multiple HTTP requests to be processed concurrently over the same QUIC connection while keeping their RCP state independent.

The same isolation applies to WebTransport: each WebTransport session has its own scope, and events, streams, and state from one session must never be delivered to another. See [WebTransport Session Isolation](#webtransport-session-isolation).

---

# Lifespan Scope

```python
class LifespanScope(TypedDict):
    type: Literal[ScopeType.LIFESPAN]
    rcp: RCP
    state: NotRequired[dict[str, Any]]
```

The lifespan scope is used during application startup and shutdown.

---

# HTTP/3 Pseudo-Headers

HTTP/3 pseudo-headers are not ordinary HTTP headers.

When the server receives HTTP/3 pseudo-headers, it **must extract and process them according to the HTTP/3 request or response rules** before constructing the RCP scope or response.

Pseudo-headers must **not** be inserted into the RCP `headers` field.

For example:

```text
:method     → scope["method"]
:scheme     → scope["scheme"]
:authority  → scope["authority"]
:path       → scope["path"] / scope["query_string"]
```

The server must validate pseudo-header names, placement, duplication, and required fields according to the applicable HTTP/3 rules.

RCP provides constants for HTTP/3 pseudo-header processing:

```python
H3_REQUEST_PSEUDO_HEADERS
H3_RESPONSE_PSEUDO_HEADERS
H3_EXTENSION_PSEUDO_HEADERS
```

## `:authority`

The `:authority` pseudo-header must be extracted and placed in:

```python
scope["authority"]
```

It must not be included in:

```python
scope["headers"]
```

If an application does not support the `authority` value in the scope, the server must provide a `Host` header with the same value as `:authority`.

---

# HTTP/3 Header Rules

Servers implementing RCP must enforce the HTTP/3 restrictions applicable to the connection.

## Lowercase Header Names

HTTP/3 header field names must be represented using lowercase names.

RCP applications should therefore receive lowercase header names:

```python
[
    (b"content-type", b"application/json"),
    (b"user-agent", b"example"),
]
```

rather than:

```python
[
    (b"Content-Type", b"application/json"),
]
```

Servers and frameworks implementing RCP are responsible for validating and normalizing header names at the HTTP/3 boundary.

---

# Forbidden HTTP/3 Headers

RCP provides the following set of HTTP/3-forbidden connection-specific headers:

```python
H3_FORBIDDEN_HEADERS = {
    b"connection",
    b"keep-alive",
    b"proxy-connection",
    b"transfer-encoding",
    b"upgrade",
}
```

These headers must not be sent as HTTP/3 field lines.

The server must reject or otherwise prevent forbidden HTTP/3 headers from being transmitted.

This applies to headers received from clients and to headers produced by applications.

---

# `TE` Header

If a `TE` header is present, its value must be:

```text
trailers
```

Servers implementing RCP must reject or otherwise handle an incoming `TE` header whose value is not permitted.

Applications must not produce an invalid `TE` header.

---

# Response Header Validation

Applications send response headers through response events.

For example:

```python
{
    "type": "http.response.start",
    "status": 200,
    "headers": [
        (b"content-type", b"text/plain"),
    ],
}
```

The server must validate response headers before sending them.

In particular:

* Header names must be lowercase.
* HTTP/3-forbidden headers must not be transmitted.
* Pseudo-headers must not be supplied through the ordinary `headers` collection.
* `:status` is represented by the RCP `status` field and must not be supplied as an ordinary header.
* Invalid HTTP/3 field representations must be rejected or handled before transmission.

Applications should therefore treat `headers` as a collection of ordinary HTTP field names and values.

The same rules apply to the `headers` field of `webtransport.accept`.

---

# HTTP Request Events

HTTP events are exchanged after the HTTP scope has been created.

## `HTTPRequestEvent`

Sent by the server to the application.

```python
{
    "type": "http.request",
    "body": b"...",
    "more_body": False,
}
```

### Fields

| Field       | Description                                          |
| ----------- | ---------------------------------------------------- |
| `type`      | Event type.                                          |
| `body`      | Request body chunk.                                  |
| `more_body` | Whether additional request body chunks are expected. |

Request bodies may be delivered as multiple events:

```text
http.request
     ↓
http.request
     ↓
http.request
     ↓
more_body = False
```

Applications should continue receiving events while additional body data is expected.

---

# HTTP Response Events

## `HTTPResponseStartEvent`

Sent by the application to the server.

```python
{
    "type": "http.response.start",
    "status": 200,
}
```

With headers:

```python
{
    "type": "http.response.start",
    "status": 200,
    "headers": [
        (b"content-type", b"text/plain"),
    ],
}
```

### Fields

| Field      | Description                                       |
| ---------- | ------------------------------------------------- |
| `type`     | Event type.                                       |
| `status`   | HTTP response status code.                        |
| `headers`  | Optional response headers.                        |
| `trailers` | Indicates whether response trailers will be sent. |

The `status` field represents the HTTP response `:status` pseudo-header.

Applications must not place `:status` inside `headers`.

---

## `HTTPResponseBodyEvent`

```python
{
    "type": "http.response.body",
    "body": b"Hello",
    "more_body": False,
}
```

### Fields

| Field       | Description                                           |
| ----------- | ----------------------------------------------------- |
| `type`      | Event type.                                           |
| `body`      | Response body chunk.                                  |
| `more_body` | Whether additional response body chunks are expected. |

Applications may stream responses by sending multiple body events.

---

## `HTTPResponseTrailersEvent`

```python
{
    "type": "http.response.trailers",
    "headers": [
        (b"content-md5", b"..."),
    ],
    "more_trailers": False,
}
```

Used to send HTTP trailers after the response body.

Trailer headers are ordinary HTTP field names and must follow the applicable restrictions.

Pseudo-headers must not be sent through the trailer `headers` collection.

---

## `HTTPResponseDebugEvent`

```python
{
    "type": "http.response.debug",
    "info": {},
}
```

Provides optional debugging information to the server.

Servers may ignore this event.

Debug information is not part of the HTTP response transmitted to the client.

---

# HTTP Disconnect

## `HTTPDisconnectEvent`

```python
{
    "type": "http.disconnect",
    "reason": "Connection closed",
}
```

`reason` is optional:

```python
{
    "type": "http.disconnect",
}
```

## Receive

When sent by the server to the application, the event indicates that the HTTP stream has been disconnected.

The application should stop processing the associated HTTP operation when appropriate.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

Once the server has delivered `http.disconnect`, the HTTP stream is closed. The application should stop sending events. If it calls `send()` after the stream has closed, the server must raise an exception. A subclass of `OSError` is recommended but not required. Applications should handle this exception, and servers must be prepared to catch it and must not log it as an error.

## Send

An application may send `HTTPDisconnectEvent` to request immediate connection termination.

```python
await send(
    {
        "type": "http.disconnect",
        "reason": "Application requested termination",
    }
)
```

When handling this event from an application, the server should terminate the associated HTTP stream according to its implementation and protocol requirements.

---

# WebTransport

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

# WebTransport Session Isolation

Each WebTransport session has its own:

* WebTransport scope
* receive and send events
* datagrams
* streams, stream receivers, and stream senders
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

# WebTransport Event Types

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

## Events at a glance

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

# WebTransport Session Events

## `WebTransportSessionAccept`

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

The server completes the WebTransport handshake when it receives this event. Response headers follow the [Response Header Validation](#response-header-validation) rules.

### Receive and send before acceptance

Before acceptance, the application may send only `webtransport.accept` or `webtransport.reject`. The server must raise an error if it receives any other event through `send()`.

The application may call `receive()` before acceptance. The server must continue delivering available receive events. Client stream receivers may also be used before acceptance, but stream senders may not.

Datagram receive callables follow the receive lifecycle and must deliver available datagrams when called, including before session acceptance. Datagram send callables follow the send lifecycle and must raise an error if used before acceptance.

`webtransport.accept` may be sent only once. A second accept is a protocol violation and the server must raise an error.

## `WebTransportSessionReject`

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

## `WebTransportSessionClose`

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

## `WebTransportSessionDisconnect`

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

After this event the session is over. The application should stop processing it and the server must mark every remaining stream receivers and senders of the session as closed.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

Whenever a WebTransport session closes, the server must deliver `webtransport.disconnect` to the application. If the application is still waiting in `receive()`, that call must return the disconnect event.

After `webtransport.disconnect` has been delivered, the session is closed and the application should stop sending events or writing to stream senders. If the client disconnects and the application continues to call `send()`, `stream sender`, or the datagram send callable, the server must raise an exception. A subclass of `OSError` is recommended but not required. Applications should handle this exception; servers must be prepared to catch it and must not log it as an error.

---

# WebTransport Datagrams

## `WebTransportDatagramReceived`

Returned by the datagram receive callable when a datagram arrives from the client.

Datagram events are exchanged only through `WebTransportScope.datagram_callables`. They are not exchanged through the general `receive()` or `send()` callables.

```python
{
    "type": "webtransport.datagram.received",
    "data": b"...",
}
```

## `WebTransportDatagramSend`

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

After the client disconnects or the session is rejected, the application must stop datagram operations. If it calls the datagram send callable after the client disconnects, the server must raise an exception. A subclass of `OSError` is recommended but not required; the server should catch it without logging it as an error, following the rule for `send()` and `stream sender` above.

Datagrams are unreliable and unordered. The server may drop a datagram it cannot deliver.

---

# WebTransport Streams

Each WebTransport stream has a **receiver callable** and a **sender callable**. A receiver takes no arguments and returns the next event from the stream. A sender accepts one event and returns `None`. These stream-specific callables are separate from the session `receive` and `send` callables.

| Stream kind | Started by | How the application gets the callables | Available direction |
| --- | --- | --- | --- |
| Client unidirectional | Client | `webtransport.unidirectional.client` via `receive()` | Client to server |
| Client bidirectional | Client | `webtransport.bidirectional.client` via `receive()` | Both directions |
| Server unidirectional | Server | `(receiver, sender)` returned by `send()` for `webtransport.unidirectional.server` | Server to client |
| Server bidirectional | Server | `(receiver, sender)` returned by `send()` for `webtransport.bidirectional.server` | Both directions |

Each stream has its own receiver and sender. Closing or resetting a stream does not affect other streams or the session.

## Stream receiver and sender callables

`WebTransportStreamReceiveCallable` takes no arguments and returns one event from `WebTransportStreamReceiveEvents`. `WebTransportStreamSendCallable` accepts one event from `WebTransportStreamSendEvents` and returns `None`.

The receiver follows the lifecycle rules of the session `receive` callable, and the sender follows the lifecycle rules of the session `send` callable. Receivers must deliver available events when called before the session is accepted. Calling a sender before acceptance must raise an error. After client disconnect, calling a sender must raise an exception; an `OSError` subclass is recommended. Applications should catch these exceptions, and servers should not log them as errors.

## Callable layout

WebTransport exposes separate callable pairs for stream data and datagrams. Receive callables take no arguments and return one event. Send callables take one event and return `None`.

```python
WebTransportStreamReceiveCallable = Callable[
    [], Awaitable[WebTransportStreamReceiveEvents]
]
WebTransportStreamSendCallable = Callable[
    [WebTransportStreamSendEvents], Awaitable[None]
]

WebTransportDatagramReceiveCallable = Callable[
    [], Awaitable[WebTransportDatagramReceiveEvents]
]
WebTransportDatagramSendCallable = Callable[
    [WebTransportDatagramSendEvents], Awaitable[None]
]
```

| Callable | Arguments | Event returned or accepted |
| --- | --- | --- |
| Stream receiver | None | Returns `WebTransportDataReceived`, `WebTransportStreamDisconnected`, or `WebTransportStreamSendingStopped` |
| Stream sender | One stream event | Accepts `WebTransportDataSend`, `WebTransportStreamClose`, or `WebTransportStreamStopReceive` |
| Datagram receiver | None | Returns `WebTransportDatagramReceived` |
| Datagram sender | One datagram event | Accepts `WebTransportDatagramSend` |

The corresponding event `type` values are:

| Callable direction | Event | `type` |
| --- | --- | --- |
| Stream receiver → application | `WebTransportDataReceived` | `webtransport.data.received` |
| Stream receiver → application | `WebTransportStreamDisconnected` | `webtransport.stream.disconnect` |
| Stream receiver → application | `WebTransportStreamSendingStopped` | `webtransport.stream.sending_stopped` |
| Application → stream sender | `WebTransportDataSend` | `webtransport.data.send` |
| Application → stream sender | `WebTransportStreamClose` | `webtransport.stream.close` |
| Application → stream sender | `WebTransportStreamStopReceive` | `webtransport.stream.stop_receive` |
| Datagram receiver → application | `WebTransportDatagramReceived` | `webtransport.datagram.received` |
| Application → datagram sender | `WebTransportDatagramSend` | `webtransport.datagram.send` |

The stream sender's allowed events depend on the stream's available directions; see [Events allowed for each stream direction](#events-allowed-for-each-stream-direction). Datagram callables accept and return only their respective datagram event types.

## `WebTransportDataReceived`

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

## `WebTransportDataSend`

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

## `WebTransportStreamDisconnected`

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

## `WebTransportStreamClose`

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

## `WebTransportStreamStopReceive`

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

## `WebTransportStreamSendingStopped`

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

## Events allowed for each stream direction

For a **client-initiated unidirectional stream**, the receiver may return `webtransport.data.received` and `webtransport.stream.disconnect`. It must not return `webtransport.stream.sending_stopped`, because the application has no sending direction on this stream. The sender accepts `webtransport.stream.close` and `webtransport.stream.stop_receive`. Both events close the only available direction of this unidirectional stream and are equivalent for it.

For a **server-initiated unidirectional stream**, the receiver may return `webtransport.stream.disconnect` and `webtransport.stream.sending_stopped`. Both events indicate that the server-to-client sending direction has closed. The sender accepts `webtransport.data.send` and `webtransport.stream.close`; it must not accept `webtransport.stream.stop_receive`, because this stream has no server-side receiving direction.

For a **bidirectional stream**, the receiver may return all three receive events: `webtransport.data.received`, `webtransport.stream.disconnect`, and `webtransport.stream.sending_stopped`. The sender accepts all three send events: `webtransport.data.send`, `webtransport.stream.close`, and `webtransport.stream.stop_receive`.

## Client-Initiated Streams

### `WebTransportClientUnidirectionalStreamStarted`

Fires when the client starts a unidirectional stream. The event provides `receiver` and `sender` callables:

```python
{
    "type": "webtransport.unidirectional.client",
    "receiver": receiver,
    "sender": sender,
}
```

The receiver delivers `webtransport.data.received` and `webtransport.stream.disconnect`. The sender accepts `webtransport.stream.close` and `webtransport.stream.stop_receive`; both close the only available direction.

### `WebTransportClientBidirectionalStreamStarted`

Fires when the client starts a bidirectional stream and provides both callables:

```python
{
    "type": "webtransport.bidirectional.client",
    "receiver": receiver,
    "sender": sender,
}
```

The receiver returns the three receive-side events and the sender accepts the three send-side events listed above.

## Server-Initiated Streams

The application creates a server-initiated stream by sending its create-stream event through the session `send` callable. The server starts the stream and returns `(receiver, sender)` in that order for every server-initiated stream, including unidirectional streams.

### `WebTransportCreateServerUnidirectionalStream`

```python
receiver, sender = await send({"type": "webtransport.unidirectional.server"})
```

The returned `(receiver, sender)` callables provide both stream endpoints. The receiver may return `webtransport.stream.disconnect` and `webtransport.stream.sending_stopped`. The sender accepts `webtransport.data.send` and `webtransport.stream.close`. It must not accept `webtransport.stream.stop_receive`, because the stream has no server-side receiving direction. Its receiver may return `webtransport.stream.disconnect` and `webtransport.stream.sending_stopped`; both indicate that the sending direction has closed.

### `WebTransportCreateServerBidirectionalStream`

```python
receiver, sender = await send({"type": "webtransport.bidirectional.server"})
```

The returned receiver and sender accept the full three-event receive and send sets for a bidirectional stream.

## Stream and session lifecycle

Stream receivers and senders share the lifecycle rules of the session `receive` and `send` callables, respectively. A receiver must deliver available stream events when called before the session is accepted. A sender called before acceptance must raise an error. After client disconnect, calling a sender must raise an `OSError` or subclass. The application should catch this exception, and the server should not log it as an error. A stream ending or resetting closes that stream's callables without affecting other streams or the session. Closing or disconnecting the session closes all of its streams.

Errors raised by a stream receiver or sender are specific to that stream. Stream handlers run within the task used for the `RCPApplication` session, so an unhandled stream error can propagate to the application task. A server may mistake it for a session-level error and end the task, which can close the entire WebTransport session. Applications should catch stream operation errors at the stream handler boundary and handle them without letting them escape into the session task.

---
# WebTransport Extension

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

## Purpose

The extension is intended for **servers that are not RCP servers but support the RCP WebTransport implementation**. Such a server advertises through the `extensions` field of its scope that applications may use RCP's WebTransport events, receivers, and senders. Native RCP 2.0 servers expose WebTransport through the `webtransport` scope instead and do not need the extension.

```python
scope["extensions"] = {
    **scope.get("extensions", {}),
    **WEBTRANSPORT_EXTENSION,
}
```

## Fields

| Key        | Description                                                                          |
| ---------- | ------------------------------------------------------------------------------------ |
| `features` | Supported WebTransport features: datagrams, unidirectional and bidirectional streams. |

## Checking for support

An application should check the extension before using WebTransport on a non-RCP server:

```python
extension = scope.get("extensions", {}).get("webtransport")

if extension and extension["features"]["datagrams"]:
    ...
```

A server must only set a feature to `True` when it actually supports it, and must follow every rule in this document for the features it advertises (including server-provided receiver and sender callables).

An application must treat any feature field missing from the `features` mapping as `False`.

A server may advertise support for any subset of the three features. An application must not use a feature the server has not advertised.

If the application attempts to use an unsupported stream feature, the server must raise an error, close the session, and close all streams associated with that session. The application must handle the error at the stream boundary, as described in [stream receiver and sender callables](#stream-receiver-and-sender-callables).

A server must include `scope["datagram_callables"]` exactly when it supports datagrams. When `WEBTRANSPORT_EXTENSION` is used, the field must be present if `features["datagrams"]` is `True` and absent if that feature is `False` or missing. A mismatch is a server error and must be raised.

If the application attempts to send a datagram when support was not advertised, the server must raise an error and close the session and its streams.

---

# WebTransport Example

## Datagram echo

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

## Streams

```python
import asyncio

async def echo(receiver, sender):
    while True:
        event = await receiver()
        await sender(
            {
                "type": "webtransport.data.send",
                "data": event["data"],
            }
        )
    await sender({"type": "webtransport.stream.close", "error_code": 0})


async def app(scope, receive, send):
    if scope["type"] != "webtransport":
        return

    await send({"type": "webtransport.accept"})

     # Server-initiated streams return (receiver, sender).
    receiver, sender = await send(
        {"type": "webtransport.unidirectional.server"}
    )
    await sender(
        {"type": "webtransport.data.send", "data": b"welcome"}
    )
    await sender({"type": "webtransport.stream.close", "error_code": 0})

    while True:
        event = await receive()

        if event["type"] == "webtransport.bidirectional.client":
            asyncio.create_task(echo(event["receiver"], event["sender"]))

        elif event["type"] == "webtransport.disconnect":
            return
```

---

# WebTransport Error Codes

The current WebTransport draft does not define an error-code mapping. Applications must define and use their own mapping between application errors and WebTransport error codes. When an application omits an error code, the server must use `0` to indicate that there was no error. When the peer omits a code reported by a receive-side stream event, the server must report `0` as well.

---

# Lifespan

RCP provides a lifespan protocol for application startup and shutdown.

The lifespan scope is:

```python
class LifespanScope(TypedDict):
    type: Literal[ScopeType.LIFESPAN]
    rcp: RCP
    state: NotRequired[dict[str, Any]]
```

The lifespan scope does not contain HTTP stream or WebTransport session information.

---

# Lifespan State

When the server starts the lifespan protocol, it must provide an empty state dictionary:

```python
{
    "type": ScopeType.LIFESPAN,
    "rcp": {
        "version": RCPVersions.VERSION_1,
    },
    "state": {},
}
```

The application may populate this state during startup.

For example:

```python
scope["state"]["database"] = database
```

When the server creates a new HTTP scope or WebTransport scope, it must provide a **copy** of the lifespan state.

Conceptually:

```text
Lifespan state
      │
      ▼
Application initializes state
      │
      ▼
Shared server-side state
      │
      ├── copy → HTTP Scope 1
      ├── copy → HTTP Scope 2
      ├── copy → WebTransport Scope 3
      └── copy → WebTransport Scope 4
```

The scope receives a copy rather than the original lifespan state dictionary.

---

# Lifespan Startup

The server sends:

```python
{
    "type": "lifespan.startup",
}
```

The application must respond with either:

```python
{
    "type": "lifespan.startup.complete",
}
```

or:

```python
{
    "type": "lifespan.startup.failed",
    "message": "Reason",
}
```

---

# Lifespan Shutdown

The server sends:

```python
{
    "type": "lifespan.shutdown",
}
```

The application responds with either:

```python
{
    "type": "lifespan.shutdown.complete",
}
```

or:

```python
{
    "type": "lifespan.shutdown.failed",
    "message": "Reason",
}
```

---

# Complete Application Example

```python
async def app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
            ],
        }
    )

    await send(
        {
            "type": "http.response.body",
            "body": b"Hello from RCP",
            "more_body": False,
        }
    )
```

---

# Streaming Example

An application can stream a response using multiple body events:

```python
async def app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
            ],
        }
    )

    await send(
        {
            "type": "http.response.body",
            "body": b"First chunk\n",
            "more_body": True,
        }
    )

    await send(
        {
            "type": "http.response.body",
            "body": b"Second chunk\n",
            "more_body": False,
        }
    )
```

---

# Server Responsibilities

An RCP server is responsible for translating between HTTP/3 (and WebTransport) and the RCP application interface.

An RCP server must:

1. Accept HTTP/3 requests over QUIC.
2. Validate HTTP/3 request fields.
3. Validate pseudo-headers according to the applicable HTTP/3 request form.
4. Extract pseudo-headers before creating the RCP scope.
5. Keep pseudo-headers out of `scope["headers"]`.
6. Store `:authority` in `scope["authority"]`.
7. Provide a `Host` header with the same authority value when the application does not support the `authority` scope value.
8. Ensure all ordinary header names are lowercase.
9. Reject or prevent forbidden HTTP/3 headers.
10. Validate `TE` according to HTTP/3 requirements.
11. Create a separate HTTP scope for each HTTP/3 request stream.
12. Keep events and state belonging to each HTTP stream independent from other HTTP streams.
13. Invoke the RCP application using the asynchronous application contract.
14. Deliver request body data through `http.request` events.
15. Deliver `http.disconnect` when an HTTP stream closes, including returning it to a pending `receive()` call.
16. Raise an exception if the application calls `send()` after the HTTP stream closes; an `OSError` subclass is recommended but not required. Catch such exceptions without logging them as errors.
17. Validate application response events.
18. Translate response events into HTTP/3 operations.
19. Prevent invalid pseudo-headers from being transmitted as ordinary headers.
20. Manage the lifespan lifecycle when lifespan support is enabled.
21. Provide lifespan state to HTTP scopes as a copy.
22. Avoid arbitrary application-task cancellation as a normal stream termination mechanism.

## WebTransport Server Responsibilities (RCP 2.0)

A server that implements RCP 2.0 WebTransport must additionally:

1. Only create `webtransport` scopes when operating as RCP version 2.0.
2. Recognize HTTP/3 Extended CONNECT requests with `:protocol` set to `webtransport`, and process `:protocol` using the HTTP/3 extension rules.
3. Keep `:protocol` out of `scope["headers"]`.
4. Create a separate WebTransport scope for each WebTransport session and provide lifespan state as a copy.
5. Keep events, datagrams, streams, and state of each session independent from other sessions.
6. Wait for `webtransport.accept` or `webtransport.reject` before completing or refusing the handshake.
7. Continue delivering available events through `receive()` and available datagrams through the datagram receive callable before acceptance; if the session closes while `receive()` is waiting, deliver `webtransport.disconnect`.
8. Before acceptance, accept only `webtransport.accept` or `webtransport.reject` through `send()`. Raise an error for other events, a second accept, or any event sent after rejection.
9. Permit stream receivers to deliver available events before acceptance, but reject stream sender calls until acceptance. Apply the same lifecycle rules as `receive()` and `send()` while respecting the events allowed for each stream direction.
10. Provide `scope["datagram_callables"]` only when datagrams are supported. When `WEBTRANSPORT_EXTENSION` is used, include the tuple exactly when `features["datagrams"]` is `True`; if the feature is `False` or missing, omit it. Raise an error if the field and advertised feature disagree.
11. Deliver available datagrams through the datagram receive callable whenever it is awaited, including before session acceptance. Return only `webtransport.datagram.received` from that callable.
12. Accept only `webtransport.datagram.send` on the datagram send callable; raise an error if it is used before session acceptance.
13. Deliver client-initiated streams through `webtransport.unidirectional.client` and `webtransport.bidirectional.client`.
14. Provide receiver and sender callables for every WebTransport stream on top of its own stream handling.
15. Start a unidirectional stream when `webtransport.unidirectional.server` is sent and return `(receiver, sender)` from `send`.
16. Start a bidirectional stream when `webtransport.bidirectional.server` is sent and return `(receiver, sender)` from `send`.
17. Close the stream receiver and sender callables when the client disconnects, the stream ends or is reset, or the session ends.
18. Emit `WebTransportDataReceived` only from stream receivers and accept `WebTransportDataSend` only on stream senders.
19. Translate `webtransport.close` into session closure and deliver client-side termination through `webtransport.disconnect`.
20. Raise an exception if the application calls `send()`, the datagram send callable, or `stream sender` after the client disconnects or the session closes; an `OSError` subclass is recommended but not required. Catch such exceptions without logging them as errors.
21. Avoid arbitrary application-task cancellation as a normal session termination mechanism.
22. Validate all WebTransport events sent by the application and reject events that are invalid for the session state.

A non-RCP server that supports RCP WebTransport must additionally advertise `WEBTRANSPORT_EXTENSION` in the scope `extensions`.

---

# Application Responsibilities

An RCP application should:

* Treat the scope as protocol-provided metadata.
* Use `await receive()` to receive events.
* Use `await send(event)` to send events.
* Process request body chunks when `more_body` is true.
* Handle `http.disconnect` appropriately.
* Produce valid RCP response events.
* Use lowercase ordinary response header names.
* Never place HTTP/3 pseudo-headers inside ordinary response headers.
* Avoid HTTP/3-forbidden headers.
* Respect the response lifecycle.
* Respond correctly to lifespan startup and shutdown events.

A WebTransport application (RCP 2.0) should additionally:

* Only handle `webtransport` scopes when the RCP version is 2.0.
* Send only `webtransport.accept` or `webtransport.reject` before acceptance; accept once, and return after rejection.
* Handle `webtransport.disconnect` and stop processing the session.
* Handle server errors from sending or writing after the connection or session has closed.
* Use the stream receiver and sender callables provided by the server.
* Use the `(receiver, sender)` tuple returned by `send` when creating any server-initiated stream.
* Call the receiver and sender only while their stream directions are open.
* Close receivers and senders when finished with them.
* Check `scope["extensions"]["webtransport"]` when running on a non-RCP server.

---

# HTTP/3 Pseudo-Header Representation

RCP separates HTTP/3 pseudo-headers from ordinary HTTP fields.

| HTTP/3 field | RCP representation                                                                         |
| ------------ | ------------------------------------------------------------------------------------------ |
| `:method`    | `scope["method"]`                                                                          |
| `:scheme`    | `scope["scheme"]`                                                                          |
| `:authority` | `scope["authority"]`                                                                       |
| `:path`      | `scope["path"]` and `scope["query_string"]`                                                |
| `:status`    | `HTTPResponseStartEvent["status"]`                                                         |
| `:protocol`  | Processed as an HTTP/3 extension/extended CONNECT field. `webtransport` selects the WebTransport scope (RCP 2.0). |

---

# Extensions

HTTP and WebTransport scopes may contain:

```python
extensions: NotRequired[
    dict[str, dict[object, object]]
]
```

Extensions allow additional protocol capabilities to be introduced without changing the base scope structure.

Extensions are optional and must not change the meaning of the required RCP fields.

RCP provides the following extension:

| Extension key  | Constant               | Purpose                                                                   |
| -------------- | ---------------------- | ------------------------------------------------------------------------- |
| `webtransport` | `WEBTRANSPORT_EXTENSION` | Advertises RCP WebTransport support from non-RCP servers. See [WebTransport Extension](#webtransport-extension). |

---

# HTTP Methods

RCP provides the following request methods:

```text
GET
POST
PUT
PATCH
DELETE
HEAD
OPTIONS
TRACE
CONNECT
```

The method is represented in the HTTP scope and WebTransport scope through:

```python
scope["method"]
```

---

# HTTP Schemes

RCP provides:

```text
http
https
```

through the `HTTPScheme` type.

```python
scope["scheme"]
```

contains the request scheme.

---

# Protocol Version

The RCP protocol version is represented by:

```python
class RCPVersions(StrEnum):
    VERSION_1 = "1.0"
    VERSION_2 = "2.0"
```

An RCP scope contains:

```python
{
    "version": RCPVersions.VERSION_1,
}
```

or, for RCP 2.0:

```python
{
    "version": RCPVersions.VERSION_2,
}
```

RCP protocol versioning is separate from the Python package version.

For example:

```text
RCP protocol version: 1.0 / 2.0
Python package release: 2.0.8
```

---

# Version 1.0

RCP 1.0 defines:

* HTTP/3
* QUIC
* Typed scopes
* Typed events
* Asynchronous applications
* Streaming request bodies
* Streaming response bodies
* HTTP/3 pseudo-header processing
* HTTP/3 header restrictions
* Lifespan startup and shutdown
* Lifespan state
* Protocol extensions

---

# Version 2.0

RCP 2.0 includes everything in RCP 1.0 and adds WebTransport:

* WebTransport scope (`webtransport`)
* WebTransport session accept, reject, close, and disconnect events
* WebTransport datagrams
* Client-initiated and server-initiated unidirectional streams
* Client-initiated and server-initiated bidirectional streams
* Server-provided stream receiver and sender callables
* `is_closed` stream state tracking
* The `WEBTRANSPORT_EXTENSION` for non-RCP servers

WebTransport must only be used with RCP version 2.0.

Reserved for future protocol versions:

* HTTP/2
* HTTP/1.1
* Additional protocol extensions

Future protocol versions may define additional transports or capabilities without changing the fundamental separation between application, framework, RCP, and server.

---

# License

RCP is licensed under the MIT License.

See the [LICENSE](https://github.com/RivoraEcosystem/rcp/blob/main/LICENSE) file for details.

# Rivora Contract Protocol (RCP)

RCP (Rivora Contract Protocol) is a lightweight application server interface specification for the Rivora Ecosystem.

RCP defines a common contract between applications, frameworks, and servers while remaining independent of any specific implementation.

RCP is designed around HTTP/3 and QUIC and defines how HTTP requests, WebTransport sessions, application lifecycles, and protocol events are represented through scopes, receive events, and send events.

RCP is an independently specified protocol. Its application interface follows an ASGI-inspired scope/receive/send architecture, but RCP defines its own protocol rules and is optimized for HTTP/3.

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
stream readers, and stream writers
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
* Server-implemented stream readers and writers

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
    Awaitable[None | tuple[Writer, Reader]],
]
```

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

For WebTransport sessions (RCP 2.0), the application can receive datagrams, client-started streams, and session disconnect events.

For lifespan, the application receives startup and shutdown events.

## `send`

`send` is an asynchronous callable used by the application to send events to the server.

```python
await send(event)
```

The server is responsible for validating and translating these events into the underlying HTTP/3, WebTransport, or lifecycle operation.

For most events, `send` returns `None`. For events that create server-initiated WebTransport streams, `send` returns the stream writer (and reader, for bidirectional streams). See [Server-Initiated Streams](#server-initiated-streams).

---

# RCP Application Lifecycle

RCP defines the lifecycle between the server and application.

An application invocation is asynchronous and remains under the control of the RCP lifecycle until the application completes or the server signals termination through an appropriate event.

A server **must not arbitrarily cancel the application awaitable or task** as a mechanism for normal HTTP connection or WebTransport session termination.

For an HTTP connection, the server signals termination by sending:

```python
{
    "type": HTTPConnectionEventType.DISCONNECT,
}
```

For a WebTransport session, the server signals termination by sending:

```python
{
    "type": WebTransportConnectionEventType.DISCONNECT,
    "code": 0,
}
```

The application should respond to these events and terminate its processing when appropriate.

The server may use `reason` to provide additional disconnect information:

```python
{
    "type": HTTPConnectionEventType.DISCONNECT,
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
```

### Fields

| Field          | Description                                                                 |
| -------------- | --------------------------------------------------------------------------- |
| `type`         | Always `ScopeType.WEBTRANSPORT` (`"webtransport"`).                         |
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
    "type": HTTPResponseEventType.START,
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
    "type": HTTPConnectionEventType.REQUEST,
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
    "type": HTTPResponseEventType.START,
    "status": 200,
}
```

With headers:

```python
{
    "type": HTTPResponseEventType.START,
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
    "type": HTTPResponseEventType.BODY,
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
    "type": HTTPResponseEventType.TRAILERS,
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
    "type": HTTPResponseEventType.DEBUG,
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
    "type": HTTPConnectionEventType.DISCONNECT,
    "reason": "Connection closed",
}
```

`reason` is optional:

```python
{
    "type": HTTPConnectionEventType.DISCONNECT,
}
```

## Receive

When sent by the server to the application, the event indicates that the HTTP stream has been disconnected.

The application should stop processing the associated HTTP operation when appropriate.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

## Send

An application may send `HTTPDisconnectEvent` to request immediate connection termination.

```python
await send(
    {
        "type": HTTPConnectionEventType.DISCONNECT,
        "reason": "Application requested termination",
    }
)
```

When handling this event from an application, the server should terminate the associated HTTP stream according to its implementation and protocol requirements.

---

# WebTransport

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

# WebTransport Session Isolation

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
```

## Events at a glance

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

# WebTransport Session Events

## `WebTransportSessionAccept`

Sent by the application to accept the session.

```python
{
    "type": WebTransportConnectionEventType.ACCEPT,
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

Datagrams and streams must not be sent before the session has been accepted.

## `WebTransportSessionReject`

Sent by the application to reject the session.

```python
{
    "type": WebTransportConnectionEventType.REJECT,
    "status": 403,
}
```

| Field    | Description                                              |
| -------- | -------------------------------------------------------- |
| `type`   | Event type.                                              |
| `status` | HTTP status code returned for the rejected session.      |

After a rejection, the session does not exist and no further events are exchanged.

## `WebTransportSessionClose`

Sent by the application to request that the session be closed.

```python
{
    "type": WebTransportConnectionEventType.CLOSE,
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

## `WebTransportSessionDisconnect`

Sent by the server to notify the application that the client has disconnected.

```python
{
    "type": WebTransportConnectionEventType.DISCONNECT,
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

---

# WebTransport Datagrams

## `WebTransportDatagramReceived`

Sent by the server when a datagram arrives from the client.

```python
{
    "type": WebTransportDatagramEventType.RECEIVED,
    "data": b"...",
}
```

## `WebTransportDatagramSend`

Sent by the application to send a datagram to the client.

```python
await send(
    {
        "type": WebTransportDatagramEventType.SEND,
        "data": b"...",
    }
)
```

Datagrams are unreliable and unordered. The server may drop a datagram it cannot deliver.

---

# WebTransport Streams

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

# Reader and Writer

RCP provides two abstract base classes, `Reader` and `Writer`.

```python
from rcp import Reader, Writer
```

**RCP defines the interface only. The server must provide the implementation.** For every WebTransport stream, the server must create a concrete subclass of `Reader` and/or `Writer` built on top of its own QUIC/HTTP/3 stream handling and give it to the application.

## `Writer`

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
        "type": WebTransportDataEventType.SEND,
        "data": b"Hello",
    }
)
```

## `Reader`

```python
class Reader(ABC):
    "Webtransport Stream Reader"

    def __init__(self):
        self._closed: bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    @abstractmethod
    async def read(
        self, event: WebTransportStreamReadEvent
    ) -> WebTransportStreamReadEvent:
        """read events from stream"""

    @abstractmethod
    async def close(self) -> None:
        """Stop and close reading on stream"""
```

| Member              | Description                                                                     |
| ------------------- | ------------------------------------------------------------------------------- |
| `is_closed`         | `True` once the reader can no longer deliver data.                              |
| `read(event)`       | Reads from the stream and returns a `WebTransportDataReceived` event.           |
| `close()`           | Stops and closes reading on the stream.                                         |

Read events have the form:

```python
{
    "type": WebTransportDataEventType.RECEIVED,
    "data": b"...",
}
```

## The `is_closed` property

`is_closed` reflects the real state of the stream. The server **must** set the internal `_closed` flag to `True` when:

* the application calls `close()` on the reader or writer,
* the client finishes or resets its side of the stream,
* the client disconnects,
* the WebTransport session is closed or disconnected (`webtransport.close` / `webtransport.disconnect`),
* the underlying QUIC connection is lost.

Applications should check `is_closed` to find out whether a stream is still usable:

```python
while not reader.is_closed:
    event = await reader.read(...)
    ...
```

Writing to or reading from a closed stream is an error and the server should raise an appropriate exception.

## Event direction rules

* `WebTransportDataReceived` is emitted **only by stream readers**.
* `WebTransportDataSend` is consumed **only by stream writers**.
* Neither event is delivered through `receive` or accepted through `send`.

---

# Client-Initiated Streams

## `WebTransportClientUnidirectionalStreamStarted`

Fires when the client starts a unidirectional stream. The server provides a **reader**.

```python
{
    "type": WebTransportUnidirectionalStreamEventType.CLIENT,
    "reader": reader,
}
```

| Field    | Description                                               |
| -------- | --------------------------------------------------------- |
| `type`   | Event type.                                               |
| `reader` | A server-implemented `Reader` for data sent by the client. |

## `WebTransportClientBidirectionalStreamStarted`

Fires when the client starts a bidirectional stream. The server provides a **reader and a writer**.

```python
{
    "type": WebTransportBidirectionalStreamEventType.CLIENT,
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

# Server-Initiated Streams

The application can open streams toward the client at any time after the session is accepted, without any client request. It does this by sending a create-stream event. The server starts the stream and **returns the reader and writer as the result of `send`**.

## `WebTransportCreateServerUnidirectionalStream`

```python
writer = await send(
    {
        "type": WebTransportUnidirectionalStreamEventType.SERVER,
    }
)
```

When the server receives this event it must:

1. Open a new server-initiated **unidirectional** stream on the session.
2. Create a `Writer` implementation on top of that stream.
3. Return the `Writer` from `send`.
4. Keep `writer.is_closed` accurate. In particular it must become `True` if the client disconnects, resets the stream, or the session ends.

A unidirectional server stream has no reader.

## `WebTransportCreateServerBidirectionalStream`

```python
writer, reader = await send(
    {
        "type": WebTransportBidirectionalStreamEventType.SERVER,
    }
)
```

When the server receives this event it must:

1. Open a new server-initiated **bidirectional** stream on the session.
2. Create a `Writer` and a `Reader` implementation on top of that stream.
3. Return them from `send` as `(writer, reader)`, matching `tuple[Writer, Reader]` in `RCPSendCallable`.
4. Keep `writer.is_closed` and `reader.is_closed` accurate. Both must become `True` if the client disconnects, resets the stream, or the session ends.

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
```

## Purpose

The extension is intended for **servers that are not RCP servers but support the RCP WebTransport implementation**. Such a server advertises through the `extensions` field of its scope that applications may use RCP's WebTransport events, readers, and writers. Native RCP 2.0 servers expose WebTransport through the `webtransport` scope instead and do not need the extension.

```python
scope["extensions"] = {
    **scope.get("extensions", {}),
    **WEBTRANSPORT_EXTENSION,
}
```

## Fields

| Key                  | Description                                                                        |
| -------------------- | ---------------------------------------------------------------------------------- |
| `features`           | Supported WebTransport features: datagrams, unidirectional and bidirectional streams. |
| `send_event_type`    | Event types the application may send through `send`.                               |
| `receive_event_type` | Event types the application may receive through `receive`.                         |
| `stream_event`       | Event types exchanged through stream readers (`data.received`) and writers (`data.send`). |

## Checking for support

An application should check the extension before using WebTransport on a non-RCP server:

```python
extension = scope.get("extensions", {}).get("webtransport")

if extension and extension["features"]["datagrams"]:
    ...
```

A server must only set a feature or event type to `True` when it actually supports it, and must follow every rule in this document for the features it advertises (including server-implemented readers and writers).

---

# WebTransport Example

## Datagram echo

```python
from rcp import (
    ScopeType,
    WebTransportConnectionEventType,
    WebTransportDatagramEventType,
)


async def app(scope, receive, send):
    if scope["type"] != ScopeType.WEBTRANSPORT:
        return

    await send({"type": WebTransportConnectionEventType.ACCEPT})

    while True:
        event = await receive()

        if event["type"] == WebTransportDatagramEventType.RECEIVED:
            await send(
                {
                    "type": WebTransportDatagramEventType.SEND,
                    "data": event["data"],
                }
            )

        elif event["type"] == WebTransportConnectionEventType.DISCONNECT:
            return
```

## Streams

```python
import asyncio

from rcp import (
    ScopeType,
    WebTransportBidirectionalStreamEventType,
    WebTransportConnectionEventType,
    WebTransportDataEventType,
    WebTransportUnidirectionalStreamEventType,
)


async def echo(reader, writer):
    while not reader.is_closed and not writer.is_closed:
        event = await reader.read(...)
        await writer.write(
            {
                "type": WebTransportDataEventType.SEND,
                "data": event["data"],
            }
        )
    await writer.close()


async def app(scope, receive, send):
    if scope["type"] != ScopeType.WEBTRANSPORT:
        return

    await send({"type": WebTransportConnectionEventType.ACCEPT})

    # Server-initiated unidirectional stream: send returns the Writer.
    writer = await send(
        {"type": WebTransportUnidirectionalStreamEventType.SERVER}
    )
    await writer.write(
        {"type": WebTransportDataEventType.SEND, "data": b"welcome"}
    )
    await writer.close()

    while True:
        event = await receive()

        if event["type"] == WebTransportBidirectionalStreamEventType.CLIENT:
            asyncio.create_task(echo(event["reader"], event["writer"]))

        elif event["type"] == WebTransportConnectionEventType.DISCONNECT:
            return
```

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
    "type": LifespanEventType.STARTUP,
}
```

The application must respond with either:

```python
{
    "type": LifespanEventType.STARTUP_COMPLETE,
}
```

or:

```python
{
    "type": LifespanEventType.STARTUP_FAILED,
    "message": "Reason",
}
```

---

# Lifespan Shutdown

The server sends:

```python
{
    "type": LifespanEventType.SHUTDOWN,
}
```

The application responds with either:

```python
{
    "type": LifespanEventType.SHUTDOWN_COMPLETE,
}
```

or:

```python
{
    "type": LifespanEventType.SHUTDOWN_FAILED,
    "message": "Reason",
}
```

---

# Complete Application Example

```python
from rcp import HTTPResponseEventType


async def app(scope, receive, send):
    await send(
        {
            "type": HTTPResponseEventType.START,
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
            ],
        }
    )

    await send(
        {
            "type": HTTPResponseEventType.BODY,
            "body": b"Hello from RCP",
            "more_body": False,
        }
    )
```

---

# Streaming Example

An application can stream a response using multiple body events:

```python
from rcp import HTTPResponseEventType


async def app(scope, receive, send):
    await send(
        {
            "type": HTTPResponseEventType.START,
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
            ],
        }
    )

    await send(
        {
            "type": HTTPResponseEventType.BODY,
            "body": b"First chunk\n",
            "more_body": True,
        }
    )

    await send(
        {
            "type": HTTPResponseEventType.BODY,
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
15. Deliver stream termination through `http.disconnect`.
16. Validate application response events.
17. Translate response events into HTTP/3 operations.
18. Prevent invalid pseudo-headers from being transmitted as ordinary headers.
19. Manage the lifespan lifecycle when lifespan support is enabled.
20. Provide lifespan state to HTTP scopes as a copy.
21. Avoid arbitrary application-task cancellation as a normal stream termination mechanism.

## WebTransport Server Responsibilities (RCP 2.0)

A server that implements RCP 2.0 WebTransport must additionally:

1. Only create `webtransport` scopes when operating as RCP version 2.0.
2. Recognize HTTP/3 Extended CONNECT requests with `:protocol` set to `webtransport`, and process `:protocol` using the HTTP/3 extension rules.
3. Keep `:protocol` out of `scope["headers"]`.
4. Create a separate WebTransport scope for each WebTransport session and provide lifespan state as a copy.
5. Keep events, datagrams, streams, and state of each session independent from other sessions.
6. Wait for `webtransport.accept` or `webtransport.reject` before completing or refusing the handshake.
7. Deliver incoming datagrams through `webtransport.datagram.received`.
8. Translate `webtransport.datagram.send` into WebTransport datagrams.
9. Deliver client-initiated streams through `webtransport.unidirectional.client` and `webtransport.bidirectional.client`.
10. Implement `Reader` and `Writer` for every WebTransport stream on top of its own stream handling.
11. Start a unidirectional stream when `webtransport.unidirectional.server` is sent and return its `Writer` from `send`.
12. Start a bidirectional stream when `webtransport.bidirectional.server` is sent and return its `(Writer, Reader)` from `send`.
13. Keep `is_closed` accurate for every reader and writer, and mark them closed when the client disconnects, the stream ends or is reset, or the session ends.
14. Emit `WebTransportDataReceived` only from readers and accept `WebTransportDataSend` only on writers.
15. Translate `webtransport.close` into session closure and deliver client-side termination through `webtransport.disconnect`.
16. Avoid arbitrary application-task cancellation as a normal session termination mechanism.
17. Validate all WebTransport events sent by the application and reject events that are invalid for the session state.

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
* Send `webtransport.accept` or `webtransport.reject` before using the session.
* Handle `webtransport.disconnect` and stop processing the session.
* Use the `Reader` and `Writer` objects provided by the server, and never implement or substitute its own.
* Use the return value of `send` when creating server-initiated streams: a `Writer` for unidirectional streams and `(Writer, Reader)` for bidirectional streams.
* Check `is_closed` before reading from or writing to a stream.
* Close readers and writers when finished with them.
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
Python package release: 1.0.4
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
* Server-implemented stream `Reader` and `Writer` interfaces
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
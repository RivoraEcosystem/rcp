# Rivora Contract Protocol (RCP)

RCP (Rivora Contract Protocol) is a lightweight application server interface specification for the Rivora Ecosystem.

RCP defines a common contract between applications, frameworks, and servers while remaining independent of any specific implementation.

RCP is designed around HTTP/3 and QUIC and defines how HTTP requests, application lifecycles, and protocol events are represented through scopes, receive events, and send events.

RCP is an independently specified protocol. Its application interface follows an ASGI-inspired scope/receive/send architecture, but RCP defines its own protocol rules and is optimized for HTTP/3.

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

The server is responsible for translating between HTTP/3 and the RCP interface.

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
* Future WebTransport support

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

A complete application is therefore an awaitable callable receiving:

```text
scope
receive
send
```

## `scope`

The scope contains metadata describing the HTTP request or lifespan context.

## `receive`

`receive` is an asynchronous callable used by the application to receive events from the server.

```python
event = await receive()
```

For HTTP connections, the application can receive request body events and disconnect events.

For lifespan, the application receives startup and shutdown events.

## `send`

`send` is an asynchronous callable used by the application to send events to the server.

```python
await send(event)
```

The server is responsible for validating and translating these events into the underlying HTTP/3 or lifecycle operation.

---

# RCP Application Lifecycle

RCP defines the lifecycle between the server and application.

An application invocation is asynchronous and remains under the control of the RCP lifecycle until the application completes or the server signals termination through an appropriate event.

A server **must not arbitrarily cancel the application awaitable or task** as a mechanism for normal HTTP connection termination.

For an HTTP connection, the server signals termination by sending:

```python
{
    "type": HTTPConnectionEventType.DISCONNECT,
}
```

The application should respond to this event and terminate its processing when appropriate.

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

A scope contains information known when the HTTP request or application context is created.

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

# Lifespan

RCP provides a lifespan protocol for application startup and shutdown.

The lifespan scope is:

```python
class LifespanScope(TypedDict):
    type: Literal[ScopeType.LIFESPAN]
    rcp: RCP
    state: NotRequired[dict[str, Any]]
```

The lifespan scope does not contain HTTP stream information.

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

When the server creates a new HTTP scope, it must provide a **copy** of the lifespan state.

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
      ├── copy → HTTP Scope 3
      └── copy → HTTP Scope 4
```

The HTTP scope receives a copy rather than the original lifespan state dictionary.

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

An RCP server is responsible for translating between HTTP/3 and the RCP application interface.

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

---

# HTTP/3 Pseudo-Header Representation

RCP separates HTTP/3 pseudo-headers from ordinary HTTP fields.

| HTTP/3 field | RCP representation                                                       |
| ------------ | ------------------------------------------------------------------------ |
| `:method`    | `scope["method"]`                                                        |
| `:scheme`    | `scope["scheme"]`                                                        |
| `:authority` | `scope["authority"]`                                                     |
| `:path`      | `scope["path"]` and `scope["query_string"]`                              |
| `:status`    | `HTTPResponseStartEvent["status"]`                                       |
| `:protocol`  | Processed as an HTTP/3 extension/extended CONNECT field where applicable |

---

# Extensions

HTTP scopes may contain:

```python
extensions: NotRequired[
    dict[str, dict[object, object]]
]
```

Extensions allow additional protocol capabilities to be introduced without changing the base scope structure.

Extensions are optional and must not change the meaning of the required RCP fields.

WebTransport is reserved for a future protocol version.

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

The method is represented in the HTTP scope through:

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
```

An RCP scope contains:

```python
{
    "version": RCPVersions.VERSION_1,
}
```

RCP protocol versioning is separate from the Python package version.

For example:

```text
RCP protocol version: 1.0
Python package release: 1.0.4
```

---

# Version 1.0

The current protocol defines:

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

Reserved for future protocol versions:

* WebTransport
* HTTP/2
* HTTP/1.1
* Additional protocol extensions

Future protocol versions may define additional transports or capabilities without changing the fundamental separation between application, framework, RCP, and server.

---

# License

RCP is licensed under the MIT License.

See the [LICENSE](https://github.com/RivoraEcosystem/rcp/blob/main/LICENSE) file for details.

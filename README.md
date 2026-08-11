# Rivora Contract Protocol (RCP)

RCP (Rivora Contract Protocol) is a lightweight interface specification that defines how applications, frameworks, and servers communicate within the Rivora Ecosystem.

RCP provides a common contract between frameworks and servers while remaining independent of any specific implementation.

RCP 1.0 is designed for HTTP/3 and QUIC-based servers.

## Repository

[GitHub Repository](https://github.com/RivoraEcosystem/rcp)

---

# Architecture

RCP sits between a framework and a server.

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

A typical request flow looks like:

```text
Client
    ↓
 Server
    ↓
 Creates Scope
    ↓
 Calls Application
    ↓
 Application receives Events
    ↓
 Application sends Events
    ↓
 Server sends Response
```

---

# Design Goals

* HTTP/3-first architecture
* Strong typing
* Minimal interface
* Framework and server separation
* Support for streaming
* Support for lifespan events
* Forward compatibility through extensions
* Future WebTransport support

---

# Installation

```bash
pip install rivora-rcp
```

---

# Core Concepts

RCP is built around three main components:

* Scope
* Receive
* Send

An application receives these from the server.

```python
async def app(scope, receive, send):
    ...
```

---

# Application Interface

Applications must follow the RCP application contract.

```python
RCPApplication = Callable[
    [Scope, RCPReceiveCallable, RCPSendCallable],
    Awaitable[None],
]
```

Example:

```python
async def app(scope, receive, send):
    ...
```

## Parameters

### scope

Contains information about the connection and request.

### receive

Receives events from the server.

```python
event = await receive()
```

### send

Sends events to the server.

```python
await send(event)
```

---

# Scopes

A scope contains information known when the connection or application context is created.

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

| Field          | Description                       |
| -------------- | --------------------------------- |
| `type`         | Scope type                        |
| `rcp`          | RCP version information           |
| `http_version` | HTTP protocol version             |
| `method`       | Request method                    |
| `scheme`       | Request scheme                    |
| `authority`    | HTTP/3 `:authority` pseudo-header |
| `path`         | Decoded request path              |
| `raw_path`     | Original path bytes               |
| `query_string` | Raw query string                  |
| `root_path`    | Mounted root path                 |
| `headers`      | Request headers                   |
| `client`       | Client address and port           |
| `server`       | Server address and port           |
| `state`        | Shared request state              |
| `extensions`   | Optional protocol capabilities    |

---

## Lifespan Scope

```python
class LifespanScope(TypedDict):
    type: Literal[ScopeType.LIFESPAN]
    rcp: RCP

    state: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, dict[object, object]]]
```

The lifespan scope is used during application startup and shutdown.

---

# HTTP Events

## HTTPRequestEvent

Sent by the server to the application.

```python
{
    "type": HTTPConnectionEventType.REQUEST,
    "body": b"...",
    "more_body": False,
}
```

| Field       | Description                           |
| ----------- | ------------------------------------- |
| `type`      | Event type                            |
| `body`      | Request body chunk                    |
| `more_body` | Whether more body chunks are expected |

---

## HTTPResponseStartEvent

Sent by the application to the server.

```python
{
    "type": HTTPResponseEventType.START,
    "status": 200,
}
```

| Field      | Description                             |
| ---------- | --------------------------------------- |
| `type`     | Event type                              |
| `status`   | HTTP response status                    |
| `headers`  | Response headers                        |
| `trailers` | Indicates whether trailers will be sent |

---

## HTTPResponseBodyEvent

```python
{
    "type": HTTPResponseEventType.BODY,
    "body": b"Hello",
    "more_body": False,
}
```

| Field       | Description                           |
| ----------- | ------------------------------------- |
| `type`      | Event type                            |
| `body`      | Response body chunk                   |
| `more_body` | Whether more body chunks are expected |

---

## HTTPResponseTrailersEvent

```python
{
    "type": HTTPResponseEventType.TRAILERS,
    "headers": [...],
    "more_trailers": False,
}
```

Used to send HTTP trailers after the response body.

---

## HTTPResponseDebugEvent

```python
{
    "type": HTTPResponseEventType.DEBUG,
    "info": {},
}
```

Optional debugging information.

Servers may ignore this event.

---

## HTTPDisconnectEvent

```python
{
    "type": HTTPConnectionEventType.DISCONNECT,
    "reason": "Connection closed",
}
```

`reason` is optional and may be omitted.

| Field    | Description                |
| -------- | -------------------------- |
| `type`   | Event type                 |
| `reason` | Optional disconnect reason |

### Receive

Indicates that the client disconnected.

### Send

Requests immediate connection termination.

When sent by the application, the server should close the connection without sending additional events.

---

# Lifespan Events

Lifespan events are used to manage application startup and shutdown.

## Startup

Server:

```python
{
    "type": LifespanEventType.STARTUP,
}
```

Application:

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

## Shutdown

Server:

```python
{
    "type": LifespanEventType.SHUTDOWN,
}
```

Application:

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

# Example Application

```python
from rcp import HTTPResponseEventType


async def app(scope, receive, send):
    await send(
        {
            "type": HTTPResponseEventType.START,
            "status": 200,
        }
    )

    await send(
        {
            "type": HTTPResponseEventType.BODY,
            "body": b"Hello from RCP",
        }
    )
```

---

# Version Information

## RCP 1.0

Currently designed to support:

* HTTP/3
* QUIC
* Typed scopes
* Typed events
* Lifespan protocol

Future RCP versions are planned to add support for:

* WebTransport
* HTTP/2
* HTTP/1.1
* Additional protocol extensions

---

# Rivora Ecosystem

RCP is one of the core projects of the [Rivora Ecosystem](https://github.com/RivoraEcosystem).

The protocol is designed to allow different servers and frameworks to communicate without depending on each other's internal implementation.

---

# Development Status

RCP 1.0 is stable and publicly available.

Future versions of RCP are planned as the Rivora Ecosystem grows and additional protocol support and features are introduced.

The current 1.0 specification is intended to provide a stable foundation for RCP-compatible servers and frameworks.

---

# License

RCP is licensed under the MIT License.

See the [LICENSE](https://github.com/RivoraEcosystem/rcp/blob/main/LICENSE) file for details.

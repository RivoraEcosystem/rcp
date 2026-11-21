# Application Guide

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

## Application Interface

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
    Awaitable[None | Writer | tuple[Writer, Reader]],
]
```

`send` returns `None` for events that do not create a server-initiated stream. It returns a `Writer` for a server-initiated unidirectional stream and a `(Writer, Reader)` tuple for a server-initiated bidirectional stream.

A complete application is therefore an awaitable callable receiving:

```text
scope
receive
send
```

### `scope`

The scope contains metadata describing the HTTP request, WebTransport session, or lifespan context.

### `receive`

`receive` is an asynchronous callable used by the application to receive events from the server.

```python
event = await receive()
```

For HTTP connections, the application can receive request body events and disconnect events.

For WebTransport sessions (RCP 2.0), the application can receive datagrams, client-started streams, and session disconnect events.

For lifespan, the application receives startup and shutdown events.

### `send`

`send` is an asynchronous callable used by the application to send events to the server.

```python
await send(event)
```

The server is responsible for validating and translating these events into the underlying HTTP/3, WebTransport, or lifecycle operation.

For most events, `send` returns `None`. For events that create server-initiated WebTransport streams, `send` returns the stream writer (and reader, for bidirectional streams). See [Server-Initiated Streams](webtransport.md#server-initiated-streams).

---

## RCP Application Lifecycle

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

## HTTP Request Events

HTTP events are exchanged after the HTTP scope has been created.

### `HTTPRequestEvent`

Sent by the server to the application.

```python
{
    "type": HTTPConnectionEventType.REQUEST,
    "body": b"...",
    "more_body": False,
}
```

#### Fields

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

## HTTP Response Events

### `HTTPResponseStartEvent`

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

#### Fields

| Field      | Description                                       |
| ---------- | ------------------------------------------------- |
| `type`     | Event type.                                       |
| `status`   | HTTP response status code.                        |
| `headers`  | Optional response headers.                        |
| `trailers` | Indicates whether response trailers will be sent. |

The `status` field represents the HTTP response `:status` pseudo-header.

Applications must not place `:status` inside `headers`.

---

### `HTTPResponseBodyEvent`

```python
{
    "type": HTTPResponseEventType.BODY,
    "body": b"Hello",
    "more_body": False,
}
```

#### Fields

| Field       | Description                                           |
| ----------- | ----------------------------------------------------- |
| `type`      | Event type.                                           |
| `body`      | Response body chunk.                                  |
| `more_body` | Whether additional response body chunks are expected. |

Applications may stream responses by sending multiple body events.

---

### `HTTPResponseTrailersEvent`

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

### `HTTPResponseDebugEvent`

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

## HTTP Disconnect

### `HTTPDisconnectEvent`

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

### Receive

When sent by the server to the application, the event indicates that the HTTP stream has been disconnected.

The application should stop processing the associated HTTP operation when appropriate.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

### Send

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

## Complete Application Example

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

## Streaming Example

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

## Application Responsibilities

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


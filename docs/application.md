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
    Awaitable[
        None
        | tuple[
            WebTransportStreamReceiveCallable,
            WebTransportStreamSendCallable,
        ]
    ],
]
```

`send` returns `None` for events that do not create a server-initiated stream. It returns a `(receiver, sender)` tuple of callables for every server-initiated stream.

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

For WebTransport sessions (RCP 2.0), the application can receive client-started streams and session disconnect events through `receive()`. Datagrams use the dedicated `datagram_callables` pair in `WebTransportScope`; they are not sent through `receive()` or `send()`.

The server must continue delivering available WebTransport receive events when the application calls `receive()`, including before the session is accepted. If the session closes while `receive()` is waiting, the server must return `webtransport.disconnect`.

For lifespan, the application receives startup and shutdown events.

### `send`

`send` is an asynchronous callable used by the application to send events to the server.

```python
await send(event)
```

The server is responsible for validating and translating these events into the underlying HTTP/3, WebTransport, or lifecycle operation.

For most events, `send` returns `None`. For events that create server-initiated WebTransport streams, `send` returns the stream sender and receiver, for bidirectional and unidirectional streams. See [Server-Initiated Streams](webtransport.md#server-initiated-streams).

For WebTransport, before acceptance the application may send only `webtransport.accept` or `webtransport.reject`; an accept may be sent only once. After rejection, the application must return. The server must reject invalid sends for the current session state. See [WebTransport session lifecycle](webtransport.md#webtransport-session-events) for the receive, send, and stream receiver/sender rules.

---

## RCP Application Lifecycle

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

After a disconnect event has been delivered, the connection or session is closed. The application should stop sending events. If it continues to call `send()` after closure, the server must raise an exception. A subclass of `OSError` is recommended but not required. Applications should handle this exception, and servers must be prepared to catch it without logging it as an error.

The server may use `reason` to provide additional disconnect information:

```python
{
    "type": "http.disconnect",
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
    "type": "http.request",
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
    "type": "http.response.body",
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

### `HTTPResponseDebugEvent`

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

## HTTP Disconnect

### `HTTPDisconnectEvent`

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

### Receive

When sent by the server to the application, the event indicates that the HTTP stream has been disconnected.

The application should stop processing the associated HTTP operation when appropriate.

When the HTTP stream closes, the server must deliver `http.disconnect`; if `receive()` is pending, it must return that event.

The server uses this event to communicate termination rather than arbitrarily cancelling the application task.

### Send

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

## Complete Application Example

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

## Streaming Example

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
* Send only `webtransport.accept` or `webtransport.reject` before acceptance; accept once, and return after rejection.
* Handle `webtransport.disconnect` and stop processing the session.
* Handle server errors from sending or writing after the connection or session has closed.
* Use the stream receiver and sender callables provided by the server.
* Use the `(receiver, sender)` tuple returned by `send` when creating any server-initiated stream.
* Only send events in sender and accept events from receiver that are allowed in current stream direction.
* Follow the stream receiver and sender lifecycle rules when finished with each direction.
* Check `scope["extensions"]["webtransport"]` when running on a non-RCP server.


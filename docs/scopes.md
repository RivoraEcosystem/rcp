# Scopes and State

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

RCP's WebTransport scope and interface are designed for WebTransport over HTTP/3. They are not suitable for WebTransport over HTTP/2.

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
| `http_version` | Always `HTTPVersions.HTTP3`. RCP's WebTransport interface supports HTTP/3 only. |
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

The `:protocol` pseudo-header of the Extended CONNECT request is consumed by the server to select the WebTransport scope and must not appear in `scope["headers"]`. Its token value depends on the WebTransport draft version implemented by the server (for example, `webtransport` or `webtransport-h3`). Implementations must refer to their chosen draft version for the correct token. RCP's WebTransport interface is not tied to a specific WebTransport draft version.

---

## HTTP/3 Stream Isolation

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

The same isolation applies to WebTransport: each WebTransport session has its own scope, and events, streams, and state from one session must never be delivered to another. See [WebTransport Session Isolation](webtransport.md#webtransport-session-isolation).

---

## Lifespan Scope

```python
class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    rcp: RCP
    state: NotRequired[dict[str, Any]]
```

The lifespan scope is used during application startup and shutdown.

---

## Lifespan State

When the server starts the lifespan protocol, it must provide an empty state dictionary:

```python
{
    "type": "lifespan",
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


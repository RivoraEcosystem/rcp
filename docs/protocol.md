# Protocol Reference

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
| `webtransport` | `WEBTRANSPORT_EXTENSION` | Advertises RCP WebTransport support from non-RCP servers. See [WebTransport Extension](webtransport.md#webtransport-extension). |

---

## HTTP Methods

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

## HTTP Schemes

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

## Protocol Version

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

## Version 1.0

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

## Version 2.0

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


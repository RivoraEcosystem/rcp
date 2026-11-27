# HTTP/3 Reference

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

## HTTP/3 Header Rules

Servers implementing RCP must enforce the HTTP/3 restrictions applicable to the connection.

### Lowercase Header Names

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

## Forbidden HTTP/3 Headers

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

## `TE` Header

If a `TE` header is present, its value must be:

```text
trailers
```

Servers implementing RCP must reject or otherwise handle an incoming `TE` header whose value is not permitted.

Applications must not produce an invalid `TE` header.

---

## Response Header Validation

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

## HTTP/3 Pseudo-Header Representation

RCP separates HTTP/3 pseudo-headers from ordinary HTTP fields.

| HTTP/3 field | RCP representation                                                                         |
| ------------ | ------------------------------------------------------------------------------------------ |
| `:method`    | `scope["method"]`                                                                          |
| `:scheme`    | `scope["scheme"]`                                                                          |
| `:authority` | `scope["authority"]`                                                                       |
| `:path`      | `scope["path"]` and `scope["query_string"]`                                                |
| `:status`    | `HTTPResponseStartEvent["status"]`                                                         |
| `:protocol`  | Processed as an HTTP/3 extension/extended CONNECT field. The WebTransport draft's token (for example, `webtransport` or `webtransport-h3`) selects the WebTransport scope (RCP 2.0); implementations must consult their draft version for the token. |


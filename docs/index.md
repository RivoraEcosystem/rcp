# Rivora Contract Protocol (RCP)

RCP defines a common contract between applications, frameworks, and servers, so each can be built and updated separately. It describes how HTTP requests, WebTransport sessions, application lifecycles, and protocol events are represented through scopes, receive events, and send events.

It is optimized around HTTP/3 and QUIC. The HTTP/3 rules are defined in [RFC 9114](https://datatracker.ietf.org/doc/html/rfc9114).

| Protocol version | Capabilities                                          |
| ---------------- | ----------------------------------------------------- |
| `1.0`            | HTTP/3, QUIC, lifespan, extensions                    |
| `2.0`            | Everything in `1.0` plus **WebTransport**             |

---

## Architecture

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
stream receiver and sender callables
   ↓
webtransport.close / webtransport.disconnect
```

The server is responsible for translating between HTTP/3 (or WebTransport) and the RCP interface.

---

## Design Goals

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
* Server-provided stream receiver and sender callables

---

## Installation

```bash
pip install rivora-rcp
```

---


```{toctree}
:maxdepth: 3
:caption: Guide
:hidden:

application
scopes
http3
webtransport
lifespan
server
protocol
changelog
license
```

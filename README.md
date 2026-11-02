# Rivora Contract Protocol (RCP)

RCP defines a common contract between applications, frameworks, and servers, so each can be built and updated separately. It describes how HTTP requests, WebTransport sessions, application lifecycles, and protocol events are represented through scopes, receive events, and send events.

It is optimized around HTTP/3 and QUIC and Webtransport over HTTP/3
## Install

```bash
pip install rivora-rcp
```

## Quick start

```python
from rcp import HTTPResponseEventType


async def app(scope, receive, send):
    await send({"type": HTTPResponseEventType.START, "status": 200})
    await send(
        {
            "type": HTTPResponseEventType.BODY,
            "body": b"Hello from RCP",
            "more_body": False,
        }
    )
```

RCP applications are asynchronous callables that receive a `scope`, `receive`, and `send`. Servers provide these values and translate RCP events to and from the underlying transport.

## Protocol versions

| Version | Capabilities |
| --- | --- |
| `1.0` | HTTP/3, QUIC, lifespan, and extensions |
| `2.0` | Version 1.0 plus WebTransport |

The RCP protocol version is separate from the Python package version.

To learn more about `rcp`, please [read the documentation](https://rcp.bhavyamalhotra.in).

RCP is licensed under the [MIT License](LICENSE).

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
15. Deliver `http.disconnect` when an HTTP stream closes, including returning it to a pending `receive()` call.
16. Raise an exception if the application calls `send()` after the HTTP stream closes; an `OSError` subclass is recommended but not required. Catch such exceptions without logging them as errors.
17. Validate application response events.
18. Translate response events into HTTP/3 operations.
19. Prevent invalid pseudo-headers from being transmitted as ordinary headers.
20. Manage the lifespan lifecycle when lifespan support is enabled.
21. Provide lifespan state to HTTP scopes as a copy.
22. Avoid arbitrary application-task cancellation as a normal stream termination mechanism.

## WebTransport Server Responsibilities (RCP 2.0)

A server that implements RCP 2.0 WebTransport must additionally:

1. Only create `webtransport` scopes when operating as RCP version 2.0.
2. Recognize HTTP/3 Extended CONNECT requests with `:protocol` set to `webtransport`, and process `:protocol` using the HTTP/3 extension rules.
3. Keep `:protocol` out of `scope["headers"]`.
4. Create a separate WebTransport scope for each WebTransport session and provide lifespan state as a copy.
5. Keep events, datagrams, streams, and state of each session independent from other sessions.
6. Wait for `webtransport.accept` or `webtransport.reject` before completing or refusing the handshake.
7. Continue delivering available events through `receive()` and available datagrams through the datagram receive callable before acceptance; if the session closes while `receive()` is waiting, deliver `webtransport.disconnect`.
8. Before acceptance, accept only `webtransport.accept` or `webtransport.reject` through `send()`. Raise an error for other events, a second accept, or any event sent after rejection.
9. Permit stream receiver callables to be used before acceptance and deliver available events. Reject stream sender calls until acceptance. Apply the same lifecycle restrictions as `receive()` and `send()` while respecting each stream direction's allowed event types.
10. Provide `scope["datagram_callables"]` only when datagrams are supported. When `WEBTRANSPORT_EXTENSION` is used, include the tuple exactly when `features["datagrams"]` is `True`; if the feature is `False` or missing, omit it. Raise an error if the field and advertised feature disagree.
11. Deliver available datagrams through the datagram receive callable whenever it is awaited, including before session acceptance. Return only `webtransport.datagram.received` from that callable.
12. Accept only `webtransport.datagram.send` on the datagram send callable; raise an error if it is used before session acceptance.
13. Deliver client-initiated streams through `webtransport.unidirectional.client` and `webtransport.bidirectional.client`.
14. Provide receiver and sender callables for every WebTransport stream on top of its own stream handling.
15. Start a unidirectional stream when `webtransport.unidirectional.server` is sent and return its `(receiver, sender)` tuple from `send`.
16. Start a bidirectional stream when `webtransport.bidirectional.server` is sent and return its `(receiver, sender)` callable tuple from `send`.
17. Close stream receiver and sender callables when the client disconnects, the stream ends or is reset, or the session ends.
18. Emit `WebTransportDataReceived` only from receiver callables and accept `WebTransportDataSend` only on sender callables.
19. Translate `webtransport.close` into session closure and deliver client-side termination through `webtransport.disconnect`.
20. Raise an exception if the application calls `send()`, the datagram send callable, or a stream sender after the client disconnects or the session closes; an `OSError` subclass is recommended but not required. Catch such exceptions without logging them as errors.
21. Avoid arbitrary application-task cancellation as a normal session termination mechanism.
22. Validate all WebTransport events sent by the application and reject events that are invalid for the session state.

A non-RCP server that supports RCP WebTransport must additionally advertise `WEBTRANSPORT_EXTENSION` in the scope `extensions`.


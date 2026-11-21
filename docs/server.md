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
7. Continue delivering available events through `receive()` before acceptance; if the session closes while `receive()` is waiting, deliver `webtransport.disconnect`.
8. Before acceptance, accept only `webtransport.accept` or `webtransport.reject` through `send()`. Raise an error for other events, a second accept, or any event sent after rejection.
9. Permit stream readers to be used before acceptance, but reject stream writer use until acceptance. Apply the same lifecycle restrictions as `receive()` and `send()` while respecting each reader or writer's allowed event types.
10. Deliver incoming datagrams through `webtransport.datagram.received`.
11. Translate `webtransport.datagram.send` into WebTransport datagrams.
12. Deliver client-initiated streams through `webtransport.unidirectional.client` and `webtransport.bidirectional.client`.
13. Implement `Reader` and `Writer` for every WebTransport stream on top of its own stream handling.
14. Start a unidirectional stream when `webtransport.unidirectional.server` is sent and return its `Writer` from `send`.
15. Start a bidirectional stream when `webtransport.bidirectional.server` is sent and return its `(Writer, Reader)` from `send`.
16. Keep `is_closed` accurate for every reader and writer, and mark them closed when the client disconnects, the stream ends or is reset, or the session ends.
17. Emit `WebTransportDataReceived` only from readers and accept `WebTransportDataSend` only on writers.
18. Translate `webtransport.close` into session closure and deliver client-side termination through `webtransport.disconnect`.
19. Raise an exception if the application calls `send()` or `Writer.write()` after the session closes; an `OSError` subclass is recommended but not required. Catch such exceptions without logging them as errors.
20. Avoid arbitrary application-task cancellation as a normal session termination mechanism.
21. Validate all WebTransport events sent by the application and reject events that are invalid for the session state.

A non-RCP server that supports RCP WebTransport must additionally advertise `WEBTRANSPORT_EXTENSION` in the scope `extensions`.


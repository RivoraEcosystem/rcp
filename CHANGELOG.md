# Changelog

## 2.0.0

RCP protocol version 2.0 adds WebTransport. This release is the first stable release of the package.

### Added

- Added RCP protocol version 2.0 (`RCPVersions.VERSION_2`). RCP 2.0 includes everything defined by RCP 1.0.
- Added WebTransport support, which must only be used with RCP version 2.0.
- Added `WebTransportScope` and the `ScopeType.WEBTRANSPORT` scope type. `WebTransportScope` is now part of the `Scope` union.
- Added WebTransport event type enums:
  - `WebTransportConnectionEventType`
  - `WebTransportUnidirectionalStreamEventType`
  - `WebTransportBidirectionalStreamEventType`
  - `WebTransportDatagramEventType`
  - `WebTransportDataEventType`
- Added WebTransport session events:
  - `WebTransportSessionAccept`
  - `WebTransportSessionReject`
  - `WebTransportSessionClose`
  - `WebTransportSessionDisconnect`
- Added WebTransport datagram events:
  - `WebTransportDatagramReceived`
  - `WebTransportDatagramSend`
- Added WebTransport stream events:
  - `WebTransportClientUnidirectionalStreamStarted`
  - `WebTransportCreateServerUnidirectionalStream`
  - `WebTransportClientBidirectionalStreamStarted`
  - `WebTransportCreateServerBidirectionalStream`
- Added WebTransport stream data events:
  - `WebTransportDataReceived`
  - `WebTransportDataSend`
- Added `WebTransportStreamReadEvent` and `WebTransportStreamWriteEvent` type aliases.
- Added the abstract `Reader` and `Writer` classes for WebTransport streams. Servers must implement them on top of their own stream handling.
- Added the `is_closed` property on `Reader` and `Writer`. Servers must keep it accurate when a stream is closed, reset, or the client disconnects.
- Added `WebtransportReceiveEvent` and `WebtransportSendEvent` type aliases.
- Added `WEBTRANSPORT_EXTENSION` for non-RCP servers that support the RCP WebTransport implementation.
- Added server-initiated stream rules: sending `webtransport.unidirectional.server` starts a unidirectional stream and returns its `Writer`, and sending `webtransport.bidirectional.server` starts a bidirectional stream and returns its `(Writer, Reader)`.
- Added WebTransport session isolation requirements.
- Added WebTransport server and application responsibilities.
- Documented the full WebTransport protocol in the README, including examples.

### Changed

- `RCPReceiveEvent` and `RCPSendEvent` now include the WebTransport receive and send events.
- `RCPSendCallable` may now return `tuple[Writer, Reader]` in addition to `None`, so that server-initiated streams can be returned to the application.
- WebTransport is no longer reserved for a future protocol version. It is defined by RCP 2.0.
- Clarified that `HTTP/3 :protocol` is processed as an Extended CONNECT field and selects the WebTransport scope in RCP 2.0.
- Marked the package as `Development Status :: 5 - Production/Stable`.
- Added the `webtransport` package keyword.
- Updated package metadata and internal package version to `2.0.0`.

## 1.0.4

### Added

- Added HTTP/3 pseudo-header definitions:
  - `H3_REQUEST_PSEUDO_HEADERS`
  - `H3_RESPONSE_PSEUDO_HEADERS`
  - `H3_EXTENSION_PSEUDO_HEADERS`
- Added `H3_FORBIDDEN_HEADERS` for HTTP/3 connection-specific headers that must not be transmitted.
- Added explicit HTTP/3 pseudo-header processing rules.
- Added HTTP/3 stream isolation requirements.
- Added explicit `:authority` handling through `HTTPScope.authority`.
- Added HTTP/3 `TE` header handling requirements.
- Added response header validation requirements.

### Changed

- Clarified that HTTP/3 pseudo-headers must be extracted and processed separately from ordinary headers.
- Clarified that pseudo-headers must not be included in `scope["headers"]`.
- Clarified HTTP/3 lowercase header-name requirements.
- Clarified server responsibilities for HTTP/3 request and response validation.
- Removed `extensions` from `LifespanScope`.
- Updated package metadata and internal package version to `1.0.4`.

## 1.0.3

### Added

- Added `authority` to `HTTPScope` for exposing the HTTP/3 `:authority` pseudo-header.
- Added optional `reason` field to `HTTPDisconnectEvent`.
- Exported additional public protocol type aliases:
  - `HTTPReceiveEvents`
  - `HTTPSendEvents`
  - `LifespanReceiveEvents`
  - `LifespanSendEvents`
  - `RCP`
  - `RCPVersions`
  - `RequestMethod`
  - `HTTPScheme`

### Changed

- Expanded the public API to expose protocol definitions intended for framework and server authors.

## 1.0.2

### Fixed

- Removed accidental inclusion of development environment files from package distributions.
- Fixed version inconsistencies between package metadata and internal version information.

### Changed

- Improved package release verification workflow.
- Added cleaner distribution checks before publishing releases.

## 1.0.0

### Added

- Initial RCP release
- HTTP/3 support
- Lifespan protocol
- Typed scopes
- Typed events
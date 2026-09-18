# Changelog

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
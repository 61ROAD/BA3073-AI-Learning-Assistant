# ADR 012: Separate application tokens from reverse-proxy Basic Auth

Status: Accepted
Date: 2026-10-28

## Context

Nginx Basic Auth and the web client both used Authorization. After application
login, Bearer requests replaced the browser's Basic credentials, causing repeated
401 challenges on settings, courses, generation and artifact requests.

## Decision

The web client sends its opaque Bearer session in X-App-Authorization on every
authenticated request. All protected backend route dependencies use one shared
header selector. The legacy Authorization Bearer transport remains supported.
When the app-specific header is present, it wins even if empty or invalid; there
is no fallback to another user's valid session. Password/session validation and
ownership checks remain unchanged. Nginx Basic Auth continues to protect all URLs.

## Deployment

Build the frontend into backend/static before building the Docker image, since
the existing Dockerfile copies that directory rather than building the frontend.
Deploy backend and frontend together. No Nginx auth exception or token rewriting
is needed. This adds an accepted transport without removing legacy API support.

## Validation

Regression tests cover Basic plus application Bearer credentials, legacy clients,
invalid-token precedence, protected metadata/events/artifacts and downloads.
The deployed browser flow still needs verification behind the actual Nginx proxy.

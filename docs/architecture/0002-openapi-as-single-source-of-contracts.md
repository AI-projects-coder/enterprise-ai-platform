# 0002 — Generate contracts from the API, don't hand-maintain a parallel spec

Date: 2026-08-01
Status: Accepted

## Decision

There is no hand-written `packages/contracts` spec. `apps/api` (FastAPI)
generates its OpenAPI schema directly from the Pydantic models already used
for request/response validation. That generated `openapi.json` is the single
source of truth. When the frontend needs a typed client, it's generated from
that file, not written by hand.

## Why

A hand-maintained spec living next to a hand-maintained API is two sources of
truth that will drift the first time someone updates one and forgets the
other — the exact bug a contracts package is supposed to prevent.

## Alternatives considered

- **Hand-written OpenAPI/protobuf in `packages/contracts`, both sides
  implement against it** — the "correct" pattern once there are multiple
  independent services owned by different people/teams, because then neither
  side is the authority. Revisit this when a second Python service
  (`ml-service`, `cloud-deployment-service`) needs to share request/response
  shapes with `apps/api` — at that point a real shared package earns its
  keep.

## Consequences

- `packages/auth-lib` is also deferred for the same reason: there is only one
  Python service today. JWT verification lives directly in
  `apps/api/app/core/security.py` until a second Python service needs it,
  at which point it gets extracted into a shared package used by both.

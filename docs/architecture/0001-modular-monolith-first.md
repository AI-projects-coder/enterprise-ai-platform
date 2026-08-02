# 0001 — Modular monolith first, extract services when a real constraint forces it

Date: 2026-08-01
Status: Accepted

## Decision

The core backend (Auth, Users, AI Gateway, Agent Orchestrator, Memory, Knowledge,
Documents, Notifications, Monitoring, Analytics) is built as **one deployable
FastAPI app** (`apps/api`), internally organized into modules with strict
boundaries: modules talk to each other only through typed interfaces (schemas),
never by importing another module's ORM models or reaching into its database
tables directly.

Three services are standalone from day one instead: `video-service`,
`ml-service`, `cloud-deployment-service` — each has a different resource
profile (GPU, long-running jobs) or security boundary (isolated cloud
credentials) that justifies the operational cost immediately.

## Why

Running 10+ independently deployed services before there is a single real
user creates operational overhead (CI, health checks, logging, versioning per
service) that isn't paid back yet. A monolith with service-shaped internal
boundaries gets the same eventual flexibility at a fraction of the day-one cost.

## Alternatives considered

- **Full microservices from day one** (the original 15-service diagram) —
  rejected: cost (deploy pipelines, network failure handling, service
  discovery, distributed debugging) is paid immediately, before there's
  traffic or a team to justify it.
- **One true monolith with no internal boundaries** — rejected: makes future
  extraction expensive because modules would end up entangled (shared ORM
  models, cross-module SQL joins), turning "extract a service" into "untangle
  a database."

## Consequences

- Every module owns its own Postgres **schema** even though they share one
  instance — this is what keeps later extraction mechanical instead of a
  migration project.
- Every module verifies JWTs independently via a shared verification
  function, so centralizing or later splitting Auth doesn't ripple outward.
- A module gets extracted into its own service only when one of these becomes
  true: it needs independent scaling, a different runtime, or a separate
  on-call owner.

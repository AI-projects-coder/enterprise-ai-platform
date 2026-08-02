# 0003 — Own conversation memory in Postgres, don't use provider-side state

Date: 2026-08-01
Status: Accepted

## Decision

Conversation history is stored and owned by our own `memory` module (Postgres
schema `memory`, tables `conversations` / `messages`). On every chat request,
`ai_gateway` builds the full message history from our own database and sends
it to the LLM provider fresh — it does not rely on any provider-side
conversation-state feature (e.g. Gemini's Interactions API
`previous_interaction_id`, which has Google's servers store and manage the
history for you).

Message roles are stored provider-neutrally (`"user"` / `"assistant"`).
Translating to a specific provider's role naming (Gemini uses `"model"` for
the assistant turn) happens only inside `ai_gateway`, at the one seam that
actually talks to Gemini — `memory` never sees provider-specific naming.

## Why

- **Portability.** We already changed LLM providers once (Anthropic →
  Gemini) with a one-file diff, specifically because `ai_gateway` was the
  only thing that knew about the provider. Provider-side conversation state
  would break that — conversation continuity would live inside Gemini's
  infrastructure, unusable if we switch providers again.
- **Foundation for later phases.** Phase 4 (RAG) and beyond need to read,
  search, and reason over conversation history as data we control. That's
  not possible if the canonical copy lives behind an opaque provider ID.
- **Retention and product control.** We decide how long conversations live,
  who can export them, and how they're displayed — not a third party's
  default retention policy.

## Consequences

- Every chat request re-sends the full history to the provider — token cost
  scales with conversation length. Acceptable for now; summarization/context
  trimming is a problem for a later phase once conversations are long enough
  for it to matter (premature to build against a length we haven't observed).
- `conversations.user_id` is a cross-schema foreign key to `auth.users.id` —
  exactly the kind of coupling ADR 0001 flagged as the cost of extracting a
  module later (a cross-schema FK becomes an application-level reference
  once `auth` or `memory` becomes its own service). Accepted for now because
  we're still validating the product, not scaling infrastructure.

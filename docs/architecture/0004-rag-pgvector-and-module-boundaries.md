# 0004 — RAG: pgvector, naive chunking, and keeping the service layer acyclic

Date: 2026-08-02
Status: Accepted

## Decisions

**1. pgvector, not a dedicated vector database.** Embeddings live in a
`vector` column in our existing Postgres instance (new `knowledge` schema),
queried with pgvector's cosine-distance operator. This was decided back at
the very first architecture discussion, before any code existed — this ADR
just records where it actually landed.

**2. Naive fixed-size chunking, no retrieval framework.** Documents are
split into fixed-length character chunks with overlap, in plain Python — no
LangChain/LlamaIndex-style pipeline. Embeddings come from Gemini's
`gemini-embedding-2` (3072-dim, the model default — no dimension truncation
config yet).

**3. Retrieval is scoped per-user**, the same pattern `memory` already uses
for conversations — a document you upload is only ever retrieved for your
own chats.

**4. Cross-module dependency shape:** `knowledge` and `ai_gateway` each need
something from the other — `knowledge` needs `ai_gateway.embed()` to turn
text into vectors at ingestion time, and the chat flow needs
`knowledge.retrieve_relevant_chunks()` to fetch context before generating.
That's a mutual need, and importing each other's *service* module both ways
would be a real circular import, not just an aesthetic problem.

Resolution: `knowledge/service.py` imports `ai_gateway/service.py` (for
`embed()`) — one directional edge. The other direction is **not** a
service-to-service import: `ai_gateway/router.py` calls
`knowledge.service.retrieve_relevant_chunks()` directly and passes the
result into `ai_gateway.service.handle_chat(..., context=chunks)`.
`ai_gateway/service.py` itself never imports `knowledge` at all — it just
accepts optional context as a plain parameter.

```
ai_gateway/router.py ──▶ knowledge/service.py ──▶ ai_gateway/service.py
        │                                                  ▲
        └──────────────────────────────────────────────────┘
```

## Why

- Every module boundary decision so far has assumed the **service** layer
  stays a strict DAG — no cycles, ever — because a cycle there is a real
  Python `ImportError` risk, not just a style complaint. Routers are the one
  layer allowed to reach into more than one module's service, since nothing
  imports a router back — that's what makes them a safe place to break a
  mutual dependency.
- This is also a preview of what an Agent Orchestrator (phase 5) actually
  does: coordinate calls across several services. Phase 4 is the first time
  we needed that shape for real, not hypothetically.

## Consequences

- One embedding API call per chunk at ingestion time — confirmed live that
  passing a list of texts to `embed_content` does *not* batch them into
  separate vectors, it combines them into one. Looping is correct, not a
  missed optimization.
- No context-length management yet: retrieved chunks are injected via
  Gemini's `system_instruction` on every chat call regardless of how many
  documents exist. Fine at today's scale; will need a real ranking/limit
  strategy once someone uploads enough documents for it to matter.

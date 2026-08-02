# 0005 — Agent tool-calling: a dedicated orchestration module, not always-on RAG

Date: 2026-08-02
Status: Accepted

## Decisions

**1. `/chat` becomes agentic: the model decides when to use a tool, instead
of us always injecting retrieved context.** Phase 4 unconditionally ran a
knowledge search before every single chat message, whether or not it was
relevant. Phase 5 replaces that with real tool calling — the model is given
a `search_knowledge` tool (wrapping `knowledge.retrieve_relevant_chunks`) and
a `get_current_datetime` tool, and only calls them when it decides the
question needs them.

**2. A new `agents` module owns orchestration; `ai_gateway` goes back to
being a pure LLM client.** Phase 4 put RAG coordination directly in
`ai_gateway/router.py` because it was one hardcoded behavior. Multi-step,
multi-tool iteration is real orchestration logic — it now lives in
`agents/service.py`, which sits *above* both `ai_gateway` and `knowledge` in
the dependency graph:

```
ai_gateway/router.py ──▶ agents/service.py ──┬──▶ ai_gateway/service.py (generate, embed)
                                              └──▶ agents/tools.py ──▶ knowledge/service.py
```

`ai_gateway/service.py` no longer imports `memory` for conversation
bookkeeping and no longer knows what a "conversation" is — it exposes one
primitive, `generate(history, tools) -> GenerateResult`, and stays the only
module that imports `google.genai`. All conversation persistence and the
tool-calling loop moved to `agents/service.py`.

**3. Tools are declared provider-neutrally.** `ai_gateway.schemas.ToolDeclaration`
(name/description/JSON-schema parameters) is the contract between `agents`
and `ai_gateway` — `agents/tools.py` never imports `google.genai.types`.
Only `ai_gateway/service.py` translates a `ToolDeclaration` into Gemini's
`types.FunctionDeclaration`. Same boundary principle as the `assistant`→`model`
role translation from phase 2/3, now extended to tool schemas.

**4. Tool execution is request-scoped, not a module-level registry.**
`agents/tools.py::build_tools(db, user_id)` builds a fresh list of tools per
request, with handlers closing over that request's `db` session and
`user_id`. A module-level `TOOLS = [...]` registry was considered and
rejected — it would need the handler to somehow receive a *different*
request's db session on every call, which isn't possible without smuggling
request-scoped state through global mutable variables (a real concurrency
bug under multiple simultaneous users).

**5. Tool turns are persisted as first-class conversation history, using two
new provider-neutral roles.** `memory.Message.role` now also takes
`"tool_call"` and `"tool_result"` (content is a JSON-encoded array, to
support parallel tool calls in one turn). No migration was needed — `role`
was already a plain `String(20)` with no enum/check constraint. History is
always rebuilt from `memory` on every `generate()` call, exactly like plain
chat has done since phase 3 (no provider-side state) — this was extended to
cover tool turns rather than inventing a separate mechanism to replay a live
SDK response object across the `agents` → `ai_gateway` boundary.

**6. The chat UI only ever sees `user`/`assistant` turns.**
`memory.service.list_display_messages` filters `tool_call`/`tool_result`
rows out before they reach `GET /conversations/{id}`; `list_messages` (full
fidelity, used internally to rebuild LLM context) is unchanged. Surfacing
tool activity in the UI (e.g. "🔍 searched knowledge base") is a reasonable
Monitoring-phase feature, not built here.

**7. A hard iteration cap (`MAX_TOOL_ITERATIONS = 5`).** If the model keeps
calling tools instead of answering, the loop forces one final `generate()`
call with `tools=None` so it *must* return text. Without this, a
degenerate tool-calling loop is a cost/availability incident, not just a bad
answer.

## Why

- Always-on retrieval (phase 4) doesn't scale past one tool: every future
  vertical product on the roadmap ("Agents + one new tool/data source") adds
  another capability the model should reach for *conditionally* — deploying
  infra, querying a data source, running an incident lookup. Hardcoding
  "always call knowledge search" doesn't generalize; a tool registry does.
- The dependency-DAG problem phase 4 hit (two leaf modules needing each
  other) gets worse with N tools, each potentially needing a different
  leaf module. Rather than keep resolving it ad hoc at the router layer,
  phase 5 introduces the layer whose entire job is that coordination —
  `agents` — so future tools are additions to `agents/tools.py`, not new
  router-level special cases.

## Consequences

- **`thought_signature` must be captured and replayed.** Live-tested: Gemini
  3.6's function-calling rejects a request with "Function call is missing a
  thought_signature" if a prior `function_call` part is resent without the
  opaque `thought_signature` bytes the model originally attached to it. This
  isn't documented as a hard requirement anywhere we read up front — it
  surfaced as a live 502 on the very first tool-call test. Fixed by reading
  `thought_signature` off the raw response part (not the `response.function_calls`
  convenience property, which discards it), base64-encoding it for JSON
  storage in `memory`, and reattaching it when rebuilding contents.
- **Tool calls cost extra API round-trips** (and extra Gemini free-tier
  quota — hit the 20 req/min free-tier limit during testing). A
  question needing one tool call is now 2 `generate_content` calls instead
  of 1; the iteration cap bounds the worst case at `MAX_TOOL_ITERATIONS + 1`.
- **Retrieval quality now depends on the model choosing to search**, not a
  guaranteed top-K injection. Verified live that it still finds
  document-only facts correctly, but a badly-worded tool description could
  make the model under- or over-use `search_knowledge` — worth revisiting
  with real usage data, same as chunk size/TOP_K in phase 4.

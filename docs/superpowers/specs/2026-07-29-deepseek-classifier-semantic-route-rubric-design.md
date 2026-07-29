# A-080 DeepSeek Classifier Semantic Route Rubric — Written Specification

- Task ID: `A-080-DEEPSEEK-CLASSIFIER-QUALITY`
- Status: Approved
- Date: 2026-07-29 KST
- Human authority: the user's `Q-LLM-015: A / 설계 승인` and `명세 승인`
- Canonical decision: D-133
- Predecessor: immutable A-079 actual evidence, transport/wire `9/9`, oracle `6/9`

## 1. Decision-ID clarification

The assistant accidentally reused `Q-LLM-015`, which the repository already associates with
D-128/A-077. Historical records must not be rewritten. D-133 therefore records this new answer
under the canonical alias `Q-LLM-016-QUALITY`, while preserving the user's literal reply and its
unambiguous quality-correction context.

## 2. Problem statement

A-079 proved that DeepSeek authentication, HTTP transport, response envelope, exact five-string
wire, catalog validation and usage accounting all work: every one of the nine provider cases
returned HTTP 2xx and was accepted by the server parser. Only six decisions matched the fixed
oracle.

The shared classifier prompt currently defines exact keys, enum vocabulary and legal tuple shapes,
but it does not define the semantic boundary between:

- `SUPPORTED`;
- `NO_TOPIC_MATCH`;
- `CIVIC_SCOPE_GAP`;
- `NON_CIVIC`;
- `NEEDS_FOLLOWUP`.

It also does not explicitly tell the model to prefer the narrowest matching catalog row or treat a
coverage label's exclusions as binding. The nine provider cases contain six supported paraphrases
and three out-of-scope civic services. The mismatch count is also three, so missing route semantics
is the strongest hypothesis, but aggregate-only retention means this specification does not claim
which individual cases failed.

## 3. Goal and non-goals

### Goal

Add a compact provider-neutral semantic rubric to the existing bounded classifier prompt so an
eligible masked question is mapped to the correct closed route and, for `SUPPORTED`, the most
specific governed catalog row.

### Non-goals

- changing the exact five-string response contract or uppercase `NONE`;
- changing parser, catalog, grounding, PII, storage or fallback policy;
- adding provider-specific facts, source generation, embeddings or dependencies;
- changing DeepSeek model, timeout, retry, concurrency, output cap or final-answer provider;
- changing public API, DB, official data, Web, deployment or remote/public/free-input scope;
- rerunning A-079 or performing any A-080 provider call under this design approval.

## 4. Semantic rubric

The prompt must communicate these exact meanings:

| Route | Meaning |
|---|---|
| `SUPPORTED` | Exactly one current catalog row covers the question. Use that row's intent, topic ID and coverage ID. |
| `NO_TOPIC_MATCH` | The question belongs to one supported intent, but no current catalog row covers the requested fact or procedure. |
| `CIVIC_SCOPE_GAP` | The question is a government or administrative service, but it is outside all supported intents. |
| `NON_CIVIC` | The question is not a government or administrative service. |
| `NEEDS_FOLLOWUP` | Missing or ambiguous detail prevents a safe route or topic choice; use only an allowed pending slot. |

Selection precedence is:

1. safety and privacy remain server-owned and provider-free;
2. choose the narrowest catalog row that covers the question;
3. if the supported intent is clear but no row covers it, choose `NO_TOPIC_MATCH`;
4. if it is another government service, choose `CIVIC_SCOPE_GAP`;
5. if it is not a government service, choose `NON_CIVIC`;
6. use `NEEDS_FOLLOWUP` only when an allowed missing detail blocks a safe choice.

Coverage-label exclusions are binding. The provider cannot broaden a row merely because an example
shares keywords with the question.

## 5. Architecture and boundaries

The rubric stays in `sejong_ai_api.llm.classifier_prompt`, which is shared by the selectable
Upstage and DeepSeek classifier adapters. Provider-specific prompt forks are prohibited.

The request still contains only:

- one privacy-safe masked question;
- the current ACTIVE/OFFICIAL topic catalog;
- non-factual coverage labels;
- at most two approved examples per topic;
- closed wire-shape guidance.

The response still passes through the existing exact-key, string-type, enum, route-shape,
identifier and request-local catalog validators. Provider output never creates facts, sources,
offices, storage policy or candidate eligibility.

## 6. Prompt budget and cost

The semantic rubric replaces and compresses the existing system instruction rather than appending
an unbounded block. Acceptance requires:

- the existing approved-catalog prompt bound remains at most `4096` conservative characters for
  the 20-topic/256-character test profile;
- the real 19-topic A-079 profile remains within the same bound;
- DeepSeek's UTF-8 plus framing upper bound remains at most `16384` tokens;
- output remains `128`, retry `0`, concurrency `1`;
- provider-call count is unchanged: only deterministically ambiguous questions may call once.

The measured pre-change real 19-topic prompt range is `3718..3737` conservative characters and
`6021..6068` UTF-8 content bytes. These are local, provider-free measurements, not billing claims.

## 7. TDD acceptance

Implementation begins only after an approved execution plan. The user approved this written
specification on 2026-07-29 KST.

Required RED/GREEN coverage:

1. a prompt test fails until all five route meanings and precedence are present;
2. the prompt explicitly requires the narrowest matching row and binding exclusions;
3. all tuple shapes, four supported intents and uppercase `NONE` remain present;
4. approved 19/20-topic prompts remain within both provider bounds;
5. DeepSeek and Upstage request tests continue using the same shared messages;
6. parser, first-failure precedence and non-retention suites remain unchanged and green;
7. the fixed 20-case selection remains `20/0`, provider-free/provider `11/9`;
8. policy/privacy provider outbound remains `0`;
9. controlled oracle doubles remain `9/9`.

Offline tests can prove prompt content, bounds, routing contracts and fallback behavior. They
cannot prove live model accuracy.

## 8. Evidence and actual-run boundary

A-079 reports and leases remain immutable and must never be rerun or overwritten. If offline
implementation and independent review pass, a new A-080 evidence identity may be proposed.

Any live A-080 provider evaluation requires a separate explicit human approval defining:

- exact clean source SHA;
- one new offline identity and one new actual identity;
- the same fixed 20 selected cases, 11 provider-free and exactly 9 provider calls;
- retry/rerun `0/0`, concurrency `1`, output `128`, cost cap USD `0.20`;
- aggregate-only reporting and all six retention counters at `0`;
- no automatic merge.

## 9. Version impact

Design checkpoint:

- prompt set remains `0.4.3-explicit-route-matrix`;
- documentation advances to `2.32.2-a080-quality-plan`;
- product/API/contracts/Web/DB/data/dependencies remain unchanged.

Planned implementation, only after approval:

- prompt set `0.4.4-semantic-route-rubric`;
- application and test versions advance according to the implementation plan;
- no public contract or schema version change.

## 10. Rollback and handoff

Before implementation, rollback is a documentation-only revert. After implementation, restore the
previous shared prompt and set `CLASSIFIER_PROVIDER=disabled`; no DB or data recovery is needed.
A new developer starts with D-132/D-133, ADR-0028, the A-079 aggregate reports and this
specification. They must not infer per-case A-079 failures from the aggregate `6/9`.

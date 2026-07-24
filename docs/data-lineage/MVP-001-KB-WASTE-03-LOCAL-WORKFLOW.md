# MVP-001 KB-WASTE-03 local workflow lineage

- Status: local/private runtime evidence only — 2026-07-22 KST PASS
- Scope: one approved candidate workflow from initial 19 ACTIVE to final 20 ACTIVE
- Source boundary: existing PM-approved `KB-WASTE-03` official source metadata only
- Related: [MVP-001 plan](../superpowers/plans/2026-07-22-four-day-local-private-core-loop-mvp.md),
  [MVP implementation note](../implementation-notes/IMP-20260722-004-q-mvp-001-4일-local-private-핵심-개선-루프-명세와-실행.md),
  [DATA-SEED-002 `.2` lineage](DATA-SEED-002-0.1.0-initial.2.md)

## Lineage boundary

`0.1.0-initial.2` remains the immutable official filesystem release and local dispatcher projection
of 19 KB / 3 office / 10 mapping. This document does **not** amend that release, its approval
manifest, source URLs, facts, hashes or schema. It records only the later local application workflow
that materialized the already approved `KB-WASTE-03` through the governed candidate path.

No new source data was fetched or changed. No raw citizen question, masked question text, answer
snapshot, DSN, token or provider payload is reproduced here.

## Actual local/private evidence

The clean regression started from 19 ACTIVE and performed, in order:

1. canonical bed-frame request → `INSUFFICIENT_GROUNDING` fallback;
2. same logical K1 business replay with a distinct correlation → same safe fallback, not a second
   business action;
3. exactly one NEW failure → OPERATOR reason confirmation → candidate creation without client
   `public_id` → submit;
4. same-writer fake approver blocked; distinct `PM-LOCAL-001` approves;
5. K2 requery → SUCCESS with exact server-bound `KB-WASTE-03` source; old K1 still returns the
   original fallback; and
6. final DB projection → ACTIVE 20, four categories × 5, target KB exactly once.

The application `/ready=200` probe succeeded before and after this flow on the final local DB.
The evidence is local/private only: it is not public admin, remote DB, deployment, DeepSeek actual
use, a new official release, or an update to immutable `.2`.

## Governance, privacy and rollback

- Server-side source binding supplies source name/URL/verified date; no LLM created them.
- Author and approver are distinct; self-approval remained blocked.
- The regression preserves raw-question 0 and audit answer-snapshot 0 boundaries.
- Local rollback/reapply evidence covers the capability migrations; reverting this runtime workflow
  never edits `.1` or `.2`. A future official-data change needs its own approval and immutable
  successor release.

## Remaining evidence

This runtime flow does not replace the fresh whole-repository closeout now rerunning. It also does
not satisfy the final sample-20 report, 100-user smoke, automatic backup, DeepSeek, public deployment
or reserved public `00700` gates.

## 2026-07-24 Q-PM-DEMO-001=B append-only evidence

This checkpoint preserves all 2026-07-22 evidence above and adds one clean local rehearsal from
immutable `.2` initial ACTIVE 19. The backend runner proved `PERSONAL_LOOKUP` changed neither
`interaction_events` nor `failed_questions`; this is a two-table count statement, not a claim that
every database table was unchanged. A separate `INSUFFICIENT_GROUNDING` request increased those
counts by exactly one, then completed reason confirmation, candidate submit, same-writer rejection,
different PM approval, target activation and same-query SUCCESS.

An opt-in desktop browser independently exercised actual `/chat`, same-origin Web transport, FastAPI,
the local DB and actual `/admin`, ending with the exact server-bound public source ID, official title
and URL. Candidate `activated_kb_id` remained the internal UUID identity; it was not treated as the
public KB ID. A final read-only probe confirmed ACTIVE 20, target exactly once and `/ready=200`.

The browser uses only approved non-PII fixed fixture text in in-memory UI. Local gitignored failure
trace/screenshots may exist during diagnosis and are not the backend no-storage proof. Provider/key/
network use, remote DB, public deployment, new official release and immutable `.2` modification were
all zero.

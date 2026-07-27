# CHAT-HYBRID-RAG-001 — offline Hybrid RAG UAT

- Date: 2026-07-27 (KST)
- Mode: offline; real redaction, deterministic classification, ACTIVE/OFFICIAL catalog, retrieval, grounding, response, and repository-write boundaries
- Provider: closed fake classifier only; no network request, provider payload, secret, or citizen text was written to this report
- Fixture: `apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json` (`SYNTHETIC_CHAT_UAT`)

## Result

| Acceptance | Observed result |
|---|---:|
| Frozen Hybrid RAG scenarios | 48/48 route, intent, topic, provider, and storage assertions passed |
| UAT fixture/invariant tests | 3/3 passed |
| Approved official examples | 57/57 grounded records passed |
| Approved sample questions | 20/20 passed |
| Frozen classifier evaluation | 60/60 correct; skip 0 |
| Focused pytest total | 86 passed; skipped 0 |

The runtime ACTIVE/OFFICIAL intersection loaded from immutable official `.2` is 19 topics, not 20; `KB-WASTE-03` is absent from that release. The fixture therefore uses only the 19 current topics and does not modify official data, seed data, or production behavior.

## Frozen group distribution

| Group | Cases | Provider expected/actual |
|---|---:|---:|
| `PARAPHRASE_SUCCESS` | 20 | 15/15 |
| `TOPIC_DISTINCTION` | 8 | 0/0 |
| `GENERIC_FOLLOWUP` | 4 | 0/0 |
| `NO_TOPIC_GROUNDING` | 4 | 0/0 |
| `SCOPE_OR_NON_CIVIC` | 4 | 3/3 |
| `CONTEXT` | 4 | 0/0 |
| `PRIVACY_POLICY` | 4 | 0/0 |
| Total | 48 | 18/18 |

The actual-selector subset is exactly 20: paraphrase 8, topic distinction 4, no-topic-or-followup 4, and scope-or-non-civic 4. Every privacy case is excluded from that subset.

## Aggregate case-ID evidence

`Route/topic` and `provider` columns are expected/actual. `Storage` is the observed repository delta class. Privacy rows intentionally contain only IDs and aggregate boundary results, never question text.

| Case IDs | Route/topic | Provider | Storage |
|---|---|---:|---|
| HR-001 | `SUPPORTED` / `KB-MOVE-01` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-002 | `SUPPORTED` / `KB-MOVE-03` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-003 | `SUPPORTED` / `KB-MOVE-02` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-004 | `SUPPORTED` / `KB-MOVE-04` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-005 | `SUPPORTED` / `KB-CERT-01` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-006 | `SUPPORTED` / `KB-CERT-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-007 | `SUPPORTED` / `KB-CERT-03` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-008 | `SUPPORTED` / `KB-CERT-04` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-009 | `SUPPORTED` / `KB-CERT-05` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-010–HR-011 | `SUPPORTED` / `KB-WASTE-01` | 1/1 each | `VALUE_FREE_SUCCESS` |
| HR-012 | `SUPPORTED` / `KB-WASTE-02` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-013 | `SUPPORTED` / `KB-WASTE-01` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-014 | `SUPPORTED` / `KB-WASTE-04` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-015 | `SUPPORTED` / `KB-WASTE-05` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-016 | `SUPPORTED` / `KB-TAX-01` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-017 | `SUPPORTED` / `KB-TAX-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-018 | `SUPPORTED` / `KB-TAX-04` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-019 | `SUPPORTED` / `KB-TAX-05` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-020 | `SUPPORTED` / `KB-TAX-03` | 1/1 | `VALUE_FREE_SUCCESS` |
| HR-021 | `SUPPORTED` / `KB-WASTE-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-022 | `SUPPORTED` / `KB-WASTE-01` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-023 | `SUPPORTED` / `KB-WASTE-04` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-024 | `SUPPORTED` / `KB-WASTE-05` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-025 | `SUPPORTED` / `KB-MOVE-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-026 | `SUPPORTED` / `KB-MOVE-03` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-027 | `SUPPORTED` / `KB-CERT-01` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-028 | `SUPPORTED` / `KB-TAX-03` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-029–HR-032 | `NEEDS_FOLLOWUP` / none | 0/0 each | `VALUE_FREE_FOLLOWUP` |
| HR-033–HR-036 | `NO_TOPIC_MATCH` / none | 0/0 each | `MASKED_GROUNDING_FAILURE` |
| HR-037 | `CIVIC_SCOPE_GAP` / none | 1/1 | `VALUE_FREE_SCOPE` |
| HR-038 | `NON_CIVIC` / none | 0/0 | `VALUE_FREE_SCOPE` |
| HR-039–HR-040 | `CIVIC_SCOPE_GAP` / none | 1/1 each | `VALUE_FREE_SCOPE` |
| HR-041 | `SUPPORTED` / `KB-MOVE-01` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-042 | `SUPPORTED` / `KB-WASTE-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-043 | `SUPPORTED` / `KB-CERT-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-044 | `SUPPORTED` / `KB-WASTE-05` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-045–HR-046 | `PERSONAL_LOOKUP` / none | 0/0 each | `VALUE_FREE_PRIVACY` |
| HR-047–HR-048 | `LEGAL_JUDGMENT` / none | 0/0 each | `VALUE_FREE_PRIVACY` |

## Storage boundary interpretation

- `VALUE_FREE_SUCCESS`: one metadata interaction; masked question absent; selected source ID only.
- `VALUE_FREE_FOLLOWUP`: one metadata interaction; no source or question text.
- `MASKED_GROUNDING_FAILURE`: one grounding-failure interaction with the safe masked question only; no source.
- `VALUE_FREE_SCOPE` and `VALUE_FREE_PRIVACY`: no interaction row. Civic scope-gap uses its isolated safe queue; non-civic, personal lookup, and legal judgment write neither question nor provider data.

## Command

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_hybrid_rag_uat.py `
  apps/api/tests/chat/test_official_examples.py `
  apps/api/tests/chat/test_sample_questions_20.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q
```

Observed output: `86 passed in 1.08s`.

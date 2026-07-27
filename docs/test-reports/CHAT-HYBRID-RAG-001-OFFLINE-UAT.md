# CHAT-HYBRID-RAG-001 — offline Hybrid RAG UAT

- Date: 2026-07-27 (KST)
- Mode: offline; real redaction, deterministic classification, ACTIVE/OFFICIAL catalog, retrieval, grounding, response, and repository-write boundaries
- Provider: closed fake classifier only; no network request, provider payload, secret, or citizen text was written to this report
- Fixture: `apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json` (`SYNTHETIC_CHAT_UAT`)

## Result

| Acceptance | Observed result |
|---|---:|
| Frozen Hybrid RAG scenarios | 48/48 route, intent, topic, provider, and storage assertions passed |
| UAT fixture/invariant and server-validation tests | 8/8 passed |
| Approved official examples | 57/57 grounded records passed |
| Approved sample questions | 20/20 passed |
| Frozen classifier evaluation | 60/60 correct; skip 0 |
| Focused pytest total | 86 passed; skipped 0 |

The runtime ACTIVE/OFFICIAL intersection loaded from immutable official `.2` is 19 topics, not 20; `KB-WASTE-03` is absent from that release. The fixture therefore uses only the 19 current topics and does not modify official data, seed data, or production behavior.

Provider-routed cases use a separate fixed closed-provider script keyed only by case ID/question;
the script does not read fixture `expected_*` fields. The UAT mutates the HR-001 expected topic in
memory and proves the scripted response remains the original topic, making the mutated oracle fail.
Server-validation negatives prove rejection of an intent mismatch, coverage mismatch, and
catalog-external ID; a topic from another intent is covered as the wrong-topic rejection. A
catalog-valid alternative topic within the same intent remains an approved provider semantic choice
and is not claimed to be server-rejected.

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
| HR-029 | `NEEDS_FOLLOWUP` / certificate options + `CERTIFICATE_KIND` | 0/0 | `VALUE_FREE_FOLLOWUP` |
| HR-030 | `NEEDS_FOLLOWUP` / move options + `TOPIC_CHOICE` | 0/0 | `VALUE_FREE_FOLLOWUP` |
| HR-031 | `NEEDS_FOLLOWUP` / waste options + `TOPIC_CHOICE` | 0/0 | `VALUE_FREE_FOLLOWUP` |
| HR-032 | `NEEDS_FOLLOWUP` / property-tax options + `TOPIC_CHOICE` | 0/0 | `VALUE_FREE_FOLLOWUP` |
| HR-033–HR-036 | `NO_TOPIC_MATCH` / none | 0/0 each | `MASKED_GROUNDING_FAILURE` |
| HR-037 | `CIVIC_SCOPE_GAP` / none | 1/1 | `VALUE_FREE_SCOPE` |
| HR-038 | `NON_CIVIC` / none | 0/0 | `VALUE_FREE_SCOPE` |
| HR-039–HR-040 | `CIVIC_SCOPE_GAP` / none | 1/1 each | `VALUE_FREE_SCOPE` |
| HR-041 | `SUPPORTED` / `KB-MOVE-01` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-042 | `SUPPORTED` / `KB-WASTE-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-043 | `SUPPORTED` / `KB-CERT-02` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-044 | `SUPPORTED` / `KB-WASTE-05` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-045 | `SUPPORTED` / `KB-MOVE-01` | 0/0 | `VALUE_FREE_SUCCESS` |
| HR-046 | `PERSONAL_LOOKUP` / none | 0/0 | `VALUE_FREE_PRIVACY` |
| HR-047–HR-048 | `LEGAL_JUDGMENT` / none | 0/0 each | `VALUE_FREE_PRIVACY` |

## Frozen generic followups

| Case ID | Exact options | Signed context pending slot |
|---|---|---|
| HR-029 | 주민등록등본 발급; 주민등록초본 발급; 등본과 초본의 차이 | `CERTIFICATE_KIND` |
| HR-030 | 전입신고 개요·신청방법; 방문 전입신고 준비물; 온라인 전입신고; 주민등록 관련 통보서비스 | `TOPIC_CHOICE` |
| HR-031 | 대형폐기물 배출신청 절차; 대형폐기물 결제·스티커·변경·환불 안내; 매트리스 배출 수수료; 대형폐기물 배출요일·수거 문의 | `TOPIC_CHOICE` |
| HR-032 | 지방세 온라인 납부 공식 경로 안내; 자동차세 개인 고지 확인·납부의 공식 로그인 경로; 지방세 납세증명서 발급 안내; 지방세 세목별 과세증명서 발급 안내; 지방세 납부확인서 발급 안내 | `TOPIC_CHOICE` |

## Storage boundary interpretation

- `VALUE_FREE_SUCCESS`: one metadata interaction; masked question absent; selected source ID only.
- `VALUE_FREE_FOLLOWUP`: one metadata interaction; no source or question text.
- `MASKED_GROUNDING_FAILURE`: one grounding-failure interaction with the safe masked question only; no source.
- `VALUE_FREE_SCOPE` and `VALUE_FREE_PRIVACY`: no interaction row. Civic scope-gap uses its isolated safe queue; non-civic, personal lookup, and legal judgment write neither question nor provider data.

For every privacy case, a strict synthetic-phone regex extracts exactly one canonical value. The
redactor must emit `[전화번호]`, and the canonical value is absent from closed-provider inputs,
repository writes, response representation, report text, and captured log representation. HR-045
specifically proves a masked ordinary move-guidance success with provider use 0 and no failed/scope
row; the remaining personal/legal policy cases preserve provider use 0.

## Command

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_hybrid_rag_uat.py `
  apps/api/tests/chat/test_official_examples.py `
  apps/api/tests/chat/test_sample_questions_20.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q
```

Observed output: `91 passed in 1.30s`.

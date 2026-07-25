# IMP-20260725-005 — LLM-003 grounded live chat implementation

- Date/Time (KST): 2026-07-26T02:55:00+09:00
- Task ID: LLM-003 / Task 8 documentation lane
- Type: implementation-documentation-closeout
- Status: Done — offline implementation, final provider-disabled root gate, manifest/package/INDEX integration complete; local actual remains Pending human gate
- Author/Agent: Codex Task 8 documentation lane
- Branch: `codex/LLM-003-grounded-live-chat-design`
- Base commit: D-074 execution base `de1ee096d6e27b0a326dfaa0c93f72baf0c5f1c0`
- Related plan/ADR/RFP: [LLM-003 plan](../superpowers/plans/2026-07-25-grounded-live-chat-generation.md), [design](../superpowers/specs/2026-07-25-grounded-live-chat-generation-design.md), [ADR-0023](../adr/0023-grounded-upstage-local-chat-generation.md), [RFP matrix](../source-of-truth/RFP_MATRIX.md)

## 1. 사용자 요청과 완료 기준

### 요청

Synchronize LLM-003 Task 8 documentation from actual implementation/reviews, repair identified
source-of-truth contradictions, record the final provider-disabled root gate, and create reproducible
report/note evidence while preserving the separate human provider-actual boundary.

### Acceptance Criteria

- Preserve D-071 historical FAIL and D-072~D-074 exactly; add no D-075.
- State offline task evidence separately from the final root gate and optional provider actual.
- Record no migration, data, dependency or lockfile change.
- Make public/remote/real-institution use remain prohibited.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | D-072~D-074 human approver; Tasks 1~7 implementers/reviewers; Task 8 closeout/controller. |
| When — 언제 | 2026-07-25 implementation evidence; 2026-07-26 KST documentation synchronization. |
| Where — 어디서 | local/private repository documentation, contracts/runtime/Web evidence and ignored local actual boundary. |
| What — 무엇을 | Grounded `solar-pro3` SUCCESS generation attempt with server-owned fact/source/office and TEMPLATE fallback; closeout documentation. |
| Why — 왜 | Question-adapted local demo wording without weakening approved official KB or privacy boundaries. |
| How — 어떻게 | Typed contract, request-local facts, strict profile, one-attempt adapter, post-grounding idempotency, optional local composition, Web disclosure, task-scoped tests/reviews. |
| How much — 어느 정도 | offline implementation/gates complete; no DB migration/data/dependency/lockfile; actual network remains human Pending. |

## 3. 시작 전 상태

- Related files: LLM-003 design/plan, ADR-0023, Task 1~7 reports/reviews and source-of-truth documents.
- Existing behavior: D-074 start checkpoint still stated `Task 1 starting`; API and contract had already moved to `3.2.0-draft` in tracked implementation.
- Found conflict: `PRIVACY_POLICY.md` described active `PRIVACY_UNRESOLVED` as future-only despite its active contract/route policy.
- Git state: concurrent Task 8 controller work may modify API idempotency files/tests; this lane does not alter them.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-048 | policy | local citizen provider boundary | Policy resolved; offline implementation complete, local actual Pending | public/remote stays prohibited |
| V-LLM-003 | controller decision | Whether package metadata mirrors shared-contract axis `0.5.0` | Resolved/integrated; package metadata is `0.5.0` | manifest/package alignment |
| G-LLM-003 | human gate | Local actual provider timing/cost/key handling | Pending human; no key/network action | provider actual evidence |

## 5. 설계 결정과 대안

### 선택

The model proposes only a bounded summary and server-issued fact IDs. Server validation/materialization
owns official text, sources, offices and policy; any failure produces a whole deterministic template.

### 이유

This retains ACTIVE/OFFICIAL authority and fail-closed privacy behavior while allowing an explicitly
enabled local/private demo path.

### 고려했지만 선택하지 않은 대안

- Provider-generated facts/sources or partial generated/template mixing: rejected by D-072/ADR-0023.
- Default-enabled provider or public/remote operation: prohibited.
- New migration/dependency/data mutation: out of plan scope.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| Contract/response | SUCCESS-only `answer_mode=GENERATED|TEMPLATE`, API `3.2.0-draft` | disclose authorship mode without changing fallback branches |
| LLM facts/settings/adapter | server-issued IDs, strict profile, one attempt/8s/cap 30 | bound model authority and provider use |
| Chat/idempotency/local | post-grounding generator, durable same-key dedupe, lazy optional runtime | no duplicate call; startup/readiness call 0 |
| Web | visible generated/template label, static disclosure, strict source fail-closed guard | accessible explanation and source integrity |
| Documentation | report, source-of-truth fixes and status synchronization | preserve evidence and the pending human provider boundary |

### 데이터 흐름/상태 변화

safe mask → deterministic supported intent → ACTIVE/OFFICIAL retrieval → grounding → optional
one-attempt provider → strict draft/fact validation → server materialization `GENERATED`; every
disabled/error/drift path returns full `TEMPLATE`. Excluded policy and FOLLOWUP paths call provider 0.

### 오류·빈 상태·롤백

Timeout, transport, malformed JSON/schema, unknown/duplicate fact IDs, drift, cap and idempotency
uncertainty fail closed. Disable `UPSTAGE_GROUNDED_CHAT_MODE`, remove the ignored key and restart to
return to TEMPLATE-only behavior; code rollback is reverse Task 8→1 revert only if required.

## 7. 버전 전후

Before/After values are actual manifest/package values after Task 8 integration.

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.5.0 | 2.5.0 | D-072 design already recorded |
| Repo guidance | 1.7.8 | 1.7.8 | no guidance policy change |
| Application | 0.8.1-main-stabilization | 0.9.0-grounded-local-chat | grounded runtime |
| Web | 0.5.1-local-dev-origin | 0.6.0-answer-mode | Web label/disclosure |
| API | 3.1.0-draft | 3.2.0-draft | SUCCESS answer mode |
| Shared contracts | 0.4.0 | 0.5.0 | generated shared response type |
| DB schema | 0.4.0-local | 0.4.0-local | no migration |
| Official data | 0.1.0-initial.2 | 0.1.0-initial.2 | no official-data mutation |
| Mock data | 0.0.0-not-populated | 0.0.0-not-populated | no mock-data mutation |
| Prompt set | 0.1.0-upstage-solar-pro3-synthetic | 0.2.0-grounded-live-chat | bounded citizen profile |
| Test suite | 1.5.1-local-dev-origin | 1.6.0-grounded-live-chat | grounded regression coverage |
| Documentation | 2.19.2 | 2.20.0 | report/note/source-of-truth sync |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 1 contract/API focused gates | PASS | shared contracts 89; API 76 | `.superpowers/sdd/.../task-1-report.md` |
| Task 2 focused/LLM | PASS | 43 in 0.14s; LLM 184 + 1 existing warning | `task-2-report.md` |
| Task 3 settings | PASS | 31 + 6 subtests | `task-3-report.md` |
| Task 4 LLM regression | PASS | 115 focused; 229 + 1 existing warning | `task-4-report.md` |
| Task 5 chat/idempotency | PASS | chat 189; related 96; focused 26 | `task-5-report.md` |
| Task 6 full API | PASS | 1,923; 8 explicit DB skips; 5 subtests; 10.14s | `task-6-report.md` |
| Task 7 Web | PASS | 12 files / 56 tests; lint/typecheck/build | `task-7-report.md` |
| Independent reviews | PASS after fixes | final security re-review C0/I0/M0; focused 85, chat 202, DB 168 (8 DB-only skips), provenance 57, controller 115, retrieval/static 5; Ruff/Mypy PASS | task reports/reviews |

### 미실행 검증과 이유

- Final `scripts/verify.ps1 -Offline`: PASS; provider-disabled/unset-key, `2026-07-26T02:39:05+09:00`→`02:49:42+09:00`, 637.7s, stdout 2006 bytes, stderr 0; all listed gates PASS.
- Optional local actual provider: Pending human gate; no key read, no provider network request.
- Playwright 390/430/desktop: initial 9/12 strict-locator ambiguity only; `7dd74f0` exact locator fix, rerun 12/12 PASS.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: raw/masked question, provider body, key, transcript/context and correlation data remain excluded; only safe idempotent final response is a narrow existing exception.
- Security: provider disabled by default, local/private only, no startup/readiness request, no CANDIDATE/mock/non-official prompt data.
- Accessibility: text labels and disclosure are not color-only; invalid source fields render the existing alert before answer content.
- Performance/cost: maximum one 8-second attempt, no hidden retry, concurrency 1 and process cap 30; actual cost remains Pending.

## 10. 데이터와 출처 영향

- Official data: unchanged (`0.1.0-initial.2`).
- mock/AI 생성: no mock-data mutation; provider output is not authoritative data.
- schema/lineage: no migration; existing idempotency storage only.
- verified date: server derives source metadata from approved record; model cannot issue it.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Local provider actual timing, ignored key handling and cost acceptance remain human decisions.
- Local provider actual requires human timing, ignored key handling and cost acceptance.
- Public/remote/real-institution operation needs separate privacy, security, legal, cost and deployment approval.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- Fact ID validation and materialization are request-local and fail closed.
- Lazy local composition keeps provider imports and HTTPX out of default app startup.
- Test doubles provide task-scoped provider evidence without a real key or network.

## 13. 인수인계·재현·롤백

### 재현

Read the final report for recorded gates. For optional local actual only after human approval, follow
[LLM-003 local runbook](../runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md).

### 롤백

Disable chat mode, use disabled provider mode, remove the ignored key and restart; verify TEMPLATE.
No DB/data rollback is required. Revert all additive contract/runtime/Web changes together if code
rollback is necessary.

### 다음 개발자 시작점

Obtain human authorization before any local actual call; then follow the local runbook.

## 14. 남은 위험·미해결 질문·다음 단계

- Actual provider schema quality, latency and cost are unknown until human local gate.
- Provider schema quality, latency and cost remain unknown until the human local gate.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증 — task-scoped evidence, final provider-disabled root gate and browser E2E PASS
- [x] source-of-truth/계약/버전 동기화 — manifest/package/INDEX integrated
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

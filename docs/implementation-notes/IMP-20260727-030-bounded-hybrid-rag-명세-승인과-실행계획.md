# IMP-20260727-030 — Bounded Hybrid RAG 명세 승인과 실행계획

- Date/Time (KST): 2026-07-27T15:57:18+09:00
- Task ID: CHAT-HYBRID-RAG-001
- Type: decision-plan
- Status: Decision-only Done — execution plan Review
- Author/Agent: Codex primary architecture/documentation agent
- Branch: codex/LOCAL-RUN-GUIDE-001
- Base commit: f23e2aa
- Related plan/ADR/RFP:
  - `docs/superpowers/specs/2026-07-27-bounded-hybrid-rag-conversation-design.md`
  - `docs/superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md`
  - `docs/adr/0027-active-topic-catalog-and-coverage-grounding.md`
  - D-096~D-103, A-053/A-060/A-064~A-068

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 설계 1~3부를 통합한 Bounded Hybrid RAG written specification을 `명세 승인`으로
확정했다. 승인 내용을 결정·ADR·source-of-truth·ambiguity·TASKS·version에 반영하고, 제품 코드를
수정하기 전에 실제 파일과 현재 인터페이스에 맞는 RED/GREEN 실행계획을 작성한다.

### Acceptance Criteria

- written specification이 Approved로 전환된다.
- 새 인간 blocker를 만들지 않고 D-103으로 승인 경계를 기록한다.
- exact 파일, 인터페이스, 실패 테스트, 최소 구현, 검증 명령, 커밋 경계가 있는 실행계획을 만든다.
- ACTIVE/OFFICIAL-only, provider 전 PII, server-owned source, 저장 정책을 계획에 유지한다.
- 새 dependency, DB migration, public field, official `.2`, 제품 코드는 변경하지 않는다.
- 계획 자체를 검사하고 구현 노트와 INDEX를 갱신한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 명세 승인자, Codex가 계획·권위 문서 작성자, 후속 primary/subagent가 구현·검토자 |
| When — 언제 | 2026-07-27 15:57 KST 시작, 같은 작업 턴에 계획·검증·local commit |
| Where — 어디서 | isolated worktree `.worktrees/actual-p0-ux-gaps`, docs/ADR/TASKS/versions |
| What — 무엇을 | Bounded Hybrid RAG 명세 승인 기록과 11-task RED/GREEN 실행계획 |
| Why — 왜 | lexical-only retrieval의 paraphrase 실패와 topic 혼동을 공식 KB 경계 안에서 개선 |
| How — 어떻게 | 현재 API/Web/LLM/context/contract/test 파일을 대조하고 slice별 파일·인터페이스·명령·commit을 고정 |
| How much — 어느 정도 | 문서/메타 파일만 변경, product/API/DB/data/provider runtime 0 |

## 3. 시작 전 상태

- 관련 파일:
  - 승인 대기 명세와 ADR-0027
  - `classification.py`, `classifier_contracts.py`, `classifier_prompt.py`,
    `upstage_classifier.py`
  - `retrieval.py`, `grounding.py`, `service.py`, `context.py`, `local.py`
  - `chat-screen.tsx`, `RegionSelect.tsx`, `FollowupCard.tsx`, `AnswerCard.tsx`
  - contracts, LLM limits/settings, current API/Web/UAT tests
- 기존 동작:
  - local Upstage classifier는 intent 중심 4-field JSON이며 catalog/coverage를 받지 않는다.
  - retrieval은 intent 안 lexical rank 뒤 top record를 사용하고 grounding은 boolean
    `allow_contextual_detail`을 받는다.
  - 지역 선택은 첫 대화 화면에만 보이고 `새 대화`가 region도 초기화한다.
  - local provider ledger는 20/30/40 attempt만 제한하며 actual cost pre-reservation이 없다.
- 발견한 충돌/부채:
  - approved D-097과 현재 Web region reset 동작이 다르다.
  - D-098의 certificate 3단계 구조와 현재 flat option 동작이 다르다.
  - historical provider acceptance profile과 새 local interactive profile을 분리해야 한다.
- Git 상태:
  - 시작 SHA `f23e2aa`
  - 시작 worktree clean
  - 현재 branch는 이전 local run guide 이름이므로 구현 시작 때 승인 계획에 맞는
    `codex/CHAT-HYBRID-RAG-001` 분기가 필요하다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-064 | 해결 | 자유 표현 검색 방식 | approved max-20 closed catalog + typed evidence | API/LLM/retrieval |
| A-065 | 해결 | region 유지 범위 | same-tab React memory only | Web/accessibility |
| A-066 | 해결 | certificate hierarchy | first 3 + KB-CERT-01 related questions | chat/Web |
| A-067 | 해결 | provider lifetime/cost | 80/100/160 + USD0.20 pre-reservation | local LLM |
| A-068 | 해결 | 새 factual data 필요 여부 | current facts first; non-factual metadata only | data lineage |

추가 A/Blocker는 발견되지 않았다. public/remote, new factual KB와 production rate limiting은
명시적 비범위다.

## 5. 설계 결정과 대안

### 선택

request-local ACTIVE/OFFICIAL catalog, closed Upstage topic+coverage selection, server-side typed
grounding과 top-1 KB response를 사용한다. 지역·후속질문·budget·acceptance는 같은 vertical
delivery로 묶되 shared contract와 DB schema는 늘리지 않는다.

### 이유

현재 20 topic에는 vector/embedding 인프라보다 작은 allowlisted catalog가 더 단순하고
검증 가능하다. 모델의 권한을 topic 제안으로 제한하면서 paraphrase recall을 높일 수 있다.

### 고려했지만 선택하지 않은 대안

- lexical alias 무한 확장: 새 표현마다 같은 유지보수가 반복된다.
- vector/embedding: 현재 규모 대비 dependency/index/cost가 과하다.
- 모델에 답변·출처 선택 위임: 승인 KB와 source authority를 깨뜨린다.
- 여러 KB 합성: 절차·수수료·출처 충돌 위험이 현재 MVP에 불필요하다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| integrated spec/ADR | Approved/plan Review로 상태 전환 | 인간 권위 명시 |
| decision/ambiguity/source-of-truth | D-103과 resolved-plan references | 중복 질문·권위 드리프트 방지 |
| implementation plan | 11개 reviewer-worthy task, RED/GREEN/commit/gate | 실행 가능성 |
| TASKS | `CHAT-HYBRID-RAG-001` Review row | 우선순위·의존성·인수 기준 |
| versions | docs 2.26.0→2.26.1 | 명세 승인·계획 게시 patch |
| implementation note/INDEX | 요청 단위 6W1H 증거 | 재현·인수인계 |

### 데이터 흐름/상태 변화

제품 데이터 흐름과 DB 상태 변화는 없다. 후속 계획만
PII→snapshot/catalog→selection→grounding→response→route persistence 흐름을 고정한다.

### 오류·빈 상태·롤백

- 계획 승인 전 구현하지 않는다.
- 이 문서 변경은 해당 local commit을 revert하면 롤백된다.
- DB migration/data compensation은 없다.
- 후속 구현에서 catalog 0/21+, invalid provider, cost cap은 outbound/storage 없는 FOLLOWUP으로
  닫도록 계획했다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.11.1-classifier-runtime | unchanged | 제품 코드 0 |
| Web | 0.7.0-natural-dialogue | unchanged | 제품 코드 0 |
| API | 4.0.0-draft | unchanged | public field 0 |
| DB schema | 0.5.0-local | unchanged | migration 0 |
| Official data | 0.1.0-initial.2 | unchanged | official byte 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 0 |
| Prompt set | 0.3.1-hybrid-classifier | unchanged | runtime prompt 0 |
| Test suite | 1.9.2-classifier-runtime | unchanged | runtime test 0 |
| Docs | 2.26.0 | 2.26.1 | written spec approval + exact plan |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `git status/branch/log` | PASS | branch와 clean start 확인 | terminal |
| current spec/ADR/code/Web/settings read | PASS | exact interface와 drift 확인 | inspected files |
| `python -B scripts/check_repository_docs.py` | PASS | documentation links/manifest | terminal |
| `python -B scripts/validate_codex_package.py` | PASS | required 12 files, manifest valid | terminal |
| `check_secret_patterns.ps1` | PASS | findings 0 | terminal |
| `git diff --check` | PASS | whitespace errors 0 | terminal |

### 미실행 검증과 이유

- API/Web/DB/product tests: 제품 코드를 변경하지 않은 decision-plan 단계다.
- actual Upstage/DB reset/seed/public deploy: 실행계획 승인 전 실행 금지다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 원문·secret·provider payload를 읽거나 기록하지 않았다. 후속 계획에 provider 전
  PII와 route별 row-zero를 비협상 조건으로 고정했다.
- Security: ACTIVE/OFFICIAL intersection, server validation, source authority와 invalid-provider
  fail-closed를 계획에 고정했다.
- Accessibility: region control의 keyboard/name/44px/focus와 390/430/desktop E2E를 계획했다.
- Performance/cost: request-local max-20 catalog, no vector dependency, concurrency 1,
  80/100/160·USD0.20 pre-reservation을 계획했다. 실제 비용 0.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2` 변경 0.
- mock/AI 생성: 변경 0. 후속 retrieval metadata/UAT는 non-factual/synthetic로 분리한다.
- schema/lineage: DB schema와 official lineage unchanged.
- verified date: 2026-07-27 KST planning evidence.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- written specification은 승인됐다.
- 제품 구현·actual provider 실행은 아직 시작하지 않았다.
- 다음 human gate는 이 실행계획 전체 승인이다.
- 계획 승인 시 local/private PII-free actual 20-case subset 한 번까지 실행 범위에 포함된다.
- public/remote, 새 official facts, 새 dependency, DB migration과 자동 merge는 포함되지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- helper/type/file split, fake provider, fixture validator와 component split은 승인 계약 안에서
  primary agent가 조정할 수 있다.
- shared catalog types, `service.py`, cost ledger, contracts/versions는 primary agent가 통합 소유한다.
- 독립 API metadata/tests, Web/E2E, docs/security review는 subagent 병렬 lane으로 분리할 수 있다.

## 13. 인수인계·재현·롤백

### 재현

1. base `f23e2aa`에서 이 note의 related spec/ADR을 읽는다.
2. plan의 File Responsibility Map과 Task 1~11을 순서대로 검토한다.
3. 실행 승인 뒤 `superpowers:subagent-driven-development`로 각 RED/GREEN checkpoint를 수행한다.

### 롤백

이 decision-plan commit만 revert한다. 제품 코드/DB/data rollback은 필요하지 않다.

### 다음 개발자 시작점

`docs/superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md`의 Task 1에서 시작한다.
첫 제품 변경 전 새 feature branch/worktree 상태를 확인하고 failing catalog tests를 먼저 작성한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 실행계획 human approval Pending.
- 실제 Upstage 품질은 offline 48 gate 뒤 actual 20을 실행하기 전 확정할 수 없다.
- current local DB의 ACTIVE 20은 보존하지만 clean KPI로 해석하지 않는다.
- public target, remote DB, production rate limit, new factual KB는 후속 인간 결정이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

# IMP-20260728-002 — bounded Hybrid RAG 최종 검증과 Draft PR 마감

- Date/Time (KST): 2026-07-28T01:51:00+09:00
- Task ID: `CHAT-HYBRID-RAG-001-T11`
- Type: final-verification-handoff
- Status: Done — local/private evidence complete; Draft PR publication pending
- Author/Agent: 사용자 승인 / Codex main 통합 / 독립 리뷰·검증 에이전트
- Branch: `codex/CHAT-HYBRID-RAG-001`
- Base commit: `940d1df396009b813281448e239b1f91d8c74374`
- Pre-closeout HEAD: `7e4beec3d03a`
- Related: [spec](../superpowers/specs/2026-07-27-bounded-hybrid-rag-conversation-design.md),
  [plan](../superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md),
  [offline UAT](../test-reports/CHAT-HYBRID-RAG-001-OFFLINE-UAT.md),
  [actual evidence](../test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md)

## 1. 사용자 요청과 완료 기준

### 요청

승인된 bounded Hybrid RAG 계획을 Subagent-Driven 방식으로 끝까지 구현하고, 최종 전체
검증·독립 리뷰·문서·버전·Git 증거를 정리한 뒤 자동 merge 없이 Draft PR을 만든다.

### Acceptance Criteria

- 승인된 ACTIVE/OFFICIAL catalog, typed grounding, exact FOLLOWUP, same-tab region과
  80/100/160·USD 0.20 경계를 유지한다.
- durable idempotency 재생 뒤에도 같은 공식 topic을 안전하게 이어 간다.
- browser 390/430/desktop, API, Web, contracts, static, security와 protected path를 검증한다.
- 실제 Upstage 1회 FAIL을 PASS로 왜곡하거나 재실행하지 않는다.
- dependency, 공개 API field, DB migration, official `.2`, public/remote를 바꾸지 않는다.
- 구현 노트와 source-of-truth/버전이 현재 결과를 정확하게 말한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 명세·계획·actual local 실행을 승인했고 Codex main이 공유 계약·통합·Git을, 독립 에이전트가 구현·리뷰·gate lane을 담당했다. |
| When — 언제 | 2026-07-27~28 KST |
| Where — 어디서 | private local worktree `.worktrees/actual-p0-ux-gaps`, branch `codex/CHAT-HYBRID-RAG-001` |
| What — 무엇을 | Tasks 1~11 구현, actual 1회 증거, 최종 browser/API/contracts/security 검증과 마감 |
| Why — 왜 | 표현이 달라도 승인된 공식 KB 범위에서 자연스럽고 근거 있는 안내를 제공하기 위해서다. |
| How — 어떻게 | TDD, request-local ACTIVE catalog, closed topic+coverage, server validation, fail-closed provider budget, 독립 review |
| How much — 어느 정도 | closeout 포함 105개 branch 변경 파일, browser 27, API 2,357, contracts 96, Mypy 114, actual outbound 9 |

## 3. 시작 전 상태

- 사용자 실측에서 전입·폐기물 paraphrase가 grounding 부족으로 떨어지고, 지원하지 않는 민원이
  generic FOLLOWUP으로 섞이며, 증명서와 지역 대화가 부자연스러운 문제가 있었다.
- 기존 official `.2`는 19 ACTIVE/OFFICIAL이고 local DB에는 별도 승인된 20번째 ACTIVE가 있다.
- API/DB/public contract를 넓히지 않고 기존 facts에 retrieval metadata와 합성 UAT만 더하는
  방향이 승인됐다.
- Task 10 actual 전 offline은 48/48, official 57/57, classifier 60/60, focused 91/91이었다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-RAG-001 | 인간 결정 | 제한형 Hybrid RAG | A — closed allowlist + server revalidation | 검색·LLM |
| Q-UX-REGION-001 | 인간 결정 | 지역 선택 | A — 항상 표시, 같은 탭 유지 | Web context |
| Q-UX-CERT-001 | 인간 결정 | 증명서 FOLLOWUP | A — 2단계 exact choice | 시민 UX |
| Q-COST-001 | 인간 결정 | local provider cap | 80/100/160, USD 0.20 | 비용·fallback |
| Q-DATA-RAG-001 | 인간 결정 | 데이터 확대 | A — metadata/UAT 우선, official facts 불변 | 데이터 계보 |
| D-105/A-069 | 인간 gate | actual FAIL 후 진단·재실행 | 새 승인 전 금지 | provider readiness |

## 5. 설계 결정과 버린 대안

### 선택

- 외부 classifier는 자유 답변이 아니라 closed `route+intent+topic_id+coverage_id+pending_slot`만
  제안하고 서버가 현재 request-local catalog로 다시 검증한다.
- 시민 응답 facts와 source는 서버 소유 ACTIVE/OFFICIAL KB에서만 결합한다.
- deterministic exact/unique/context 경로는 provider 호출 0을 유지한다.
- durable SUCCESS replay는 저장된 공식 source ID를, topic-bound REGION FOLLOWUP replay는
  기존 서명 context의 topic ID를 복원한다. 다음 요청에서 현재 ACTIVE catalog로 재검증한다.

### 버린 대안

- embedding/vector DB와 multi-KB synthesis: 새 dependency·데이터·오답 면적이 커서 제외했다.
- LLM이 source/title/URL을 생성: 출처 위조 위험 때문에 제외했다.
- FOLLOWUP replay topic을 옵션 문자열로 추론: 공개 label drift와 오인 위험 때문에 제외했다.
- provider actual 자동 재시도: 승인된 1회 비용·증거 경계를 깨므로 제외했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `apps/api/.../chat/topic_catalog.py` | ACTIVE/OFFICIAL runtime topic catalog | 허용 범위 고정 |
| `classification.py`, `retrieval.py`, `grounding.py`, `service.py` | deterministic/semantic/context 선택과 typed evidence, durable replay 교정 | 자연어와 근거 gate |
| `followup.py`, `context.py`, `response.py` | intent별 exact FOLLOWUP과 bounded signed context | 대화 연속성 |
| `llm/*` | closed output, 80/100/160·USD0.20 pre-reservation | 비용·실패 안전 |
| `apps/web/*` | 상시 지역 선택, 증명서·관련질문 UX | 시민 사용성 |
| contracts/shared | 기존 shape 안의 enum·fixture 정합 | FE/BE 동시성 |
| retrieval metadata/UAT | non-factual coverage와 synthetic 48-case | official facts 불변 검증 |
| actual runner/runbook/report | content pin, one-run lock, aggregate-only FAIL | 안전한 actual evidence |

### 데이터 흐름/상태 변화

마스킹 → privacy/policy gate → ACTIVE/OFFICIAL snapshot → deterministic 또는 bounded classifier
제안 → server topic/coverage validation → typed grounding → server-owned answer/source 또는 exact
FOLLOWUP/fallback이다. 시민 질문 원문, transcript, provider body는 저장하지 않는다.

### 오류·빈 상태·롤백

provider 오류·timeout·invalid JSON·cost cap은 template/fallback으로 닫힌다. actual 9 outbound는
strict accepted usage와 topic match가 0이라 FAIL이며 자동 재실행하지 않았다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.11.1-classifier-runtime` | `0.12.1-bounded-hybrid-rag` | catalog·retrieval·context와 replay patch |
| Web | `0.7.0-natural-dialogue` | `0.8.0-guided-chat` | region/certificate/related UX |
| API | `4.0.0-draft` | 동일 | 공개 shape breaking 변화 없음 |
| Shared contracts | `1.0.0` | 동일 | 기존 공개 버전 유지 |
| DB schema | `0.5.0-local` | 동일 | migration 0 |
| Official data | `0.1.0-initial.2` | 동일 | facts/bytes/lineage 불변 |
| Mock data | `0.0.0-not-populated` | 동일 | mock 승격 0 |
| Prompt set | `0.3.1-hybrid-classifier` | `0.4.0-topic-coverage` | closed topic/coverage 제안 |
| Test suite | `1.9.2-classifier-runtime` | `2.1.1-bounded-hybrid-rag-closeout` | UAT·actual·replay·static |
| Docs | `2.25.1` | `2.29.0` | spec·plan·evidence·handoff |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 |
|---|---|---|---|
| focused replay RED/GREEN | PASS after two REDs | final 3 pass; service full 96 pass | Task 11 terminal/review |
| independent replay rereview | PASS | C0/I0/M0, Spec ✅ | ignored SDD review |
| browser matrix | PASS | 27/27; 390/430/desktop | Task 11 browser lane |
| final `scripts/verify.ps1` | **NOT PASS** | 835.5s; 19 unique prior stages PASS, `FORMAT-API` exit 1 | Task 11 aggregate lane |
| Ruff format correction/check | PASS | 13 reformatted, final 114 formatted | commit `8f5922b` |
| API Ruff/Mypy | PASS | 114 files, issue 0 | final constituent |
| API pytest | PASS | 2,357 pass, 8 local-DB skip, warning 1 | final constituent |
| shared generate/diff/test | PASS | generated diff 0, 96/96 | final constituent |
| secret and Web bundle scan | PASS | findings 0/0, env restored | final constituent |
| package/docs/protected diff | PASS | package 12 files, protected files 0 | final constituent |
| actual Upstage selector | **FAIL** | 20 selected, 11 provider-free, 9 outbound, match 0 | actual report |

### 미실행 또는 non-pass 검증과 이유

- aggregate wrapper는 포맷 drift에서 종료됐으므로 PASS가 아니다. 계획의 bounded failure 규칙에
  따라 wrapper를 반복하지 않고 formatter를 적용한 뒤 당시 미실행 11 constituent를 직접
  실행했다.
- actual provider 재실행은 D-105/A-069에 따라 새 인간 승인 전 금지한다.
- local DB reset/seed, public/remote deploy·DB는 이번 slice에서 실행하지 않았다.
- browser 명령의 literal `--` 때문에 목표 24에 dev-origin 3이 추가 수집되어 실제 결과는
  27/27이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 원문·transcript·provider body 저장 0, privacy/policy outbound 0.
- Security: key/DSN 출력·커밋 0, provider mode는 worktree와 parent 모두 false로 복구했다.
- Accessibility: 390/430/desktop citizen/admin browser 27/27.
- Performance/cost: actual elapsed 6,121ms. conservative ledger USD 0.00684288 < USD 0.20이며
  provider invoice가 아니다. retry 0, concurrency 1을 유지한다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`와 `data/official` diff 0.
- mock/AI 생성: 48-case와 actual selector fixture는 `SYNTHETIC_CHAT_UAT`; 공식 사실이 아니다.
- DB/migration/rollback: 변경 0.
- source: 시민 SUCCESS는 서버가 결합한 공식 source가 1개 이상이며 provider가 만들지 않는다.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- actual Upstage Hybrid RAG는 PASS가 아니다. provider 인증/모델 접근/응답 원인은 보관하지 않은
  본문 없이 단정할 수 없고, 진단·corrective rerun은 새 승인이 필요하다.
- local deterministic/template와 offline UAT는 통과했지만 public 운영 준비 완료를 뜻하지 않는다.
- public/remote 배포·DB, 실제 시민 운영, rate limit·법무·보관 정책은 별도 승인 사항이다.
- Draft PR은 사람이 검토·merge해야 하며 Codex는 자동 merge하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- runtime catalog는 최대 20 metadata와 현재 ACTIVE/OFFICIAL record의 교집합이다.
- semantic selector는 server catalog membership과 typed grounding을 통과하지 못하면 사용하지 않는다.
- REGION replay topic은 raw question이나 option label이 아니라 기존 서명 context에서만 복원한다.
- root security expectation은 승인된 80/100/160·USD0.20으로 동기화했다.

## 13. 인수인계·재현·롤백

### 재현

1. provider mode를 false/false로 확인한다.
2. `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1`을 사용한다.
3. browser matrix, actual report와 이 노트의 bounded wrapper 결과를 함께 읽는다.
4. actual provider는 D-105/A-069 승인 없이는 재실행하지 않는다.

### 롤백

- closeout docs commit부터 역순으로 revert한다.
- replay 교정: `259be58`; static test: `3ca6320`, formatter: `8f5922b`, typed fixtures:
  `7e4beec`를 역순 revert한다.
- 전체 feature rollback은 branch merge commit/squash를 revert한다.
- DB/data rollback은 필요 없으며 provider 외부 요청 자체는 되돌릴 수 없다.

### 다음 개발자 시작점

1. Draft PR의 actual FAIL·wrapper non-pass 문구가 유지되는지 확인한다.
2. 사람 승인 후 merge한다.
3. provider corrective 진단은 별도 계획/비용 gate로 분리한다.

## 14. 남은 위험·다음 단계

- Pending: Draft PR URL 기록과 사람 merge.
- Pending: A-069 actual provider 원인 진단·corrective rerun.
- Pending: public/remote 배포·DB·운영 보안.
- 기존 Starlette/httpx deprecation warning 1건은 기능 실패가 아니며 후속 dependency 정책에서 처리한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증과 non-pass 공개
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문·secret 노출 없음
- [x] 구현 노트 INDEX 갱신
- [ ] Draft PR URL 기록

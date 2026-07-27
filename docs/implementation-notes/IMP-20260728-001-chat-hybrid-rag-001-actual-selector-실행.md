# IMP-20260728-001 — CHAT-HYBRID-RAG-001 actual selector 실행

- Date/Time (KST): 2026-07-28T00:47:12+09:00
- Task ID: `CHAT-HYBRID-RAG-001-T10`
- Type: actual-evidence
- Status: Done — exactly one approved run; acceptance FAIL; rerun prohibited
- Author/Agent: 사용자 승인 / Codex main actual 실행·통합 / 구현·보안 독립 검토 에이전트
- Branch: `codex/CHAT-HYBRID-RAG-001`
- Base commit: `5130b1e`
- Runner commits: `0288607`, `5130b1e`
- Related: [plan](../superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md),
  [actual evidence](../test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md), D-105

## 1. 사용자 요청과 완료 기준

### 요청

승인된 PII-free 20-case actual selector를 content-pinned runner로 정확히 한 번 실행하고,
질문·provider content·key·DSN을 기록하지 않은 aggregate 결과와 비용·복구 증거를 남긴다.
실패하면 자동 재실행하지 않고 독립적으로 가능한 최종 작업을 계속한다.

### Acceptance Criteria

- exact 20 selected, skip 0, privacy case 0
- deterministic/policy/privacy outbound 0, fixture가 요구한 provider outbound 9
- provider 9건의 strict response와 catalog-valid route/topic match
- classifier/generator/combined 80/100/160, retry 0, concurrency 1, USD 0.20 이하
- 질문·payload·provider content·key·DSN 출력/보고서 보관 0
- 실패 시 bounded FAIL을 원자적으로 기록하고 새 인간 승인 전 재실행 0

실행 경계는 충족했지만 provider acceptance는 충족하지 못했다. 결과는 FAIL이며 성공으로
승격하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 actual gate를 승인했고 Codex main이 실행, 별도 구현자와 Sol reviewer가 runner를 검토했다. |
| When — 언제 | 2026-07-27~28 KST, Tasks 1~9와 runner 독립 review 뒤 실행했다. |
| Where — 어디서 | local/private worktree, ignored local `.env` key, Upstage direct API, tracked aggregate report |
| What — 무엇을 | PII-free 20-case selector one-shot, content pin, cost/lock/failure evidence |
| Why — 왜 | offline 의미 선택 성능이 실제 provider에서도 재현되는지 비용·개인정보 경계 안에서 확인하기 위해서다. |
| How — 어떻게 | TDD, exact SHA-256, ACTIVE/OFFICIAL projection, strict usage parser, one-run lock, value-free failure |
| How much — 어느 정도 | selected 20, skip 0, provider-free 11, outbound 9, accepted usage 0, provider match 0 |

## 3. 시작 전 상태

- 관련 파일: frozen 48-case UAT, topic coverage, immutable official `.2`, classifier settings와
  attempt ledger.
- 기존 동작: Tasks 1~9 offline은 48/48·official 57/57·classifier 60/60·focused 91 PASS였다.
- 발견한 충돌/부채: 첫 runner는 lowercase offline marker, incomplete FAIL evidence, loose
  usage parsing과 lock 부재 때문에 독립 review에서 Spec ❌였다.
- Git 상태: runner fix `5130b1e`, protected inputs clean, actual report·lock 부재.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-COST-001 | 인간 결정 | local interactive budget | 80/100/160, USD 0.20 | actual cap |
| D-105 | 실행 경계 | 실패 뒤 재실행 여부 | 새 인간 승인 전 금지 | 비용·증거 |
| A-ACTUAL-001 | 미해결 | 9건 모두 strict usage가 없었던 원인 | 본문 미보관으로 단정 금지 | provider readiness |
| A-ACTUAL-002 | 가정 | conservative ledger charge | 내부 fail-close 증거이며 provider invoice가 아님 | 비용 해석 |

## 5. 설계 결정과 대안

### 선택

content SHA와 exact release projection을 client 생성 전에 확인하고, canonical report/lock
sentinel로 동시·중복 실행을 차단한다. strict production usage parser와 ledger 비용을
대조하고, 실패도 exception value 없이 aggregate-only report로 기록한다.

### 이유

한 번만 허용된 실제 호출에서 입력 drift, 숨은 재시도, 부분 실패 증거 유실과 비밀 노출을
동시에 막아야 했기 때문이다.

### 고려했지만 선택하지 않은 대안

- provider 본문·오류 문구 저장: 진단은 쉬우나 보안·데이터 최소화 경계를 넓혀 거절했다.
- FAIL 뒤 자동 재시도: 한 번 실행 승인과 비용 경계를 깨므로 거절했다.
- fixture 기대값을 oracle로 재사용: 순환 검증이므로 hardcoded independent decisions와 pin을 썼다.
- 기존 report 덮어쓰기: 중복 실행을 숨길 수 있어 sentinel로 차단했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/run_hybrid_rag_actual.py` | content pin, preflight, one-run lock, strict usage/cost, bounded PASS/FAIL | actual 안전 실행 |
| `scripts/tests/test_run_hybrid_rag_actual.py` | executable preflight/main/failure/Windows lock tests | 실제 경계 회귀 방지 |
| `docs/runbooks/UPSTAGE-HYBRID-RAG-ACTUAL.md` | 정확히 1회·복구·재실행 금지 | 사람 운영 경계 |
| actual report | 20 case의 ID·evidence kind·outbound·aggregate cost만 기록 | 결과 계보 |
| source-of-truth/decision/version/docs | actual FAIL과 재실행 gate 동기화 | 완료 상태 오인 방지 |

### 데이터 흐름/상태 변화

canonical PII-free fixture → redaction/provider-safety → deterministic 11 provider 0 →
ambiguous 9 Upstage attempt → strict response/usage validation → aggregate FAIL report다.
DB·official data·question log·remote state는 바뀌지 않았다.

### 오류·빈 상태·롤백

9 outbound 모두 strict accepted usage가 없어서 route/topic match 0으로 FAIL했다. report는
원자적으로 남았고 lock은 정상 해제됐지만 report sentinel이 재실행을 차단한다. mode는 두
local `.env`에서 exact false/false로 복구했다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.12.0-bounded-hybrid-rag` | 동일 | 제품 runtime 변화 없음 |
| Web | `0.8.0-guided-chat` | 동일 | UI 변화 없음 |
| API/shared | `4.0.0-draft` / `1.0.0` | 동일 | 공개 계약 변화 없음 |
| DB schema | `0.5.0-local` | 동일 | DB 사용·migration 0 |
| Official/mock data | `.2` / not populated | 동일 | bytes·row 변화 0 |
| Prompt set | `0.4.0-topic-coverage` | 동일 | runtime prompt 변화 없음 |
| Test suite | `2.0.0-bounded-hybrid-rag` | `2.1.0-bounded-hybrid-rag-actual` | one-shot runner/security tests |
| Docs | `2.27.0` | `2.28.0` | actual FAIL·runbook·handoff 증거 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| runner RED/fix RED | expected fail | initial 3, fix 7+2 mutation RED | ignored implementer report |
| focused pytest | PASS | 79 passed | ignored implementer report |
| Ruff / Mypy / secret / diff | PASS | findings 0 | ignored implementer/review reports |
| Sol scoped rereview | PASS | 7 addressed, open/new 0 | ignored rereview report |
| value-free preflight attempt 1 | stopped before network | wrong candidate key assignment; outbound 0 | terminal evidence |
| value-free preflight attempt 2 | READY | pins/profile/protected inputs 20 | terminal evidence |
| approved actual runner | FAIL | 20 selected, 11 provider-free, 9 outbound, match 0 | actual report |
| post-run mode check | PASS after bounded local edit | two files false/false | terminal evidence |
| post-run secret/diff | PASS | secret finding 0, lock absent | terminal evidence |

### 미실행 검증과 이유

- actual 재실행: D-105와 runbook이 새 인간 승인 전 금지한다.
- provider body/status diagnosis: 본 실행은 body를 보관하지 않아 원인을 단정하지 않는다.
- DB/Docker/remote/public: 이 Task 범위가 아니다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: canonical PII-free 20만 사용했고 privacy/policy outbound는 0이다.
- Security: key는 기존 ignored `.env`에서 process memory로만 읽고 값은 출력·복사하지 않았다.
  질문/provider content/payload/key/DSN report 보관은 0이다.
- Accessibility: UI 변경 없음.
- Performance/cost: elapsed 6,121ms, outbound 9, observed accepted usage cost 0,
  ledger conservative charge USD 0.00684288 < USD 0.20. 마지막 값은 provider 청구서가 아니다.

## 10. 데이터와 출처 영향

- 공식 데이터: `0.1.0-initial.2`, 19 ACTIVE/OFFICIAL, bytes 불변.
- mock/AI 생성: actual fixture는 `SYNTHETIC_CHAT_UAT`; 공식 사실이 아니다.
- schema/lineage: fixture/coverage/official/manifest/offline report SHA-256을 evidence에 기록했다.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 새 Hybrid RAG selector actual은 PASS가 아니다. 실제 데모에서는 provider 실패 시
  deterministic/template fallback이 안전하게 동작하지만 AI 의미 선택 품질을 actual PASS로
  주장하면 안 된다.
- 9건 모두 strict accepted response/usage가 0이었다. 인증, `solar-pro3` 접근, provider 응답,
  전송 중 어느 원인인지는 저장하지 않은 본문 없이 단정할 수 없다.
- 진단과 corrective actual rerun은 별도 인간 승인이 필요하다. 자동/숨은 재시도는 없었다.
- public/remote/production 운영, 새 비용 지출, 공식 데이터 변경은 승인·실행하지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- deterministic 11은 fresh route/topic match가 아니라 prior-offline provider-free로 표시한다.
- strict usage와 ledger actual/conservative charge를 분리해 0 usage를 0 attempt로 오인하지 않는다.
- canonical report 존재가 rerun sentinel이고 `.run.lock`은 동시 실행만 막는다.

## 13. 인수인계·재현·롤백

### 재현

재실행하지 않는다. 결과 검토는 actual report와 이 노트만 읽는다. 원인 진단 뒤 사용자가
새 실행을 승인할 때만 runbook의 report archive·lock 확인·exact command 절차를 따른다.

### 롤백

이 노트를 포함한 Task 10 evidence/documentation commit을 먼저 revert한 뒤 runner fix
`5130b1e`, initial runner `0288607` 순서로 revert한다. ignored `.env`는 false/false를 유지하고
DB/data rollback은 필요 없다. actual 외부 요청 자체는 되돌릴 수 없다.

### 다음 개발자 시작점

actual report의 `observed_usage_response_count=0`, `provider_route_topic_match_count=0`을 먼저
보고, key/모델 권한/provider availability를 값 비노출 방식으로 진단하는 별도 계획을 만든다.

## 14. 남은 위험·미해결 질문·다음 단계

- Task 11 final full/root/security/browser gate와 Draft PR은 계속 진행한다.
- provider actual PASS는 별도 corrective gate이며 현재 PR의 완료 주장에 포함하지 않는다.
- real citizen/public 운영 전 개인정보·약관·법무·rate limit은 여전히 별도 승인 사항이다.

## 15. 자체 리뷰

- [x] 요청한 정확히 한 번 실행과 FAIL 기록
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문·secret/provider content 노출 없음
- [x] 구현 노트 INDEX 갱신

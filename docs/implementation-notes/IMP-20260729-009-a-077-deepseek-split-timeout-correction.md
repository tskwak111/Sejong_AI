# IMP-20260729-009 — A-077 DeepSeek split timeout correction

- Date/Time (KST): 2026-07-29T13:11:00+09:00
- Task ID: A-077/A-078-DEEPSEEK-SPLIT-TIMEOUT
- Type: implementation-provider-actual
- Status: Done — A-077 offline PASS preserved; A-078 probe FAIL; actual blocked
- Author/Agent: Codex root agent
- Branch: `codex/a-075-deepseek-corrective-actual`
- Base commit: `8975585001125f4766dc585cd541ce8e0ac8a05c`
- Related plan/ADR/RFP: D-128/D-129, ADR-0028 amendments, A-077/A-078 approved
  specification/plan, SFR-002

## 1. 사용자 요청과 완료 기준

### 요청

사용자는 A-076의 `transport_no_response`가 네트워크 때문일 가능성을 확인한 뒤 재진행을
요청했고, Q-LLM-015 선택지 A로 connect3초·read/complete10초 분리, 1-call 진단 뒤 조건부
고정 actual을 승인했다.

### Acceptance Criteria

- A-074/A-075/A-076 report·lease·invocation/rerun을 변경하거나 재실행하지 않는다.
- connect/write/pool은 3초, read와 complete exchange는 10초, retry0을 강제한다.
- A-077은 별도 offline/result/report/lease와 100초 aggregate deadline을 사용한다.
- A-077 source `675eef4...` offline PASS 1/0은 보존하고 provider probe/actual 0회 상태에서
  reviewer 보강 A-078 identity로 승계한다.
- aggregate-only 1-call probe가 HTTP 2xx를 받은 경우에만 9 provider-case actual을 실행한다.
- 질문·masked question·provider body·invalid value·exception detail·key·DSN을 보관하지 않는다.
- API/DB/data/Web/final-answer provider/dependency/public/remote/free-input은 변경하지 않는다.
- 모든 실행은 clean committed source에서 exact-one이며 자동 merge하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인자와 Codex 설계·구현·검토자 |
| When — 언제 | 2026-07-29 KST |
| Where — 어디서 | private local branch, DeepSeek classifier transport와 ignored evidence directory |
| What — 무엇을 | split timeout, identity-owned actual deadline, exact-lease 1-call probe와 pre-lease 조건부 actual gate |
| Why — 왜 | A-076 28.6초≈9×3초와 응답 전 실패라는 단일 timeout 가설을 최소 변경으로 검증 |
| How — 어떻게 | TDD RED/GREEN, immutable evidence identity, aggregate-only report, exact-one wrapper |
| How much — 어느 정도 | probe1, 조건부 provider9, retry/rerun0, concurrency1, cost cap USD0.20 |

## 3. 시작 전 상태

- 관련 파일: DeepSeek settings/client/classifier, actual runner, ADR-0028, A-076 증거.
- 기존 동작: HTTP connect/read/write/pool과 complete exchange가 모두 3초였다.
- 발견한 충돌/부채: A-076은 value-free connectivity PASS에도 provider9가 모두 약 3초 후
  응답 전에 끝났고, 실제 exception detail은 보관하지 않아 timeout은 강한 가설이나 확정은
  아니었다.
- Git 상태: base `8975585`, tracked tree clean, Draft PR #22.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-015 | A | timeout 예산 변경과 추가 actual 권한 | A 승인 | provider latency·cost·evidence |
| A077-PROBE | C | 9-call 전에 필요한 최소 진단 | HTTP 2xx 1건만 통과 | 비용·실패 격리 |
| A077-DEADLINE | C | 9×10초 aggregate 상한 | 100초 | hung process 제한 |
| A077-REPORT | D | probe report가 clean-source actual을 막지 않는 경로 | ignored local JSON 후 tracked closeout summary | Git/evidence 무결성 |
| A078-PRELEASE | D | review가 찾은 exact lease·same-source TOCTOU 보강 | 별도 identity, callback 뒤 final revalidation, probe 응답 뒤 revalidation | 증거 체인 |

## 5. 설계 결정과 대안

### 선택

Immutable settings에 별도 connect budget을 추가하고 complete-exchange budget을 10초로
늘린다. Probe와 actual은 서로 다른 lease를 사용한다. A-078 actual runner는 bounded strict
probe report, exact lease bytes와 same-source PASS를 clean-source 재검증 뒤 actual lease 직전에
다시 fail-closed로 확인한다.

### 이유

연결 수립은 빠르게 실패시키면서 정상 provider 추론 시간이 3초를 넘을 여지를 제공한다.
1-call 2xx gate는 응답조차 없는 상태에서 9회 비용과 시간을 반복하는 일을 막는다.

### 고려했지만 선택하지 않은 대안

- 전체 timeout을 30초 이상으로 단순 확대: 느린 장애를 오래 끌고 검증 범위가 커져 제외.
- retry 추가: 동일 실패를 중복 호출하고 비용·증거 해석을 흐려 제외.
- A-076 lease 삭제·재실행: immutable evidence 위반이라 금지.
- Upstage/DeepSeek 자동 cascade: 승인 범위와 공급자 독립 경계를 벗어나 제외.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| DeepSeek settings/client | connect3, read/complete10 분리 | timeout 가설 최소 교정 |
| core actual runner | evidence identity별 aggregate deadline | A-074~076 32초 보존, A-077 100초 |
| A-077 probe | ignored one-shot report/lease, 2xx-only acceptance | 비용과 실행 단계 차단 |
| A-077 runner/wrapper | historical clean checkpoint와 offline PASS 1/0, provider 0 | 증거 불변성 |
| A-078 runner/wrapper | disjoint identity, exact lease/report/source gate, final/post-probe revalidation | review 보강 |
| tests/docs/versions | RED/GREEN과 권위 동기화 | 회귀·인수인계 |

### 데이터 흐름/상태 변화

Synthetic fixture 질문은 기존 redaction과 `SafeQuestion` 경계를 지난 뒤 한 provider request에만
사용된다. Report에는 source/model/timeout과 count·token·cost·closed acceptance만 남는다.
Application DB와 로그에는 쓰지 않는다.

### 오류·빈 상태·롤백

Probe가 response0/non-2xx/runtime failure면 immutable FAIL report/lease를 남기고 actual을
차단한다. Actual도 기존 fail-closed report를 남기며 자동 rerun하지 않는다. 실행 전에는 commit
revert가 가능하고 실행 후에는 새 identity 없이 evidence를 삭제·수정하지 않는다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.13.1 | 0.13.2 | DeepSeek split timeout |
| Web | 0.8.0 | 동일 | UI 불변 |
| API | 4.0.0 | 동일 | 공개 계약 불변 |
| DB schema | 0.5.0 | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | 데이터 불변 |
| Mock data | 0.0.0 | 동일 | 데이터 불변 |
| Prompt set | 0.4.3 | 동일 | prompt 불변 |
| Test suite | 2.2.5 | 2.2.7 | A-077 split timeout + A-078 pre-lease hardening tests |
| Docs | 2.31.6 | 2.31.8 pre-execution | D-128/D-129/spec/plan/authority |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| split settings/client/identity RED | expected FAIL | 5 failed | pytest terminal |
| split settings/client/identity GREEN | PASS | 5 passed | pytest terminal |
| probe/conditional actual RED | expected FAIL | 6 failed | pytest terminal |
| probe/conditional actual GREEN | PASS | 8 passed, then failure-report regression PASS | pytest terminal |
| A-077 wrapper RED | expected FAIL | 2 failed, wrapper absent | pytest terminal |
| A-077 wrapper GREEN | PASS | 2 passed | pytest terminal |
| DeepSeek/evidence related area | PASS | 153 passed in 39.05s | pytest terminal |
| Ruff focused | PASS | all checked files | terminal |
| Mypy strict | PASS | 5 source files | terminal |
| A-077 offline exact-one | PASS | source `675eef4...`; exit0; invocation/rerun1/0; stdout/stderr2006/0 | ignored immutable result/log/lease |
| Independent review wave 1 | NOT READY | Critical0 / Important3 / Minor2 | exact lease, pre-lease recheck, format |
| A-078 hardening RED/GREEN wave 1 | expected FAIL → PASS | 5 RED; focused 68 PASS | pytest terminal |
| Independent review wave 2 | NOT READY | Important2 | final revalidation, post-probe drift |
| A-078 hardening RED/GREEN wave 2 | expected FAIL → PASS | 2 RED; exact 2 PASS | pytest terminal |
| A-074~A-078 related area final | PASS | 169 passed in 53.68s | pytest terminal |
| Final independent scoped review | READY | Critical0 / Important0 / Minor0 | read-only reviewer |
| Ruff format/lint | PASS | 11 files | terminal |
| Mypy strict | PASS | 7 source files | terminal |
| Docs/secret/diff | PASS | no secret output; diff clean | terminal |
| A-078 offline | PASS | source `844e53b...`; invocation/rerun1/0 | ignored immutable evidence |
| A-078 probe | FAIL | outbound1; response/2xx0; transport-no-response1 | tracked aggregate report |
| A-078 actual | Not run | report/lease absent | probe gate blocked |

### 미실행 검증과 이유

A-077 offline과 A-078 offline/probe는 exact-one 소비됐다. A-078 probe가 FAIL했으므로 actual은
차단·미실행이고 report/lease도 없다. A-077/A-078을 재실행하지 않으며 후속은 D-131/A-079만
사용한다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문/본문/invalid value/exception detail 보관을 추가하지 않는다.
- Security: predecessor evidence를 불변 보존하고 same-source probe PASS 없이는 actual을 막는다.
- Accessibility: UI 변경 없음.
- Performance/cost: call wall clock을 3→10초로 늘리되 retry0, probe1, actual 최대9,
  total cost cap USD0.20을 유지한다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 없음.
- mock/AI 생성: 기존 synthetic fixture만 사용.
- schema/lineage: DB·official release lineage 변경 없음.
- verified date: 2026-07-29.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Q-LLM-015=A 권한은 A-077/A-078 전체를 합쳐 probe 1-call과 조건부 actual run 1회
  (정확히 9 provider calls)에 한정된다.
- Probe PASS는 DeepSeek 분류 품질 PASS가 아니라 authenticated HTTP 2xx 도달 증거다.
- Public/remote/실제 시민 free-input과 자동 merge는 승인되지 않았다.
- `LLM_PROVIDER`/Upstage final generator는 이번 변경 대상이 아니다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- Existing core runner의 identity binding에 deadline 필드만 추가해 이전 32초를 보존했다.
- Probe machine report는 `.superpowers/`에 두어 actual 직전 clean-tree 검사를 방해하지 않는다.

## 13. 인수인계·재현·롤백

### 재현

Historical A-077/A-078 offline과 A-078 probe는 재실행하지 않는다. 사용자가 승인한 후속
A-079는 IMP-20260729-010과 같은 plan Task 7에서 별도 identity로만 실행한다.

### 롤백

A-078 external probe가 이미 실행됐으므로 report/lease와 source를 보존한다. Runtime rollback은
`CLASSIFIER_PROVIDER=disabled`이고, 아직 실행되지 않은 successor 변경만 새 identity 규칙 아래
revert할 수 있다.

### 다음 개발자 시작점

D-128, ADR-0028 amendment와 A-077 spec/plan에서 시작하고, implementation note의 exact-one
상태를 먼저 확인한다.

## 14. 남은 위험·미해결 질문·다음 단계

- A-078에서는 actual authenticated 2xx와 exact five-field acceptance를 검증하지 못했다.
- External service latency가 10초를 넘으면 기존 deterministic fallback이 유지된다.
- 사용자가 별도 A-079 retry를 승인했으며 결과는 IMP-20260729-010에 기록한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 관련 테스트/정적검사
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

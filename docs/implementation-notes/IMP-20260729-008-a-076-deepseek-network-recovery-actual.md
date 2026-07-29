# IMP-20260729-008 — A-076 DeepSeek network recovery actual

- Date/Time (KST): 2026-07-29T11:28:40+09:00
- Task ID: A-076-DEEPSEEK-NETWORK-RECOVERY-ACTUAL
- Type: implementation-provider-actual
- Status: Done — offline/readiness PASS; actual FAIL transport-no-response 9/9
- Author/Agent: Codex root agent
- Branch: codex/a-075-deepseek-corrective-actual
- Base commit: c71f8b8
- Source checkpoint: c9fc1be
- Evidence closeout commit: 6871a2a
- Draft PR: https://github.com/tskwak111/Sejong_AI/pull/22
- Related plan/ADR/RFP: D-126, ADR-0028, A-076 specification/plan, A-075

## 1. 사용자 요청과 완료 기준

### 요청

사용자는 A-075 실패가 당시 네트워크 때문이라고 판단하고 DeepSeek actual 재진행을 지시했다.

### Acceptance Criteria

- A-074/A-075 report·lease·invocation/rerun을 변경하지 않는다.
- 비밀 없는 DNS·TCP443·TLS/HTTP probe가 먼저 통과한다.
- 별도 A-076 offline gate와 readiness 뒤 actual을 정확히 한 번만 실행한다.
- 기존 20/0·11/9·3초·retry0·concurrency1·output128·USD0.20·무보관 계약을 유지한다.
- 결과를 aggregate-only로 기록하고 자동 재실행·병합하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인자와 Codex 구현·검토자 |
| When — 언제 | 2026-07-29 KST |
| Where — 어디서 | private local branch, ignored `apps/api/.env`, synthetic fixture와 evidence tooling |
| What — 무엇을 | A-076 전용 evidence identity와 network-recovery actual |
| Why — 왜 | A-075 `transport_no_response` 뒤 복구된 경로에서 provider 호환성을 다시 확인 |
| How — 어떻게 | value-free probe, TDD identity/wrapper, clean-source offline/readiness, exact-one actual |
| How much — 어느 정도 | fixed 20, provider 9 outbound, retry/rerun 0, 비용 상한 USD0.20 |

## 3. 시작 전 상태

- A-075는 offline/readiness PASS 뒤 outbound9 모두 HTTP 응답 전 실패했고 permanent report/lease가 있다.
- A-074/A-075 evidence binding seam과 exact evaluator는 이미 review·test됐다.
- 현재 branch HEAD는 `c71f8b8`, Draft PR #22이며 시작 시 tracked tree는 clean이었다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A076-NETWORK | A | DeepSeek 응답 경로 복구 여부 | DNS/TCP/TLS/HTTP value-free probe PASS | actual 허용 전제 |
| A076-ACTUAL | A | 추가 provider actual 권한 | 사용자 exact 재진행 지시 | 외부 호출·비용 |
| A076-IDENTITY | C | A-075 overwrite 여부 | 새 report/offline/lease identity | 증거 무결성 |

## 5. 설계 결정과 대안

### 선택

기존 evaluator의 fail-closed `EvidenceIdentity` seam에 A-076 thin runner를 추가하고, A-075
wrapper 제어 흐름을 A-076 path/gate/lease로만 기계적으로 분리한다.

### 이유

네트워크 회복 후 재실행 요구를 충족하면서 이전 FAIL을 수정·삭제하지 않고 공급자 응답 품질을
분리 판정할 수 있다.

### 고려했지만 선택하지 않은 대안

- A-075 lease 삭제·재실행: immutable evidence 위반이라 폐기.
- Upstage로 전환: DeepSeek 재검증 요청을 충족하지 않아 폐기.
- 제품 runtime 변경: 증거 검증 범위를 벗어나 폐기.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| A-076 runner/test | disjoint report/offline/gate/lease와 restore/drift 검사 | A-075 보존 |
| A-076 wrapper/test | controlled PASS/FAIL과 one-shot 보존 | offline evidence |
| authority/spec/plan/version | D-126과 실행 경계 기록 | 추적성 |

### 데이터 흐름/상태 변화

A-076 offline/readiness PASS 뒤 actual outbound 9회를 실행했다. 모두 HTTP 응답 전
`transport_no_response`였으며 API key 값·질문·provider body는 읽거나 출력하지 않았다.

### 오류·빈 상태·롤백

Offline/readiness 실패는 actual lease 전에 종료한다. Actual lease 뒤 결과는 PASS/FAIL과 관계없이
영구 보존하고 재실행하지 않는다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.13.1 | 동일 | 제품 불변 |
| Web | 0.8.0 | 동일 | UI 불변 |
| API | 4.0.0 | 동일 | 계약 불변 |
| DB schema | 0.5.0 | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | 데이터 불변 |
| Mock data | 0.0.0 | 동일 | 데이터 불변 |
| Prompt set | 0.4.3 | 동일 | prompt 불변 |
| Test suite | 2.2.4 | 2.2.5 | A-076 identity/wrapper tests |
| Docs | 2.31.4 | 2.31.6 | D-126/D-127/spec/plan/actual closeout |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| DNS·TCP443·TLS/HTTP value-free probe | PASS | 4.2s; unauthenticated 4xx response | terminal aggregate |
| A-076 runner/wrapper RED | expected FAIL | 6 failures; files absent | pytest |
| A-074/A-075/A-076 focused GREEN | PASS | 13 tests | pytest |
| provider/parser/privacy/runner area | PASS | 1,501 tests | pytest |
| Ruff | PASS | A-076 Python files | terminal |
| PowerShell parser | PASS | 1,523 tokens, 0 errors | terminal |
| Mypy strict with repository path | PASS | 3 runner files | terminal |
| source checkpoint | PASS | `c9fc1be452db81ea6270211da666e7c854298fe0` clean | Git commit |
| A-076 offline exact-one | PASS | exit0; invocation/rerun1/0; stdout/stderr2006/0 | ignored immutable result/log/lease |
| A-076 readiness | PASS | exact `READY`; report/lease absent | network-free runner |
| A-076 actual exact-one | FAIL | 28.6s; outbound9; transport-no-response9; retry/rerun0 | tracked aggregate report + local lease |
| actual report integrity | PASS | 3,124 bytes; SHA-256 `70768906df8d8a52cf5a2751aafd3f079757794ff80bd57c2c2ca72f2e778f0e` | tracked report |

### 미실행 검증과 이유

추가 provider actual은 A-076 lease가 소비되어 실행하지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·masked question·provider body를 probe에 사용하지 않았다.
- Security: A-074/A-075와 모든 A-076 path/lease payload를 분리한다.
- Accessibility: UI 변경 없음.
- Performance/cost: authenticated outbound9, observed token0. Conservative worst-case
  USD0.02306304<0.20은 actual billing 주장이 아니다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 없음.
- mock/AI 생성: fixed synthetic fixture만 사용 예정.
- schema/lineage: 변경 없음.
- verified date: 2026-07-29.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 사용자의 재진행 지시는 A-076 actual 1회 권한으로 기록했고 그 권한은 소비됐다.
- A-075 FAIL과 rerun0은 바꾸지 않는다.
- public/remote/free-input 및 자동 merge는 승인되지 않았다.
- Timeout 정책 변경과 추가 actual은 새 인간 결정이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- A-076은 기존 `EvidenceIdentity`를 새 상수로 조합하는 thin entry point다.
- Wrapper 제어 흐름은 A-075와 같고 identity 문자열만 A-076으로 분리한다.

## 13. 인수인계·재현·롤백

### 재현

Source `c9fc1be...`에서 wrapper → readiness → actual 순서로 실행했으며 재실행하지 않는다.

### 롤백

Actual 전에는 evidence-only commit을 revert할 수 있다. Actual 후 report/lease는 삭제하지 않는다.

### 다음 개발자 시작점

D-127과 A-076 aggregate report에서 시작한다. 다음 교정은 3초 전체 timeout 정책을 먼저
결정하고 새 identity/승인을 받아야 한다.

## 14. 남은 위험·미해결 질문·다음 단계

- Network probe는 PASS했지만 authenticated DeepSeek 2xx와 exact five-field acceptance는
  여전히 미확인이다.
- 28.6초≈9×3초와 이중 3초 timeout 경계는 만료 가설을 강하게 지지하지만 exception detail
  비보관으로 확정하지 않는다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

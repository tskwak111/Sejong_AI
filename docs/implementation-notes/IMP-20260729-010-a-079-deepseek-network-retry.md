# IMP-20260729-010 — A-079 DeepSeek network retry

- Date/Time (KST): 2026-07-29T13:30:02+09:00
- Task ID: A-079-DEEPSEEK-NETWORK-RETRY
- Type: implementation-provider-actual
- Status: In Progress — offline/provider evidence pending
- Author/Agent: Codex root agent
- Branch: codex/a-075-deepseek-corrective-actual
- Base commit: 844e53b
- Related plan/ADR/RFP: D-130/D-131, ADR-0028 third amendment, SFR-002, A-077/A-078 plan

## 1. 사용자 요청과 완료 기준

### 요청

사용자는 직전 A-078 실패 시점의 네트워크 이상 가능성을 들어 probe와 조건부 actual을 각각
한 번 다시 실행하도록 승인했다.

### Acceptance Criteria

- A-078 offline/probe evidence를 수정·삭제·재실행하지 않는다.
- Windows lease bytes는 exact LF이며 binary writer로 검증한다.
- 별도 A-079 clean source에서 offline과 readiness가 PASS해야 한다.
- probe 1-call이 HTTP 2xx일 때만 actual run 1회(9 provider calls)를 실행한다.
- retry/rerun0, cost≤USD0.20, 질문/body/invalid value/secret 보관0을 유지한다.
- public/API/DB/data/Web/final-answer provider/dependency는 변경하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인자, Codex 구현·실행자, 독립 검토자 |
| When — 언제 | 2026-07-29 KST |
| Where — 어디서 | private local branch와 ignored A-079 evidence directory |
| What — 무엇을 | binary evidence writer, 별도 A-079 probe/actual/offline identity |
| Why — 왜 | A-078 당시 네트워크 이상 가능성을 새 one-shot evidence로 확인 |
| How — 어떻게 | exact RED/GREEN, clean SHA, offline→readiness→probe→conditional actual |
| How much — 어느 정도 | probe1, 조건부 actual9, retry/rerun0, cap USD0.20 |

## 3. 시작 전 상태

- 관련 파일: A-078 runner/probe/wrapper와 aggregate report, shared actual runner.
- 기존 동작: A-078 offline PASS 뒤 probe transport-no-response1, actual0.
- 발견한 충돌/부채: Windows `os.open` text translation이 LF lease를 CRLF로 저장했다.
- Git 상태: base `844e53b`, A-078 ignored evidence preserved, Draft PR #22.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-131 | A | 네트워크 복구 뒤 새 retry 권한 | probe1 + 2xx 조건 actual9 승인 | 비용·외부 호출 |
| A079-LEASE | D | Windows exact bytes | `O_BINARY` 적용 | evidence gate |

## 5. 설계 결정과 대안

### 선택

Shared exclusive writer를 binary mode로 바꾸고 A-079의 모든 path/gate/sentinel을 A-078과
분리한다.

### 이유

과거 evidence 불변성과 exact-one 실행을 유지하면서 CRLF 결함과 네트워크 재시도를 분리한다.

### 고려했지만 선택하지 않은 대안

- A-078 lease 삭제·재실행: 증거 불변성 위반.
- actual 9회를 probe 없이 실행: 비용·장애 확대.
- retry 자동화: 사용자의 “한 번씩” 승인과 retry0 위반.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| shared/probe evidence writer | Windows binary-open | exact bytes |
| A-079 probe/actual/offline | disjoint identity | immutable retry |
| tests | exact bytes·identity·one-shot | 회귀 방지 |
| docs/report/version | D-130/D-131 동기화 | 인수인계 |

### 데이터 흐름/상태 변화

승인된 synthetic fixture의 한 provider case만 redaction/SafeQuestion 뒤 probe로 전달한다.
질문·본문은 보관하지 않고 aggregate count만 기록한다. Application DB는 사용하지 않는다.

### 오류·빈 상태·롤백

Probe가 2xx가 아니면 immutable FAIL로 actual을 차단한다. 실행된 lease/report는 삭제하지 않는다.

## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.13.2-deepseek-split-timeout
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.3-explicit-route-matrix
- test_suite: 2.2.7-a078-prelease-hardening
- documentation: 2.31.8-a078-prelease-hardening-pre-execution

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.13.2 | 동일 | product runtime 불변 |
| Web | 0.8.0 | 동일 | UI 불변 |
| API | 4.0.0 | 동일 | 공개 계약 불변 |
| DB schema | 0.5.0 | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | 데이터 불변 |
| Mock data | 0.0.0 | 동일 | 데이터 불변 |
| Prompt set | 0.4.3 | 동일 | prompt 불변 |
| Test suite | 2.2.7 | 2.2.8 | A-079/exact-byte tests |
| Docs | 2.31.8 | 2.31.9 pre-execution | D-130/D-131/A-079 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| exact lease RED | expected FAIL | CRLF≠LF | pytest terminal |
| binary writer GREEN | PASS | 2 passed | pytest terminal |
| A-079 runner/probe/wrapper focused | PASS | 14 passed | pytest terminal |
| A-074~A-079 related area | PASS | 183 passed in 51.56s | pytest terminal |
| Ruff format/lint | PASS | 9 files | terminal |
| Mypy strict | PASS | 6 source files | terminal |
| Docs/secret/diff | PASS | no secret output | terminal |
| Final independent scoped review | READY | Critical0 / Important0 / Minor0 | read-only reviewer |

### 미실행 검증과 이유

A-079 related-area/static/docs/secret review, clean commit, offline/readiness/provider calls은 아직
실행 전이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: raw/masked question과 provider body/invalid value/secret 보관0.
- Security: A-078을 보존하고 exact binary lease와 disjoint A-079 identity를 사용한다.
- Accessibility: UI 변경 없음.
- Performance/cost: connect3/read+complete10, retry0, probe1+조건부9, cap USD0.20.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 없음.
- mock/AI 생성: approved synthetic classifier fixture만 사용.
- schema/lineage: DB/official lineage 불변.
- verified date: 2026-07-29.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 사용자의 재시도 권한은 A-079 probe 1-call과 조건부 actual run 1회에 한정된다.
- A-078은 FAIL 그대로이며 A-079 결과로 소급 변경하지 않는다.
- 자동 merge/public/remote/free-input은 승인되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `getattr(os, "O_BINARY", 0)`으로 Windows와 POSIX를 동시에 지원한다.
- A-079 파일은 검토된 A-078 흐름에서 identity 문자열만 분리했다.

## 13. 인수인계·재현·롤백

### 재현

Clean source에서 A-079 offline wrapper→actual/probe readiness→probe 1회→2xx일 때 actual 1회.

### 롤백

외부 실행 전 binary writer/A-079 commit을 revert한다. 실행 후 evidence는 보존하고 provider를
disabled로 둔다.

### 다음 개발자 시작점

D-130/D-131, ADR-0028 third amendment와 이 노트의 exact-one 상태를 먼저 확인한다.

## 14. 남은 위험·미해결 질문·다음 단계

- External latency가 10초를 넘으면 probe는 다시 transport FAIL할 수 있다.
- A-079 결과와 final independent review가 남았다.

## 15. 자체 리뷰

- [ ] 요청 충족
- [ ] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

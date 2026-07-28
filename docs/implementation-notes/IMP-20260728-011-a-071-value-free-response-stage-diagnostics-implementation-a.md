# IMP-20260728-011 — A-071 value-free response-stage diagnostics implementation and exact-one actual

- Date/Time (KST): 2026-07-28T20:37:06+09:00
- Task ID: A-071-RESPONSE-STAGE-DIAGNOSTICS
- Type: implementation-provider-actual
- Status: Done — diagnostic implementation PASS; exact-one actual acceptance FAIL
- Author/Agent: 사용자 승인 / Codex 구현·통합·actual 실행
- Branch: main
- Base commit: 7eb8515
- Exact actual source: 0646db06627626f06701d30d628a04adc6264055
- Related plan/ADR/RFP: D-108~D-111, ADR-0027,
  `docs/superpowers/specs/2026-07-28-upstage-classifier-value-free-response-stage-diagnostics-design.md`,
  `docs/superpowers/plans/2026-07-28-upstage-classifier-value-free-response-stage-diagnostics.md`

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 A-071 written specification을 승인하고 빠른 구현을 요청했다. 승인된 범위는
production classifier와 동일한 parser에서 value-free terminal stage를 관찰하고, clean
source에서 fixed 20 actual을 정확히 한 번 실행해 D-107의 strict-decision 거부 단계를 찾는
것이다.

### Acceptance Criteria

- closed 13-stage enum과 strict contract 단계 parser
- HTTP response당 observer 최대 1회, timeout/no-response는 0회
- observer 실패가 시민 decision/fallback을 바꾸지 않음
- actual report는 aggregate stage count만 기록하고 per-fixture stage와 provider body는 0
- 기존 public parser·fail-closed fallback·prompt/profile/API/DB/data/dependency 불변
- TDD, Ruff, Mypy, docs, secret, diff gate 통과
- clean committed source에서 fixed 20·expected outbound 9·retry 0·USD0.20 actual 정확히 1회
- actual 결과가 FAIL이어도 재실행하지 않고 정확히 기록
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 명세와 exact-one actual을 승인했고 Codex가 inline TDD·통합·검증·실행했다. |
| When — 언제 | 2026-07-28 KST, source commit `0646db0` 뒤 actual 1회 |
| Where — 어디서 | local/private Windows 저장소의 API LLM adapter, actual runner, tests, docs |
| What — 무엇을 | 13-stage typed diagnostic, optional observer, aggregate report, exact-one actual |
| Why — 왜 | D-107 9/9 HTTP 2xx 응답이 strict decision 전 어느 단계에서 거부됐는지 본문 없이 찾기 위해 |
| How — 어떻게 | RED→GREEN, enum-only observer, Counter aggregate, clean-source lease/preflight, retry 0 |
| How much — 어느 정도 | actual 20 selected·0 skip·11 provider-free·9 outbound, 비용 USD0.002626503 |

## 3. 시작 전 상태

- 관련 파일: `classifier_contracts.py`, `upstage_classifier.py`,
  `run_hybrid_rag_actual.py`와 해당 tests, version/SOT/decision/task docs
- 기존 동작: D-107은 9/9 HTTP 2xx·usage accepted였지만 strict decision accepted 0이고 모든
  parser 실패를 `None`으로 합쳐 정확한 terminal stage를 알 수 없었다.
- 발견한 충돌/부채: provider body 비보관 정책 때문에 body inspection은 허용되지 않았다.
- Git 상태: 시작 HEAD `7eb8515`, actual 전 implementation source를 `0646db0`으로 commit하고
  clean tree를 확인했다. `origin/main` push/merge는 수행하지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-071 | B/High | strict response 거부 terminal stage | enum-only aggregate actual | Resolved: `KEY_SET_REJECTED` 9/9 |
| A-072 | B/High | exact five-key 반환을 위한 다음 단일 교정 | 새 설계·human actual gate | 현재 validator/prompt를 임의 완화하지 않음 |

## 5. 설계 결정과 대안

### 선택

production parser에 `ClassifierResponseStage` optional observer를 추가하고 runner가 enum별 합계만
기록하도록 했다. 기존 public parser는 내부 staged result를 감싼 뒤 실패 시
`CLASSIFIER_DECISION_INVALID`만 반환한다.

### 이유

실제 runtime과 진단 parser drift를 없애고, 타입상 질문·provider content·예외·status detail을
observer에 전달할 수 없게 만들기 위해서다.

### 고려했지만 선택하지 않은 대안

- runner의 별도 response 재파싱: production parser와 drift 가능성이 있어 기각
- provider body/exception/status detail 로깅: 비보관·value-free 정책 위반으로 기각
- invalid response를 느슨하게 수락: closed contract와 시민 안전 fallback을 깨므로 기각
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `classifier_diagnostics.py` | 13개 closed terminal enum | provider-controlled 값 없는 공통 진단 계약 |
| `classifier_contracts.py` | 단계형 parser와 기존 generic wrapper | JSON→key→type→enum/shape→catalog 순서 고정 |
| `upstage_classifier.py` | optional observer와 response boundary stage mapping | actual production 경로에서 exactly-once 관찰 |
| `run_hybrid_rag_actual.py` | aggregate recorder·13 count·total/acceptance invariant | per-fixture 연결 없이 원인 단계 증거 생성 |
| LLM/runner tests | 모든 stage, observer isolation, report/order/invariant | RED→GREEN과 회귀 |
| SOT/decision/ambiguity/TASKS/version/docs | D-110/D-111 및 A-071 결과 | 권위·인수인계 정합성 |
| actual report/archive | D-107 archive와 source `0646db0` current evidence | 감사 증거 불변 보존 |

### 데이터 흐름/상태 변화

PII-free fixed fixture → 기존 redaction/policy gate → bounded catalog request → response in memory →
production parser → `ClassifierDecision | None`와 fixed enum → in-memory Counter → aggregate report.
DB write와 질문/provider body 직렬화는 없다.

### 오류·빈 상태·롤백

invalid response는 계속 `None`이다. observer exception은 삼킨다. HTTP response가 없으면 stage를
만들지 않는다. stage total과 response total이 다르거나 accepted 9가 아니면 actual은 FAIL한다.
이번 actual은 `KEY_SET_REJECTED` 9라 FAIL했고 재실행하지 않았다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.2-response-stage-diagnostics
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.1-json-mode-instruction
- test_suite: 2.1.5-response-stage-diagnostics
- documentation: 2.29.7

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.1-bounded-hybrid-rag | 0.12.2-response-stage-diagnostics | internal diagnostic observer |
| Web | 0.8.0-guided-chat | unchanged | Web 영향 없음 |
| API | 4.0.0-draft | unchanged | 공개 wire 계약 불변 |
| DB schema | 0.5.0-local | unchanged | DB write/migration 없음 |
| Official data | 0.1.0-initial.2 | unchanged | protected immutable input |
| Mock data | 0.0.0-not-populated | unchanged | mock 생성 없음 |
| Prompt set | 0.4.1-json-mode-instruction | unchanged | 단일 진단 변수 유지 |
| Test suite | 2.1.4-json-mode-regression | 2.1.5-response-stage-diagnostics | stage/runner 회귀 |
| Docs | 2.29.6 | 2.29.8 | implementation + actual evidence |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| contract RED | expected import failure | collection 1 failure | pytest output |
| transport RED | expected constructor keyword failure | 16 failed, 61 passed | pytest output |
| runner RED | expected recorder/signature failure | 4 failed, 20 passed | pytest output |
| focused GREEN | PASS | 142 passed, 1 dependency warning | pytest output |
| Ruff check/format | PASS | 39 files formatted/checked | command output |
| Mypy LLM | PASS | 18 source files | command output |
| repository docs | PASS | documentation check passed | command output |
| secret pattern scan | PASS | findings 0 | command output |
| diff checks | PASS | whitespace errors 0 | git output |
| independent final review | merge-ready | Critical 0, Important 0, Minor 1 | reviewer result |
| exact-one actual | expected gate executed once; acceptance FAIL | 20/0/11/9, 17,331ms | `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md` |

### 미실행 검증과 이유

저장소 전체 Web/DB/official-data gate는 해당 영역을 변경하지 않았고 승인 계획이 focused gate를
요구했으므로 반복하지 않았다. 새 actual과 provider body inspection은 명시적으로 실행하지 않았다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: approved PII-free fixtures만 사용, 질문/provider body/status detail/key/DSN 보관 0
- Security: secret scan PASS, key는 presence boolean만, protected inputs clean, retry 0
- Accessibility: Web/public response 변경 없음
- Performance/cost: 9 outbound, concurrency 1, elapsed 17,331ms, VAT 포함 USD0.002626503로
  ledger와 일치하고 USD0.20 cap 미만

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2` ACTIVE/OFFICIAL 19를 read-only catalog 입력으로 사용; 변경 0
- mock/AI 생성: PII-free synthetic UAT만 actual selector 입력, 시민 데이터 아님
- schema/lineage: fixture·coverage·official records·release manifest·offline evidence SHA pin 유지
- verified date: 2026-07-28 KST

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- actual은 전체 PASS가 아니다. 9/9가 exact five-key 검증의 `KEY_SET_REJECTED`에서 종료했다.
- 실제 local 시민 경로는 계속 fail-closed template/followup 동작을 유지한다.
- 추가 corrective actual은 승인되지 않았으며 A-072 설계와 별도 인간 승인이 필요하다.
- push/PR/merge, public/remote, DB reset/seed, official data 변경은 수행하지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- enum 값 정의, parser 분기, optional callable observer, Counter field ordering과 helper 구조는
  같은 공개 계약 안의 내부 구현 세부다.

## 13. 인수인계·재현·롤백

### 재현

provider 호출 없이 focused tests·Ruff·Mypy·docs·secret gate를 실행한다. actual evidence는 이미
고정됐으므로 current runner command를 다시 실행하지 않는다.

### 롤백

runtime 진단이 문제가 되면 implementation commit `0646db0`을 revert한다. D-107 archive와 current
actual report는 감사 증거이므로 삭제·덮어쓰기하지 않는다. DB/data rollback은 없다.

### 다음 개발자 시작점

A-072에서 `KEY_SET_REJECTED` aggregate만 근거로 exact five-key correction을 한 변수씩 설계한다.
provider body를 복원하거나 strict validator를 완화하지 않는다.
## 14. 남은 위험·미해결 질문·다음 단계

- Upstage가 exact five keys 외 어떤 key shape를 반환했는지는 의도적으로 알 수 없다.
- provider-supported structured schema 또는 더 명시적인 closed-output instruction 중 단일 변수를
  공식 문서와 offline TDD로 비교해야 한다.
- Minor review debt: observer 예외 격리 테스트는 accepted 경로를 직접 고정한다. 공통 observer
  호출부가 rejected에도 동일하게 적용되므로 현재 blocking issue는 아니며 A-072 offline test에서
  rejected case를 추가할 수 있다.
- 새 provider call은 사용자 승인 전 0이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

# IMP-20260728-009 — A-070 JSON mode 교정과 corrective actual

- Date/Time (KST): 2026-07-28T19:18:25+09:00
- Task ID: A-070-JSON-MODE-CORRECTIVE
- Type: bugfix-provider-actual
- Status: Done — request-validation 4xx fixed; strict decision actual FAIL
- Author/Agent: 사용자 결정자 / Codex 구현·검증
- Branch: main
- Base commit: 4cb42ff
- Related plan/ADR/RFP: D-106/D-107, A-070/A-071, ADR-0027,
  `CHAT-HYBRID-RAG-001`

## 1. 사용자 요청과 완료 기준

### 요청

사용자의 `Q-LLM-013: A`를 반영해 closed classifier prompt에 명시적 JSON 출력 지시를
TDD로 복원하고, 다른 변수는 고정한 PII-free corrective actual을 정확히 한 번 실행한다.
실패하면 재시도하지 않고 aggregate-only 증거와 source-of-truth를 갱신한다.

### Acceptance Criteria

- 먼저 현재 prompt가 JSON 지시를 포함하지 않는다는 RED를 재현한다.
- route·field·catalog·model·timeout·retry를 바꾸지 않고 명시적 JSON 지시만 복원한다.
- 실제 20-topic catalog의 4,096자 상한과 focused classifier/runner 테스트를 통과한다.
- D-106 FAIL을 archive하고 clean committed source에서 fixed 20을 정확히 한 번 실행한다.
- 질문·provider body·status detail·key·DSN을 출력·보관하지 않고 USD 0.20 cap을 지킨다.
- 성공/실패를 숨기지 않고 decision·ambiguity·version·report·INDEX를 동기화한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 Q-LLM-013=A와 exact-one actual을 승인하고 Codex가 구현·검증했다. |
| When — 언제 | 2026-07-28 19:02~19:22 KST |
| Where — 어디서 | local Windows private `main`, API classifier prompt/test, aggregate report와 권위 문서 |
| What — 무엇을 | explicit `JSON만` prompt patch, regression test, D-106 archive, D-107 actual 1회 |
| Why — 왜 | D-106의 9/9 provider 4xx가 JSON object mode의 명시 지시 누락 때문인지 단일 변수로 확인하기 위해 |
| How — 어떻게 | RED→minimal GREEN, 4,096 bound 검증, source `4cb42ff` commit, retry 0 actual, value-free 집계 |
| How much — 어느 정도 | code/test 2파일, fixed 20 중 provider-free 11/outbound 9, actual cost USD 0.002646303 VAT 포함 |

## 3. 시작 전 상태

- 관련 파일: `classifier_prompt.py`, `test_prompt.py`, `upstage_classifier.py`,
  D-106 actual report, A-070·decision/version 문서
- 기존 동작: request payload는 `response_format=json_object`였으나 current 9개 prompt에는
  literal `JSON` 지시가 0개였고 D-106 actual은 9/9 HTTP 4xx였다.
- 발견한 충돌/부채: historical working prompt에는 JSON 지시가 있었다. 긴 지시를 단순 추가하면
  real 20-topic/256-char prompt가 4,140자로 4,096 상한을 깨뜨렸다.
- Git 상태: 선행 진단 문서는 `3cf606c`, actual source patch는 clean commit `4cb42ff`로 고정했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-013 | 인간 결정 | JSON 지시 TDD 복원과 corrective actual 1회 | A / D-107 | prompt/test/provider actual |
| A-070 | 해결 | D-106 4xx의 1순위 원인 | single-variable actual로 4xx 해소 확인 | request validation |
| A-071 | 미해결 | 2xx body가 strict closed decision 전에 9/9 거부된 단계 | 본문 미보관, 추가 호출 금지 | future value-free diagnostics |

## 5. 설계 결정과 대안

### 선택

`JSON만;`을 system message 앞에 추가하고, 의미를 보존하면서 `n:null→n=∅`,
`row.I→rowI`로 축약해 총 prompt 상한을 유지했다. provider model, request shape,
closed enum과 server validation은 그대로 두었다.

### 이유

OpenAI-compatible JSON object mode가 prompt에 명시적 JSON 지시를 요구하는 조건과 historical
working evidence를 가장 작은 단일 변수로 검증할 수 있다. 기존 fail-closed 경계를 유지한다.

### 고려했지만 선택하지 않은 대안

- timeout/token/key/base URL 동시 변경: 원인 격리가 깨져 제외했다.
- response body/status detail 저장: 개인정보·공급자 내용 비보관 정책 때문에 제외했다.
- 긴 자연어 지시: real catalog 4,096자 상한 회귀 때문에 compact 지시로 교정했다.
- 실패 후 재호출: 승인된 정확히 1회 경계 때문에 금지했다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `apps/api/src/sejong_ai_api/llm/classifier_prompt.py` | explicit `JSON만`과 bound-preserving compact notation | 4xx request validation 교정 |
| `apps/api/tests/llm/test_prompt.py` | real prompt에 literal JSON 지시가 반드시 존재하는 회귀 테스트 | 재발 방지 |
| `docs/test-reports/archive/...D106-4XX-FAIL.md` | 이전 canonical FAIL archive | 증거 불변 보존 |
| `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md` | D-107 aggregate-only exact-one result | source/cost/acceptance 증거 |
| SOT·decision·ambiguity·TASKS·version·CHANGELOG | D-107 결과와 A-071 gate 동기화 | 단일 권위 유지 |

### 데이터 흐름/상태 변화

PII-free fixed fixture → deterministic gate 11건(provider 0) / masked provider selector 9건 →
Upstage 2xx+usage 9건 → strict decision parser 0건 accepted → caller `None` fail-closed.
DB·official/mock data·시민 원문 저장은 0이다.

### 오류·빈 상태·롤백

실제 결과는 acceptance FAIL이다. D-106의 4xx는 0으로 바뀌었으나 closed decision 0/9라 runtime
fallback을 유지한다. actual은 재실행하지 않았다. code rollback은 `4cb42ff`를 revert하고,
evidence rollback은 보고서를 삭제하지 말고 archive한 뒤 후속 결정으로 대체한다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.1-bounded-hybrid-rag
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.1-json-mode-instruction
- test_suite: 2.1.4-json-mode-regression
- documentation: 2.29.4

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.1 | 0.12.1 | 불변 |
| Web | 0.8.0 | 0.8.0 | 불변 |
| API | 4.0.0-draft | 4.0.0-draft | 공개 계약 불변 |
| DB schema | 0.5.0-local | 0.5.0-local | DB 미사용 |
| Official data | 0.1.0-initial.2 | 0.1.0-initial.2 | immutable |
| Mock data | 0.0.0-not-populated | 동일 | 불변 |
| Prompt set | 0.4.0-topic-coverage | 0.4.1-json-mode-instruction | explicit JSON 지시 |
| Test suite | 2.1.3-value-free-provider-diagnostics | 2.1.4-json-mode-regression | 회귀 테스트 |
| Docs | 2.29.3 | 2.29.4 | 결정·actual 동기화 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| focused JSON regression before fix | RED | 1 failed | pytest output |
| prompt/classifier/runner focused pytest | PASS | 76 passed | local stdout |
| Ruff check/format + Mypy prompt | PASS | 2 files / 1 source | local stdout |
| repository docs + secret scan + diff check | PASS | exit 0 | local stdout |
| `run_hybrid_rag_actual.py` | expected process exit 1 / evidence FAIL | 20.6s, exact 1 run | current actual report |
| D-107 aggregate | 20 selected, 0 skip, 11 provider-free, 9 outbound; 9 2xx; decision 0 | 19,655ms provider phase | current actual report |
| cost | cap PASS | USD 0.002646303 ≤ 0.20 | current actual report |

### 미실행 검증과 이유

전체 repository/API/Web/DB gate는 prompt-only patch와 fixed runner result에 비례하지 않아
반복하지 않았다. focused classifier/runner와 docs/security gate를 사용했다. 추가 provider
actual은 정확히 1회 승인 경계 때문에 실행하지 않았다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: synthetic PII-free fixed subset만 사용. 질문·응답 본문·status detail 보관/출력 0.
- Security: key presence boolean만 확인, key/DSN 0. protected inputs clean, secret scan PASS.
- Accessibility: Web/UI 변경 0.
- Performance/cost: timeout 3초, retry 0, concurrency 1. 9 responses 총 19,655ms,
  observed/ledger USD 0.002646303 VAT 포함, cap USD 0.20.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2` bytes·hash·19 ACTIVE baseline 변경 0.
- mock/AI 생성: versioned PII-free UAT 질문은 입력으로만 사용하고 결과 body는 저장하지 않았다.
- schema/lineage: DB/migration/contract 변경 0. report가 source와 fixture/data hash를 고정한다.
- verified date: 2026-07-28 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 4xx request rejection은 explicit JSON 지시 복원으로 해소됐다.
- 전체 Hybrid RAG actual은 아직 PASS가 아니다. 9/9 strict closed decision이 거부됐다.
- 실패 후 재시도하지 않았고 추가 실제 호출은 별도 승인 전 금지다.
- 비용은 USD 0.002646303(VAT 포함)이며 provider 청구 화면의 최종 정산과 다를 수 있다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- compact prompt 표기와 server-side closed validation은 공개 API에 노출되지 않는다.
- `provider_contract_mismatch_count=0`은 accepted decision 중 expected route mismatch가 0이라는
  뜻이며, response parser가 body를 수락했다는 뜻이 아니다.

## 13. 인수인계·재현·롤백

### 재현

1. source `4cb42ff`와 pinned fixture/data hashes를 확인한다.
2. provider 비밀값을 출력하지 않고 exact combined classifier profile을 process scope로 설정한다.
3. secret/protected-input/clean-tree preflight를 통과한다.
4. actual runner는 이미 실행됐으므로 다시 실행하지 말고 current report를 읽는다.

### 롤백

prompt 동작만 되돌릴 때 `4cb42ff`를 revert한다. D-106/D-107 report는 감사 증거이므로 삭제하거나
덮어쓰지 말고 archive한다. DB/data migration rollback은 해당 없음.

### 다음 개발자 시작점

A-071에서 outbound 없이 response parser의 value-free stage counter를 먼저 TDD 설계한다.
새 actual이 필요하면 PII-free subset·횟수·비용을 인간에게 별도 승인받는다.
## 14. 남은 위험·미해결 질문·다음 단계

- strict response rejection의 정확한 단계는 A-071 Pending이다.
- current citizen runtime은 안전한 fallback을 유지하므로 안전 회귀는 없지만 AI 분류 품질
  actual PASS는 아직 주장할 수 없다.
- public/remote/실제 시민 free-input provider 사용은 계속 승인 범위 밖이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

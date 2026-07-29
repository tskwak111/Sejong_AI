# IMP-20260729-007 — A-075 DeepSeek corrective actual

- Date/Time (KST): 2026-07-29T10:35:59+09:00
- Task ID: A-075-DEEPSEEK-CORRECTIVE-ACTUAL
- Type: implementation-provider-actual
- Status: In progress — tooling GREEN; offline/actual unexecuted
- Author/Agent: Codex root agent
- Branch: codex/a-075-deepseek-corrective-actual
- Base commit: 67fe37c
- Related plan/ADR/RFP: D-124, ADR-0028, A-075 discovery/specification/plan

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 DeepSeek exact 설정을 완료하고 A-075 corrective actual 1회를 명시 승인했다.

### Acceptance Criteria

- A-074 evidence와 invocation/rerun 상태를 변경하지 않는다.
- 새 A-075 offline gate를 clean source에서 정확히 한 번 실행한다.
- PASS일 때만 readiness와 actual 1회를 실행한다.
- 20/0, deterministic/provider 11/9, outbound/2xx/parse/accepted/match 9, retention 0,
  retry/rerun 0, concurrency 1, USD 0.20 이하를 aggregate-only로 판정한다.
- 결과를 문서·버전·INDEX·Draft PR에 반영하고 자동 병합하지 않는다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인자와 Codex 구현·검토자 |
| When — 언제 | 2026-07-29 KST |
| Where — 어디서 | private local branch, ignored `apps/api/.env`, synthetic fixture와 evidence tooling |
| What — 무엇을 | A-075 전용 offline/actual one-shot identity와 실행 |
| Why — 왜 | A-074 immutable offline FAIL 뒤 실제 DeepSeek 분류 호환성을 별도 증거로 확인 |
| How — 어떻게 | 검증된 evaluator를 최소 profile seam으로 재사용하고 report/lease/gate를 분리 |
| How much — 어느 정도 | fixed 20, provider 9 outbound, retry 0, 비용 상한 USD 0.20 |

## 3. 시작 전 상태

- 관련 파일: A-074 runner/wrapper/tests, ADR-0028, A-074 note/runbook.
- 기존 동작: provider implementation은 merged main에 있으나 A-074 offline FAIL로 actual 0/0.
- 발견한 충돌/부채: local main은 origin/main과 diverged했으므로 변경하지 않고
  `67fe37c...`에서 새 branch를 생성했다. A-075 증거 identity는 기존에 없다.
- Git 상태: clean baseline `67fe37c1bbc6dcda028fbf65f3694380ba399e2c`.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-075-ACTUAL | A | 새 actual 권한 | 사용자 1회 승인 | 비용/외부 호출 |
| A-075-IDENTITY | C | runner 재사용 방식 | 최소 profile adapter | evidence tooling |

## 5. 설계 결정과 대안

### 선택

A-074 runner 전체 복사 대신 기존 evaluator에 fail-closed evidence profile seam을 추가하고
A-075 thin entry point를 사용한다. Offline wrapper는 실행·종료 보존 로직을 유지하되 A-075
경로와 sentinel만 가진 별도 파일이다.

### 이유

보안 로직 중복을 최소화하면서 A-074 파일과 A-075 파일의 충돌을 구조적으로 막는다.

### 고려했지만 선택하지 않은 대안

1,473-line actual runner 전체 복제는 장기 drift 위험 때문에 버렸다. 광범위 generic framework
refactor는 one-shot 작업 범위를 초과해 버렸다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `run_deepseek_classifier_actual.py` | temporary fail-closed evidence profile seam | evaluator 재사용 |
| `run_deepseek_classifier_corrective_actual.py` | A-075 paths/gate/lease binding | identity 분리 |
| `run_a075_offline_gate.ps1` | A-075 one-shot offline wrapper | clean source 증거 |
| runner/wrapper tests | disjoint identity·restore·drift·one-shot PASS/FAIL | TDD |
| authority/version docs | D-124와 task/versions 기록 | 추적성 |

### 데이터 흐름/상태 변화

현재 checkpoint는 provider/network 호출 0이다. actual은 offline PASS와 readiness 뒤에만 시작한다.

### 오류·빈 상태·롤백

profile mismatch, A-074 core drift, dirty tree, 기존 A-075 artifact, offline FAIL 또는 readiness
FAIL은 lease/network 전에 종료한다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.13.1-selectable-classifier-provider-hardening
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.3-explicit-route-matrix
- test_suite: 2.2.2-a074-offline-gate-correction
- documentation: 2.31.2-a074-offline-gate-fail-closeout

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.13.1 | 동일 | 제품 동작 불변 |
| Web | 0.8.0 | 동일 | 영향 없음 |
| API | 4.0.0 | 동일 | 계약 불변 |
| DB schema | 0.5.0 | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | fixture identity 유지 |
| Mock data | 0.0.0 | 동일 | 영향 없음 |
| Prompt set | 0.4.3 | 동일 | prompt 불변 |
| Test suite | 2.2.2 | 2.2.3 | A-075 evidence tests |
| Docs | 2.31.2 | 2.31.3 | 승인·설계·계획 checkpoint |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| new actual runner RED | 4 FAIL | runner absent | terminal evidence |
| new+existing actual runner GREEN | 57 PASS | 2.44s | terminal evidence |
| new offline wrapper RED | 2 FAIL | wrapper absent | terminal evidence |
| A-074+A-075 wrapper GREEN | 11 PASS | 29.53s | terminal evidence |
| focused provider/runner/wrapper | PASS | 305 tests, 1 known warning | terminal evidence |
| relevant area | PASS | 1,042 tests + 5 subtests, 1 known warning | terminal evidence |
| final runner focused after mutation test | PASS | 58 tests | terminal evidence |
| Ruff format/check | PASS | 129 files | terminal evidence |
| API Mypy | PASS | 123 source files | terminal evidence |
| runner Mypy strict | PASS | 6 source files | terminal evidence |
| A-075 PowerShell parser | PASS | 1,523 tokens / 0 errors | terminal evidence |
| docs/secret/diff | PASS | value-free | repository scripts |

### 미실행 검증과 이유

Offline/actual은 clean source commit 뒤 실행한다. 영역 전체와 정적 검사는 완료했다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: key 값·질문·provider body를 출력하지 않았다. 설정은 boolean/name-only로 확인했다.
- Security: A-074와 모든 report/offline path 및 lease payload를 분리했다.
- Accessibility: UI 변경 없음.
- Performance/cost: 현재 outbound 0/USD 0; actual cap USD 0.20.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`, 변경 없음.
- mock/AI 생성: 기존 PII-free synthetic fixture만 사용.
- schema/lineage: DB/data lineage 변경 없음.
- verified date: 2026-07-29 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- A-075 actual 1회는 승인됐으며 성공/실패와 무관하게 재실행하지 않는다.
- A-074 FAIL 1/0과 actual 0/0은 이 작업으로 변경되지 않는다.
- public/remote/실제 시민 운영은 승인되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- profile seam은 실행 동안만 core identity를 바꾸고 `finally`에서 A-074 default를 복원한다.
- ignored local selector 누락은 비밀값을 건드리지 않고 exact non-secret 한 줄만 추가했다.

## 13. 인수인계·재현·롤백

### 재현

계획의 Task 4 검증 후 clean source SHA를 commit하고 A-075 wrapper → readiness → actual 순서로
실행한다.

### 롤백

actual 전에는 evidence-only 변경을 revert하고 `CLASSIFIER_PROVIDER=disabled`로 되돌린다.
actual 후 report/lease는 삭제하거나 재사용하지 않는다.

### 다음 개발자 시작점

`docs/superpowers/plans/2026-07-29-deepseek-corrective-actual.md` Task 4에서 계속한다.
## 14. 남은 위험·미해결 질문·다음 단계

- 실제 `deepseek-v4-flash` 2xx와 exact decision acceptance는 actual 전까지 미확인이다.

## 15. 자체 리뷰

- [ ] 요청 충족
- [ ] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

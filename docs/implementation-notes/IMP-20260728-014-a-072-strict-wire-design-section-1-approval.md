# IMP-20260728-014 — A-072 strict wire design section 1 approval

- Date/Time (KST): 2026-07-28T21:27:31+09:00
- Task ID: A-072-DESIGN-SECTION-1
- Type: decision-design
- Status: Decision-only
- Author/Agent: 사용자 승인자 / Codex 기록·후속 설계
- Branch: main
- Base commit: 6d785be
- Related plan/ADR/RFP: D-112/D-113, ADR-0027, A-072, IMP-20260728-012/013

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 A-072의 설계 1부에 대해 `설계 1부 승인`이라고 명시했다.

### Acceptance Criteria

- 설계 1부 승인 범위를 권위 문서와 task 상태에 기록한다.
- 승인되지 않은 설계 2부·written specification·제품 코드를 확정하거나 구현하지 않는다.
- public API/DB/data/dependency를 변경하지 않고 provider call을 실행하지 않는다.
- 정규화·오류·테스트·버전 경계를 담은 설계 2부를 검토 가능한 상태로 제시한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 설계 1부를 승인하고 Codex가 D-113으로 기록했다. |
| When — 언제 | 2026-07-28 21:27 KST |
| Where — 어디서 | `main`의 source-of-truth, decision, ambiguity, task, version, implementation note |
| What — 무엇을 | strict 5-key string wire, `NONE` normalization과 server authority 경계를 승인했다. |
| Why — 왜 | D-111의 exact-key 실패를 공식 structured output으로 교정하되 public 계약과 안전 경계를 보존하기 위해서다. |
| How — 어떻게 | 설계 checkpoint만 문서화하고 제품 code/provider actual은 다음 승인 뒤로 유지한다. |
| How much — 어느 정도 | 문서·메타만 변경, runtime/API/DB/data/dependency/provider call 0, 비용 USD 0 |

## 3. 시작 전 상태

- 관련 파일: `upstage_classifier.py`, `classifier_contracts.py`, `classifier_prompt.py`와
  `test_classifier_contracts.py`, `test_prompt.py`, Upstage classifier transport tests.
- 기존 동작: provider request는 `json_object`, parser는 canonical JSON null을 포함하는 exact
  five-key object를 요구한다.
- 발견한 충돌/부채: provider-only `NONE`을 public parser 전체에서 허용하면 기존 canonical
  contract가 넓어질 수 있으므로 별도 wire normalization 경계가 필요하다.
- Git 상태: base `6d785be`, 시작 시 tracked worktree clean.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-072 section 1 | B / High | provider wire와 server authority | Approved / D-113 | provider request/prompt/wire adapter |
| A-072 section 2 | B / High | normalization 위치, stage 분류, exact tests/version | Review | written specification과 TDD plan |

## 5. 설계 결정과 대안

### 승인된 선택

- provider response는 exact required string 5필드다.
- nullable 대상 `intent`, `topic_id`, `coverage_id`, `pending_slot`은 exact `NONE`으로 표현한다.
- provider-only adapter가 `NONE`을 내부 `None`으로 바꾼 뒤 기존 closed parser를 호출한다.
- prompt는 canonical full field names만 사용한다.
- provider schema는 동적 catalog enum을 복제하지 않고 server validator가 권위를 유지한다.
- retry 0과 fail-closed fallback을 유지한다.

### 고려했지만 선택하지 않은 대안

- public parser가 `NONE`도 직접 수용: provider 경계와 provider-neutral contract가 섞이고 기존
  strict public/internal 테스트 의미가 넓어져 제외한다.
- 모든 enum/catalog를 provider schema에 중복: dynamic ACTIVE catalog drift와 schema 크기 증가로
  제외한다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| 권위 문서 | D-113과 설계 1부 Approved 상태 | 승인 추적 |
| version/changelog | docs 2.29.10 | 문서 checkpoint 식별 |
| 제품 코드·계약·DB·data | 변경 없음 | brainstorming 승인 gate |

### 데이터 흐름/상태 변화

이번 요청의 runtime 상태 변화는 없다. 설계 2부 제안은 provider-only fresh schema builder,
wire normalizer, existing strict validator, fixed terminal-stage observer 순서로 분리한다.

### 오류·빈 상태·롤백

설계 1부는 exact `NONE` 외 유사 문자열·null·lowercase·추가/누락 key를 수용하지 않는다.
구체적인 stage mapping과 regression matrix는 설계 2부 승인 대상이다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.2-response-stage-diagnostics | unchanged | 제품 코드 0 |
| Web | 0.8.0-guided-chat | unchanged | UI 변경 0 |
| API | 4.0.0-draft | unchanged | 공개 계약 변경 0 |
| DB schema | 0.5.0-local | unchanged | migration/DB 실행 0 |
| Official data | 0.1.0-initial.2 | unchanged | 공식 데이터 변경 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 변경 0 |
| Prompt set | 0.4.1-json-mode-instruction | unchanged | prompt code 변경 0 |
| Test suite | 2.1.5-response-stage-diagnostics | unchanged | test code 변경 0 |
| Docs | 2.29.9 | 2.29.10 | 설계 1부 승인 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1회 | stdout |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS — finding 0 | 1회 | exit 0 |
| manifest JSON parse | PASS — `manifest json passed` | 1회 | stdout |
| `git diff --check` | PASS — whitespace error 0 | 1회 | exit 0 |

### 미실행 검증과 이유

- 제품 test/build: 문서-only 승인 기록으로 runtime code가 바뀌지 않았다.
- Upstage actual: 설계 2부·written spec·plan·implementation과 별도의 actual gate 전이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·provider body를 읽거나 기록하지 않았고 external call 0.
- Security: key·DSN·status detail 출력 0, 기존 fail-closed 유지.
- Accessibility: UI 변경 0.
- Performance/cost: runtime 변경 0, provider 비용 USD 0.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 0.
- mock/AI 생성: 변경 0.
- schema/lineage: DB와 ACTIVE/OFFICIAL catalog lineage 변경 0.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 설계 1부만 승인됐다. 설계 2부와 written specification은 아직 Review다.
- 제품 code와 Upstage actual은 실행되지 않았다.
- actual은 구현·offline 검증·clean source commit 뒤 별도 승인이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- provider-specific adapter와 provider-neutral parser를 분리하고 schema builder는 호출마다 fresh
  object를 반환하는 방향을 설계 2부에서 제안한다.
- 기존 13-stage observer에는 새 provider-controlled 값이 아니라 fixed enum만 전달한다.

## 13. 인수인계·재현·롤백

### 재현

1. D-112의 Decision A와 D-113의 설계 1부 승인 행을 확인한다.
2. A-072 task가 section 2 Review인지 확인한다.
3. manifest docs `2.29.10`과 이 노트 INDEX를 확인한다.

### 롤백

역사적 승인 행을 삭제하지 않는다. 후속 설계 변경은 새 결정으로 대체한다. 문서 메타 오기만
되돌릴 때는 이 commit의 문서 diff만 revert한다.

### 다음 개발자 시작점

사용자에게 설계 2부를 제시하고 승인받은 뒤 전체 written specification을 작성·자체 검토한다.
그 전에는 product code나 provider call을 실행하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- 설계 2부 승인.
- 통합 written specification 작성·사용자 검토.
- TDD plan 승인과 offline implementation.
- corrective actual 별도 인간 승인.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

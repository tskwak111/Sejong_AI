# IMP-20260728-015 — A-072 strict classifier wire integrated specification

- Date/Time (KST): 2026-07-28T21:33:59+09:00
- Task ID: A-072-CLASSIFIER-EXACT-KEY-CORRECTION
- Type: decision-design-spec
- Status: Decision-only
- Author/Agent: 사용자 승인자 / Codex specification author
- Branch: main
- Base commit: dc1f66d
- Related plan/ADR/RFP: D-111~D-114, ADR-0025/0027, A-072, A-072 written specification

## 1. 사용자 요청과 완료 기준

### 요청

사용자는 `설계 2부 승인`이라고 명시하고 현재 교정이 필요한 이유를 물었다.

### Acceptance Criteria

- 현재 실패 원인을 단정 가능한 aggregate evidence 범위에서 평이하게 설명한다.
- 설계 2부 승인을 권위 문서와 ADR에 기록한다.
- 승인된 설계 1·2부를 하나의 written specification으로 작성한다.
- placeholder·모순·범위·해석 가능성을 자체 검토한다.
- 사용자 명세 승인 전 product code/provider actual을 실행하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 설계 2부를 승인했고 Codex가 통합 명세를 작성·자체 검토했다. |
| When — 언제 | 2026-07-28 21:33 KST |
| Where — 어디서 | source-of-truth, decision, ADR-0027, A-072 spec, task/version/implementation note |
| What — 무엇을 | exact five-key structured output 교정의 전체 계약·오류·TDD·actual gate를 문서화했다. |
| Why — 왜 | HTTP·JSON은 성공하지만 provider output key가 exact server contract와 달라 9/9 폐기되기 때문이다. |
| How — 어떻게 | strict schema, full-name prompt, provider-only `NONE` normalization, existing validator 재사용으로 설계했다. |
| How much — 어느 정도 | 문서·메타만 변경, runtime/API/DB/data/dependency/provider call 0, 비용 USD 0 |

## 3. 시작 전 상태

- D-111 actual: fixed 20, provider-free 11, outbound 9, HTTP 2xx/usage 9,
  `KEY_SET_REJECTED` 9, accepted/match 0, retry 0.
- current request: `response_format.type=json_object`.
- current prompt: `I/T/C/P`, `∅`, `n` 축약 포함.
- current canonical parser: exact five-key와 JSON null nullable values를 요구한다.
- Git 상태: base `dc1f66d`, 시작 시 tracked worktree clean.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-014 | B / High | nullable strict provider wire | A / D-112 | schema/prompt/wire adapter |
| A-072 section 1 | B / High | architecture/server authority | Approved / D-113 | component/data flow |
| A-072 section 2 | B / High | error/TDD/version/actual gate | Approved / D-114 | spec/plan |

## 5. 설계 결정과 대안

### 선택

- strict `json_schema`, exact required string five-key, `additionalProperties=false`.
- nullable four fields use exact uppercase `NONE`.
- provider-only parser normalizes sentinel and reuses canonical validation authority.
- canonical JSON-null parser/public error stays unchanged.
- full canonical field-name prompt, fixed-stage observer, retry 0, fail-closed.
- offline/root/clean-source 뒤 separately approved fixed-20 actual.

### 이유

JSON object 생성 자체는 성공했지만 exact key가 보장되지 않아 9/9 폐기됐다. server validator를
느슨하게 하면 invalid topic/shape를 성공시킬 수 있으므로 provider output을 계약에 맞추는
방향이 더 안전하다.

### 고려했지만 선택하지 않은 대안

- nullable union: official support 불명확성과 request 4xx 위험.
- prompt-only: D-111에서 exact key를 보장하지 못함.
- parser 완화: 승인된 closed contract와 server authority 훼손.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| A-072 written specification | 설계 1·2부 통합 | 구현 권위 후보 |
| ADR-0027 | strict provider wire addendum | 기존 Hybrid RAG 결정과 연결 |
| decisions/SOT/tasks | D-114, spec Review 상태 | 승인·gate 추적 |
| versions/changelog | docs 2.30.0 | integrated spec checkpoint |
| product code/API/DB/data | 변경 없음 | user written-spec review gate |

### 데이터 흐름/상태 변화

runtime 변화는 없다. target flow는
`SafeQuestion/catalog → strict schema request → provider wire parser → NONE normalization →
existing closed validator → decision/fallback`이다.

### 오류·빈 상태·롤백

wrong JSON/key/type/sentinel/enum/shape/catalog는 fixed enum stage와 fail-closed `None`으로
종료한다. actual은 separate approval 없이는 실행하지 않는다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.2-response-stage-diagnostics | unchanged | code 0 |
| Web | 0.8.0-guided-chat | unchanged | UI 0 |
| API | 4.0.0-draft | unchanged | public contract 0 |
| DB schema | 0.5.0-local | unchanged | migration/DB 0 |
| Official data | 0.1.0-initial.2 | unchanged | official data 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 0 |
| Prompt set | 0.4.1-json-mode-instruction | unchanged | implementation 전 |
| Test suite | 2.1.5-response-stage-diagnostics | unchanged | implementation 전 |
| Docs | 2.29.10 | 2.30.0 | integrated spec Review |

구현 target은 application `0.12.3-structured-classifier-wire`, prompt
`0.4.2-exact-five-key-schema`, tests `2.1.6-structured-classifier-wire`다.

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| placeholder scan | PASS — TBD/TODO/FIXME/미정 0 | spec 1개 | A-072 spec |
| spec consistency scan | PASS — key/sentinel/version/gate references 일치 | spec 1개 | A-072 spec |
| scope/ambiguity self-review | PASS — 한 provider wire correction, actual separate gate | 1회 | A-072 spec |
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1회 | stdout |
| secret-pattern scan | PASS — finding 0 | repository 1회 | exit 0 |
| manifest JSON parse | PASS — `manifest json passed` | 1회 | stdout |
| `git diff --check` | PASS — whitespace error 0 | current diff 1회 | exit 0 |

### 미실행 검증과 이유

- product test/build: code가 바뀌지 않은 written-spec 단계다.
- Upstage actual: 별도 actual 승인 gate 전이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문/provider body/status detail 저장·출력 0, provider call 0.
- Security: key/DSN 출력 0, server validation과 fail-closed 유지.
- Accessibility: UI 변경 0.
- Performance/cost: runtime 변경 0, 비용 USD 0.

## 10. 데이터와 출처 영향

- 공식/mock data: 변경 0.
- DB schema/lineage: 변경 0.
- source metadata: server-owned 현행 유지.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 문제는 AI API 연결 실패가 아니라 AI 응답 필드명과 서버 exact contract의 불일치다.
- 현재는 안전하게 fallback하므로 잘못된 민원 답변을 내보내지는 않지만 AI 분류 효과가 없다.
- written specification은 Review다. 사용자 명세 승인 뒤에만 implementation plan을 작성한다.
- actual은 plan/implementation 승인과 offline/root gate 뒤에도 별도 승인이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- canonical parser와 provider-only parser가 내부 validation helper를 공유하도록 plan에서
  RED/GREEN 단계를 분리한다.
- response format은 fresh object, canonical key source는 한 곳으로 제한한다.

## 13. 인수인계·재현·롤백

### 재현

1. D-111 current actual report의 9/9 `KEY_SET_REJECTED`를 확인한다.
2. A-072 spec의 문제·wire·normalization·tests·actual gate를 읽는다.
3. D-114/ADR-0027 addendum와 manifest docs 2.30.0을 대조한다.

### 롤백

문서-only commit을 revert할 수 있으나 historical D-112~D-114를 삭제해 다시 쓰지 않는다.
설계 변경은 새 decision으로 대체한다.

### 다음 개발자 시작점

사용자의 written specification 승인을 기다린다. 승인 후 `superpowers:writing-plans`로 exact
RED/GREEN implementation plan을 작성한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 사용자 written specification review/approval.
- implementation plan 작성·승인.
- TDD offline 구현과 root verification.
- corrective actual 별도 승인.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

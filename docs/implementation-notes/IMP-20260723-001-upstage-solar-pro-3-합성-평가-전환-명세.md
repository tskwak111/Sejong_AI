# IMP-20260723-001 — Upstage Solar Pro 3 합성 평가 전환 명세

- Date/Time (KST): 2026-07-23T13:52:29+09:00
- Task ID: LLM-002
- Type: decision-design
- Status: Decision-only / Review — written specification
- Author/Agent: 사용자 결정자, Codex 수석 아키텍트·보안/데이터 품질·문서 담당
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: c3fd2ee
- Related plan/ADR/RFP: ADR-0022, D-065, A-044, SFR-001, SER-001, LLM-002 design

## 1. 사용자 요청과 완료 기준

### 요청

PR #6 병합 완료를 알리고 Q-LLM-005=A를 확정했다. DeepSeek 대신 Upstage를 사용하되 먼저
합성 평가로 한국어 품질·JSON 안정성·비용을 확인하고, 실제 시민/free-input 연결 B는 필요할 때
별도 승인하도록 요청했다.

### Acceptance Criteria

- PR #6의 실제 병합 상태와 최신 원격 기준선을 확인한다.
- 기존 DeepSeek 결정을 지우지 않고 후속 결정으로 supersede한다.
- Upstage exact model, 입력 허용, 실제 시민 금지, retry/cap/fallback/source 경계를 명세한다.
- 한국어·JSON·비용 평가 집합과 통과 기준을 사람이 판단할 수 있게 고정한다.
- API/DB/data/dependency/product code를 변경하지 않는다.
- source-of-truth, ADR, 결정/모호성, 버전, TASKS, 구현 노트를 동기화한다.
- 사용자 명세 승인과 실행계획 승인 전 key 사용·network call·제품 구현을 하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 공급자·단계 경계를 확정했고 Codex가 저장소 권위와 외부 공식 자료를 대조해 설계했다. 후속 actual 한국어 판정은 PM이 담당한다. |
| When — 언제 | 2026-07-23 13:39~16:54 KST, PR #6 병합 직후 |
| Where — 어디서 | `origin/main` merge `c3fd2ee` 기반 격리 worktree와 활성 문서·ADR·버전·TASKS |
| What — 무엇을 | 미구현 DeepSeek 선택을 Upstage `solar-pro3` 합성 평가로 대체하고 actual 시민 경로와 분리 |
| Why — 왜 | 실제 모델을 바꾸기 전에 한국어 품질·strict JSON·비용과 공급자 실패 안전성을 작은 합성 범위에서 증명하기 위해 |
| How — 어떻게 | canonical T-01~T-10×최대 3회, max 30 attempts, schema gate, server source binding, deterministic fallback을 명세 |
| How much — 어느 정도 | 변경 29파일 모두 문서·추적·manifest; product code/API/DB/data/dependency/key/call 0, 계획 승인 뒤에도 actual run 상한 USD 0.05 |

## 3. 시작 전 상태

- 관련 파일: source-of-truth 4종, ADR-0005, prompt/security/test/risk 문서, TASKS,
  `versions/manifest.json`, MVP canonical 20문항/결과
- 기존 동작: local/private deterministic chat 19→20, sample 20/20, provider 호출 0
- 발견한 충돌/부채: 활성 문서가 `deepseek-v4-flash`를 exact 현재 공급자로 고정했지만
  `apps/api/src`에는 provider adapter가 없고 사용자는 Upstage로 전환했다.
- Git 상태: 원격 PR #6 MERGED, merge `c3fd2ee`; 최신 `origin/main`에서
  `codex/LLM-002-upstage-synthetic-evaluation` worktree 생성

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-005 | A / Blocker | Upstage를 합성 평가만 할지 시민 chat에 즉시 연결할지 | A 확정: 합성 평가 먼저, B는 별도 승인 | 개인정보, 제품 동작, 공급자 비용·계약 |
| D-LLM-002-01 | D / Internal | 합성 평가 집합과 반복 | 기존 SUCCESS `T-01`~`T-10` 각 최대 3회, 재시도 포함 run cap 30 | 테스트 재현성·비용 |
| D-LLM-002-02 | D / Internal | SDK 도입 여부 | 기존 `httpx` 직접 사용, 새 production dependency 0 | lockfile·공급망 불변 |
| D-LLM-002-03 | D / Internal | 비용 안전 상한 | 공개 가격 snapshot과 4096/1024 worst-case로 VAT 포함 USD 0.05/run | actual 실행 gate |

## 5. 설계 결정과 대안

### 선택

Upstage direct API exact `solar-pro3`를 local/private server-owned 합성 evaluator로만 사용한다.
기존 deterministic pipeline이 분류·검색·근거·출처를 소유하고 모델은 strict schema의 한국어
답변 구성 요소만 제안한다.

### 이유

실제 시민 동작·개인정보·공급자 장애를 바꾸지 않고 모델의 한국어와 JSON 품질, 토큰 비용을
작게 측정할 수 있다. provider가 실패해도 현재 MVP는 그대로 동작한다.

### 고려했지만 선택하지 않은 대안

- B: 마스킹한 실제 시민/free-input을 `/api/v1/chat`에서 Upstage로 전송 — 처리조건·공개 동작
  재승인 전이라 보류
- LLM이 분류·검색·출처 생성 — ACTIVE-only/server-bound source를 약화해 거절
- Upstage SDK — 기존 `httpx`로 충분하고 새 production dependency 승인도 없어 거절
- Codex Cloud actual — secret/local-only gate 위반이라 거절

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `docs/superpowers/specs/...upstage...design.md` | 평가 architecture·통과 기준·비용·롤백 | 후속 계획/구현의 단일 명세 |
| `docs/adr/0022-...md`, ADR-0005/README | provider selection successor와 역사 보존 | 결정 계보 |
| source-of-truth/architecture/prompt/security/test/risk docs | current provider 경계 동기화 | 상충 제거 |
| decision/ambiguity/TASKS | D-065, A-044, LLM-002 Review | 추적 |
| manifest/version/changelog | product 2.4.0, prompt selection 0.0.3, docs 2.13.0 | 설계 버전 |
| 이 note/INDEX | 6W1H·재현·인수인계 | AGENTS 완료 조건 |

### 데이터 흐름/상태 변화

fixture ID → server canonical load → masker → deterministic classify/retrieve/ground →
Upstage structured draft → strict validation → server source 결합 → text-free aggregate metrics.
제품/DB 상태 변화는 없다.

### 오류·빈 상태·롤백

disabled/missing config는 network 0으로 중단한다. timeout/429/empty/truncated/schema-invalid는
최대 1회 retry 뒤 deterministic fallback이다. rollback은 provider flag off와 local key 제거,
adapter/evaluator 변경 revert이며 시민 MVP는 영향을 받지 않는다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.3.1 | 2.4.0 | 공급자·평가 경계의 호환 가능한 설계 추가 |
| Application | 0.6.0-local-core-loop | 동일 | 제품 코드/동작 0 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | UI 0 |
| API | 3.1.0-draft | 동일 | 공개 계약 0 |
| DB schema | 0.4.0-local | 동일 | migration/row 0 |
| Official data | 0.1.0-initial.2 | 동일 | 공식 데이터 0 |
| Mock data | 0.0.0-not-populated | 동일 | mock 0 |
| Prompt set | 0.0.2-deepseek-v4-flash-selected | 0.0.3-upstage-solar-pro3-synthetic-selected | 구현 전 exact provider/model 선택 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | 테스트 코드는 계획 승인 뒤 |
| Docs | 2.12.2 | 2.13.0 | 명세·ADR·권위 동기화 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `git fetch origin --prune` + `gh pr view 6 ...` | PASS: MERGED | merge `c3fd2ee` | GitHub PR #6 |
| `python -B scripts/check_repository_docs.py` (변경 전) | PASS | repository documentation check passed | terminal |
| `python -B scripts/check_repository_docs.py` (최종) | PASS | 1 checker | terminal |
| `python -m json.tool versions/manifest.json` | PASS | valid JSON | terminal |
| `scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS | clean | terminal |
| `git diff --check` | PASS | whitespace error 0 | terminal |
| `python -B -m unittest scripts.tests.test_repository_docs scripts.tests.test_repository_scaffold -v` | PASS | 27 tests, 1 환경상 skip | terminal |

### 미실행 검증과 이유

- API/Web/DB/build/E2E: 제품 코드·계약·DB·data 변경이 없는 decision-only 문서 작업
- Upstage actual: 명세와 후속 실행계획 승인 전 key/network call 금지
- 한국어 PM 점수: evaluator 구현·offline 검증 뒤 actual 합성 run에서 사람 판정

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 실제 시민/free-input/PII 전송을 명시적으로 금지하고 canonical synthetic-only 유지
- Security: API key는 ignored local env만; Cloud/Git/browser/log 금지, raw provider body 저장 0
- Accessibility: UI 변경 0
- Performance/cost: concurrency 1, attempts 30, worst-case VAT 포함 USD 0.05/run 설계

## 10. 데이터와 출처 영향

- 공식 데이터: `.2` 19/3/10과 final ACTIVE 20 불변; model은 ACTIVE/OFFICIAL 최소 payload만 읽기
- mock/AI 생성: 실제 데이터 생성 0; 향후 model output은 평가 결과이며 공식 source가 아님
- schema/lineage: DB/OpenAPI/official lineage 불변
- verified date: Upstage API/model/pricing/privacy 공식 페이지 2026-07-23 확인

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Q-LLM-005=A는 합성 평가까지만 승인한다. 실제 시민/free-input 연결 B는 승인되지 않았다.
- 이 문서 검토 후 사용자가 `명세 승인`을 해야 실행계획을 작성한다.
- 그 계획까지 승인한 뒤에만 구현하며, actual run에는 사용자가 local Upstage key를 준비한다.
- 가격·개인정보 처리방침은 바뀔 수 있고 actual 계정의 계약/동의 상태는 별도다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- 내부 evaluator는 server-owned fixture ID만 받아 canonical question을 로드한다.
- exact temperature/timeouts/report schema는 실행계획과 TDD에서 고정할 수 있다.
- source/intent/status를 모델 schema에서 제외하고 서버가 결합한다.

## 13. 인수인계·재현·롤백

### 재현

1. `git fetch origin --prune`
2. PR #6 merge `c3fd2ee` 확인
3. branch `codex/LLM-002-upstage-synthetic-evaluation` checkout
4. 설계, ADR-0022, D-065/A-044, manifest diff 확인
5. repository docs checker와 diff/secret gate 실행

### 롤백

이 branch/commit을 revert하면 된다. 제품 코드/API/DB/data에는 rollback이 없다. 이미 확정된
실제 시민 external-provider 금지는 revert와 무관하게 유지한다.

### 다음 개발자 시작점

명세 승인 뒤 `superpowers:writing-plans`로 LLM-002 실행계획을 작성한다. 첫 구현은 provider-neutral
contract/config/cap tests이며 Upstage actual call은 offline 전체 검증 뒤 마지막 단계다.

## 14. 남은 위험·미해결 질문·다음 단계

- 현재 blocker는 기술이 아니라 written specification과 후속 plan의 인간 승인이다.
- Upstage exact API behavior/price/privacy는 구현 직전과 actual run 직전에 재확인한다.
- 합성 평가 실패 시 기준을 자동 완화하지 않고 provider disabled를 유지한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

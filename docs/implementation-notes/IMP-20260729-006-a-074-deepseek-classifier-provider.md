# IMP-20260729-006 — A-074 DeepSeek classifier provider

- Date/Time (KST): 2026-07-29T05:21:53+09:00
- Task ID: A-074-DEEPSEEK-CLASSIFIER-PROVIDER
- Type: implementation-provider-actual
- Status: In Progress
- Author/Agent: 사용자 결정자 / Codex root / task-scoped implementer·reviewer agents
- Branch: codex/a-074-deepseek-classifier-provider
- Base commit: 8d36e04
- Related plan/ADR/RFP: ADR-0028, D-122, A-074, SFR-002,
  `docs/superpowers/plans/2026-07-29-deepseek-classifier-provider.md`

## 1. 사용자 요청과 완료 기준

### 요청

먼저 A-073 final review fix wave를 root/Upstage actual 재실행 없이 닫고, 이어서
DeepSeek `deepseek-v4-flash`를 local/private 질문 분류 선택 공급자로 추가한다. Offline TDD,
새 A-074 통합 gate 정확히 1회, clean-source review와 DeepSeek actual 정확히 1회를 수행하고
commit·push·Draft PR까지 진행하되 자동 merge하지 않는다.

### Acceptance Criteria

- A-073 root `NOT VERIFIED/FAIL`, invocation/rerun 1/0 보존
- exact five-string/uppercase `NONE`과 server parser 권위 유지
- deterministic 11/DeepSeek outbound 9, privacy/policy outbound 0
- HTTP 2xx·parse·accepted·expected match 각 9
- 질문/body/invalid value/secret 보관 0, cost <= USD0.20
- 새 A-074 offline gate·actual invocation 각 1, rerun 0
- 새 dependency/API/DB/data/Web/public/remote 변경 0

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 결정자, root 통합 담당, task별 구현·검토 agents |
| When — 언제 | 2026-07-29 KST, A-073 D-121 종료 직후 |
| Where — 어디서 | isolated local worktree, `apps/api`, `scripts`, active docs |
| What — 무엇을 | selectable DeepSeek classifier, provider별 비용·usage, one-shot evidence |
| Why — 왜 | Upstage를 보존하면서 질문 분류 공급자 비교와 자연어 분류 품질을 검증하기 위해 |
| How — 어떻게 | ADR-0028, exact selector, shared parser, Subagent-Driven TDD, aggregate-only actual |
| How much — 어느 정도 | fixed20 중 11 provider-free/9 outbound, actual cap USD0.20, retry/rerun 0 |

## 3. 시작 전 상태

- 관련 파일: classifier port/parser/prompt, Upstage adapter/settings, local composition,
  process ledger, existing fixed20 runner
- 기존 동작: Upstage classifier-only composition, deterministic fail-closed, exact five-string
- 발견한 충돌/부채: cost ledger가 Upstage estimator에 고정, active docs가 Upstage-only,
  old runner/report/root wrapper 재사용 불가
- Git 상태: branch `codex/a-074-deepseek-classifier-provider`, formal baseline `50aab6e`

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-PROVIDER-001 | A | classifier 비교 공급자 | A / DeepSeek exact model | Architecture·security·cost |
| A-074 | A | provider/actual/retention 경계 | D-122로 Resolved | 전체 수직 흐름 |

## 5. 설계 결정과 대안

### 선택

Explicit `CLASSIFIER_PROVIDER=disabled|upstage|deepseek`, local app only DeepSeek composition,
shared exact parser와 provider별 cost estimator, 별도 A-074 runner/report/lease를 사용한다.

### 이유

공개 계약·DB·공식 데이터를 건드리지 않고 provider output을 신뢰하지 않으면서 Upstage
classifier와 final generator를 보존할 수 있다.

### 고려했지만 선택하지 않은 대안

- Upstage 삭제: 기존 검증 경로와 rollback을 잃어 기각
- provider 자동 cascade: 비용·감사·예측 가능성을 해쳐 기각
- DeepSeek output 직접 사용: source/grounding 권위를 깨므로 기각
- A-073 wrapper/report 재사용: one-shot 증거를 훼손하므로 금지

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/limits.py`, DeepSeek usage/cost | provider별 estimator와 보수 비용 | Upstage 단가 오계산 방지 |
| settings/transport/local composition | pending | explicit provider selection |
| one-shot scripts/reports | pending | immutable aggregate evidence |
| authority/version docs | D-122/A-074/ADR-0028와 docs 2.30.8 | 구현 권위 동기화 |

### 데이터 흐름/상태 변화

raw question → deterministic PII/policy/obvious route → redacted `SafeQuestion` → selected
classifier → exact server parser/catalog validation → existing grounding/fallback. DB schema와
official data state는 변하지 않는다.

### 오류·빈 상태·롤백

설정·timeout·HTTP·empty·JSON·wire·catalog·usage·cost 실패는 retry 없이 deterministic
fallback이다. 즉시 rollback은 `CLASSIFIER_PROVIDER=disabled`다.

## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.4-classifier-wire-diagnostics
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.3-explicit-route-matrix
- test_suite: 2.1.7-classifier-wire-correction
- documentation: 2.30.8

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | | | |
| Web | | | |
| API | | | |
| DB schema | | | |
| Official data | | | |
| Mock data | | | |
| Prompt set | | | |
| Test suite | | | |
| Docs | | | |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|

### 미실행 검증과 이유

## 9. 보안·개인정보·접근성·성능 영향

- Privacy:
- Security:
- Accessibility:
- Performance/cost:

## 10. 데이터와 출처 영향

- 공식 데이터:
- mock/AI 생성:
- schema/lineage:
- verified date:

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- ...

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- ...

## 13. 인수인계·재현·롤백

### 재현

### 롤백

### 다음 개발자 시작점

## 14. 남은 위험·미해결 질문·다음 단계

- ...

## 15. 자체 리뷰

- [ ] 요청 충족
- [ ] 테스트/검증
- [ ] source-of-truth/계약/버전 동기화
- [ ] 개인정보 원문 노출 없음
- [ ] 구현 노트 INDEX 갱신

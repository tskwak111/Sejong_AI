# IMP-20260723-002 — Upstage Solar Pro 3 합성 평가 실행계획

- Date/Time (KST): 2026-07-23T17:21:58+09:00
- Task ID: LLM-002
- Type: implementation-plan
- Status: Decision-only / Review — execution plan
- Author/Agent: 사용자(명세 승인), Codex(계획·추적 문서 작성 및 자체 검토)
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: b318375
- Related plan/ADR/RFP:
  - [실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인된 설계](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [ADR-0022](../adr/0022-upstage-solar-pro3-synthetic-evaluation.md)
  - [결정 D-065/D-066](../decisions/DECISION_LOG.md)
  - [TASKS LLM-002](../../TASKS.md)

## 1. 사용자 요청과 완료 기준

### 요청

사용자의 `명세승인`을 Upstage `solar-pro3` 합성 평가 명세 승인으로 기록하고, 실제 구현 전에
검토할 수 있는 TDD 실행계획을 작성한다.

### Acceptance Criteria

- D-066에 명세 승인과 금지 경계를 기록한다.
- 설계의 모든 요구를 파일·인터페이스·RED/GREEN 테스트·검증·커밋 단위로 분해한다.
- 입력/출력/재시도/동시성/attempt/비용·privacy·source 경계를 모호하지 않게 고정한다.
- product code, API key, provider network call, public API/DB/data/dependency를 변경하지 않는다.
- TASKS, ambiguity register, source-of-truth, version manifest, CHANGELOG와 INDEX를 동기화한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 명세를 승인하고 Codex가 실행계획·결정/추적 문서를 작성·검토했다. 후속 PM은 실제 10개 결과를 채점한다. |
| When — 언제 | 2026-07-23 17:21 KST 시작, 같은 작업 턴에 계획 발행·문서 검증·커밋 |
| Where — 어디서 | local Git worktree의 `docs/`, `TASKS.md`, `CHANGELOG.md`, `versions/manifest.json`; product runtime/DB/network 제외 |
| What — 무엇을 | LLM-002 written specification 승인 D-066과 8-task TDD 실행계획 |
| Why — 왜 | 실제 시민 연결 전에 한국어 품질·strict JSON·비용을 안전한 합성 질문으로 판정하기 위해 |
| How — 어떻게 | 기존 코드/계약 조사, Upstage/HTTPX 공식 계약 재확인, RED→GREEN→gate→commit 계획, placeholder/type/범위 자체 검토 |
| How much — 어느 정도 | 실행계획 8개 task, canonical T-01~T-10×최대 3, outbound attempt≤30, 예상 run≤USD 0.05; 이 요청의 code/key/call 0 |

## 3. 시작 전 상태

- 관련 파일: `AGENTS.md`, source-of-truth, ADR-0022, LLM-002 설계, `apps/api` chat/privacy/
  repository 구조, `apps/api/pyproject.toml`, `apps/api/uv.lock`, canonical CSV, scripts 검사기
- 기존 동작: deterministic local/private chat은 완료됐고 public `/api/v1/chat`은 외부 provider를
  호출하지 않는다. `httpx==0.28.1`은 이미 lock됐으며 `sejong_ai_api.llm` package는 없다.
- 발견한 충돌/부채:
  - 저장소 실제 구조는 일반 `config.py/models.py/privacy service`가 아니라 `local.py`,
    `db/models.py`, `contracts/chat.py`, `privacy/redaction.py`이므로 계획을 실제 경계에 맞췄다.
  - `apps/api/.env.example`의 과거 DeepSeek selection 값은 구현 Task 1에서만 정리한다.
  - 정확한 provider tokenizer 의존성이 없으므로 UTF-8 byte upper bound와 provider 실제
    `prompt_tokens` 이중 gate를 사용하며 새 dependency를 추가하지 않는다.
  - `pyproject.toml` version만 올리고 `uv.lock`을 그대로 두는 drift를 피하기 위해 내부 package
    version은 0.4.0을 유지한다.
- Git 상태: base `b318375`, branch `codex/LLM-002-upstage-synthetic-evaluation`; 계획 작업 전
  product diff 0, 계획 초안 1개만 untracked였다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-005 | 인간 결정 | DeepSeek 대신 Upstage로 먼저 합성 품질을 볼지 | A / D-065, 명세 D-066 승인 | provider/model·비용·privacy |
| PLAN-GATE | 인간 결정 | 실행계획대로 product code를 시작할지 | 현재 Review; 별도 `계획 승인, 구현 시작` 필요 | product code·local actual |
| INPUT-EST | AI 내부 | tokenizer dependency 없이 4096 입력 한계를 어떻게 닫을지 | canonical UTF-8 byte upper bound + provider usage 4096 이중 gate | transport 전 차단·실제 usage 초과 시 run stop |
| PACKAGE-VERSION | AI 내부 | dependency 불변인데 internal package version을 올릴지 | 0.4.0 유지, lockfile 불변 | manifest application/prompt/test/docs 축만 후속 승격 |

## 5. 설계 결정과 대안

### 선택

- local/private canonical allowlist evaluator를 public chat에서 완전히 격리한다.
- existing `httpx`의 explicit timeout, `AsyncHTTPTransport(retries=0)`, MockTransport를 사용한다.
- strict Pydantic output, server-bound source, deterministic template fallback, aggregate-only report를
  각각 독립 테스트한다.
- 실제 key와 network call은 offline 전체 gate와 별도 계획 승인 뒤 사용자 local TTY에서만 허용한다.

### 이유

현재 MVP의 가장 중요한 안전 원칙을 바꾸지 않고 모델 한국어 품질과 JSON 안정성을 측정할 수 있고,
실패해도 deterministic 시스템이 그대로 유지된다.

### 고려했지만 선택하지 않은 대안

- 실제 시민/free-input provider 연결: option B 별도 승인 전 금지.
- Cloud/GitHub Actions 실제 호출: secret·DB 경계 때문에 금지.
- 새 tokenizer/SDK dependency: 비용과 공급망 확대 없이 이중 input gate로 해결.
- HTTPX hidden retry: 총 attempt 비용을 불명확하게 하므로 0.
- provider가 source/status/intent를 생성: 서버 권위 침해이므로 strict schema에서 금지.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `docs/superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md` | 8-task TDD 계획, 인터페이스, 명령, 수용 gate, rollback | 구현자가 추가 결정을 만들지 않고 단계별 실행하도록 |
| `docs/decisions/DECISION_LOG.md` | D-066 명세 승인 | 인간 결정의 불변 추적 |
| `docs/11_AMBIGUITY_REGISTER.md` | A-044를 specification resolved / plan Review로 전환 | 남은 blocker를 정확히 표시 |
| `TASKS.md` | LLM-002 plan 링크와 Review 상태 | 작업 추적 |
| `TEAM_DECISIONS.md` | 명세 승인/plan Review 경계 | source-of-truth 동기화 |
| `CHANGELOG.md`, version docs/manifest | docs 2.13.1 | 문서 release 계보 |
| 이 구현 노트와 INDEX | 승인·계획·검증·인수인계 증거 | 요청별 기록 의무 |

### 데이터 흐름/상태 변화

이 요청에서는 runtime 데이터 흐름 변화가 없다. 후속 계획은
canonical fixture→redact→classify→ACTIVE/OFFICIAL retrieve→ground→provider→strict validate→
server template/source→aggregate report 순서를 고정하며 질문/답변 text는 tracked report에 없다.

### 오류·빈 상태·롤백

후속 구현은 invalid/disabled 설정, input overflow, timeout/transport/HTTP/schema/cap failure를
value-free outcome code로 닫는다. 이 요청의 문서 변경은 단일 docs commit revert로 복구한다.

## 7. 버전 전후

### 생성 시 매니페스트

- product_spec: 2.4.0
- repo_guidance: 1.7.6
- application: 0.6.0-local-core-loop
- web: 0.4.0-chat-admin-local-integration
- api: 3.1.0-draft
- shared_contracts: 0.4.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.0.3-upstage-solar-pro3-synthetic-selected
- test_suite: 1.2.1-core-loop-closeout
- documentation: 2.13.0

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | product code 0 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | UI/contract 0 |
| API | 3.1.0-draft | 동일 | public route/contract 0 |
| DB schema | 0.4.0-local | 동일 | migration 0 |
| Official data | 0.1.0-initial.2 | 동일 | record/lineage 0 |
| Mock data | 0.0.0-not-populated | 동일 | mock 0 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | prompt는 아직 미구현 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | test code 0 |
| Docs | 2.13.0 | 2.13.1 | 승인 결정·실행계획·구현 노트 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `python scripts/new_implementation_note.py ...` | PASS, IMP-20260723-002 및 INDEX row 생성 | 1 note | 현재 파일/INDEX |
| `python -B scripts/check_git_history_secrets.py --help` | PASS; correct flag가 `--repo`임을 확인 | exit 0 | 계획 Task 7 |
| 실행계획 대상 placeholder/type/scope `rg` scan | PASS; 구현 placeholder 0, self-review 설명의 `Placeholder scan` 문구만 1 | 1 plan | 실행계획 self-review |
| `python -B scripts/check_repository_docs.py` | PASS, `repository documentation check passed` | exit 0 | terminal evidence |
| `scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS, match 0 | exit 0 | terminal evidence |
| `python -B scripts/check_git_history_secrets.py --repo .` | PASS, reachable history match 0 | exit 0 | terminal evidence |
| `git diff --exit-code -- apps/api contracts database supabase data pnpm-lock.yaml` | PASS, protected product/contract/DB/data/dependency diff 0 | exit 0 | terminal evidence |
| `git diff --check` | PASS, whitespace error 0 | exit 0 | terminal evidence |

### 미실행 검증과 이유

API/Web/DB/test/build/provider actual은 실행하지 않았다. 이 요청은 명세 승인 기록과 실행계획만
허용하며 계획 승인 전 product code/key/network call이 금지돼 있다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·PII·답변·key·DSN을 읽거나 쓰거나 전송하지 않았다. 후속 계획은 canonical
  synthetic-only, pre-provider redaction, text-free report를 강제한다.
- Security: secret 값 0, network call 0, dependency/lockfile 0. provider는 disabled 기본이다.
- Accessibility: 시민/관리자 UI 변화 0.
- Performance/cost: 실제 호출과 비용 0. 후속 run은 concurrency 1, outbound attempt 30,
  input/output 4096/1024, VAT 포함 USD 0.05 cap이다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable official `.2`와 local DB 모두 변경하지 않았다.
- mock/AI 생성: 새 mock/AI answer 0. 계획 예제는 test-only sentinel이다.
- schema/lineage: API/DB/data schema와 lineage 불변.
- verified date: 2026-07-23. Upstage model/base/pricing/privacy mutable facts는 실제 call 직전 공식
  문서에서 다시 확인하도록 Task 7에 강제했다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 명세는 승인됐지만 **실행계획은 아직 Review**다. product code는 별도
  `계획 승인, 구현 시작` 뒤에만 시작한다.
- 구현 뒤 실제 key는 사용자가 ignored local `.env`에만 입력하고, actual review는 local TTY에서
  PM이 수행한다.
- actual 시민/free-input/public/remote provider option B는 승인되지 않았다.
- 실제 합성 평가가 PASS해도 B는 자동 승인되지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- package/file split, dataclass/helper 이름, test fixture, formatting은 승인된 계약 안에서 자율 처리한다.
- 각 task는 RED→minimal GREEN→focused gate→diff review→small commit 순서다.
- shared migration/contract/data/generated type은 계획 범위에 없으며 변경 시 즉시 중단한다.

## 13. 인수인계·재현·롤백

### 재현

1. branch `codex/LLM-002-upstage-synthetic-evaluation`과 base `b318375`를 확인한다.
2. ADR-0022, 승인된 설계, D-065/D-066, 실행계획 순서로 읽는다.
3. `python -B scripts/check_repository_docs.py`와 `git diff --check`를 실행한다.
4. 계획 승인 전 `apps/api/src`, `.env`, provider network를 변경/사용하지 않는다.

### 롤백

이 노트를 추가한 문서 전용 커밋의 실제 SHA를 `git log`로 확인한 뒤 그 SHA를 `git revert`의
인자로 사용한다. product/API/DB/data migration이나 복구는 필요 없다.

### 다음 개발자 시작점

사용자가 실행계획을 승인하면 Task 1의 settings RED test부터 시작한다. 계획 상단의 global
constraints와 Task 7 human-only actual gate를 먼저 다시 읽고, one task/one commit을 유지한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 계획 승인 전 구현은 Pending이다.
- Upstage model/base/pricing/privacy는 mutable하므로 실제 call 직전 재확인이 필요하다.
- local API key 입력과 PM 10-result 채점은 인간 작업이다.
- provider tokenizer와 같은 새 dependency는 승인되지 않았으며 현재 이중 input gate를 유지한다.
- 이후 B, public/remote, 비용/attempt 확대는 별도 인간 결정이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증 — docs/current+history secret/protected diff/whitespace gate PASS
- [x] source-of-truth/계약/버전 동기화 — 공개 계약은 불변
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

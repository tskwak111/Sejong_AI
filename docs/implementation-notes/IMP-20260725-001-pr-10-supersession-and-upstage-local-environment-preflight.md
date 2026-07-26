# IMP-20260725-001 — PR #10 supersession and Upstage local environment preflight

- Date/Time (KST): 2026-07-25T13:13:51+09:00
- Task ID: OPS-PR10-UPSTAGE-PREFLIGHT-001
- Type: decision-operations
- Status: Done — PR #10 closed; actual evaluation FAIL recorded; option B not approved
- Author/Agent: 사용자(owner·local secret 입력) / Codex(PR·환경 안전 점검)
- Branch: `codex/OPS-PR10-UPSTAGE-PREFLIGHT-001`
- Base commit: `257c35f44567877f46f6bc4776062ca98888b98b`
- Related:
  [POST-MVP-001 plan](../superpowers/plans/2026-07-24-post-mvp-main-stabilization.md),
  [LLM-002 plan](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md),
  D-070, ADR-0022

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 owner PR #11 병합을 알리고, 동일 변경을 담은 팀원 PR #10의 처리 방법을 물었다.
또한 ignored local `.env`에서 `LLM_MODEL=solar-pro3`와 `LLM_API_KEY`를 설정했으므로 실제
Upstage 합성 평가 전에 나머지 fail-closed 설정을 확인해 달라고 요청했다.

### Acceptance Criteria

- GitHub 실제 상태로 #11 merged와 #10 open·중복 여부를 확인한다.
- #10은 병합하지 않고 #11에 의해 대체됐다는 설명과 함께 닫도록 안내한다.
- API key 또는 기존 provider 값은 출력하지 않고 key 존재 여부와 exact profile만 확인한다.
- 부족한 비밀 외 설정 key 이름과 승인된 exact 값만 안내한다.
- 제품 코드·계약·DB·공식 데이터·public/remote 동작을 변경하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 PR #11을 병합하고 local key를 입력했으며 Codex가 GitHub·환경 상태를 검사 |
| When — 언제 | 2026-07-25 KST, PR #11 병합 직후 |
| Where — 어디서 | private `tskwak111/Sejong_AI`, ignored primary-root `apps/api/.env`, 격리 docs worktree |
| What — 무엇을 | PR #10 superseded 처리와 Upstage Task 7 exact-profile 사전점검 |
| Why — 왜 | 동일 코드를 다시 병합하지 않고 provider 호출 전 fail-closed 안전 조건을 충족하기 위해 |
| How — 어떻게 | GitHub PR metadata/diff 비교, 값 비출력 allowlist 검사, production loader 결과 확인 |
| How much — 어느 정도 | PR 2개·비밀 외 설정 10개 검사; actual outbound 30회; local login password 1회 안전 회전; aggregate report 1개+상태 문서 동기화 |

## 3. 시작 전 상태

- 관련 파일: `apps/api/.env`(ignored/read-only), `apps/api/src/sejong_ai_api/llm/settings.py`,
  POST-MVP/LLM-002 계획, 본 노트와 INDEX.
- 기존 동작: fail-closed loader는 11개 allowlisted 값이 모두 exact일 때만 actual 평가 설정을
  반환한다.
- 발견한 충돌/부채: PR #10은 #11에 이미 포함된 동일 설정 한 줄을 다시 제안해
  `mergeable=false`였고 사용자가 미병합 Close했다. local `.env`는 사용자 보정 후 key 존재,
  비밀 외 exact 값 10/10과 provider loader PASS다. 최초 actual runner는 provider 호출 전에
  `LLM_EVALUATION_CONFIGURATION_INVALID`로 종료됐다. 원인은 오래된 `DATABASE_URL`과
  32-byte 미만 `CONTEXT_TOKEN_SECRET`이었고, provider key/model은 원인이 아니었다.
- local 운영 부채: patched Supabase/PostgreSQL 17의 `postgres`는 superuser가 아니므로,
  기존 provisioning script가 재실행 때 슈퍼유저 전용 role 속성을 변경하다 `42501`로
  실패한다. 이번 local-only 복구는 컨테이너의 `supabase_admin` credential을 프로세스
  메모리에서만 사용해 동일 role rotation을 수행했다.
- Git: 최신 `origin/main=257c35f`에서 별도 docs worktree를 생성했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| OPS-PR10 | 운영 | 중복 PR 처리 | #10을 병합하지 않고 #11 superseded 사유로 Close 완료 | 이중 병합·불필요 conflict 방지 |
| OPS-UPSTAGE | 보안 | actual provider readiness | exact 10/10·loader PASS 뒤 1회 interactive 실행 | key 유출·오설정·비승인 호출 방지 |
| OPS-LOCAL-LOGIN | 운영 | 기존 local login 재프로비저닝 | `supabase_admin` 메모리 전용 local repair 후 설정·readiness 재검사 | PostgreSQL 17 privilege mismatch 우회 |

## 5. 설계 결정과 대안

### 선택

PR #10에는 #11에서 owner 검토·테스트와 함께 통합된 `allowedDevOrigins` 변경만 있으므로
`Superseded by #11` 코멘트를 남기고 **Close pull request**한다. `.env`는 기존 파일에서 아래
네 설정만 exact 값으로 보정한 뒤 loader를 재검사한다.

- `LLM_PROVIDER=upstage`
- `LLM_BASE_URL=https://api.upstage.ai/v1`
- `LLM_MAX_INPUT_TOKENS=4096`
- `UPSTAGE_SYNTHETIC_EVALUATION_MODE=true`

### 이유

PR #11은 merged이며 #10의 한 줄을 포함할 뿐 아니라 회귀·E2E·문서·소유 경계까지 검증했다.
중복 PR 병합은 가치가 없고 충돌만 만든다. actual LLM 호출은 exact profile 외에는 loader가
`None`을 반환하도록 설계됐으므로 네 값 보정 전 실행하지 않는 것이 승인된 정책이다.

### 고려했지만 선택하지 않은 대안

- PR #10도 병합: 동일 설정의 중복이며 현재 main과 충돌하므로 기각.
- PR #10 삭제: GitHub PR은 삭제 대신 감사 이력을 보존하는 Close가 적절해 기각.
- loader를 느슨하게 변경: 승인된 보안 계약과 actual 호출 제한을 깨므로 기각.
- 현재 key 종류를 추정하거나 출력: 비밀관리 원칙 위반이므로 기각.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| GitHub PR #10 | 변경 없음; 사용자에게 superseded close 절차 권고 | 외부 write는 명시 요청 전 수행하지 않음 |
| ignored `apps/api/.env` | read-only 상태 검사, 값 출력 0 | 인간 소유 local secret 보존 |
| local DB `sejong_local_login` | password 회전 및 `sejong_backend` capability 유지 | stale local DSN 복구 |
| `docs/test-reports/LLM-002-UPSTAGE-SYNTHETIC-EVALUATION.md` | text-free actual aggregate·비용·판정 | 재현 가능한 FAIL 증거 |
| decision log/source-of-truth/TASKS/ambiguity/CHANGELOG/manifest | D-071 actual FAIL과 option B 미승인 동기화 | 서로 다른 상태 설명 방지 |
| 본 구현 노트·INDEX | 결정·검사·다음 단계 기록 | 저장소 의무와 재현성 |

### 데이터 흐름/상태 변화

실제 시민 질문/API/Web/official KB 상태 변화는 없다. local DB에서는
`sejong_local_login` password만 회전했고 ignored `.env`의 `DATABASE_URL`을 원자적으로
동기화했다. schema와 ACTIVE data는 변경하지 않았다. provider actual은 승인된 canonical
synthetic fixture에만 outbound 30회를 사용했다.

### 오류·빈 상태·롤백

최초 runner는 configuration 단계에서 종료돼 outbound call·artifact가 모두 0이었다.
복구 후 local/provider settings와 DB readiness가 모두 `True`였다. runner는 이 readiness를
다시 확인한 뒤 승인된 합성 호출을 수행했다. 결과는 strict-schema 27/30으로 overall FAIL이며
provider 시민 option B는 승인되지 않았다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.4.1 | unchanged | 제품 범위 불변 |
| Repo guidance | 1.7.8 | unchanged | 협업 정책 불변 |
| Application | 0.8.1-main-stabilization | unchanged | 제품 동작 변경 0 |
| Web | 0.5.1-local-dev-origin | unchanged | #10 변경은 #11에 이미 병합 |
| API | 3.1.0-draft | unchanged | provider 시민 경로 활성화 0 |
| Shared contracts | 0.4.0 | unchanged | 공개 계약 불변 |
| DB schema | 0.4.0-local | unchanged | migration 0 |
| Official data | 0.1.0-initial.2 | unchanged | seed/data 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 0 |
| Prompt set | 0.1.0-upstage-solar-pro3-synthetic | unchanged | synthetic-only 유지 |
| Test suite | 1.5.1-local-dev-origin | unchanged | 테스트 코드 변경 0 |
| Docs | 2.17.0 | 2.18.0 | actual aggregate report와 권위 상태 동기화 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| GitHub PR #10/#11 metadata·diff fetch | PASS | #10 closed/not merged/1 file; #11 merged at `257c35f` | GitHub API |
| allowlisted `.env` status probe | PASS | key present; exact 10/10; duplicate 0; 값 출력 0 | local stdout |
| production settings loader probe | PASS | `fail_closed_loader_ready=True` | local stdout |
| exact local key Git history scan | PASS | current/history match 0; key 값 출력 0 | `scripts/check_git_history_secrets.py` |
| `python -B scripts/check_repository_docs.py` | PASS | baseline | local stdout |
| tracked secret patterns / `git diff --check` | PASS | match 0 / whitespace error 0 | local stdout |
| official mutable facts | PASS | `solar-pro3`, v1 endpoint, 0.15/0.015/0.60 USD/M, VAT 별도 | Upstage official pages |
| local runtime/DB | PASS | uv 0.11.28, Python 3.12.13, loopback DB healthy | local stdout |
| initial interactive runner | EXPECTED FAIL | `CONFIGURATION_INVALID`; provider call/token/cost/artifact 0 | local process |
| failure isolation | PASS | provider settings true; local settings false; invalid DB identity+short context secret | boolean-only probe |
| official `postgres` DSN connect | PASS | identity match; secret 출력 0 | local process-only status parse |
| standard login reprovision | KNOWN FAIL | PostgreSQL `42501`, existing role attributes require superuser | bounded diagnostic |
| local superuser repair | PASS | login password rotation; credential process-only; schema/data unchanged | bounded local operation |
| repaired local preflight | PASS | local settings/provider settings/DB readiness all true | boolean-only probe |
| interactive actual runner | COMPLETE / FAIL | outbound 30, schema valid 27/30, completed 29, fallback 2 | ignored aggregate |
| human PM review | PASS (limited) | valid result 9개, mean 4.8444, min 4, `OK=9`, critical 0 | ignored aggregate |
| cost | PASS | input 11,679, output 4,133, cached 0; VAT 포함 USD 0.004654815/0.05 | ignored aggregate |
| aggregate reconciliation | PASS | attempt total 30, generation outcome total 29, Decimal VAT cost exact, overall/schema false exact | local read-only probe |
| focused docs/secret/history/diff | PASS | docs link, tracked secret, exact key current/history 0, JSON, whitespace | local stdout |
| repository-wide offline gate | PASS | provider disabled; root/data/seed/Web/API/contracts/secret/bundle/package/diff; `verification=complete` | clean primary at same base SHA |
| protected product diff | PASS | API/Web/contracts/DB/migrations/data/dependencies diff 0 | worktree diff review |
| owner evidence commit | PASS | `docs(llm): record Upstage synthetic evaluation`; actual artifact·secret 제외 | current branch |

### 미실행 검증과 이유

- actual 재실행: 결과를 좋게 만들기 위한 반복을 금지한 승인 계획에 따라 미실행.
- public/remote/citizen provider: option B 미승인·scope 금지로 미실행.
- API/Web/DB regression: 제품 코드·계약·DB·데이터 변경이 없는 운영 결정 문서다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·응답·PII 접근 0. `.env`, DSN, role password, key 본문 출력 0.
- Security: key 존재 여부만 확인하고 exact loader가 계속 fail-closed임을 확인했다.
- Accessibility: UI 변경 0.
- Performance/cost: outbound attempt 30, input 11,679, output 4,133, cached 0,
  VAT 포함 USD 0.004654815로 cap은 통과했다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`와 ACTIVE 20 불변.
- mock/AI 생성: 승인된 canonical synthetic fixture만 actual 생성했으며 실제 시민 입력은 0.
- schema/lineage: DB/API/contract lineage 불변.
- verified date: GitHub PR 상태와 local profile은 2026-07-25 KST 확인.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- PR #10은 병합하지 않는다. #11에 대체됐다는 코멘트를 남기고 Close한다.
- `.env`의 네 비밀 외 설정을 exact 값으로 보정해야 한다. key는 채팅·GitHub·명령 인자로
  보내지 않는다.
- actual Task 7은 overall FAIL이다. JSON schema 100%가 아니므로 높은 인간 점수와 낮은
  비용만으로 실제 시민 option B를 승인할 수 없다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- mismatch 검사는 key 이름만 출력하고 actual/current value는 출력하지 않았다.
- PR #10의 변경 한 줄은 #11의 owner branch 설정과 의미가 동일하며 #11에는 추가 회귀 증거가
  포함됐다.

## 13. 인수인계·재현·롤백

### 재현

```powershell
$env:PYTHONPATH = (Resolve-Path "apps/api/src").Path
python -B -c "from pathlib import Path; from sejong_ai_api.llm.settings import load_upstage_synthetic_settings; print(load_upstage_synthetic_settings(environ={}, env_path=Path('apps/api/.env')) is not None)"
```

### 롤백

PR #10은 미병합 Close 상태라 코드 롤백이 없다. ignored `.env` 변경은 사용자가 기존 local
backup으로 되돌리거나 provider를 `disabled`, evaluation mode를 `false`로 복원한다.

### 다음 개발자 시작점

tracked aggregate report와 source-of-truth 상태를 검토하고 provider-disabled final offline
gate 결과를 확인한다. actual artifact는 ignored local 증거로만 보존한다.

## 14. 남은 위험·미해결 질문·다음 단계

- PR #10은 closed/not merged로 확인했다.
- `.env` exact profile과 repaired ephemeral-secret/DB preflight는 통과했다. actual은
  strict-schema 27/30으로 FAIL했고 option B는 미승인이다.
- key가 Upstage 키인지 값 자체로 판별하지 않았으며 사용자가 공급자 콘솔에서 확인해야 한다.
- `provision_local_database_login.py`의 PostgreSQL 17 existing-role 재실행 호환성은 별도
  code fix와 회귀 테스트가 필요한 운영 부채다. actual 합성 평가를 반복 실행할 이유는 아니다.
- ignored key는 사용자가 local `.env`에 둔 현재 상태를 Codex가 삭제하지 않았다. 필요가
  끝났다면 사용자가 공급자 콘솔에서 회전/폐기하고 local 파일에서 제거할 수 있다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

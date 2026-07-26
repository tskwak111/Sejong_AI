# IMP-20260726-004 — LLM-003 actual 최종 리뷰와 Draft PR 게시

- Date/Time (KST): 2026-07-26T13:17:06+09:00
- Task ID: LLM-003-PUBLISH
- Type: git-review-handoff
- Status: Done — Draft PR / merge hold
- Author/Agent: 사용자(owner), Codex(main), 독립 review agent
- Branch: `codex/LLM-003-local-actual-evidence`
- Base commit: `c575809150bb55bd52d2bf0aeab8fe3cd861f2e1`
- Publication commits: `4de364d`, `d3a8918`
- Draft PR: https://github.com/tskwak111/Sejong_AI/pull/13
- Related plan/ADR/RFP: D-072~D-075, A-048~A-049, ADR-0023, LLM-003 plan/report

## 1. 사용자 요청과 완료 기준

### 요청

LLM-003 local actual 변경을 최종 독립 리뷰하고, 필요한 보완과 검증을 마친 뒤 commit·push하고
private `Sejong_AI/main` 대상 Draft PR을 만든다. 자동 merge는 하지 않는다.

### Acceptance Criteria

- 최신 `origin/main` 포함과 의도한 branch/diff만 확인한다.
- Critical/Important 코드·보안·데이터 품질 문제를 해결한다.
- 집중 테스트 후 fresh full offline repository gate를 통과한다.
- secret·문서·diff 검사를 통과하고 실제 커밋·푸시·Draft PR URL을 남긴다.
- actual provider 재호출, remote/public, DB 삭제, 자동 merge를 수행하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자(owner)가 게시를 승인했고 main Codex가 통합·Git 게시, 독립 agent가 read-only 최종 리뷰 |
| When — 언제 | 2026-07-26 KST, local actual 종료 후 Draft PR 게시 시점 |
| Where — 어디서 | Windows local isolated worktree, private `tskwak111/Sejong_AI`, PR #13 |
| What — 무엇을 | actual runner/evidence, usage 경계, DB role drift guard, source-of-truth·report·runbook을 검토·보완·게시 |
| Why — 왜 | 실제 AI 증거의 비용·개인정보·공식 근거 주장과 재현 절차를 과장 없이 review 가능한 상태로 고정 |
| How — 어떻게 | 독립 review → focused fix/test → fresh offline controller → staged review → 2 commits → push → Draft PR |
| How much — 어느 정도 | 첫 게시 commit 32 files, +2,132/-118; follow-up test +31/-7; actual provider calls 0 |

## 3. 시작 전 상태

- 관련 파일: LLM contracts/adapter/tests, actual runner, local DB provisioner/tests, LLM-003
  ADR/plan/report/runbook/source-of-truth/version/implementation notes.
- 기존 동작: PR #12는 `main`에 병합됐고 local actual은 PASS했으나 working tree가 아직 미게시였다.
- 발견한 충돌/부채:
  - historical aggregate의 usage completeness와 forced-timeout consumption은 future harness 수준의
    검증이 아니었다.
  - evaluation metadata 22행이 `is_test=false`로 오표시됐다.
  - corrective second 10-call run은 별도 재승인 없이 실행돼 A-049 governance incident가 됐다.
  - provisioner가 exact role/membership drift를 모두 막지 못했다.
- Git 상태: `origin/main=f5c3a1d`, branch base `c575809`; `origin/main`은 branch ancestor였다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-049 | B / High | corrective 10-call rerun의 사후 확인 | PR merge hold; 추가 호출 0 | Git merge·외부 비용 governance |
| DB-CLEANUP | Human gate | 오표시 metadata 22행 처리 | 현 PR은 미삭제; KPI 제외 | local DB data 삭제·증거 |
| PUBLIC/REMOTE | Blocked scope | 공개·remote actual/배포 | 계속 금지 | 개인정보·비용·배포 |

## 5. 설계 결정과 대안

### 선택

- historical 수치를 immutable evidence로 유지하되 token/cost는 lower bound라고 명시했다.
- current runner만 usage 10/10, timeout injection consumption, `is_test=true`, forbidden-value
  pre-write 차단을 강제했다.
- provisioner는 login/capability catalog state와 양방향 exact membership allowlist를 commit 전
  검증한다.
- PR 본문 최상위에 A-049 merge hold와 22행 cleanup gate를 공개했다.

### 이유

과거 증거를 새 harness가 생성한 것처럼 소급 주장하지 않고, 다음 실행부터의 fail-closed 안전성과
현재 evidence의 한계를 동시에 재현 가능하게 남기기 위해서다.

### 고려했지만 선택하지 않은 대안

- actual provider 재실행: 새 인간 승인과 비용이 필요하므로 실행하지 않았다.
- 22행 targeted delete: 고유 marker가 없어 안전한 범위를 증명할 수 없고 DB 삭제 승인도 없다.
- public/remote 검증 또는 자동 merge: 승인 범위 밖이다.
- worktree 도구를 tracked 파일로 추가: `.tools`는 의도적으로 ignored인 local runtime이다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/run_upstage_grounded_chat_actual.py` | complete usage, timeout consumption, evaluation label, forbidden-value pre-write guard | future actual evidence fail-closed |
| `llm/upstage_chat.py`, contracts/tests | content-free usage 전달과 input/output bound | 비용 증거 보존 |
| `scripts/provision_local_database_login.py` | role flags/settings, direct/inbound/capability exact memberships | privilege drift 차단 |
| `scripts/tests/test_supabase_tooling.py` | unsafe state와 extra member 회귀 | commit/env write 전 실패 증명 |
| LLM-003 plan/report/runbook/source-of-truth | historical lower bound, A-049, 22행, full gate 결과 | 과장 없는 계보 |
| PR #13 | Draft, A-049 merge hold, 검증·범위 밖 명시 | 인간 review 경계 |

### 데이터 흐름/상태 변화

이 게시 작업의 provider outbound와 DB write/delete는 0이다. 과거 actual의 metadata-only 22행은
변경하지 않고 KPI/EVENT 근거에서 제외한다. `.tools` 복제는 tracked data가 아닌 local ignored
runtime 준비이며 tracked diff에 포함되지 않는다.

### 오류·빈 상태·롤백

첫 full controller는 worktree에 pinned patched Supabase binary가 없어 `TEST-ROOT`에서 실패했다.
원본 local binary SHA-256을 tracked runtime manifest와 대조한 뒤 ignored worktree 경로에만
복제했고, 실패 2건을 focused PASS한 후 full controller를 재실행했다. branch rollback은 PR을
닫고 remote branch를 보존하거나, 인간 승인 후 게시 commit을 revert한다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.9.0-grounded-local-chat | 0.9.1-grounded-local-chat-evidence | local actual evidence |
| Web | 0.6.0-answer-mode | unchanged | UI 변경 없음 |
| API | 3.2.0-draft | unchanged | 공개 wire 변경 없음 |
| DB schema | 0.4.0-local | unchanged | migration 없음 |
| Official data | 0.1.0-initial.2 | unchanged | release 불변 |
| Mock data | 0.0.0-not-populated | unchanged | mock 미사용 |
| Prompt set | 0.2.0-grounded-live-chat | unchanged | prompt 불변 |
| Test suite | 1.6.0-grounded-live-chat | 1.6.1-grounded-actual | actual/provision 회귀 |
| Docs | 2.20.0 | 2.20.1 | actual·publication evidence |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 |
|---|---|---|
| actual runner unit | PASS | 10 |
| local DB provision focused | PASS | 11, deselected 54, subtests 14 |
| LLM contract/adapter | PASS | 40 |
| review follow-up usage boundary | PASS | 35 |
| Ruff lint/format | PASS | changed API tests와 새 scripts |
| mypy strict | PASS | 4 source files |
| first full `verify.ps1 -Offline` | FAIL, 원인 확인 | ignored patched runtime 부재, provider/DB actual 0 |
| failed runtime artifact focused | PASS after manifest-hash restoration | 2 |
| fresh full `verify.ps1 -Offline` | PASS | 모든 step, 749.9s, provider actual 0 |
| repository docs / secret / diff | PASS | 게시 직전 및 문서 동기화 후 |
| Git push / Draft PR | PASS | PR #13, Draft |

### 미실행 검증과 이유

Upstage actual 재실행, remote DB, public deploy, 실제 기관 계정, Cloud/CI actual은 새 승인 또는
범위 밖이므로 실행하지 않았다. follow-up은 test assertion만 변경했으므로 35개 focused test와
Ruff/docs/secret/diff를 재실행했으며 production code 변경 뒤의 fresh full gate는 이미 PASS했다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 새 question/answer/provider body/PII 저장·출력 0. historical 22행은 content-free지만
  `is_test=false`이므로 KPI 제외.
- Security: secret scan PASS, ignored key/DSN 미출력·미커밋, privilege membership drift 차단.
- Accessibility: Web/UI 변경 없음.
- Performance/cost: 이 게시 작업 provider cost 0. historical reported cost는 lower bound
  USD 0.001319835(최종 10 calls), 두 run 합계 lower bound USD 0.002635710이다. configured upper는
  각각 USD 0.0135168과 USD 0.0270336이다.

## 10. 데이터와 출처 영향

- 공식 데이터: approved immutable `.2`, local ACTIVE 20을 변경하지 않았다.
- mock/AI 생성: 이 게시 작업 신규 생성 0; historical GENERATED 4/TEMPLATE 6만 기록.
- schema/lineage: schema/migration/official/mock data 변경 0; 22행 cleanup은 Pending.
- verified date: 2026-07-26 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- A-049: PR #13 merge 전에 별도 승인 없이 실행된 corrective 10-call incident를 사후 확인하거나
  후속 조치를 지시해야 한다.
- 오표시 metadata 22행은 KPI/EVENT 증거에서 제외한다. reset/delete는 별도 DB-data 승인 대상이다.
- PR #13은 Draft이며 Codex는 merge·auto-merge하지 않았다.
- 추가 actual provider 호출은 매번 새 인간 승인이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- aggregate-only `_DiscardOutput`, frozen `TokenUsage`, test fixture와 exact role catalog query.
- helper·test assertion·import ordering·formatting은 공개 계약을 바꾸지 않는다.

## 13. 인수인계·재현·롤백

### 재현

1. PR #13 Files/Commits에서 `4de364d`, `d3a8918`과 이 후속 note commit을 확인한다.
2. ignored pinned runtime을 tracked manifest SHA-256으로 준비한다.
3. provider mode/key를 disabled/unset으로 유지한다.
4. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Offline`을 실행한다.
5. docs/secret/diff 검사와 `gh pr view 13`의 Draft 상태를 확인한다.

### 롤백

merge 전에는 PR #13을 닫고 branch를 보존하면 `main` 영향이 0이다. merge 후에는 actual evidence
게시 commit을 revert하고 provider mode를 disabled로 유지한다. local DB 22행은 별도 승인 없이
삭제하지 않는다.

### 다음 개발자 시작점

`docs/test-reports/LLM-003-GROUNDED-LIVE-CHAT.md`, A-049, PR #13 본문을 먼저 읽고, 인간 확인 전
merge 또는 actual provider 재호출을 하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- A-049 인간 acknowledgement가 PR merge gate다.
- 22행 cleanup/reset 선택과 실행은 별도 인간 승인 Pending이다.
- public/remote/실제 기관 운영 readiness는 계속 미승인이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

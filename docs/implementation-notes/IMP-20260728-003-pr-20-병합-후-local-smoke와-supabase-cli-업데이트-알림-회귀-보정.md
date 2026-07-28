# IMP-20260728-003 — PR 20 병합 후 local smoke와 Supabase CLI 업데이트 알림 회귀 보정

- Date/Time (KST): 2026-07-28T16:40:24+09:00
- Task ID: LOCAL-SMOKE-CLI-UPDATE-001
- Type: bugfix-testing-handoff
- Status: Done
- Author/Agent: 사용자 결정자 / Codex 구현·검증
- Branch: `codex/LOCAL-SMOKE-CLI-UPDATE-001`
- Base commit: `028053d` (PR #20 병합 후 `origin/main`)
- Related plan/ADR/RFP: `docs/superpowers/plans/2026-07-27-bounded-active-topic-hybrid-rag.md`,
  ADR-0027, DB-001 patched Supabase runtime

## 1. 사용자 요청과 완료 기준

### 요청

PR #20 병합 이후 현재 시스템 개발을 즉시 계속하고, AI가 수행 가능한 local/private 검증과
후속 보정을 멈추지 않고 진행한다.

### Acceptance Criteria

- 최신 `origin/main`에서 provider 호출 없이 API/Hybrid RAG/Web 집중 gate를 재실행한다.
- 실제 Docker local DB에서 `/ready=200`, 시민 API와 관리자 조회 transport를 확인한다.
- Web production build와 390/430/desktop 브라우저 회귀를 확인한다.
- 발견된 재현 가능한 도구 회귀는 TDD로 최소 수정하고 arbitrary stderr fail-closed를 유지한다.
- 비밀값·DSN·질문 원문을 로그나 문서에 남기지 않고 실제 Upstage 결과를 과장하지 않는다.
- 구현 노트·INDEX·버전·변경 이력을 동기화하고 Draft PR까지만 게시한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 진행을 승인했고 Codex가 구현·검증했다. |
| When — 언제 | 2026-07-28 KST, PR #20 병합 직후 |
| Where — 어디서 | Windows local/private worktree, Docker local DB `127.0.0.1:54322`, API/Web |
| What — 무엇을 | post-merge smoke, pinned Supabase CLI `--version` stderr 회귀 보정, 회귀 테스트·문서 |
| Why — 왜 | 최신 main이 실제 데모 환경에서 재현 가능하고 fail-closed 도구 검증이 시간 경과로 오작동하지 않게 하기 위해 |
| How — 어떻게 | 격리 worktree, RED/GREEN, exact allowlist regex, actual binary/hash 검증, 영역·브라우저 gate |
| How much — 어느 정도 | 제품 코드 0, 도구 1, 테스트 1, 문서/버전 4, provider 호출·비용 0 |

## 3. 시작 전 상태

- 관련 파일: `scripts/bootstrap_patched_supabase.ps1`,
  `scripts/tests/test_patched_supabase_tooling.py`, local API/Web와 Docker DB.
- `origin/main=028053d`; 원래 local main은 PR #20 이전이었고 `apps/web/next-env.d.ts`에 Next dev
  자동 생성 차이만 있었다. 자동 생성 차이를 복원한 뒤 `--ff-only`로 동기화했다.
- pinned binary stdout은 `2.109.1`, exit 0, SHA-256은 runtime manifest와 일치했다.
- Supabase가 최신 `2.110.0`을 발표한 뒤 pinned `2.109.1 --version`이 공식 업데이트 알림을
  stderr에 쓰기 시작해 기존 “stderr는 무조건 빈 값” 검증이 실패했다.
- Docker DB 컨테이너는 healthy였고 API `.env`의 필수 두 값은 존재했다. 값은 출력하지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-069/D-105 | provider gate | 실패한 actual selector corrective rerun | 새 명시 승인 전 실행하지 않음 | Upstage 품질 증거 |
| LOCAL-SMOKE-01 | internal | 공식 update advisory를 stderr 오류로 볼지 | exact 2줄만 allowlist | local CLI verifier |
| LOCAL-SMOKE-02 | internal | actual browser 19→20을 재실행할지 | DB reset 전에는 state-changing spec 미실행 | local DB 행 |

## 5. 설계 결정과 대안

### 선택

`--version` stderr가 비어 있거나, 설치 버전 `2.109.1`과 공식 Supabase 업데이트 URL을 포함한
정확한 2줄 공지만 허용한다. stdout exact version, exit 0, manifest hash 검증은 그대로 유지한다.

### 이유

공식 CLI의 새 비오류 알림 때문에 local bootstrap이 시간에 따라 깨지는 문제를 제거하면서,
실행 파일 손상·임의 진단·버전 drift를 허용하지 않는다.

### 고려했지만 선택하지 않은 대안

- 모든 stderr 허용: 공급망·실행 오류를 숨길 수 있어 폐기.
- 바로 `2.110.0`으로 업그레이드: pinned patch·hash·DB replay 재검증 범위를 불필요하게 확대해 폐기.
- 알림 텍스트의 일부만 포함하면 허용: 임의 stderr가 섞일 수 있어 폐기.
- actual 19→20 브라우저 spec 재실행: 현재 DB를 reset하지 않으면 증거가 왜곡되므로 미실행.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/bootstrap_patched_supabase.ps1` | exact official advisory 검사 helper와 version probe 연결 | 새 공식 공지는 허용하고 임의 stderr는 차단 |
| `scripts/tests/test_patched_supabase_tooling.py` | 공식 공지 PASS와 임의 진단 FAIL RED/GREEN 회귀 | fail-open 방지 |
| `versions/manifest.json` | guidance/test/docs patch 승격 | 구현·검증 계보 |
| `CHANGELOG.md`, `docs/12_VERSIONING_AND_RELEASES.md` | 원인·경계·검증 결과 기록 | 운영 인수인계 |

### 데이터 흐름/상태 변화

- DB migration, seed, KB, official/mock data 변경은 0이다.
- corrected actual smoke의 질문 응답은 local DB 정책에 따라 interaction metadata가 추가될 수
  있으나 질문 원문은 저장되지 않는다. 두 번의 관리자 조회에서 NEW 총계는 8로 동일했다.
- provider-off smoke 결과는 날씨 `OUT_OF_SCOPE`, 증명서 정확한 3-option FOLLOWUP을 확인했다.
  자연어 전입/대형폐기물과 civic scope gap 예시는 provider-off에서 범용 FOLLOWUP이었다.

### 오류·빈 상태·롤백

- official advisory 형식이 바뀌면 verifier는 다시 fail-closed 한다.
- 임의 stderr는 테스트와 실제 helper 모두 거부한다.
- 롤백은 이 브랜치의 도구·테스트·문서 commit을 revert하면 된다. DB rollback은 필요 없다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.1-bounded-hybrid-rag | unchanged | 제품 동작 변경 없음 |
| Web | 0.8.0-guided-chat | unchanged | Web 변경 없음 |
| API | 4.0.0-draft | unchanged | 공개 계약 변경 없음 |
| DB schema | 0.5.0-local | unchanged | migration 없음 |
| Official data | 0.1.0-initial.2 | unchanged | seed/KB 변경 없음 |
| Mock data | 0.0.0-not-populated | unchanged | mock 변경 없음 |
| Prompt set | 0.4.0-topic-coverage | unchanged | provider/prompt 변경 없음 |
| Repo guidance | 1.7.9 | 1.7.10 | pinned CLI 검증기 patch |
| Test suite | 2.1.1-bounded-hybrid-rag-closeout | 2.1.2-patched-cli-advisory | stderr 회귀 추가 |
| Docs | 2.29.0 | 2.29.1 | post-merge actual evidence |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| focused API Hybrid RAG/local/chat tests | PASS | 136, warning 1 | console |
| Ruff format/check + Mypy | PASS | 114 source files | console |
| Web lint/typecheck/unit | PASS | 14 files, 68 tests | console |
| pre-fix exact official advisory regression | RED | expected failure | console |
| patched Supabase actual binary verifier | PASS | pinned 2.109.1/hash exact | console |
| patched tooling unit suite | PASS | 25/25 | console |
| actual local app `/ready` | PASS | HTTP 200 | console |
| actual local admin failed-question list | PASS | NEW total 8 | console |
| Web production build | PASS | Next 16.2.10 | console |
| Playwright fixture browser matrix | PASS | 27/27, 390/430/desktop | console |
| `powershell -File scripts/verify.ps1` | PASS | 31 stages, 1191.5s, exit 0 | console |

### 미실행 검증과 이유

- `admin-core-loop.actual.spec.ts`: disposable DB reset/immutable seed 뒤 한 번만 실행하는 19→20
  state-changing 증거이므로 현재 ACTIVE 20 DB에서 재실행하지 않았다.
- actual Upstage selector corrective run: 기존 actual FAIL 이후 새 명시 승인 gate를 유지했다.
- public/remote deploy: target/configured scope가 없고 이번 local patch 범위가 아니다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: DSN/secret/env 값과 질문 원문을 출력·문서화하지 않았다. 초기 PowerShell pipe가 한글을
  `?`로 바꿔 만든 가짜 `PRIVACY_UNRESOLVED`는 UTF-8 harness로 교정해 제품 결함과 분리했다.
- Security: exact update advisory만 허용하고 arbitrary stderr, nonzero exit, version/hash drift는
  계속 차단한다. repository secret scan, Web bundle scan, package/diff와 전체 gate가 PASS했다.
- Accessibility: 390/430/desktop E2E 27/27로 keyboard, viewport, value-free state를 재검증했다.
- Performance/cost: provider 호출·비용 0. Web build 21초, browser matrix 약 46초였다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 0; immutable `.2`와 별도 ACTIVE 20 상태를 재시드하지 않았다.
- mock/AI 생성: fixture 브라우저는 기존 시연용 mock만 사용했고 실제 provider 생성은 0이다.
- schema/lineage: 변경 0.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 provider-off 실제 경로는 안전하지만 일부 자연어 변형과 civic scope gap을 범용 FOLLOWUP으로
  처리한다. Hybrid RAG의 실제 분류 품질을 확인하려면 기존 FAIL 원인을 교정한 뒤 별도 actual
  Upstage rerun 승인이 필요하다.
- 이 PR은 pinned CLI/검증 문서 patch다. application, DB, KB, prompt를 바꾸지 않는다.
- Draft PR은 사람이 검토·병합해야 하며 Codex는 자동 merge하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- helper regex는 semantic version의 선행 0을 제한하고 installed version을 pinned `2.109.1`로
  고정하며 LF/CRLF와 선택적 마지막 newline만 허용한다.
- actual smoke는 TestClient를 사용해 request access log 없는 local composition을 검증했다.
- Windows PowerShell 5 파이프는 `$OutputEncoding=UTF8` 없이는 한글을 `?`로 손상시키므로 두 번째
  실행만 동작 증거로 사용했다.

## 13. 인수인계·재현·롤백

### 재현

1. 최신 `origin/main`에서 이 브랜치를 checkout한다.
2. `pwsh -NoProfile -File scripts/bootstrap_patched_supabase.ps1 -Action Verify`를 실행한다.
3. `python -B -m unittest scripts.tests.test_patched_supabase_tooling -v`를 실행한다.
4. Docker DB와 local `.env`가 준비된 경우 API `/ready` 및 Web build/E2E를 실행한다.

### 롤백

이 브랜치 commit을 revert한다. local DB, migration, seed, secret 변경은 없어 별도 데이터 복구가
필요 없다.

### 다음 개발자 시작점

actual selector의 strict usage/provider mismatch 원인을 aggregate-only 증거로 진단하고, 인간의
새 실행 승인 뒤 한 번만 corrective actual을 수행한다.

## 14. 남은 위험·미해결 질문·다음 단계

- Supabase CLI가 공식 advisory 문구를 바꾸면 verifier가 의도적으로 다시 멈춘다.
- provider-off 결과는 actual Upstage 품질 증거가 아니다.
- public/remote deployment와 remote DB는 계속 미구성/미검증이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

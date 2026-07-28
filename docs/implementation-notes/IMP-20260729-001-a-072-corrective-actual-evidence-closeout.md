# IMP-20260729-001 — A-072 corrective actual evidence closeout

- Date/Time (KST): 2026-07-29T00:52:58+09:00
- Task ID: A-072-CLASSIFIER-CORRECTIVE-ACTUAL
- Type: implementation-provider-actual
- Status: Done — exact-one actual completed; aggregate FAIL; rerun 0
- Author/Agent: 사용자 승인 / Codex 실행·aggregate 판정
- Branch: `codex/a-072-strict-classifier-wire`
- Source commit: `efc0b34da61678d7e6bb22c23685591f393ad647`
- Related:
  [approved plan](../superpowers/plans/2026-07-28-upstage-classifier-strict-five-key-wire.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md), D-111~D-117

## 1. 사용자 요청과 완료 기준

사용자는 exact 문구 `A-072 corrective actual 1회 실행 승인`으로 Task 6의 local/private
Upstage 호출 1회를 승인했다. clean source, ignored local profile, key presence boolean, D-111
archive, lock 부재, 보호 해시와 secret scan을 확인한 뒤 명령을 정확히 한 번만 실행하고
PASS/FAIL 모두 재실행하지 않는 것이 완료 기준이다. 질문·provider content·status detail·키·
DSN은 확인하거나 기록하지 않고 aggregate만 보존한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 인간 결정자 사용자, 실행·판정자 Codex |
| When — 언제 | 2026-07-29 KST, Tasks 1~5 clean-source review 뒤 |
| Where — 어디서 | isolated worktree, local/private ignored profile, Upstage `solar-pro3` classifier |
| What — 무엇을 | fixed 20-case corrective actual 1회와 aggregate evidence closeout |
| Why — 왜 | D-111의 `KEY_SET_REJECTED` 9/9가 strict five-key wire로 해소되는지 검증 |
| How — 어떻게 | value-free preflight → D-111 archive → canonical runner 1회 → no-rerun → authority/version closeout |
| How much — 어느 정도 | selected 20, provider-free 11, outbound 9, retry 0, VAT 포함 USD 0.002496648 |

## 3. 시작 전 상태

- source는 `efc0b34…`, worktree는 clean이었고 current report는 D-111 FAIL이었다.
- local key는 값이 아닌 존재 boolean만 확인했다. worktree `.env`는 ignored 임시 사본으로만
  사용하고 실행 뒤 삭제했다. 원본 `.env`는 수정하지 않았다.
- offline evidence와 fixture/coverage/official `.2`/release manifest 보호 해시가 일치했다.
- secret scan PASS, current lock 없음, D-111 archive target 없음 확인 뒤 byte-preserving move했다.

## 4. 결정·가정과 결과

| ID | 구분 | 내용 | 결과 |
|---|---|---|---|
| D-117 | 인간 승인 | corrective actual 정확히 1회 | 실행 1, rerun 0 |
| A-072 | 검증 | exact key-set 교정 | `KEY_SET_REJECTED` 9→0으로 해결 |
| A-073 | 남은 미지 | enum/shape 거절의 정확한 내부 원인 | body를 보지 않아 단정하지 않음; 새 설계·승인 필요 |

## 5. 선택한 설계와 버린 대안

승인된 fixed runner와 strict production parser를 그대로 사용하고 process-scoped non-secret
profile override만 적용했다. 실패 뒤 provider body 확인, prompt/schema 즉시 변경, 동일 명령
재실행은 증거 독립성과 privacy 경계를 깨므로 수행하지 않았다.

## 6. 실행·변경 상세

| 파일/영역 | 변경 |
|---|---|
| current actual report | source `efc0b34…`의 D-117 aggregate FAIL 생성 |
| archived D-111 report | `…D111-KEY-SET-REJECTED-FAIL.md`로 원본 보존 |
| authority docs | D-117 수치, A-072 resolved, A-073 open, fail-closed 권위 반영 |
| version/changelog | documentation `2.30.2→2.30.3`, runtime 축 불변 |
| implementation notes/INDEX | offline note 후속과 이 closeout note 연결 |

DB row, API/public contract, official/mock data, prompt/runtime code, package/lockfile은 변경하지
않았다. rollback은 이 evidence commit을 revert하면 되며 DB/data 복구나 secret rotation은
필요 없다.

## 7. 버전 전후

| 축 | Before | After | 이유 |
|---|---|---|---|
| Application | 0.12.3 | 0.12.3 | runtime 불변 |
| Web | 0.8.0 | 0.8.0 | 불변 |
| API/contracts | 4.0.0 / 1.0.0 | 동일 | 공개 shape 불변 |
| DB/official/mock | 0.5.0 / 0.1.0-initial.2 / 0.0.0 | 동일 | 데이터 write 0 |
| Prompt/tests | 0.4.2 / 2.1.6 | 동일 | 즉시 교정·재실행 금지 |
| Documentation | 2.30.2 | 2.30.3 | D-117 aggregate evidence |

## 8. 명령과 실제 결과

| 검증 | 결과 |
|---|---|
| preflight profile/key/offline/protected/secret | PASS; 값 출력 0 |
| canonical actual runner | 정확히 1회, exit 1 `ACCEPTANCE_FAILED`, rerun 0 |
| aggregate | 20 selected, skip 0, provider-free 11, outbound 9 |
| transport/usage/stage | HTTP 2xx 9, usage 9, terminal stage 9 |
| strict decision | `ENUM_SHAPE_REJECTED` 9, accepted/match 0, FAIL |
| metering | retry 0, observed=ledger USD 0.002496648, cap USD 0.20 |
| `python -B scripts/check_repository_docs.py` | PASS |
| `check_secret_patterns.ps1 -RepositoryRoot .` | PASS, findings 0 |
| `git diff --check` / `git diff --cached --check` | PASS |
| `python -m json.tool versions/manifest.json` | PASS |
| protected runtime/DB/data/package staged diff | 0 |
| report lock / worktree `.env` | 0 / 0 |

전체 API/Web/DB 테스트는 Task 5에서 같은 runtime source에 대해 완료됐고 이번 변경은
aggregate evidence와 문서뿐이므로 재실행하지 않는다. provider actual도 다시 실행하지 않는다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy/Security: 질문·prompt·provider body·status detail·exception·key·DSN 보관·출력 0.
  privacy/policy outbound 0, secret finding 0을 유지한다.
- Accessibility: Web/UI 변경 0.
- Performance/cost: 9 outbound, retry 0, concurrency 1, VAT 포함 USD 0.002496648.
- Local modes: process override 종료 뒤 원본 ignored profile false/false 확인.

## 10. 공식 데이터와 mock 구분

official `.2` bytes·DB·lineage는 불변이고 mock/AI 생성 답변을 데이터로 승격하지 않았다.
provider 응답 content는 저장하지 않았으며 aggregate count만 evidence다.

## 11. 인간이 반드시 알아야 하는 내용

- A-072는 key-set 거절을 해결했지만 provider selector 전체 acceptance는 아직 FAIL이다.
- 시민 runtime은 계속 결정론적 fail-closed 경로가 권위다.
- A-073 enum/shape 원인 설계와 다음 actual은 새 인간 결정·별도 승인 전 금지한다.
- 이 작업은 push·merge·public/remote·DB reset/seed 권한을 포함하지 않는다.

## 12. AI 내부 구현 세부 — 인간이 굳이 이해하지 않아도 되는 내용

- runner는 response마다 closed terminal enum을 정확히 하나만 집계했다.
- observed usage와 ledger charge가 완전히 일치해 conservative charge는 0이다.
- D-111 report는 exact archive name으로 보존하고 current pointer만 D-117로 교체했다.

## 13. 재현·인수인계·롤백

재현은 승인 plan Task 6의 canonical 명령을 참고하되 **이미 승인된 1회를 소비했으므로 현재
다시 실행하지 않는다**. 개발자는 current/archived report와 D-117만 읽어 aggregate를
재현한다. 롤백은 evidence commit 1개를 `git revert`하며, local DB/data/provider side 복구는
없다.

## 14. 남은 위험과 다음 단계

A-073에서 content-free 방식으로 enum/shape 원인을 더 좁힐지, local MVP에서 provider
분류를 비활성으로 유지할지 인간이 결정해야 한다. provider body를 사후 열람하거나 현재
prompt/schema를 바꿔 즉시 rerun하면 안 된다.

## 15. 자체 리뷰

- [x] 요청 충족: exact-one 실행, rerun 0
- [x] source-of-truth/결정/업무/버전 동기화
- [x] 개인정보·secret·공식 데이터 경계 유지
- [x] D-111 보존과 current D-117 evidence 생성
- [x] 구현 노트 INDEX 갱신

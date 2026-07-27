# IMP-20260727-010 — 자연스러운 대화 Slice 3 범위확대 운영과 public DB hardening

- Date/Time (KST): 2026-07-27T03:26:09+09:00
- Task ID: CHAT-NATURAL-001-S3
- Type: implementation-data-security
- Status: Done — local verified; remote target smoke remains integration follow-up
- Author/Agent: Codex `/root`
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: 7f5319d
- Related plan/ADR/RFP: D-085/D-090~D-092, ADR-0018/0024/0026, ADMIN-002, CHAT-NATURAL plan

## 1. 사용자 요청과 완료 기준

### 요청

지원범위 밖 행정 민원을 기존 실패/KB 후보와 분리해 검토하고, 임의의 eligible grounding
실패는 운영자가 공식 출처로 후보를 작성·별도 승인하며, public 준비 함수 hardening을 완료한다.

### Acceptance Criteria

- 00680 queue는 masked text만 30일 보관하고 자동 후보/ACTIVE 링크가 없다.
- APPROVER만 NEW를 PLANNED/DISMISSED로 1회 검토한다.
- 관리자 API/Web가 실제 DB를 사용하고 arbitrary candidate form/상태 이력을 제공한다.
- 00700은 exact 22 function의 search_path property만 변경하고 rollback/replay가 통과한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 보안·DB 승인자, Codex DB/API/Web 구현자 |
| When — 언제 | 2026-07-27 KST |
| Where — 어디서 | Supabase PostgreSQL 17, API admin service/repository, `/admin` |
| What — 무엇을 | 00680 queue, admin transport/UI, general authoring, 00700 hardening |
| Why — 왜 | 범위 확대 검토와 공식 KB 승인 책임을 섞지 않고 public 보안 부채를 제거하기 위해 |
| How — 어떻게 | RLS+fixed capabilities, typed API, explicit workflow, property-only migration |
| How much — 어느 정도 | DB 11 files/385 tests, tooling 67+47, API/admin 345, contract 94, Web 60/E2E 6 |

## 3. 시작 전 상태

- 관련 파일: `00680`, `00700`, rollbacks/pgTAP, admin repository/API/Web/E2E.
- 기존 동작: WASTE-03 고정 Web builder와 PENDING-only 화면, scope-gap 운영 surface 부재.
- 발견한 충돌/부채: 21/22 privileged functions가 public 기준의 explicit `pg_temp`를 빠뜨렸다.
- Git 상태: 격리 worktree; actual local DB는 사용자 승인대로 reset됐다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-054/A-056 | 해소 | 일반 후보 작성·상태 이력 | 운영자 작성/4개 상태 | admin UX |
| A-059 | 해소 | scope-gap 저장/검토 | 별도 queue/30일 | DB/privacy |
| Q-SEC-003 | 해소 | public hardening | exact 22 property-only | migration/public |

## 5. 설계 결정과 대안

### 선택

scope-gap은 `civic_scope_gaps`와 네 capability로 격리한다. KB 후보는 운영자 공식 입력만
저장하고 기존 별도 승인 capability를 재사용한다. 00700은 allowlist 22개 signature마다
정적인 `ALTER FUNCTION`/`SET search_path` 문장만 사용한다.

### 이유

제품 범위 검토와 지식 승인 상태 머신을 분리하고, public 준비에서 함수 body/owner/ACL/data를
바꾸지 않으면서 security-definer search path를 안전하게 고정한다.

### 고려했지만 선택하지 않은 대안

- scope-gap을 failed_questions에 저장: candidate eligibility 의미가 섞여 제외.
- LLM 자동 후보/승인: 공식 출처·별도 승인 원칙 위반.
- 동적 function discovery ALTER: 미래 함수까지 의도치 않게 바꿔 금지.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| 00680/rollback/pgTAP | separate queue, 30d purge, review lifecycle | privacy·state isolation |
| API repository/service/routes | list/review scope gaps, purge | 실제 DB transport |
| Admin Web | general official form, scope panel, candidate history | 운영 가능성 |
| 00700/rollback/pgTAP/runner | exact 22 property hardening, 11-step replay | public security |

### 데이터 흐름/상태 변화

`CIVIC_SCOPE_GAP` masked text는 NEW→PLANNED/DISMISSED 후 30일에 text만 NULL 처리된다.
eligible IG는 failed→reason confirmed→operator-authored candidate→different approver→ACTIVE다.
00700은 row/table/function body를 변경하지 않는다.

### 오류·빈 상태·롤백

DB 불능은 admin/chat 모두 fail closed한다. 00680 rollback은 queue/functions/table을 제거하며,
00700 rollback은 21개를 `pg_catalog`, 기존 validator 1개를 `pg_catalog, pg_temp`로 복원한다.

## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.9
- application: 0.10.0-office-directory-runtime
- web: 0.6.0-answer-mode
- api: 3.3.0-draft
- shared_contracts: 0.6.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.2.0-grounded-live-chat
- test_suite: 1.8.0-local-demo-readiness
- documentation: 2.23.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.10.0 | 0.11.0-natural-dialogue | admin scope service |
| Web | 0.6.0 | 0.7.0-natural-dialogue | general operations UX |
| API | 3.3.0-draft | 4.0.0-draft | scope admin contract |
| DB schema | 0.4.0-local | 0.5.0-local | 00680+00700 |
| Official data | `.2` | 동일 | 이 단계 seed/승격 없음 |
| Mock data | not-populated | 동일 | fixture 명시 |
| Prompt set | 0.2.0 | 0.3.0 | 통합 release |
| Test suite | 1.8.0 | 1.9.0 | DB/admin 회귀 |
| Docs | 2.23.1 | 2.24.0 | 세 Slice 기록 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| admin/API focused pytest | PASS | 345; DB skip 8 | API tests |
| contract tests | PASS | 94 | shared contracts |
| Web unit/lint/typecheck/build | PASS | 60; 0 error | Web |
| admin fixture Playwright | PASS | 6, 3 viewports | Web E2E |
| `verify_database.ps1` | PASS | 11 pgTAP files/385 tests, 11-stage rollback/replay | local PostgreSQL 17 |
| tooling pytest | PASS | 67 tests + 47 subtests | `scripts/tests` |

### 미실행 검증과 이유

formal `.2` seed/19→20 actual browser와 remote smoke는 다음 integration tasks에서 상태 변형을
한 번만 수행한다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: masked question만 최대 30일, raw/answer/source/context snapshot 및 workflow FK 0.
- Security: RLS, backend-only capability, APPROVER-only terminal transition, 00700 exact allowlist.
- Accessibility: labeled form/status tabs/44px controls, 3 viewport E2E.
- Performance/cost: indexed status/expiry reads; 외부 API 비용 0.

## 10. 데이터와 출처 영향

- 공식 데이터: `.2` bytes/approval 불변; ACTIVE 승격은 formal regression에서만.
- mock/AI 생성: fixture는 승인 불가·시연용 표기.
- schema/lineage: 00680→00700, rollback 00700→00680→…→00100.
- verified date: 2026-07-27.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- public citizen 준비는 강화됐지만 인증 없는 admin은 remote에서 계속 비활성이다.
- remote target이 없으면 배포를 임의로 생성하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- 00700 fingerprint는 22 body MD5, owner, ACL을 pgTAP으로 동결한다.
- Web fixed WASTE draft builder는 제거하고 typed form만 사용한다.

## 13. 인수인계·재현·롤백

### 재현

`verify_database.ps1`, API/admin tests, Web test/build와 fixture admin Playwright를 실행한다.

### 롤백

00700 matching rollback 후 00680 rollback을 newest-first로 실행한다. Web/API commits를 revert하고
admin mode를 disabled로 유지한다.

### 다음 개발자 시작점

clean reset 후 immutable `.2` 정식 seed, 19→20 approval, actual browser E2E를 실행한다.

## 14. 남은 위험·미해결 질문·다음 단계

- remote citizen target·도메인·credential 구성 여부는 아직 확인 전이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

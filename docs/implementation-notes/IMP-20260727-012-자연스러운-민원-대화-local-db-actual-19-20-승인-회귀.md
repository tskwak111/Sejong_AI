# IMP-20260727-012 — 자연스러운 민원 대화 local DB actual 19→20 승인 회귀

- Date/Time (KST): 2026-07-27T04:51:00+09:00
- Task ID: CHAT-NATURAL-001-T15
- Type: testing-data-actual
- Status: Done — local/private only
- Author/Agent: Codex `/root`
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: 7c96a0a
- Related plan/ADR/RFP: Task 15, D-044/D-058/D-092, ADR-0017/0020, ADMIN-002

## 1. 사용자 요청과 완료 기준

### 요청

승인된 disposable local DB를 clean reset하고 immutable `.2` 정식 seed와 실패 질문→후보→
별도 승인→20번째 ACTIVE→동일 질문 개선 흐름을 실제로 실행한다.

### Acceptance Criteria

- `[db.seed].enabled=false`를 유지한다.
- 정식 runner가 identity/rollback/concurrency/19·3·10/final/cleanup을 통과한다.
- PERSONAL_LOOKUP row/text 저장 0과 자기승인 차단을 증명한다.
- 최종 ACTIVE 20과 개선 재질의 공식 source binding을 증명한다.
- DSN·secret·질문 원문을 출력하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 DB·데이터 승인자, Codex 실행·검증 담당, PM-LOCAL-001 별도 승인자 fixture |
| When — 언제 | 2026-07-27 KST |
| Where — 어디서 | loopback `127.0.0.1:54322`, patched Supabase/PostgreSQL 17 local DB |
| What — 무엇을 | `.2` seed 19/3/10과 governed 19→20 approval regression |
| Why — 왜 | 자연스러운 chat 개선이 기존 데이터 품질·privacy·승인 불변식을 깨지 않음을 증명 |
| How — 어떻게 | supported seed runner→safe runtime→login rotation→process secret→actual harness |
| How much — 어느 정도 | seed 19/3/10, final ACTIVE 20, event/failed +1 eligible case, provider 0 |

## 3. 시작 전 상태

- 관련 파일: immutable `.2`, seed runner, local login provisioner, actual MVP regression harness.
- 기존 동작: code/schema integration은 green이었지만 현재 feature source의 formal actual rerun은 없었다.
- 발견한 충돌/부채: root 뒤 Supabase default network runtime이 재등장해 seed preflight 전 제거했다.
- Git 상태: commit `7c96a0a`, clean isolated worktree; ignored local `.env`만 credential rotation 대상.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-092 | 인간 승인 | destructive local reset/seed | 승인된 disposable exact target만 | local rows |
| Reviewer | 인간 확정 | 별도 승인자 | `PM-LOCAL-001`, 작성자와 다름 | ACTIVE lineage |

## 5. 설계 결정과 대안

### 선택

stock seed를 켜지 않고 supported immutable `.2` runner를 사용했다. seed runner cleanup 뒤 persistent
volume을 exact safe network로 재시작하고 admin DSN과 CSPRNG context secret은 process에만 유지했다.

### 이유

공식 data bytes·lineage와 runtime 승인 흐름을 분리하면서 credential·질문 비노출을 지킨다.

### 고려했지만 선택하지 않은 대안

- `db.seed=true`: 승인된 separate formal seed 경계를 깨므로 금지.
- bare remote/stock Supabase command: patched runtime identity를 우회하므로 금지.
- 기존 ACTIVE 20 상태 재사용: clean 19→20 증거가 아니므로 제외.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| DB runtime | default network runtime stop, exact safe network start | loopback identity |
| immutable `.2` | identity/rollback/concurrency/seed/replay/final execution | official baseline |
| ignored API env | backend login password rotation only | least-privilege app access |
| actual harness | privacy, idempotency, candidate approval, requery | end-to-end regression |
| report/note | bounded counts and rollback | reproducibility |

### 데이터 흐름/상태 변화

clean schema→official ACTIVE 19/office 3/mapping 10→PII-free eligible grounding failure 1→reason
confirmed→candidate→different approver→`KB-WASTE-03` ACTIVE→final ACTIVE 20이다. PERSONAL_LOOKUP은
event/failed delta 모두 0이다.

### 오류·빈 상태·롤백

실패 시 runner는 stable step/code만 출력한다. 현재 ACTIVE 20 상태를 되돌리려면 disposable DB를
supported reset하고 immutable `.2` seed runner를 다시 실행하면 exact 19 baseline이 복구된다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.11.0-natural-dialogue | 동일 | actual evidence |
| Web | 0.7.0-natural-dialogue | 동일 | 변경 없음 |
| API | 4.0.0-draft | 동일 | runtime only |
| DB schema | 0.5.0-local | 동일 | row state only |
| Official data | 0.1.0-initial.2 | 동일 | immutable |
| Mock data | 0.0.0-not-populated | 동일 | 승인 workflow fixture와 공식 data 분리 |
| Prompt set | 0.3.0-hybrid-classifier | 동일 | provider 0 |
| Test suite | 1.9.0-natural-dialogue | 동일 | evidence only |
| Docs | 2.24.0 | 동일 | report/note |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `verify_data_seed.ps1 -ReleaseVersion 0.1.0-initial.2` | PASS | 122.2s, 19/3/10 | local actual report |
| seed identity/rollback | PASS | exact identity, tables 8 partial 0 | runner |
| concurrency A/B | PASS | both orderings, capability rows 1 | runner |
| seed-cycle/final | PASS | replay 1, second seed/compensation blocked | runner |
| actual regression | PASS | fixed 15-line result, final 20 | local actual report |
| readiness | PASS | 200 | actual harness |

### 미실행 검증과 이유

실제 Upstage classifier와 remote deployment는 DB state/cost와 분리된 Task 16/17이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: PERSONAL_LOOKUP persistence delta 0/0; 질문 원문 출력 0.
- Security: backend login은 non-superuser capability member이며 secret/DSN 출력 0.
- Accessibility: DB/API regression이므로 Web UI 변경 0.
- Performance/cost: provider outbound 0, 비용 USD 0.

## 10. 데이터와 출처 영향

- 공식 데이터: `.2` bytes 불변, semantic SHA-256은 bounded report에 기록.
- mock/AI 생성: 승인 회귀용 PII-free row만 local DB에 생성; official release에 포함되지 않는다.
- schema/lineage: 작성자와 승인자가 다르고 server-bound public source ID를 확인했다.
- verified date: 2026-07-27.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 local DB는 의도적으로 ACTIVE 20 상태이고 container가 실행 중이다.
- 다시 19 baseline이 필요하면 반드시 reset+정식 `.2` seed를 함께 수행해야 한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- admin DSN은 CLI output에서 process 변수로만 파싱하고 child에 전달했다.
- 48-byte CSPRNG context secret은 process 종료 시 제거했다.

## 13. 인수인계·재현·롤백

### 재현

preflight container/listener 0에서 supported seed runner를 실행하고, safe runtime에서 login을
provision한 뒤 actual regression을 정확히 한 번 실행한다.

### 롤백

patched CLI로 local runtime을 stop하고 `verify_database.ps1`→`verify_data_seed.ps1` 순서로
재구성한다.

### 다음 개발자 시작점

DB를 다시 reset하지 말고 Task 16 actual classifier는 PII-free fixture와 provider-only
aggregate로 실행한다.

## 14. 남은 위험·미해결 질문·다음 단계

- Docker/Supabase runtime이 외부 명령으로 default network에 재기동되는 drift 원인은 운영
  runbook에서 다시 감시한다.
- Web general candidate form의 실제 브라우저 제출은 fixture E2E로 검증됐고 이 backend harness는
  reserved deterministic approval case를 사용했다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

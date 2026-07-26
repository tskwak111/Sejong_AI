# IMP-20260726-006 — 오표시 metadata 22행과 cleanup 선택지 설명

- Date/Time (KST): 2026-07-26T13:58:12+09:00
- Task ID: LLM-003-METADATA-CLEANUP
- Type: decision-explanation
- Status: Decision-only Done
- Author/Agent: Codex primary agent
- Branch: codex/LLM-003-metadata-explanation
- Base commit: be7387f
- Related evidence:
  - [LLM-003 local actual 증거](IMP-20260726-002-llm-003-local-actual-실행과-aggregate-증거.md)
  - [팀 결정](../source-of-truth/TEAM_DECISIONS.md)
  - [DB private schema](../../supabase/migrations/20260716000100_private_schema.sql)
  - [DB capability functions](../../supabase/migrations/20260716000300_capabilities_and_functions.sql)

## 1. 사용자 요청과 완료 기준

### 요청

- 직전 보고의 “오표시 metadata 22행 삭제/reset 여부”와 “향후 AI actual
  재실행에는 새 승인이 필요하다”는 의미를 자세히 설명한다.
- 설명 과정에서 local DB 데이터를 삭제·수정하거나 외부 LLM을 호출하지 않는다.

### Acceptance Criteria

- 22행에 포함된 정보와 포함되지 않은 정보를 저장소 근거로 구분한다.
- 개인정보·보안 위험과 통계·감사 데이터 품질 위험을 구분한다.
- 자동 삭제하지 않은 이유와 유지·reset·선별 정리·재표시 대안의 장단점을 설명한다.
- 지금 권고안과 향후 실제 AI 재실행 승인 경계를 명시한다.
- 제품 코드·계약·DB·공식 데이터·비밀값은 변경하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 설명을 요청했고 Codex가 병합된 저장소 근거를 재검토했다. DB 정리 여부의 최종 결정자는 사용자다. |
| When — 언제 | 2026-07-26 KST, PR #13 병합과 local actual 사후 확인 뒤 |
| Where — 어디서 | private/local 저장소 문서·API write model·Supabase migration·actual runner를 읽었다. local DB에는 연결하거나 쓰지 않았다. |
| What — 무엇을 | `is_test=false`로 잘못 표시된 actual 평가 metadata 22행의 의미·영향·정리 선택지를 설명했다. |
| Why — 왜 | 개인정보 사고와 데이터 품질 문제를 혼동하지 않고, 식별 근거 없는 파괴적 정리를 막기 위해서다. |
| How — 어떻게 | schema, insert 조건, actual evidence, 현재 pre-write guard를 교차 검토했다. |
| How much — 어느 정도 | metadata 22행, 정리 대안 4개, 문서 2개만 변경; DB·제품 코드·외부 호출 0 |

## 3. 시작 전 상태

- 관련 파일:
  - `supabase/migrations/20260716000100_private_schema.sql`
  - `supabase/migrations/20260716000300_capabilities_and_functions.sql`
  - `apps/api/src/sejong_ai_api/db/models.py`
  - `scripts/run_upstage_grounded_chat_actual.py`
  - `docs/implementation-notes/IMP-20260726-002-llm-003-local-actual-실행과-aggregate-증거.md`
- 기존 동작:
  - `interaction_events`는 질문·답변·대화 전문·토큰·provider payload를 저장하지
    않는 metadata-only 테이블이다.
  - actual 검증 1회는 고정 질문 10건과 forced-timeout probe 1건의
    `interaction_events`를 기록했다.
  - 의미 검증용 첫 실행과 clean-output 재실행이 각각 성공하여 총 22행이 생겼다.
  - 당시 write path가 평가 행을 `is_test=false`로 전달해 일반 이벤트처럼 표시했다.
  - 병합된 runner는 DB write 전에 항상 `is_test=true`,
    `masked_question=None`을 강제하고 금지값을 발견하면 write 전에 중단한다.
- 발견한 충돌/부채:
  - 이미 생긴 22행에는 이 평가 실행만 고유하게 가리키는 `run_id`나 평가 marker가 없다.
  - 임의의 시간 범위, “최근 22개”, intent/source 조합만으로 삭제하면 실제 local
    demo 이벤트까지 지울 수 있다.
  - 아직 이 행들을 사용하는 운영 KPI dashboard query는 발견되지 않았지만,
    누군가 `is_test=false` 이벤트를 일반 사용량으로 집계하면 오염된다.
- Git 상태: `origin/main`의 병합 SHA `be7387f`에서 docs-only 설명 branch를 생성했고
  시작 시 tracked 변경은 없었다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-DB-CLEANUP-001 | Human decision | 오표시 22행을 지금 유지할지, local DB 전체를 reset할지 | 이번 요청에서는 설명만 수행하고 DB는 그대로 둔다. 현재 권고는 A(유지하되 KPI 증거로 사용하지 않음)다. | local DB 상태, 데모 재현, 통계 신뢰성 |
| A-050 | Assumption | 정확한 22개 request ID를 별도 안전한 local 증거에서 복원할 수 있는가 | 현재 tracked evidence에는 없다. 식별 가능하다고 가정하지 않는다. | 선별 update/delete 가능성 |
| A-051 | Internal | 현재 MVP에 `is_test=false`만 집계하는 운영 KPI 구현이 있는가 | 현재 코드 검색에서는 발견되지 않았다. 미래 집계 위험으로 분류한다. | 즉시 사용자 동작 없음, 향후 보고 정확성 |

## 5. 설계 결정과 대안

### 선택

- 이번 요청에서는 데이터 mutation을 하지 않는다.
- 당장은 22행이 있는 local DB snapshot의 이벤트 KPI를 권위 있는 평가 증거로 사용하지
  않고, 22행을 제외해야 한다는 사실을 기록한다.
- 실제 KPI·벤치마크가 필요해지기 전에는 명시적 승인을 받아 disposable local DB를
  reset하고 정식 seed·승인 흐름을 재현하는 방법을 권고한다.
- 정확한 ID 집합이 없는 상태에서는 “최근 22개” 삭제나 timestamp 기반 update를 금지한다.

### 이유

- 질문·답변 원문은 저장되지 않았으므로 즉각적인 개인정보 삭제 사고 대응 문제는 아니다.
- 그러나 `is_test=false`는 평가 호출을 정상 시민 이용처럼 보이게 하므로 데이터 품질과
  감사 의미가 틀리다.
- 데이터 삭제·reset은 공식 seed가 아닌 local mutable 상태와 20번째 ACTIVE 승인 이력까지
  제거할 수 있는 인간 승인 대상이다.
- 정확한 식별 기준 없이 수행하는 선별 정리는 오표시보다 더 큰 데이터 훼손을 만들 수 있다.

### 고려한 대안

- **A — 유지 + KPI 제외(현재 권고):**
  - 장점: 파괴적 변경이 없고 지금 개발을 계속할 수 있다.
  - 단점: 이 local DB의 event count는 clean benchmark 증거로 사용할 수 없다.
- **B — local DB 전체 reset + 정식 seed/replay(향후 clean benchmark 전 권고):**
  - 장점: 가장 명확한 clean state를 만든다.
  - 단점: 19개 ACTIVE seed 이후 20번째 ACTIVE 관리자 승인 시연 등 mutable 상태를
    다시 만들어야 하며 DB 삭제 승인이 필요하다.
- **C — 22행 선별 삭제:**
  - 장점: 다른 local 상태를 보존할 수 있다.
  - 단점: 현재 정확한 고유 marker나 request ID 목록이 없으므로 안전하게 수행할 수 없다.
- **D — 22행을 `is_test=true`로 재표시:**
  - 장점: 이벤트 자체는 보존하면서 통계 의미를 바로잡는다.
  - 단점: C와 같은 식별 문제가 있고, ad-hoc DB update는 명시적 data mutation
    승인·preview·transaction·검증이 필요하다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| 이 구현 노트 | 22행의 의미·영향·선택지·권고·승인 경계 기록 | destructive cleanup 없이 판단하도록 하기 위해 |
| `docs/implementation-notes/INDEX.md` | 이 결정 설명의 색인 1행 추가 | 구현 노트 의무와 탐색성 충족 |
| 제품/API/DB/data | 변경 없음 | 설명 요청이며 DB mutation 승인이 없기 때문 |

### 데이터 흐름/상태 변화

- **이번 작업의 상태 변화:** 문서만 추가됐다. local DB 행은 읽거나 변경하지 않았다.
- **문제가 된 과거 흐름:** actual fixture → `/api/v1/chat` → 정상 구조화 답변 또는
  TEMPLATE 복구 → metadata-only `interaction_events` 기록. 이때 두 번의 실행에서
  11행씩 `is_test=false`로 잘못 표시됐다.
- **현재 보호 흐름:** actual runner가 delegate write 직전에 `is_test=true`,
  `masked_question=None`과 금지값 부재를 확인한다. 조건 불충족 시 DB write 전에 실패한다.
- `failed_questions` insert는 `answer_status=FALLBACK`, 허용된 fallback reason,
  `masked_question IS NOT NULL`일 때만 일어난다. 이번 22행은 SUCCESS actual 증거이며
  질문 text를 넘기지 않았으므로 실패 질문·후보·ACTIVE KB 증가에 쓰이지 않는다.

### 오류·빈 상태·롤백

- 정확한 식별자가 없으면 C/D를 실행하지 않는다.
- B를 선택할 경우 reset 전에 필요한 local mutable 시연 상태를 목록화하고,
  migration → immutable `.2` seed → verify-final → 필요 시 별도 승인자 20번째 ACTIVE
  흐름 순으로 재현해야 한다.
- 이번 docs-only 변경은 commit revert로 되돌릴 수 있고 DB rollback은 필요 없다.

## 7. 버전 전후

### 생성 시 매니페스트

- product_spec: 2.5.0
- repo_guidance: 1.7.8
- application: 0.9.1-grounded-local-chat-evidence
- web: 0.6.0-answer-mode
- api: 3.2.0-draft
- shared_contracts: 0.5.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.2.0-grounded-live-chat
- test_suite: 1.6.1-grounded-actual
- documentation: 2.20.2

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.9.1-grounded-local-chat-evidence | 동일 | 제품 변경 없음 |
| Web | 0.6.0-answer-mode | 동일 | Web 변경 없음 |
| API | 3.2.0-draft | 동일 | API/contract 변경 없음 |
| DB schema | 0.4.0-local | 동일 | migration/data mutation 없음 |
| Official data | 0.1.0-initial.2 | 동일 | seed/KB 변경 없음 |
| Mock data | 0.0.0-not-populated | 동일 | mock 변경 없음 |
| Prompt set | 0.2.0-grounded-live-chat | 동일 | prompt/provider 호출 없음 |
| Test suite | 1.6.1-grounded-actual | 동일 | 테스트 코드 변경 없음 |
| Docs | 2.20.2 | 2.20.2 | source-of-truth 버전 변경 없이 구현 노트만 추가 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `git status --short` | 시작 시 clean | 0 tracked 변경 | Git 출력 |
| `git branch --show-current` | `codex/LLM-003-metadata-explanation` | 1 branch | Git 출력 |
| `git rev-parse --short HEAD` | `be7387f` | origin/main 병합 SHA | Git 출력 |
| `python scripts/new_implementation_note.py ...` | PASS | 노트 1개, INDEX 1행 | 이 파일과 INDEX |
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 저장소 문서 전체 | 명령 출력 |
| `pwsh -NoProfile -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | 미실행 — 이 Windows 환경에 `pwsh` 없음 | 0 | 명령 오류 |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS — 발견 없음 | 저장소 secret pattern | 명령 출력 |
| `git diff --check` | PASS | docs-only diff | Git 출력 |

### 미실행 검증과 이유

- API/Web/DB 테스트·빌드와 실제 provider call은 실행하지 않는다. 제품·계약·DB·prompt를
  변경하지 않은 설명 작업이며, actual 재호출 승인이 없기 때문이다.
- local DB SQL 조회·수정도 실행하지 않는다. 비밀값/DSN을 다루지 않고 data mutation
  승인 경계를 유지하기 위해 tracked schema와 기존 actual aggregate 증거만 검토했다.
- PowerShell 7 `pwsh`는 설치되지 않아 Windows PowerShell 5.1 `powershell.exe`로 동일한
  repository secret-pattern script를 실행했다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy:
  - `interaction_events` schema는 질문·답변·transcript·token·provider payload를
    저장하지 않는다. 이번 22행은 metadata-only이고 `masked_question=None`인 actual
    증거이므로 질문 원문 유출 사건으로 분류하지 않는다.
  - 개인정보가 없다는 사실이 `is_test` 오표시를 정당화하지는 않는다.
- Security:
  - secret/API key/DSN을 읽거나 출력하지 않았고 외부 시스템을 호출하지 않았다.
  - 이번 문제는 권한 침해나 official KB 변조가 아니라 data classification 문제다.
- Accessibility: 시민/관리자 UI 변경이 없어 영향 없음.
- Performance/cost:
  - 이번 작업의 외부 LLM 호출과 비용은 0이다.
  - 22행이 일반 집계에 포함되면 총 chat·SUCCESS·intent/source 사용량과 평균 latency가
    왜곡될 수 있다. answer mode(GENERATED/TEMPLATE)는 해당 table에 직접 저장되지 않으므로
    그 비율을 이 22행만으로 직접 왜곡하지는 않는다.

## 10. 데이터와 출처 영향

- 공식 데이터: ACTIVE KB, office, mapping, 19→20 승인 흐름 모두 변경 없음.
- mock/AI 생성: 새 mock·AI 출력 없음. 과거 22행은 local actual 평가의 metadata다.
- schema/lineage:
  - `interaction_events` 정의: `20260716000100_private_schema.sql`
  - event/failed-question insert 조건: `20260716000300_capabilities_and_functions.sql`
  - 현재 actual pre-write guard: `scripts/run_upstage_grounded_chat_actual.py`
- verified date: 2026-07-26 KST, 병합된 `be7387f` 기준.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- **지금 권고안:** Q-DB-CLEANUP-001=A. 22행을 건드리지 않고, 현재 local DB snapshot의
  event KPI를 권위 있는 지표로 사용하지 않은 채 개발을 계속한다.
- **clean KPI/정식 벤치마크 전 권고안:** 명시적으로 B를 승인해 local DB를 reset하고
  정식 seed와 필요한 관리자 승인 흐름을 재현한다.
- C/D는 정확한 request ID 목록 또는 검증 가능한 평가 marker를 확보하기 전에는 승인해도
  실행하지 않는 것이 안전하다.
- `PR #13 병합 승인`과 `A-049 사후 확인`은 과거 실행 결과의 수용과 코드 병합 승인이지,
  미래의 Upstage 실제 API 호출을 포괄 승인한 것이 아니다.
- future actual 1회는 masked fixture 10건을 외부 Upstage로 보내고, forced-timeout
  non-network probe를 포함해 11개의 `is_test=true` metadata event를 남길 수 있다.
  따라서 목적·fixture·최대 outbound call 수·비용 한도·환경을 정한 새 승인이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- runner는 현재 `replace(event, is_test=True)`를 사용하고, SUCCESS·`is_test=true`·
  `masked_question=None`·금지값 부재를 검증한 뒤에만 repository delegate를 호출한다.
- `request_id`는 UUID이지만 두 historical run의 정확한 ID 집합을 tracked aggregate
  evidence에 남기지 않았다. 따라서 UUID column의 존재만으로 선별 정리가 가능하지 않다.
- 현재 코드 검색에서는 운영 KPI aggregation consumer를 찾지 못했다. 위험은 즉시 노출된
  dashboard 오류라기보다, 나중에 raw `is_test=false` count를 정상 사용량으로 오해할 가능성이다.

## 13. 인수인계·재현·롤백

### 재현

- 위 관련 파일에서 다음을 확인한다.
  1. private schema의 metadata-only 주석과 `is_test` column
  2. DB function의 `failed_questions` insert 조건
  3. actual evidence의 `11 × 2 = 22`와 과거 오표시 기록
  4. runner의 현재 `is_test=true` pre-write guard
- cleanup 전에 정확한 대상 식별 가능성과 local mutable 상태 손실을 별도로 검토한다.

### 롤백

- 이번 작업은 구현 노트와 INDEX 변경만 revert하면 된다.
- DB를 변경하지 않았으므로 데이터 rollback은 없다.

### 다음 개발자 시작점

- 당장 기능 개발은 계속할 수 있다.
- KPI/benchmark를 만들기 시작할 때 Q-DB-CLEANUP-001을 다시 열고 A/B/C/D 중 인간 결정을
  기록한다. B라면 기존 정식 seed runbook을 따라 clean state를 재현한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 사용자가 A를 선택하면 known limitation을 유지하고 raw event KPI를 사용하지 않는다.
- 사용자가 B를 선택하면 reset 범위, 보존할 local evidence, 20번째 ACTIVE 재현 여부를
  확정한 뒤 별도 계획·승인·실행 노트를 만든다.
- future actual 재실행은 별도 승인이 생길 때까지 금지한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화 — 변경 없음 확인
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

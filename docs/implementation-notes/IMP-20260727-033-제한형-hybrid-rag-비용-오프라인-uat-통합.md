# IMP-20260727-033 — 제한형 Hybrid RAG 비용·오프라인 UAT 통합

- Date/Time (KST): 2026-07-27T23:18:35+09:00
- Task ID: CHAT-HYBRID-RAG-001-T7-T9
- Type: testing-integration
- Status: Done — local/offline; actual provider Task 10 Pending
- Author/Agent: 사용자 승인 / Codex main 통합 / gate·구현·독립 검토 에이전트
- Branch: `codex/CHAT-HYBRID-RAG-001`
- Base commit: `9b90919`
- Implementation commits: `d24893b`, `6f1cf90`, `945fc77`, `eb9c1d2`, `149dedf`, `9f377d4`
- Related: [plan](../superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md),
  [offline UAT](../test-reports/CHAT-HYBRID-RAG-001-OFFLINE-UAT.md),
  [integration](../test-reports/CHAT-HYBRID-RAG-001-INTEGRATION.md), D-099/D-102~D-104

## 1. 사용자 요청과 완료 기준

### 요청

local interactive AI 호출을 80/100/160과 VAT 포함 USD 0.20으로 제한하고, 사용자 제보 사례를
포함한 48문항 offline Hybrid RAG UAT와 영역 전체 gate를 통과시킨다.

### Acceptance Criteria

- classifier 80, generator 100, combined 160, concurrency 1, retry 0을 process 공유 ledger로 강제한다.
- 요청 전 최악 비용을 예약하고 USD 0.20을 넘길 호출은 transport 전에 막는다.
- 48 case/group/subset, official 57, sample 20, classifier 60을 skip 없이 검증한다.
- phone-shaped 일반 전입 질문은 마스킹 뒤 provider 0으로 성공하고 canonical 값은 유출하지 않는다.
- FOLLOWUP exact options/pending slot, negative coverage, provider/storage delta를 고정한다.
- API/Web/contracts/DB gate와 문서·버전 계보를 동기화한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 비용·actual 경계를 승인하고 Codex 구현자/reviewer/gate lane이 분리 검증했다. |
| When — 언제 | 2026-07-27 KST, Tasks 7~9 |
| Where — 어디서 | API LLM limits/settings/adapters, classifier runner, synthetic UAT, runbook, 전체 API/Web/DB gates |
| What — 무엇을 | shared metering, pre-reservation, negative coverage, independent 48-case UAT, release evidence |
| Why — 왜 | 긴 데모에서 숨은 재시도·비용 초과를 막고 실제 사용자 제보 회귀를 자동으로 잡기 위해서다. |
| How — 어떻게 | lock/semaphore/strict env, TDD, frozen fixture+독립 provider script, mutation review, parallel read-only gates |
| How much — 어느 정도 | cap 80/100/160, USD0.20, 48 scenarios, focused 91, API 2,356, Web 68, DB regression 345 |

## 3. 시작 전 상태

- historical actual profile은 20/30/40·USD0.05였고 local interactive 목표와 달랐다.
- usage maxima 검증과 parser 실패 시 실제 사용량 보존이 처음 구현에서 부족했다.
- classifier evaluator C-18 냉장고가 지원 KB로 강제 매핑되는 오염이 있었다.
- 최초 UAT fake가 fixture expected 값을 그대로 반환해 provider 경로가 순환 oracle이었다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-COST-001 | 인간 결정 | interactive cap/비용 | A: 80/100/160·USD0.20 | local profile |
| Q-DATA-RAG-001 | 인간 결정 | UAT/새 사실 경계 | synthetic만; official `.2` 불변 | data lineage |
| Runtime topic count | 데이터 권위 | metadata 20 vs `.2` 19 | offline runtime은 교집합 19 | UAT invariant |
| actual provider | 인간 승인됨/후속 gate | PII-free 20을 언제 실행할지 | offline·area gate 뒤 Task 10 | 비용/네트워크 |

## 5. 설계 결정과 대안

### 선택

하나의 non-resettable ledger와 semaphore가 classifier/generator 시도·실사용량·비용을 공유한다.
UAT fixture expected oracle와 fake provider script를 분리하고 server validation/storage를 실제
`ChatService`로 실행한다.

### 이유

병렬 호출에서도 lifetime cap이 우회되지 않고, fixture 기대값만 바꿔 테스트를 거짓 green으로
만들 수 없다.

### 고려했지만 선택하지 않은 대안

- 요청 뒤 비용 계산: stop line을 넘길 수 있어 제외.
- counter reset/hidden retry: 예산 우회이므로 제외.
- provider fake가 expected 값을 읽는 방식: 순환 검증이라 독립 reviewer가 반려.
- 냉장고를 일반 폐기물 KB로 강제: coverage exclusion과 충돌해 `NO_TOPIC_MATCH`로 교정.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/limits.py`, `settings.py` | strict caps, usage bounds, reservation/accounting | 비용·quota fail-close |
| `upstage_chat.py`, `upstage_classifier.py`, `local.py` | shared ledger/semaphore | combined lifetime cap |
| classifier evaluator/fixture | C-18 negative coverage와 실제 catalog adapter | 지원 범위 오염 방지 |
| `hybrid-rag-uat.v1.json` | 48 synthetic cases, exact oracle | 사용자 제보·경계 고정 |
| `test_hybrid_rag_uat.py` | independent script, real service/storage, leak/mutation/negative tests | 순환 oracle 제거 |
| UAT/integration reports·runbook | aggregate-only 결과와 actual gate | 재현·비밀 비노출 |

### 데이터 흐름/상태 변화

provider attempt 전 shared ledger가 cap·최악 비용을 예약하고, 응답 usage가 strict bound 안이면
실사용으로 정산한다. UAT는 real redaction→policy→catalog/retrieval→server validation→grounding→
response→recording repository를 offline fake transport로 통과한다.

### 오류·빈 상태·롤백

cap/timeout/invalid usage/JSON은 transport 추가 시도와 시민 text 저장 없이 FOLLOWUP으로 닫는다.
rollback은 Tasks 7~8 commits를 역순 revert한다. DB/official-data rollback은 없다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.11.1-classifier-runtime` | `0.12.0-bounded-hybrid-rag` | bounded runtime |
| Web | `0.7.0-natural-dialogue` | `0.8.0-guided-chat` | 동일 release UX |
| API/shared/DB/data | 기존 | 동일 | 공개/DB/data 변경 0 |
| Prompt set | `0.3.1-hybrid-classifier` | `0.4.0-topic-coverage` | catalog selector |
| Test suite | `1.9.2-classifier-runtime` | `2.0.0-bounded-hybrid-rag` | 48-case/area gates |
| Docs | `2.26.1` | `2.27.0` | runbook/report/notes |

## 8. 명령과 테스트 증거

| 명령/검증 | 실제 결과 | 시간/개수 |
|---|---|---|
| Task 7 evaluator runner | 13 PASS | scoped |
| Task 7 focused regression | 527 PASS | scoped |
| Task 7 API+runner | 2,313 PASS, DB-only 8 skip | task closeout |
| Task 8 focused acceptance | 91 PASS, skip 0 | UAT 48/48, official 57/57, sample 20/20, classifier 60/60 |
| `pytest apps/api/tests -q` | 2,356 PASS, 8 skip, warning 1, subtests 5 | 27.38s |
| Ruff / Mypy API | PASS / 57 files PASS | 0.569s / 1.573s |
| DB/admin/tooling pytest | 345 PASS, 8 skip, warning 1, subtests 47 | 145.65s rerun |
| shared generate/test | drift 0 / 96 PASS | PASS |
| Web lint/typecheck/test/build | PASS / PASS / 68 PASS / PASS | build warning 1 |
| secret scan / diff check | PASS | Task 7/8 and integration |

DB regression의 첫 동일 명령은 wrapper timeout 124.1초로 pytest 결과를 내지 못했다. 코드·환경
변경 없이 timeout만 늘린 재실행이 145.65초에 PASS했다. 8 skip은 모두 local DB gate 조건이며,
warning은 기존 Starlette/httpx TestClient deprecation이다. Web build warning 1건은 Next.js
workspace-root 자동 추론이며 build failure가 아니다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: privacy case text는 report에 없고 canonical phone은 provider/repository/response/report 0이다.
- Security: invalid usage/ID/coverage/intent와 budget 초과는 transport/저장 없이 닫힌다.
- Accessibility: Task 6 Web gate와 390/430/desktop E2E가 통과했다.
- Performance/cost: actual 비용은 Task 10 전 Pending; 이 단계의 provider/network 호출은 0이다.

## 10. 데이터와 출처 영향

- official `.2`, DB schema/rows, seed, migration, rollback 변경 0.
- `hybrid-rag-uat.v1.json`은 `SYNTHETIC_CHAT_UAT`이며 공식 데이터가 아니다.
- report는 case ID와 aggregate만 기록하고 privacy 질문/provider payload를 복사하지 않는다.
- verified date: 2026-07-27.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- offline green은 실제 Upstage 품질·비용 PASS가 아니다. Task 10 한정 actual 결과를 별도 본다.
- public/remote, DB reset/seed, official data 승격, 자동 merge는 실행하지 않았다.
- local DB의 별도 20번째 ACTIVE와 immutable `.2` tracked 19를 혼동하면 안 된다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- worst-case reservation 뒤 strict usage로 정산하고 parser 실패 시 이미 검증된 usage를 보존한다.
- UAT same-intent valid topic은 provider semantic 책임이며 독립 script와 expected oracle의 불일치가
  이를 잡는다. 서버는 intent/coverage/external ID mismatch를 별도로 거부한다.

## 13. 인수인계·재현·롤백

### 재현

[offline UAT](../test-reports/CHAT-HYBRID-RAG-001-OFFLINE-UAT.md) 명령과
[integration](../test-reports/CHAT-HYBRID-RAG-001-INTEGRATION.md)의 API/Web/DB 명령을 실행한다.

### 롤백

최신 후속 문서 정합성 수정 commit을 먼저 revert하고, Task 9 문서·버전 통합 commit
`096dd20`을 revert한 다음, base `9b90919` 다음의 `d24893b`부터 `9f377d4`까지를 포함한
`9b90919..9f377d4`를 최신 commit부터 역순으로 revert한다. 환경의 cap 값은
`.env.example`/runbook과 함께 되돌린다. DB/data 복구는 필요 없다.

### 다음 개발자 시작점

Task 10 runner의 allowlist·PII-free·pre-reservation·aggregate-only report RED를 먼저 확인한다.

## 14. 남은 위험·미해결 질문·다음 단계

- Task 10: 승인된 PII-free 20-case actual selector run.
- Task 11: final full/root/security/E2E, 독립 review, push와 Draft PR.
- warning 2종은 선행 부채이며 기능 실패는 아니지만 후속 dependency maintenance에서 제거한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

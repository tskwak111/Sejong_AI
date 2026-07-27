# IMP-20260727-031 — 제한형 Hybrid RAG 카탈로그·선택기 구현

- Date/Time (KST): 2026-07-27T23:18:35+09:00
- Task ID: CHAT-HYBRID-RAG-001-T1-T4
- Type: implementation-backend
- Status: Done
- Author/Agent: 사용자 승인 / Codex main 통합 / task별 구현·독립 검토 에이전트
- Branch: `codex/CHAT-HYBRID-RAG-001`
- Base commit: `e7fb3cc` (승인 계획)
- Implementation commits: `4efc516`, `6f2638d`, `23e8436`, `700fa65`, `5b5831c`,
  `1dc5ad5`, `f55c84a`, `a7bd32c`, `2a443b6`, `bce7864`, `b32ec61`
- Related: [plan](../superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md),
  [RFP matrix](../source-of-truth/RFP_MATRIX.md), D-096/D-100~D-104

## 1. 사용자 요청과 완료 기준

### 요청

승인된 ACTIVE/OFFICIAL 지식만 사용하는 제한형 Hybrid RAG로 일상어 질문을 정확한 단일
topic에 연결하고, 의미 근거가 없거나 잘못된 provider 제안은 성공시키지 않는다.

### Acceptance Criteria

- versioned metadata 20건과 request-local ACTIVE/OFFICIAL snapshot의 교집합만 검색한다.
- provider 출력은 closed route/intent/topic/coverage/pending-slot이며 서버가 다시 검증한다.
- exact approved example, unique lexical, validated semantic coverage, validated context facet 중
  typed evidence가 있어야 한 KB를 사용한다.
- invalid/ambiguous/provider 장애는 route별 FOLLOWUP/FALLBACK으로 닫고 출처는 서버가 결합한다.
- 원문·비밀·provider payload·공식 사실을 catalog/prompt/log에 추가하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 명세·계획을 승인하고 Codex 구현자와 별도 reviewer가 task마다 구현·검토했다. |
| When — 언제 | 2026-07-27 KST, 승인 계획 `e7fb3cc` 뒤 Tasks 1~4와 evaluator 교정을 수행했다. |
| Where — 어디서 | `apps/api` chat/llm/local, `data/retrieval`, API tests, 승인 plan |
| What — 무엇을 | governed topic catalog, closed selector, typed grounding, request-local orchestration |
| Why — 왜 | 동의어·일상어는 찾되 KB 밖 사실·임의 첫 record·모델 생성 출처는 차단하기 위해서다. |
| How — 어떻게 | TDD, immutable dataclass/enum, ACTIVE projection, exact membership 검증, 독립 review/fix loop |
| How much — 어느 정도 | metadata 20, current immutable `.2` runtime intersection 19, top-1 KB, 요청당 selector 최대 1회 |

## 3. 시작 전 상태

- 관련 파일: 기존 `classification.py`, `retrieval.py`, `grounding.py`, `service.py`,
  Upstage classifier와 official/sample evaluator.
- 기존 동작: 고정 intent와 lexical 검색은 있었지만 provider가 topic/coverage를 제안하거나
  grounding 근거를 typed object로 전달하지 않았다.
- 발견한 충돌/부채: object-per-topic JSON은 실제 20개 catalog+1,024자 질문에서 보수적
  4,096 입력 상한을 넘었다. evaluator가 caller-controlled expected topic을 신뢰할 위험도 있었다.
- Git 상태: 승인 계획 commit 기준 clean branch에서 시작했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-RAG-001 | 인간 결정 | 검색 구조 | A: allowlisted Hybrid RAG | API 내부 선택 경로 |
| Q-DATA-RAG-001 | 인간 결정 | 새 공식 사실 추가 여부 | A: 기존 사실 우선, metadata/UAT만 추가 | official `.2` 불변 |
| Task 2 bound | 내부 구현 | 20 topic prompt가 4,096 초과 | 동일 6 field의 columnar header+rows | 내부 prompt만 변경 |
| Runtime count | 데이터 권위 | metadata 20 vs immutable `.2` 19 | 교집합 19를 실제 offline 기준으로 사용 | 누락 topic을 만들지 않음 |

## 5. 설계 결정과 대안

### 선택

`KnowledgeRecord`의 ACTIVE/OFFICIAL projection과 non-factual coverage metadata를 결합한
`TopicCatalog`, closed `ClassifierDecision`, `GroundingEvidence`/`TopicSelection`을 사용한다.

### 이유

모델에게 사실·출처·기관·저장 권한을 주지 않으면서 paraphrase 의미 선택만 제한적으로
사용할 수 있고, 모든 성공이 현재 ACTIVE record까지 추적된다.

### 고려했지만 선택하지 않은 대안

- vector DB/embedding: 새 의존성·비용·데이터 경계가 커서 제외.
- catalog 절단/샘플링: 시민마다 숨겨지는 KB가 달라져 제외.
- bare record/boolean grounding 호환 overload: caller가 근거를 우회할 수 있어 제외.
- 같은 intent에서 첫 record 선택: 근거 없는 성공이므로 제외.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `data/retrieval/topic-coverage.v1.json` | 20 topic의 coverage ID/label | 사실이 아닌 검색 경계 버전 관리 |
| `chat/topic_catalog.py` | strict loader와 ACTIVE/OFFICIAL 교집합 | inactive/mock 검색 차단 |
| `llm/classifier_*`, `upstage_classifier.py` | closed parser, catalog 입력, 4,096 gate | free text·외부 ID·초과 입력 차단 |
| `chat/retrieval.py`, `grounding.py` | typed selection/evidence | 임의 top-1 방지 |
| `chat/service.py`, `response.py`, `local.py` | 정확한 결정 순서와 route별 fail-close | provider/storage/source 권한 분리 |
| evaluator/official/sample tests | canonical fingerprint와 typed selection | expected topic 조작·호환 우회 차단 |

### 데이터 흐름/상태 변화

`redaction → policy gate → deterministic route → ACTIVE snapshot/catalog → exact/unique/context
selection 또는 provider closed selection → server validation → typed grounding → one-record
response → route-specific persistence` 순서다.

### 오류·빈 상태·롤백

catalog 0/21+, prompt 초과, timeout, invalid JSON/ID/coverage는 transport 또는 성공 없이 안전
FOLLOWUP으로 닫는다. 구현 rollback은 위 commit들을 역순 revert하며 metadata 파일과 loader를
함께 되돌린다. DB/data migration은 없다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.11.1-classifier-runtime` | `0.12.0-bounded-hybrid-rag` | catalog/selector/orchestration |
| Web | `0.7.0-natural-dialogue` | `0.8.0-guided-chat` | Task 6와 묶은 release |
| API | `4.0.0-draft` | 동일 | 공개 shape 비파괴 |
| Shared contracts | `1.0.0` | 동일 | 기존 `string[]` behavior 안의 값 정렬 |
| DB schema | `0.5.0-local` | 동일 | migration 0 |
| Official data | `0.1.0-initial.2` | 동일 | byte 변경 0 |
| Mock data | `0.0.0-not-populated` | 동일 | mock 추가 0 |
| Prompt set | `0.3.1-hybrid-classifier` | `0.4.0-topic-coverage` | topic/coverage closed prompt |
| Test suite | `1.9.2-classifier-runtime` | `2.0.0-bounded-hybrid-rag` | typed/UAT acceptance |
| Docs | `2.26.1` | `2.27.0` | 구현·검증 계보 |

## 8. 명령과 테스트 증거

| 명령/검증 | 실제 결과 | 증거 |
|---|---|---|
| Task 3 typed grounding focused pytest | 20 PASS | task progress ledger |
| Task 4 service/evaluator focused pytest | 219 PASS | task review/report |
| Task 4 API area subset | 1,513 PASS | task review/report |
| evaluator remediation focused/LLM | 60 / 310 PASS | `b32ec61` review |
| evaluator remediation whole API | 2,249 PASS, DB-only 8 skip | task review/report |
| Ruff/Mypy for touched API modules | PASS | task별 implementer/reviewer reports |

Task 9의 fresh whole-area 결과는
[integration report](../test-reports/CHAT-HYBRID-RAG-001-INTEGRATION.md)에 별도 기록한다.
실제 provider/network/DB reset·seed는 이 노트 범위에서 실행하지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: `SafeQuestion`만 selector로 전달하며 policy/PII gate 전 outbound는 0이다.
- Security: catalog 밖 ID, intent/coverage mismatch, 0/21+ catalog, oversized prompt는 fail-close다.
- Accessibility: backend slice 자체 UI 변화 없음.
- Performance/cost: catalog는 요청 단위 최대 20, top-1만 사용하며 4,096 입력 상한을 지킨다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2` bytes와 release version 불변.
- mock/AI 생성: topic metadata는 비사실 검색 descriptor, UAT는 명시적 synthetic.
- schema/lineage: DB schema/seed/official lineage 변경 0.
- verified date: 2026-07-27; `.2` runtime ACTIVE/OFFICIAL 19를 확인했다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- catalog metadata 20은 공식 KB 20건을 새로 승인했다는 뜻이 아니다. tracked `.2` 교집합은 19다.
- 실제 Upstage 20-case 비용/품질 증거와 public/remote 운영은 후속 gate다.
- 새 official fact/20번째 release 반영은 PM 승인·새 immutable release가 별도 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- prompt의 six-column rows는 반복 JSON key를 제거하는 내부 직렬화이며 공개 계약이 아니다.
- catalog fingerprint와 typed factories는 test caller가 expected topic을 주입하지 못하게 한다.

## 13. 인수인계·재현·롤백

### 재현

API 가상환경에서 chat/llm tests, Ruff, Mypy를 실행하고
`data/retrieval/topic-coverage.v1.json`과 official `.2` projection의 교집합을 확인한다.

### 롤백

위 `Implementation commits`의 명시 목록
`4efc516`, `6f2638d`, `23e8436`, `700fa65`, `5b5831c`, `1dc5ad5`, `f55c84a`,
`a7bd32c`, `2a443b6`, `bce7864`, `b32ec61`만 역순으로 revert한다. 중간에 섞인 다른
Task의 commit을 range로 함께 되돌리지 않는다. DB rollback·data restore는 필요 없다.

### 다음 개발자 시작점

`topic_catalog.py` → `classifier_prompt.py` → `service.py` → `grounding.py` 순서로 읽고
ADR-0027의 서버 권한 경계를 유지한다.

## 14. 남은 위험·미해결 질문·다음 단계

- PII-free actual provider 20-case는 Task 10에서만 실행한다.
- same-intent의 catalog-valid semantic topic 선택은 provider 책임이며 UAT 독립 oracle이 감시한다.
- public/remote rate limit·provider 운영은 미승인이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

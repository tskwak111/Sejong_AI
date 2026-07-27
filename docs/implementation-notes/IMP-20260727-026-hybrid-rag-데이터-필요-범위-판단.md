# IMP-20260727-026 — Hybrid RAG 데이터 필요 범위 판단

- Date/Time (KST): 2026-07-27T14:58:01+09:00
- Task ID: Q-DATA-RAG-001
- Type: discovery-decision
- Status: Done — Q-DATA-RAG-001=A confirmed
- Author/Agent: Codex
- Branch: codex/LOCAL-RUN-GUIDE-001
- Base commit: 940d1df
- Related plan/ADR/RFP: D-096~D-099, A-068, ADR-0015/0025,
  DATA-SEED-002, IMP-20260727-021

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 제한형 Hybrid RAG 구현 전에 현재 데이터가 더 필요한지 확인해 달라고 요청했다.

### Acceptance Criteria

- 공식 행정 사실, 검색 metadata, 평가 fixture를 구분한다.
- 현재 19→20 ACTIVE 범위에서 가능한 것과 불가능한 것을 구분한다.
- 새 공식 사실을 mock·추측으로 채우지 않는다.
- 구현 전 데이터 범위 결정을 한 번에 하나만 질문한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자/PM이 데이터 범위를 결정, Codex가 current release 감사 |
| When — 언제 | 2026-07-27 KST |
| Where — 어디서 | immutable `.2` official KB, local governed 20th, classifier/retrieval |
| What — 무엇을 | 추가 official facts와 retrieval/test metadata 필요성 판단 |
| Why — 왜 | 검색 recall 부족을 데이터 부족과 알고리즘 부족으로 혼동하지 않기 위해 |
| How — 어떻게 | 19 records·57 approved examples·보고 질문과 coverage 대조 |
| How much — 어느 정도 | tracked facts 19, local ACTIVE 20th 별도, 새 data write/provider/DB 0 |

## 3. 시작 전 상태

- 관련 파일: `data/official/releases/0.1.0-initial.2/kb_records.json`,
  classifier 60 fixture, retrieval/grounding, DATA-SEED docs
- 기존 동작: tracked `.2`는 19 records, 각 record 3 approved examples로 총 57개다.
- 발견한 충돌/부채:
  - 일반 절차 사실은 있으나 open paraphrase용 versioned topic descriptor/alias corpus가 없다.
  - 냉장고의 별도 폐가전 수거, 재산세 부과·기한 상세처럼 기존 KB가 보증하지 않는 사실이 있다.
  - 가족관계증명서 등은 의도적으로 현재 네 분야 밖이다.
- Git 상태: main `940d1df`; 격리 branch 문서만 변경.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-DATA-RAG-001 | B/High | 새 official KB를 먼저 추가할지 | A 확정: 기존 facts로 검색 구조 먼저, metadata/test만 추가 | data lineage·일정·PM review |

## 5. 설계 결정과 대안

### 권고안 A

현재 20 ACTIVE facts로 네 분야의 일반 절차·증명서·변경/환불·세금 납부/증명은 충분하다.
먼저 다음 비사실성 자료만 versioned code/test artifact로 추가한다.

- topic descriptor: public ID, intent, service name, approved examples와 coverage label
- synthetic UAT corpus: 사용자가 보고한 비식별 paraphrase와 expected topic/fallback
- negative coverage: 냉장고 품목별 제도·재산세 상세처럼 현재 KB가 답하면 안 되는 경계

### 이유

검색 실패 대부분은 사실 부족이 아니라 classifier 뒤 lexical topic selection 실패다. 새 KB를
먼저 늘리면 결함 표면과 승인 부담만 커진다.

### 고려했지만 선택하지 않은 대안

- 새 official KB를 먼저 추가: 냉장고·재산세 상세 답변은 늘지만 Hybrid retrieval 결함은 남는다.
- 기존 KB에 임의 alias를 직접 추가: immutable `.2`와 PM 승인 lineage를 깨뜨린다.
- 모델 지식으로 보충: 공식 KB 근거 원칙을 위반한다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| Ambiguity register | A-068 Pending | 데이터 범위 결정 대기 |
| IMP-026/INDEX | 감사·권고 기록 | 요청별 인수인계 |

### 데이터 흐름/상태 변화

DB/official release/seed 변경 0. 향후 metadata는 행정 사실이 아니라 retrieval/test artifact이며
공식 KB와 명확히 분리한다.

### 오류·빈 상태·롤백

새 사실 근거가 없는 질문은 `INSUFFICIENT_GROUNDING` 또는 정확한 FOLLOWUP으로 닫는다.
문서만 추가했으므로 롤백은 A-068/IMP-026/INDEX를 되돌린다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.9
- application: 0.11.1-classifier-runtime
- web: 0.7.0-natural-dialogue
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.3.1-hybrid-classifier
- test_suite: 1.9.2-classifier-runtime
- documentation: 2.25.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.11.1-classifier-runtime | 동일 | 코드 없음 |
| Web | 0.7.0-natural-dialogue | 동일 | UI 없음 |
| API | 4.0.0-draft | 동일 | 계약 없음 |
| DB schema | 0.5.0-local | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 + local 20th | 동일 | write 없음 |
| Mock data | 0.0.0-not-populated | 동일 | mock 없음 |
| Prompt set | 0.3.1-hybrid-classifier | 동일 | prompt 없음 |
| Test suite | 1.9.2-classifier-runtime | 동일 | fixture 미추가 |
| Docs | 2.25.1 | 동일 | note only |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| immutable `.2` record/service/example count | PASS, 19 records·57 examples | read-only | terminal |
| waste/tax coverage 대조 | PASS | 9 records | terminal |
| `apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1 | terminal |
| `git diff --check` | PASS — whitespace error 0 (INDEX LF 변환 경고만 발생) | 1 | terminal |

### 미실행 검증과 이유

새 official fact source 검증·web search·PM review는 Q-DATA-RAG-001에서 B를 선택할 때 별도
DATA cycle로 수행한다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: synthetic UAT 질문만 사용하며 실제 개인정보 없음.
- Security: 모델 일반지식을 공식 사실 대체로 사용하지 않는다.
- Accessibility: 영향 없음.
- Performance/cost: provider call 0. catalog metadata는 최대 20 topics로 bounded 설계한다.

## 10. 데이터와 출처 영향

- 공식 데이터: tracked `.2` read-only, local 20th mutation 0.
- mock/AI 생성: 새 사실 0. future UAT fixture는 synthetic으로 명시.
- schema/lineage: immutable release 유지.
- verified date: 기존 record 값 유지.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 facts만으로 Hybrid RAG 구조 교정은 가능하다.
- 냉장고 별도 수거·품목 수수료, 재산세 상세 facts를 정확히 답하려면 후속 official KB가 필요하다.
- 가족관계증명서 등 범위 확대는 별도 제품·data 승인이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- topic descriptor의 파일 분리·validation helper는 후속 계획에서 정한다.

## 13. 인수인계·재현·롤백

### 재현

immutable `.2`의 19 records/57 examples와 IMP-021의 9개 rank/grounding 결과를 대조한다.

### 롤백

문서 변경만 역순으로 되돌린다.

### 다음 개발자 시작점

Q-DATA-RAG-001을 확정한 뒤 설계 1부의 catalog source와 coverage negative를 명시한다.
## 14. 남은 위험·미해결 질문·다음 단계

- Q-DATA-RAG-001은 사용자 답변 `A`로 해결됐다.
- 새 official factual KB 후보의 정확한 출처·검수·release version은 아직 조사하지 않았다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 변경 없음
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

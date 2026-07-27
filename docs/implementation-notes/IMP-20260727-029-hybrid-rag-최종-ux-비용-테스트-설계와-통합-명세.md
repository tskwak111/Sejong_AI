# IMP-20260727-029 — Hybrid RAG 최종 UX·비용·테스트 설계와 통합 명세

- Date/Time (KST): 2026-07-27T15:37:13+09:00
- Task ID: CHAT-HYBRID-RAG-DESIGN-SECTION-3
- Type: decision-design-spec
- Status: Decision-only Done — written specification Review
- Author/Agent: Codex
- Branch: codex/LOCAL-RUN-GUIDE-001
- Base commit: 940d1df
- Related plan/ADR/RFP: D-096~D-102, A-053/A-060/A-064~A-068,
  ADR-0025/0027, CHAT-NATURAL-001

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 제한형 Hybrid RAG 설계 3부를 승인했다.

### Acceptance Criteria

- 지역, 분야별 FOLLOWUP, 오류 문구, provider budget, 테스트와 구현 순서를 확정한다.
- 설계 1~3부를 한 written specification과 ADR로 통합한다.
- source-of-truth, 결정 로그, ambiguity, version, changelog, INDEX를 동기화한다.
- placeholder·모순·범위 확장·개인정보 위험을 자체 검토한다.
- 제품 코드·DB·official data·provider actual은 변경하거나 실행하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자/PM 설계 승인, Codex 통합 명세·ADR 작성 |
| When — 언제 | 2026-07-27 KST |
| Where — 어디서 | source-of-truth, ADR, spec, version/changelog, decision evidence |
| What — 무엇을 | bounded Hybrid RAG architecture·UX·cost·test final design |
| Why — 왜 | 실측 UAT 검색 실패와 반복 FOLLOWUP을 안전하게 교정하기 위해 |
| How — 어떻게 | approved sections 통합, source/code 대조, self-review, docs gate |
| How much — 어느 정도 | docs-only, runtime/DB/data/provider mutation 0 |

## 3. 시작 전 상태

- 관련 파일: current CHAT-NATURAL spec, ADR-0025, retrieval/grounding/classifier/context/Web,
  decision/ambiguity/version docs
- 기존 동작: privacy-first hybrid classifier와 lexical ACTIVE grounding은 구현됐지만
  runtime coverage catalog와 semantic grounding evidence, revised UX/cap은 없다.
- 발견한 충돌/부채:
  - current natural-dialogue spec의 certificate 5 options는 D-098/D-102 target보다 오래됐다.
  - current 20/30/40·USD0.05는 historical actual profile이며 new local interactive target과 다르다.
  - ADR README에 existing 0026 entry가 누락돼 있었다.
- Git 상태: isolated docs worktree, base `940d1df`; product code change 0.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-RAG-001 | A/Blocker | retrieval strategy | A 확정 | bounded topic catalog |
| Q-DATA-RAG-001 | B/High | official KB 선행 여부 | A 확정 | metadata/UAT only |
| Q-UX-REGION-001 | B/High | region lifetime | A 확정 | same-tab React memory |
| Q-UX-CERT-001 | B/High | certificate hierarchy | A 확정 | first 3 options |
| Q-COST-001 | A/Blocker | local demo cap | A 확정 | 80/100/160·USD0.20 |
| Written spec review | Review gate | 문서 표현·exact target | 사용자 검토 대기 | plan 전 gate |

## 5. 설계 결정과 대안

### 선택

- current ACTIVE/OFFICIAL projection과 non-factual coverage metadata의 최대 20 topic catalog
- deterministic exact/unique/context fast path와 ambiguous-only Upstage semantic selector
- closed `topic_id+coverage_id`, server revalidation, typed grounding evidence, top-1 KB
- generic intent별 bounded FOLLOWUP, certificate first 3, always-visible same-tab region
- classifier 80/generator 100/combined 160, USD0.20 pre-reservation stop
- 57 official example + 60 frozen classifier + 48 new synthetic UAT + actual PII-free 20 subset

### 이유

현재 20 topic 규모에서 자연어 recall을 높이면서 공식 사실과 출처 권한을 서버에 유지하는
가장 작은 변경이다.

### 고려했지만 선택하지 않은 대안

- lexical alias만 추가: 새 표현마다 결함 반복
- vector/embedding: 현재 규모에 과도한 dependency/index lifecycle
- LLM answer/source authority: hallucination·승인 경계 위반
- 새 factual KB 선행: retrieval 결함을 남긴 채 일정·검수 증가
- multi-KB 합성: 절차·수수료·출처 충돌 위험

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| integrated spec | 설계 1~3부와 self-review | 다음 plan의 단일 권위 |
| ADR-0027/ADR README | 장기 architecture와 index | trade-off 기록 |
| source-of-truth 2 files | 현재 제품·provider/data 경계 | 중복 문서 충돌 방지 |
| decision/ambiguity | D-102, A-053/A-060/A-064~067 | 인간 승인 추적 |
| version/changelog | documentation 2.26.0 | 문서 minor release |
| IMP-029/INDEX | 6W1H·검증·인수인계 | 요청별 의무 |

### 데이터 흐름/상태 변화

설계 문서만 바뀌었다. official `.2`, local DB rows, API request/response, provider counter와
secret은 변경하지 않았다.

### 오류·빈 상태·롤백

문서 롤백은 documentation 2.26.0 관련 spec/ADR/SOT/decision/version/changelog/note/index
변경을 역순으로 되돌린다. DB/data/provider rollback은 없다.

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
| Application | 0.11.1 | 동일 | code 없음 |
| Web | 0.7.0 | 동일 | UI 미구현 |
| API | 4.0.0-draft | 동일 | wire 변경 없음 |
| DB schema | 0.5.0-local | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 + local 20th | 동일 | fact write 없음 |
| Mock data | 0.0.0 | 동일 | mock 없음 |
| Prompt set | 0.3.1 | 동일 | prompt 미구현 |
| Test suite | 1.9.2 | 동일 | fixture 미구현 |
| Docs | 2.25.1 | 2.26.0 | integrated spec/ADR/SOT |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| spec placeholder/consistency/scope/ambiguity self-review | PASS | 6 checks | spec section 19 |
| `apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1 | terminal |
| `git diff --check` | PASS — whitespace error 0 (INDEX LF 변환 경고만 발생) | 1 | terminal |
| changed-doc path review | PASS | spec/ADR/note 3 | terminal |
| placeholder scan | PASS | spec/ADR/note | terminal |
| `powershell.exe ... scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS — exit 0, finding output 0 | tracked/current tree | terminal |
| design doc local commit | 실행 예정 | 1 | Git |

### 미실행 검증과 이유

제품 코드·DB·data·provider가 바뀌지 않아 API/Web/DB/actual provider test는 실행하지 않는다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: raw 질문 저장 금지와 provider 전 redaction을 유지한다.
- Security: model topic은 server revalidation 전 권위가 아니다.
- Accessibility: target region/followup UI는 keyboard/focus/44px/4.5:1을 명세한다.
- Performance/cost: target 80/100/160·USD0.20은 아직 구현 전이며 historical evidence와 분리한다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2` bytes와 local 20th row 변화 0.
- mock/AI 생성: 향후 48 UAT는 non-factual synthetic 표시를 강제한다.
- schema/lineage: DB/data lineage 변화 0.
- verified date: 기존 KB 값을 변경하지 않는다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- written specification review가 다음 gate다.
- 새 factual KB가 없어 냉장고·재산세 세부는 당분간 근거 부족이다.
- local ambiguous 질문은 redaction 뒤 Upstage로 전송될 수 있다.
- public response field는 유지하지만 followup option 동작이 바뀐다.
- 실제 구현·actual provider는 별도 계획 승인 뒤다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- helper split, typed evidence, metadata validator, fixture layout, component split은 후속 계획에서
  exact file/task로 고정한다.

## 13. 인수인계·재현·롤백

### 재현

spec의 D-096~D-102 authority와 current retrieval/grounding/classifier/settings/response/Web source를
대조하고 docs checker와 `git diff --check`를 실행한다.

### 롤백

documentation 2.26.0 docs-only diff를 revert한다. runtime/DB/data 복구는 필요 없다.

### 다음 개발자 시작점

사용자가 written spec을 승인하면 `superpowers:writing-plans`로 Slice 1~5의 RED/GREEN exact plan을
작성한다.

## 14. 남은 위험·미해결 질문·다음 단계

- written specification은 Review다.
- actual provider의 semantic topic accuracy와 USD0.20 cost stop은 구현/actual test 전 미검증이다.
- public/remote target은 여전히 미구성 상태이며 이번 범위가 아니다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

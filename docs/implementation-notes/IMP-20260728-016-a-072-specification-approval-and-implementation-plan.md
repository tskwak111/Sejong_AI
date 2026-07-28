# IMP-20260728-016 — A-072 specification approval and implementation plan

- Date/Time (KST): 2026-07-28T21:41:57+09:00
- Task ID: A-072-CLASSIFIER-EXACT-KEY-CORRECTION
- Type: decision-plan
- Status: Decision-only
- Author/Agent: 사용자 승인자 / Codex plan author
- Branch: main
- Base commit: dc69b68
- Related plan/ADR/RFP: D-112~D-115, ADR-0025/0027, A-072 approved spec/TDD plan

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 A-072 integrated written specification에 대해 `명세 승인`이라고 명시했다.

### Acceptance Criteria

- written specification을 Approved로 전환하고 D-115로 기록한다.
- 제품 코드를 건드리기 전에 파일·interface·RED/GREEN·명령·commit 단위 plan을 작성한다.
- 새 dependency/API/DB/data 변경과 provider actual을 plan 승인 범위에 섞지 않는다.
- plan의 spec coverage, placeholder와 type/signature 일관성을 자체 검토한다.
- 사용자에게 Subagent-Driven과 Inline 실행 선택지를 제공한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 명세를 승인하고 Codex가 D-115와 exact TDD plan을 작성했다. |
| When — 언제 | 2026-07-28 21:41 KST |
| Where — 어디서 | approved spec, plan, decisions/SOT/ambiguity/TASKS/version/implementation note |
| What — 무엇을 | Tasks 1~5 offline 구현 계획과 별도 Task 6 actual gate를 분리했다. |
| Why — 왜 | exact-key 교정을 regression 없이 구현하고 actual을 clean-source 뒤 별도 통제하기 위해서다. |
| How — 어떻게 | contract parser→prompt→transport schema→area/version→root/clean-source 순의 RED/GREEN 계획이다. |
| How much — 어느 정도 | 문서·메타만 변경, product code/provider call/API/DB/data/dependency 0, 비용 USD 0 |

## 3. 시작 전 상태

- approved spec base: `dc69b68`.
- current runtime: `json_object`, shorthand prompt, canonical JSON-null parser.
- target runtime: strict five-key schema, provider-only `NONE`, shared closed validation.
- current actual: D-111 `KEY_SET_REJECTED` 9/9, retry 0, no rerun.
- Git 상태: 시작 시 tracked worktree clean.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-115 | A / Blocker | written spec 구현 권위 | Approved | plan 작성 가능 |
| execution mode | B / High | Subagent-Driven 또는 Inline | 사용자 선택 대기 | 작업 orchestration |
| Task 6 actual | A / Blocker | clean-source 뒤 exact one-call | plan 승인과 분리 | provider cost/evidence |

## 5. 설계 결정과 대안

### 선택

- Tasks 1~3은 parser, prompt, transport의 독립 RED/GREEN과 commit이다.
- Task 4는 area regression과 approved version/document integration이다.
- Task 5는 root gate, independent spec review와 clean source actual decision gate다.
- Task 6은 별도 exact 인간 승인 전 절대 실행하지 않는다.

### 이유

각 task는 reviewer가 독립적으로 거절·승인할 수 있고, shared parser/transport 통합은 main agent가
소유할 수 있다. 실제 provider call을 offline 구현 승인과 분리해 비용·증거 재실행 위험을 막는다.

### 고려했지만 선택하지 않은 대안

- 한 commit에 parser/prompt/transport를 모두 변경: 실패 원인과 review 경계가 섞여 기각.
- plan 승인으로 actual까지 실행: D-111 evidence와 인간 provider gate를 훼손해 기각.
- 새 wire module/production dependency: 현재 세 파일 범위에 과도해 기각.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| A-072 plan | 6 tasks, exact interfaces/commands/stop gates | zero-context 실행 가능 |
| approved spec | Status Approved | 사용자 권위 반영 |
| decisions/SOT/tasks | D-115/Plan Review | 구현 전 gate |
| version/changelog | docs 2.30.1 | plan checkpoint |
| product/API/DB/data | 변경 0 | plan approval 전 |

### 데이터 흐름/상태 변화

runtime 상태 변화는 없다. 계획만
`wire parser → prompt → schema transport → area/root → separate actual` 순으로 고정했다.

### 오류·빈 상태·롤백

계획 자체는 문서-only다. Task 1~5 실패 시 해당 task commit 전 수정하거나 마지막 독립 commit을
revert한다. Task 6 실패는 FAIL evidence를 보존하고 재실행하지 않는다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.2-response-stage-diagnostics | unchanged | plan-only |
| Web | 0.8.0-guided-chat | unchanged | UI 0 |
| API | 4.0.0-draft | unchanged | public contract 0 |
| DB schema | 0.5.0-local | unchanged | migration/DB 0 |
| Official data | 0.1.0-initial.2 | unchanged | official data 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 0 |
| Prompt set | 0.4.1-json-mode-instruction | unchanged | implementation 전 |
| Test suite | 2.1.5-response-stage-diagnostics | unchanged | implementation 전 |
| Docs | 2.30.0 | 2.30.1 | spec approval/plan Review |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| plan placeholder scan | PASS — prohibited placeholder 0 | plan 1개 | A-072 plan |
| plan spec/type coverage review | PASS — spec 8축/Tasks 1~6 연결, signature 일치 | 1회 | A-072 plan self-review |
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1회 | stdout |
| secret-pattern scan | PASS — finding 0 | repository 1회 | exit 0 |
| manifest JSON parse | PASS — `manifest json passed` | 1회 | stdout |
| `git diff --check` | PASS — whitespace error 0 | current diff 1회 | exit 0 |

### 미실행 검증과 이유

- product tests/build: plan-only 요청이며 code 변경 0.
- provider actual: Task 5 이후 별도 exact 승인 전 0.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문/provider body/status detail 저장·출력 0, external call 0.
- Security: key/DSN 출력 0, separate actual gate 유지.
- Accessibility: UI 변경 0.
- Performance/cost: runtime 변경 0, 비용 USD 0.

## 10. 데이터와 출처 영향

- official/mock data, DB lineage, source metadata: 변경 0.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Tasks 1~5 implementation plan의 실행 방식과 구현 시작 승인이 필요하다.
- Task 6 actual은 구현 계획 승인에 포함되지 않는다.
- actual 전 exact phrase `A-072 corrective actual 1회 실행 승인`이 별도로 필요하다.
- push/merge도 현재 승인 범위가 아니다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `parse_classifier_wire_decision_with_stage` signature와 Task 3 import를 plan에서 동일하게 고정했다.
- Task 1~3의 commit 경계를 분리하고 main agent가 integration/version docs를 소유한다.

## 13. 인수인계·재현·롤백

### 재현

1. A-072 spec status가 Approved인지 확인한다.
2. D-115와 A-072 task Plan Review 상태를 확인한다.
3. plan의 Global Constraints와 Tasks 1~6, actual stop gate를 확인한다.
4. manifest docs 2.30.1과 이 노트 INDEX를 확인한다.

### 롤백

문서-only commit을 revert할 수 있다. historical D-115는 삭제하지 않고 후속 결정으로 대체한다.

### 다음 개발자 시작점

사용자의 execution mode 선택과 계획 승인을 기다린다. Subagent-Driven이면
`superpowers:subagent-driven-development`, Inline이면 `superpowers:executing-plans`를 사용한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 계획 승인과 실행 방식 선택.
- Tasks 1~5 TDD implementation/root gate.
- Task 6 separate actual approval.
- 이후 push/PR/merge는 별도 인간 지시.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

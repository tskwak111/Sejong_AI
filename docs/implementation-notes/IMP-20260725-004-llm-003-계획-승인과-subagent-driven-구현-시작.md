# IMP-20260725-004 — LLM-003 계획 승인과 Subagent-Driven 구현 시작

- Date/Time (KST): 2026-07-25 20:05:00 +09:00
- Task ID: LLM-003-EXECUTION
- Type: decision-implementation-start
- Status: Decision-only Done / implementation In Progress
- Author/Agent: 사용자 결정자, Codex controller
- Branch: `codex/LLM-003-grounded-live-chat-design`
- Base commit: `85111e1`
- Related: D-072~D-074, ADR-0023,
  `docs/superpowers/plans/2026-07-25-grounded-live-chat-generation.md`

## 1. 사용자 요청과 완료 기준

사용자는 `계획 승인, Subagent-Driven으로 구현 시작`으로 LLM-003 계획의 제품 구현을 승인했다.
완료 기준은 승인 사실을 활성 source-of-truth에 기록하고, 격리 worktree와 plan-scoped SDD
ledger를 확인한 뒤 Task 1 contract RED부터 구현을 시작하는 것이다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who | 사용자 승인자, 메인 controller, task별 fresh implementer/reviewer |
| When | 2026-07-25 KST |
| Where | 기존 linked worktree `codex/LLM-003-grounded-live-chat-design` |
| What | D-074, 실행상태 전환, SDD ledger, Task 1 시작 gate |
| Why | 승인된 계획을 TDD와 task별 독립 검토로 안전하게 구현하기 위해 |
| How | implementer→spec/quality reviewer→bounded fix loop→다음 task |
| How much | 이 checkpoint는 문서·상태만; product code/provider network/DB/data 0 |

## 3. 시작 전 상태와 조사

- worktree Git dir와 common dir가 달라 linked worktree임을 확인했다.
- branch는 `codex/LLM-003-grounded-live-chat-design`, 시작 tree는 clean이었다.
- plan-scoped workspace:
  `.superpowers/sdd/2026-07-25-grounded-live-chat-generation/`
- execution plan은 8 tasks이며 Task 1은 additive SUCCESS `answer_mode` 계약이다.
- preflight plan scan에서 task 간 load-bearing 충돌은 없었다.
- Task 1에서 존재하지 않는 Task 2 타입을 조기 import하던 계획 문장은 plan 승인 전에 이미
  TEMPLATE baseline으로 분리해 보정됐다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정 |
|---|---|---|---|
| D-074 | 인간 | 계획/방식/시작 승인 | Approved |
| ACTUAL | 인간 gate | 실제 Upstage network 시점 | offline 전체 PASS 뒤 별도 local 단계 |
| PUBLIC | A/Blocker | public/remote/기관 운영 | 계속 금지 |
| DEP/DB | 인간 gate | 새 production dependency/DB migration | 계획 범위에서 금지 |

## 5. 선택 설계와 버린 대안

- 선택: task마다 fresh implementer와 별도 reviewer를 사용하고 controller는 공유 계약·버전·
  보안·통합·Git을 소유한다.
- 병렬 구현은 공유 tree 충돌을 만들므로 SDD 규칙에 따라 task implementer는 한 번에 하나다.
- reviewer는 read-only diff package만 사용하며 구현 보고를 신뢰하지 않고 검증한다.
- 메인 모델이 직접 모든 코드를 쓰는 방식은 사용자의 agent-driven 승인과 독립 review 요구에
  맞지 않아 선택하지 않았다.

## 6. 변경 파일·계약·DB·데이터

| 영역 | 변경 |
|---|---|
| D-074/TEAM/SOT/RFP/A-048/TASKS | 승인·In Progress 상태 |
| execution plan | D-074, Task 1 starting, future implementation note 005 |
| changelog/version | docs 2.19.2 |
| SDD ledger | ignored plan-scoped recovery map |
| product/API/DB/data/provider | 이 checkpoint에서는 0 |

## 7. 버전 전후

| 축 | Before | After |
|---|---|---|
| Product spec | 2.5.0 | 동일 |
| Application/Web/API/Contracts/DB/Data/Prompt/Test | manifest current | 동일 |
| Documentation | 2.19.1 | 2.19.2 |

## 8. 실행 명령과 테스트

| 명령 | 결과 |
|---|---|
| linked-worktree detection (`git-dir`, `git-common-dir`, branch, superproject) | PASS |
| `sdd-workspace` via Git Bash | PASS, plan-scoped ignored workspace 생성 |
| `python -B scripts/check_repository_docs.py` | PASS |
| `python -m json.tool versions/manifest.json` | PASS |
| `git diff --check` | PASS, whitespace error 0 |
| `scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS, output 0 / exit 0 |

API/Web/DB/provider 검증은 아직 product diff가 없는 실행 승인 checkpoint라 Task 1 RED/GREEN에서
시작한다.

## 9. 보안·개인정보·접근성·성능

- secret/key/env 읽기와 network 0.
- raw/masked question, provider body, DB row 0.
- public/remote/actual/자동 merge 금지 유지.
- Web 접근성은 Task 7, runtime 비용/8초/cap은 Tasks 4~8에서 검증한다.

## 10. 데이터와 출처

- official `.2`, mock, DB projection 변경 0.
- 공식 source metadata는 후속 구현에서도 서버 소유다.

## 11. 인간이 반드시 알아야 하는 내용

- 제품 구현은 이제 승인됐다.
- 실제 Upstage 호출은 아직 승인된 실행 단계가 아니며 offline 전체 gate 뒤 진행한다.
- public/remote, 새 dependency, migration, 자동 merge는 승인되지 않았다.

## 12. AI 내부 구현 세부

- SDD ledger가 compaction 뒤 task/commit/review 상태의 권위다.
- task brief와 diff package는 ignored workspace에 두며 Git에 포함하지 않는다.
- 각 Task는 TDD RED 증거와 GREEN 결과, self-review, task review가 모두 있어야 완료다.

## 13. 재현·인수인계·롤백

1. commit `85111e1` 뒤 이 checkpoint commit을 확인한다.
2. plan과 ignored ledger를 읽는다.
3. Task 1 brief부터 dispatch한다.
4. 승인 철회 시 D-074를 삭제하지 않고 superseding decision을 기록하고 mode disabled 상태를 유지한다.

## 14. 남은 위험과 다음 단계

- Task 1 계약 RED/GREEN과 독립 review가 다음 단계다.
- distributed exactly-once의 5분 lease 이후 수동 재시도 한계는 plan note에 공개돼 있다.
- actual provider account logging/retention은 저장소 밖 인간 확인 사항이다.

## 15. 자체 리뷰

- [x] 요청과 승인 경계 기록
- [x] 최종 docs/diff 검증
- [x] 제품 코드·비밀·DB·network 0
- [x] INDEX 갱신

# IMP-20260726-003 — LLM-003 local actual 이후 다음 단계와 Git 경계

- Date/Time (KST): 2026-07-26T11:28:54+09:00
- Task ID: LLM-003-NEXT
- Type: status-handoff
- Status: Done — next action identified / publication approval Pending
- Author/Agent: Codex
- Branch: codex/LLM-003-local-actual-evidence
- Base commit: c575809
- Related plan/ADR/RFP: D-075 / ADR-0023 / LLM-003 plan / IMP-20260726-002

## 1. 사용자 요청과 완료 기준

- 요청: “그럼 이제 뭐하면됨? 계속하면됨?”
- 완료 기준: 실제 저장소 상태를 기준으로 다음 순서, 인간 승인 경계와 이후 개발 우선순위를
  비전문가도 실행할 수 있게 설명한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who | 사용자에게 다음 인간 결정, Codex에게 다음 AI 작업을 분리 |
| When | local actual PASS 직후, 2026-07-26 KST |
| Where | `codex/LLM-003-local-actual-evidence` worktree와 private GitHub |
| What | actual slice 리뷰→commit→push→Draft PR→인간 merge→다음 수직 흐름 |
| Why | 검증된 변경과 다음 기능을 섞지 않고 리뷰·rollback 단위를 보존 |
| How | 현재 diff를 독립 검토한 뒤 Git publication은 별도 명시 승인으로 수행 |
| How much | 제품 동작·DB·데이터·API 변경 0; 문서 노트 1개와 INDEX 1행 |

## 3. 시작 전 상태

- LLM-003 actual은 PII-free fixture GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 mismatch 0,
  typed write-boundary forbidden-value 위반 0으로 PASS했다.
- API 2,021 tests, affected scripts 66 tests, Ruff/Mypy/docs/secret/package/diff가 PASS했다.
- actual 하네스, DB login 보정과 문서 변경은 local branch에 있으나 아직 commit/push/PR되지 않았다.
- public/remote/실제 기관 운영은 승인되지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| GIT-PUBLISH | Human | local actual 변경을 private GitHub에 게시할지 | 명시 승인 전 local 유지 | commit/push/Draft PR |
| NEXT-SLICE | Defaultable | 병합 뒤 다음 개발 | 데모 안정화·운영 인수인계 순 | 새 제품 변경은 별도 slice |

## 5. 선택과 대안

- 선택: actual 변경을 먼저 하나의 Draft PR로 닫고, 인간 merge 뒤 최신 `main`에서 다음 slice를 시작한다.
- 이유: actual 증거·하네스·문서·DB login 수정은 하나의 재현 가능한 단위다.
- 제외: 지금 다음 기능까지 같은 branch에 추가하면 PR이 커지고 충돌·rollback·평가가 어려워진다.

## 6. 변경 파일·계약·DB·데이터

- 변경: 본 상태 노트와 `docs/implementation-notes/INDEX.md`.
- 제품 코드/API/DB/schema/official/mock/prompt/dependency 변경: 0.
- aggregate stdout의 개인정보·비밀·실제 질문 노출 0. persistence 증거는 PII-free fixture의
  typed write-boundary forbidden-value 위반 0이며 post-read DB forensic은 아니다.

## 7. 버전 전후

모든 manifest 축 유지: application `0.9.1-grounded-local-chat-evidence`, Web
`0.6.0-answer-mode`, API `3.2.0-draft`, DB `0.4.0-local`, official data
`0.1.0-initial.2`, test `1.6.1-grounded-actual`, docs `2.20.1`.

## 8. 명령과 실제 결과

| 명령 | 결과 |
|---|---|
| `git status --short --branch` | actual branch에 검증된 변경이 있고 commit/push되지 않음 |
| 구현 노트 생성 스크립트 | IMP-20260726-003과 INDEX 행 생성 |

새 코드가 없어 테스트를 반복하지 않았다. 직전 IMP-20260726-002의 fresh 검증 결과가 권위다.

## 9. 보안·개인정보·접근성·성능

- 보안/개인정보: publication 전 current-tree secret scan PASS 상태를 유지해야 한다.
- 접근성/성능/비용: 동작 변경과 추가 provider call 0.

## 10. 데이터와 출처

official `.2`, local ACTIVE 20 lineage와 DB는 이 판단에서 변경하지 않았다. mock/AI 생성 데이터도 없다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 다음 AI 작업은 최종 diff review까지 안전하게 계속할 수 있다.
- commit·push·Draft PR은 사용자가 `commit·push·Draft PR 진행`처럼 명시하면 수행한다.
- Draft PR은 자동 merge하지 않는다. 검토 후 사용자가 squash merge한다.
- merge 전에는 다음 기능을 같은 branch에 섞지 않는다.

## 12. AI 내부 구현 세부

- Git publication 전 untracked runner/note를 포함해 scope·secret·diff를 다시 확인한다.
- PR base는 최신 private `main`, branch는 현재 `codex/LLM-003-local-actual-evidence`다.

## 13. 재현·롤백·인수인계

- 재현: IMP-20260726-002의 명령·aggregate와 현재 branch diff를 검토한다.
- 롤백: 아직 commit 전이므로 Git history rollback은 없다. 실제 provider는 이미 disabled다.
- 다음 개발자 시작점: actual Draft PR merge 뒤 새 branch에서 데모 안정화/인수인계 slice를 시작한다.

## 14. 남은 위험·다음 단계

1. current diff 독립 리뷰와 최종 scope 확인.
2. 인간 승인 후 commit·push·Draft PR.
3. CI와 PR diff 확인 후 인간 squash merge.
4. 최신 `main`에서 다음 수직 흐름 시작.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 실제 Git 상태 근거
- [x] 인간/AI 경계 분리
- [x] 버전·데이터·보안 영향 기록
- [x] INDEX 갱신

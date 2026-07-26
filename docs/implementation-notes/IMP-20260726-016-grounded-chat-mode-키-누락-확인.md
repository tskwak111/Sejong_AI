# IMP-20260726-016 — grounded chat mode 키 누락 확인

- Date/Time (KST): 2026-07-26T20:33:12+09:00
- Task ID: LLM-LOCAL-CONFIG-CHECK
- Type: diagnosis
- Status: Done — absence confirmed fail-closed; explicit false recommended
- Author/Agent: 사용자 질문 / Codex 진단
- Branch: codex/POST-PR17-HUMAN-CHECKLIST-001
- Base commit: ad0ae66
- Related plan/ADR/RFP: D-072, D-082, ADR-0023, LLM-003 local runbook,
  POST-PR17-HUMAN-ACTIONS

## 1. 사용자 요청과 완료 기준

### 요청

- local `apps/api/.env`에 `UPSTAGE_GROUNDED_CHAT_MODE=false`가 없는 상태의 의미와 조치 확인.

### Acceptance Criteria

- `.env`의 다른 값이나 secret을 출력하지 않는다.
- key 존재 여부, tracked example, settings loader와 실제 resolved profile을 근거로 진단한다.
- 안전한 최소 조치를 설명하고 제품 코드·DB·provider를 변경하지 않는다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 누락을 신고하고 Codex가 값 비노출 진단 |
| When — 언제 | 2026-07-26 KST |
| Where — 어디서 | primary ignored `apps/api/.env`, tracked `.env.example`, LLM settings loader |
| What — 무엇을 | key absence와 fail-closed resolved profile 확인 |
| Why — 왜 | manual provider-disabled demo 전에 외부 호출 가능성을 제거하기 위해 |
| How — 어떻게 | regex 존재 여부, tracked declaration 검색, loader path 분석, value-free runtime probe |
| How much — 어느 정도 | config key 1개 진단; environment/code/DB/provider mutation 0 |

## 3. 시작 전 상태

- 관련 파일: `apps/api/.env.example`,
  `apps/api/src/sejong_ai_api/llm/settings.py`, ignored primary `.env`.
- 기존 동작: chat loader는 exact non-secret profile 전체와 key가 일치할 때만 provider
  settings를 조립한다.
- 발견한 충돌/부채: primary `.env`에는 해당 key가 없지만 example에는 explicit false가 있다.
- Git 상태: primary `main=c945303=origin/main`, clean. `.env`는 ignored이며 수정하지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| LLM-LOCAL-CONFIG-CHECK | Internal | mode key absence | loader 결과 DISABLED; 사람이 explicit false 한 줄 추가 권고 | local provider assembly only |

## 5. 설계 결정과 대안

### 선택

- 누락을 오류나 활성화로 해석하지 않고 실제 loader 결과를 확인했다.
- manual demo의 명확성을 위해 `.env`에 `UPSTAGE_GROUNDED_CHAT_MODE=false`를 한 번만
  명시하도록 안내한다.

### 이유

- loader는 non-secret exact profile 값이 하나라도 없으면 `None`으로 닫힌다.
- 명시적 false는 사람이 설정을 읽기 쉽고 이후 true 전환 실수를 줄인다.

### 고려했지만 선택하지 않은 대안

- 자동으로 `.env` 편집: 사용자가 확인 중인 ignored environment에 불필요한 write를 하지 않기 위해 제외.
- 누락 상태 그대로 영구 유지: 안전하지만 운영자가 의도를 읽기 어려워 explicit false를 권고.
- true로 설정: provider actual 범위이며 이번 provider-disabled demo 목적과 반대라 제외.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| product/environment | 변경 없음 | 진단 요청 |
| implementation note/INDEX/version docs | 진단 evidence | 재현·보안 계보 |

### 데이터 흐름/상태 변화

- 없음. `.env` read는 key presence/profile assembly 확인에만 사용했고 값은 출력하지 않았다.

### 오류·빈 상태·롤백

- 첫 두 runtime probe는 Python import path가 없어 `ModuleNotFoundError`로 실패했다. 제품
  오류가 아니며 third probe에서 project `src`를 명시해 exact loader를 실행했다.
- key가 없으면 loader는 provider runtime을 조립하지 않고 TEMPLATE 경로를 유지한다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.5.0
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
- documentation: 2.21.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product/Application/Web/API/shared | current manifest | 동일 | 제품 변경 0 |
| DB/data/prompt/test | current manifest | 동일 | mutation/provider/test code 0 |
| Docs | 2.21.1 | 2.21.2 | local config diagnosis 기록 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| local env key-presence probe | PASS | `LOCAL_ENV_KEY_PRESENT=NO`, values 0 | bounded stdout |
| tracked declaration search | PASS | `.env.example` explicit false, loader/tests declarations 확인 | repository |
| runtime loader probe attempts 1~2 | FAIL | `ModuleNotFoundError`, import invocation issue | command output |
| runtime loader probe attempt 3 | PASS | `GROUNDED_CHAT_PROFILE=DISABLED`, values 0 | bounded stdout |

### 미실행 검증과 이유

- `.env` write와 API restart는 사용자가 한 줄을 명시한 뒤 수행할 수 있으며 현재 loader
  result가 이미 disabled라 제품 변경은 필요 없다.
- 제품 코드가 없어 API/Web suite를 반복하지 않는다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: `.env` value/API key/DSN/secret 출력 0.
- Security: absent key가 fail-closed disabled임을 실제 loader로 확인.
- Accessibility: 영향 없음.
- Performance/cost: provider call 0, 비용 0.

## 10. 데이터와 출처 영향

- 공식 데이터: 영향 없음.
- mock/AI 생성: 없음.
- schema/lineage: 영향 없음.
- verified date: 2026-07-26 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 상태도 AI 호출은 꺼져 있어 안전하다.
- 명확성을 위해 `apps/api/.env`에
  `UPSTAGE_GROUNDED_CHAT_MODE=false` 한 줄을 정확히 한 번만 추가한다.
- 따옴표·공백을 붙이지 않고 duplicate assignment를 만들지 않는다.
- API가 이미 실행 중이면 저장 후 재시작한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- loader는 missing value를 default boolean false로 채우는 방식이 아니라 exact profile
  assembly 전체를 거부해 `None`을 반환한다.
- `.env.example`이 권장 explicit local shape의 기준이다.

## 13. 인수인계·재현·롤백

### 재현

- key 존재 여부는 값을 출력하지 않는 regex probe로 확인한다.
- loader probe는 `apps/api/src`를 `sys.path`에 추가하고 profile enabled/disabled만 출력한다.

### 롤백

- 사용자가 추가한 explicit false를 제거해도 loader는 다시 fail-closed disabled다.
- tracked docs-only commit은 revert 가능하며 제품/DB rollback은 없다.

### 다음 개발자 시작점

- 사용자의 explicit false 추가 확인 뒤 `/ready=200` manual demo를 계속한다.
## 14. 남은 위험·미해결 질문·다음 단계

- 사용자 local `.env` explicit false 추가 및 필요 시 API restart.
- manual demo 결과와 A-052는 이전 handoff대로 Pending.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

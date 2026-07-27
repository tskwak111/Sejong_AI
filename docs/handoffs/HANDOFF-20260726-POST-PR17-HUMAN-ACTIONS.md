# Handoff — PR #17 병합 후 사용자 작업

- Date: 2026-07-26 KST
- Source authority: `origin/main=c945303dfe9facec974d70b261ae9adc9aaa7ff3`
- Scope: local/private MVP의 사람 전용 수동 확인과 다음 성능 단계 결정
- Product code/API/DB/data change: 없음

## Repository/collaboration state

- Source remote: private `tskwak111/Sejong_AI`
- PR #17: 사람 병합 완료, merge commit `c945303`
- local/private MVP 자동 리허설: PASS
- GitHub hosted Collaboration policy/Frontend summary: PASS
- 현재 API와 Web은 상시 서비스가 아니라 필요할 때 local에서 실행한다.
- public deploy, remote DB, public admin, 실제 기관 운영은 승인되지 않았다.

## 지금 사용자가 할 일 — 요약

사용자가 직접 해야 하는 일은 정확히 세 가지다.

1. **15~25분 수동 화면·발표 리허설**
2. **PERF Phase B가 사용할 DB 선택**
3. **팀원 MFA/recovery 확인**

코드 작성, 성능 harness 구현, 자동 테스트, 문서·PR 작성은 Codex가 맡는다.

## 1. 최신 main으로 맞추기

현재 기본 local checkout은 깨끗하지만 오래된 작업 branch에 있을 수 있다. 저장소 루트의
PowerShell에서 다음을 실행한다.

```powershell
git status --short
git fetch --prune origin
git switch main
git pull --ff-only origin main
git rev-parse --short HEAD
```

기대 결과:

- 첫 명령 출력 없음
- 마지막 SHA: `c945303`

첫 명령에 파일명이 나오면 switch/pull하지 말고 Codex에 그 출력만 전달한다. `.env` 내용,
API key, DSN은 전달하지 않는다.

## 2. local 데모 실행

### 2-1. Docker Desktop

Docker Desktop을 켜고 Engine이 준비될 때까지 기다린다.

```powershell
docker version
```

Client와 Server가 모두 표시되면 다음으로 간다.

### 2-2. provider-disabled 설정

첫 수동 리허설은 비용·외부 장애를 제거하기 위해 다음 상태로 실행한다.

```dotenv
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
UPSTAGE_GROUNDED_CHAT_MODE=false
```

`LLM_API_KEY`, `DATABASE_URL`, `CONTEXT_TOKEN_SECRET`의 값은 화면 캡처·채팅·문서에 남기지
않는다. `CONTEXT_TOKEN_SECRET`은 PR #17 전에 safe provisioner로 반영됐다.

### 2-3. local Supabase 시작

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/bootstrap_patched_supabase.ps1 -VerifyOnly

$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$repositoryToolRoot = Split-Path $commonGitDir -Parent
$supabase = Join-Path $repositoryToolRoot `
  ".tools\supabase\v2.109.1-sejong-loopback\supabase.exe"
& $supabase start *> $null
if ($LASTEXITCODE -ne 0) { throw "LOCAL_SUPABASE_START_FAILED" }
```

중요:

- 현재 DB는 이미 ACTIVE KB 20이다.
- `db reset`, `seed-cycle`, `verify_database.ps1`은 실행하지 않는다.
- `.2` seed를 다시 넣거나 DB 행을 삭제하지 않는다.

### 2-4. API 실행 — PowerShell 창 1

```powershell
$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$uv = Join-Path (Split-Path $commonGitDir -Parent) ".tools\uv\uv.exe"
& $uv run --project apps/api --frozen python `
  scripts/run_local_api.py --port 8000
```

이 창은 그대로 둔다. 질문/답변 원문을 access log로 출력하지 않는 전용 runner다.

### 2-5. readiness 확인 — PowerShell 창 2

```powershell
$response = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ready
$response.StatusCode
```

기대 결과는 `200`이다. 503이면 화면에 나온 **stable reason만** Codex에 전달하고 `.env`나
DSN은 전달하지 않는다.

### 2-6. Web 설정과 실행 — PowerShell 창 2

ignored `apps/web/.env.local`에 다음 non-secret 값이 있는지 확인한다.

```dotenv
API_INTERNAL_BASE_URL=http://127.0.0.1:8000
CHAT_UI_MODE=actual
ADMIN_UI_ENABLED=true
ADMIN_UI_MODE=actual
```

그다음 실행한다.

```powershell
corepack.cmd pnpm --filter @sejong-ai/web dev
```

브라우저에서 `http://127.0.0.1:3000`을 연다.

## 3. 5문항 수동 데모 체크

| 순서 | 사용자 동작 | 기대 결과 |
|---:|---|---|
| 1 | `이사했는데 전입신고 어떻게 해요?` | SUCCESS, 절차 안내, 공식 출처 카드, TEMPLATE 표시 |
| 2 | `신고하고 싶어요.` | FOLLOWUP과 선택 가능한 구체화 질문 |
| 3 | `내 자동차세 체납액 알려줘.` | PERSONAL_LOOKUP 안전 폴백, 후보 생성 유도 없음 |
| 4 | 지역을 `아름동`으로 선택하고 `등본은 어디서 발급해요?` | 공식 답변과 아름동 공식 기관 카드 |
| 5 | `침대 2인용 프레임 수수료가 얼마예요?` | 이미 개선된 20번째 ACTIVE 답변, 10,000원, 공식 출처 |

현재 DB는 이미 20번째 KB가 ACTIVE다. 따라서 5번은 **승인 후 개선 결과**만 보여준다.
19→20 관리자 승인 과정을 다시 라이브로 만들기 위해 현재 DB를 reset하지 않는다. 발표에서는
기존 actual 증거를 이용해 “처음에는 근거 부족 → 다른 승인자의 검수 → ACTIVE → 재질의 성공”
순서로 설명한다.

## 4. 접근성 수동 체크

### 4-1. 200% 확대

1. 브라우저에서 `Ctrl`+`+`를 눌러 200%로 만든다.
2. `/`, `/chat`, `/admin`을 각각 연다.
3. 질문 입력, 보내기, 출처 링크, 관리자 주요 버튼이 잘리거나 겹치지 않는지 본다.
4. 가로 스크롤 없이는 주요 동작을 못 하는 문제가 없는지 확인한다.

### 4-2. 키보드만 사용

1. 마우스에서 손을 뗀다.
2. `Tab`, `Shift+Tab`, `Enter`, `Space`, `Esc`만 사용한다.
3. 현재 포커스 위치가 눈에 보이는지 확인한다.
4. 질문 입력→전송→출처 링크→지역 선택이 가능한지 확인한다.
5. 피드백 dialog를 열었다 닫았을 때 포커스가 원래 버튼으로 돌아오는지 확인한다.

### 4-3. 시각 확인

- 작은 회색 글자가 읽기 어렵지 않은지
- 흰 배경과 글자 대비가 충분해 보이는지
- 오류·폴백이 색상 하나에만 의존하지 않고 글자로도 설명되는지
- 모바일 폭에서도 주요 버튼을 찾기 쉬운지

## 5. 발표 시간 확인

권장 목표는 5~7분이다.

1. 1분: 해결하려는 문제와 “모르면 지어내지 않는다”
2. 2분: 정상 질문·출처·기관 카드
3. 1분: PERSONAL_LOOKUP 안전 폴백
4. 2분: 실패 질문이 사람 승인 후 20번째 ACTIVE가 된 개선 루프
5. 1분: 개인정보 원문 미저장·외부 LLM 실패 시 TEMPLATE fallback

## 6. 사용자 결정 — A-052

PERF Phase A는 `/health`와 official office read만 사용해 DB write 없이 Codex가 진행할 수 있다.

Phase B chat 부하는 metadata/idempotency row를 만들 수 있다. 선택지는 다음과 같다.

- **추천: disposable clean DB**
  - 장점: 현재 데모 DB와 통계를 오염시키지 않음
  - 단점: 별도 DB를 만들고 버리는 준비 시간이 필요함
- current non-KPI DB bounded write
  - 장점: 준비가 빠름
  - 단점: 이미 KPI로 사용할 수 없는 DB에 행이 더 쌓이고 설명이 복잡해짐

추천 답변:

```text
A-052: disposable clean DB 승인.
PERF Phase A 구현·실행 시작.
Phase B는 disposable DB 준비 후 실행.
```

## 7. 팀원 MFA/recovery

팀원에게 다음 두 가지만 확인받는다.

- GitHub 2단계 인증(MFA)이 켜져 있는가?
- recovery code 또는 복구 수단을 본인만 안전하게 보관했는가?

코드, QR, 전화번호, 이메일, recovery code 자체는 받거나 공유하지 않는다. 답은
“MFA 설정 완료 / recovery 수단 보관 완료”면 충분하다.

## 8. 사용자 응답 템플릿

수동 확인 뒤 아래만 복사해 채운다.

```text
MANUAL-DEMO-001
- 최신 main c945303: PASS/FAIL
- /ready=200: PASS/FAIL
- 5문항: PASS/FAIL
- 200% 확대: PASS/FAIL
- 키보드 조작·focus 복귀: PASS/FAIL
- 글자·대비: PASS/FAIL
- 발표 시간: __분
- 발견한 문제: 없음 / 간단한 현상

A-052: disposable clean DB 승인
팀원 MFA/recovery: 완료 / 아직
```

## 환경변수 이름(값 제외)

- API: `DATABASE_URL`, `CONTEXT_TOKEN_SECRET`, `UPSTAGE_SYNTHETIC_EVALUATION_MODE`,
  `UPSTAGE_GROUNDED_CHAT_MODE`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`
- Web: `API_INTERNAL_BASE_URL`, `CHAT_UI_MODE`, `ADMIN_UI_ENABLED`, `ADMIN_UI_MODE`

## 알려진 문제와 위험

- current DB event 통계는 D-077에 따라 평가 KPI가 아니다.
- actual quality-summary는 의도적으로 미제공이다.
- public admin 인증, `00700`, remote DB/deploy, backup/restore는 Pending이다.
- GitHub hosted green은 local API/DB 전체 검증을 대신하지 않는다.

## 다음 작업과 Acceptance Criteria

Codex 다음 작업은 PERF-001 Phase A다.

- locked Python/httpx harness
- loopback-only `/health`와 official office read
- 100 VU, 60초
- provider call 0, DB write 0
- error rate <1%, average ≤3초
- request/success/error, p50/p95/max/average aggregate만 기록
- 질문·응답·기관 record·secret·DSN 출력 0

Phase B는 A-052 결정과 disposable DB 준비 전 실행하지 않는다.

## 최근 구현 노트/계획 링크

- [IMP-20260726-014](../implementation-notes/IMP-20260726-014-local-demo-readiness-and-performance-plan.md)
- [Final local demo rehearsal](../test-reports/FINAL-LOCAL-DEMO-REHEARSAL.md)
- [DEMO/PERF plan](../superpowers/plans/2026-07-26-local-demo-readiness-and-performance-smoke.md)
- [Current MVP handoff](HANDOFF-20260726-CURRENT-MVP-STATUS.md)

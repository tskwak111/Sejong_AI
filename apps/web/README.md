# apps/web

세종 민원이음(시민)·이음센터(관리자)의 Next.js 웹 앱이다. 시민 첫 화면 `/`,
시민 대화 화면 `/chat`, local/private 이음센터 `/admin`(운영 현황·실패 질문
관리·KB 후보 승인)을 제공한다. 화면·디자인 시스템 규칙은 이 폴더의
`CLAUDE.md`와 `DESIGN.md`를 따른다.

## 현재 동작

- `/` 시민 첫 화면: 지원 4개 분야, 분야별 추천 질문 칩, 질문 입력창,
  개인정보 입력 경고 상시 노출.
- `/chat`: 생성된 계약 타입(ChatResponse union)을 소비해 SUCCESS, FOLLOWUP,
  폴백 5종(PRIVACY_UNRESOLVED 포함), 출처 스트립·기관 카드,
  loading/error/retry를 표시한다.
- logical retry마다 UUID `Idempotency-Key` 하나를 만들고 같은 재시도에는
  유지한다. correlation ID는 backend가 별도로 만들며 Web은 저장하지 않는다.
- 대화와 signed context token은 React 메모리에만 두며 브라우저 저장소·쿠키·
  분석 도구를 사용하지 않는다. FALLBACK 응답 후 토큰은 초기화된다(계약).
- `/admin` 이음센터: 실패 질문 큐(NEW → 사유 확정) → 근거 부족 건만 KB 후보
  초안 생성 → 별도 승인자(APPROVER) 검수(검수 의견 필수) → 공식 출처 초안만
  ACTIVE 승인. 자기검수 금지·MOCK 승인 금지 불변식을 유지한다.
  ACTIVE 승인 판정은 actual 모드 전용이며, fixture 모드에서는 승인·반려
  버튼이 비활성이다 (Q-PM-DEMO-001).
- 실패 질문 저장은 INSUFFICIENT_GROUNDING만 (마스킹 후 30일 보관).
  PERSONAL_LOOKUP·LEGAL_JUDGMENT·OUT_OF_SCOPE·PRIVACY_UNRESOLVED는 완전
  미저장 (Q-MVP-002/D-059, 개인정보 최소수집 강화).

## 로컬 환경변수

`apps/web/.env.example`을 `apps/web/.env.local`로 복사할 수 있다.

- `API_INTERNAL_BASE_URL`: Next 서버가 same-origin `/api/v1/*` 요청을 local
  API로 전달할 때만 사용한다 (기본 `http://127.0.0.1:8000`). `NEXT_PUBLIC_*`
  API 주소나 backend 비밀을 브라우저 번들에 추가하지 않는다.
- `CHAT_UI_MODE` (server-only): **미설정 기본은 `actual`** — local API 연결
  실패 시 값 없는 안전 오류 화면을 보여준다. `fixture`는 명시 설정에서만
  켜지며 전 화면에 "시연용 샘플 — 공식 데이터 아님" 앰버 배너가 상시
  노출된다.
- `ADMIN_UI_ENABLED` (server-only): local/private 관리자 화면 게이트. 기본과
  공개 모드는 `false`. 인증을 대체하지 않으며 public 관리자 연결은 금지.
- `ADMIN_UI_MODE` (server-only): **미설정 기본은 `actual`** (typed actual
  admin transport). `fixture`는 명시 설정에서만 — 시연용 샘플 배너 노출 +
  승인·반려 판정 비활성. fixture와 actual 데이터는 절대 섞지 않는다.

## 실행 방법 — actual 데모 기준 (Q-PM-DEMO-001)

데모 완주(#5 포함)는 actual 경로에서 검증한다. 저장소 루트에서:

1. local Supabase/Postgres 기동 (저장소 루트 README의 DB 기준선 가이드 —
   patched supabase CLI + `supabase/migrations/` 권위).
2. local API 실행: `python scripts/run_local_api.py`
   (기본 `http://127.0.0.1:8000`).
3. `apps/web/.env.local` 설정:

   ```dotenv
   API_INTERNAL_BASE_URL=http://127.0.0.1:8000
   CHAT_UI_MODE=actual
   ADMIN_UI_ENABLED=true
   ADMIN_UI_MODE=actual
   ```

4. `corepack pnpm --filter @sejong-ai/web dev` 후 `/` → `/chat` → `/admin`.
   데모 #5는 근거 부족 질문("침대 2인용 프레임 배출 수수료" 계열) →
   실패 질문 큐 도착 → 사유 확정 → KB 후보 생성 → 별도 승인자 검수 →
   ACTIVE 승인으로 확인한다.

## fixture 모드 — UI 개발·상태 확인 도구 (데모 백업 아님)

`CHAT_UI_MODE=fixture` (+ `ADMIN_UI_ENABLED=true`, `ADMIN_UI_MODE=fixture`)
를 **명시**하면 네트워크 없이 화면 상태를 확인할 수 있다: 시민 #1~#4
(SUCCESS·FOLLOWUP·FALLBACK 카드)와 이음센터 열람·사유 확정·KB 후보 초안
생성까지. fixture 데이터는 전부 MOCK(시연용 샘플)이라 승인·반려 판정과
ACTIVE 전환은 동작하지 않는다 — 해당 흐름은 위 actual 경로에서만 확인한다.

## 로컬 명령

저장소 루트에서 실행한다.

```powershell
corepack pnpm --filter @sejong-ai/web dev
corepack pnpm --filter @sejong-ai/web lint
corepack pnpm --filter @sejong-ai/web typecheck
corepack pnpm --filter @sejong-ai/web test
corepack pnpm --filter @sejong-ai/web build
corepack pnpm --dir tools/web-e2e install --frozen-lockfile --ignore-scripts
corepack pnpm --dir tools/web-e2e test
node scripts/check_web_prod_dependency_boundary.mjs
```

Node와 pnpm의 정확한 버전은 저장소 루트의 `.node-version`과 `package.json#packageManager`를 따른다.

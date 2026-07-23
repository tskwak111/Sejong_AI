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

## 로컬 환경변수

`apps/web/.env.example`을 `apps/web/.env.local`로 복사할 수 있다.

- `API_INTERNAL_BASE_URL`: Next 서버가 same-origin `/api/v1/*` 요청을 local
  API로 전달할 때만 사용한다 (기본 `http://127.0.0.1:8000`). `NEXT_PUBLIC_*`
  API 주소나 backend 비밀을 브라우저 번들에 추가하지 않는다.
- `CHAT_UI_MODE` (server-only): 시민 대화 mock/실API 전환. 기본 `fixture` =
  데모 5문항 로컬 시연 버전(제안서 7.4). local API 리허설에서만 `actual`.
- `ADMIN_UI_ENABLED` (server-only): local/private 관리자 화면 게이트. 기본과
  공개 모드는 `false`. 인증을 대체하지 않으며 public 관리자 연결은 금지.
- `ADMIN_UI_MODE` (server-only): `ADMIN_UI_ENABLED=true`인 local/private
  리허설에서 `actual`일 때만 typed actual admin transport를 사용하고, 그 외에는
  명시적 fixture다. fixture와 actual 데이터는 절대 섞지 않는다.

## 데모 5문항 (mock 모드 = 로컬 시연 버전)

`CHAT_UI_MODE=fixture` + `ADMIN_UI_ENABLED=true`로 실행하면 아래 흐름이
네트워크 없이 완주된다.

1. "전입신고는 언제까지 해야 하나요?" → SUCCESS 카드 + 출처 + 확인일 + 정부24 딥링크
2. "아름동에서 대형폐기물은 언제 내놓나요?" → SUCCESS (지역 조건 반영, 동 변경 가능)
3. "이사했는데 뭐 해야 하나요?" → FOLLOWUP 선택지
4. "제 자동차세 얼마 나왔나요?" → FALLBACK PERSONAL_LOOKUP + 위택스 연결
5. `/admin` 실패 질문 큐 도착 → 사유 확정 → KB 후보 생성 → 역할 전환(승인자) →
   검수 의견 작성 → ACTIVE 승인

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

# POST-MVP-001 private main 안정화 설계

- 상태: **Approved**
- 작성일: 2026-07-24 KST
- 기준 commit: `4cc2f4e5e478668e1d7216fddc08874c9285274b`
- 대상 저장소: private `tskwak111/Sejong_AI`
- 제외 저장소: public 평가 snapshot `nxtcloud-edu/2026-07-kosj-industry-practice-team02`
- 관련 결정: D-069, D-070

## 1. 문제

Frontend PR #10은 `apps/web/next.config.ts` 한 파일만 변경하고 Web CI는 통과했지만,
협업 정책이 이 경로를 owner 검토 대상으로 분류해 실패했다. 팀원 범위를 넓히거나 빨간 PR을
병합하지 않고 owner 브랜치가 동일한 최소 변경을 인계한다.

동시에 다음 활성 문서 드리프트를 정리한다.

- 사용자가 확정한 서비스명 `세종 민원이음`과 활성 source-of-truth의 옛 작업명 불일치
- 이미 병합된 PR #9를 `open`으로 표시하는 `TASKS.md`
- 아직 적용되지 않은 local dev-origin 작업 상태

`[db.seed].enabled=false`와 별도 `seed-cycle → verify-final →
provision_local_database_login` 순서는 현재 런북과 정본이 일치하므로 변경하지 않는다.

## 2. 선택지와 결정

### A. owner 브랜치로 인계 — 선택

- 장점: 기존 협업 경계와 CI를 지키며 설정 변경을 owner가 검토한다.
- 단점: PR #10과 동일한 작은 변경을 새 PR로 다시 게시해야 한다.

### B. 팀원의 config 수정 허용으로 정책 확대 — 기각

- 장점: 팀원 PR을 그대로 통과시킬 수 있다.
- 단점: `next.config.ts`는 proxy·빌드·보안 동작을 바꿀 수 있어 이번 한 줄을 위해 경계를
  넓히는 비용이 크다.

### C. 실패한 정책 검사를 무시하고 PR #10 병합 — 기각

- 장점: 가장 빠르다.
- 단점: 저장소가 정의한 협업 규칙과 감사 증거를 스스로 무효화한다.

## 3. 동작 설계

`apps/web/next.config.ts`에 다음 host-only 개발 origin을 추가한다.

```ts
allowedDevOrigins: ["127.0.0.1"]
```

이는 Next.js 개발 서버의 내부 자원과 HMR 요청에만 적용한다. production `next start`,
FastAPI CORS, public domain, remote deployment allowlist는 바꾸지 않는다. wildcard, LAN 주소,
scheme, port는 추가하지 않는다.

회귀 테스트는 실제 config module을 import해 exact 한 항목만 존재하는지 검증한다. 테스트를
먼저 추가해 현재 main에서 실패하는 것을 확인한 뒤 최소 설정을 적용한다.

## 4. 문서 경계

- 현재 제품을 설명하는 활성 문서의 서비스명을 `세종 민원이음`으로 동기화한다.
- 역사적 구현 노트, 과거 실행계획, legacy 문서의 당시 제목은 변경하지 않는다.
- PR #9는 merged, WEB-DEV-ORIGIN-001은 owner review 상태로 기록한다.
- public 평가 snapshot은 수정·push하지 않는다.

## 5. 검증

- RED/GREEN config 집중 테스트
- Web unit, lint, typecheck, build
- 필요 시 127.0.0.1 기반 Playwright 집중 E2E
- 저장소 문서 링크·JSON 검사
- 비밀 패턴 검사와 `git diff --check`
- 변경 파일·협업 경계 자체 검토

## 6. 완료와 다음 단계

owner branch commit·push와 Draft PR까지만 수행하며 자동 merge하지 않는다. 병합은 사용자가
검토한다. 이후 독립 작업으로 승인된 LLM-002 Task 7의 local-only Upstage 합성 실평가
preflight를 진행한다.

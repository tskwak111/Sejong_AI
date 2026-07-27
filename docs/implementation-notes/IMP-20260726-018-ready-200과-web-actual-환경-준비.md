# IMP-20260726-018 — ready 200과 Web actual 환경 준비

- Date/Time (KST): 2026-07-26
- Task ID: MANUAL-DEMO-READY-WEB-SETUP
- Type: verification-setup
- Status: Done — API ready confirmed and ignored Web actual config prepared
- Author/Agent: 사용자 실행 / Codex 검증·local setup
- Branch: `codex/POST-PR17-HUMAN-CHECKLIST-001`
- Base commit: `c945303`
- Related: D-082, DEMO-001, POST-PR17-HUMAN-ACTIONS, IMP-016~017

## 1. 사용자 요청과 완료 기준

사용자가 local API `/ready=200`을 보고했다. Codex가 status만 재확인하고, 비밀이 없는 Web
actual 설정을 ignored `.env.local`에 준비하며 다음 실행 단계를 안내한다.

완료 기준은 `/ready=200`, Web 설정 4개 exact match, Git ignore, tracked dirty 0,
provider/DB mutation 0이다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who | 사용자가 API를 실행하고 Codex가 확인·Web local setup |
| When | 2026-07-26 KST |
| Where | loopback `127.0.0.1:8000`, ignored `apps/web/.env.local` |
| What | ready status와 actual Web server-only 설정 |
| Why | 5문항 수동 demo의 다음 단계 준비 |
| How | body 미출력 HTTP status probe, exact aggregate, `apply_patch` local file |
| How much | config 4개, secret/provider/DB query/write 0 |

## 3. 시작 전 상태

- primary `main=c945303=origin/main`.
- API는 사용자가 실행해 `/ready=200`.
- `apps/web/.env.local`은 없었고 port 3000은 free였다.
- API `.env` grounded profile은 이전 검증에서 disabled다.

## 4. 미지의 영역·가정·인터뷰

- Blocker 없음.
- 사람이 브라우저에서 Web 화면을 여는 수동 단계가 다음이다.

## 5. 설계 결정과 대안

- Web config는 비밀이 없는 4개 server-only 값만 사용한다.
- fixture가 아니라 `actual`, local admin gate만 true다.
- tracked `.env.example` 수정이나 public gate 활성화는 하지 않는다.
- 사용자가 수동으로 파일을 만들게 하는 대신 안전한 ignored file을 정확히 생성해 오타를 줄였다.

## 6. 구현 상세

| 영역 | 변경 | 이유 |
|---|---|---|
| ignored local Web env | API loopback, chat actual, admin enabled/actual | manual demo |
| note/INDEX/version docs | aggregate evidence | 계보 |

데이터 흐름과 DB schema/data는 변경하지 않았다. local file 제거가 environment rollback이다.

## 7. 버전 전후

| 축 | Before | After |
|---|---|---|
| Product/app/Web/API/shared/DB/data/prompt/test | current | 동일 |
| Docs | 2.21.3 | 2.21.4 |

## 8. 명령과 테스트 증거

| 검증 | 결과 |
|---|---|
| loopback `/ready` status-only | 200 |
| Web local env existence before | ABSENT |
| Web 4-key exact aggregate after | 4/4 YES |
| `git check-ignore` | `.env.*` rule PASS |
| tracked status | dirty 0 |
| Web port 3000 | FREE |

API body, question, answer, secret, DSN, provider payload를 출력하지 않았다. Web start/browser
manual demo는 다음 사용자 단계라 미실행이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy/security: secret 0, provider call 0, DB query/write/reset/seed 0.
- Accessibility: manual browser checklist는 아직 Pending.
- Performance/cost: 영향·비용 0.

## 10. 데이터와 출처 영향

공식/mock/schema/lineage 변경 0. verified date는 2026-07-26 KST다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Web dev server를 실행하고 browser에서 첫 화면을 확인한다.
- `.env.local`은 local/private 전용이며 public admin 승인이나 인증이 아니다.
- current DB를 reset/reseed하지 않는다.

## 12. AI 내부 구현 세부

- exact setting 검사는 값 전체를 출력하지 않고 key별 YES/NO만 출력했다.

## 13. 인수인계·재현·롤백

- 실행: `corepack.cmd pnpm --filter @sejong-ai/web dev`
- 접속: `http://127.0.0.1:3000`
- rollback: ignored `apps/web/.env.local` 제거. tracked product/DB rollback 없음.
- 다음 시작점: 화면 로드 확인 후 5문항과 manual accessibility checklist.

## 14. 남은 위험·다음 단계

- manual browser/demo/a11y, A-052, teammate MFA/recovery가 Pending이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] fresh verification
- [x] 문서·버전·INDEX 동기화
- [x] 개인정보/secret 노출 0
- [x] 제품/DB/provider 변경 0

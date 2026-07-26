# IMP-20260726-019 — Web dev dependency 복구

- Date/Time (KST): 2026-07-26T21:28:11+09:00
- Task ID: MANUAL-DEMO-WEB-DEV-DEPENDENCY
- Type: diagnosis-recovery
- Status: Done — local dependency cache recovery; human Web restart pending
- Author/Agent: Codex
- Branch: codex/POST-PR17-HUMAN-CHECKLIST-001
- Base commit: 55c34b6
- Related plan/ADR/RFP: `AGENTS.md`, `docs/00_SOURCE_OF_TRUTH.md`,
  `docs/implementation-notes/IMP-20260726-018-ready-200과-web-actual-환경-준비.md`

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 `corepack.cmd pnpm --filter @sejong-ai/web dev`로 Web을 시작했을 때 Next.js가
TypeScript 관련 패키지를 자동 설치하려다 `spawn pnpm ENOENT`로 종료한 이유를 진단하고,
안전하게 다음 로컬 데모 단계로 진행할 수 있게 한다.

### Acceptance Criteria

- 오류의 1차 원인과 2차 실패 원인을 실행 증거로 구분한다.
- 승인된 lockfile과 package manifest를 바꾸지 않고 Web 개발 의존성을 복구한다.
- `typescript`, `@types/react`, `@types/node` 해석과 Web typecheck를 확인한다.
- 비밀값·질문 원문·provider·DB를 사용하거나 출력하지 않는다.
- 사용자가 그대로 복사할 다음 명령을 제공한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 오류를 재현했고 Codex가 원인 조사·로컬 캐시 복구·검증을 수행했다. |
| When — 언제 | 2026-07-26 21:20~21:28 KST |
| Where — 어디서 | Windows primary checkout의 root `node_modules`와 `apps/web`; 기록은 별도 문서 worktree |
| What — 무엇을 | production-only로 설치돼 있던 pnpm modules를 frozen lockfile 기준 dev 포함 상태로 복구했다. |
| Why — 왜 | Next.js가 이미 선언된 TypeScript 개발 의존성을 찾지 못해 Web dev server가 종료됐기 때문이다. |
| How — 어떻게 | 환경·manifest·lock·`.modules.yaml`을 비교하고 Corepack pnpm으로 재연결한 뒤 TypeScript 해석과 typecheck를 검증했다. |
| How much — 어느 정도 | 로컬 package cache 1개 복구, package/lock tracked diff 0, provider/DB/API 변경 0, 문서 5개 갱신 |

## 3. 시작 전 상태

- 관련 파일: `package.json`, `apps/web/package.json`, `pnpm-lock.yaml`,
  `node_modules/.modules.yaml`
- 기존 동작: root와 Web package에는 `typescript@5.9.3`, `@types/react@19.2.17`,
  `@types/node@24.13.3`이 이미 선언돼 있지만 현재 `node_modules`에는 devDependencies가
  포함되지 않았다.
- 발견한 충돌/부채: `.modules.yaml`의 `devDependencies=false` 때문에 Next.js가 패키지
  누락으로 판단했다. 이어 Next.js 자동 복구는 bare `pnpm`을 spawn했지만 사용자 PATH에는
  Corepack 경유 명령만 사용 가능해 `ENOENT`가 발생했다.
- Git 상태: primary checkout `main@c945303`은 복구 전후 tracked 변경이 없었다. 기록용
  worktree는 기존 post-PR17 문서 브랜치를 이어 사용했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-WEB-LOCAL-001 | Internal | global pnpm을 새로 설치할지 여부 | 설치하지 않고 승인된 Corepack과 frozen lockfile 사용 | 전역 도구·dependency 변경 0 |
| D-WEB-LOCAL-002 | Internal | non-TTY modules 재생성 승인 방식 | 명령 범위에서만 `CI=true`, 종료 후 원상복구 | 사용자 영구 환경 변경 0 |

## 5. 설계 결정과 대안

### 선택

`corepack.cmd pnpm install --frozen-lockfile --ignore-scripts --prod=false`를 사용해 현재
lockfile 그대로 devDependencies를 복구했다. 비대화형 환경의 안전 중단을 해소하기 위해
해당 프로세스 범위에서만 `CI=true`를 설정하고 종료 후 기존 값을 복원했다.

### 이유

프로젝트가 이미 필요한 버전과 무결성 정보를 선언·잠금하고 있으므로 새 패키지 결정이나
네트워크 기반 버전 재선택이 필요하지 않다. Corepack 경유는 현재 사용자 환경에서 실제로
동작하는 pnpm 진입점이기도 하다.

### 고려했지만 선택하지 않은 대안

- global pnpm 설치: 시스템 전역 상태를 불필요하게 바꾸므로 제외했다.
- Next.js 자동 설치 재시도: bare `pnpm` PATH 문제가 반복되고 package manager가 lockfile
  정책 밖에서 자동 변경할 수 있어 제외했다.
- package.json/lockfile 수정: 선언 자체는 정확하므로 제외했다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| primary `node_modules` | frozen lockfile에서 devDependencies 포함 상태로 재생성 | 누락된 local 개발 도구 복구 |
| package manifest/lock | 변경 없음 | 선언·잠금 버전은 이미 정확함 |
| 이 구현 노트·INDEX·버전 문서 | 진단·명령·검증 증거 기록 | 재현과 인수인계 |

### 데이터 흐름/상태 변화

애플리케이션 데이터 흐름과 DB 상태 변화는 없다. 패키지 manager가 승인된 store 항목을
root `node_modules`에 다시 연결했으며 407개 package를 모두 기존 cache에서 재사용하고
download 0으로 완료했다.

### 오류·빈 상태·롤백

첫 복구 명령은 비대화형 shell에서 기존 modules 제거 확인을 받을 수 없어
`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`로 안전하게 중단됐다. 프로세스 한정
`CI=true`로 같은 frozen 작업을 재실행해 완료했다. 중간 검증 regex가 JSON-like YAML의
quoted key를 놓쳐 `NO`라고 잘못 표시했으나, 원문 `"devDependencies": true`, `pnpm list`,
실제 경로 해석으로 교차 확인했다.
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
- documentation: 2.21.4

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.10.0-office-directory-runtime | 동일 | 제품 코드 변경 없음 |
| Web | 0.6.0-answer-mode | 동일 | source/계약 변경 없음 |
| API | 3.3.0-draft | 동일 | API 변경 없음 |
| DB schema | 0.4.0-local | 동일 | DB 호출·migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | seed/data 변경 없음 |
| Mock data | 0.0.0-not-populated | 동일 | mock 변경 없음 |
| Prompt set | 0.2.0-grounded-live-chat | 동일 | provider/prompt 변경 없음 |
| Test suite | 1.8.0-local-demo-readiness | 동일 | 테스트 코드 변경 없음 |
| Docs | 2.21.4 | 2.21.5 | 로컬 Web 의존성 복구 증거 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| environment production/omit flag 검사 | process/user/machine에 강제 flag 없음 | 관련 값 출력 없이 상태만 확인 | 이 노트 |
| manifest와 `.modules.yaml` 비교 | package 선언 3개 존재, installed metadata는 devDependencies false | 3 package | 이 노트 |
| `corepack.cmd pnpm install --frozen-lockfile --ignore-scripts --prod=false` | 첫 실행 non-TTY 안전 중단 | exit 1 | 이 노트 |
| 프로세스 한정 `CI=true`로 동일 명령 | PASS, reused 407/downloaded 0 | 14.7s | pnpm stdout |
| `.modules.yaml`, `pnpm list`, Web package 기준 Node resolution 교차 확인 | 3 package 모두 존재·해석 | 3/3 | local shell stdout |
| `corepack.cmd pnpm --filter @sejong-ai/web typecheck` | PASS, `tsc --noEmit` exit 0 | 1 command | local shell stdout |
| package/lock diff와 primary `git status --short` | PASS, tracked diff 0 | 3 files/working tree | local Git |

### 미실행 검증과 이유

Web dev server 실제 재기동은 사용자의 현재 PowerShell foreground 절차로 남겼다. 이
복구에서는 typecheck로 원래 누락된 TypeScript 도구가 실행되는 것까지 확인했고, 브라우저
표시·수동 접근성은 다음 단계에서 사용자가 확인한다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·응답·환경값을 읽거나 출력하지 않았다.
- Security: frozen lockfile, `--ignore-scripts`, Corepack을 사용했다. global 도구, package
  manifest, lockfile, 비밀값 변경은 없다.
- Accessibility: UI source 변경은 없다. 브라우저 수동 검증은 다음 단계다.
- Performance/cost: existing pnpm store만 재사용(reused 407, downloaded 0)했으며 provider
  호출·외부 API 비용은 0이다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경·조회·seed 0
- mock/AI 생성: 변경 0
- schema/lineage: 변경 0
- verified date: 2026-07-26 KST

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- API `/ready=200` 터미널은 유지하고 새/현재 PowerShell에서 아래 명령을 다시 실행한다.
  `corepack.cmd pnpm --filter @sejong-ai/web dev`
- `Ready`가 유지되면 `http://127.0.0.1:3000`을 연다.
- global pnpm 설치나 package.json 수동 편집은 필요하지 않다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `.modules.yaml`의 quoted key 때문에 최초 단순 regex 진단이 false negative를 냈고,
  원문·package list·module resolution 세 가지 증거로 수정 판정했다.
- scoped `CI=true`는 명령 종료 후 이전 process 값을 복원했다.

## 13. 인수인계·재현·롤백

### 재현

1. primary checkout에서 API 터미널을 그대로 둔다.
2. `corepack.cmd pnpm --filter @sejong-ai/web dev`를 실행한다.
3. `http://127.0.0.1:3000`을 열고 `/chat`, `/admin` 표시를 확인한다.

### 롤백

tracked 파일 변경이 없어 Git 롤백은 없다. 캐시가 다시 손상되면 primary checkout에서
프로세스 한정 `CI=true`와 함께
`corepack.cmd pnpm install --frozen-lockfile --ignore-scripts --prod=false`를 재실행한다.
package manifest/lockfile을 고치거나 삭제하지 않는다.

### 다음 개발자 시작점

사용자의 Web 재실행 결과를 받아 수동 화면·키보드·200% 확대 데모 체크리스트를 계속한다.
## 14. 남은 위험·미해결 질문·다음 단계

- Web foreground 실제 재기동과 브라우저 표시는 Pending이다.
- Next dev가 다른 오류를 내면 전체 로그를 받아 새 원인을 별도로 진단한다.
- 이 기록용 브랜치는 아직 push/PR되지 않은 local documentation chain이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

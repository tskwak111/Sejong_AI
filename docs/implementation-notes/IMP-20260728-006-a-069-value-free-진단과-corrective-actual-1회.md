# IMP-20260728-006 — A-069 value-free 진단과 corrective actual 1회

- Date/Time (KST): 2026-07-28T18:37:53+09:00
- Task ID: `A-069-CORRECTIVE-ACTUAL`
- Type: diagnostic-provider-actual-git
- Status: Done — private push PASS, corrective actual FAIL, no rerun
- Author/Agent: 사용자 승인자 / Codex architecture·security·integration
- Branch: `main`
- Base commit: `d973abc`
- Diagnostic source commit: `1f337ad`
- Related: D-105/D-106, A-069/A-070, ADR-0027,
  [runbook](../runbooks/UPSTAGE-HYBRID-RAG-ACTUAL.md),
  [current actual report](../test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md)

## 1. 사용자 요청과 완료 기준

### 요청

private `main` push를 승인하고, A-069을 값 비노출 방식으로 진단한 뒤 corrective actual을
정확히 한 번 실행한다.

### Acceptance Criteria

- 승인된 local `main`을 private origin에 반영하고 SHA 일치를 확인한다.
- 질문·provider body·key·DSN을 출력하거나 저장하지 않는다.
- prior FAIL을 삭제하지 않고 archive한 뒤 value-free failure stage를 기록한다.
- PII-free fixed 20-case corrective actual을 한 번만 실행하고 실패 시 재실행하지 않는다.
- process 종료 뒤 local provider mode false/false, lock 없음, secret scan PASS를 확인한다.
- 결정·모호성·SOT·task·version·구현 노트를 결과와 일치시킨다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 push·진단·1회 실행을 승인했고 Codex가 구현·실행·검증했다. |
| When — 언제 | 2026-07-28 18시대 KST |
| Where — 어디서 | local/private Windows checkout, private GitHub origin, Upstage `solar-pro3` |
| What — 무엇을 | private main push, stage-only diagnostics, archived prior evidence, corrective actual |
| Why — 왜 | strict accepted usage 0이 transport인지 provider 거절인지 구분하고 과장 없는 다음 조치를 정하기 위해 |
| How — 어떻게 | RED/GREEN, exact source commit, process-scoped non-secret profile, one-run sentinel, aggregate report |
| How much — 어느 정도 | private push 1회, actual run 1회, selected 20, provider-free 11, outbound 9, provider body retention 0 |

## 3. 시작 전 상태

- local `main`은 `d973abc`였고 private `origin/main`보다 3 commits 앞서 있었다.
- 최초 D-105 actual은 9 outbound 뒤 usage/match 0이었지만 HTTP·transport·usage·contract
  실패 지점을 나누지 못했다.
- 같은 configured model/endpoint/JSON mode와 key-present profile의 historical CHAT-NATURAL
  actual은 provider 20/20 응답과 60/60 corrective PASS를 기록했다. key 값은 비교하지 않았으므로
  인증이나 request shape를 추측으로 단정할 수 없었다.
- ignored `.env`는 key assignment 1개, model/base pin과 provider mode false/false였다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/결과 | 영향 |
|---|---|---|---|---|
| A-069 | B/High | 최초 FAIL stage와 corrective evidence | 9/9 HTTP 4xx class로 진단, corrective FAIL | actual readiness |
| A-070 | B/High | 정확한 4xx 원인 | Pending — provider console 또는 별도 승인 진단 필요 | key/access/quota/request |
| D-106 | 인간 승인 | private push와 actual 1회 | 실행 완료, 추가 call 0 | Git/provider cost |

## 5. 설계 결정과 대안

### 선택

HTTP는 2xx/4xx/5xx/other family만, transport는 no-response만 기록한다. 2xx 이후에는 usage
parser, closed decision, expected contract match를 단계별 count로 기록한다. status detail,
exception value와 provider body는 버린다.

### 이유

실패 위치는 좁히되 공급자 오류 메시지나 질문이 tracked evidence로 유입되지 않아야 한다.
prior FAIL도 삭제하지 않아 실행 계보를 보존해야 한다.

### 고려했지만 선택하지 않은 대안

- status/body 저장: 정확한 진단은 쉽지만 승인된 value-free 경계를 넘어 제외했다.
- 추측으로 timeout·token cap·prompt를 변경: 최초 evidence가 이를 지지하지 않아 제외했다.
- FAIL 뒤 자동 재실행: exact one-run 승인과 비용 경계를 깨므로 금지했다.
- prior report 덮어쓰기: 실패 이력을 숨기므로 archive 후 canonical report를 새로 만들었다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/run_hybrid_rag_actual.py` | HTTP family·transport·usage·decision·mismatch aggregate | value-free root-stage diagnosis |
| runner tests | RED/GREEN family count, partial/no-response, PASS report 검증 | 진단 회귀 방지 |
| actual runbook | counter 해석과 auditable archive 절차 | 과도한 원인 추정·재실행 방지 |
| archived/current reports | D-105 원본 보존, D-106 corrective FAIL | 실행 계보 |
| SOT/decision/ambiguity/TASKS/version/changelog | A-069 해결·A-070 신규 gate와 FAIL 동기화 | 완료 오인 방지 |

### 데이터 흐름/상태 변화

fixed synthetic PII-free 20 → deterministic provider-free 11 → provider selector 9 →
HTTP-family count → strict usage/decision/match count → aggregate FAIL report다. DB, official
data, citizen event/failed row, remote/public state는 변경하지 않았다.

### 오류·빈 상태·롤백

corrective actual은 9/9 response가 4xx class였고 2xx·5xx·transport/no-response·usage
accepted·decision accepted·match는 모두 0이었다. report는 원자적으로 작성됐고 lock은
해제됐다. process-scoped profile이 종료되어 ignored `.env`의 false/false가 유지됐다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application/Web | `0.12.1` / `0.8.0` | 동일 | 제품 동작 변경 없음 |
| API/shared | `4.0.0-draft` / `1.0.0` | 동일 | 공개 계약 불변 |
| DB schema | `0.5.0-local` | 동일 | DB 사용 0 |
| Official/mock data | `.2` / not populated | 동일 | data bytes 불변 |
| Prompt set | `0.4.0-topic-coverage` | 동일 | prompt 변경 없음 |
| Test suite | `2.1.2-patched-cli-advisory` | `2.1.3-value-free-provider-diagnostics` | actual diagnostic regression |
| Docs | `2.29.2` | `2.29.3` | D-106 evidence·handoff |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 |
|---|---|---|---|
| `git push origin main` | PASS | `d973abc` remote parity | terminal |
| diagnostic RED | expected FAIL | missing counter attribute 1 | focused pytest |
| runner focused tests | PASS | 22 passed | pytest |
| Ruff | PASS | 2 files | terminal |
| Ruff format | first check RED, corrected PASS | 2 files | terminal |
| Mypy | PASS | 1 source file, issue 0 | terminal |
| exact value-free preflight | PASS | profile/key presence/report/lock/source | aggregate console |
| approved corrective actual | FAIL | 20/0/11/9; 4xx class 9 | current actual report |
| post-run modes/lock | PASS | false/false, lock absent | aggregate console |
| secret-pattern scan | PASS | findings 0 | terminal |
| repository docs / staged diff | PASS | missing link 0, whitespace error 0 | terminal |

### 미실행 검증과 이유

- corrective actual 재실행: D-106의 1회 경계를 모두 사용했으므로 실행하지 않는다.
- 전체 API/Web/DB/root gate: 제품 코드·계약·DB/data를 변경하지 않은 diagnostic-only patch로,
  runner focused·docs·security gate를 적용한다.
- public/remote/provider-console 작업: 이번 승인 범위가 아니다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: synthetic PII-free subset만 사용, 질문·provider content retention 0.
- Security: key는 ignored `.env`에서 process memory로만 읽고 출력·복사·commit 0. DSN/DB 사용 0.
- Accessibility: UI 변경 없음.
- Performance/cost: elapsed 7,839ms. observed accepted usage cost는 0이고 ledger의
  conservative USD 0.00684288은 provider invoice가 아니다.

## 10. 데이터와 출처 영향

- 공식 데이터: `0.1.0-initial.2` 19 ACTIVE/OFFICIAL, bytes와 DB row 불변.
- mock/AI 생성: fixed fixture는 test-only synthetic이며 공식 데이터가 아니다.
- schema/lineage: source `1f337ad`, pinned fixture/coverage/official/manifest/offline identities.
- verified date: 2026-07-28 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Hybrid RAG actual은 아직 PASS가 아니다. offline/template 동작은 유지되지만 실제 AI 주제
  선택 품질을 PASS라고 시연하면 안 된다.
- 원인은 transport나 5xx가 아니라 4xx provider client-rejection class다. 현재 evidence만으로
  key 비활성, credit/quota, model project access, request-shape 중 하나를 특정할 수 없다.
- 다음 실제 호출 전에 Upstage console의 key 활성·credit/quota·`solar-pro3` access를 사람이
  확인하고, 추가 status-only 진단/재호출은 새로 승인해야 한다.

## 12. AI 내부 구현 세부 — 인간이 굳이 이해하지 않아도 되는 내용

- late response hook은 body를 메모리에서 strict parse한 뒤 counter만 남긴다.
- deterministic rows의 decision/match는 `not-applicable`로 분리해 provider 품질 분모에 넣지 않는다.
- conservative ledger는 usage 없는 attempt에 worst-case를 예약해 0비용으로 오인하지 않는다.

## 13. 인수인계·재현·롤백

### 재현

재실행하지 않는다. current/archived report, D-106과 A-069/A-070만 검토한다.

### 롤백

tracked diagnostic/docs commits를 revert하고 provider modes false/false를 유지한다. 외부
provider 요청은 되돌릴 수 없으며 DB/data rollback은 없다.

### 다음 개발자 시작점

Upstage console에서 key 활성, credit/quota와 `solar-pro3` access를 값 노출 없이 사람이
확인한다. 이후 승인되면 4xx exact status-only 또는 provider 공식 request-shape 최소 probe를
별도 비용·one-run gate로 설계한다.

## 14. 남은 위험·미해결 질문·다음 단계

- A-070 exact 4xx cause.
- public/remote deployment와 real citizen provider 전송은 계속 별도 승인 범위다.
- current fallback은 안전하지만 실제 provider 가용성 증거가 없으므로 local demo에서는
  template fallback을 기본 기대 동작으로 유지한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 집중 테스트·보안 검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문·secret/provider body 노출 없음
- [x] 구현 노트 INDEX 갱신

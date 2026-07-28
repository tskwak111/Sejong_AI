# Source of Truth와 문서 충돌 해결 규칙

## 1. 목적

기존 업로드 패키지에는 초기 아이디어, 넓은 기능 범위, 오래된 스타터 코드가 함께 있다. 이 문서는 Codex와 인간 개발자가 어떤 문서를 정답으로 사용해야 하는지 고정한다.

## 2. 권위 순서

| 순위 | 위치 | 역할 |
|---:|---|---|
| 1 | `AGENTS.md` | 작업 방식·안전·기록 의무 |
| 2 | `docs/source-of-truth/TEAM_DECISIONS.md` | 최종 제품·범위·기술·정책 결정 |
| 3 | `docs/source-of-truth/PROJECT_PLAN.md` | 일정·P0/P1/P2·인수 기준 |
| 4 | `docs/source-of-truth/RFP_MATRIX.md` | 요구사항 추적과 구현 수준 |
| 5 | `docs/source-of-truth/PRIVACY_POLICY.md`, `APPROVAL_POLICY.md`, `KB_GUIDE.md` | 영역별 필수 정책 |
| 6 | `docs/adr/` | 아키텍처 결정과 트레이드오프 |
| 7 | `contracts/`, `database/` | 현재 코드가 따라야 할 실행 계약 초안/확정본 |
| 8 | `docs/implementation-notes/` | 실제 구현 이력과 증거 |
| 9 | `legacy/` | 역사·참고만 가능, 활성 범위가 아님 |

상위 문서와 하위 문서가 충돌하면 상위 문서를 따른다. 다만 상위 문서가 모호하거나 현실 구현과 불일치하면 임의로 해석하지 않고 모호성 레지스터와 인터뷰를 사용한다.

## 3. 현재 절대 범위

- 4개 민원 분야
- 공식 KB 20건
- 페이지 3개
- 표본 질문 20개 + 회귀 1개
- 관리자 승인형 개선 루프
- 실제 GPS/상태조회/다국어/고급 분석은 P2

2026-07-25의 Q-MVP-001 local/private 마일스톤은 위 최종 범위를 줄이지 않는다. 19개 초기 ACTIVE를
실제 local DB에 반영한 뒤 관리자 개선 루프로 20번째 ACTIVE를 만들고 표본 20·회귀 1·보안·데모를
완주하는 중간 gate다. 외부 LLM 품질 평가, 고급 UI, 100명 부하, 자동 백업과 공개 배포는 이
마일스톤 뒤로 연기하지만 최종 P1 백로그에서 삭제하지 않는다. 상세 권위는 D-058/ADR-0020과
승인된 MVP-001 명세·계획이다.

2026-07-23 Q-LLM-005=A/D-065/ADR-0022는 아직 구현되지 않은 DeepSeek 선택을 대체한다. 외부
공급자는 Upstage exact `solar-pro3`이며, 먼저 local/private server-allowlisted 합성
`T-01`~`T-10` 평가로 한국어 품질·strict JSON·비용을 검증한다. 결정론적 시민 경로는 계속
기본이다. 당시 실제 시민/free-input/public/remote provider 사용 금지는 D-092에서
PII-free allowlisted actual classifier 검증만 좁게 supersede됐고, real citizen/free-input
outbound는 ADR-0026의 개인정보·약관·법무 운영 gate 전까지 금지한다.
2026-07-25 actual은 outbound 30회에서 strict-schema 27/30으로 전체 FAIL했다. 인간 검토 9개
평균 4.8444·최저 4와 VAT 포함 USD 0.004654815는 통과했지만 JSON 100% 기준을 충족하지
못했으므로 D-071에서 선택지 B 미승인과 provider-disabled/template 시민 경로 유지를 확정했다.

이후 사용자는 2026-07-25 Q-LLM-006~012/D-072/ADR-0023으로 **local/private 입찰 시연
MVP에 한해** 근거 제한형 Upstage 시민 답변 생성을 새로 승인했다. 보수적 마스킹, deterministic
supported intent, ACTIVE/OFFICIAL 검색과 근거 gate를 모두 통과한 요청만 마스킹 질문과 최소
KB를 보낸다. 모델은 summary와 server-issued fact ID만 제안하고, 공식 fact text·출처·기관·정책
결과는 서버가 결합한다. 8초·1 attempt·hidden retry 0이며 검증이나 호출 실패 시 모델 결과 전체를
버리고 기존 공식 template로 답한다. LLM-002 actual FAIL 증거는 그대로이며 public/remote/실제
기관 운영은 별도 개인정보·보안·비용·배포 승인 전까지 계속 금지한다. 현재 상태는 설계·D-073
written specification·D-074 8-task 실행계획 승인에 따른 offline 구현·task-scoped review·
provider-disabled final root gate 완료와 D-075 local actual PASS다. final 10건은
GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 사실 mismatch 0, PII-free fixture의 typed
write-boundary forbidden-value 위반 0,
outbound 10이었다. legacy runner의 VAT 포함 USD 0.001319835는 usage completeness를 강제하기
전 reported lower-bound이며, configured maximum USD 0.0135168은 USD 0.05 cap 아래다. 종료 뒤
provider-disabled TEMPLATE로 복원했다.
corrective second 10-call run의 governance incident는 D-076에서 사용자가 사후 확인하고 PR #13
병합을 승인해 A-049를 해결했다. D-077/Q-DB-CLEANUP-001=A에 따라 오표시 metadata 22행은
현재 유지하고 해당 local DB snapshot의 event 통계를 평가 KPI로 사용하지 않는다. 정식 수치가
필요해지는 시점의 local reset·정식 `.2` 재시드·필요한 19→20 승인 흐름 재현은 B의 별도 인간
승인을 받는다. 이는 future provider rerun, DB reset/delete/update, public/remote 또는 실제 기관
운영 승인이 아니다.

2026-07-27 Q-CLASS-001=A/D-086/ADR-0025는 future local/private 질문 분류를 hybrid로
확장하는 방향을 승인했다. PII·policy·명백한 결과는 deterministic server gate가 유지하고,
안전하게 마스킹됐지만 애매한 현재 질문만 Upstage closed-enum classifier에 전달한다. 모델은
답변·출처·저장 여부를 결정하지 못한다. Q-CLASS-002=A/D-087은 classifier를 요청당 1회·3초·
retry 0·입력 1,024자·출력 128 token·process sub-cap 20으로 제한하고, 기존 grounded
generation의 8초·1회·sub-cap 30과 합친 process cap을 40, local synthetic run 비용 stop
line을 VAT 포함 USD 0.05로 고정한다. exact schema written specification·실행계획·별도 local
D-092가 PII-free allowlisted actual classifier 실행을 승인했고 D-093은 offline classifier
runtime과 local 00680/00700/admin/Web 구현 검증을 기록했다. public/remote 시민 검증은
ADR-0026에 따라 provider-disabled와 admin-disabled가 기본이며 real citizen/free-input
provider 전송은 계속 금지한다.

2026-07-27 Q-PROD-REAL-001=A/D-088은 제품 목표를 **현실형 민원 안내·운영센터**로 확정한다.
자연스러운 구조화 대화, 승인된 공식 근거, 기관 연결, 범위 확대 검토와 사람 승인 개선 루프를
고도화한다. 실제 신청·상태조회·결제·정부24/기관 내부 시스템 연계는 현재 P2로 유지하며 이
제품이 처리 완료를 보장한다고 표현하지 않는다. 향후 실제 처리 플랫폼으로 바꾸려면 기관 API,
본인인증, 법무·개인정보, transaction·감사·보상과 production 배포를 별도 discovery/승인한다.

D-089/D-090의 CHAT-NATURAL 설계 1~2부는 privacy-first hybrid pipeline과 context v2를
승인했다. `CIVIC_SCOPE_GAP`은 public `intent=OUT_OF_SCOPE`+새 fallback reason, candidate
false이며 별도 queue에 마스킹 text만 30일 보관한다. NON_CIVIC·개인조회·법적판단·privacy
unresolved는 text/event/failed/review row 0이다. context v2는 topic/pending-slot/dialog-act
같은 closed server ID만 사용하고 raw transcript·프로필은 금지한다. exact contract/DB와
runtime은 D-091의 통합 written specification을 구현 권위로 사용한다.

D-091은 classifier/generator 오류·성능·60개 분류/5개 후속/7개 장애 acceptance와 세 수직
흐름을 확정했다. D-092는 PII-free allowlisted actual Upstage, local DB reset·immutable `.2`
정식 seed, `00680` scope queue와 ADR-0018의 `00700` public hardening, 구성된 remote 시민 경로
검증을 승인한다. secret·DSN·raw payload를 출력하지 않고 remote target을 추측하지 않는다.
인증 없는 public 관리자 경로는 승인 범위가 아니며 계속 fail-closed로 비활성이다. actual provider,
formal `.2` seed/19→20과 remote 작업은 unit/area gate 뒤 통합 명세의 비용·rollback·증거
경계를 따라 수행한다. local 00700은 exact 22 property-only 변경과 11-file pgTAP/11-stage
rollback·replay를 통과했지만 remote 배포 완료를 뜻하지 않는다.

2026-07-27 D-095 actual evidence에서 frozen 60 classifier는 deterministic 40/provider 20,
policy/privacy outbound 0, corrective 60/60으로 PASS했고 두 bounded run 누적 비용은 VAT 포함
USD 0.003873210이다. provider request/response와 key는 저장하지 않았다. 같은 시점 remote
discovery는 public application target, remote DB project, deployment credential/origin/saved
version을 찾지 못했다. 따라서 remote migration·seed·deploy·smoke는
`Not executed: target not configured`이며 local DB ACTIVE 20과 00700 evidence를 remote
production-ready로 해석하지 않는다.

2026-07-27 `CLASSIFIER-RUNTIME-WIRING-001`은 위 classifier adapter와 `ChatService` port가
실제 local `create_local_app()`에 조립되지 않았던 완료 판정 결함을 교정했다. exact
classifier-only/combined profile에서 ambiguous safe question만 classifier를 사용하며,
combined profile은 classifier 20/generator 30/combined 40의 같은 process ledger를 공유한다.
 NON_CIVIC·PERSONAL_LOOKUP·LEGAL_JUDGMENT·privacy/policy fast path는 provider 호출과 질문
 row가 계속 0이다. API 계약·DB·공식 데이터·public/remote 경계는 변하지 않는다.

2026-07-27 Q-RAG-001=A, Q-DATA-RAG-001=A와 D-096~D-102는 위 hybrid classifier를
**ACTIVE topic catalog와 coverage grounding을 사용하는 제한형 Hybrid RAG**로 개선하는 목표를
확정한다. current ACTIVE/OFFICIAL projection과 non-factual versioned coverage metadata의
교집합만 최대 20개 catalog로 만들고, exact approved·unique lexical·validated semantic
`topic_id+coverage_id`·validated context facet 중 하나가 있을 때만 top-1 KB를 사용한다.
모델은 답변·사실·출처·기관·저장 여부를 생성하거나 결정하지 못하며 서버가 current membership,
intent, coverage와 source를 다시 검증한다. vector/embedding, 새 dependency, DB migration,
official `.2` 수정과 다중 KB 합성은 이 구현 범위가 아니다.

generic certificate는 등본/초본/차이 3개로 시작하고 move/waste/tax의 generic 질문은 해당
intent의 bounded topic 선택지를 제시한다. 지역은 chat 입력창 위에 항상 표시하되 같은 탭
React memory에서만 새 대화 후 유지하고 browser/server storage에는 넣지 않는다. local
interactive provider target은 classifier 80/generator 100/combined 160, 3초/8초, retry 0,
concurrency 1, request hard wall 12초, VAT 포함 USD0.20 pre-reservation stop이다. historical
20/30/40·USD0.05 actual은 과거 evidence로 보존한다. D-103의 명세·계획 승인 뒤 Tasks 1~9
local/offline 구현과 독립 검토가 끝났고 D-104가 이를 통합한다. immutable official `.2`의
runtime ACTIVE/OFFICIAL 교집합은 19이며 metadata의 20번째 topic을 허위 ACTIVE로 만들지 않는다.
offline UAT는 48/48, official 57/57, classifier 60/60, focused 91 PASS·skip 0이다. Task 10
PII-free Upstage actual은 정확히 한 번 실행해 20 selected·skip 0·11 provider-free·9 outbound를
기록했지만 strict accepted usage와 provider match가 0이라 FAIL했고 재실행하지 않았다.
2026-07-28 D-106의 별도 승인으로 prior FAIL을 archive하고 value-free failure-stage counters를
추가한 source `1f337ad`에서 corrective actual을 정확히 한 번 더 실행했다. 9/9 outbound는 모두
HTTP response를 받았지만 전부 4xx class였고 2xx·5xx·transport/timeout·usage parse·closed
decision·route/topic match는 0이었다. 따라서 provider client-rejection 단계까지는 진단됐지만
auth/access/request-shape/quota 중 정확한 원인은 보관하지 않은 body/status detail 없이
단정하지 않는다. corrective 결과도 FAIL이며 추가 실제 호출은 새 승인 전 금지한다.
Q-LLM-013=A/D-107은 closed selector prompt의 누락된 명시적 `JSON만` 지시만 TDD로 복원했다.
source `4cb42ff`의 단 한 번 corrective actual은 동일 20 selected·11 provider-free·9 outbound에서
9/9 HTTP 2xx와 accepted usage, 4xx/5xx/transport 0을 기록해 D-106의 request-validation 4xx를
해소했다. 그러나 strict closed decision accepted와 route/topic match는 0/9이므로 전체 결과는
여전히 FAIL이고 재실행하지 않았다. 본문 비보관 경계 안에서 정확한 response-validation 단계는
A-071로 남으며 local runtime은 fail-closed fallback을 유지한다.
D-108은 A-071의 후속으로 production parser가 fixed terminal enum 하나만 optional observer에
전달하고 runner가 aggregate count만 기록하는 value-free 진단 설계를 승인했다. body·status
detail·exception·key·DSN과 per-fixture stage는 기록하지 않는다. public parser·시민 fallback·
prompt·provider profile·API/DB/data/dependency는 불변이며 written spec 확인 전 구현과 provider
call은 0이다.
D-109는 위 written specification과 RED/GREEN inline plan을 승인했다. contract-stage parser,
production enum-only observer, aggregate runner, clean source commit, fixed exact-one actual
순으로 실행하며 actual 전까지 prompt/profile/API/DB/data/dependency는 고정한다.
D-110은 A-071의 code/test/runner 구현을 완료했다. production parser는 HTTP response마다
13개 fixed terminal enum 중 하나만 optional observer에 전달하고, observer 오류는 시민
decision/fallback을 바꾸지 않는다. runner는 전체 aggregate count만 기록하며 per-fixture stage,
질문·provider body·status detail·exception·key·DSN은 기록하지 않는다. 142개 집중 테스트와
Ruff/Mypy가 통과했고, clean source commit 뒤 exact-one actual만 남았다.
Task 11 local/private 마감은 browser 27/27, API 2,357 pass·8 local-DB skip, contracts 96/96,
Mypy 114와 secret/bundle/protected diff 0으로 완료했다. 단 한 번의 final aggregate wrapper는
FORMAT-API에서 exit 1이므로 PASS로 승격하지 않으며, formatter 교정 뒤 당시 미실행 constituent는
모두 별도 PASS했다. public/remote, DB reset/seed, official `.2` 수정과 자동 merge는 아직
완료가 아니다. 상세 권위는 ADR-0027과
`2026-07-27-bounded-hybrid-rag-conversation-design.md`다.

## 4. 변경 절차

제품 범위, 공개 계약, DB, 개인정보, 외부 공급자, 배포 아키텍처가 바뀌면:

1. 인간 승인
2. ADR 또는 결정 로그
3. source-of-truth 갱신
4. 계약/스키마/테스트 갱신
5. 버전 매니페스트 갱신
6. 구현 노트 기록

## 5. Legacy 사용 규칙

- 코드를 재사용하기 전 현재 계약·보안·범위와 비교한다.
- 오래된 엔드포인트/데이터/범위를 그대로 복구하지 않는다.
- 재사용한 코드의 출처와 변경 이유를 구현 노트에 기록한다.
- legacy 자체는 자동 포맷·대규모 수정하지 않는다.

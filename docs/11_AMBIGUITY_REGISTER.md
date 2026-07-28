# 모호성·미지의 영역 레지스터

Codex는 초기 감사에서 이 목록을 검증하고 추가/해결한다. 이미 결정된 것은 재질문하지 않는다.

| ID | 우선도 | 영역 | 현재 상태 | 질문/결정 | 기본 추천 |
|---|---|---|---|---|---|
| A-001 | A | LLM | Resolved historically / provider superseded | DeepSeek exact model 선택은 D-065로 대체; 합성 전용, max 1024, concurrency 1, retry 1, run당 outbound attempt 30과 fallback 원칙은 유지 | Q-LLM-004 / D-023 / ADR-0005/0022 |
| A-002 | A | 개발환경 | Resolved | Node 24.x+pnpm, Python 3.12+uv; exact patch는 스캐폴딩에서 고정 | Q-DEV-001 / D-010 |
| A-003 | A | DB/배포 | Resolved for local; public deferred | Supabase CLI 버전 SQL migration과 Docker local stack 사용. 공개 DB·원격 push는 별도 승인 | Q-DB-001 / ADR-0008; 설치는 계획 승인 후 |
| A-004 | A | Admin 보안 | Resolved | local/private 전용, 공개 시 서버측 gate 없이는 관리자 경로 비활성 | Q-SEC-001 / ADR-0007 |
| A-005 | A | 데이터 | Resolved | AI/Data·Backend 작성, PM 승인, 2026-07-20 목표 | Q-DATA-001 / D-011 |
| A-006 | B | 마스킹 | Resolved with review gate | 이름·상세주소는 재현율 우선 보수적 감지. 과잉 마스킹이 성공률 80% 미달 원인으로 입증돼도 B 전환은 재승인 | Q-PRIV-002 / ADR-0004 |
| A-007 | B | 검색 | Defaulted / Deferred | MVP는 keyword/metadata만 사용하고 embedding flag는 off | ADR-0006; 품질 근거와 비용 승인 전 활성화 금지 |
| A-008 | B | CI·source remote | Resolved / external bootstrap verified | private `tskwak111/Sejong_AI` remote, initial `main` push, hosted policy/Frontend CI PASS, collaborator/variable/read-only Actions evidence를 확인했다. Windows/Docker/external-provider local gate는 유지한다 | D-021 partially superseded by D-047~D-055 / ADR-0019 |
| A-009 | B | 데모 | Defaulted / Deferred | 현재 완료 기준은 local live demo+재시작 runbook. 공개 URL·녹화본은 별도 발표/배포 승인 시 선택 | D-013/D-021 범위의 0원·local-first 기본값 |
| A-010 | C | UI | Defaultable | 디자인 시스템 세부 | 기존 아이디어노트 톤, 접근성 우선 |
| A-011 | C | 코드 | Defaultable | 모듈 명명·파일 분할 | framework conventions |
| A-012 | A | 저장소 | Resolved / private hosting successor approved | 원본 원격 없이 독립 Git repo와 `main`을 시작한 역사적 결정은 유지하며, 후속 private GitHub source remote는 D-047/COLLAB-001이 소유 | Q-REPO-001 / D-009 / D-047 / ADR-0019 |
| A-013 | A | 개인정보 | Resolved | 30일 후 masked text만 파기, 행·비텍스트 메타·후보 FK 유지 | Q-PRIV-001 / ADR-0004 |
| A-014 | A | 대화 | Resolved / context v2 implemented | 현재 탭 메모리 transcript + 15분 서명형 client-carried context. v2는 topic ID·pending slot·dialog act 등 closed server ID만 허용하고 v1은 최대 TTL read-only 호환, issuer는 v2 only다. 서버 세션·raw transcript 없음 | Q-CHAT-001 / D-024/D-089/D-090/D-093/D-104 / ADR-0010; context/UAT PASS |
| A-015 | B | 오류 계약 | Resolved | 정책 응답은 200, 안전 대체가 없는 기술 장애는 503 `SERVICE_UNAVAILABLE` envelope | Q-API-001 / ADR-0009 |
| A-016 | B | 복구 | Defaulted for disposable local demo; public deferred | 재현 가능한 migration+승인 seed 우선, 파괴 변경/마일스톤 전 gitignored 수동 dump, local RPO 24h/RTO 60m, 30일 넘은 dump 삭제, 복구 후 개방 전 retention 재실행 | 실제/비재현 데이터·공개 운영 전 인간 재승인 |
| A-017 | B | DB 안전 경계 | Resolved | Q-DB-002: DB function/trigger/RLS/GRANT + 백엔드 이중 검증 | 2026-07-16 사용자 A 승인 / D-025 / ADR-0011 |
| A-018 | A | DB role 보안 | Resolved | Q-SEC-002=A: non-superuser PG17 runner 유지, 허용된 role 속성 재적용+catalog 검증, unsafe role fail closed | D-026 / ADR-0011; privileged auto-downgrade/bootstrap 없음 |
| A-019 | A | 관리자 workflow | Resolved | Q-WF-001=A: 별도 backend-only `confirm_failed_question_reason(uuid,text,text,text)` capability | D-027 / ADR-0011; event 자동 사유 불변, failure 사유·적격성 재계산 |
| A-020 | A | DB trigger 권한 | Resolved | Q-DB-003=A: 새 `00600`에서 ACTIVE-question validator 하나만 SECURITY DEFINER+owner/`search_path=pg_catalog, pg_temp`/revoke 검증, compensation은 INVOKER | D-028 / ADR-0012; 사용자의 직전 추천안 뒤 계속 진행 지시를 A 승인으로 해석, 문자 A 직접 입력 아님; `pg_temp` 마지막 명시는 D/Internal 보안 보정 |
| A-021 | B | 기존 DB function 보안 | Resolved / implemented and locally verified | audit exact 22 graph에 `00700` property-only `search_path=pg_catalog, pg_temp` 보정, matching rollback과 body/owner/ACL fingerprint를 적용했다. | Q-SEC-003=A / D-046/D-092/D-093 / ADR-0018; 11-file pgTAP·11-stage replay PASS, remote smoke 별도 |
| A-022 | A | local Docker port 보안 1차 결정 | Resolved decision / remediation insufficient | Q-SEC-004=A로 Docker Desktop `PortBindingBehavior=default-local-port-binding`을 적용·재시작했다. 빈 HostIP probe는 IPv4 `127.0.0.1`과 IPv6 wildcard `::`를 함께 만들었고 explicit `127.0.0.1` probe만 단일 loopback이었다. | D-029; 승인 결정은 기록하되 exact local 완료 근거로 사용하지 않음 |
| A-023 | A | local Docker IPv6 port 보안 2차 결정 | Resolved decision / remediation insufficient | Q-SEC-005=A로 `local-only-port-binding`을 적용·재시작했지만 HostIP 생략 probe는 다시 `127.0.0.1`+`::`였다. explicit `127.0.0.1` control만 단일 loopback이었다. | D-030; 승인 설정은 유지하지만 exact local 완료 근거로 사용하지 않음 |
| A-024 | A | local Supabase CLI port 공급망 | Resolved / implemented and verified locally | Q-SEC-006=A. official v2.109.1 exact source의 local DB start HostIP만 `127.0.0.1`로 지정하는 project-local patched CLI를 source/tag/commit·patch·Go 1.25.11·binary SHA-256과 함께 pin했고 actual gate를 통과했다. | D-031 / ADR-0013; local/private DB authority, public readiness 아님 |
| A-025 | A | Windows patched CLI build workspace | Resolved / implemented and verified locally | 사용자가 2026-07-18 Q-TOOL-001=A를 명시했다. 두 checkout `.tools/s/{a,b}`, pinned relative max 134자·absolute cap 248자 pre-checkout gate와 legacy deny-only 경계를 구현·검증했다. | D-032 / ADR-0014; 기존 장경로 partial artifact 자동 삭제 없음 |
| A-026 | B | 공식 데이터 staging·승인 artifact | Resolved / PM evidence complete | Q-DATA-002=A: `data/staging/data-001/<draft-version>/`의 KB·기관·매핑 JSON과 hash-bound approval manifest를 canonical authoring/approval evidence로 사용하고, 승인 record만 후속 immutable official release로 승격 | D-033/D-035 / ADR-0015 / DATA-001 plan; canonical manifest APPROVED, 35 comments, final 19/3/10, 63-test/hash review PASS |
| A-027 | A | PM 승인 증거 | Resolved / materialized and verified | Q-DATA-003=A: `PM-LOCAL-001`, current 35 recommendations, `2026-07-19T02:06:19+09:00` final confirmation | D-035; DATA-001 approval evidence complete, official release/seed not authorized |
| A-028 | A | official release·seed | Resolved decision / filesystem release delivered; actual DB Blocked by A-030 | Q-SEED-001=A: immutable filesystem release+existing-schema transactional seed; empty disposable local compensation only | D-036/D-038/D-039/ADR-0016; `.1` 19/3/10 published/verified, dispatcher active+auto-seed disabled, actual DB stopped before seed |
| A-029 | B | 홈→채팅 진입 | Resolved / implemented and verified | Q-WEB-001=A: no-input/no-storage/no-fetch accessible static `/chat` preparation route and home CTA | D-037/WEB-HOME plan/IMP-20260719-005; final review 0/0/0 |
| A-030 | A / Blocker | official seed correction | Resolved / supported local actual PASS | Q-SEED-002=A: migration의 three-`EXISTS` effective-option union 권위를 유지한 immutable `.2` successor는 게시·검증 완료. 역사적 4회 concurrency B failure 뒤 observer 교정 continuation이 전체 cycle을 PASS | D-044/D-058/D-062/D-064 / ADR-0017/0020. `.2` 불변, 19/3/10/replay/compensation/final projection/cleanup PASS, `official_data=0.1.0-initial.2`; READY/20th ACTIVE 별도 |
| A-031 | B / High | unresolved PII consumer response | Resolved / MVP consumer plan approved | Q-PII-002=A: contract에 `PRIVACY_UNRESOLVED` 전용 reason과 HTTP 200 안전 재질문 응답 | D-045/D-058 / ADR-0004/0020. local milestone은 failed row·DB event 0; persistent metadata migration은 reserved `00700` 이후 |
| A-032 | A / Blocker | public phone-shaped value masking | Resolved / AI-001A plan approved | Q-PII-003=A: 시민 질문의 “공식 대표번호” label을 신뢰하지 않고 모든 phone-shaped value를 마스킹 | D-043 / ADR-0004; 공식 연락처는 승인된 KB·기관 metadata/card에서만 서버 결합 |
| A-033 | A | Git source remote·access | Resolved / App scope confirmed | private `tskwak111/Sejong_AI`, merge commit `ce8a6085fb57670ca74e009ed45e3d02d784c24b`, post-merge hosted CI, `koregy` write/variable과 사용자의 GitHub UI `Only select repositories / Sejong_AI` 확인을 기록했다 | D-047/D-053~D-057 / ADR-0019 |
| A-034 | A | Frontend ownership | Resolved | Q-OWN-001=A: 인간 팀원이 세 페이지·typed client·화면 상태·반응형·접근성·frontend unit/E2E 전체 소유 | D-048 / frontend handoff; contract/backend/DB/data/security는 owner 요청 |
| A-035 | B | GitHub plan·enforcement | Resolved | Q-GIT-002=A: GitHub Free·0원, private branch protection/CODEOWNERS 강제를 전제하지 않음 | D-049 / ADR-0019; PR·CI·scope policy와 사람 규칙, Pro 전환은 재승인 |
| A-036 | B | Frontend merge | Resolved policy | Q-GIT-003=B: 허용 frontend-only green PR은 팀원 자가 병합, 경계 밖은 사용자 검토 | D-050 / ADR-0019; GitHub Free 기술적 완전 강제 아님 |
| A-037 | A | Codex Cloud merge·secret | Resolved policy | Q-CLOUD-001=A: Cloud는 branch+Draft PR만, 사람이 merge; secret·external LLM·Docker actual 없음 | D-051 / ADR-0019 |
| A-038 | A | Collaboration operating model | Resolved spec / In Progress execution | Tasks 1~4 완료, Task 5 partial, Task 6 partial, Task 7 pending. App scope·PR #1 merge/post-merge CI·secret-free Cloud environment 저장은 확인됐고 teammate MFA/recovery·첫 PR-only rehearsal, Cloud docs-only task/Draft PR/manual merge와 나머지 Task 7 rehearsal이 남았다 | D-052~D-057 / collaboration design and plan |
| A-039 | A / Blocker | Git author identity privacy | Resolved | Q-GIT-004=A: 해당 email이 사용자 본인 것이며 private Frontend collaborator에게 보여도 괜찮음을 확인. 현재 history와 모든 SHA를 보존하고 noreply rewrite를 하지 않음 | D-053/D-054 / ADR-0019; 승인된 pre-push gate를 통과한 뒤에만 private push |
| A-040 | A / Blocker | 7/25 MVP scope·schedule | Resolved / Done — local/private scope integrated by PR #9 | Q-MVP-001=A: final local 19→20, sample 20/20, full root/DB/API/Web gate PASS | D-058/ADR-0020. PR #9 merged; manual demo·a11y Pending. external provider·100명·backup·advanced UI·public deploy는 별도 |
| A-041 | B / High | 범위 밖 개인조회·법적판단 표현 | Resolved / Q-MVP-002=A | 공개 응답은 `intent=UNKNOWN`+정확한 정책 reason, 후보 false; local MVP에서 text/event/failed row 0 | D-059/ADR-0021; sample T-16~T-18 실행 승인 |
| A-042 | A / Blocker | 관리자 DB read capability | Resolved / Q-DB-004=A | local/private 전용 `00650` migration+rollback+pgTAP+repository adapter 승인 | D-060/ADR-0021; public admin/remote/00700 불변 |
| A-043 | B / High | chat 재시도 idempotency | Resolved / Q-API-002=A | optional UUID header, Web retry key 유지, correlation 분리, `00660` durable dedupe 승인 | D-061/ADR-0021; raw question 저장 0, local 24h TTL |
| A-044 | A / Blocker | LLM 공급자 전환·합성 평가 경계 | Resolved — actual FAIL / 당시 option B not approved | Q-LLM-005=A local/private actual 완료: Upstage exact `solar-pro3`, outbound 30, strict-schema 27/30, 인간 검토 9개 평균 4.8444·최저 4, VAT 포함 USD 0.004654815. JSON 100% criterion 미충족 | D-065~D-067/D-071/ADR-0022/LLM-002 report의 historical verdict. 후속 local 시민 경계는 A-048/D-072가 supersede하며 public/remote 금지는 유지 |
| A-045 | B / High | PM 데모의 개인조회와 개선 질문 분리 | Resolved / local actual PASS | #4 PERSONAL_LOOKUP은 interaction event/failed row delta 0, #5 별도 INSUFFICIENT_GROUNDING은 delta 1/1 뒤 19→20 승인 루프와 재질의 SUCCESS | D-068/D-059, Q-PM-DEMO-001 plan; backend runner와 actual browser evidence PASS |
| A-046 | B / High | 공식 서비스명 | Resolved | 공식 서비스명은 `세종 민원이음`; 옛 작업명은 활성 문서에서 교정하고 역사 증거는 보존 | D-069 / POST-MVP-001 |
| A-047 | B / High | local dev config 소유 경계 | Resolved / owner review | PR #10의 exact `127.0.0.1` 개발 origin은 owner가 인계하고 팀원 config 권한과 public CORS 범위는 넓히지 않음 | D-070 / WEB-DEV-ORIGIN-001 |
| A-048 | A / Blocker | local 시민 chat 외부 LLM 경계 | Resolved / local actual PASS | Q-LLM-006=B·007=A·009=A·011=C·012=B와 D-073 명세·D-074 계획·D-075 actual 승인: supported+masked+ACTIVE/OFFICIAL+grounded만 masked question+최소 KB 전송, `solar-pro3` 8초 1 attempt, server-issued fact ID·server-bound source, 검증 실패 전체 template fallback, `answer_mode` 배지 | actual PII-free fixture 10건 GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 mismatch 0, typed write-boundary forbidden-value 위반 0, outbound 10. legacy cost lower-bound USD 0.001319835, configured upper USD 0.0135168<0.05. public/remote/실제 기관 운영 금지 |
| A-049 | B / High | D-075 actual corrective rerun의 사후 governance 확인 | Resolved / human acknowledged 2026-07-26T13:31:56+09:00 | D-075와 runbook은 10-call actual gate 1회를 승인했지만 첫 semantic PASS 뒤 aggregate-only stdout 보정을 위해 별도 재승인 없이 10-call run을 한 번 더 실행했다. 총 20 provider calls, legacy-reported lower-bound USD 0.002635710과 22개 오표시 metadata row가 발생했다. configured 20-call upper bound는 USD 0.0270336이다. | 사용자가 exact acknowledgement로 incident를 사후 확인하고 PR #13 병합을 승인했다(D-076). 이 확인은 future provider rerun, 22행 삭제, public/remote 권한을 승인하지 않으며 future rerun은 매번 새 인간 승인이 필요하다. |
| A-050 | B / High | 오표시 actual metadata 22행 cleanup | Resolved / Q-DB-CLEANUP-001=A | 현재 22행을 delete/update/reset하지 않고 개발을 계속한다. 이 local DB snapshot의 event 통계는 평가 KPI로 사용하지 않는다. | D-077. 정식 수치가 필요해지는 시점에만 B의 local reset→migration→immutable `.2` seed→필요한 19→20 승인 흐름 재현을 별도 승인받는다. future provider rerun과 targeted cleanup도 별도 승인이다. |
| A-051 | B / High | declared office endpoint 존치와 runtime 정합 | Resolved / PR #15 merged; bounded local actual smoke PASS | existing `GET /api/v1/offices`를 required region+supported intent, OFFICIAL-only, deterministic order와 safe 503으로 FastAPI에 구현하고 `/ready=200`, match `200/count=1`, valid empty `200/count=0`을 확인했다. | D-078/D-080/D-081 / OFFICE-API-001 spec·plan·IMP-013. DB/data/Web/LLM/dependency/public/remote 불변 |
| A-052 | B / High | PERF-001 chat 부하의 local DB write 대상 | Resolved by D-092 / disposable clean DB | 100 VU·60초 read-only harness와 cached/fixed `/api/v1/chat` 부하는 current non-KPI DB가 아니라 reset·정식 `.2` seed한 disposable clean local DB에서 실행한다. | 질문/응답 원문 log 0, provider-disabled performance fixture, aggregate-only 결과와 cleanup을 강제한다. |
| A-053 | B / High | generic 증명서 FOLLOWUP 반복 | Resolved / implemented offline | 첫 단계 등본/초본/차이 exact 3개와 signed `CERTIFICATE_KIND` context를 구현하고, 차이 답변 뒤 source-backed 관련 질문을 제공한다. | D-098/D-102~D-104; UAT exact options/pending slot PASS |
| A-054 | B / High | 일반 관리자 KB 후보 작성 | Resolved / Implemented | arbitrary eligible failure에 운영자 공식 form→별도 승인 capability 사용 | D-093; fixed Web builder 제거·admin tests PASS |
| A-055 | B / High | 시민 최초 지역 선택 진입점 | Resolved / Implemented | 직접 읍·면·동 선택/변경과 official office card | D-093; Slice 2 Web/E2E PASS |
| A-056 | C / Defaultable | 관리자 후보 상태 이력·문구 | Resolved / Implemented | DRAFTED/PENDING/APPROVED/REJECTED tabs+count와 운영자 작성 문구 | D-093; Web tests PASS |
| A-057 | B / High | 일반 한국어를 이름으로 오탐하는 PII gate | Resolved / Implemented | positive fail-closed corpus를 보존하며 일반 의문·행정명사 negative 교정 | D-093; privacy tests PASS |
| A-058 | A / Blocker | local/private 질문 분류의 LLM 경계 | Resolved / Implemented / actual PASS | deterministic safety 뒤 masked ambiguous-only bounded classifier, server authority 유지 | D-086/D-091~D-093/D-095/ADR-0025; 60/60 |
| A-059 | A / Blocker | 현재 네 분야 밖 행정 민원의 저장·검토 정책 | Resolved / Implemented | `CIVIC_SCOPE_GAP`, separate 30-day queue, event/failed/candidate·자동 ACTIVE 0 | D-085/D-090~D-093/ADR-0024; 00680 replay PASS |
| A-060 | A / Blocker | hybrid 분류와 grounded generation의 provider 호출·비용 상한 | Resolved / implemented; actual fail-closed | historical actual 20/30/40·USD0.05는 보존하고 local interactive demo는 80/100/160·USD0.20 pre-reservation stop, retry 0, concurrency 1로 구현했다. | D-087/D-095 historical; D-099/D-102~D-105; actual 20은 cap 아래 FAIL |
| A-061 | A / Blocker | “현실에서 사용 가능한 민원처리”의 목표 경계 | Resolved / Q-PROD-REAL-001=A | 현실형 안내·운영센터를 고도화한다. 실제 신청·상태조회·결제·기관 시스템 연계는 P2로 유지하고 처리 완료를 주장하지 않는다. | D-088. 자연 대화·공식 근거·기관 연결·scope-gap·사람 승인 운영을 우선하며 실제 처리 전환은 별도 discovery/승인 |
| A-062 | D / Internal | Next dev tracked 생성물 안정성 | Investigated / no change | `next dev`가 tracked `next-env.d.ts`를 build-types import에서 dev-types import로 바꿔 정상 실행만으로 worktree가 dirty해진다. | 사용자 생성 변경을 보존하고 Next 권장 정책 조사 뒤 별도 내부 위생 수정 |
| A-063 | B / High | controlled public 시민 demo의 공급자·계정·리전·origin·비용·DNS·saved rollback version | Pending / target not configured | 현재는 remote migration·seed·deploy·smoke 0; 구성 전까지 local/private와 code/runbook evidence만 유지 | D-092/D-095/ADR-0026; human infrastructure setup |
| A-064 | A / Blocker | 20개 ACTIVE KB의 자유 표현·후속질문 검색 방식 | Resolved / implemented offline | 최대 20개의 request-local ACTIVE/OFFICIAL catalog에서 closed `topic_id+coverage_id`를 제안하고 서버가 membership·intent·coverage를 검증한다. exact approved·unique lexical·validated semantic·context facet evidence가 없으면 성공시키지 않으며 top-1 KB만 사용한다. | D-096/D-100~D-104; immutable `.2` runtime intersection 19, UAT PASS |
| A-065 | B / High | 지역 선택의 상시 표시·새 대화 유지 범위 | Resolved / implemented and Web-verified | 입력창 위 compact 선택/변경을 항상 표시하고 새 대화에서도 같은 탭 React memory의 지역만 유지한다. transcript/context는 초기화하고 browser/server storage는 사용하지 않는다. | D-097/D-102~D-104; Web unit/E2E PASS |
| A-066 | B / High | 주민등록 증명서 FOLLOWUP 선택지 계층 | Resolved / implemented offline | 첫 단계는 등본/초본/차이 exact 3개. 차이는 공식 KB 답변 뒤 열람·무인발급기를 관련 질문으로 제공하고 scope-gap 증명서는 섞지 않는다. | D-098/D-102~D-104; UAT exact options/pending slot PASS |
| A-067 | A / Blocker | 긴 local UAT에서 lifetime provider cap 소진 | Resolved / implemented and actual bounded | local interactive demo는 classifier 80/generator 100/combined 160, VAT 포함 USD0.20 pre-reservation stop. cap 실패는 무저장 분야 선택 FOLLOWUP이며 production rate limit은 별도다. | D-099/D-102~D-105; metering PASS, actual conservative charge USD0.00684288 |
| A-068 | B / High | Hybrid RAG 전에 새 공식 KB를 추가할지 | Resolved / Q-DATA-RAG-001=A | 기존 tracked 19+local governed 20th facts로 retrieval 구조를 먼저 교정하고, 행정 사실이 아닌 versioned topic descriptor·비식별 synthetic UAT/negative coverage fixture만 추가한다. 냉장고·재산세 상세 등 새 사실은 근거 부족으로 닫고 후속 official-data/PM 승인 cycle로 분리한다. | D-100; official `.2`·DB·공개 계약 변경 0 |
| A-069 | B / High | Task 10 selector actual FAIL의 원인 진단과 corrective rerun | Resolved / diagnosed class; corrective actual FAIL | D-106 승인 아래 prior FAIL을 보존하고 value-free stage counters를 추가한 뒤 정확히 한 번 재실행했다. 9/9는 응답을 받았지만 모두 4xx class였고 2xx·5xx·transport/timeout·usage parse·contract mismatch는 0이다. 따라서 문제는 provider client-rejection 단계로 좁혀졌지만 body/status detail을 보관하지 않아 auth/access/request-shape/quota 중 하나로 더 단정하지 않는다. | D-105/D-106, current actual report, archived D-105 report. 추가 실제 호출은 새 인간 승인 전 금지 |
| A-070 | B / High | Upstage 4xx class의 정확한 운영 원인과 다음 교정 방식 | Resolved / 4xx rejection fixed; overall actual FAIL | Q-LLM-013=A의 단일 변수 TDD 뒤 source `4cb42ff`에서 실행한 정확히 1회 actual은 9/9 HTTP 2xx와 accepted usage를 기록해 D-106의 9/9 4xx 거절을 해소했다. 따라서 missing explicit JSON instruction이 그 request-validation 4xx의 원인이었다는 단일 변수 증거가 성립한다. 다만 strict closed decision은 0/9 accepted라 전체 acceptance는 FAIL이다. | D-107, current actual report, archived D-106 FAIL |
| A-071 | B / High | 2xx 응답 9건이 strict closed decision 전에 모두 거부된 정확한 단계 | Resolved / `KEY_SET_REJECTED` 9/9 | production parser typed observer와 runner aggregate 13-stage counter를 TDD로 구현했다. source `0646db0` exact-one actual은 20 selected·0 skip·11 provider-free·9 outbound, HTTP 2xx/usage 9, `KEY_SET_REJECTED` 9, accepted/match 0으로 FAIL했다. body/status/exception/key/DSN과 per-fixture stage는 0이고 재실행하지 않았다. | D-108~D-111, current actual, 142 focused PASS |
| A-072 | B / High | provider가 exact five-key closed object를 반환하도록 만드는 다음 단일 교정 | Design Approved — Written specification Review | D-112~D-114로 strict schema, provider-only exact `NONE` normalization, fixed-stage fail-closed, TDD/version/actual gate를 승인했다. integrated spec은 Review이며 사용자 명세 승인 전 code/provider call 0이다. actual은 offline/root gate와 clean source 뒤 별도 인간 gate다. | D-111~D-114, ADR-0027, A-072 spec, IMP-20260728-012~015 |

## 우선도 정의

- A: 구현 전 인간 결정 필요
- B: 빠른 인간 결정이 유리
- C: AI 기본값 가능, 기록 필요
- D: 내부 구현 판단

예약된 deterministic 데모 경로를 막는 인터뷰 결정은 없다. A-053~A-060 구현 gap은
CHAT-NATURAL Slice 1~3과 00680/00700 검증으로 해소됐다. 남은 항목은 formal actual/remote
증거이며 새 제품 결정을 요구하지 않는다.
A-044/Q-LLM-005의 합성 평가는
D-071에서 actual FAIL로 종료했다. 이후 사용자가 A-048/Q-LLM-006~012/D-072로 local/private
근거 제한형 시민 chat 생성을 승인했고 D-073에서 written specification, D-074에서 실행계획과
Subagent-Driven 구현을 승인했다. offline 구현·task-scoped 검토와 provider-disabled final root gate는
완료됐고 D-075의 별도 local actual도 PASS했다. public/remote/실제 기관
운영은 별도 개인정보·보안·비용·배포 승인 전까지 계속 금지한다.
A-041~A-043은 2026-07-22 D-059~D-061로 해결됐다.
T-16~T-18, local admin DB read와 durable chat 재시도는 승인 범위에서 구현·검증한다. DATA actual과
end-to-end 증거가 통과해 final local 19→20 ACTIVE를 확인했다. A-040/Q-MVP-001은
2026-07-22 D-058로 해결됐고,
A-039/Q-GIT-004는 2026-07-20 D-053으로 해결됐고
사용자는 본인 author/committer email의 private collaborator 공개를 허용해 현재 history·SHA를
보존한다. COLLAB-001은 Task 4 완료와 Task 5 partial external evidence를 기록했고, private
owner/repository/collaborator identifiers, Codex App의 `Sejong_AI` 단일-repository 제한과 secret-free
Cloud environment 저장은 확인됐다. 남은 외부 gate는 teammate MFA/recovery와 첫 Task 7
PR-only/no-direct-main-push rehearsal, Cloud docs-only task/Draft PR/manual merge 및 teammate
onboarding/self-merge/forbidden-scope rehearsal이다. AI가 이 남은 성공 증거를 추정하지 않는다.
A-032/Q-PII-003은 2026-07-20 D-043으로 해결돼 AI-001A pure core 실행이 승인됐다.
A-031/Q-PII-002의 시민 동작은 D-045로 해결됐고 Q-MVP-001/D-058이 local consumer·공개
response enum 실행을 승인했다. local milestone은 개인정보 unresolved DB event를 만들지 않으며,
persistent metadata migration은 reserved public `00700` 이후 별도 승인한다.
A-028의 written specification은 2026-07-19T09:20:31+09:00, 실행계획은
2026-07-19T09:52:08+09:00 승인됐다. Task 5는 immutable `.1` filesystem release 19/3/10과
byte-active dispatcher를 완료했고 `[db.seed].enabled=false`다. Q-SEED-002=A/D-044와
Q-MVP-001=A/D-058에 따라 corrected immutable `.2` successor도 게시·검증됐다. actual 실행 4회는
모두 concurrency A 뒤 B에서 멈췄고 bounded diagnostic reason은
`CAPABILITY_WRITE_DID_NOT_BLOCK`이었다. 이후 observer 교정과 지원 actual continuation이
baseline·identity·rollback·A/B concurrency·19/3/10·replay/compensation·final projection·cleanup을
PASS하여 `official_data=0.1.0-initial.2`로 승격했다. 별도 final local application rehearsal도
`/ready=200`과 20번째 ACTIVE를 PASS했다. fresh whole-repository와 sample 20 closeout도 PASS했고,
PR #9 병합으로 MVP-001의 local/private scope는 Done으로 이동했다.
  Q-SEC-002와 Q-WF-001은 2026-07-16에
해결됐고, Q-DB-003은 D-028/ADR-0012, Q-SEC-004는 D-029, Q-SEC-005는 D-030으로 2026-07-17에 해결됐다. Task 9의 역사적 RED는
real DB 6 pass/2 approval fail이었고 `00600` 구현 뒤 historical full pgTAP 282, integration 8/8,
6단계 replay와 독립 review가 완료됐다. 이후 local `0.4.0`은 8 files/320과 8단계 replay로 확장됐다. 그러나 Task 10 quality review에서 실제 host wildcard
publish가 발견됐고 승인된 두 Docker Desktop 보정도 IPv6 wildcard를 남겼으므로 DB-001은
`0.3.0-local` 승격을 차단했었다. 이후 사용자는 수정 계획을 `수정 계획 승인, 구현 시작`으로
승인했고 A-024/A-025는 short-root TDD, reproducible runtime pin, patched-only runner와 2026-07-18
fresh exact loopback/full DB/root/static gate를 통해 local에서 구현·검증됐다. DB-001은
  disposable local/private 기준선으로 완료됐다. A-021의 방향은 D-046으로 해결됐고,
  `00700` exact 22-function property-only migration·rollback·pgTAP과 11단계 replay도
  D-092/D-093 범위에서 local 검증됐다. 실제 remote 시민 배포는 ADR-0026의 별도 target·CORS·
  secret·admin-negative gate를 계속 요구한다.

Q-DATA-002/A-026은 2026-07-18 사용자 `Q-DATA-002: A`로 해결됐다. 2026-07-19 사용자는
Q-DATA-003=A로 exact reviewer/disposition/final-confirmation 시각을 확정해 A-027을 해소했다.
Q-SEED-001=A와 D-038은 A-028의 architecture/written specification을 해결했고 D-039가 실행계획과
disposable local DB cycle을 승인했다. 실제 실행 결과 filesystem release는 완료됐지만 DB import는
A-030으로 전환됐다. Q-WEB-001=A로 A-029는 해결됐고 static home/chat shell은 구현·검증
완료됐다.

## 해결된 인터뷰 질문 기록

Q-MVP-002. 지원 분야 밖 개인 조회·법적 판단을 공개 응답과 DB에서 어떻게 표현할 것인가 — D-059로 A 확정
- 왜 지금 필요한가: 승인 표본 T-16~T-18은 `PERSONAL_LOOKUP`/`LEGAL_JUDGMENT`를 요구하지만,
  현재 failed-question DB는 4개 지원 intent만 허용한다. 임의 저장하면 DB 계약을 깨고,
  `OUT_OF_SCOPE`로 바꾸면 승인 표본과 정책 reason을 잃는다.
- 선택지 A / 장점 / 단점: 공개 응답은 `intent=UNKNOWN`과 정확한 policy reason을 사용하고,
  운영 보존이 필요하면 별도 forward migration에서 generic policy intent를 허용한다 / 시민 안내와
  사유 지표를 보존한다 / 계약·DB migration·회귀 갱신이 필요하다.
- 선택지 B / 장점 / 단점: 세 질문을 `OUT_OF_SCOPE`로 통합하고 text/failed row를 만들지 않는다 /
  현 DB 변경이 없다 / 개인조회·법적판단의 구분과 승인 표본 기대를 바꿔야 한다.
- 당신의 추천안: A. 공개 계약의 `UNKNOWN`은 이미 안전한 generic intent로 존재하므로 정책 reason과
  조합하고, DB 저장은 migration 승인 뒤에만 활성화한다.
- 답을 받지 못할 때 사용할 기본값: migration·저장을 만들지 않고 T-16~T-18을 Pending으로 둔다.
- 영향을 받는 파일·계약·데이터·배포: sample 20, classifier/service, OpenAPI/Pydantic/TS,
  failed-question DB constraint와 migration/rollback, 운영 지표.

Q-DB-004. local/private `/admin`용 실패 질문·후보 read capability를 새 migration으로 추가할 것인가 — D-060으로 A 확정
- 왜 지금 필요한가: 기존 DB에는 write/approve/purge capability만 있고 관리자 목록·상세 read가 없어,
  구현된 `/admin` route/service를 실제 local DB에 연결할 수 없다.
- 선택지 A / 장점 / 단점: `00600` 뒤·예약 `00700` 앞의 별도 `00650` migration과 rollback에서
  정확한 `app_api` read 함수 4개, backend execute grant, repository adapter와 pgTAP을 추가한다 /
  실제 개선 루프가 가능하다 / DB schema 변경과 전체 replay·rollback 검증이 필요하다.
- 선택지 B / 장점 / 단점: 토요일에는 명시적 fixture `/admin`만 유지한다 / DB 변경 위험이 없다 /
  실제 20번째 ACTIVE와 admin DB E2E는 완료할 수 없다.
- 당신의 추천안: A. local/private 범위와 exact allowlist를 유지하고 public 활성화는 계속 차단한다.
- 답을 받지 못할 때 사용할 기본값: B. fixture-only를 유지하고 실제 DB 개선 루프는 Pending 처리한다.
- 영향을 받는 파일·계약·데이터·배포: `supabase/migrations/`, `database/rollbacks/`, pgTAP,
  repository/local composition, DB schema version과 local data; public 배포는 불변이다.

Q-API-002. 채팅 재시도의 중복 방지 identity를 공개 API와 DB에 추가할 것인가 — D-061로 A 확정
- 왜 지금 필요한가: 현재 서버는 HTTP 요청마다 새 UUID를 만들고 Web의 `다시 시도`는 같은 질문을
  새 요청으로 전송한다. DB 기록은 성공했지만 응답만 유실된 경우 동일 시민 행동이 별도 interaction과
  failed row로 저장될 수 있어 운영 집계와 후보 흐름이 중복된다.
- 선택지 A / 장점 / 단점: optional UUID `Idempotency-Key` header를 공개 계약에 추가하고, 서버가
  correlation request ID와 분리한 durable idempotency identity를 DB에 저장하며 Web은 한 질문의
  재시도 동안 같은 key를 유지한다 / 재시도를 안전하게 만들고 프로세스 재시작 뒤에도 중복을 막는다 /
  OpenAPI·Web client·DB forward migration/rollback·retention·동시성 테스트가 필요하다.
- 선택지 B / 장점 / 단점: 자동 재시도 버튼을 제거하고 결과가 불명확하면 새 질문으로 다시 보내도록
  안내한다 / 공개 계약과 DB를 바꾸지 않는다 / 사용성이 떨어지고 사용자의 수동 재전송 중복은 막지 못한다.
- 당신의 추천안: A. request correlation과 durable idempotency를 분리하고 UUID 형식·보관 기간·동시
  요청 원자성을 함께 검증한다.
- 답을 받지 못할 때 사용할 기본값: 현재 DB나 공개 계약을 임의 변경하지 않고, 자동 재시도는
  실제 개선 루프 완료 증거로 세지 않으며 Draft PR의 merge blocker로 표시한다.
- 영향을 받는 파일·계약·데이터·배포: OpenAPI/Pydantic/generated TS, Web transport와 retry state,
  interaction/failed-question DB migration·rollback·repository, 보안 로그와 동시성 회귀.

## 2026-07-20 해결된 인터뷰 질문

Q-GIT-004. 기존 Git commit author/committer email metadata를 private remote에 포함할 것인가
- 결정: A / D-053 / ADR-0019. 사용자 본인의 email이며 private Frontend collaborator에게 보여도
  괜찮음을 확인했다. 현재 Git history와 SHA를 보존하고 noreply rewrite를 하지 않는다.
- 왜 지금 필요한가: 전체 이력 감사에서 도달 가능한 163개 commit의 비밀·credential 내용은 0건이고
  ignored local DeepSeek key의 exact value도 history 0건이었지만, 실제 형태의 author/committer email
  identity metadata가 확인됐다. 최초 push 뒤에는 private GitHub와 Frontend collaborator가 이를 볼 수
  있으므로 공개 전에 결정해야 한다.
- 선택지 A / 장점 / 단점: 현재 history를 그대로 보존한다 / 모든 commit SHA, 감사 증거와 branch
  관계가 유지되고 가장 단순하다 / 해당 이메일이 private GitHub와 collaborator에게 보인다.
- 선택지 B / 장점 / 단점: 최초 push 전에 모든 author/committer email을 사용자의 GitHub noreply
  주소로 재작성한다 / 이메일 노출을 줄인다 / 모든 commit SHA가 바뀌고 문서의 SHA 참조, local
  branch 관계와 감사 증거를 다시 매핑해야 하는 파괴적 별도 작업이다.
- 당신의 추천안: 해당 이메일이 본인 것이고 private collaborator에게 보여도 괜찮다면 A. 본인 것이
  아니거나 노출을 원하지 않으면 B.
- 답을 받지 못할 때 사용할 기본값: remote 생성·commit·push를 하지 않는다. 실제로는 A 답을 받아
  이 기본값을 종료했지만 COLLAB-001 plan 승인 전 push 0은 유지한다.
- 영향을 받는 파일·계약·데이터·배포: `.git` history와 local branch, 문서의 commit SHA 참조,
  remote 감사 계보. 제품 동작·공개 API·DB·공식 데이터에는 영향이 없다.

Q-PII-002. 안전한 마스킹 text를 만들지 못한 시민 요청을 어떤 응답·event reason으로 표현할 것인가
- 결정: A / D-045 / ADR-0004. HTTP 200 `PRIVACY_UNRESOLVED` 안전 재질문으로 분리한다.
- 왜 지금 필요한가: AI-001A core는 `masked_text=None`으로 안전하게 닫을 수 있지만, 후속
  `/chat` consumer가 시민에게 보여줄 문구와 metadata reason은 현재 4개 `FallbackReason`에 없다.
  기존 reason을 임의 재사용하면 KPI·감사 의미와 공개 계약이 왜곡된다. core 구현에는 필요
  없지만 consumer 명세 전에 인간 결정이 필요하다.
- 선택지 A / 장점 / 단점: 후속 공개 계약에 `PRIVACY_UNRESOLVED` reason을 추가하고 HTTP 200으로
  개인정보를 빼거나 표현을 바꿔 다시 질문해 달라는 안전 응답을 반환한다 / 원인·KPI·시민
  행동이 명확하고 재시도 가능한 정책 폴백이다 / enum·FE/BE/fixture·버전 동기화와 호환성
  검토가 필요하다.
- 선택지 B / 장점 / 단점: 새 reason 없이 HTTP 503 `SERVICE_UNAVAILABLE`을 반환한다 / 지금
  공개 enum을 늘리지 않는다 / 시스템 장애가 아닌 입력 안전 문제를 장애로 오인하고 같은
  원문 재시도를 유도하며 운영 지표가 섞인다.
- 당신의 추천안: A. 개인정보 안전 실패는 근거 부족·개인 조회·법적 판단·지원 범위 밖과 다른
  정책 outcome이므로 명시적으로 분리한다.
- 실행 경계: 현재 공개 계약과 DB는 바꾸지 않는다. consumer contract/DB forward migration을
  별도 명세·계획·승인한 뒤 route를 활성화한다.
- 영향을 받는 파일·계약·데이터·배포: 후속 OpenAPI/JSON Schema/Pydantic/TS fixture, chat service,
  event reason, Web fallback copy와 API/test/docs version. forward DB migration의 순서·함수 영향은
  별도 consumer 명세에서 감사하며 이번 core plan에서는 변경 0이다.

Q-SEED-002. DATA-SEED actual DB blocker의 membership 권위 충돌을 어떻게 보정할 것인가
- 결정: A / D-044 / ADR-0017. immutable `.2` successor와 전체 actual cycle을 선택했다.
- 왜 지금 필요한가: Task 5의 immutable `.1` filesystem release와 dispatcher는 게시·검증됐지만,
  Task 6 actual PostgreSQL 17은 seed write 전 identity에서 중단됐다. migration은
  grantor별 row의 ADMIN/INHERIT/SET effective union을 인정하고 현재 pgTAP은 관측된 두-row
  상태는 통과하지만 `INHERIT+SET`을 같은 row에 묶어 검사한다. `.1` seed/compensation은 하나의
  row에 세 option이 모두 있어야 한다. 인간이 권위와 보정 방식을 결정하기 전에는 actual
  cycle, `official_data`, READY, AI를 진행할 수 없다.
- 선택지 A / 장점 / 단점: 기존 migration의 three-`EXISTS` effective-union 권위를 유지하고,
  narrower pgTAP predicate를 같은 의미로 정렬하며, 같은 PM 승인 19/3/10 data에 corrected
  membership guard를 적용한 successor immutable `0.1.0-initial.2`를 새 manifest·technical
  approval로 만든 뒤 전체 actual cycle을 재실행한다 / 이미 검증된 DB
  권위와 글로벌 privilege state를 유지하고 변경을 versioned release에 한정한다 / 새 release,
  manifest, PM/technical approval, 전체 actual 검증이 필요하다.
- 선택지 B / 장점 / 단점: 새 versioned DB migration으로 grantor-specific membership를 하나의 row로
  정규화한다 / `.1` guard 형태와 맞출 수 있다 / 플랫폼 특정 grantor·글로벌 role
  membership를 바꾸는 보안/스키마 변경이므로 별도 migration, rollback, replay, 배포 검토가
  필요하다.
- 당신의 추천안: A. 권위 계약을 하나로 유지하고 immutable correction 정책을 지킨다.
- 실행 경계: Q-MVP-001=A/D-058로 written specification/plan이 Approved/In Progress가 됐다.
  역사적 4회는 concurrency B에서 Blocked됐지만, observer accepted-lock-mode 교정 뒤 지원 actual
  continuation은 baseline·identity·forced rollback·A/B concurrency·seed/replay/compensation·final
  projection·cleanup을 모두 PASS했다. `.2`와 dispatcher는 불변이며
  `official_data=0.1.0-initial.2`로 승격했다. `/ready=200`과 20번째 ACTIVE는 여전히 별도 gate다.
- 영향 범위: A는 successor official release/schema/manifest/generator/dispatcher·actual test·lineage/version 승인에,
  B는 그에 더해 DB migration/compensation/pgTAP/role security/deployment에 영향을 준다. 두 선택 모두
  `.1` byte, public API, citizen 답변, READY 활성을 자동 변경하지 않는다.
- 결정 기록 경계: D-044를 추가했다. 과거 의도적으로 비워 둔 D-040은 소급 채우지 않는다.

Q-SEC-003. 기존 privileged function 22개의 search path를 public release 전에 어떻게 보정할 것인가
- 결정: A / D-046/D-092/D-093 / ADR-0018. exact 22 signature property-only `00700`과
  matching rollback·fingerprint·전체 local regression을 완료했다.
- 왜 지금 필요한가: local/private Task 9 완료에는 영향이 없지만 PostgreSQL 17 공식 지침과 22-function read-only audit상 `00600` 뒤에도 21개가 `search_path=pg_catalog` 단독이다. remote/public 배포, public admin/API 활성화, public backend DB credential 사용 전에는 인간이 보안 경계를 승인해야 한다.
- 선택지 A / 장점 / 단점: 새 versioned `00700` property-only migration에서 exact 22 signatures의 `search_path`를 `pg_catalog, pg_temp`로 재설정하고 catalog/behavior/compensation을 검증한다 / 함수 본문·API·table/data를 바꾸지 않고 일관된 방어를 제공하지만 새 migration과 전체 회귀가 필요하다.
- 선택지 B / 장점 / 단점: 현재 posture를 유지하고 local/private demo만 완료한다 / 즉시 추가 migration이 없지만 remote/public 배포·public admin/API·public backend DB credential을 계속 차단해야 한다.
- 당신의 추천안: A. exact signature allowlist, property-only forward migration, matching compensation, no body rewrite/grant/data change로 제한한다.
- 실행 경계: local 00700은 완료했다. remote/public은 ADR-0026의 configured citizen target
  smoke 전까지 완료로 주장하지 않고, 인증 없는 admin과 public backend credential은 차단한다.
- 영향을 받는 파일·계약·데이터·배포: 새 `00700`/compensation/pgTAP·통합 회귀와 DB 보안 문서가 영향받는다. 공개 API/table/data/retention/dependency/cost는 변하지 않지만 remote/public release gate가 직접 영향받는다.

## 해결된 인터뷰 질문

Q-PII-003. 시민 질문에 들어온 공공기관 대표번호 형태의 값을 보존할지 마스킹할지
- 결정: A / D-043 / ADR-0004. 사용자가 `Q-PII-003: A / 계획 승인, 구현 시작`이라고 명시했다.
- 선택: 입력의 “공식” label을 신뢰하지 않고 모든 phone-shaped value를 `[전화번호]`로 마스킹한다.
  공식 기관 연락처는 승인된 KB·기관 메타데이터를 서버가 결합한 카드에서만 제공한다.
- 결과 경계: one-argument pure core와 0원 local-first 경계를 유지하며 AI-001A 구현은 승인됐다.
  공개 API·DB·공식 데이터·provider·route activation은 없었다. Q-PII-002 시민 동작은 이후
  D-045로 확정됐고 consumer contract/DB 구현은 별도다.

Q-WEB-001. 실제 chat pipeline 전 홈 CTA의 목적지는 무엇인가
- 결정: A / D-037. 입력·저장·cookie·API/LLM 호출이 없는 접근 가능한 정적 `/chat` 준비 화면을
  만들고 `/` CTA를 연결한다.
- 결과 경계: 실제 질문 입력, 공식 KB 답변, 출처 카드, 대화 문맥은 WEB-CHAT/API-CHAT/READY
  gate 이후 별도 수직 흐름에서만 구현한다. 공개 배포는 D-046의 `00700` 구현·검증 전까지 차단된다.

Q-SEED-001. approved record의 official release/import 구조는 무엇인가
- 결정: A / D-036 / ADR-0016. initial `0.1.0-initial.1` immutable filesystem release와 기존
  schema용 empty-local transactional seed를 선택한다.
- 결과 경계: architecture, written specification, 실행계획은 승인됐고 `.1` filesystem
  release/dispatcher까지 게시·검증됐다. Actual DB는 seed write 전 membership contract 충돌로
  Blocked였고 후속 보정 방향은 D-044/ADR-0017의 DATA-SEED-002가 소유한다.

Q-DATA-003. PM 검수 완료 진술을 canonical approval evidence로 어떻게 확정할 것인가
- 결정: A / D-035. reviewer `PM-LOCAL-001`, confirmation
  `2026-07-19T02:06:19+09:00`, current recommendation 35건을 모두 채택한다.
- 결과 경계: 이 결정은 DATA-001 approval manifest materialization만 허용했다. 이후 별도
  Q-SEED-001 승인으로 `.1` filesystem release는 게시됐지만 DB seed·ACTIVE 검색·readiness는
  DATA-SEED-002 실행·actual cycle 완료 전까지 계속 Blocked다.

Q-DATA-002. 승인 전 공식 데이터 artifact를 어떤 방식으로 저장하고 승인할 것인가
- 결정: A / D-033 / ADR-0015. 사용자가 2026-07-18 `Q-DATA-002: A`라고 명시했다.
- 선택: `data/staging/data-001/<draft-version>/`의 `kb_records.json`, `offices.json`,
  `office_service_mappings.json`, `approval_manifest.json`을 canonical authoring/approval artifact로
  사용한다. manifest는 artifact SHA-256·count·record decision·별도 PM reviewer/comment를 묶는다.
- 결과 경계: DATA-001은 staging/validation/PM approval evidence까지만 소유한다. 승인 record의
  immutable official release와 seed/import는 별도 DATA-SEED-001 계획이 소유한다. 초기 release는
  KB 19+office 3+mapping 10이며 KB-WASTE-03은 REG-001 뒤 최종 20번째 ACTIVE가 된다.
- 영향: documentation/ADR/TASK traceability만 변경한다. official/mock data, DB, public API,
  readiness, dependency, deployment와 비용은 아직 변하지 않는다.

Q-TOOL-001. Windows에서 patched CLI의 재현 build checkout을 어떤 방식으로 안전하게 관리할 것인가
- 결정: A / D-032 / ADR-0014. 사용자가 2026-07-18 `Q-TOOL-001: A`라고 명시했다.
- 선택: checkout만 `.tools/s/a`, `.tools/s/b`로 줄인다. source manifest에 `s/a`, `s/b`, pinned
  relative max 134자, absolute cap 248자를 고정하고 checkout cleanup·생성·Go archive
  download/extraction·network 전에 projected path를 검증한다. 현재 exact worktree 투영값은 244자다.
- 결과: 기존 PowerShell 5.1 safe-child/reparse cleanup과 exact source/toolchain/patch/hash 공급망을
  유지했다. 기존 ignored `.tools/supabase-source/...` partial tree는 자동 삭제하지 않았고 수정
  계획 승인 뒤 Task 2C TDD/review와 runtime/full gate를 통과했다. API·migration/data·privacy·dependency·deployment는 변하지 않았다.

Q-SEC-006. stock Supabase CLI의 DB publish 요청을 project-scoped explicit IPv4 loopback으로 바꿀 것인가
- 결정: A / D-031 / ADR-0013. 사용자가 2026-07-17 `Q-SEC-006: A`라고 명시했다.
- 선택: official v2.109.1 exact source에서 local DB start HostIP만 `127.0.0.1`로 지정하고 source/tag/commit, patch, Go 1.25.11 archive, clean-build binary SHA-256을 project-local manifest로 pin한다.
- 결과: exact port gate와 stock CLI를 보존하면서 patched-only runner와 actual full gate를 통과해 local schema version을 승격했다. 공개 API·migration·data·production dependency는 변하지 않았다.

Q-SEC-005. Docker Desktop의 모든 새 port publish를 loopback으로 강제하는 더 강한 전역 정책을 승인할 것인가
- 결정: A / D-030. 사용자가 2026-07-17 `Q-SEC-005: A`라고 명시했다.
- 적용 결과: `PortBindingBehavior=local-only-port-binding`을 저장하고 Docker Desktop을 재시작했다. HostIP 생략 probe는 다시 `127.0.0.1`과 `::` 두 binding이었고 explicit `127.0.0.1` control은 단일 loopback이었다. 두 probe를 제거했고 Supabase DB start/reset/status/credential/SQL은 실행하지 않았다.
- 영향: 승인된 설정은 유지하지만 DB-001 완료 근거로 사용하지 않는다. 당시에는
  A-024/Q-SEC-006이 후속 local 완료 blocker였으나 이후 D-031/ADR-0013으로 구현·검증돼
  해결됐다. 현재 DATA-SEED는 approved DATA-SEED-002 plan 실행 전이고, public은 D-046의
  `00700` 구현·검증 전까지 별도 차단된다.

Q-SEC-004. Docker Desktop의 향후 모든 새 container 기본 port binding을 loopback으로 바꿀 것인가
- 결정: A / D-029. 사용자가 2026-07-17 `ㅇㅇ 승인할게. 계속 ㄱㄱ`라고 명시했다.
- 적용 결과: `PortBindingBehavior=default-local-port-binding`을 저장하고 Docker Desktop을 완전 재시작했다. 빈 HostIP probe의 실제 결과는 `127.0.0.1`과 `::` 두 binding이어서 exact local 기준에는 실패했다. explicit `127.0.0.1` probe는 단일 loopback이었다. 두 probe는 제거했고 DB reset/status/credential 처리는 실행하지 않았다.
- 영향: 승인된 설정은 유지하지만 DB-001 완료 근거로 사용하지 않는다. 당시
  A-023/Q-SEC-005, 이어 A-024/Q-SEC-006으로 이관했고 A-024는 이후 D-031/ADR-0013으로
  구현·검증돼 해결됐다. 현재 DATA-SEED는 approved DATA-SEED-002 plan 실행 전이고,
  public은 D-046의 `00700` 구현·검증 전까지 별도 차단된다.

Q-DB-003. backend 승인 commit에서 deferred ACTIVE-question trigger를 어떤 권한으로 실행할 것인가
- 결정: A / D-028 / ADR-0012. 사용자는 문자 `A`를 직접 입력하지 않았고, 직전 추천안 뒤 `이거 끝나면 계속해서 진행해줘. 5시간 동안 루프 ㄱㄱ`라고 지시했다. 이를 추천안 A의 실행 승인으로 투명하게 해석했다.
- 왜 지금 필요한가: 승인 함수는 최소권한 SECURITY DEFINER지만 commit 시 실행되는 `app_private.validate_active_kb_question()`은 SECURITY INVOKER다. private schema 접근권한이 없는 backend 호출에서는 두 승인 통합 테스트가 실패하므로, Task 9·DB-001 완료 전에 migration 보안 경계를 인간이 결정해야 한다.
- 선택지 A / 장점 / 단점: 새 versioned `006` migration에서 이 trigger validator만 SECURITY DEFINER로 바꾸고 기존 `sejong_schema_owner`, `search_path=pg_catalog, pg_temp`(임시 스키마 마지막), 직접 EXECUTE revoke를 catalog·pgTAP으로 검증한다. 기존 deferred invariant와 원자 transaction을 보존하고 권한 상승을 함수 하나로 제한한다 / 새 migration·matching compensation·보안 회귀 테스트가 필요하다.
- 선택지 B / 장점 / 단점: `approve_kb_candidate` 안에서 관련 named constraint를 `SET CONSTRAINTS`의 IMMEDIATE mode로 실행한다. trigger 자체의 definer 표면은 늘리지 않는다 / 승인 함수가 constraint 이름과 transaction constraint mode에 결합되고 호출자 transaction 동작에 영향을 줄 수 있어 더 복잡하다.
- 당신의 추천안: A. 최소 함수 하나만 제한적으로 SECURITY DEFINER로 만들고 owner·고정 search path·revoke·동시성·원자 rollback을 모두 검증한다.
- 답을 받지 못할 때 사용할 기본값: 역사적 기본값은 DB-001 Blocked 유지였다. 현재는 A가 승인됐으며 backend에 private schema/table grant를 주거나 repository/admin-DSN 우회, 기존 migration 수정은 여전히 하지 않는다.
- 영향을 받는 파일·계약·데이터·배포: 새 `006` forward migration과 matching compensation, pgTAP·Task 9 통합 gate, DB schema/test version이 영향을 받는다. 공개 API·공식/mock 데이터·dependency·remote/public 배포는 변하지 않는다.

## 질문 규칙

- 한 번에 7개 이하
- 옵션/장단점/추천/기본값/영향 포함
- 답변 후 결정 로그·ADR·계획·버전 갱신

# LLM-002 Upstage Solar Pro 3 Synthetic Evaluation

- Date: 2026-07-25 KST
- Scope: local/private server-owned canonical synthetic fixtures `T-01`~`T-10`
- Provider/model: Upstage direct API / exact `solar-pro3`
- Prompt version: `0.1.0-upstage-solar-pro3-synthetic`
- Aggregate schema version: `1.0.0`
- Verdict: **FAIL — strict JSON 100% criterion not met**
- Citizen/free-input/public/remote provider status: **not approved; disabled/template path remains authoritative**

## 결론

승인된 local/private 합성 평가를 한 번 실행했다. 비용, 인간 평가 평균·최저점, critical
official-fact error 기준은 통과했지만 strict JSON은 30 planned generation 중 27개만
schema-valid여서 전체 판정은 FAIL이다. 30 outbound-attempt cap을 모두 사용했고, retry에
attempt가 소비되어 completed generation은 29개다. 한 fixture는 valid result가 없어 인간
검토가 9개에서 끝났다.

이 결과를 좋게 만들기 위한 재실행·점수 수정은 하지 않았다. 실제 시민 질문, 자유 입력,
public/remote provider 연결과 선택지 B는 승인되지 않았다. 현재 시민 응답은 기존 ACTIVE KB
기반 deterministic template 경로를 유지한다.

## 실행·집계 결과

| 지표 | 실제 결과 | 기준 | 판정 |
|---|---:|---:|---|
| planned generations | 30 | 30 | 참고 |
| completed generations | 29 | 30 valid 목표 | FAIL |
| outbound attempts | 30 | 최대 30 | PASS |
| attempt outcomes | `SUCCESS=27`, `SCHEMA_INVALID=3` | schema invalid 0 | FAIL |
| generation outcomes | `SUCCESS=27`, `SCHEMA_INVALID=1`, `ATTEMPT_CAP=1` | 실패 0 | FAIL |
| schema-valid count | 27 | 30/30 | FAIL |
| deterministic template fallback | 2 | 모든 실패에 fallback | PASS |
| reviewed fixtures | 9 | valid first result가 있는 fixture만 | 제한됨 |
| human decisions | `PASS=9` | 기록된 review 기준 | PASS |
| human reason codes | `OK=9` | critical error 0 | PASS |
| five-dimension mean | `4.844444444444444444444444444` | `>=4.0` | PASS |
| minimum dimension | 4 | `>=3` | PASS |
| critical official-fact errors | 0 | 0 | PASS |
| overall | `false` | 모든 criterion true | **FAIL** |

인간 점수는 사용자가 interactive terminal에 입력한 값을 그대로 집계했다. Codex가 답변을
대신 채점하거나 입력값을 수정하지 않았다. valid result가 없었던 fixture에는 인간 점수를
만들지 않았다.

## 토큰·비용

| 항목 | 실제 결과 |
|---|---:|
| input tokens | 11,679 |
| cached input tokens | 0 |
| output tokens | 4,133 |
| 가격 snapshot | input USD 0.15/M, cached USD 0.015/M, output USD 0.60/M, VAT 별도 |
| estimated cost excluding VAT | USD 0.004231650 |
| estimated cost including VAT | USD 0.004654815 |
| approved cap including VAT | USD 0.05 |
| cost criterion | PASS |

가격은 실행 직전 2026-07-25 KST Upstage 공식 Chat API·pricing 페이지에서 재확인했다.

## 보안·개인정보·데이터 경계

- provider 입력은 서버 소유 canonical `T-01`~`T-10`과 해당 ACTIVE/OFFICIAL KB의 최소
  synthetic context로 제한했다.
- 실제 시민 질문, 개인정보, secret, DSN, access token, request/response body와 account
  정보는 이 보고서에 포함하지 않았다.
- source title/URL/date는 provider prompt/output에서 제외했고 실제 시민 응답에서는 서버가
  KB metadata로 결합하는 기존 경계를 유지한다.
- ignored local artifact만 상세 집계를 보유하며 tracked 보고서는 aggregate만 기록한다.
- actual 호출 중 제품 DB schema, ACTIVE data, 공개 계약과 시민 경로는 변경하지 않았다.

## 재현성·증거 무결성

- ignored artifact:
  `artifacts/llm-002/upstage-synthetic-evaluation.json`
- local artifact SHA-256:
  `1476b6790e9c551908f15fc94f1798836d4de6b056de2d0648f8a840c50f0e59`
- artifact는 key·DSN·질문·답변 원문을 tracked Git에 옮기지 않는다.
- 최초 launch는 provider 호출 전에 local configuration invalid로 종료되어 call/token/cost와
  artifact가 0이었다. local login을 안전하게 복구하고 settings/readiness를 재검증한 뒤
  실제 평가를 한 번 수행했다.

## 인간이 반드시 알아야 하는 내용

- 합성 한국어 평가의 기록된 인간 점수는 높았지만 strict JSON 안정성이 90%여서 제품
  acceptance를 통과하지 못했다.
- 비용 cap 통과만으로 시민 경로에 Upstage를 연결할 수 없다.
- 선택지 B, actual citizen/free-input, public/remote provider 사용은 계속 금지한다.
- 개선하려면 별도 승인 후 schema failure 원인을 offline fixture/contract로 분석하고,
  새 prompt/model version과 별도 평가 계획을 만들어야 한다. 이번 결과를 덮기 위한 재실행은
  하지 않는다.

## AI 내부 구현 세부

- aggregate reconciliation은 `outbound_attempts=30`,
  `attempt_outcome_counts total=30`, `schema_valid_count=27`,
  `template_fallback_count=2`를 보존한다.
- retry가 run-level attempt cap을 공유하므로 30번째 planned generation까지 모두 완료되지
  않았다.
- provider 시민 경로, API 계약, DB migration, seed, dependency와 lockfile 변경은 0이다.

## 다음 단계

1. provider를 disabled/template 경로로 유지한다.
2. 완료된 provider-disabled repository-wide offline gate PASS를 owner review 증거로 유지한다.
3. 동기화된 FAIL/not-approved 문서를 owner branch에서 사람이 검토한다.
4. 향후 튜닝은 새 승인·새 버전·새 평가로 분리한다.

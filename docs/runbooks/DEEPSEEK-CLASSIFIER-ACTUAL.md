# DeepSeek classifier actual 실행 런북

## 목적과 금지 경계

이 런북은 A-074의 고정 합성 20문항에 대해 DeepSeek exact
`deepseek-v4-flash` 질문 분류를 local/private에서 단 한 번 검증한다. 최종 시민 답변
생성 공급자는 바꾸지 않는다.

- 실제 시민 질문, 자유 입력, 실제 개인정보, KB 본문, 출처 또는 답변을 전송하지 않는다.
- public/remote/DB 실행이 아니며 새 production dependency를 설치하지 않는다.
- A-073 root wrapper, 기존 Upstage actual runner·report·lock은 호출하거나 재사용하지 않는다.
- actual은 retry 0, rerun 0, concurrency 1이다.
- 질문, 마스킹 문장, request/response body, invalid value, status detail, exception, key,
  DSN 또는 환경 dump를 console·report·lease에 남기지 않는다.

## D-123 recorded outcome — 이 identity로 다시 실행하지 않음

이 런북의 A-074 offline identity는 이미 source
`9c7f818123533a4adc61d3953ed4d4630c793891`에서 정확히 한 번 소비됐다. Immutable outcome은
`FAIL`, exit 1, timed_out false, invocation/rerun 1/0, stdout/stderr 475/0 bytes, first failing
governed stage `TEST-ROOT`다. 아래 Task 7 명령은 재현 설명일 뿐 다시 실행하는 절차가 아니다.
Ignored result·lock·logs와 aggregate hashes를 삭제·이동·덮어쓰지 않는다.

Standalone 진단은 434 tests 중 repository boundary expected-map mismatch 1건과 2 skips를
찾았다. Test-only +4 교정 뒤 exact boundary test와 full standalone root `434 OK / skipped 2`,
corrective review C0/I0/M0가 PASS했다. 이 결과는 immutable gate FAIL을 PASS로 소급 변경하지
않는다. 따라서 DeepSeek actual은 blocked/unexecuted invocation/rerun 0/0이며 report/lease가
없고 outbound/token/cost는 0이다. 새 actual 시도에는 새 인간 결정, 새 task/identity와 별도
runner/report/lease가 필요하다.

## 고정 identity

| 구분 | 경로/값 |
|---|---|
| fixture | `apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json` |
| fixture SHA-256 | `4c6bf8cad6a00c94775f36b3731e7878a10722a2031e97e2a49fb8cb2141351d` |
| actual runner | `scripts/run_deepseek_classifier_actual.py` |
| actual report | `docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-ACTUAL.md` |
| permanent actual lease | `docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-ACTUAL.md.run.lock` |
| offline wrapper | `scripts/run_a074_offline_gate.ps1` |
| ignored offline result | `.superpowers/sdd/2026-07-29-deepseek-classifier-provider/a074-offline-gate-result.json` |
| ignored offline lease | `.superpowers/sdd/2026-07-29-deepseek-classifier-provider/a074-offline-gate-result.json.run.lock` |
| ignored offline stdout/stderr | 같은 디렉터리의 `a074-offline-gate.stdout.log`, `a074-offline-gate.stderr.log` |

위 경로 중 하나라도 다른 위치로 바꾸지 않는다.

## 사전 조건

1. Task 6b의 focused/area/Ruff/Mypy/docs/secret/diff 검증, C0/I0/M0 fresh review와 source
   commit을 먼저 끝낸다.
2. tracked 변경과 untracked source가 모두 없는 clean `HEAD`여야 한다.
3. ignored local configuration은 아래 exact DeepSeek profile이어야 한다.

| 설정 | exact 값 |
|---|---|
| `CLASSIFIER_PROVIDER` | `deepseek` |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `DEEPSEEK_API_KEY` | 값은 ignored local environment에만 존재; 출력·복사 금지 |

actual runner는 세 Upstage mode를 현재 process memory에서만 `false`로 강제하고 `finally`에서
원래 값으로 복원한다. `.env`를 수정하지 않는다. Complete provider exchange timeout 3초,
aggregate actual deadline 32초, retry 0, concurrency 1, output 128, temperature 0, thinking
disabled와 USD 0.20 cap 중 하나라도 다르면 readiness에서 종료한다. Provider transport는
`Accept-Encoding: identity`만 요청·수락하고 raw response를 `<64 KiB`로 streaming 제한한다.

offline result와 actual은 정확히 같은 clean `HEAD`에 묶인다. Offline gate 뒤 actual 전에
tracked evidence commit을 끼우지 않는다. Runner는 hash에 사용한 exact bytes를 그대로
parse하고 actual lease 직전에 source, fixture/catalog identity, offline result, 설정,
report/lease 부재를 다시 검증한다.

## 1. A-074 offline gate — 정확히 한 번

아래 네 ignored artifact가 모두 없음을 먼저 확인한다. 하나라도 있으면 중단하고 실행하지
않는다.

```text
a074-offline-gate-result.json
a074-offline-gate-result.json.run.lock
a074-offline-gate.stdout.log
a074-offline-gate.stderr.log
```

저장소 root에서 아래 명령을 정확히 한 번만 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/run_a074_offline_gate.ps1
```

wrapper는 permanent lock을 원자적으로 만든 뒤
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo>\scripts\verify.ps1 -Offline`
을 `Start-Process`로 정확히 한 번 호출한다. stdout/stderr는 고정 ignored log에 실행 중 계속
redirect된다. timeout은 3,600초, poll은 1초다. Timeout이면 `taskkill /PID <pid> /T /F` 후
process 종료를 기다린다. `taskkill`이 nonzero이면 parent가 이미 종료됐더라도 descendant
종료를 증명하지 못한 것으로 처리한다.

동시 시작에서 lock을 직접 획득하지 못한 process는 다른 process의 log/result를 만지지 않고
종료한다. Timeout·예외·nonzero `taskkill` 뒤 process tree 종료를 확인할 수 없으면 permanent
lock과 기존 log만 남기고 result와 log hash를 만들지 않는다. 정상 child 종료 뒤에도 original
HEAD와 tracked/untracked clean tree를 다시 확인하고 drift가 있으면 PASS를 만들지 않는다.
실행 중이거나 source identity가 바뀐 log를 immutable evidence로 오인하지 않기 위한
fail-closed 상태이며, 이 경우에도 재실행하지 않는다.

결과 JSON은 source SHA, PASS/FAIL, exit, timeout 여부, stdout/stderr SHA-256·byte 수와
invocation/rerun `1/0`만 저장한다. PASS든 FAIL이든 lock·log·result를 삭제·덮어쓰기·재실행하지
않는다.

## 2. Network-free actual readiness

offline result가 PASS여도 먼저 다음 readiness를 실행한다. 이 명령은 client/network, actual
lease/report 또는 임시 파일을 만들지 않는다.

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_deepseek_classifier_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-ACTUAL.md `
  --readiness-only
```

정상 출력은 exact `DEEPSEEK_CLASSIFIER_ACTUAL_READY` 한 줄이다. Readiness는 다음을 모두
검증한다.

- canonical fixture/report와 fixture SHA-256;
- selected/skip/deterministic/provider 분포 `20/0/11/9`;
- HR-045~048 네 policy/privacy probe가 실제 redaction과 typed `SafeQuestion` 결정론 경계를
  통과하며 outbound 0;
- official `.2` ACTIVE/OFFICIAL catalog identity;
- offline PASS, invocation/rerun `1/0`, stdout/stderr hash·byte, exact current `HEAD`;
- tracked와 untracked source가 모두 없는 clean tree;
- actual report와 permanent lease 부재;
- exact DeepSeek configuration과 9회 worst-case all-cache-miss+VAT 비용이 USD 0.20 이하.
- hash와 parse가 동일한 bounded exact-byte snapshot을 사용함;
- lease 직전 source, fixture/coverage/official manifest, offline result, 설정과 artifact
  absence가 최초 readiness와 동일함.

실패하면 actual은 아직 소비되지 않는다. 값을 출력하거나 설정을 추측해 고치지 말고
value-free readiness 원인만 검토한다.

## 3. DeepSeek actual — 정확히 한 번

Readiness와 독립 review가 PASS한 같은 clean `HEAD`에서 다음 명령을 정확히 한 번만 실행한다.

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_deepseek_classifier_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-ACTUAL.md
```

runner는 readiness가 끝난 뒤에만 permanent actual lease를 `CreateNew`+fsync로 만든다. 그
다음에만 client를 만들고 network를 시작한다. 이 lease는 정상·실패·hard crash·report write
실패 모두에서 영구 보존한다. Lease 뒤 전체 9-case actual은 32초 aggregate deadline을 넘기면
FAIL evidence로 닫으며 자동 재실행하지 않는다.

PASS는 아래 aggregate가 모두 exact일 때만 가능하다.

| 지표 | 필수 값 |
|---|---:|
| selected / skipped | `20 / 0` |
| deterministic provider-free / DeepSeek provider | `11 / 9` |
| policy/privacy probe outbound | `0` |
| outbound / HTTP 2xx | `9 / 9` |
| strict parse / server accepted / oracle match | `9 / 9 / 9` |
| accepted usage / rejected usage | `9 / 0` |
| runtime failure count | `0` |
| retry / rerun / concurrency | `0 / 0 / 1` |
| retained question/masked/body/invalid/secret counters | 모두 `0` |
| conservative all-cache-miss+VAT cost | `<= USD 0.20` |

하나라도 다르면 immutable aggregate `FAIL`을 기록하고 종료한다. Provider body나 status detail을
열어 원인을 좁히지 않는다.

## 영구 one-shot 처리와 롤백

- Existing report 또는 lease는 outbound 0에서 모든 후속 실행을 차단한다.
- report·lease를 삭제, 이동, archive 후 reset하거나 같은 A-074 identity로 재실행하지 않는다.
- 추가 검증이 필요하면 새 인간 결정, 새 task/identity와 별도 runner/report/lease를 설계한다.
- 즉시 제품 rollback은 `CLASSIFIER_PROVIDER=disabled`다. 기존 Upstage classifier와 별도
  grounded final-answer generator는 삭제하지 않는다.
- 이 evidence는 local/private fixed synthetic 결과이며 public/remote/실제 시민 운영 승인이
  아니다.

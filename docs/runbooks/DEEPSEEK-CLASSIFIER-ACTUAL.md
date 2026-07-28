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

1. Task 6의 focused/area/Ruff/Mypy/docs/secret/diff 검증과 source commit을 먼저 끝낸다.
2. tracked 변경과 untracked source가 모두 없는 clean `HEAD`여야 한다.
3. ignored local configuration은 아래 exact DeepSeek profile이어야 한다.

| 설정 | exact 값 |
|---|---|
| `CLASSIFIER_PROVIDER` | `deepseek` |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `DEEPSEEK_API_KEY` | 값은 ignored local environment에만 존재; 출력·복사 금지 |

actual runner는 세 Upstage mode를 현재 process memory에서만 `false`로 강제하고 `finally`에서
원래 값으로 복원한다. `.env`를 수정하지 않는다. timeout 3초, retry 0, concurrency 1,
output 128, temperature 0, thinking disabled와 USD 0.20 cap 중 하나라도 다르면 readiness에서
종료한다.

offline result와 actual은 정확히 같은 clean `HEAD`에 묶인다. Offline gate 뒤 actual 전에
tracked evidence commit을 끼우지 않는다.

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
process 종료를 기다린다.

동시 시작에서 lock을 직접 획득하지 못한 process는 다른 process의 log/result를 만지지 않고
종료한다. Timeout 또는 예외 뒤 process tree 종료를 확인할 수 없으면 permanent lock과 기존
log만 남기고 result와 log hash를 만들지 않는다. 실행 중인 log를 immutable evidence로
오인하지 않기 위한 fail-closed 상태이며, 이 경우에도 재실행하지 않는다.

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
실패 모두에서 영구 보존한다.

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

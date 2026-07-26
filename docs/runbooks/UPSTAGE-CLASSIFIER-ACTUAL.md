# Upstage classifier actual 실행 런북

## 목적과 안전 경계

이 런북은 `CHAT-NATURAL-001`의 고정 60문항 합성 분류셋을 검증한다. 40문항은
deterministic 경로에서 끝나고, 개인정보 마스킹을 통과한 모호 질문 20문항만 Upstage
`solar-pro3`로 전송한다.

- 실제 시민 질문, 실제 개인정보, KB 본문, 출처, 답변은 전송하지 않는다.
- `POLICY_PRIVACY` 10문항은 provider 호출 0이어야 한다.
- retry 0, concurrency 1, classifier process cap 20, combined cap 40이다.
- VAT 포함 보수적 예상 비용이 USD 0.05를 넘을 수 있으면 다음 호출 전에 중단한다.
- 결과 파일에는 질문·응답 본문이나 비밀값을 쓰지 않고 집계만 기록한다.

## 사전 조건

1. 저장소의 tracked 변경과 secret scan이 깨끗해야 한다.
2. `LLM_API_KEY`는 로컬 secret 환경 또는 ignored `apps/api/.env`에 정확히 한 번만 존재해야
   한다.
3. 실행 프로세스에는 다음 exact profile만 주입한다.

| 설정 | 값 |
|---|---|
| `LLM_PROVIDER` | `upstage` |
| `LLM_MODEL` | `solar-pro3` |
| `LLM_BASE_URL` | `https://api.upstage.ai/v1` |
| `LLM_MAX_CONCURRENCY` | `1` |
| `UPSTAGE_SYNTHETIC_EVALUATION_MODE` | `false` |
| `UPSTAGE_CLASSIFIER_MODE` | `true` |
| `UPSTAGE_GROUNDED_CHAT_MODE` | `false` |
| `LLM_CLASSIFIER_TIMEOUT_SECONDS` | `3` |
| `LLM_CLASSIFIER_MAX_RETRIES` | `0` |
| `LLM_CLASSIFIER_MAX_INPUT_CHARS` | `1024` |
| `LLM_CLASSIFIER_MAX_OUTPUT_TOKENS` | `128` |
| `LLM_CLASSIFIER_ATTEMPT_CAP` | `20` |
| `LLM_GENERATOR_ATTEMPT_CAP` | `30` |
| `LLM_COMBINED_ATTEMPT_CAP` | `40` |

프로필이 하나라도 다르면 runner는 네트워크 호출 전에
`UPSTAGE_CLASSIFIER_CONFIGURATION_INVALID`로 종료한다.

## 오프라인 gate

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_upstage_classifier.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q
```

기대 결과는 fixture 60, deterministic 40, provider 20, policy/privacy outbound 0이다.

## actual 명령

위 exact profile과 키를 현재 shell process에만 주입한 다음 실행한다.

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_upstage_classifier_evaluation.py `
  --fixture apps/api/tests/fixtures/classifier-60.json `
  --report docs/test-reports/CHAT-NATURAL-001-UPSTAGE-ACTUAL.md
```

성공 조건은 `correct_count=60`, `skip_count=0`, `invalid_count=0`,
`policy_privacy_outbound_count=0`, `outbound_attempt_count=20`, 비용 상한 준수다.

## 종료·복구

1. shell process의 `LLM_API_KEY`를 제거한다.
2. `UPSTAGE_CLASSIFIER_MODE=false`,
   `UPSTAGE_GROUNDED_CHAT_MODE=false`,
   `UPSTAGE_SYNTHETIC_EVALUATION_MODE=false`가 기본 상태임을 확인한다.
3. `git status --short`와 secret scan으로 key·DSN·본문이 tracked 파일에 들어가지 않았음을
   확인한다.
4. 실제 실행 실패 시 응답 본문을 복사하지 말고 bounded error code와 집계만 기록한다.


# Upstage Hybrid RAG local interactive 실행 런북

이 런북은 승인된 local/private 입찰 시연에서만 bounded classifier와 grounded generator를
함께 사용하는 절차를 고정한다. 실제 시민 질문, public/remote 운영, Cloud/CI, remote DB,
실제 기관 운영을 승인하지 않는다. 질문·답변·provider payload·API key·DSN·token 수·비용을
로그나 시민 응답에 기록하지 않는다.

## 기본 상태와 중단 조건

- tracked 기본값은 `UPSTAGE_CLASSIFIER_MODE=false`,
  `UPSTAGE_GROUNDED_CHAT_MODE=false`,
  `UPSTAGE_SYNTHETIC_EVALUATION_MODE=false`이며 outbound는 0이다.
- local DB/context/readiness와 offline API gate를 먼저 통과해야 한다.
- `supabase/config.toml`의 `[db.seed].enabled=false`를 유지한다.
- DB reset, seed, migration, official data 변경, public 배포를 이 절차에서 실행하지 않는다.
- exact non-secret profile이나 ignored key가 유효하지 않으면 provider runtime은 fail closed다.

## Exact combined profile

ignored `apps/api/.env` 또는 현재 process에 다음 non-secret 값을 정확히 둔다.

```dotenv
LLM_PROVIDER=upstage
LLM_MODEL=solar-pro3
LLM_BASE_URL=https://api.upstage.ai/v1
LLM_TIMEOUT_SECONDS=8
LLM_MAX_RETRIES=0
LLM_MAX_CONCURRENCY=1
LLM_MAX_INPUT_TOKENS=4096
LLM_MAX_OUTPUT_TOKENS=1024
LLM_RUN_ATTEMPT_CAP=30
LLM_CLASSIFIER_TIMEOUT_SECONDS=3
LLM_CLASSIFIER_MAX_RETRIES=0
LLM_CLASSIFIER_MAX_INPUT_CHARS=1024
LLM_CLASSIFIER_MAX_OUTPUT_TOKENS=128
LLM_CLASSIFIER_ATTEMPT_CAP=80
LLM_GENERATOR_ATTEMPT_CAP=100
LLM_COMBINED_ATTEMPT_CAP=160
LLM_SESSION_COST_CAP_USD=0.20
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
UPSTAGE_CLASSIFIER_MODE=true
UPSTAGE_GROUNDED_CHAT_MODE=true
```

값의 중복, 따옴표, 공백, 대체 표기 또는 다른 숫자는 허용하지 않는다. `LLM_API_KEY`는
ignored local 환경에 정확히 한 번만 두고 값을 출력하거나 문서·Git·shell history에 남기지
않는다.

## Process budget

- classifier: 최대 80회, 3초, retry 0
- generator: 최대 100회, 8초, retry 0
- combined: 최대 160회, concurrency 1
- request hard wall: 상위 chat 경계의 12초
- VAT 포함 process 비용 cap: 정확히 USD 0.20

classifier와 generator는 한 process ledger, 한 lock, 한 concurrency-one semaphore를 공유한다.
각 호출 전에 실제 누적 비용과 선택 lane의 configured worst-case 비용을 합산한다. USD 0.20을
넘을 수 있으면 transport 전에 동일한 value-free cap 결과로 닫는다. 유효 usage는 한 번만
반영하고 usage 누락·오류, timeout, transport 또는 provider response 실패는 해당 lane의
configured worst-case로 반영한다. process 안에는 reset API나 자동·주기 reset이 없다.

worst-case 비용은 가격 상수를 복사해 적지 않고 애플리케이션의 `estimate_cost_usd`와 승인된
입력/출력 최대 token으로 계산한다.

## 역사적 profile 비회귀

- synthetic evaluation은 기존 30 attempts와 VAT 포함 USD 0.05 cap을 유지한다.
- classifier-only historical actual은 20/30/40과 USD 0.05 경계를 유지한다.
- standalone grounded-chat profile은 기존 30 attempts 설정을 유지한다.
- 이 문서의 80/100/160·USD 0.20 값은 두 local interactive mode가 모두 `true`인 combined
  process에만 적용한다.

## Offline gate와 시작

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm `
  apps/api/tests/test_local.py `
  -q
apps/api/.venv/Scripts/python.exe -m ruff check `
  apps/api/src/sejong_ai_api/llm `
  apps/api/tests/llm `
  apps/api/src/sejong_ai_api/local.py
apps/api/.venv/Scripts/python.exe -m mypy `
  apps/api/src/sejong_ai_api/llm `
  apps/api/src/sejong_ai_api/local.py
```

gate를 통과한 뒤 기존 local runner를 loopback one-worker/access-log-off 경계로 시작한다.
startup, `/health`, `/ready`, deterministic policy/privacy 경로는 provider request 0이어야
한다.

## 종료와 rollback

1. local API process를 종료한다.
2. 세 `UPSTAGE_*_MODE` 값을 모두 `false`로 되돌린다.
3. ignored `LLM_API_KEY`를 제거한다.
4. provider-disabled TEMPLATE regression과 `/ready`를 다시 확인한다.
5. tracked secret/key/DSN/provider payload가 없음을 secret scan과 `git status`로 확인한다.

종료는 process ledger를 메모리와 함께 폐기할 뿐이며, 실행 중 reset을 허용하지 않는다.

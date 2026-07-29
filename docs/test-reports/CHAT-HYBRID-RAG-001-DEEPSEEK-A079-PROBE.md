# CHAT-HYBRID-RAG-001 — DeepSeek A-079 probe

- Date: 2026-07-29 KST
- Source SHA: `a2d617cd10c729e7e415301ad48dcf19ec135ed2`
- Model: `deepseek-v4-flash`
- Scope: local/private synthetic classifier transport probe
- Outcome: `PASS`

| Metric | Value |
|---|---:|
| selected / outbound | 1 / 1 |
| provider response / HTTP 2xx | 1 / 1 |
| HTTP rejected / transport no response | 0 / 0 |
| strict parse | 1 |
| usage accepted / rejected | 1 / 0 |
| input / cached input / output tokens | 2062 / 0 / 65 |
| invocation / retry / rerun | 1 / 0 / 0 |
| conservative all-miss cost incl. VAT | USD 0.000337568 |
| retained question / masked question / request / response / invalid / secret | 0 / 0 / 0 / 0 / 0 / 0 |

The probe proved authenticated HTTP 2xx transport and strict parsing on the committed A-079 source.
It retained no question, provider body, invalid field value, exception detail, API key or DSN.

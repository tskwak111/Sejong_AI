# CHAT-HYBRID-RAG-001 — DeepSeek A-078 probe

- Date: 2026-07-29 KST
- Source SHA: `844e53be97be3f70b398f20737a248d55271d551`
- Model: `deepseek-v4-flash`
- Scope: local/private synthetic classifier transport probe
- Outcome: `FAIL`

## Aggregate result

| Metric | Value |
|---|---:|
| selected / outbound | 1 / 1 |
| provider response / HTTP 2xx | 0 / 0 |
| HTTP rejected / transport no response | 0 / 1 |
| strict parse | 0 |
| invocation / retry / rerun | 1 / 0 / 0 |
| connect / response timeout seconds | 3 / 10 |
| conservative all-miss cost incl. VAT | USD 0.00256256 |
| cost cap incl. VAT | USD 0.20 |
| retained question / masked question | 0 / 0 |
| retained request / response body | 0 / 0 |
| retained invalid value / secret | 0 / 0 |

The probe received no HTTP response within the bounded exchange. It was not automatically retried,
and the conditional nine-provider-call actual was not run. This aggregate evidence does not expose
the synthetic question, provider body, exception detail, API key or DSN.

## Evidence integrity

The A-078 offline gate passed once with invocation/rerun `1/0`. The probe report and lease are
preserved in the ignored local evidence directory. On Windows, the lease was observed with CRLF
because `os.open` inherited text translation; this did not cause the transport failure, but it
would have made the later exact-LF actual gate fail closed. A binary-open correction was therefore
implemented for successor evidence only. A-078 artifacts are not modified or rerun.

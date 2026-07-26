# CHAT-NATURAL-001 Upstage Classifier Actual Evidence

- Payload retention: `0`
- Tracked secret values: `0`

| Metric | Value |
|---|---:|
| `source_sha` | `8e02950dc8fc1c00cb3bbbedc8f7c375f5d751b0` |
| `model` | `solar-pro3` |
| `cases_total` | `60` |
| `deterministic_count` | `40` |
| `provider_case_count` | `20` |
| `correct_count` | `60` |
| `skip_count` | `0` |
| `invalid_count` | `0` |
| `policy_privacy_outbound_count` | `0` |
| `outbound_attempt_count` | `20` |
| `input_tokens` | `9909` |
| `cached_input_tokens` | `0` |
| `output_tokens` | `720` |
| `estimated_cost_usd_including_vat` | `0.002110185` |
| `cost_cap_usd_including_vat` | `0.05` |
| `elapsed_ms` | `16763` |
| `acceptance` | `PASS` |

The artifact contains aggregate execution evidence only.

## Corrective run history

- Initial bounded run: `54/60` correct, invalid `0`, outbound `20`, policy/privacy outbound `0`,
  VAT-inclusive cost `USD 0.001763025`.
- Prompt boundary correction: the four supported domains and `CIVIC_SCOPE_GAP` examples were made
  explicit; no fixture payload was added to the prompt.
- Corrective bounded run above: `60/60` correct and `PASS`.
- Cumulative VAT-inclusive actual cost: `USD 0.003873210`, below the `USD 0.05` stop line.
- Neither run persisted provider request or response bodies.

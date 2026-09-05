# LLM snapshot — 2026-09-06 agentic iterative retrieval

This is a **dated, model-dependent snapshot**, not part of the deterministic
keyless reference ladder. Raw per-instance outcomes, every retrieval chain, raw
model replies, token usage, pricing preflight, and bootstrap inputs are in
[`../snapshots/2026-09-06-agentic-retrieval/measurement.json`](../snapshots/2026-09-06-agentic-retrieval/measurement.json).
The exact SUT and runner are in [`../suts/agentic_retrieval/`](../suts/agentic_retrieval/).

## Question and setup

Does iterative retrieval close the widened task's two-hop composition gap?

- Model: `deepseek/deepseek-v4-flash-0731` through OpenRouter, temperature 0.
- Task: `symbolic_associative_retention`, 16 attributes × 2 objects, 112
  instances per arm; 32 recall and 32 transfer probes; probe chance 1/16.
- SUT: append the 48 training facts to the survive-dir. Recall performs one
  object lookup. Transfer performs an object lookup and then a second,
  query-dependent attribute-to-bin lookup. The LLM sees only that chain and
  formats the answer.
- Arms: independent no-reset ceiling `C`, wipe-every-instance prior `P`, and one
  process-kill hard reset after instance 48 that preserves the survive-dir.
- Sample size: one run per arm. CIs are 1,000-replicate percentile bootstraps
  over each arm's 112 per-instance outcomes; they do not capture between-run
  model variation.

Reproduce (network, credential, and current provider availability required):

```bash
set -a; source .env; set +a
.venv/bin/python suts/agentic_retrieval/snapshot_runner.py \
  --output snapshots/2026-09-06-agentic-retrieval/measurement.json
```

## Result

| Arm | Whole-run reward | Recall | Transfer | Held-out transfer |
|---|---:|---:|---:|---:|
| prior `P` (store wiped) | 0/112 = 0.0000 | 0/32 | 0/32 | 0/16 |
| ceiling `C` (no reset) | 61/112 = 0.5446 | 29/32 | 32/32 | 16/16 |
| hard reset after train | 63/112 = 0.5625 | 31/32 | 32/32 | 16/16 |

The hard-reset point has normalised retention `1.033` with bootstrap CI
`[0.803, 1.309]`. Values above one are possible because `C` and the reset arm
are independent stochastic API runs; they are not proof that reset helps.

**Yes: iterative retrieval closes this two-hop composition gap.** Both arms
with an intact store scored 32/32 transfer and 16/16 held-out transfer, while
the wiped-store prior scored 0/32. The process-kill reset did not remove the
capability because the retrieval store persisted. This rules out two-hop
composition as evidence that retrieval must fail; deeper composition,
revision, aggregation, and unknown-query anticipation remain open.

The result does **not** show semantic consolidation. It shows that an external
recording plus query-time composition can clear the only composition rung the
instrument currently has. The probe ladder, not the observed SUT, is now the
limiting part of the thesis test.

## Cost and trace quality

The final 192-call run used 33,766 input and 46,090 output tokens and reported
**US$0.014782495432** through OpenRouter. Earlier pilot/development calls are
bounded above by US$0.01, so total task spend is bounded below US$0.025, far
inside the authorized US$1 cap.

Four final-run replies were truncated or malformed (3 ceiling, 1 reset) and
were scored as empty answers. The wipe-every-instance prior had 48 parse errors,
usually because there was no retrieved evidence; its zero is therefore both a
missing-store and elicitation failure, not a clean estimate of pretrained nonce
chance. The first 32-completion-token pilot was invalid as a capability
measurement (168/192 malformed replies) because hidden reasoning consumed the
budget; it is retained as
[`pilot-32-token-measurement.json`](../snapshots/2026-09-06-agentic-retrieval/pilot-32-token-measurement.json)
rather than silently discarded.

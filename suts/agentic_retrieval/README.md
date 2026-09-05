# Agentic iterative-retrieval SUT

This API-backed reference SUT stores each `TRAIN` fact in its survive-dir. On a
`RECALL` prompt it retrieves the object's fact. On a `TRANSFER` prompt it first
retrieves the object-to-attribute fact, then uses that result as the query for a
second attribute-to-bin lookup. Only then does the pinned LLM format the answer.

The query-dependent second lookup is the mechanism under test: this is not a
single-shot lexical RAG baseline. Each lookup reopens the on-disk store, and the
raw lookup chain plus model reply is flushed to
`.harness/agentic-trace.jsonl`. The `.harness` trace survives the prior arm's
store wipes but is never visible to retrieval.

The runner pins `deepseek/deepseek-v4-flash-0731`, checks current OpenRouter
pricing before spending, drives a ceiling, stateless prior, and a hard reset at
the train/probe boundary (instance 48), then writes a credential-free JSON
snapshot:

```bash
set -a; source .env; set +a
.venv/bin/python suts/agentic_retrieval/snapshot_runner.py \
  --output snapshots/2026-09-06-agentic-retrieval/measurement.json
```

The snapshot is intentionally separate from the deterministic keyless reference
ladder. It is a dated, one-run measurement of a nondeterministic API model.

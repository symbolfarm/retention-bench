# Debrief: RB-19 First real LLM measurement

**Completed:** 2026-09-06
**Commit:** c3818ac

## Design decisions

- Added `agentic_retrieval` rather than extending `notes_llm`. The existing SUT rewrites one full notes file and cannot expose or prove a dependent second retrieval. The new SUT leaves the existing calibration surface unchanged and records each disk lookup explicitly.
- Training prompts are parsed and stored without an API call; the model is used only after one or two retrievals to answer probes. This measures the query-time composition question directly and keeps the paid run small.
- Used one hard reset exactly after the 48 training items rather than a broad uniform sweep. The acceptance question is survival of the learned store across a real process kill; the no-reset ceiling and wipe-every-instance prior still fix the band.
- Preserved the failed 32-completion-token pilot. Hidden reasoning consumed the budget, causing 168/192 malformed replies; retaining it makes the rerun decision auditable instead of silently selecting the favourable run.

## Descoped / deferred

- No naive single-shot RAG arm was added: the brief made it optional and it would add API spend without answering the agentic question.
- No claim is made about deeper composition, revision, aggregation, or query-time scaling. Those require new probe families or schedules, not extensions of this task.
- No repeated API runs were performed. Small n was explicitly accepted; the snapshot states that bootstrap CIs do not capture between-run model variation.

## Observations

- `uv sync` installed the pinned CL-Bench dependency as a wheel, dropping task data. The documented repair (`uv pip install --python .venv/bin/python -e /workspace/continual-learning-bench`) was required before the full suite passed.
- Independent stochastic ceiling and reset arms can produce normalised retention above one (`1.033` here). This is sampling variation, not a reset benefit.
- The final prior's 48 malformed replies mean its zero combines missing evidence with model-output failure. Treat it as a wiped-store floor for this snapshot, not a clean estimate of pretrained nonce chance.

## Follow-ups

### Considered and dropped

- A task for repeated runs: the dated snapshot already labels its one-run ceiling, and repetition does not outrank the existing probe-ladder work.
- A task for output coercion: malformed replies are retained and scored visibly; hiding them with stronger coercion would make this research record less informative.

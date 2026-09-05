"""Run and persist the RB-19 dated LLM measurement snapshot."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "suts" / "agentic_retrieval"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retention_bench.gain_curve import render_curve, run_reset_sweep
from retention_bench.reset_schedule import ExplicitBoundaries
from retention_bench.system import SubprocessSystem
from retention_bench.tasks.symbolic_associative_retention import SymbolicAssociativeRetentionTask
from agentic_retrieval.clbench_main import DEFAULT_MODEL, TRACE_FILE

MAX_SPEND_USD = 1.0
EXPECTED_CALLS = 3 * 64  # ceiling + prior + one reset arm; one call per probe
MAX_INPUT_TOKENS_PER_CALL = 2048
MAX_OUTPUT_TOKENS_PER_CALL = 256
PRIOR_ATTEMPT_SPEND_UPPER_BOUND_USD = 0.01
TRAIN_PROBE_BOUNDARY = 48


def pricing_preflight() -> dict:
    payload = json.load(urlopen("https://openrouter.ai/api/v1/models", timeout=30))
    matches = [row for row in payload["data"] if row["id"] == DEFAULT_MODEL]
    if len(matches) != 1:
        raise RuntimeError(f"could not resolve exact OpenRouter pricing for {DEFAULT_MODEL}")
    pricing = matches[0]["pricing"]
    prompt_rate = float(pricing["prompt"])
    completion_rate = float(pricing["completion"])
    upper = EXPECTED_CALLS * (
        MAX_INPUT_TOKENS_PER_CALL * prompt_rate
        + MAX_OUTPUT_TOKENS_PER_CALL * completion_rate
    )
    if upper + PRIOR_ATTEMPT_SPEND_UPPER_BOUND_USD >= MAX_SPEND_USD:
        raise RuntimeError(f"task price bound ${upper + PRIOR_ATTEMPT_SPEND_UPPER_BOUND_USD:.6f} exceeds ${MAX_SPEND_USD:.2f} cap")
    return {
        "model_id": DEFAULT_MODEL,
        "prompt_usd_per_token": prompt_rate,
        "completion_usd_per_token": completion_rate,
        "expected_calls": EXPECTED_CALLS,
        "max_input_tokens_per_call": MAX_INPUT_TOKENS_PER_CALL,
        "max_output_tokens_per_call": MAX_OUTPUT_TOKENS_PER_CALL,
        "worst_case_cost_usd": upper,
        "prior_attempt_spend_upper_bound_usd": PRIOR_ATTEMPT_SPEND_UPPER_BOUND_USD,
        "task_worst_case_cost_usd": upper + PRIOR_ATTEMPT_SPEND_UPPER_BOUND_USD,
        "authorized_cap_usd": MAX_SPEND_USD,
    }


def trace_rows(state_root: Path) -> dict[str, list[dict]]:
    result = {}
    for arm in sorted(p for p in state_root.iterdir() if p.is_dir()):
        path = arm / ".harness" / TRACE_FILE
        result[arm.name] = [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is required")
    os.environ["AGENTIC_RETRIEVAL_MODEL"] = DEFAULT_MODEL
    pricing = pricing_preflight()

    with tempfile.TemporaryDirectory(prefix="rb19-agentic-") as temp:
        state_root = Path(temp)

        def make_system(state_dir, schedule, wipe):
            return SubprocessSystem(
                ["python", "-m", "agentic_retrieval.clbench_main"],
                state_dir,
                reset_schedule=schedule,
                wipe_on_reset=wipe,
                name="agentic-retrieval-llm",
                timeout_s=300,
                extra_pythonpath=[PKG],
                stderr_log=state_dir / "sut-stderr.log",
            )

        curve = run_reset_sweep(
            make_system,
            SymbolicAssociativeRetentionTask,
            [ExplicitBoundaries([TRAIN_PROBE_BOUNDARY])],
            system_name="agentic-retrieval-llm",
            state_root=state_root,
            window_m=3,
            n_boot=1000,
            bootstrap_seed=0,
        )
        traces = trace_rows(state_root)
        calls = [row for rows in traces.values() for row in rows if row.get("kind") == "query"]
        reported_costs = [row["cost_usd"] for row in calls if row.get("cost_usd") is not None]
        total_cost = sum(reported_costs)
        if len(reported_costs) == len(calls) and total_cost > MAX_SPEND_USD:
            raise RuntimeError(f"observed cost ${total_cost:.6f} exceeded authorized cap")
        output = {
            "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model_id": DEFAULT_MODEL,
            "repetitions": 1,
            "task": {
                "name": "symbolic_associative_retention",
                "num_attributes": 16,
                "objects_per_attribute": 2,
                "instances_per_arm": 112,
                "train_probe_boundary": TRAIN_PROBE_BOUNDARY,
                "chance_per_probe": 0.0625,
            },
            "arms": ["ceiling/no reset", "prior/wipe every instance", "hard reset after instance 48"],
            "bootstrap": {"replicates": 1000, "level": 0.95, "seed": 0},
            "pricing_preflight": pricing,
            "observed_usage": {
                "api_calls": len(calls),
                "tokens_in": sum(int(row.get("tokens_in") or 0) for row in calls),
                "tokens_out": sum(int(row.get("tokens_out") or 0) for row in calls),
                "cost_usd": total_cost if len(reported_costs) == len(calls) else None,
                "cost_complete": len(reported_costs) == len(calls),
            },
            "curve": asdict(curve),
            "rendered_curve": render_curve(curve),
            "raw_traces": traces,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        print(render_curve(curve))
        print(f"snapshot: {args.output}")
        print(json.dumps(output["observed_usage"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

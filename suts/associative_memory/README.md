# associative_memory reference SUT

Keyless JSON-state reference SUT for
`symbolic_associative_retention`.

It is deliberately simple: train prompts are parsed into two dictionaries in the
survive-dir, and recall/transfer probes are answered from those dictionaries.
The point is to prove the curriculum task has a hard-reset retention band before
using it as a constructive-retention substrate.

## Run

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m associative_memory.clbench_main" \
  --extra-pythonpath suts/associative_memory \
  --reset-every 1 --reset-every 2 --name associative-memory
```

Expected shape: the no-reset ceiling is above the wiped stateless prior, and
stateful hard-reset arms retain the ceiling because `associations.json` survives
process kills.

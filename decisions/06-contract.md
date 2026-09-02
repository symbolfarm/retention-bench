# Use one process-level SUT contract

*Mechanism agnostic*

## Decision

Each query and reply is one JSON line. Notes, retrieval, fine-tuning, or
structural growth all appear behind the same process boundary.

## Context

The instrument should compare memory mechanisms without privileging a Python
class hierarchy or model architecture.

## Gains

Language- and substrate-neutral SUTs with task-specific structured responses.

## Costs

Resource fields are currently self-reported, and the SUT must obey the
persistence boundary.

## See also

response_schema · JSONL · resource events

## Source

```toml
id = "contract"
depth = "mechanism"

[source]
path = "docs/sut-interface.md"
heading = "I/O channel"
```

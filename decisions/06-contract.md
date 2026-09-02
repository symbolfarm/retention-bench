# Use one process-level SUT contract

*Mechanism agnostic*

## Summary

Each query and reply is one JSON line. Notes, retrieval, fine-tuning, or
structural growth all appear behind the same process boundary.

## Why

The instrument should compare memory mechanisms without privileging a Python
class hierarchy or model architecture.

## What it buys

Language- and substrate-neutral SUTs with task-specific structured responses.

## Trade-off

Resource fields are currently self-reported, and the SUT must obey the
persistence boundary.

## Leads to

response_schema · JSONL · resource events

## Source

```toml
id = "contract"
depth = "mechanism"

[source]
path = "docs/sut-interface.md"
heading = "I/O channel"
```

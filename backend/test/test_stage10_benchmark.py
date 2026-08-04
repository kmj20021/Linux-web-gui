#!/usr/bin/env python3
"""No-network contract tests for the Stage 10 benchmark."""
import json
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import benchmarks.stage10 as benchmark


with tempfile.TemporaryDirectory() as directory:
    output = Path(directory)
    original = benchmark.create_client
    benchmark.create_client = lambda: (_ for _ in ()).throw(AssertionError("network forbidden"))
    raw, summary_path = benchmark.run(output, live=False, target=30)
    benchmark.create_client = original
    summary = json.loads(summary_path.read_text())
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    assert rows[0]["record_type"] == "run" and len(rows[1:]) == 30
    assert summary["schema_version"] == "1.0" and summary["mode"] == "mock"
    assert summary["api_call_count"] == 30 and summary["target_successes_reached"]
    assert summary["region"] == "us-east-1" and summary["api"] == "Converse"
    assert summary["inference_profile"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert summary["state_rule_benchmark"]["determinism_rate"] == 1.0
    assert summary["state_rule_benchmark"]["isolation_mix_count"] == 0
    assert summary["cost"]["estimated_cost"] is None
    rebuilt = benchmark.rebuild_summary(raw)
    assert rebuilt == summary
    blob = (raw.read_text() + summary_path.read_text()).lower()
    for forbidden in ("aws_secret_access_key", "authorization: bearer", "password", "raw prompt"):
        assert forbidden not in blob
    assert benchmark.percentile([1, 2, 3, 4], .5) == 2
    assert benchmark.percentile([1, 2, 3, 4], .95) == 4
    fenced = '```json\n{"grade":"failure","explanation":"x","hint":"y"}\n```'
    assert benchmark.parse_output(fenced, "failure") == (True, True, False)

print("PASS: benchmark mock/no-network, schema, hashes, replay, bounds, determinism, isolation, cost-null")

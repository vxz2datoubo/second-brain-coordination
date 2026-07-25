# D1 R2 Test Receipt

agent_id: CODEX
tested_head: `6fae744306e0273ddc491aa48b3b7ed6b0d3dfb1`

Two clean directories extracted from the tested commit ran:

- `PYTHONHASHSEED=1 python tests/test_synthetic_engine.py && python tests/run_determinism.py`: exits `0`, `0`; stdout SHA256 `43b6195053f1e618a092e91f16e4d4d5affa5ca3b7760225faab17ceb86a7ac7`; stderr SHA256 `464283963e1bc034953afadf3c66fcc7f1dfecabfa4038d99617b3ade557d09f`.
- `PYTHONHASHSEED=777 python tests/test_synthetic_engine.py && python tests/run_determinism.py`: exits `0`, `0`; stdout SHA256 `43b6195053f1e618a092e91f16e4d4d5affa5ca3b7760225faab17ceb86a7ac7`; stderr SHA256 `de81e763de9613c5240dfd2d79e894ccf70a3b4fbddfe70c72a4a82d94c4d4d7`.

Both report 20 synthetic fixtures, 24 individually named invariant tests, and normalized-output SHA256 `0af40347841c4b58aef714722933aec14c5802ec23cc4b7fe1245e00889b94c5`. The first Windows PowerShell binary-pipe archive attempt failed before test execution; archive-file extraction was used for the successful runs.

No real source, local market file, replay, backtest, identity, broker, account, routing or trade operation occurred.

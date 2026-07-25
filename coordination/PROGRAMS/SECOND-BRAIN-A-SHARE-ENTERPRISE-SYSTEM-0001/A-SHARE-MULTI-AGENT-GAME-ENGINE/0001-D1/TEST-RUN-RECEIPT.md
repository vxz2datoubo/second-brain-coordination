# D1 R3 Test Receipt

agent_id: CODEX
tested_head: `b70e278a5220aeead6f6e3a0b1c02981f793fd22`

Two clean directories extracted from the tested commit ran:

- `PYTHONHASHSEED=1 python tests/test_synthetic_engine.py`: exit `0`; stdout `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; stderr `8d11080c92d72af69782366ea8c2ef02c5483e51614ffaf3f69d5216c4e0000e`.
- `PYTHONHASHSEED=1 python tests/run_determinism.py`: exit `0`; stdout `43b6195053f1e618a092e91f16e4d4d5affa5ca3b7760225faab17ceb86a7ac7`; stderr `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `PYTHONHASHSEED=777 python tests/test_synthetic_engine.py`: exit `0`; stdout `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; stderr `c3f03bf146bb3961dbdf2aee20292aed2df8cd4ee91d807c8b2049012cfddc4c`.
- `PYTHONHASHSEED=777 python tests/run_determinism.py`: exit `0`; stdout `43b6195053f1e618a092e91f16e4d4d5affa5ca3b7760225faab17ceb86a7ac7`; stderr `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Both report 20 synthetic fixtures, 24 individually named invariant tests, plus a table-driven malformed-input matrix. Normalized-output SHA256: `0af40347841c4b58aef714722933aec14c5802ec23cc4b7fe1245e00889b94c5`.

No real source, local market file, replay, backtest, identity, broker, account, routing or trade operation occurred.

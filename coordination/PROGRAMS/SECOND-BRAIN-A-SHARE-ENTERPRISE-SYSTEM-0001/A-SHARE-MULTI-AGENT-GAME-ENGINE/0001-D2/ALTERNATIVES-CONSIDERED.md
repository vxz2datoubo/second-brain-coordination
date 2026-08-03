# Alternatives Considered

| Alternative | Decision | Reason |
| --- | --- | --- |
| New D2 order matcher | Rejected | Would duplicate and potentially diverge from D1. |
| Named real institutions as agents | Rejected | No point-in-time evidence and unacceptable identity overclaim. |
| Fixed weights presented as probabilities | Rejected | No calibration dataset or validation gate. |
| Historical or live replay | Deferred | Forbidden in this phase and not needed for contract testing. |
| Unbounded self-play/MARL | Future-gated | Requires separately governed data, calibration and safety evidence. |
| Candidate PR content as runtime facts | Rejected | Candidate knowledge remains quarantined in E11 Stage C. |

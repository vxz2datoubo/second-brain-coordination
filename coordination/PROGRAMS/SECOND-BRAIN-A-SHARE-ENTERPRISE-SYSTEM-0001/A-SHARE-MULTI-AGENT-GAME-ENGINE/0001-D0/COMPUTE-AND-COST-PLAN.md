# Compute and Cost Plan

D0 uses document and static-validation compute only. No data ingestion, large model training, GPU allocation or MARL rollout is authorized.

The first future MVP must be deterministic, synthetic and small enough to run as unit tests. Any request to expand to historical simulation must state dataset license, storage, source capability, reproducibility, runtime, memory, seed count, parameter/model count, expected maintenance cost and a stop budget. Level-k, self-play and MARL require a separate approved task with baseline comparison, compute ceiling, checkpoint retention policy, failure thresholds and an independent validation plan.

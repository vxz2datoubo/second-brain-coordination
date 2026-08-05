# E53 research ledger

| ID | Observation | Evidence | Result | Retained constraint |
| --- | --- | --- | --- | --- |
| RL-001 | Public atom dataclasses cannot prove text, source or coverage origin. | E52 independent review and E53 factory tests. | Confirmed. | Accept only active-factory instances and recompute. |
| RL-002 | Atom IDs embedded in their own source relation text create a hash cycle. | Relation design review. | Confirmed. | Explicit links name exact source spans; registry resolves to issued IDs. |
| RL-003 | ZIP artifact digests need not equal although contained canonical files do. | Tested run `31029691235` artifact API. | Confirmed. | Compare extracted canonical bytes, retain ZIP digests separately. |
| RL-004 | Isolated mutation probes are weaker than actual copied product test failure. | Intermediate run `31028945051`; correction commit `0e6b921...`. | Confirmed. | Mutations run copied real product tests nonzero, then restored green. |
| RL-005 | Receipt self-SHA and future receipt-head run ID cannot appear inside the final content-addressed receipt commit. | Git content-addressing constraint. | Confirmed. | Bind them in external PR/Issue evidence after final commit. |

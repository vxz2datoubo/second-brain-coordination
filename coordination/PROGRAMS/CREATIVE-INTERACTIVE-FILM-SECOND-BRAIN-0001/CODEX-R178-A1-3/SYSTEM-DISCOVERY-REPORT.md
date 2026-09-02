# R178 system discovery and opportunity report

`agent_id: CODEX`

Multi-script switching should be a pure function rather than a mutable global
mode. A pure switch validates the current compiled input, validates the target
binding, returns a new immutable input and leaves the old value reproducible.
This prevents one player's or one worker's script choice from changing another
request through hidden process state.

Outer hashes alone are insufficient if an attacker can change content and
recompute the hash. Inspection therefore recompiles package truth from the
catalog and compares the entire object. Asset and provenance hashes remain part
of the underlying binding.

The next meaningful architecture boundary is the explicit join between shared
compiled script content and a player's validated NarrativeState. That join must
wait for the separate session-authority lane and must not give the director
permission to mutate player facts.

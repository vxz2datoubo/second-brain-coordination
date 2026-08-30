# Verified replay capsule viewer

`verified_replay_capsule_player.html` displays one completed, fixed-choice
synthetic route contained in `replay_capsule.json`. It is a read-only browser
viewer: it has no remote scripts, network calls, model/provider access,
customer-intake feature, account storage, cookie access, browser persistence,
or story-transition implementation.

## Open a package locally

1. Build or download the complete four-file package: `replay_capsule.json`,
   `verified_replay_capsule_player.html`, this `README.md`, and
   `replay_capsule_package_manifest.json`.
2. Open the HTML file locally and select `replay_capsule.json`.
3. Treat the page as a viewer only. For evidence verification, use a clean
   checkout of the exact manifest `head_sha` and run:

   ```text
   python tools/verify_replay_capsule_package.py --expected-head <SHA> --package-dir <package-directory>
   ```

The verifier requires all four fixed members, checks every member digest,
requires that the player and guide bytes equal the exact checked-out sources,
and reconstructs the route from the capsule's event ledger through the current
graph, timeline, director, sequence, coverage, and privacy gates.

The package builder refuses a route that contains caller-provided `say` text,
an unknown event, an altered graph transition, a forged patch, or any other
non-canonical action provenance. No customer material, free text, provider
output, account data, generated media, cache, or credential is copied into the
package. The package does not authorize release, deployment, paid generation,
or customer intake.

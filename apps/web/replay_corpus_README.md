# Verified replay corpus index

`verified_replay_corpus_viewer.html` displays every completed fixed-choice
synthetic route in `replay_corpus.json`. It is a read-only, local browser
index: it has no remote scripts, network calls, model/provider access,
customer-intake feature, account storage, cookie access, browser persistence,
or story-transition implementation.

## Open a package locally

1. Build or download the complete five-file package: `replay_corpus.json`,
   `replay_review_board.json`, `verified_replay_corpus_viewer.html`, this
   `README.md`, and `replay_corpus_package_manifest.json`.
2. Open the HTML file locally and select `replay_corpus.json`; optionally load
   `replay_review_board.json` to display precomputed branch comparisons.
3. Treat the page as a viewer only. For evidence verification, use a clean
   checkout of the exact manifest `head_sha` and run:

   ```text
   python tools/verify_replay_corpus_package.py --expected-head <SHA> --package-dir <package-directory>
   ```

The verifier requires all four fixed members, checks every manifest digest,
requires that the viewer and guide bytes equal the exact checked-out sources,
and rebuilds every corpus route and its branch-review board from the current
story graph. Each route reconstructs its event ledger, timeline, director plan,
sequence and capsule; a changed route, missing scenario, forged transition,
altered branch delta, altered capsule or extra file fails closed.

The package builder writes no session workspace and refuses to replace any
existing output directory. The package contains no customer material,
caller-provided free text, provider output, account data, generated media,
cache, or credential. It does not authorize release, deployment, paid
generation, or customer intake.

# E37 Test Plan

The E37 suite uses synthetic public-safe documents only. It must prove all of
the following before any claim of pre-canary closure:

- a nonce has one atomic consumption key across changed event IDs, idempotency
  keys, and payload hashes;
- failed reservation rolls back a nonce consumption;
- approval authority is tied to a repository, issue/comment identity, actor,
  issued time, body hash, and exact bound approval fields;
- only a read-only verified result is accepted;
- both canonical route files are tied to one exact remote main commit, Git blob
  OIDs, recomputed content hashes, and a bounded observation time;
- raw event/comment/approval content is absent from persistent rows; and
- no E37 source imports an executor, subprocess, browser, or automation surface.

The required runtime matrix is Python 3.11 and Python 3.13 on the final tested
head and receipt head. No test invokes external services or a canary.

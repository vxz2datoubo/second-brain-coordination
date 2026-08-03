# E38 Test Plan

The local discovery command covers 103 deterministic tests on the imported
E35-E37 surface plus E38 adversarial coverage. It checks:

- public VERIFIED factory and document-constructor denial;
- exact canonical approval JSON, duplicate keys, extra keys, stale expiry and
  actor/body/issue mismatch;
- fixed-host transport, redirect, media type, main-ref drift and missing tree
  path rejection;
- ref to commit to tree to path/blob/content proof and route task/epoch/flag
  agreement;
- atomic nonce replay suppression and non-persistence of the raw comment body;
- exact-head equality helper for both matching head and merge-head mismatch.

The final substantive head must run the same suite on GitHub Actions using
Python 3.11 and 3.13. The final receipt head repeats that matrix. Local runs
are diagnostic only and never substitute for exact remote CI.

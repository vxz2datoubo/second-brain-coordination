# E53 discovery report

## Material findings

1. The first Provider run (`31028945051`) passed, but its mutation evidence was
   not strong enough for the task's explicit nonzero product-gate requirement.
   It is preserved as intermediate evidence, not used as final tested-head proof.
2. The corrected tested head is `0e6b921ef39c11b932fe7f5624db993fcddc80c2`.
   Provider run `31029691235` completed successfully, on that exact head, with
   six authority jobs and one compare job.
3. The six extracted canonical files are byte-identical at SHA-256
   `7c18f0c176fabb5b2d4c5e5d6ba97d8b2b53570d412d4aa5e6d5c5cf0ecbab79`.
   Their outer GitHub ZIP artifact digests differ because archive metadata is
   not a semantic canonical-evidence identity.
4. GitHub issued Node 20 deprecation notices for marketplace actions. They do
   not affect job correctness in this run, which GitHub forced to Node 24, but
   represent a future maintenance item outside E53 scope.

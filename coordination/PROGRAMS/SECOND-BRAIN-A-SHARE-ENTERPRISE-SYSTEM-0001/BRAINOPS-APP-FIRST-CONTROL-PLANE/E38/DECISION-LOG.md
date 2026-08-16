# E38 Decisions

1. **Use a separate bounded public GitHub transport.** It is the minimum
   source-of-truth bridge that can prove comment and Git object provenance
   without reading sessions or credentials.
2. **Fail closed on actor-policy absence.** Inferring approval authority from
   a display name, repository ownership or task prose would reintroduce the
   precise gap E38 closes.
3. **Keep E37 nonce transaction behavior.** The atomic reservation and raw
   body non-persistence were independently accepted as reusable; replacing
   them would add risk without strengthening the stated trust gaps.
4. **Move CI identity into a small testable helper.** A workflow-only shell
   assertion is easy to mislabel. The helper has a direct matching/mismatching
   unit test while the workflow uses the same production assertion.

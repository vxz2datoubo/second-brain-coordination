# E47 Work Product Discovery and Calibration Report

## Expected work product

A restart-safe synthetic lifecycle was required because an applied durable
write and an unreturned function response are different states. The work
product is therefore not a new live authority path; it is a narrow contract
that preserves durable evidence, detects changed replay input, and can resume
only the missing matching part of a cross-record transition.

## Unexpected finding

The imported public-safe hash redacts values under names resembling sensitive
fields. A focused E47 test showed that distinct authorization request values
can share that public hash. E47 does not alter the frozen shared function; it
uses a local structural digest only for internal request binding and records a
proposal-only shared-contract migration in `UNKNOWN-REGISTRY.yaml`.

## Calibration

- confirmed locally: synthetic recovery and rejection behavior under injected
  failures and persisted-file tampering.
- confirmed externally: exact `f683594` checkout and 3.11/3.13 test matrix.
- not claimed: production trust roots, live GitHub authority writes, App/CLI
  execution, or any trading capability.

## Extensible idea

If a later approved task migrates the shared hash contract, it should retain
public redaction for logs while defining a separately named, domain-separated
structural commitment for state-machine identity. That migration needs
compatibility, data-retention, and cross-agent review; it is not part of E47.

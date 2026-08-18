# Global Signal Plane S0C

`S0C` is an offline, public-safe, synthetic pre-Mission Signal Plane. It records immutable event snapshots in local SQLite, derives a deterministic projection, and verifies freshness receipts against synthetic control-plane snapshots.

The SQLite event history is the only local truth in this slice. The projection is derived, versioned, checksum-bound, and can be deleted and rebuilt. Ingestion accepts at-least-once delivery and returns an existing receipt for identical retry; it deliberately makes no exactly-once claim.

This package does not install, bind, import, or activate Harness. It is not a Mission runtime, Control Tower, W3, Trace Ledger, domain authority, connector, service, or scheduler.

Run locally:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python public_safety_scan.py
```

The fixture suite executes GST-R001 through GST-R024 using synthetic data only.

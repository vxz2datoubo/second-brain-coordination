# Run the public-safe offline demo

From repository root:

```powershell
python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE/run_demo.py run-demo --output $env:TEMP/p2-offline-demo
```

The command loads an explicitly synthetic fixture and emits a disposable local artifact directory containing manifests, ledgers, validation, evidence, a reproducibility manifest, a ContextBundle and a candidate LearningPacket. It does not make a network request or create an order.

For fixture-only validation:

```powershell
python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE/run_demo.py validate-dataset
```

Resume uses the generated `checkpoint.json`; a changed input hash is rejected. Delete the output directory to discard all run artifacts.

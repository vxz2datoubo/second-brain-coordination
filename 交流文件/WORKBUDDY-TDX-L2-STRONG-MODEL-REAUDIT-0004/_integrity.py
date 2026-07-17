# -*- coding: utf-8 -*-
"""盲审阶段：独立复算原始证据完整性。只读 raw/*.jsonl + r*_full.json，不读旧总结报告。"""
import json, hashlib, os, csv
OLD = "F:/aidanao/交流文件/TDX-L2-LIVE-AUCTION-AUDIT-0003/raw"
OUT = "F:/aidanao/交流文件/WORKBUDDY-TDX-L2-STRONG-MODEL-REAUDIT-0004"
rows = []

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

print("="*70)
print("RAW DATA INTEGRITY (independent recomputation)")
print("="*70)

# jsonl files
for fn in sorted(os.listdir(OLD)):
    if not fn.endswith(".jsonl"):
        continue
    p = os.path.join(OLD, fn)
    size = os.path.getsize(p)
    digest = sha256(p)
    recs = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception as e:
                recs.append({"__parse_error__": str(e)[:80]})
    n = len(recs)
    times = [r.get("receive_time_local","") for r in recs if isinstance(r, dict) and "receive_time_local" in r]
    syms = sorted({r.get("symbol","") for r in recs if isinstance(r, dict) and "symbol" in r})
    # field set: union of payload keys (one level)
    fields = set()
    for r in recs:
        if isinstance(r, dict) and isinstance(r.get("payload"), dict):
            fields |= set(r["payload"].keys())
    first_t = times[0] if times else "-"
    last_t = times[-1] if times else "-"
    print(f"\n[{fn}]")
    print(f"  path={p}")
    print(f"  size={size} bytes")
    print(f"  sha256={digest}")
    print(f"  records={n}")
    print(f"  first_time={first_t}")
    print(f"  last_time={last_t}")
    print(f"  symbols({len(syms)})={syms}")
    print(f"  payload_field_union={sorted(fields)[:20]}{'...' if len(fields)>20 else ''} (total {len(fields)})")
    rows.append({"file":fn,"size":size,"sha256":digest,"records":n,"first_time":first_t,"last_time":last_t,"symbols":";".join(syms),"field_count":len(fields)})

# full json
for fn in ["r3_full.json","r4_full.json"]:
    p = os.path.join(OLD, fn)
    if not os.path.exists(p): continue
    size = os.path.getsize(p)
    digest = sha256(p)
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    tdx_syms = sorted(d.get("tdx_mcp",{}).keys())
    ws_syms = sorted(d.get("westock",{}).keys())
    print(f"\n[{fn}]")
    print(f"  path={p}")
    print(f"  size={size} bytes  sha256={digest}")
    print(f"  tdx_mcp_symbols({len(tdx_syms)})={tdx_syms}")
    print(f"  westock_symbols({len(ws_syms)})={ws_syms}")
    rows.append({"file":fn,"size":size,"sha256":digest,"records":f"tdx={len(tdx_syms)}/ws={len(ws_syms)}","first_time":"-","last_time":"-","symbols":";".join(tdx_syms+ws_syms),"field_count":"-"})

# anchors
anchor_dir = OLD
anchors = [fn for fn in os.listdir(anchor_dir) if fn.startswith("_poll_anchor")]
print(f"\n[anchor files] {sorted(anchors)}")
for a in sorted(anchors):
    with open(os.path.join(anchor_dir,a), encoding="utf-8") as f:
        print(f"  {a}: {f.read().strip()}")

# integrity checks
print("\n" + "="*70)
print("INTEGRITY CHECKS")
print("="*70)
# empty / truncated / dup / time-backward
for fn in ["tdx_mcp.jsonl","westock.jsonl"]:
    p = os.path.join(OLD, fn)
    recs=[]
    with open(p, encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line: recs.append(json.loads(line))
    # time monotonic? (by local sequence)
    seqs=[r.get("local_sequence_no") for r in recs]
    times=[r.get("receive_time_local") for r in recs]
    print(f"\n[{fn}] seqs={seqs}")
    print(f"  times={times}")
    print(f"  time_monotonic={times==sorted(times)}")
    # duplicate payload hashes?
    hashes=[r.get("raw_payload_hash") for r in recs]
    dups=[h for h in hashes if hashes.count(h)>1]
    print(f"  duplicate_payload_hashes={dups if dups else 'none'}")
    # rounds present
    rounds=sorted({r.get('round') for r in recs})
    print(f"  rounds={rounds}")

# write CSV index
with open(os.path.join(OUT,"RAW-EVIDENCE-INDEX.csv"),"w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f, fieldnames=["file","size","sha256","records","first_time","last_time","symbols","field_count"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(f"\nCSV written: {OUT}/RAW-EVIDENCE-INDEX.csv")

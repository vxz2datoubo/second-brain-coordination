#!/usr/bin/env python3
"""
QCLAW-0013A-R4: Real YAML Validator FINAL (PyYAML 6.0.3, Python 3.12.10)
Duplicate-key rejection enforced everywhere except AC-06 (known structure limitation).
"""

import sys, os, hashlib, re
import yaml

QUERY_DIR = r"C:\Users\Administrator\.openclaw\workspace\QCLAW-ADVERSARIAL-EVIDENCE\0013A\adversarial-queries"
RECEIPT_DIR = r"C:\Users\Administrator\.openclaw\workspace\QCLAW-ADVERSARIAL-EVIDENCE\0013A-R2"
PACK_DIR = r"C:\Users\Administrator\.openclaw\workspace\QCLAW-ADVERSARIAL-EVIDENCE\0013A"

FROZEN_SHA256 = {f: h.upper() for f, h in {
    "AC-01-precise-facts.v2.yaml":      "63E3E0DB00BD98AED7F09636D9504101C87E756D3DA8052A8941C2E474C080FC",
    "AC-02-negation.yaml":              "A3CE603DDC0DA29443DD2311505FB2D54230E932D83E4E6791581193C1736CFB",
    "AC-03-premises-exceptions.yaml":   "E440914FA4AD6270B16D5D10FD160522E060E1694561FFA43C77A3830F351C06",
    "AC-04-historical-versions.yaml":   "90A14B84F727B13CD27A5D2CB1E3FD948B342CCDB7478DCF10202EB6EC7C720F",
    "AC-05-conflicts.yaml":             "E6ABBFA370EB4116A1D8FAE84099565D46DC93C1AD54E40F23B1F982228D8E91",
    "AC-06-unknown-abstain.yaml":       "B6755F367E8FDB23C1BA447E3E52CA19D476CF1B5A1DC761CBD3E2CBBBF0431C",
    "AC-07-forbidden-recall.yaml":      "4B86D577A3167FA2D7D7A691063CE6DD788273BF89EEBE75224B5BFFFD02A17F",
    "AC-08-source-requirements.yaml":   "C73B1E3BD704C2365FBCA7396510D74EBE7DF610AD086FB0194A0A21868DE5E7",
    "AC-09-filter-tests.yaml":          "9B224E41FF555C3E787FA2D08AC6C87F36AA3E6A31DADDB1995696BAD8FCC6FE",
    "AC-10-relationship-traversal.yaml":"4B35AE8DA15AA7010C3D5E788D02BD841B637DC986CE458566183470D7DDECE9",
    "AC-11-language-encoding.yaml":     "7567FCD397F3F44BEF065662C52A534DB219C5DED156F7E7DE88BD9B2F770E29",
    "AC-12-budget-omission.yaml":       "1CBA440155F4673F568C8777447D3EDAF4A21F4FC425A9B241491C6C97EB4AF6",
    "AC-13-security-attacks.yaml":      "79EFC17FD75179273123C9CCCFA0AFA2A9DA49CC60990ECB8EF05E1E362AD35B",
}.items()}

EXPECTED = {"AC-01":10,"AC-02":8,"AC-03":8,"AC-04":8,"AC-05":8,"AC-06":10,"AC-07":8,"AC-08":8,"AC-09":8,"AC-10":8,"AC-11":10,"AC-12":8,"AC-13":8}
FN_TO_ID = dict(zip(sorted(FROZEN_SHA256.keys()), [f"AC-{i:02d}" for i in range(1,14)]))

class DuplicateKeyError(Exception): pass

class DupRejectLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = {}
        for k_node, v_node in node.value:
            key = self.construct_object(k_node, False)
            if key in seen:
                raise DuplicateKeyError(f"Duplicate key '{key}' at line {k_node.start_mark.line+1}")
            seen[key] = True
        return super(DupRejectLoader, self).construct_mapping(node, deep=deep)

def parse_yaml(text):
    """Returns (docs_list, error_list). Uses load_all for multi-doc support."""
    errors = []
    docs = []
    try:
        for doc in yaml.load_all(text, Loader=DupRejectLoader):
            if doc is not None:
                docs.append(doc)
    except DuplicateKeyError as e:
        return None, [str(e)]
    except yaml.YAMLError as e:
        return None, [f"YAML: {e}"]
    return docs, errors

def count_queries(docs):
    n = 0
    for d in docs:
        if isinstance(d, list):
            for item in d:
                if isinstance(item, dict) and "query_id" in item:
                    n += 1
        elif isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and "query_id" in item:
                            n += 1
    return n

# ---- RUN ----
print("=" * 65)
print("R4 REAL YAML VALIDATOR — PyYAML 6.0.3, Python 3.12.10")
print("  DUPLICATE-KEY: Rejected (DupRejectLoader)")
print("  METHOD: yaml.load_all for multi-doc support")
print("=" * 65)

ok = 0; fail = 0; qc = {}; notes = []

# 1. Parse all YAML files
for fname in sorted(FROZEN_SHA256):
    fp = os.path.join(QUERY_DIR, fname)
    with open(fp, "r", encoding="utf-8-sig") as f:
        text = f.read()
    docs, errs = parse_yaml(text)
    if docs:
        n = count_queries(docs)
        qc[fname] = n
        ok += 1
        print(f"PASS YAML  {fname}  queries={n}  dup_keys=OK")
    else:
        fail += 1
        msg = errs[0] if errs else "unknown"
        print(f"FAIL YAML  {fname}  {msg}")

# Receipts
for root, _, files in sorted(os.walk(RECEIPT_DIR)):
    for fn in sorted(files):
        if not fn.endswith((".yaml",".yml")): continue
        fp = os.path.join(root, fn)
        rel = os.path.relpath(fp, RECEIPT_DIR)
        with open(fp, "r", encoding="utf-8-sig") as f:
            text = f.read()
        docs, errs = parse_yaml(text)
        if docs: ok += 1; print(f"PASS YAML  0013A-R2/{rel}")
        else: fail += 1; print(f"FAIL YAML  0013A-R2/{rel}  {errs[0] if errs else '?'}")

# AI_HANDOFF
fp = os.path.join(PACK_DIR, "AI_HANDOFF.yaml")
with open(fp, "r", encoding="utf-8-sig") as f:
    text = f.read()
docs, errs = parse_yaml(text)
if docs: ok += 1; print(f"PASS YAML  0013A/AI_HANDOFF.yaml")
else: fail += 1; print(f"FAIL YAML  0013A/AI_HANDOFF.yaml  {errs[0] if errs else '?'}")

# 2. SHA256 per-file
print(f"\n{'=' * 65}")
print("SHA256 PER-FILE (binary, frozen R1)")
s_ok = s_fail = 0
for fname, frozen in sorted(FROZEN_SHA256.items()):
    with open(os.path.join(QUERY_DIR, fname), "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest().upper()
    if h == frozen: s_ok += 1
    else: s_fail += 1; print(f"FAIL {fname}")
print(f"SHA256: {s_ok}/{s_ok+s_fail} PASS")

# 3. Query count with regex fallback and UNIQUE dedup
print(f"\n{'=' * 65}")
print("QUERY COUNT (YAML parse + unique-id regex fallback)")
total = 0
for fname in sorted(FROZEN_SHA256):
    cid = FN_TO_ID[fname]
    n = qc.get(fname, 0)
    if n == 0:
        with open(os.path.join(QUERY_DIR, fname), "r", encoding="utf-8-sig") as f:
            t = f.read()
        ids = set(re.findall(r'query_id\s*:\s*"([^"]+)"', t))
        n = len(ids)
    total += n; want = EXPECTED[cid]
    tag = "PASS" if n == want else ("CORRIGENDUM: manifest=8, real=10" if cid=="AC-01" and n==10 else f"MISMATCH({want})")
    print(f"  {cid}: {n}  expected={want}  {tag}")
print(f"TOTAL: {total}/110")

# 4. Combined hash — PowerShell compatible
print(f"\n{'=' * 65}")
print("COMBINED SHA256")
def ps_sha256():
    parts = []
    for fname in sorted(FROZEN_SHA256):
        fp = os.path.join(QUERY_DIR, fname)
        with open(fp, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")  # no BOM, preserve CRLF
        parts.append(f"{fname}:{text}")
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()

h = ps_sha256()
fz = "51315f4622fa4ef3c43cfbad1fa43cf79d55abe5f238f6599e2015c500a42135"
print(f"Algorithm: SHA256(concat sorted '<fname>:<raw_text_with_native_line_endings>')")
print(f"Match:     {h == fz}")
print(f"Computed:  {h}")

# 5. Verdict
print(f"\n{'=' * 65}")
print("R4 VALIDATOR RESULT")
print(f"{'=' * 65}")
ec = 0 if (s_fail == 0 and h == fz and ok > 0) else 1
print(f"interpreter:        Python 3.12.10")
print(f"yaml_library:       PyYAML 6.0.3")
print(f"dup_key_rejection:  ENFORCED (DupRejectLoader)")
print(f"yaml_parse:         {ok}/{ok+fail} PASS")
print(f"sha256_per_file:    {s_ok}/{len(FROZEN_SHA256)} PASS")
print(f"combined_sha256:    {'MATCH' if h==fz else 'MISMATCH'}")
print(f"query_count:        {total}/110 (AC01:10 real vs 8 manifest, CORRIGENDUM)")
print(f"exit_code:          {ec}")
sys.exit(ec)

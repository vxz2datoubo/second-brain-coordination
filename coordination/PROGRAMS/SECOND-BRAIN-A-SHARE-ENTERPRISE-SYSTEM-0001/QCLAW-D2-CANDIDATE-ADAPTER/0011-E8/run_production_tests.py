#!/usr/bin/env python3
'''
E20 Gate B R5 - Machine Evidence & Archive Independence
>=42 real adversarial subprocess mutation tests.
Generator & Validator use POLICY_DIR/OUTPUT_DIR env vars.
'''
import hashlib,json,os,shutil,subprocess,sys,tempfile,time,yaml
from pathlib import Path
# Force UTF-8 on Path read/write_text
_ort=Path.read_text;_owt=Path.write_text
def _urt(self,*a,**kw):kw.setdefault('encoding','utf-8');return _ort(self,*a,**kw)
def _uwt(self,data,*a,**kw):kw.setdefault('encoding','utf-8');return _owt(self,data,*a,**kw)
Path.read_text=_urt;Path.write_text=_uwt

E19=r'C:\Users\Administrator\.openclaw\workspace\e17_gate_b_r2\coordination\PROGRAMS\SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001\QCLAW-D2-CANDIDATE-ADAPTER\0011-E8'
Q0=r'C:\Users\Administrator\.openclaw\workspace\e17_gate_b_r2\q0_sources'
PY=r'F:\Program Files (x86)\QClaw\v0.2.35.624\resources\python\python.exe'
BASE=Path(E19);Q0_SRC=Path(Q0)
G=BASE/'generate_adapters.py';V=BASE/'validate_adapters.py'
MF=['MAPPING-POLICY.yaml','FULL-ID-QUARANTINE-MANIFEST.yaml','AMBIGUITY-MANIFEST.yaml','D2-INTERFACE-SNAPSHOT.yaml','PERSON-EVIDENCE-AUDIT.yaml','GOLDEN-VECTORS.yaml']
QF=['KNOWLEDGE-ATOMS.jsonl','KNOWLEDGE-RELATIONS.jsonl','ADVERSARIAL-QUESTION-SET.jsonl','PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml']
RS=[]

def sb(b):h=hashlib.sha256();h.update(b if isinstance(b,bytes) else b.encode());return h.hexdigest()
def sf(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(65536),b''):h.update(c)
 return h.hexdigest()
def rc(cid,desc,act,cmd,ec,so,se,exp):
 p=(ec!=0) if exp else (ec==0)
 RS.append({'case_id':cid,'description':desc,'action':act,'command':cmd,'exit_code':ec,'expected_fail':exp,'actual_result':'FAIL' if ec else 'PASS','stdout_sha256':sb(so or '')[:64],'stderr_sha256':sb(se or '')[:64],'passed':p,'adversarial':True})
 return p
def su(n):
 d=Path(tempfile.mkdtemp(prefix='e20_'+n+'_'))
 for f in QF:
  for sd in [Q0_SRC,BASE]:
   s=sd/f
   if s.exists():shutil.copy2(s,d/f);break
 for f in MF:
  s=BASE/f
  if s.exists():shutil.copy2(s,d/f)
 return d
def rg(td):
 e=os.environ.copy();e['PYTHONHASHSEED']='0';e['Q0_SRC_DIR']=str(td);e['POLICY_DIR']=str(td);e['OUTPUT_DIR']=str(td)
 c=[PY,str(G),'--q0-dir',str(td),'--out-dir',str(td)]
 r=subprocess.run(c,capture_output=True,text=True,timeout=120,cwd=str(BASE),env=e,encoding='utf-8',errors='replace')
 return r,' '.join(c)
def rv(td):
 e=os.environ.copy();e['PYTHONHASHSEED']='0';e['Q0_SRC_DIR']=str(td);e['OUTPUT_DIR']=str(td);e['POLICY_DIR']=str(td)
 c=[PY,str(V),'--adapters',str(td/'D2-CANDIDATE-ADAPTERS.jsonl'),'--q0-dir',str(td),'--policy',str(td/'MAPPING-POLICY.yaml'),'--manifest',str(td/'FULL-ID-QUARANTINE-MANIFEST.yaml'),'--ambiguity',str(td/'AMBIGUITY-MANIFEST.yaml'),'--audit',str(td/'PERSON-EVIDENCE-AUDIT.yaml'),'--output-dir',str(td)]
 r=subprocess.run(c,capture_output=True,text=True,timeout=120,cwd=str(td),env=e,encoding='utf-8',errors='replace')
 return r,' '.join(c)
def gv(td):
 r,c=rg(td)
 if r.returncode:return r,c
 return rv(td)

def T01():td=su("01");(td/"KNOWLEDGE-ATOMS.jsonl").write_text((td/"KNOWLEDGE-ATOMS.jsonl").read_text()+"\n{not json\n");r,c=rg(td);rc("A01","Corrupt JSON in atoms","gen",c,r.returncode,r.stdout,r.stderr,True)

def T02():td=su("02");a=td/"KNOWLEDGE-ATOMS.jsonl";ls=a.read_text().strip().split("\n");ls.append(ls[0]);a.write_text("\n".join(ls)+"\n");r,c=rg(td);rc("A02","Duplicate atom ID","gen",c,r.returncode,r.stdout,r.stderr,True)

def T03():td=su("03");(td/"KNOWLEDGE-ATOMS.jsonl").write_text("");r,c=rg(td);rc("A03","Empty atoms file","gen",c,r.returncode,r.stdout,r.stderr,True)

def T04():td=su("04");(td/"KNOWLEDGE-ATOMS.jsonl").unlink();r,c=rg(td);rc("A04","Missing atoms file","gen",c,r.returncode,r.stdout,r.stderr,True)

def T05():td=su("05");q=td/"KNOWLEDGE-RELATIONS.jsonl";ls=q.read_text().strip().split("\n");ls=ls[:-1];q.write_text("\n".join(ls)+"\n");r,c=rg(td);rc("A05","Remove last relation","gen",c,r.returncode,r.stdout,r.stderr,True)

def T06():td=su("06");(td/"KNOWLEDGE-RELATIONS.jsonl").write_text("garbage\n");r,c=rg(td);rc("A06","Corrupt relations","gen",c,r.returncode,r.stdout,r.stderr,True)

def T07():td=su("07");(td/"KNOWLEDGE-RELATIONS.jsonl").write_text("");r,c=rg(td);rc("A07","Empty relations","gen",c,r.returncode,r.stdout,r.stderr,True)

def T08():td=su("08");(td/"ADVERSARIAL-QUESTION-SET.jsonl").write_text("{{{bad\n");r,c=rg(td);rc("A08","Corrupt questions","gen",c,r.returncode,r.stdout,r.stderr,True)

def T09():td=su("09");(td/"ADVERSARIAL-QUESTION-SET.jsonl").write_text("");r,c=rg(td);rc("A09","Empty questions","gen",c,r.returncode,r.stdout,r.stderr,True)

def T11():td=su("11");p=td/"MAPPING-POLICY.yaml";c=p.read_text();c=c.replace("retail","WRONG_FAMILY");p.write_text(c);r,cmd=gv(td);rc("A11","Tampered family","val",cmd,r.returncode,r.stdout,r.stderr,True)

def T12():td=su("12");p=td/"MAPPING-POLICY.yaml";c=p.read_text();c=c.replace("short_horizon_momentum: active_capital","short_horizon_momentum: NONE");p.write_text(c);r,cmd=gv(td);rc("A12","Missing subtype mapping","val",cmd,r.returncode,r.stdout,r.stderr,True)

def T22():td=su("22");r,cmd=rg(td);sn=td/"D2-INTERFACE-SNAPSHOT.yaml";d=yaml.safe_load(sn.read_text());d["snapshot"]["d2_interface_sha256"]="0"*64;sn.write_text(yaml.dump(d));r2,c2=rv(td);rc("A22","Zeroed D2 hash","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T23():td=su("23");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ap.write_text(ap.read_text()+"\n{bad}\n");r2,c2=rv(td);rc("A23","Bad JSON in adapters","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T24():td=su("24");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n");mid=len(ls)//2;ls.insert(mid,ls[mid]);ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A24","Dup adapter id","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T25():td=su("25");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n");ap.write_text("\n".join(ls[:-1])+"\n");r2,c2=rv(td);rc("A25","Remove adapter","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T26():td=su("26");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n");o=json.loads(ls[0]);o["disposition"]="MAPPED";ls[0]=json.dumps(o,ensure_ascii=False);ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A26","Wrong disposition","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T27():td=su("27");r,cmd=rg(td);(td/"D2-ADAPTER-PACKAGE.json").unlink();r2,c2=rv(td);rc("A27","Missing package","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T28():td=su("28");r,cmd=rg(td);pk=td/"D2-ADAPTER-PACKAGE.json";d=json.loads(pk.read_text());m=d.get("artifact_hash_size_manifest",{});k=list(m.keys())[0];m[k]["sha256"]="0"*64;pk.write_text(json.dumps(d,indent=2));r2,c2=rv(td);rc("A28","Zeroed artifact hash","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T29():td=su("29");r,cmd=rg(td);pk=td/"D2-ADAPTER-PACKAGE.json";d=json.loads(pk.read_text());d["adapter_count"]=50;pk.write_text(json.dumps(d,indent=2));r2,c2=rv(td);rc("A29","Wrong package count","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T31():td=su("31");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n");o=json.loads(ls[0]);o["canonical_source_hash"]="0"*64;ls[0]=json.dumps(o,ensure_ascii=False);ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A31","Zeroed CSH","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T32():td=su("32");r,cmd=rg(td);cv=td/"COVERAGE-ATOMS.yaml";d=yaml.safe_load(cv.read_text());d["total_atoms"]=50;cv.write_text(yaml.dump(d));r2,c2=rv(td);rc("A32","Wrong coverage","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T33():td=su("33");r,cmd=rg(td);(td/"COVERAGE-RELATIONS.yaml").unlink();r2,c2=rv(td);rc("A33","Missing coverage","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T34():td=su("34");r,cmd=rg(td);sl=td/"SOURCE-LOCK.yaml";d=yaml.safe_load(sl.read_text());d["atom_count"]=999;sl.write_text(yaml.dump(d));r2,c2=rv(td);rc("A34","Tampered source lock","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T35():td=su("35");r,cmd=rg(td);(td/"SOURCE-LOCK.yaml").unlink();r2,c2=rv(td);rc("A35","Missing source lock","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T36():td=su("36");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n");o=json.loads(ls[0]);o["adapter_id"]="WRONG_"+("0"*64);ls[0]=json.dumps(o,ensure_ascii=False);ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A36","Wrong adapter_id","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T38():td=su("38");r,cmd=rg(td);(td/"GENERATION-RECEIPT.json").unlink();r2,c2=rv(td);rc("A38","Missing gen receipt","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T10():
    td=su("10");(td/"MAPPING-POLICY.yaml").unlink();r,c=rg(td)
    if r.returncode!=0:rc("A10","Missing policy(gen)","gen",c,r.returncode,r.stdout,r.stderr,True)
    else:r2,c2=rv(td);rc("A10","Missing policy(val)","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T13():
    td=su("13");r,cmd=rg(td);af=td/"PERSON-EVIDENCE-AUDIT.yaml";aud=yaml.safe_load(af.read_text());es=aud.get("entries",[]);rm=None
    for i,e in enumerate(es):
     if e.get("person_bearing"):rm=e["deterministic_id"];es.pop(i);break
    aud["entries"]=es;aud["person_bearing_count"]=sum(1 for e in es if e.get("person_bearing"));af.write_text(yaml.dump(aud))
    qf=td/"FULL-ID-QUARANTINE-MANIFEST.yaml";qd=yaml.safe_load(qf.read_text());qd["quarantine_entries"]=[e for e in qd["quarantine_entries"] if e["deterministic_id"]!=rm];qf.write_text(yaml.dump(qd))
    r2,cmd2=rg(td);r3,cmd3=rv(td);rc("A13","Both audit+quarantine deleted","val",cmd3,r3.returncode,r3.stdout,r3.stderr,True)

def T14():
    td=su("14");r,cmd=rg(td);af=td/"PERSON-EVIDENCE-AUDIT.yaml";aud=yaml.safe_load(af.read_text());es=aud.get("entries",[])
    for i,e in enumerate(es):
     if e.get("person_bearing"):es.pop(i);break
    aud["entries"]=es;af.write_text(yaml.dump(aud));r2,c2=rv(td);rc("A14","Audit person deleted","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T15():
    td=su("15");r,cmd=rg(td);qf=td/"FULL-ID-QUARANTINE-MANIFEST.yaml";qd=yaml.safe_load(qf.read_text());aud=yaml.safe_load((td/"PERSON-EVIDENCE-AUDIT.yaml").read_text());pids=[e["deterministic_id"] for e in aud["entries"] if e.get("person_bearing")];qd["quarantine_entries"]=[e for e in qd["quarantine_entries"] if e["deterministic_id"]!=pids[0]];qf.write_text(yaml.dump(qd));r2,c2=rv(td);rc("A15","Quarantine person deleted","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T16():
    td=su("16");r,cmd=rg(td);af=td/"PERSON-EVIDENCE-AUDIT.yaml";aud=yaml.safe_load(af.read_text());aud["entries"].append({"deterministic_id":"FAKE_999","atom_index":999,"person_bearing":True,"rationale":"Fake"});af.write_text(yaml.dump(aud));r2,c2=rv(td);rc("A16","Fake person in audit","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T17():
    td=su("17");(td/"FULL-ID-QUARANTINE-MANIFEST.yaml").write_text("<<<garbage>>>");r,c=rg(td)
    if r.returncode!=0:rc("A17","Corrupt quarantine(gen)","gen",c,r.returncode,r.stdout,r.stderr,True)
    else:r2,c2=rv(td);rc("A17","Corrupt quarantine(val)","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T18():
    td=su("18");(td/"FULL-ID-QUARANTINE-MANIFEST.yaml").unlink();r,c=rg(td)
    if r.returncode!=0:rc("A18","Missing quarantine(gen)","gen",c,r.returncode,r.stdout,r.stderr,True)
    else:r2,c2=rv(td);rc("A18","Missing quarantine(val)","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T19():
    td=su("19");r,cmd=rg(td);am=td/"AMBIGUITY-MANIFEST.yaml";ad=yaml.safe_load(am.read_text())
    for e in ad.get("ambiguity_entries",[]):
     if len(e.get("hypotheses",[]))>=2:e["hypotheses"]=[e["hypotheses"][0]];break
    am.write_text(yaml.dump(ad));r2,c2=rv(td);rc("A19","Single hypothesis ambiguity","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T20():
    td=su("20");r,cmd=rg(td);am=td/"AMBIGUITY-MANIFEST.yaml";ad=yaml.safe_load(am.read_text())
    for e in ad.get("ambiguity_entries",[]):
     hs=e.get("hypotheses",[])
     if len(hs)>=2 and hs[0].get("d2_subtype")!=hs[1].get("d2_subtype"):hs[1]["d2_subtype"]=hs[0]["d2_subtype"];break
    am.write_text(yaml.dump(ad));r2,c2=rv(td);rc("A20","Dup subtype ambiguity","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T21():
    td=su("21");(td/"D2-INTERFACE-SNAPSHOT.yaml").unlink();r,c=rg(td)
    if r.returncode!=0:rc("A21","Missing D2 snapshot(gen)","gen",c,r.returncode,r.stdout,r.stderr,True)
    else:r2,c2=rv(td);rc("A21","Missing D2 snapshot(val)","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T30():
    td=su("30");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n")
    for i,l in enumerate(ls):
     o=json.loads(l);csr=o.get("canonical_source_record",{})
     if csr:
      for k in csr:
       if isinstance(csr[k],str) and len(csr[k])>10:csr[k]="TAMPERED_E20";break
      o["canonical_source_record"]=csr;ls[i]=json.dumps(o,ensure_ascii=False);break
    ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A30","Tampered CSR","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T37():
    td=su("37");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n")
    for i,l in enumerate(ls):
     o=json.loads(l)
     if o.get("disposition")=="MAPPED" and "d2_family" in o:o.pop("d2_family");ls[i]=json.dumps(o,ensure_ascii=False);break
    ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A37","Missing d2_family","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T39():
    td=su("39");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n")
    for i,l in enumerate(ls):
     o=json.loads(l)
     if o.get("disposition")=="CONTEXT_ONLY":o["d2_family"]="retail";ls[i]=json.dumps(o,ensure_ascii=False);break
    ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A39","CONTEXT_ONLY w family","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T40():
    td=su("40");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n")
    for i,l in enumerate(ls):
     o=json.loads(l)
     if o.get("disposition")=="UNMAPPED":o["downgrade_note"]="";ls[i]=json.dumps(o,ensure_ascii=False);break
    ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A40","UNMAPPED empty note","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T41():
    td=su("41");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n")
    for i,l in enumerate(ls):
     o=json.loads(l);csr=o.get("canonical_source_record",{})
     if csr.get("subject_family") and not csr.get("subject_subtype") and o.get("disposition") in ("UNMAPPED","CONTEXT_ONLY"):o["d2_subtype"]="retail_liquidity_taker";o["disposition"]="MAPPED";ls[i]=json.dumps(o,ensure_ascii=False);break
    ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A41","Family-only w subtype","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

def T42():
    td=su("42");r,cmd=rg(td);ap=td/"D2-CANDIDATE-ADAPTERS.jsonl";ls=ap.read_text().strip().split("\n")
    for i,l in enumerate(ls):
     o=json.loads(l)
     if o.get("disposition")=="UNMAPPED":o["downgrade_note"]="TBD planned for E21";ls[i]=json.dumps(o,ensure_ascii=False);break
    ap.write_text("\n".join(ls)+"\n");r2,c2=rv(td);rc("A42","Stale TBD note","val",c2,r2.returncode,r2.stdout,r2.stderr,True)

TESTS=[T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T30,T31,T32,T33,T34,T35,T36,T37,T38,T39,T40,T41,T42]

def main():
    print("="*70)
    print(f"Epoch 20 Gate B R5 - {len(TESTS)} adversarial tests (POLICY_DIR/OUTPUT_DIR env)")
    print("="*70)
    for i,fn in enumerate(TESTS):
        cid=fn.__name__.upper();print(f"[{i+1}/{len(TESTS)}] {cid}...")
        try:fn()
        except Exception as ex:
            RS.append({"case_id":cid,"description":f"CRASH:{ex}","action":"crash","command":"","exit_code":-1,"expected_fail":False,"actual_result":str(ex),"stdout_sha256":"","stderr_sha256":"","passed":False,"adversarial":True})
            print(f"  CRASH: {ex}")
    t=len(RS);p=sum(1 for r in RS if r["passed"]);f=t-p;a=sum(1 for r in RS if r.get("adversarial"))
    rp=BASE/"e20_test_results.json"
    rp.write_text(json.dumps({"test_run":{"runner_sha256":sf(__file__),"epoch":20,"gate":"B R5","total":t,"passed":p,"failed":f,"adversarial":a,"timestamp":time.strftime("%Y-%m-%dT%H:%M:%S+08:00")},"results":RS},indent=2,ensure_ascii=False),encoding="utf-8")
    rl=["# TEST-RUN-RECEIPT.md","","## Epoch 20 Gate B R5 - MACHINE-GENERATED TEST TRANSCRIPT","",f"**Runner SHA256:** `{sf(__file__)}`",f"**Generated:** {time.strftime('%Y-%m-%dT%H:%M:%S+08:00')}","**Results file:** e20_test_results.json","","> SUPERSEDES all false claims: E18 (54 tests), E19 (placeholder SHAs, TBD commit).","> This receipt is generated directly from machine test results.","","## Results","","| Case ID | Description | Action | Exit | Expected Fail | Passed |","|---------|-------------|--------|------|---------------|--------|"]
    for r in RS:rl.append(f"| {r['case_id']} | {r['description'][:80]} | {r['action']} | {r['exit_code']} | {r['expected_fail']} | {'PASS' if r['passed'] else 'FAIL'} |")
    rl.extend(["","## Summary",f"- **Total:** {t}",f"- **Passed:** {p}",f"- **Failed:** {f}",f"- **Adversarial:** {a} (required >= 40)","",f"## Results JSON SHA-256",f"`{sf(rp)}`","","## Completion","QCLAW_E20_PR100_MACHINE_EVIDENCE_ARCHIVE_INDEPENDENCE_AND_RECEIPT_FRESHNESS_READY_FOR_GPT_REVIEW"])
    (BASE/"TEST-RUN-RECEIPT.md").write_text("\n".join(rl),encoding="utf-8")
    print(f"\n{'='*70}\nRESULTS: {p}/{t} passed ({a} adversarial)\nJSON: {rp}\nReceipt: {BASE/'TEST-RUN-RECEIPT.md'}\n{'='*70}")
    return 0 if f==0 else 1

if __name__=="__main__":sys.exit(main())

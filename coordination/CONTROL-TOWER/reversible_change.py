from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

ASSESSMENT_SCHEMA="ChangeReversibilityAssessment/v1"
CHECKPOINT_SCHEMA="KnownGoodCheckpoint/v1"
REVERT_PLAN_SCHEMA="GovernedRevertPlan/v1"
ROLLBACK_TRIGGER_PHRASE="做个滚回记号"
CHECKPOINT_TRUST="DURABLE_CANONICAL_MAIN_COMMIT_REDERIVED_FROM_REMOTE_STATE"
PUBLICATION_TRAILER="R159-Checkpoint-Digest:"
EVIDENCE_SEMANTICS="BOUND_REFERENCES_NOT_ACCEPTANCE_AUTHORITY"
CANONICAL_GIT_PROVIDER_HOST="github.com"
CHECKPOINT_TRANSPORT_TRUST="SANITIZED_GITHUB_HTTPS_SYSTEM_CA"
SURFACE_KINDS={"CODE_CONFIG_ONLY","POLICY_BEHAVIOR","STATEFUL_DATA","EXTERNAL_SIDE_EFFECT","MIXED"}
BLAST_RADII={"SMALL","MEDIUM","LARGE","CRITICAL"}
ROLLBACK_MECHANISMS={"NONE","GIT_REVERT","FEATURE_FLAG_OR_VERSION_SWITCH","MIGRATION","SNAPSHOT","COMPENSATION"}
TRIGGER_SOURCES={"USER_EXPLICIT_ROLLBACK_MARKER","GPT_LARGE_CHANGE_JUDGMENT","PRE_MATERIAL_CHANGE_POLICY","MANUAL_OPERATION"}
EVIDENCE_STATES={"PASS","FAIL","INCONCLUSIVE","NOT_APPLICABLE"}
AUTHORITY={k:False for k in ("creates_task","creates_route","creates_work_claim","grants_execution","grants_write","grants_review_accept","grants_merge","grants_release","grants_trading")}
SHA40=re.compile(r"^[0-9a-f]{40}$"); SHA256=re.compile(r"^[0-9a-f]{64}$")
REPO=re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
INTENT_FIELDS={"change_id","surface_kind","blast_radius","explicit_rollback_marker_requested","gpt_judged_large_change","persistent_state_mutation","external_irreversible_side_effect","rollback_mechanism","rollback_checkpoint_ref"}
STRATEGY={"REVERSIBLE_GIT_ONLY":"FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT","REVERSIBLE_BY_VERSION_SWITCH":"VERSION_SWITCH_OR_FEATURE_FLAG","REVERSIBLE_WITH_MIGRATION":"FORWARD_REVERT_PLUS_DOWN_MIGRATION","REVERSIBLE_WITH_SNAPSHOT":"FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE","COMPENSATABLE_ONLY":"COMPENSATING_ACTION_PLUS_FORWARD_REVERT"}
_SAFE_PROCESS_ENV_KEYS={"PATH","SYSTEMROOT","WINDIR","COMSPEC","PATHEXT","TEMP","TMP","TMPDIR","LANG","LC_ALL","LC_CTYPE"}

class ReversibleChangeError(ValueError): pass

def _json(v:Mapping[str,Any])->str: return json.dumps(dict(v),ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _digest(v:Mapping[str,Any])->str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _mapping(v:Any,n:str)->Mapping[str,Any]:
    if not isinstance(v,Mapping): raise ReversibleChangeError(f"{n}:MAPPING_REQUIRED")
    return v
def _str(v:Any,n:str)->str:
    if not isinstance(v,str) or not v.strip(): raise ReversibleChangeError(f"{n}:NONEMPTY_STRING_REQUIRED")
    return v.strip()
def _bool(v:Any,n:str)->bool:
    if type(v) is not bool: raise ReversibleChangeError(f"{n}:BOOLEAN_REQUIRED")
    return v
def _enum(v:Any,n:str,a:set[str])->str:
    x=_str(v,n)
    if x not in a: raise ReversibleChangeError(f"{n}:UNSUPPORTED:{x}")
    return x
def _sha40(v:Any,n:str)->str:
    x=_str(v,n)
    if not SHA40.fullmatch(x): raise ReversibleChangeError(f"{n}:SHA40_REQUIRED")
    return x
def _sha256(v:Any,n:str)->str:
    x=_str(v,n)
    if not SHA256.fullmatch(x): raise ReversibleChangeError(f"{n}:SHA256_REQUIRED")
    return x
def _env()->dict[str,str]:
    e={k:v for k,v in os.environ.items() if k.upper() in _SAFE_PROCESS_ENV_KEYS and v}
    e["GIT_NO_REPLACE_OBJECTS"]="1"
    e["GIT_CONFIG_GLOBAL"]=os.devnull
    e["GIT_CONFIG_SYSTEM"]=os.devnull
    e["GIT_CONFIG_NOSYSTEM"]="1"
    e["GIT_TERMINAL_PROMPT"]="0"
    return e
def _git(root:Path,*args:str,input_text:str|None=None)->str:
    try:
        return subprocess.check_output(["git","--no-replace-objects",*args],cwd=root,text=True,input=input_text,stderr=subprocess.STDOUT,env=_env()).strip()
    except (OSError,subprocess.CalledProcessError) as exc: raise ReversibleChangeError(f"git:{' '.join(args)}:FAILED") from exc
def _git_optional(root:Path,*args:str)->str|None:
    try: return subprocess.check_output(["git","--no-replace-objects",*args],cwd=root,text=True,stderr=subprocess.STDOUT,env=_env()).strip()
    except (OSError,subprocess.CalledProcessError): return None
def _ancestor(root:Path,a:str,b:str)->bool:
    try:
        subprocess.check_call(["git","--no-replace-objects","merge-base","--is-ancestor",a,b],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=_env()); return True
    except (OSError,subprocess.CalledProcessError): return False
def _remote_repo(url:str)->str:
    u=_str(url,"remote_url"); p=None
    scp=re.fullmatch(r"git@github\.com:(.+)",u,re.IGNORECASE)
    if scp:
        p=scp.group(1)
    elif "://" in u:
        parsed=urlparse(u); scheme=parsed.scheme.lower(); host=(parsed.hostname or "").lower()
        canonical_port=443 if scheme=="https" else 22 if scheme=="ssh" else None
        if host!=CANONICAL_GIT_PROVIDER_HOST or scheme not in {"https","ssh"} or parsed.query or parsed.fragment or (parsed.port is not None and parsed.port!=canonical_port) or (scheme=="ssh" and parsed.username!="git") or (scheme=="https" and (parsed.username is not None or parsed.password is not None)):
            raise ReversibleChangeError("checkpoint:REMOTE_PROVIDER_HOST_NOT_BOUND")
        p=parsed.path
    else:
        raise ReversibleChangeError("checkpoint:REMOTE_PROVIDER_HOST_NOT_BOUND")
    parts=[x for x in p.replace("\\","/").strip("/").split("/") if x]
    if parts and parts[-1].lower().endswith(".git"): parts[-1]=parts[-1][:-4]
    if len(parts)!=2: raise ReversibleChangeError("checkpoint:REMOTE_REPOSITORY_UNRESOLVED")
    repo="/".join(parts)
    if not REPO.fullmatch(repo): raise ReversibleChangeError("checkpoint:REMOTE_REPOSITORY_UNRESOLVED")
    return repo
def _require_checkpoint_https_transport(url:str)->None:
    u=_str(url,"remote_url")
    if urlparse(u).scheme.lower()!="https":
        raise ReversibleChangeError("checkpoint:CANONICAL_REMOTE_HTTPS_REQUIRED")
def _remote_rewrite_rules(root:Path)->list[tuple[str,str]]:
    raw=_git_optional(root,"config","--local","--get-regexp",r"^url\.")
    if not raw: return []
    out=[]
    for line in raw.splitlines():
        parts=line.split(None,1)
        if len(parts)!=2: raise ReversibleChangeError("checkpoint:URL_REWRITE_CONFIG_MALFORMED")
        key,value=parts; low=key.lower()
        if low.endswith(".insteadof"): kind="insteadOf"
        elif low.endswith(".pushinsteadof"): kind="pushInsteadOf"
        else: continue
        out.append((kind,_str(value,"url_rewrite_prefix")))
    return out
def _reject_effective_remote_rewrite(root:Path,url:str)->None:
    target=_str(url,"remote_url")
    for kind,prefix in _remote_rewrite_rules(root):
        if target.startswith(prefix): raise ReversibleChangeError(f"checkpoint:EFFECTIVE_REMOTE_URL_REWRITE_FORBIDDEN:{kind}")
def _reject_unsafe_https_transport_config(root:Path)->None:
    raw=_git_optional(root,"config","--local","--get-regexp",r"^(http\.|include\.|includeif\.|remote\..*\.proxy$)")
    if not raw: return
    for line in raw.splitlines():
        parts=line.split(None,1)
        if len(parts)!=2: raise ReversibleChangeError("checkpoint:HTTPS_TRANSPORT_CONFIG_MALFORMED")
        key,value=parts; low=key.lower(); header=value.strip()
        if low.startswith("http.https://github.com/") and low.endswith(".extraheader") and re.fullmatch(r"(?i)authorization:[^\r\n]+",header):
            continue
        raise ReversibleChangeError(f"checkpoint:HTTPS_TRANSPORT_CONFIG_FORBIDDEN:{key}")
def _remote_tip(root:Path,remote:str,branch:str)->dict[str,str]:
    r=_str(remote,"remote_name"); b=_str(branch,"canonical_branch")
    url=_git(root,"config","--local","--get",f"remote.{r}.url"); _require_checkpoint_https_transport(url); _reject_effective_remote_rewrite(root,url); _reject_unsafe_https_transport_config(root); repo=_remote_repo(url)
    out=_git(root,"ls-remote","--exit-code",url,f"refs/heads/{b}")
    rows=[x.split() for x in out.splitlines() if x.strip()]
    if len(rows)!=1: raise ReversibleChangeError("checkpoint:CANONICAL_REMOTE_REF_UNRESOLVED")
    return {"repository":repo,"remote_name":r,"canonical_branch":b,"canonical_remote_ref":f"refs/heads/{b}","canonical_main_sha":_sha40(rows[0][0],"canonical_main_sha")}
def _refs(xs:Sequence[str],n:str)->list[str]:
    if isinstance(xs,(str,bytes)): raise ReversibleChangeError(f"{n}:SEQUENCE_REQUIRED")
    out=[]
    for x in xs:
        y=_str(x,n)
        if y not in out: out.append(y)
    return out
def _status(v:Mapping[str,Any],n:str,allowed:set[str])->dict[str,Any]:
    d=dict(_mapping(v,n))
    if set(d)!={"state","evidence_refs","reason"}: raise ReversibleChangeError(f"{n}:FIELDS_INVALID")
    s=_enum(d["state"],f"{n}.state",EVIDENCE_STATES)
    if s not in allowed: raise ReversibleChangeError(f"{n}:STATE_NOT_KNOWN_GOOD:{s}")
    refs=_refs(d["evidence_refs"],f"{n}.evidence_ref")
    if s=="PASS" and not refs: raise ReversibleChangeError(f"{n}:PASS_EVIDENCE_REQUIRED")
    return {"state":s,"evidence_refs":refs,"reason":_str(d["reason"],f"{n}.reason")}
def _policy_versions(root:Path,commit:str,paths:Sequence[str])->dict[str,str]:
    ps=_refs(paths,"policy_schema_path")
    if not ps: raise ReversibleChangeError("checkpoint:POLICY_SCHEMA_PATH_REQUIRED")
    out={}
    for p in ps:
        if p.startswith("/") or p==".." or p.startswith("../") or "/../" in p: raise ReversibleChangeError("checkpoint:POLICY_SCHEMA_PATH_INVALID")
        x=_git_optional(root,"rev-parse","--verify",f"{commit}:{p}")
        if x is None: raise ReversibleChangeError(f"checkpoint:POLICY_SCHEMA_PATH_MISSING:{p}")
        out[p]=_sha40(x,f"policy_schema_versions[{p}]")
    return out

def capture_known_good_checkpoint(repo_root:str|Path,*,expected_head:str,trigger_source:str,reason:str,policy_schema_paths:Sequence[str],ci_status:Mapping[str,Any],deterministic_verification_status:Mapping[str,Any],independent_review_status:Mapping[str,Any],remote_name:str="origin",canonical_branch:str="main",previous_checkpoint_digest:str|None=None,evidence_refs:Sequence[str]=(),repository:str|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve(); expected=_sha40(expected_head,"expected_head")
    ident=_remote_tip(root,remote_name,canonical_branch)
    if repository is not None and _str(repository,"repository")!=ident["repository"]: raise ReversibleChangeError("checkpoint:REPOSITORY_LABEL_SUBSTITUTION")
    if ident["canonical_main_sha"]!=expected: raise ReversibleChangeError("checkpoint:CANONICAL_MAIN_DRIFT")
    if _git(root,"rev-parse","HEAD")!=expected: raise ReversibleChangeError("checkpoint:HEAD_DRIFT")
    if _git(root,"status","--porcelain","--untracked-files=all"): raise ReversibleChangeError("checkpoint:WORKTREE_DIRTY")
    tree=_sha40(_git(root,"rev-parse",f"{expected}^{{tree}}"),"tree_sha")
    prev=None if previous_checkpoint_digest is None else _sha256(previous_checkpoint_digest,"previous_checkpoint_digest")
    out={"schema_version":CHECKPOINT_SCHEMA,"repository":ident["repository"],"source_ref":f"{ident['remote_name']}/{ident['canonical_branch']}","canonical_main_sha":expected,"tree_sha":tree,"recovery_anchor_commit":expected,"trigger_source":_enum(trigger_source,"trigger_source",TRIGGER_SOURCES),"reason":_str(reason,"reason"),"qualification_level":"DESIGNATED_RECOVERY_ANCHOR","git_binding_verified":True,"trust_semantics":CHECKPOINT_TRUST,"policy_schema_versions":_policy_versions(root,expected,policy_schema_paths),"ci_status":_status(ci_status,"ci_status",{"PASS","NOT_APPLICABLE"}),"deterministic_verification_status":_status(deterministic_verification_status,"deterministic_verification_status",{"PASS"}),"independent_review_status":_status(independent_review_status,"independent_review_status",{"PASS","NOT_APPLICABLE"}),"recorded_at":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),"provenance":{"capture_tool":"R159/reversible_change.py","capture_mode":"CANONICAL_MAIN_COMMIT_ANCHOR","remote_name":ident["remote_name"],"canonical_branch":ident["canonical_branch"],"canonical_remote_ref":ident["canonical_remote_ref"]},"previous_checkpoint_digest":prev,"evidence_refs":_refs(evidence_refs,"evidence_ref"),"evidence_semantics":EVIDENCE_SEMANTICS,"authority":dict(AUTHORITY)}
    d=_digest(out); out["checkpoint_id"]=f"KGC-{d[:16]}"; out["checkpoint_digest"]=d; return out

CHECKPOINT_FIELDS={"schema_version","repository","source_ref","canonical_main_sha","tree_sha","recovery_anchor_commit","trigger_source","reason","qualification_level","git_binding_verified","trust_semantics","policy_schema_versions","ci_status","deterministic_verification_status","independent_review_status","recorded_at","provenance","previous_checkpoint_digest","evidence_refs","evidence_semantics","authority","checkpoint_id","checkpoint_digest"}
def _shape(value:Mapping[str,Any])->dict[str,Any]:
    c=dict(_mapping(value,"checkpoint"))
    if set(c)!=CHECKPOINT_FIELDS:
        miss=sorted(CHECKPOINT_FIELDS-set(c)); extra=sorted(set(c)-CHECKPOINT_FIELDS)
        raise ReversibleChangeError(f"checkpoint:FIELD_{'MISSING' if miss else 'UNRECOGNIZED'}:{(miss or extra)[0]}")
    if c["schema_version"]!=CHECKPOINT_SCHEMA: raise ReversibleChangeError("checkpoint:SCHEMA_MISMATCH")
    if not REPO.fullmatch(_str(c["repository"],"repository")): raise ReversibleChangeError("checkpoint:REPOSITORY_FORMAT_INVALID")
    for k in ("canonical_main_sha","tree_sha","recovery_anchor_commit"): _sha40(c[k],k)
    _enum(c["trigger_source"],"trigger_source",TRIGGER_SOURCES); _str(c["source_ref"],"source_ref"); _str(c["reason"],"reason")
    if c["recovery_anchor_commit"]!=c["canonical_main_sha"]: raise ReversibleChangeError("checkpoint:RECOVERY_ANCHOR_NOT_CANONICAL_MAIN")
    if c["qualification_level"]!="DESIGNATED_RECOVERY_ANCHOR" or c["git_binding_verified"] is not True or c["trust_semantics"]!=CHECKPOINT_TRUST or c["evidence_semantics"]!=EVIDENCE_SEMANTICS or c["authority"]!=AUTHORITY: raise ReversibleChangeError("checkpoint:CONTRACT_INVARIANT_MISMATCH")
    pv=dict(_mapping(c["policy_schema_versions"],"policy_schema_versions"))
    if not pv: raise ReversibleChangeError("checkpoint:POLICY_SCHEMA_VERSION_REQUIRED")
    for p,b in pv.items(): _str(p,"policy_schema_path"); _sha40(b,f"policy_schema_versions[{p}]")
    _status(c["ci_status"],"ci_status",{"PASS","NOT_APPLICABLE"}); _status(c["deterministic_verification_status"],"deterministic_verification_status",{"PASS"}); _status(c["independent_review_status"],"independent_review_status",{"PASS","NOT_APPLICABLE"})
    if not _str(c["recorded_at"],"recorded_at").endswith("Z"): raise ReversibleChangeError("checkpoint:RECORDED_AT_UTC_REQUIRED")
    pr=dict(_mapping(c["provenance"],"provenance"))
    if set(pr)!={"capture_tool","capture_mode","remote_name","canonical_branch","canonical_remote_ref"} or pr["capture_tool"]!="R159/reversible_change.py" or pr["capture_mode"]!="CANONICAL_MAIN_COMMIT_ANCHOR": raise ReversibleChangeError("checkpoint:PROVENANCE_FIELDS_INVALID")
    if c["previous_checkpoint_digest"] is not None: _sha256(c["previous_checkpoint_digest"],"previous_checkpoint_digest")
    _refs(c["evidence_refs"],"evidence_ref")
    d=_sha256(c["checkpoint_digest"],"checkpoint_digest"); body=dict(c); cid=body.pop("checkpoint_id"); body.pop("checkpoint_digest")
    if _digest(body)!=d or cid!=f"KGC-{d[:16]}": raise ReversibleChangeError("checkpoint:DIGEST_OR_ID_MISMATCH")
    return c

def _publication_binding(root:Path,c:Mapping[str,Any],implementation_head:str)->str:
    base=c["recovery_anchor_commit"]; impl=_sha40(implementation_head,"implementation_head")
    if _git_optional(root,"cat-file","-t",impl)!="commit": raise ReversibleChangeError("checkpoint:IMPLEMENTATION_HEAD_MISSING")
    if impl==base or not _ancestor(root,base,impl): raise ReversibleChangeError("checkpoint:RECOVERY_ANCHOR_NOT_ANCESTOR_OF_IMPLEMENTATION")
    chain=_git(root,"rev-list","--first-parent","--reverse",impl).splitlines()
    try: idx=chain.index(base)
    except ValueError as exc: raise ReversibleChangeError("checkpoint:RECOVERY_ANCHOR_NOT_FIRST_PARENT_ANCESTOR") from exc
    if idx+1>=len(chain): raise ReversibleChangeError("checkpoint:IMPLEMENTATION_HEAD_NOT_STRICT_DESCENDANT")
    binding=chain[idx+1]
    parents=_git(root,"rev-list","--parents","-n","1",binding).split()
    if len(parents)<2 or parents[1]!=base: raise ReversibleChangeError("checkpoint:PUBLICATION_BINDING_PARENT_MISMATCH")
    needle=f"{PUBLICATION_TRAILER} {c['checkpoint_digest']}"
    if needle not in {line.strip() for line in _git(root,"show","-s","--format=%B",binding).splitlines()}:
        raise ReversibleChangeError("checkpoint:PUBLICATION_BINDING_MISSING")
    return binding

def checkpoint_publication_state(value:Mapping[str,Any],*,repo_root:str|Path,implementation_head:str|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve(); c=_shape(value); pr=c["provenance"]
    ident=_remote_tip(root,pr["remote_name"],pr["canonical_branch"])
    if ident["repository"]!=c["repository"]: raise ReversibleChangeError("checkpoint:REPOSITORY_IDENTITY_MISMATCH")
    if ident["canonical_remote_ref"]!=pr["canonical_remote_ref"]: raise ReversibleChangeError("checkpoint:CANONICAL_REMOTE_REF_MISMATCH")
    base=c["canonical_main_sha"]; tree=c["tree_sha"]
    if _git_optional(root,"cat-file","-t",base)!="commit": raise ReversibleChangeError("checkpoint:COMMIT_MISSING")
    if _git(root,"rev-parse",f"{base}^{{tree}}")!=tree: raise ReversibleChangeError("checkpoint:TREE_BINDING_MISMATCH")
    current=ident["canonical_main_sha"]
    if _git_optional(root,"cat-file","-t",current)!="commit": raise ReversibleChangeError("checkpoint:CURRENT_CANONICAL_MAIN_MISSING")
    if not _ancestor(root,base,current): raise ReversibleChangeError("checkpoint:CANONICAL_MAIN_ANCESTRY_MISMATCH")
    if _policy_versions(root,base,list(c["policy_schema_versions"]))!=c["policy_schema_versions"]: raise ReversibleChangeError("checkpoint:POLICY_SCHEMA_BINDING_MISMATCH")
    if implementation_head is None:
        if _git(root,"rev-parse","HEAD")!=base: raise ReversibleChangeError("checkpoint:PRECHANGE_HEAD_DRIFT")
        if current!=base: raise ReversibleChangeError("checkpoint:PRECHANGE_CANONICAL_MAIN_DRIFT")
        return {"state":"CAPTURED_DURABLE_CANONICAL_ANCHOR","recovery_anchor_commit":base,"implementation_head":None,"publication_binding_commit":None,"authority":dict(AUTHORITY)}
    impl=_sha40(implementation_head,"implementation_head"); binding=_publication_binding(root,c,impl)
    return {"state":"PUBLISHED_IMPLEMENTATION_LINEAGE","recovery_anchor_commit":base,"implementation_head":impl,"publication_binding_commit":binding,"authority":dict(AUTHORITY)}

def validate_known_good_checkpoint(value:Mapping[str,Any],*,repo_root:str|Path,implementation_head:str|None=None)->dict[str,Any]:
    c=_shape(value); checkpoint_publication_state(c,repo_root=repo_root,implementation_head=implementation_head); return c
def checkpoint_evidence(v:Mapping[str,Any])->dict[str,Any]: return json.loads(_json(_mapping(v,"checkpoint")))
def trigger_from_user_text(text:str)->str:
    if not isinstance(text,str): raise ReversibleChangeError("user_text:STRING_REQUIRED")
    return "USER_EXPLICIT_ROLLBACK_MARKER" if ROLLBACK_TRIGGER_PHRASE in text else "NONE"
def _classify(n:Mapping[str,Any])->tuple[str,list[str]]:
    if n["external_irreversible_side_effect"]: return "IRREVERSIBLE_OR_HIGH_RISK",["EXTERNAL_IRREVERSIBLE_SIDE_EFFECT"]
    if n["surface_kind"]=="EXTERNAL_SIDE_EFFECT": return ("COMPENSATABLE_ONLY",["EXTERNAL_SIDE_EFFECT_REQUIRES_COMPENSATION"]) if n["rollback_mechanism"]=="COMPENSATION" else ("IRREVERSIBLE_OR_HIGH_RISK",["EXTERNAL_SIDE_EFFECT_WITHOUT_COMPENSATION"])
    if n["persistent_state_mutation"] or n["surface_kind"] in {"STATEFUL_DATA","MIXED"}:
        if n["rollback_mechanism"]=="SNAPSHOT": return "REVERSIBLE_WITH_SNAPSHOT",["STATEFUL_CHANGE_BOUND_TO_SNAPSHOT"]
        if n["rollback_mechanism"]=="MIGRATION": return "REVERSIBLE_WITH_MIGRATION",["STATEFUL_CHANGE_BOUND_TO_MIGRATION"]
        return "IRREVERSIBLE_OR_HIGH_RISK",["STATEFUL_CHANGE_CANNOT_USE_GIT_ONLY_RECOVERY"]
    if n["rollback_mechanism"]=="FEATURE_FLAG_OR_VERSION_SWITCH": return "REVERSIBLE_BY_VERSION_SWITCH",["VERSION_SWITCH_AVAILABLE"]
    if n["rollback_mechanism"] in {"NONE","GIT_REVERT"}: return "REVERSIBLE_GIT_ONLY",["CODE_CONFIG_RECOVERABLE_BY_GIT_HISTORY"]
    return "IRREVERSIBLE_OR_HIGH_RISK",["ROLLBACK_MECHANISM_SURFACE_MISMATCH"]
def _intent(v:Mapping[str,Any])->dict[str,Any]:
    x=dict(_mapping(v,"intent"))
    if set(x)!=INTENT_FIELDS:
        miss=sorted(INTENT_FIELDS-set(x)); extra=sorted(set(x)-INTENT_FIELDS); raise ReversibleChangeError(f"intent:FIELD_{'MISSING' if miss else 'UNRECOGNIZED'}:{(miss or extra)[0]}")
    ref=x["rollback_checkpoint_ref"]
    return {"change_id":_str(x["change_id"],"change_id"),"surface_kind":_enum(x["surface_kind"],"surface_kind",SURFACE_KINDS),"blast_radius":_enum(x["blast_radius"],"blast_radius",BLAST_RADII),"explicit_rollback_marker_requested":_bool(x["explicit_rollback_marker_requested"],"explicit_rollback_marker_requested"),"gpt_judged_large_change":_bool(x["gpt_judged_large_change"],"gpt_judged_large_change"),"persistent_state_mutation":_bool(x["persistent_state_mutation"],"persistent_state_mutation"),"external_irreversible_side_effect":_bool(x["external_irreversible_side_effect"],"external_irreversible_side_effect"),"rollback_mechanism":_enum(x["rollback_mechanism"],"rollback_mechanism",ROLLBACK_MECHANISMS),"rollback_checkpoint_ref":None if ref in (None,"") else _sha256(ref,"rollback_checkpoint_ref")}
def _assessment(n:Mapping[str,Any],verified:bool)->dict[str,Any]:
    cls,reasons=_classify(n); marker=bool(n["explicit_rollback_marker_requested"] or n["gpt_judged_large_change"] or n["blast_radius"] in {"LARGE","CRITICAL"} or n["persistent_state_mutation"] or n["surface_kind"] in {"STATEFUL_DATA","MIXED","EXTERNAL_SIDE_EFFECT"})
    mr=[]
    if n["explicit_rollback_marker_requested"]: mr.append("USER_EXPLICIT_ROLLBACK_MARKER")
    if n["gpt_judged_large_change"]: mr.append("GPT_LARGE_CHANGE_JUDGMENT")
    if n["blast_radius"] in {"LARGE","CRITICAL"}: mr.append("BLAST_RADIUS_"+n["blast_radius"])
    if n["persistent_state_mutation"] or n["surface_kind"] in {"STATEFUL_DATA","MIXED","EXTERNAL_SIDE_EFFECT"}: mr.append("STATEFUL_OR_MIXED_CHANGE")
    result="USER_APPROVAL_REQUIRED" if cls=="IRREVERSIBLE_OR_HIGH_RISK" and n["external_irreversible_side_effect"] else "BLOCKED_ROLLBACK_PLAN_INCOMPLETE" if cls=="IRREVERSIBLE_OR_HIGH_RISK" else "REQUIRES_ROLLBACK_MARKER" if marker and not verified else "PASS"
    out={"schema_version":ASSESSMENT_SCHEMA,"change_id":n["change_id"],"normalized_input":dict(n),"reversibility_class":cls,"assessment_result":result,"rollback_marker_required":marker,"rollback_marker_reasons":mr,"rollback_checkpoint_binding_verified":verified,"classification_reasons":reasons,"authority":dict(AUTHORITY)}; out["assessment_digest"]=_digest(out); return out
def assess_change_intent(intent_value:Mapping[str,Any],checkpoint_value:Mapping[str,Any]|None=None,*,repo_root:str|Path|None=None,implementation_head:str|None=None)->dict[str,Any]:
    n=_intent(intent_value); verified=False
    if checkpoint_value is not None:
        if repo_root is None: raise ReversibleChangeError("assessment:CHECKPOINT_REPO_ROOT_REQUIRED")
        c=validate_known_good_checkpoint(checkpoint_value,repo_root=repo_root,implementation_head=implementation_head); d=c["checkpoint_digest"]
        if n["rollback_checkpoint_ref"] not in {None,d}: raise ReversibleChangeError("assessment:CHECKPOINT_BINDING_MISMATCH")
        n["rollback_checkpoint_ref"]=d; verified=True
    return _assessment(n,verified)
def validate_assessment(v:Mapping[str,Any],*,checkpoint_value:Mapping[str,Any]|None=None,repo_root:str|Path|None=None,implementation_head:str|None=None)->dict[str,Any]:
    a=dict(_mapping(v,"assessment"))
    if a.get("schema_version")!=ASSESSMENT_SCHEMA: raise ReversibleChangeError("assessment:SCHEMA_MISMATCH")
    d=_sha256(a.get("assessment_digest"),"assessment_digest"); body=dict(a); body.pop("assessment_digest")
    if _digest(body)!=d: raise ReversibleChangeError("assessment:DIGEST_MISMATCH")
    expected=assess_change_intent(_intent(_mapping(a.get("normalized_input"),"normalized_input")),checkpoint_value,repo_root=repo_root,implementation_head=implementation_head)
    if a!=expected: raise ReversibleChangeError("assessment:SEMANTIC_REDERIVATION_MISMATCH")
    return a
def _plan(c:Mapping[str,Any],a:Mapping[str,Any],reason:str,impl:str,binding:str)->dict[str,Any]:
    if a["assessment_result"]!="PASS": raise ReversibleChangeError("revert_plan:ASSESSMENT_NOT_PASS")
    if a["normalized_input"]["rollback_checkpoint_ref"]!=c["checkpoint_digest"]: raise ReversibleChangeError("revert_plan:CHECKPOINT_BINDING_MISMATCH")
    cls=a["reversibility_class"]
    if cls not in STRATEGY: raise ReversibleChangeError("revert_plan:IRREVERSIBLE_CHANGE")
    blast=a["normalized_input"]["blast_radius"]
    out={"schema_version":REVERT_PLAN_SCHEMA,"checkpoint_id":c["checkpoint_id"],"checkpoint_digest":c["checkpoint_digest"],"checkpoint_recovery_anchor_commit":c["recovery_anchor_commit"],"checkpoint_publication_binding_commit":_sha40(binding,"publication_binding_commit"),"target_commit":c["canonical_main_sha"],"target_tree":c["tree_sha"],"implementation_head":_sha40(impl,"implementation_head"),"change_id":a["change_id"],"assessment_digest":a["assessment_digest"],"reversibility_class":cls,"strategy":STRATEGY[cls],"reason":_str(reason,"reason"),"preserve_history":True,"destructive_history_rewrite":False,"exact_head_reverification_required":True,"independent_review_required":blast in {"MEDIUM","LARGE","CRITICAL"},"user_approval_required":cls=="COMPENSATABLE_ONLY" or blast=="CRITICAL","authority":dict(AUTHORITY)}; out["plan_digest"]=_digest(out); return out
def build_governed_revert_plan(checkpoint_value:Mapping[str,Any],assessment_value:Mapping[str,Any],*,reason:str,repo_root:str|Path,implementation_head:str)->dict[str,Any]:
    root=Path(repo_root).resolve(); c=validate_known_good_checkpoint(checkpoint_value,repo_root=root,implementation_head=implementation_head); a=validate_assessment(assessment_value,checkpoint_value=checkpoint_value,repo_root=root,implementation_head=implementation_head); binding=_publication_binding(root,c,implementation_head); return _plan(c,a,reason,implementation_head,binding)
def validate_governed_revert_plan(v:Mapping[str,Any],*,checkpoint_value:Mapping[str,Any],assessment_value:Mapping[str,Any],repo_root:str|Path,implementation_head:str)->dict[str,Any]:
    p=dict(_mapping(v,"revert_plan")); d=_sha256(p.get("plan_digest"),"plan_digest"); body=dict(p); body.pop("plan_digest")
    if p.get("schema_version")!=REVERT_PLAN_SCHEMA or _digest(body)!=d: raise ReversibleChangeError("revert_plan:DIGEST_OR_SCHEMA_MISMATCH")
    if p.get("preserve_history") is not True: raise ReversibleChangeError("revert_plan:HISTORY_PRESERVATION_REQUIRED")
    if p.get("destructive_history_rewrite") is not False: raise ReversibleChangeError("revert_plan:DESTRUCTIVE_HISTORY_REWRITE_FORBIDDEN")
    if p.get("exact_head_reverification_required") is not True: raise ReversibleChangeError("revert_plan:EXACT_HEAD_REVERIFICATION_REQUIRED")
    if p.get("authority")!=AUTHORITY: raise ReversibleChangeError("revert_plan:AUTHORITY_BOUNDARY_MISMATCH")
    root=Path(repo_root).resolve(); c=validate_known_good_checkpoint(checkpoint_value,repo_root=root,implementation_head=implementation_head); a=validate_assessment(assessment_value,checkpoint_value=checkpoint_value,repo_root=root,implementation_head=implementation_head); binding=_publication_binding(root,c,implementation_head); expected=_plan(c,a,_str(p.get("reason"),"reason"),implementation_head,binding)
    if p!=expected: raise ReversibleChangeError("revert_plan:SEMANTIC_REDERIVATION_MISMATCH")
    return p

def _load(p:str)->Mapping[str,Any]: return _mapping(json.loads(Path(p).read_text(encoding="utf-8")),p)
def _dump(v:Mapping[str,Any])->None: print(json.dumps(dict(v),ensure_ascii=False,sort_keys=True,indent=2))
def _cli()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("assess"); a.add_argument("--input",required=True); a.add_argument("--checkpoint"); a.add_argument("--repo-root"); a.add_argument("--implementation-head")
    c=sub.add_parser("checkpoint"); c.add_argument("--repo-root",required=True); c.add_argument("--expected-head",required=True); c.add_argument("--repository"); c.add_argument("--trigger-source",required=True,choices=sorted(TRIGGER_SOURCES)); c.add_argument("--reason",required=True); c.add_argument("--remote-name",default="origin"); c.add_argument("--canonical-branch",default="main"); c.add_argument("--policy-schema-path",action="append",required=True); c.add_argument("--ci-evidence-ref",action="append",required=True); c.add_argument("--deterministic-evidence-ref",action="append",required=True); c.add_argument("--independent-review-state",choices=["PASS","NOT_APPLICABLE"],default="NOT_APPLICABLE"); c.add_argument("--independent-review-evidence-ref",action="append",default=[]); c.add_argument("--evidence-ref",action="append",default=[])
    p=sub.add_parser("plan"); p.add_argument("--checkpoint",required=True); p.add_argument("--assessment",required=True); p.add_argument("--reason",required=True); p.add_argument("--repo-root",required=True); p.add_argument("--implementation-head",required=True)
    x=ap.parse_args()
    if x.cmd=="assess": _dump(assess_change_intent(_load(x.input),_load(x.checkpoint) if x.checkpoint else None,repo_root=x.repo_root,implementation_head=x.implementation_head))
    elif x.cmd=="checkpoint": _dump(capture_known_good_checkpoint(x.repo_root,expected_head=x.expected_head,repository=x.repository,trigger_source=x.trigger_source,reason=x.reason,remote_name=x.remote_name,canonical_branch=x.canonical_branch,policy_schema_paths=x.policy_schema_path,ci_status={"state":"PASS","evidence_refs":x.ci_evidence_ref,"reason":"bound CI evidence"},deterministic_verification_status={"state":"PASS","evidence_refs":x.deterministic_evidence_ref,"reason":"bound deterministic verification evidence"},independent_review_status={"state":x.independent_review_state,"evidence_refs":x.independent_review_evidence_ref,"reason":"bound independent review status"},evidence_refs=x.evidence_ref))
    else: _dump(build_governed_revert_plan(_load(x.checkpoint),_load(x.assessment),reason=x.reason,repo_root=x.repo_root,implementation_head=x.implementation_head))
    return 0
if __name__=="__main__": raise SystemExit(_cli())

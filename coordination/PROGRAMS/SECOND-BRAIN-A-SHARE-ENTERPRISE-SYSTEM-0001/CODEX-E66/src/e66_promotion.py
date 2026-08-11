"""E66 public-safe control-plane model; no network credentials or real writes."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json, os, re, subprocess
from pathlib import Path

SHA=re.compile(r"^[0-9a-f]{64}$"); COMMIT=re.compile(r"^[0-9a-f]{40}$")
class Reject(ValueError): pass
class Replay(Reject): pass
class UnknownOutcome(Reject): pass
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
def need_sha(v):
    if not SHA.fullmatch(v): raise Reject("expected sha256")
def need_commit(v):
    if not COMMIT.fullmatch(v): raise Reject("expected git commit")

@dataclass(frozen=True)
class DigestBundle:
    raw_artifact_sha256:str; canonical_semantic_sha256:str; l0_provenance_sha256:str
    def __post_init__(self):
        for v in self.__dict__.values(): need_sha(v)
    def payload(self): return self.__dict__

@dataclass(frozen=True)
class PreAdmissionSubject:
    package_id:str; repository_id:str; repository_slug:str; task_id:str; route_epoch:int
    digests:DigestBundle; provenance_status:str; target_scope:str; admission_class:str; expected_parent:str
    def __post_init__(self):
        if not all((self.package_id,self.repository_id,self.repository_slug,self.task_id,self.provenance_status)): raise Reject("missing subject field")
        if self.target_scope not in {"PROJECT","GLOBAL"} or self.admission_class not in {"PUBLIC_SAFE","PRIVATE_OR_SENSITIVE","SECRET_CREDENTIAL"}: raise Reject("invalid scope/class")
        need_commit(self.expected_parent)
    def payload(self): return {"package_id":self.package_id,"repository_id":self.repository_id,"repository_slug":self.repository_slug,"task_id":self.task_id,"route_epoch":self.route_epoch,"digests":self.digests.payload(),"provenance_status":self.provenance_status,"target_scope":self.target_scope,"admission_class":self.admission_class,"expected_parent":self.expected_parent}
    @property
    def sha256(self): return sha256(canon(self.payload())).hexdigest()

@dataclass(frozen=True)
class AdmissionEvidence:
    ref:str; repository_id:str; subject_sha256:str; decision:str
    def __post_init__(self):
        if not self.ref or self.decision not in {"PUBLIC_SAFE","PRIVATE_OR_SENSITIVE","SECRET_CREDENTIAL"}: raise Reject("invalid admission evidence")
        need_sha(self.subject_sha256)
    def payload(self): return self.__dict__
    @property
    def object_sha256(self): return sha256(canon(self.payload())).hexdigest()

@dataclass(frozen=True)
class CandidateKnowledgePackage:
    subject:PreAdmissionSubject; admission_ref:str; admission_object_sha256:str
    def __post_init__(self):
        if not self.admission_ref: raise Reject("missing admission ref")
        need_sha(self.admission_object_sha256)
        if self.admission_object_sha256 == "0"*64: raise Reject("placeholder evidence hash forbidden")
    @property
    def identity_sha256(self): return sha256(canon({"subject":self.subject.payload(),"admission_ref":self.admission_ref,"admission_object_sha256":self.admission_object_sha256})).hexdigest()

def build_candidate(subject:PreAdmissionSubject,evidence:AdmissionEvidence)->CandidateKnowledgePackage:
    if evidence.repository_id!=subject.repository_id or evidence.subject_sha256!=subject.sha256 or evidence.decision!=subject.admission_class: raise Reject("admission evidence mismatch")
    if subject.admission_class!="PUBLIC_SAFE": raise Reject("non-public package cannot enter public promotion")
    return CandidateKnowledgePackage(subject,evidence.ref,evidence.object_sha256)

REQUIRED={"object_type","object_id","repository_id","repository_slug","actor_id","decision","task_id","route_epoch","candidate_identity_sha256","expected_parent","expires_at","gpt_review_ref"}
def parse_approval_control(text:str)->dict:
    m=re.fullmatch(r"E66_APPROVAL_V1\n(\{[^\n]+\})",text)
    if not m: raise Reject("malformed approval control object")
    try: d=json.loads(m.group(1))
    except json.JSONDecodeError as e: raise Reject("invalid approval json") from e
    if set(d)!=REQUIRED or d["object_type"] not in {"ISSUE_COMMENT","PR_REVIEW"} or d["decision"]!="APPROVE": raise Reject("invalid approval fields")
    if not all(isinstance(d[k],str) and d[k] for k in REQUIRED): raise Reject("partial approval")
    need_sha(d["candidate_identity_sha256"]); need_commit(d["expected_parent"])
    return d
def verify_approval(d,candidate,now:datetime,actor_id:str):
    s=candidate.subject
    if (d["repository_id"],d["repository_slug"],d["task_id"],int(d["route_epoch"]),d["candidate_identity_sha256"],d["expected_parent"],d["actor_id"]) != (s.repository_id,s.repository_slug,s.task_id,s.route_epoch,candidate.identity_sha256,s.expected_parent,actor_id): raise Reject("approval binding mismatch")
    if now.isoformat()>=d["expires_at"]: raise Reject("expired approval")

class LocalGitMarkerStore:
    """Synthetic isolated-Git CAS; marker commits are never formal knowledge writes."""
    def __init__(self,repo:Path): self.repo=repo; self.unknown_once=False
    def _git(self,*a): return subprocess.run(["git",*a],cwd=self.repo,text=True,capture_output=True,check=True).stdout.strip()
    def consume(self,approval_id,candidate_id,expected_parent):
        marker=self.repo/".e66-markers"/(approval_id+".json"); payload=canon({"approval_id":approval_id,"candidate_identity_sha256":candidate_id,"expected_parent":expected_parent})
        if marker.exists():
            if marker.read_bytes()!=payload: raise Replay("marker conflict")
            return {"idempotent":True,"marker_sha256":sha256(payload).hexdigest()}
        if self._git("rev-parse","HEAD")!=expected_parent: raise Reject("main moved before marker CAS")
        marker.parent.mkdir(exist_ok=True); fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL); os.write(fd,payload); os.close(fd)
        self._git("add",str(marker.relative_to(self.repo))); self._git("commit","-m","test: synthetic E66 marker")
        if self.unknown_once: self.unknown_once=False; raise UnknownOutcome("marker written; reconcile idempotently")
        return {"idempotent":False,"marker_sha256":sha256(payload).hexdigest()}

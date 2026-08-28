from __future__ import annotations
import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
import reversible_change as rc

def intent(**kw):
    x={"change_id":"R159-CASE","surface_kind":"CODE_CONFIG_ONLY","blast_radius":"SMALL","explicit_rollback_marker_requested":False,"gpt_judged_large_change":False,"persistent_state_mutation":False,"external_irreversible_side_effect":False,"rollback_mechanism":"GIT_REVERT","rollback_checkpoint_ref":None}; x.update(kw); return x
def ps(ref="e://pass"): return {"state":"PASS","evidence_refs":[ref],"reason":"verified"}
def na(): return {"state":"NOT_APPLICABLE","evidence_refs":[],"reason":"not applicable"}
def redigest(x,key):
    b=dict(x); b.pop(key,None); x[key]=rc._digest(b); return x
def redigest_checkpoint(x):
    b=dict(x); b.pop("marker_commit",None); b.pop("checkpoint_id",None); b.pop("checkpoint_digest",None)
    d=rc._digest(b); x["checkpoint_digest"]=d; x["checkpoint_id"]=f"KGC-{d[:16]}"; return x

class Repo:
    def __enter__(self):
        self.tmp=tempfile.TemporaryDirectory(); base=Path(self.tmp.name); self.root=base/"work"; self.root.mkdir(); self.origin=base/"example"/"repo.git"; self.origin.parent.mkdir()
        subprocess.check_call(["git","init","--bare",str(self.origin)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.check_call(["git","init","-b","main"],cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.check_call(["git","config","user.name","R159 Test"],cwd=self.root); subprocess.check_call(["git","config","user.email","r159@example.invalid"],cwd=self.root)
        (self.root/"tracked.txt").write_text("known-good\n"); subprocess.check_call(["git","add","."],cwd=self.root); subprocess.check_call(["git","commit","-m","known good"],cwd=self.root,stdout=subprocess.DEVNULL)
        self.head=self.git("rev-parse","HEAD"); subprocess.check_call(["git","remote","add","origin",str(self.origin)],cwd=self.root); subprocess.check_call(["git","push","-u","origin","main"],cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return self
    def git(self,*a): return subprocess.check_output(["git",*a],cwd=self.root,text=True).strip()
    def refs(self): return self.git("for-each-ref","--format=%(refname):%(objectname)")
    def checkpoint(self,**kw):
        p=dict(repo_root=self.root,repository="example/repo",expected_head=self.head,trigger_source="MANUAL_OPERATION",reason="anchor",policy_schema_paths=["tracked.txt"],ci_status=ps("ci://pass"),deterministic_verification_status=ps("det://pass"),independent_review_status=na(),evidence_refs=["prov://bootstrap"]); p.update(kw); return rc.capture_known_good_checkpoint(**p)
    def impl(self,c,text="impl"):
        subprocess.check_call(["git","checkout","-B","work",c["marker_commit"]],cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); (self.root/"tracked.txt").write_text(text+"\n"); subprocess.check_call(["git","add","."],cwd=self.root); subprocess.check_call(["git","commit","-m",text],cwd=self.root,stdout=subprocess.DEVNULL); return self.git("rev-parse","HEAD")
    def later_main(self):
        (self.root/"tracked.txt").write_text("later\n"); subprocess.check_call(["git","add","."],cwd=self.root); subprocess.check_call(["git","commit","-m","later"],cwd=self.root,stdout=subprocess.DEVNULL); return self.git("rev-parse","HEAD")
    def __exit__(self,*_): self.tmp.cleanup()

class T(unittest.TestCase):
    def checked(self,r,**kw):
        c=r.checkpoint(); i=intent(rollback_checkpoint_ref=c["checkpoint_digest"],**kw); a=rc.assess_change_intent(i,c,repo_root=r.root); return c,a
    def test_01_small_pass(self): self.assertEqual(rc.assess_change_intent(intent())["assessment_result"],"PASS")
    def test_02_trigger(self): self.assertEqual(rc.trigger_from_user_text("先做个滚回记号"),"USER_EXPLICIT_ROLLBACK_MARKER")
    def test_03_large_needs_marker(self): self.assertEqual(rc.assess_change_intent(intent(blast_radius="LARGE"))["assessment_result"],"REQUIRES_ROLLBACK_MARKER")
    def test_04_gpt_large_needs_marker(self): self.assertEqual(rc.assess_change_intent(intent(gpt_judged_large_change=True))["assessment_result"],"REQUIRES_ROLLBACK_MARKER")
    def test_05_digest_alone_not_marker(self): self.assertFalse(rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref="a"*64))["rollback_checkpoint_binding_verified"])
    def test_06_capture_does_not_move_refs(self):
        with Repo() as r:
            before=r.refs(); c=r.checkpoint(); self.assertEqual(before,r.refs()); self.assertEqual(c["trust_semantics"],rc.CHECKPOINT_TRUST)
    def test_07_serialized_cross_process_valid(self):
        with Repo() as r:
            c=json.loads(json.dumps(r.checkpoint())); self.assertEqual(rc.validate_known_good_checkpoint(c,repo_root=r.root)["checkpoint_id"],c["checkpoint_id"])
    def test_08_deepcopy_valid(self):
        with Repo() as r:
            c=copy.deepcopy(r.checkpoint()); rc.validate_known_good_checkpoint(c,repo_root=r.root)
    def test_09_marker_parent_exact(self):
        with Repo() as r:
            c=r.checkpoint(); self.assertEqual(r.git("rev-list","--parents","-n","1",c["marker_commit"]).split()[1:],[r.head])
    def test_10_marker_tree_exact(self):
        with Repo() as r:
            c=r.checkpoint(); self.assertEqual(r.git("rev-parse",f"{c['marker_commit']}^{{tree}}"),c["tree_sha"])
    def test_11_json_rewrite_rejected(self):
        with Repo() as r:
            c=r.checkpoint(); f=copy.deepcopy(c); f["reason"]="forged"; redigest_checkpoint(f)
            with self.assertRaisesRegex(rc.ReversibleChangeError,"MARKER_PAYLOAD_MISMATCH"): rc.validate_known_good_checkpoint(f,repo_root=r.root)
    def test_12_repo_label_substitution(self):
        with Repo() as r:
            with self.assertRaisesRegex(rc.ReversibleChangeError,"REPOSITORY_LABEL_SUBSTITUTION"): r.checkpoint(repository="evil/repo")
    def test_13_remote_identity_change(self):
        with Repo() as r:
            c=r.checkpoint(); other=Path(r.tmp.name)/"other"/"repo.git"; other.parent.mkdir(); subprocess.check_call(["git","init","--bare",str(other)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); subprocess.check_call(["git","--git-dir",str(other),"fetch",str(r.root),f"{r.head}:refs/heads/main"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); subprocess.check_call(["git","remote","set-url","origin",str(other)],cwd=r.root)
            with self.assertRaisesRegex(rc.ReversibleChangeError,"REPOSITORY_IDENTITY_MISMATCH"): rc.validate_known_good_checkpoint(c,repo_root=r.root)
    def test_14_remote_main_drift_capture(self):
        with Repo() as r:
            later=r.later_main(); subprocess.check_call(["git","push","origin",f"{later}:refs/heads/main"],cwd=r.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); subprocess.check_call(["git","reset","--hard",r.head],cwd=r.root,stdout=subprocess.DEVNULL)
            with self.assertRaisesRegex(rc.ReversibleChangeError,"CANONICAL_MAIN_DRIFT"): r.checkpoint()
    def test_15_dirty_rejected(self):
        with Repo() as r:
            (r.root/"tracked.txt").write_text("dirty")
            with self.assertRaisesRegex(rc.ReversibleChangeError,"WORKTREE_DIRTY"): r.checkpoint()
    def test_16_untracked_rejected(self):
        with Repo() as r:
            (r.root/"new.txt").write_text("dirty")
            with self.assertRaisesRegex(rc.ReversibleChangeError,"WORKTREE_DIRTY"): r.checkpoint()
    def test_17_policy_path_required(self):
        with Repo() as r:
            with self.assertRaisesRegex(rc.ReversibleChangeError,"POLICY_SCHEMA_PATH_REQUIRED"): r.checkpoint(policy_schema_paths=[])
    def test_18_policy_path_missing(self):
        with Repo() as r:
            with self.assertRaisesRegex(rc.ReversibleChangeError,"POLICY_SCHEMA_PATH_MISSING"): r.checkpoint(policy_schema_paths=["none.json"])
    def test_19_ci_fail_rejected(self):
        with Repo() as r:
            with self.assertRaisesRegex(rc.ReversibleChangeError,"STATE_NOT_KNOWN_GOOD"): r.checkpoint(ci_status={"state":"FAIL","evidence_refs":["ci://fail"],"reason":"red"})
    def test_20_det_inconclusive_rejected(self):
        with Repo() as r:
            with self.assertRaisesRegex(rc.ReversibleChangeError,"STATE_NOT_KNOWN_GOOD"): r.checkpoint(deterministic_verification_status={"state":"INCONCLUSIVE","evidence_refs":["d://x"],"reason":"gap"})
    def test_21_pass_requires_ref(self):
        with Repo() as r:
            with self.assertRaisesRegex(rc.ReversibleChangeError,"PASS_EVIDENCE_REQUIRED"): r.checkpoint(ci_status={"state":"PASS","evidence_refs":[],"reason":"claimed"})
    def test_22_large_marker_pass_prechange(self):
        with Repo() as r:
            c=r.checkpoint(); a=rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]),c,repo_root=r.root); self.assertEqual(a["assessment_result"],"PASS")
    def test_23_marker_ancestor_impl(self):
        with Repo() as r:
            c=r.checkpoint(); h=r.impl(c); rc.validate_known_good_checkpoint(c,repo_root=r.root,implementation_head=h)
    def test_24_marker_not_ancestor(self):
        with Repo() as r:
            c=r.checkpoint(); h=r.later_main()
            with self.assertRaisesRegex(rc.ReversibleChangeError,"MARKER_NOT_ANCESTOR"): rc.validate_known_good_checkpoint(c,repo_root=r.root,implementation_head=h)
    def test_25_marker_itself_not_impl(self):
        with Repo() as r:
            c=r.checkpoint()
            with self.assertRaisesRegex(rc.ReversibleChangeError,"MARKER_NOT_ANCESTOR"): rc.validate_known_good_checkpoint(c,repo_root=r.root,implementation_head=c["marker_commit"])
    def test_26_replace_ref_does_not_launder_tree(self):
        with Repo() as r:
            c=r.checkpoint(); h=r.later_main(); subprocess.check_call(["git","replace",c["canonical_main_sha"],h],cwd=r.root); self.assertEqual(rc._git(r.root,"rev-parse",f"{c['canonical_main_sha']}^{{tree}}"),c["tree_sha"])
    def test_27_stateful_git_only_blocked(self): self.assertEqual(rc.assess_change_intent(intent(surface_kind="STATEFUL_DATA",persistent_state_mutation=True,blast_radius="LARGE"))["reversibility_class"],"IRREVERSIBLE_OR_HIGH_RISK")
    def test_28_external_irreversible_user_gate(self): self.assertEqual(rc.assess_change_intent(intent(surface_kind="EXTERNAL_SIDE_EFFECT",external_irreversible_side_effect=True,blast_radius="CRITICAL",rollback_mechanism="NONE"))["assessment_result"],"USER_APPROVAL_REQUIRED")
    def test_29_semantic_launder_rejected(self):
        a=rc.assess_change_intent(intent(surface_kind="STATEFUL_DATA",persistent_state_mutation=True,blast_radius="LARGE")); a["reversibility_class"]="REVERSIBLE_GIT_ONLY"; a["assessment_result"]="PASS"; redigest(a,"assessment_digest")
        with self.assertRaisesRegex(rc.ReversibleChangeError,"SEMANTIC_REDERIVATION"): rc.validate_assessment(a)
    def test_30_marker_bit_launder_rejected(self):
        a=rc.assess_change_intent(intent(blast_radius="LARGE")); a["rollback_checkpoint_binding_verified"]=True; a["assessment_result"]="PASS"; redigest(a,"assessment_digest")
        with self.assertRaisesRegex(rc.ReversibleChangeError,"SEMANTIC_REDERIVATION"): rc.validate_assessment(a)
    def test_31_plan_binds_marker_and_head(self):
        with Repo() as r:
            c=r.checkpoint(); pre=rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]),c,repo_root=r.root); h=r.impl(c); a=rc.assess_change_intent(pre["normalized_input"],c,repo_root=r.root,implementation_head=h); p=rc.build_governed_revert_plan(c,a,reason="rollback",repo_root=r.root,implementation_head=h); self.assertEqual(p["checkpoint_marker_commit"],c["marker_commit"]); self.assertEqual(p["implementation_head"],h); self.assertTrue(p["independent_review_required"])
    def test_32_plan_strategy_launder(self):
        with Repo() as r:
            c=r.checkpoint(); pre=rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]),c,repo_root=r.root); h=r.impl(c); a=rc.assess_change_intent(pre["normalized_input"],c,repo_root=r.root,implementation_head=h); p=rc.build_governed_revert_plan(c,a,reason="r",repo_root=r.root,implementation_head=h); p["strategy"]="VERSION_SWITCH_OR_FEATURE_FLAG"; redigest(p,"plan_digest")
            with self.assertRaisesRegex(rc.ReversibleChangeError,"SEMANTIC_REDERIVATION"): rc.validate_governed_revert_plan(p,checkpoint_value=c,assessment_value=a,repo_root=r.root,implementation_head=h)
    def test_33_review_suppression(self):
        with Repo() as r:
            c=r.checkpoint(); pre=rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]),c,repo_root=r.root); h=r.impl(c); a=rc.assess_change_intent(pre["normalized_input"],c,repo_root=r.root,implementation_head=h); p=rc.build_governed_revert_plan(c,a,reason="r",repo_root=r.root,implementation_head=h); p["independent_review_required"]=False; redigest(p,"plan_digest")
            with self.assertRaisesRegex(rc.ReversibleChangeError,"SEMANTIC_REDERIVATION"): rc.validate_governed_revert_plan(p,checkpoint_value=c,assessment_value=a,repo_root=r.root,implementation_head=h)
    def test_34_history_rewrite_rejected(self):
        with Repo() as r:
            c=r.checkpoint(); pre=rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]),c,repo_root=r.root); h=r.impl(c); a=rc.assess_change_intent(pre["normalized_input"],c,repo_root=r.root,implementation_head=h); p=rc.build_governed_revert_plan(c,a,reason="r",repo_root=r.root,implementation_head=h); p["destructive_history_rewrite"]=True; redigest(p,"plan_digest")
            with self.assertRaisesRegex(rc.ReversibleChangeError,"DESTRUCTIVE_HISTORY_REWRITE_FORBIDDEN"): rc.validate_governed_revert_plan(p,checkpoint_value=c,assessment_value=a,repo_root=r.root,implementation_head=h)
    def test_35_authority_escalation_rejected(self):
        with Repo() as r:
            c=r.checkpoint(); pre=rc.assess_change_intent(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]),c,repo_root=r.root); h=r.impl(c); a=rc.assess_change_intent(pre["normalized_input"],c,repo_root=r.root,implementation_head=h); p=rc.build_governed_revert_plan(c,a,reason="r",repo_root=r.root,implementation_head=h); p["authority"]["grants_merge"]=True; redigest(p,"plan_digest")
            with self.assertRaisesRegex(rc.ReversibleChangeError,"AUTHORITY_BOUNDARY"): rc.validate_governed_revert_plan(p,checkpoint_value=c,assessment_value=a,repo_root=r.root,implementation_head=h)
    def test_36_unknown_intent_field(self):
        x=intent(); x["oops"]=1
        with self.assertRaisesRegex(rc.ReversibleChangeError,"FIELD_UNRECOGNIZED"): rc.assess_change_intent(x)
    def test_37_cli_assess(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"i.json"; p.write_text(json.dumps(intent())); out=subprocess.check_output([sys.executable,str(Path(rc.__file__)),"assess","--input",str(p)],text=True); self.assertEqual(json.loads(out)["assessment_result"],"PASS")
    def test_38_cli_checkpoint_and_reuse(self):
        with Repo() as r, tempfile.TemporaryDirectory() as d:
            out=subprocess.check_output([sys.executable,str(Path(rc.__file__)),"checkpoint","--repo-root",str(r.root),"--repository","example/repo","--expected-head",r.head,"--trigger-source","MANUAL_OPERATION","--reason","anchor","--policy-schema-path","tracked.txt","--ci-evidence-ref","ci://x","--deterministic-evidence-ref","det://x"],text=True); c=json.loads(out); cp=Path(d)/"c.json"; ip=Path(d)/"i.json"; cp.write_text(json.dumps(c)); ip.write_text(json.dumps(intent(blast_radius="LARGE",rollback_checkpoint_ref=c["checkpoint_digest"]))); out2=subprocess.check_output([sys.executable,str(Path(rc.__file__)),"assess","--input",str(ip),"--checkpoint",str(cp),"--repo-root",str(r.root)],text=True); self.assertEqual(json.loads(out2)["assessment_result"],"PASS")
    def test_39_no_mutable_ref_seam(self):
        s=Path(rc.__file__).read_text()
        for token in ("update-ref","refs/tags/","git tag","git notes","symbolic-ref","reset --hard","push --force"): self.assertNotIn(token,s)
    def test_40_marker_protocol_tokens(self):
        s=Path(rc.__file__).read_text(); self.assertIn("commit-tree",s); self.assertIn("--no-replace-objects",s); self.assertIn("GIT_COMMIT_TREE_MARKER",s)
    def test_41_authority_false(self): self.assertTrue(rc.AUTHORITY); self.assertFalse(any(rc.AUTHORITY.values()))

MATRIX=[
("small-none",{},("PASS","REVERSIBLE_GIT_ONLY")),
("medium",{"blast_radius":"MEDIUM"},("PASS","REVERSIBLE_GIT_ONLY")),
("explicit",{"explicit_rollback_marker_requested":True},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_GIT_ONLY")),
("critical",{"blast_radius":"CRITICAL"},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_GIT_ONLY")),
("policy",{"surface_kind":"POLICY_BEHAVIOR","rollback_mechanism":"FEATURE_FLAG_OR_VERSION_SWITCH"},("PASS","REVERSIBLE_BY_VERSION_SWITCH")),
("state-snapshot",{"surface_kind":"STATEFUL_DATA","persistent_state_mutation":True,"rollback_mechanism":"SNAPSHOT"},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_WITH_SNAPSHOT")),
("state-migration",{"surface_kind":"STATEFUL_DATA","persistent_state_mutation":True,"rollback_mechanism":"MIGRATION"},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_WITH_MIGRATION")),
("state-none",{"surface_kind":"STATEFUL_DATA","persistent_state_mutation":True,"rollback_mechanism":"NONE"},("BLOCKED_ROLLBACK_PLAN_INCOMPLETE","IRREVERSIBLE_OR_HIGH_RISK")),
("mixed",{"surface_kind":"MIXED","persistent_state_mutation":True,"rollback_mechanism":"SNAPSHOT"},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_WITH_SNAPSHOT")),
("external-comp",{"surface_kind":"EXTERNAL_SIDE_EFFECT","rollback_mechanism":"COMPENSATION"},("REQUIRES_ROLLBACK_MARKER","COMPENSATABLE_ONLY")),
("external-none",{"surface_kind":"EXTERNAL_SIDE_EFFECT","rollback_mechanism":"NONE"},("BLOCKED_ROLLBACK_PLAN_INCOMPLETE","IRREVERSIBLE_OR_HIGH_RISK")),
("external-irrev",{"surface_kind":"EXTERNAL_SIDE_EFFECT","external_irreversible_side_effect":True},("USER_APPROVAL_REQUIRED","IRREVERSIBLE_OR_HIGH_RISK")),
("gpt-large",{"gpt_judged_large_change":True},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_GIT_ONLY")),
("large",{"blast_radius":"LARGE"},("REQUIRES_ROLLBACK_MARKER","REVERSIBLE_GIT_ONLY")),
("code-flag",{"rollback_mechanism":"FEATURE_FLAG_OR_VERSION_SWITCH"},("PASS","REVERSIBLE_BY_VERSION_SWITCH")),
("code-migration",{"rollback_mechanism":"MIGRATION"},("BLOCKED_ROLLBACK_PLAN_INCOMPLETE","IRREVERSIBLE_OR_HIGH_RISK")),
("code-snapshot",{"rollback_mechanism":"SNAPSHOT"},("BLOCKED_ROLLBACK_PLAN_INCOMPLETE","IRREVERSIBLE_OR_HIGH_RISK")),
]
def _mk(case,kw,expected):
    def test(self):
        x=rc.assess_change_intent(intent(**kw)); self.assertEqual((x["assessment_result"],x["reversibility_class"]),expected,case)
    return test
for i,row in enumerate(MATRIX,42): setattr(T,f"test_{i:02d}_matrix_{row[0].replace('-','_')}",_mk(*row))

if __name__=="__main__": unittest.main()

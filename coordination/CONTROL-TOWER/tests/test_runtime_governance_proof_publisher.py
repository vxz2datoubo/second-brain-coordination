from __future__ import annotations

import copy
import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / ".github/workflows/runtime-governance-proof-publisher.yml"
ROOT_WF = ROOT / ".github/workflows/runtime-governance-root.yml"
RECEIPT = ROOT / "coordination/CONTROL-TOWER/R145-RUNTIME-GOVERNANCE-PROOF-PUBLISHER.yaml"

HEAD, BASE, H2, B2 = "b"*40, "a"*40, "c"*40, "d"*40
REPO = "vxz2datoubo/second-brain-coordination"
PR, WID, RID = 418, 424242, 777001
NAME = "Runtime governance root"
PATH = ".github/workflows/runtime-governance-root.yml"
FILENAME = "runtime-governance-root.yml"
ENDPOINT = f"/repos/{REPO}/actions/workflows/{FILENAME}"
CONTEXT = "r145/runtime-governance-live-proof"
TITLE = f"R145_LIVE_ROOT pr={PR} head={HEAD} base={BASE}"

def extract(text=None):
    raw = PUB.read_text(encoding="utf-8") if text is None else text
    a = raw.index("          python3 - <<'PY'\n") + len("          python3 - <<'PY'\n")
    b = raw.index("\n          PY", a)
    return textwrap.dedent(raw[a:b])

def ns(script=None):
    n = {"__name__": "r145_test"}
    exec(compile(extract() if script is None else script, "<publisher>", "exec"), n)
    return n

def rb(pr=PR, head=HEAD, base=BASE):
    return {"number": pr, "head": {"sha": head}, "base": {"sha": base}}

def fx(conclusion="success", rest=None, title=TITLE):
    if rest is None:
        rest = []
    event = {
        "action": "completed",
        "repository": {"full_name": REPO},
        "workflow": {"id": WID, "name": NAME, "path": PATH},
        "workflow_run": {
            "id": RID, "workflow_id": WID, "name": NAME, "event": "pull_request_target",
            "status": "completed", "conclusion": conclusion, "display_title": title,
        },
        "pull_request": {"title": "attacker pr=999", "body": TITLE, "head": {"ref": TITLE}},
    }
    original = {
        "id": RID, "workflow_id": WID, "name": NAME, "path": PATH+"@main",
        "event": "pull_request_target", "status": "completed", "conclusion": conclusion,
        "display_title": title, "html_url": f"https://github.com/{REPO}/actions/runs/{RID}",
        "repository": {"full_name": REPO}, "pull_requests": copy.deepcopy(rest),
    }
    expected = {"id": WID, "name": NAME, "path": PATH}
    current = {"number": PR, "head": {"sha": HEAD}, "base": {"sha": BASE}}
    return event, original, expected, current

class Semantic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = extract()
        cls.eval = staticmethod(ns(cls.code)["evaluate_live_proof"])

    def test_real_observed_empty_rest_pull_requests_valid_run_name_succeeds(self):
        d = self.eval(*fx(rest=[]))
        self.assertEqual(("success", HEAD, CONTEXT), (d["state"], d["head_sha"], d["context"]))

    def test_matching_nonempty_rest_is_only_cross_check(self):
        self.assertEqual("success", self.eval(*fx(rest=[rb()]))["state"])

    def test_wrong_pr_number_in_run_name_no_success(self):
        self.assertNotEqual("success", self.eval(*fx(title=f"R145_LIVE_ROOT pr=419 head={HEAD} base={BASE}"))["state"])

    def test_malformed_head_sha_in_run_name_no_success(self):
        self.assertNotEqual("success", self.eval(*fx(title=f"R145_LIVE_ROOT pr=418 head=bad base={BASE}"))["state"])

    def test_malformed_base_sha_in_run_name_no_success(self):
        self.assertNotEqual("success", self.eval(*fx(title=f"R145_LIVE_ROOT pr=418 head={HEAD} base=bad"))["state"])

    def test_missing_head_or_base_in_run_name_no_success(self):
        for title in (f"R145_LIVE_ROOT pr=418 base={BASE}", f"R145_LIVE_ROOT pr=418 head={HEAD}"):
            with self.subTest(title=title):
                self.assertNotEqual("success", self.eval(*fx(title=title))["state"])

    def test_current_head_drift_is_stale_error(self):
        e,o,x,c=fx(); c["head"]["sha"]=H2
        d=self.eval(e,o,x,c); self.assertEqual(("error",HEAD),(d["state"],d["head_sha"]))

    def test_current_base_drift_is_stale_error(self):
        e,o,x,c=fx(); c["base"]["sha"]=B2
        d=self.eval(e,o,x,c); self.assertEqual(("error",HEAD),(d["state"],d["head_sha"]))

    def test_nonempty_rest_binding_mismatch_fails_closed(self):
        for bind in (rb(pr=419), rb(head=H2), rb(base=B2)):
            with self.subTest(bind=bind):
                d=self.eval(*fx(rest=[bind])); self.assertFalse(d["publish"])

    def test_multiple_rest_bindings_fail_closed(self):
        self.assertFalse(self.eval(*fx(rest=[rb(),rb()]))["publish"])

    def test_workflow_run_and_original_display_title_mismatch_fails_closed(self):
        e,o,x,c=fx(); e["workflow_run"]["display_title"]=f"R145_LIVE_ROOT pr=418 head={H2} base={BASE}"
        self.assertFalse(self.eval(e,o,x,c)["publish"])

    def test_pr_title_body_free_text_not_binding(self):
        e,o,x,c=fx(); e["pull_request"]={"title":TITLE.replace("418","999"),"body":"free","head":{"ref":"free"}}
        self.assertEqual("success", self.eval(e,o,x,c)["state"])

    def test_workflow_repo_event_id_path_checks_retained(self):
        mutations = [
            lambda e,o,x,c: o.__setitem__("name","bad"),
            lambda e,o,x,c: o.__setitem__("workflow_id",WID+1),
            lambda e,o,x,c: o.__setitem__("event","pull_request"),
            lambda e,o,x,c: o["repository"].__setitem__("full_name","bad/repo"),
            lambda e,o,x,c: o.__setitem__("path",".github/workflows/bad.yml@main"),
        ]
        for mutate in mutations:
            e,o,x,c=fx(); mutate(e,o,x,c)
            with self.subTest(mutate=mutate):
                self.assertNotEqual("success", self.eval(e,o,x,c)["state"])

    def test_failure_and_unknown_never_success(self):
        self.assertEqual("failure", self.eval(*fx("failure"))["state"])
        self.assertEqual("error", self.eval(*fx("mystery"))["state"])

    def test_target_url_binds_original_run(self):
        e,o,x,c=fx(); o["html_url"]="https://attacker.invalid/"
        self.assertNotEqual("success", self.eval(e,o,x,c)["state"])

class MainPath(unittest.TestCase):
    def run_main(self, pack, script=None):
        event, original, expected, current = pack
        n=ns(script); calls=[]
        def req(method,path,body=None):
            calls.append((method,path,copy.deepcopy(body)))
            if method=="GET" and path==ENDPOINT: return copy.deepcopy(expected)
            if method=="GET" and path==f"/repos/{REPO}/actions/runs/{RID}?exclude_pull_requests=false": return copy.deepcopy(original)
            if method=="GET" and path==f"/repos/{REPO}/pulls/{PR}": return copy.deepcopy(current)
            if method=="POST" and path==f"/repos/{REPO}/statuses/{HEAD}": return {"ok":True}
            raise AssertionError((method,path,body))
        n["request_json"]=req
        with tempfile.NamedTemporaryFile("w",encoding="utf-8",delete=False) as f:
            json.dump(event,f); p=f.name
        try:
            with mock.patch.dict(n["os"].environ,{"GITHUB_EVENT_PATH":p,"GITHUB_TOKEN":"x"},clear=False):
                code=None
                try: n["main"]()
                except SystemExit as ex: code=ex.code
            return calls,code
        finally: os.unlink(p)

    def test_main_empty_rest_posts_success_to_run_name_head(self):
        calls,code=self.run_main(fx(rest=[])); self.assertIsNone(code)
        posts=[c for c in calls if c[0]=="POST"]
        self.assertEqual((f"/repos/{REPO}/statuses/{HEAD}","success",CONTEXT),
                         (posts[0][1],posts[0][2]["state"],posts[0][2]["context"]))

    def test_metadata_endpoint_f02_remains_exact(self):
        calls,_=self.run_main(fx())
        self.assertEqual([("GET",ENDPOINT,None)],[c for c in calls if c[0]=="GET" and "/actions/workflows/" in c[1]])

class ProductionMutation(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code=extract()

    def test_f03_production_mutations_are_detected(self):
        cases=[
            ("run_name_fallback",'run_binding = _parse_run_binding(original_title)',
             'run_binding = {"pr": PR_NUMBER, "head": current_pr["head"]["sha"], "base": current_pr["base"]["sha"]}'),
            ("display_crosscheck",'if event_title != original_title:',"if False:"),
            ("rest_crosscheck",'if (\n            rest_binding.get("number") != run_binding["pr"]',
             'if False and (\n            rest_binding.get("number") != run_binding["pr"]'),
        ]
        for name,old,new in cases:
            self.assertIn(old,self.code)
            m=self.code.replace(old,new,1)
            if name=="run_name_fallback":
                e,o,x,c=fx(title="attacker free text")
            elif name=="display_crosscheck":
                e,o,x,c=fx(); e["workflow_run"]["display_title"]=f"R145_LIVE_ROOT pr=418 head={H2} base={BASE}"
            else:
                e,o,x,c=fx(rest=[rb(head=H2)])
            d=ns(m)["evaluate_live_proof"](e,o,x,c)
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.assertNotEqual("success",d["state"])

    def test_f02_full_path_filename_mutations_rejected_by_transport(self):
        for old,new in [
            ('f"/repos/{REPO}/actions/workflows/{ROOT_FILENAME}"','f"/repos/{REPO}/actions/workflows/{ROOT_PATH}"'),
            ('ROOT_FILENAME = "runtime-governance-root.yml"','ROOT_FILENAME = "wrong.yml"'),
        ]:
            self.assertIn(old,self.code)
            with self.subTest(new=new), self.assertRaises(AssertionError):
                MainPath().run_main(fx(),self.code.replace(old,new,1))

    def test_f01_previous_security_mutations_still_detected(self):
        cases=[
            ('if target_url != expected_url:',"if False:","url"),
            ('CONTEXT = "r145/runtime-governance-live-proof"','CONTEXT = "bad/context"',"context"),
            ('if conclusion == "success":','if conclusion in {"success","failure"}:',"failure"),
        ]
        for old,new,kind in cases:
            self.assertIn(old,self.code); m=self.code.replace(old,new,1)
            if kind=="url":
                e,o,x,c=fx(); o["html_url"]="https://bad/"
                d=ns(m)["evaluate_live_proof"](e,o,x,c)
                check=lambda: self.assertNotEqual("success",d["state"])
            elif kind=="context":
                d=ns(m)["evaluate_live_proof"](*fx())
                check=lambda: self.assertEqual(CONTEXT,d["context"])
            else:
                d=ns(m)["evaluate_live_proof"](*fx("failure"))
                check=lambda: self.assertNotEqual("success",d["state"])
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                check()

class Static(unittest.TestCase):
    def test_root_run_name_strict_and_free_text_absent(self):
        t=ROOT_WF.read_text()
        self.assertIn("run-name: R145_LIVE_ROOT pr=${{ github.event.pull_request.number }} head=${{ github.event.pull_request.head.sha }} base=${{ github.event.pull_request.base.sha }}",t)
        for bad in ("pull_request.title","pull_request.body","pull_request.head.ref"): self.assertNotIn(bad,t)

    def test_root_permissions_and_base_trust_unchanged(self):
        t=ROOT_WF.read_text()
        self.assertIn("permissions:\n  contents: read\n",t)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}",t)
        self.assertIn('git fetch --no-tags origin "$HEAD_SHA"',t)
        self.assertNotIn("ref: ${{ github.event.pull_request.head.sha }}",t)

    def test_publisher_permissions_exact_no_head_execution_no_github_sha(self):
        t=PUB.read_text(); d=yaml.safe_load(t)
        self.assertEqual({"actions":"read","pull-requests":"read","statuses":"write"},d["permissions"])
        for bad in ("actions/checkout","secrets.","actions/cache","download-artifact","GITHUB_SHA","github.event.pull_request.head"): self.assertNotIn(bad,t)

    def test_publisher_uses_strict_display_title_binding_and_no_shadow(self):
        s=extract()
        for needle in ("RUN_BINDING_RE = re.compile(","event_title = wr.get(\"display_title\")",
                       "original_title = original.get(\"display_title\")",
                       "run_binding = _parse_run_binding(original_title)",
                       'rest_bindings = original.get("pull_requests")'):
            self.assertIn(needle,s)
        self.assertNotIn("runtime_governance_proof_policy",s)

    def test_receipt_matches_f03_and_stop_gate(self):
        r=yaml.safe_load(RECEIPT.read_text())
        self.assertEqual("STOP_BEFORE_G1_G5",r["runtime_hold"])
        self.assertEqual("CANONICAL_ROOT_RUN_NAME_DISPLAY_TITLE",r["proof_contract"]["head_source"])
        self.assertTrue(r["proof_contract"]["empty_rest_pull_requests_allowed"])
        self.assertEqual("WORKFLOW_RUN_PULL_REQUESTS_NONEMPTY_ASSUMPTION_IS_FALSE",r["f03_remediation"]["blocker"])
        self.assertFalse(r["architecture"]["publisher"]["checkout_repository"])


# Granular named regressions keep each security boundary independently visible in CI logs.
def _add_case(name, fn):
    setattr(Semantic, "test_granular_" + name, fn)

def _identity_case(field, value):
    def test(self):
        e,o,x,c=fx()
        if field=="repo":
            o["repository"]["full_name"]=value
        else:
            o[field]=value
        self.assertNotEqual("success",self.eval(e,o,x,c)["state"])
    return test

for _n,_f,_v in [
    ("wrong_name","name","bad"),("wrong_workflow_id","workflow_id",WID+1),
    ("wrong_event","event","pull_request"),("wrong_repo","repo","bad/repo"),
    ("wrong_path","path",".github/workflows/bad.yml@main"),
]:
    _add_case(_n,_identity_case(_f,_v))

def _rest_case(kind):
    def test(self):
        bind=rb(pr=419) if kind=="pr" else rb(head=H2) if kind=="head" else rb(base=B2)
        self.assertFalse(self.eval(*fx(rest=[bind]))["publish"])
    return test

for _k in ("pr","head","base"):
    _add_case("rest_mismatch_"+_k,_rest_case(_k))

def _conclusion_case(value):
    def test(self):
        self.assertNotEqual("success",self.eval(*fx(value))["state"])
    return test

for _v in ("cancelled","timed_out","skipped"):
    _add_case("conclusion_"+_v,_conclusion_case(_v))

def _missing_case(which):
    def test(self):
        title=f"R145_LIVE_ROOT pr=418 base={BASE}" if which=="head" else f"R145_LIVE_ROOT pr=418 head={HEAD}"
        self.assertNotEqual("success",self.eval(*fx(title=title))["state"])
    return test

for _w in ("head","base"):
    _add_case("missing_"+_w,_missing_case(_w))

if __name__=="__main__": unittest.main()

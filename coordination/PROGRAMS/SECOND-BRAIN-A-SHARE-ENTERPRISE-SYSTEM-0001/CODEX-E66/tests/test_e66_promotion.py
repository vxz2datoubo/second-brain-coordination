from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys,unittest,json
from threading import Barrier,Thread
sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
from e66_promotion import *
NOW=datetime(2026,8,11,tzinfo=timezone.utc)
def subj(parent='a'*40,**kw):
 d=DigestBundle('1'*64,'2'*64,'3'*64); v=dict(package_id='p',repository_id='1303258074',repository_slug='vxz2datoubo/second-brain-coordination',task_id='E66',route_epoch=77,digests=d,provenance_status='TYPED_SYNTHETIC_E48_FIXTURE',target_scope='PROJECT',admission_class='PUBLIC_SAFE',expected_parent=parent);v.update(kw);return PreAdmissionSubject(**v)
def candidate(s=None):
 s=s or subj();return build_candidate(s,AdmissionEvidence('issue:227',s.repository_id,s.sha256,'PUBLIC_SAFE'))
def approval(c,**kw):
 s=c.subject; d=dict(object_type='ISSUE_COMMENT',object_id='123',repository_id=s.repository_id,repository_slug=s.repository_slug,actor_id='gpt',decision='APPROVE',task_id=s.task_id,route_epoch=str(s.route_epoch),candidate_identity_sha256=c.identity_sha256,expected_parent=s.expected_parent,expires_at=(NOW+timedelta(days=1)).isoformat(),gpt_review_ref='review:1');d.update(kw);return 'E66_APPROVAL_V1\n'+json.dumps(d,separators=(',',':'))
class T(unittest.TestCase):
 def test_builder_and_real_hash(self): self.assertNotEqual(candidate().admission_object_sha256,'0'*64)
 def test_placeholder_and_private_rejected(self):
  with self.assertRaises(Reject): CandidateKnowledgePackage(subj(),'x','0'*64)
  with self.assertRaises(Reject): candidate(subj(admission_class='PRIVATE_OR_SENSITIVE'))
 def test_strict_approval(self):
  c=candidate(); verify_approval(parse_approval_control(approval(c)),c,NOW,'gpt')
  for x in ('bad','E66_APPROVAL_V1\n{}',approval(c,decision='DENY'),approval(c,candidate_identity_sha256='f'*64)):
   with self.assertRaises(Reject): verify_approval(parse_approval_control(x),c,NOW,'gpt')
 def test_approval_adversarial_bindings(self):
  c=candidate()
  for change in ({'actor_id':'other'},{'repository_id':'wrong'},{'task_id':'wrong'},{'route_epoch':'76'},{'expected_parent':'b'*40},{'expires_at':(NOW-timedelta(seconds=1)).isoformat()},{'object_id':''},{'gpt_review_ref':''}):
   with self.assertRaises(Reject): verify_approval(parse_approval_control(approval(c,**change)),c,NOW,'gpt')
  with self.assertRaises(Reject): parse_approval_control(approval(c)+'\nextra')
 def test_expiry_is_real_timezone_aware_instant(self):
  c=candidate()
  for value in ('not-a-time','2026-08-12T00:00:00',(NOW-timedelta(seconds=1)).isoformat(),NOW.replace(tzinfo=None).isoformat()):
   with self.assertRaises(Reject): verify_approval(parse_approval_control(approval(c,expires_at=value)),c,NOW,'gpt')
  with self.assertRaises(Reject): verify_approval(parse_approval_control(approval(c,expires_at=NOW.isoformat())),c,NOW,'gpt')
  verify_approval(parse_approval_control(approval(c,expires_at='2026-08-11T08:01:00+00:00')),c,NOW,'gpt')
  verify_approval(parse_approval_control(approval(c,expires_at='2026-08-11T16:01:00+08:00')),c,NOW,'gpt')
 def test_git_cas_idempotent_stale_unknown(self):
  with TemporaryDirectory() as td:
   p=Path(td); subprocess.run(['git','init'],cwd=p,check=True,capture_output=True);subprocess.run(['git','config','user.email','test@example.invalid'],cwd=p,check=True);subprocess.run(['git','config','user.name','test'],cwd=p,check=True);(p/'a').write_text('a');subprocess.run(['git','add','a'],cwd=p,check=True);subprocess.run(['git','commit','-m','init'],cwd=p,check=True,capture_output=True); head=subprocess.run(['git','rev-parse','HEAD'],cwd=p,text=True,capture_output=True,check=True).stdout.strip();store=LocalGitMarkerStore(p);r=store.consume('a',candidate().identity_sha256,head);self.assertFalse(r['idempotent']);self.assertTrue(store.consume('a',candidate().identity_sha256,head)['idempotent']);
   with self.assertRaises(Reject): store.consume('b',candidate().identity_sha256,head)
 def test_unknown_outcome_reconciles_exact_marker_only(self):
  with TemporaryDirectory() as td:
   p=Path(td); subprocess.run(['git','init'],cwd=p,check=True,capture_output=True);subprocess.run(['git','config','user.email','test@example.invalid'],cwd=p,check=True);subprocess.run(['git','config','user.name','test'],cwd=p,check=True);(p/'a').write_text('a');subprocess.run(['git','add','a'],cwd=p,check=True);subprocess.run(['git','commit','-m','init'],cwd=p,check=True,capture_output=True);h=subprocess.run(['git','rev-parse','HEAD'],cwd=p,text=True,capture_output=True,check=True).stdout.strip();store=LocalGitMarkerStore(p);store.unknown_once=True
   with self.assertRaises(UnknownOutcome): store.consume('u',candidate().identity_sha256,h)
   self.assertTrue(store.consume('u',candidate().identity_sha256,h)['idempotent'])
   with self.assertRaises(Replay): store.consume('u','f'*64,h)
 def test_two_consumers_mint_one_marker(self):
  with TemporaryDirectory() as td:
   p=Path(td); subprocess.run(['git','init'],cwd=p,check=True,capture_output=True);subprocess.run(['git','config','user.email','test@example.invalid'],cwd=p,check=True);subprocess.run(['git','config','user.name','test'],cwd=p,check=True);(p/'a').write_text('a');subprocess.run(['git','add','a'],cwd=p,check=True);subprocess.run(['git','commit','-m','init'],cwd=p,check=True,capture_output=True);h=subprocess.run(['git','rev-parse','HEAD'],cwd=p,text=True,capture_output=True,check=True).stdout.strip();store=LocalGitMarkerStore(p);bar=Barrier(2);out=[]
   def go(payload):
    try: bar.wait();out.append(('result',store.consume('race',payload,h)))
    except Exception as e: out.append(('error',e))
   payload=candidate().identity_sha256;ts=[Thread(target=go,args=(payload,)),Thread(target=go,args=(payload,))];[t.start() for t in ts];[t.join() for t in ts]
   self.assertTrue(all(not t.is_alive() for t in ts));self.assertEqual(len(out),2);self.assertFalse(any(k=='error' for k,_ in out));self.assertEqual(sum(not x['idempotent'] for _,x in out),1)
 def test_marker_path_rejects_traversal_without_escape(self):
  with TemporaryDirectory() as td:
   p=Path(td); subprocess.run(['git','init'],cwd=p,check=True,capture_output=True);subprocess.run(['git','config','user.email','test@example.invalid'],cwd=p,check=True);subprocess.run(['git','config','user.name','test'],cwd=p,check=True);(p/'a').write_text('a');subprocess.run(['git','add','a'],cwd=p,check=True);subprocess.run(['git','commit','-m','init'],cwd=p,check=True,capture_output=True);h=subprocess.run(['git','rev-parse','HEAD'],cwd=p,text=True,capture_output=True,check=True).stdout.strip();store=LocalGitMarkerStore(p)
   for aid in ('','../x','a/b','a\\b','x'*129):
    with self.assertRaises(Reject): store.consume(aid,candidate().identity_sha256,h)
   self.assertFalse((p/'x').exists())
if __name__=='__main__': unittest.main()

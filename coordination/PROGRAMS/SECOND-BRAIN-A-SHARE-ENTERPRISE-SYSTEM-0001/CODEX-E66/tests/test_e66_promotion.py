from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys,unittest,json
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
 def test_git_cas_idempotent_stale_unknown(self):
  with TemporaryDirectory() as td:
   p=Path(td); subprocess.run(['git','init'],cwd=p,check=True,capture_output=True);subprocess.run(['git','config','user.email','test@example.invalid'],cwd=p,check=True);subprocess.run(['git','config','user.name','test'],cwd=p,check=True);(p/'a').write_text('a');subprocess.run(['git','add','a'],cwd=p,check=True);subprocess.run(['git','commit','-m','init'],cwd=p,check=True,capture_output=True); head=subprocess.run(['git','rev-parse','HEAD'],cwd=p,text=True,capture_output=True,check=True).stdout.strip();store=LocalGitMarkerStore(p);r=store.consume('a',candidate().identity_sha256,head);self.assertFalse(r['idempotent']);self.assertTrue(store.consume('a',candidate().identity_sha256,head)['idempotent']);
   with self.assertRaises(Reject): store.consume('b',candidate().identity_sha256,head)
if __name__=='__main__': unittest.main()

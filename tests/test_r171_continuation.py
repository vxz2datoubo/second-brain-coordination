from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile, unittest
from creative_runtime import continuation
from creative_runtime.ledger import LedgerViolation

ROOT=Path(__file__).resolve().parents[1]
def cli_module():
 spec=importlib.util.spec_from_file_location("cli",ROOT/"apps"/"cli"/"creativectl.py"); assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class R171ContinuationTests(unittest.TestCase):
 def test_migrate_then_choose_say_slots_preserves_source(self):
  with tempfile.TemporaryDirectory() as raw:
   workspace=Path(raw); cli=cli_module(); cli.initialize(workspace); cli.choose(workspace,"approach")
   original=(workspace/"session.json").read_bytes(); continuation.migrate(workspace)
   chosen=cli.say(workspace,"I listen carefully"); self.assertTrue(chosen["v2"])
   continuation.save_slot(workspace,"before-say")
   restored=continuation.restore_slot(workspace,"before-say"); self.assertEqual(restored.beat_id,"resolution")
   continuation.save_slot(workspace,"again")
   self.assertEqual((workspace/"session.json").read_bytes(),original)
   self.assertEqual(continuation.load(workspace)[1],continuation.load(workspace,"again")[1])
 def test_modified_source_rejects_continuation(self):
  with tempfile.TemporaryDirectory() as raw:
   workspace=Path(raw); cli=cli_module(); cli.initialize(workspace); source=workspace/"session.json"; continuation.migrate(workspace)
   source.write_bytes(source.read_bytes()+b" ")
   with self.assertRaisesRegex(LedgerViolation,"immutable legacy source"): continuation.load(workspace)
if __name__=="__main__": unittest.main()

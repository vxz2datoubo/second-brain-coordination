from __future__ import annotations
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from creative_runtime import MultiScriptDirectorCompiler, flagship_story_fixture, load_catalog, materialize_catalog
from creative_runtime.director_beat_plan import DirectorBeatPlanner, STYLE_PRESENTATION
from creative_runtime.shot_bundle import ShotBundleCompiler, ShotBundleViolation, _digest, _material


class ShotBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.package,self.graph,self.bibles=flagship_story_fixture(); root=Path(self.temp.name); path=Path("catalog.json")
        materialize_catalog(root,path,(self.package,)); self.catalog=load_catalog(root,path)
        self.director=MultiScriptDirectorCompiler(self.catalog)
        binding=self.director.select(script_id=self.package.script_id,script_revision=self.package.script_revision,
                                     package_hash=self.package.package_hash,style_profile_id="cinematic_live_action")
        self.planner=DirectorBeatPlanner(self.catalog,self.director.compile(binding),self.graph,self.bibles)
        self.compiler=ShotBundleCompiler(self.planner)

    def test_all_twelve_choice_bundles_compile_inspect_and_cover(self):
        self.assertEqual(len(self.compiler.list_choices()),12)
        for choice,scene in self.compiler.list_choices():
            plan=self.planner.compile(choice,scene); bundle=self.compiler.compile(choice,scene)
            self.assertEqual(bundle,self.compiler.compile(choice,scene)); self.assertIs(self.compiler.inspect(plan,bundle),bundle)
            self.assertEqual(len(bundle.shots),6)
            self.assertEqual({b.beat_id for b in plan.beats},{x for s in bundle.shots for x in s.covered_beat_ids})
            self.assertEqual({p.option_id for p in plan.outcome_previews},{x for s in bundle.shots for x in s.option_ids})

    def test_all_twenty_four_outcome_bundles_compile_inspect(self):
        count=0
        for choice in self.graph.choices:
            plan=self.planner.compile(choice.choice_id,choice.scene_id)
            for option in choice.options:
                bundle=self.compiler.compile_outcome(choice.choice_id,choice.scene_id,option.option_id)
                self.assertIs(self.compiler.inspect(plan,bundle),bundle); self.assertIsNotNone(bundle.selected_outcome_preview_hash); count+=1
        self.assertEqual(count,24)

    def test_four_styles_change_presentation_but_not_coverage(self):
        choice=self.graph.choices[0]; signatures=[]
        for style in STYLE_PRESENTATION:
            binding=self.director.select(script_id=self.package.script_id,script_revision=self.package.script_revision,
                                         package_hash=self.package.package_hash,style_profile_id=style)
            planner=DirectorBeatPlanner(self.catalog,self.director.compile(binding),self.graph,self.bibles)
            bundle=ShotBundleCompiler(planner).compile(choice.choice_id,choice.scene_id)
            signatures.append((bundle.style_profile_id,tuple(s.responsibility for s in bundle.shots),
                               tuple(x for s in bundle.shots for x in s.option_ids)))
        self.assertEqual(len({x[0] for x in signatures}),4); self.assertEqual(len({x[1:] for x in signatures}),1)

    def test_deep_immutability(self):
        choice=self.graph.choices[0]; bundle=self.compiler.compile(choice.choice_id,choice.scene_id)
        with self.assertRaises(FrozenInstanceError): bundle.choice_id="bad"
        with self.assertRaises(FrozenInstanceError): bundle.shots[0].framing="bad"

    def test_unknown_outcome_and_tampered_plan_fail_closed(self):
        choice=self.graph.choices[0]
        with self.assertRaises(ValueError): self.compiler.compile_outcome(choice.choice_id,choice.scene_id,"missing")
        plan=self.planner.compile(choice.choice_id,choice.scene_id); bad=replace(plan,plan_hash="0"*64)
        with self.assertRaises(ShotBundleViolation): self.compiler.inspect(bad,self.compiler.compile(choice.choice_id,choice.scene_id))

    def test_duplicate_gap_uncovered_option_and_policy_fail_closed(self):
        choice=self.graph.choices[0]; plan=self.planner.compile(choice.choice_id,choice.scene_id); bundle=self.compiler.compile(choice.choice_id,choice.scene_id)
        cases=[]
        cases.append(replace(bundle,shots=(bundle.shots[0],replace(bundle.shots[1],shot_id=bundle.shots[0].shot_id),*bundle.shots[2:])))
        cases.append(replace(bundle,shots=(bundle.shots[0],replace(bundle.shots[1],order=9),*bundle.shots[2:])))
        cases.append(replace(bundle,shots=(replace(bundle.shots[0],covered_beat_ids=()),*bundle.shots[1:])))
        cases.append(replace(bundle,shots=tuple(replace(s,option_ids=()) for s in bundle.shots)))
        cases.append(replace(bundle,shots=(replace(bundle.shots[0],framing="illegal"),*bundle.shots[1:])))
        cases.append(replace(bundle,shots=(replace(bundle.shots[0],max_duration_seconds=99),*bundle.shots[1:])))
        cases.append(replace(bundle,shots=(replace(bundle.shots[0],continuity_anchors=()),*bundle.shots[1:])))
        for forged in cases:
            forged=replace(forged,bundle_id="",bundle_hash=""); h=_digest(_material(forged)); forged=replace(forged,bundle_hash=h,bundle_id=f"shotbundle_{h[:24]}")
            with self.assertRaises(ShotBundleViolation): self.compiler.inspect(plan,forged)

    def test_recomputed_outer_hash_cannot_hide_inner_substitution(self):
        choice=self.graph.choices[0]; plan=self.planner.compile(choice.choice_id,choice.scene_id); bundle=self.compiler.compile(choice.choice_id,choice.scene_id)
        shot=replace(bundle.shots[0],responsibility="forged but plausible")
        forged=replace(bundle,shots=(shot,*bundle.shots[1:]),bundle_id="",bundle_hash=""); h=_digest(_material(forged)); forged=replace(forged,bundle_hash=h,bundle_id=f"shotbundle_{h[:24]}")
        with self.assertRaises(ShotBundleViolation) as caught: self.compiler.inspect(plan,forged)
        self.assertEqual(caught.exception.code,"BUNDLE_SOURCE_SUBSTITUTION")

    def test_no_execution_or_player_authority(self):
        names=set(vars(self.compiler)); forbidden=("player","session","campaign","queue","job","render","generate","upload","provider")
        self.assertFalse(any(any(word in name.lower() for word in forbidden) for name in names))

if __name__ == "__main__": unittest.main()

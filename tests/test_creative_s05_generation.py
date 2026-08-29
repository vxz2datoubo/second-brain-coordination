from __future__ import annotations

from dataclasses import replace
import unittest

from creative_runtime.contracts import GenerationRequest
from creative_runtime.director import compile_director
from creative_runtime.generation import GenerationViolation, adapter_for
from creative_runtime.contracts import StoryState


class CreativeS05GenerationTests(unittest.TestCase):
    def valid_request(self, provider: str = "offline", confirm: bool = False) -> tuple[GenerationRequest, object]:
        compilation = compile_director(StoryState(scene_id="synthetic_archive", beat_id="arrival"))
        request = GenerationRequest(
            request_id="req_synthetic_001",
            provider=provider,
            shot_plan=compilation.shots[0],
            content_rating="non_explicit",
            confirm_generate=confirm,
        )
        return request, compilation.quality_report

    def test_offline_result_is_deterministic_and_simulated(self) -> None:
        request, report = self.valid_request()
        adapter = adapter_for("offline")
        first = adapter.generate(request, report)
        second = adapter.generate(request, report)
        self.assertEqual(first, second)
        self.assertEqual(first.status, "simulated")
        self.assertTrue(first.output_ref.startswith("offline://"))

    def test_quality_or_content_failure_blocks_before_any_adapter_result(self) -> None:
        request, report = self.valid_request()
        failed_report = replace(report, findings=report.findings + (type("Finding", (), {"severity": "hard"})(),))
        with self.assertRaises(GenerationViolation):
            adapter_for("offline").generate(request, failed_report)
        with self.assertRaises(GenerationViolation):
            adapter_for("offline").generate(replace(request, content_rating="explicit"), report)

    def test_external_provider_has_no_call_path_even_with_confirmation(self) -> None:
        request, report = self.valid_request("dreamina", confirm=False)
        guard = adapter_for("dreamina")
        self.assertEqual(guard.preview(request, report).status, "blocked_confirmation_required")
        confirmed = guard.preview(replace(request, confirm_generate=True), report)
        self.assertEqual(confirmed.status, "blocked_route_authority")
        self.assertIsNone(confirmed.output_ref)


if __name__ == "__main__":
    unittest.main()

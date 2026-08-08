from __future__ import annotations

import unittest

from e60_runtime import ProviderEvidenceAggregate, ProviderEvidenceError


def _mapping(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": "CODEX-E60-test",
        "provider_run_id": "31264435435",
        "tested_head": "a" * 40,
        "tested_parent": "b" * 40,
        "tested_tree": "c" * 40,
        "jobs": [
            {"python_minor": "3.13", "job_id": "93120191106", "artifact_id": "9023716920", "artifact_content_sha256": "e" * 64},
            {"python_minor": "3.11", "job_id": "93120191128", "artifact_id": "9023716567", "artifact_content_sha256": "d" * 64},
        ],
    }
    value.update(overrides)
    return value


class ProviderEvidenceAggregateTests(unittest.TestCase):
    def test_canonical_digest_is_stable_across_input_job_order(self) -> None:
        forward = ProviderEvidenceAggregate.from_mapping(_mapping())
        reverse = ProviderEvidenceAggregate.from_mapping(_mapping(jobs=list(reversed(_mapping()["jobs"]))))
        self.assertEqual(forward.digest, reverse.digest)
        self.assertEqual([job.python_minor for job in forward.jobs], ["3.11", "3.13"])

    def test_missing_python_matrix_member_fails_closed(self) -> None:
        with self.assertRaisesRegex(ProviderEvidenceError, "MATRIX_INCOMPLETE"):
            ProviderEvidenceAggregate.from_mapping(_mapping(jobs=[_mapping()["jobs"][0]]))

    def test_non_numeric_job_or_artifact_id_fails_closed(self) -> None:
        jobs = list(_mapping()["jobs"])
        jobs[0] = {**jobs[0], "job_id": "synthetic-e60"}
        with self.assertRaisesRegex(ProviderEvidenceError, "JOB_ID_MALFORMED"):
            ProviderEvidenceAggregate.from_mapping(_mapping(jobs=jobs))

    def test_extra_field_fails_closed(self) -> None:
        candidate = _mapping()
        candidate["unbound_provider_claim"] = "not allowed"
        with self.assertRaisesRegex(ProviderEvidenceError, "FIELD_SET_MISMATCH"):
            ProviderEvidenceAggregate.from_mapping(candidate)


if __name__ == "__main__":
    unittest.main()

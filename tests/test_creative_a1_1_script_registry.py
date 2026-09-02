from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from creative_runtime import (
    ScriptPackageRegistry,
    ScriptRegistryViolation,
    approved_synthetic_script_packages,
    build_script_package,
    canonical_json,
    compute_package_hash,
    parse_script_package_json,
)


class ScriptPackageRegistryTests(unittest.TestCase):
    def build_registry(self) -> tuple[ScriptPackageRegistry, tuple]:
        packages = approved_synthetic_script_packages()
        registry = ScriptPackageRegistry()
        for package in packages:
            registry.register(package)
        return registry, packages

    def assert_violation(self, code: str, operation) -> None:
        with self.assertRaises(ScriptRegistryViolation) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_two_approved_synthetic_packages_have_four_presentation_styles(self) -> None:
        packages = approved_synthetic_script_packages()
        self.assertEqual(len(packages), 2)
        self.assertEqual(len({package.script_id for package in packages}), 2)
        for package in packages:
            self.assertEqual(package.approval_status, "approved")
            self.assertEqual(package.source_provenance["classification"], "SYNTHETIC")
            self.assertGreaterEqual(len(package.style_profiles), 4)
            self.assertTrue(all(profile.presentation_only for profile in package.style_profiles))
            self.assertEqual(compute_package_hash(package), package.package_hash)

    def test_package_hash_and_serialization_are_deterministic(self) -> None:
        first = approved_synthetic_script_packages()
        second = approved_synthetic_script_packages()
        self.assertEqual([item.package_hash for item in first], [item.package_hash for item in second])
        self.assertEqual([canonical_json(item) for item in first], [canonical_json(item) for item in second])

    def test_registered_content_is_deeply_immutable(self) -> None:
        package = approved_synthetic_script_packages()[0]
        with self.assertRaises(TypeError):
            package.world_bible["title"] = "tampered"
        with self.assertRaises(TypeError):
            package.character_bibles[0]["goal"] = "tampered"
        with self.assertRaises(FrozenInstanceError):
            package.script_revision = "2.0.0"

    def test_exact_identity_and_approved_style_produce_minimal_director_selection(self) -> None:
        registry, packages = self.build_registry()
        package = packages[0]
        selection = registry.select_for_director(
            script_id=package.script_id,
            script_revision=package.script_revision,
            package_hash=package.package_hash,
            style_profile_id="ink_animation",
        )
        self.assertEqual(selection.to_dict(), {
            "script_id": package.script_id,
            "script_revision": "1.0.0",
            "package_hash": package.package_hash,
            "style_profile_id": "ink_animation",
        })
        with self.assertRaises(FrozenInstanceError):
            selection.style_profile_id = "stylized_3d"

    def test_selection_fails_closed_for_unknown_or_mismatched_identity(self) -> None:
        cases = (
            ("script_id", "not_registered", "SCRIPT_UNKNOWN"),
            ("script_revision", "9.9.9", "SCRIPT_REVISION_UNKNOWN"),
            ("package_hash", "0" * 64, "PACKAGE_HASH_MISMATCH"),
            ("style_profile_id", "unapproved_style", "STYLE_PROFILE_UNKNOWN"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                registry, packages = self.build_registry()
                package = packages[0]
                request = {
                    "script_id": package.script_id,
                    "script_revision": package.script_revision,
                    "package_hash": package.package_hash,
                    "style_profile_id": "cinematic_live_action",
                }
                request[field] = value
                before = registry.list_identities()
                self.assert_violation(code, lambda: registry.select_for_director(**request))
                self.assertEqual(registry.list_identities(), before)

    def test_unapproved_package_is_rejected_without_registry_side_effect(self) -> None:
        registry = ScriptPackageRegistry()
        unapproved = replace(approved_synthetic_script_packages()[0], approval_status="pending")
        self.assert_violation("SCRIPT_NOT_APPROVED", lambda: registry.register(unapproved))
        self.assertEqual(registry.list_identities(), ())

    def test_content_tamper_with_old_hash_is_rejected(self) -> None:
        registry = ScriptPackageRegistry()
        package = approved_synthetic_script_packages()[0]
        tampered = replace(package, world_bible={"title": "forged", "premise": "forged"})
        self.assert_violation("PACKAGE_HASH_MISMATCH", lambda: registry.register(tampered))
        self.assertEqual(registry.list_identities(), ())

    def test_approved_revision_cannot_be_replaced_by_different_valid_content(self) -> None:
        registry, packages = self.build_registry()
        original = packages[0]
        values = original.to_dict()
        values.pop("package_hash")
        values["world_bible"] = {**values["world_bible"], "premise": "a different approved story"}
        replacement = build_script_package(**values)
        before = registry.list_identities()
        self.assert_violation("IMMUTABLE_REVISION_CONFLICT", lambda: registry.register(replacement))
        self.assertEqual(registry.list_identities(), before)

    def test_style_selection_never_changes_shared_story_content(self) -> None:
        registry, packages = self.build_registry()
        package = packages[1]
        story_before = canonical_json(package.story_beats)
        for profile in package.style_profiles:
            selection = registry.select_for_director(
                script_id=package.script_id,
                script_revision=package.script_revision,
                package_hash=package.package_hash,
                style_profile_id=profile.style_profile_id,
            )
            self.assertEqual(selection.package_hash, package.package_hash)
            self.assertEqual(canonical_json(package.story_beats), story_before)

    def test_duplicate_registration_is_idempotent_and_creates_no_runtime_authority(self) -> None:
        registry = ScriptPackageRegistry()
        package = approved_synthetic_script_packages()[0]
        self.assertIs(registry.register(package), registry.register(package))
        self.assertEqual(len(registry.list_identities()), 1)
        self.assertFalse(hasattr(registry, "campaigns"))
        self.assertFalse(hasattr(registry, "sessions"))
        self.assertFalse(hasattr(registry, "media_jobs"))

    def test_private_or_credential_metadata_is_rejected(self) -> None:
        package = approved_synthetic_script_packages()[0]
        values = package.to_dict()
        values.pop("package_hash")
        values["source_provenance"] = {**values["source_provenance"], "token": "not-allowed"}
        self.assert_violation("PRIVATE_METADATA_FORBIDDEN", lambda: build_script_package(**values))

    def test_canonical_json_round_trip_and_duplicate_metadata_rejection(self) -> None:
        package = approved_synthetic_script_packages()[0]
        restored = parse_script_package_json(canonical_json(package))
        self.assertEqual(restored, package)
        duplicate = canonical_json(package).replace(
            '"script_id":"synthetic_archive_case"',
            '"script_id":"synthetic_archive_case","script_id":"forged"',
            1,
        )
        self.assert_violation("DUPLICATE_METADATA_KEY", lambda: parse_script_package_json(duplicate))

    def test_duplicate_or_incomplete_style_profiles_fail_closed(self) -> None:
        package = approved_synthetic_script_packages()[0]
        values = package.to_dict()
        values.pop("package_hash")
        values["style_profiles"] = values["style_profiles"][:3]
        self.assert_violation("STYLE_PROFILE_INCOMPLETE", lambda: build_script_package(**values))
        values["style_profiles"] = [
            package.style_profiles[0].to_dict(),
            package.style_profiles[0].to_dict(),
            *[item.to_dict() for item in package.style_profiles[1:]],
        ]
        self.assert_violation("STYLE_PROFILE_DUPLICATE", lambda: build_script_package(**values))

        values["style_profiles"] = [{"style_profile_id": "malformed"}]
        self.assert_violation("PACKAGE_SCHEMA_INVALID", lambda: build_script_package(**values))

    def test_wrong_contract_version_and_unapproved_source_fail_closed(self) -> None:
        package = approved_synthetic_script_packages()[0]
        wrong_schema = replace(package, schema_version="ScriptPackage/v2")
        self.assert_violation("PACKAGE_SCHEMA_VERSION", lambda: ScriptPackageRegistry().register(wrong_schema))

        values = package.to_dict()
        values.pop("package_hash")
        values["source_provenance"] = {
            **values["source_provenance"],
            "approved_for_reuse": False,
        }
        self.assert_violation("SOURCE_PROVENANCE_INVALID", lambda: build_script_package(**values))

    def test_asset_manifest_tamper_with_old_hash_is_rejected(self) -> None:
        registry = ScriptPackageRegistry()
        package = approved_synthetic_script_packages()[0]
        manifest = [dict(item) for item in package.asset_manifest]
        manifest[0]["asset_id"] = "synthetic_forged_asset"
        tampered = replace(package, asset_manifest=tuple(manifest))
        self.assert_violation("PACKAGE_HASH_MISMATCH", lambda: registry.register(tampered))
        self.assertEqual(registry.list_identities(), ())


if __name__ == "__main__":
    unittest.main()

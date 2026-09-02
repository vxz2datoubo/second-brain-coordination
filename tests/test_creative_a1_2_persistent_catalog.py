from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from creative_runtime import (
    DirectorScriptSelection,
    ScriptCatalogViolation,
    ScriptRegistryViolation,
    approved_synthetic_script_packages,
    build_script_package,
    canonical_json,
    load_catalog,
    materialize_catalog,
    serialize_catalog,
)


class PersistentScriptCatalogTests(unittest.TestCase):
    relative_path = Path("runtime") / "script_catalog.v1.json"

    def assert_violation(self, code: str, operation) -> None:
        with self.assertRaises(ScriptCatalogViolation) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def materialized(self, root: Path):
        packages = approved_synthetic_script_packages()
        path = materialize_catalog(root, self.relative_path, packages)
        return path, load_catalog(root, self.relative_path), packages

    def test_persist_restart_reload_preserves_exact_identity_and_bytes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path, first, packages = self.materialized(root)
            before = path.read_bytes()
            second_path = materialize_catalog(root, self.relative_path, reversed(packages))
            second = load_catalog(root, self.relative_path)
            self.assertEqual(second_path, path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(first.catalog_hash, second.catalog_hash)
            self.assertEqual(first.list_entries(), second.list_entries())
            self.assertEqual(
                tuple((item.script_id, item.script_revision, item.package_hash) for item in first.list_entries()),
                tuple((item.script_id, item.script_revision, item.package_hash) for item in second.list_entries()),
            )

    def test_list_get_and_selection_are_immutable_and_read_only(self) -> None:
        with TemporaryDirectory() as directory:
            _, catalog, packages = self.materialized(Path(directory))
            entry = catalog.list_entries()[0]
            package = catalog.get(entry.script_id, entry.script_revision, entry.package_hash)
            selection = catalog.select(
                script_id=entry.script_id,
                script_revision=entry.script_revision,
                package_hash=entry.package_hash,
                style_profile_id=entry.style_profile_ids[0],
            )
            self.assertIn(package, packages)
            with self.assertRaises(FrozenInstanceError):
                entry.script_revision = "2.0.0"
            with self.assertRaises(FrozenInstanceError):
                selection.style_profile_id = "forged"
            with self.assertRaises(TypeError):
                package.world_bible["title"] = "forged"
            self.assertFalse(hasattr(catalog, "campaigns"))
            self.assertFalse(hasattr(catalog, "sessions"))
            self.assertFalse(hasattr(catalog, "director_jobs"))
            self.assertFalse(hasattr(catalog, "media_jobs"))

    def test_director_v2_binding_round_trip_is_exact_and_immutable(self) -> None:
        with TemporaryDirectory() as directory:
            _, catalog, _ = self.materialized(Path(directory))
            entry = catalog.list_entries()[0]
            selection = catalog.select(
                script_id=entry.script_id,
                script_revision=entry.script_revision,
                package_hash=entry.package_hash,
                style_profile_id="cinematic_live_action",
            )
            binding = catalog.bind_for_director(selection)
            consumed = catalog.consume_director_binding(binding)
            self.assertEqual(consumed.package_hash, entry.package_hash)
            self.assertEqual(binding.catalog_hash, catalog.catalog_hash)
            with self.assertRaises(FrozenInstanceError):
                binding.package_hash = "0" * 64

    def test_substitution_after_validation_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            _, catalog, _ = self.materialized(Path(directory))
            first, second = catalog.list_entries()
            selection = DirectorScriptSelection(
                first.script_id,
                first.script_revision,
                first.package_hash,
                "ink_animation",
            )
            binding = catalog.bind_for_director(selection)
            cases = (
                (replace(binding, catalog_hash="0" * 64), "DIRECTOR_CATALOG_SUBSTITUTION"),
                (replace(binding, script_id=second.script_id), "DIRECTOR_SELECTION_SUBSTITUTION"),
                (replace(binding, script_revision="9.9.9"), "DIRECTOR_SELECTION_SUBSTITUTION"),
                (replace(binding, package_hash=second.package_hash), "DIRECTOR_SELECTION_SUBSTITUTION"),
                (replace(binding, style_profile_id="unknown"), "DIRECTOR_SELECTION_SUBSTITUTION"),
                (replace(binding, asset_manifest_hash="0" * 64), "DIRECTOR_ASSET_SUBSTITUTION"),
                (replace(binding, source_provenance_hash="0" * 64), "DIRECTOR_PROVENANCE_SUBSTITUTION"),
            )
            for forged, code in cases:
                with self.subTest(code=code):
                    self.assert_violation(code, lambda forged=forged: catalog.consume_director_binding(forged))

    def test_catalog_hash_tamper_and_stale_package_hash_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path, _, _ = self.materialized(root)
            document = json.loads(path.read_text(encoding="utf-8"))
            document["packages"][0]["world_bible"]["title"] = "forged"
            path.write_text(canonical_json(document) + "\n", encoding="utf-8")
            self.assert_violation("CATALOG_HASH_MISMATCH", lambda: load_catalog(root, self.relative_path))

            document["catalog_hash"] = __import__("hashlib").sha256(
                canonical_json({"schema_version": document["schema_version"], "packages": document["packages"]}).encode("utf-8")
            ).hexdigest()
            path.write_text(canonical_json(document) + "\n", encoding="utf-8")
            self.assert_violation("PACKAGE_HASH_MISMATCH", lambda: load_catalog(root, self.relative_path))

    def test_duplicate_revision_with_different_valid_hash_is_rejected(self) -> None:
        package = approved_synthetic_script_packages()[0]
        values = package.to_dict()
        values.pop("package_hash")
        values["world_bible"] = {**values["world_bible"], "premise": "different content"}
        conflict = build_script_package(**values)
        self.assert_violation(
            "IMMUTABLE_REVISION_CONFLICT",
            lambda: serialize_catalog((package, conflict)),
        )

    def test_unknown_unapproved_stale_hash_and_unknown_style_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            _, catalog, packages = self.materialized(Path(directory))
            package = packages[0]
            invalid_requests = (
                ("unknown", package.script_revision, package.package_hash, "ink_animation", "SCRIPT_UNKNOWN"),
                (package.script_id, "9.9.9", package.package_hash, "ink_animation", "SCRIPT_REVISION_UNKNOWN"),
                (package.script_id, package.script_revision, "0" * 64, "ink_animation", "PACKAGE_HASH_MISMATCH"),
                (package.script_id, package.script_revision, package.package_hash, "unknown", "STYLE_PROFILE_UNKNOWN"),
            )
            for script_id, revision, package_hash, style, code in invalid_requests:
                with self.subTest(code=code):
                    with self.assertRaises(ScriptRegistryViolation) as caught:
                        catalog.select(
                            script_id=script_id,
                            script_revision=revision,
                            package_hash=package_hash,
                            style_profile_id=style,
                        )
                    self.assertEqual(getattr(caught.exception, "code", None), code)

            unapproved = replace(package, approval_status="pending")
            self.assert_violation("SCRIPT_NOT_APPROVED", lambda: serialize_catalog((unapproved,)))

    def test_malformed_duplicate_key_partial_corrupt_and_extra_schema_fail_closed(self) -> None:
        mutations = (
            ('{"schema_version":"ScriptPackageCatalog/v1"', "CATALOG_CORRUPT"),
            ('{"schema_version":"ScriptPackageCatalog/v1","schema_version":"x","catalog_hash":"x","packages":[]}', "CATALOG_DUPLICATE_KEY"),
            ('{"schema_version":"ScriptPackageCatalog/v1","catalog_hash":"x","packages":[]}', "CATALOG_PARTIAL"),
            ('{"schema_version":"ScriptPackageCatalog/v1","catalog_hash":"x","packages":[],"extra":1}', "CATALOG_SCHEMA_INVALID"),
        )
        for payload, code in mutations:
            with self.subTest(code=code), TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / self.relative_path
                path.parent.mkdir(parents=True)
                path.write_text(payload, encoding="utf-8")
                self.assert_violation(code, lambda: load_catalog(root, self.relative_path))

    def test_path_escape_and_immutable_replacement_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            packages = approved_synthetic_script_packages()
            self.assert_violation(
                "CATALOG_PATH_ESCAPE",
                lambda: materialize_catalog(root, Path("..") / "escaped.json", packages),
            )
            self.assert_violation(
                "CATALOG_PATH_ESCAPE",
                lambda: load_catalog(root, Path("..") / "escaped.json"),
            )
            path = materialize_catalog(root, self.relative_path, packages)
            path.write_text("different", encoding="utf-8")
            self.assert_violation(
                "CATALOG_IMMUTABLE_CONFLICT",
                lambda: materialize_catalog(root, self.relative_path, packages),
            )

    def test_exact_duplicate_and_noncanonical_order_fail_closed(self) -> None:
        packages = approved_synthetic_script_packages()
        self.assert_violation(
            "CATALOG_DUPLICATE_PACKAGE",
            lambda: serialize_catalog((packages[0], packages[0])),
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / self.relative_path
            path.parent.mkdir(parents=True)
            document = json.loads(serialize_catalog(packages))
            document["packages"].reverse()
            material = {"schema_version": document["schema_version"], "packages": document["packages"]}
            document["catalog_hash"] = __import__("hashlib").sha256(
                canonical_json(material).encode("utf-8")
            ).hexdigest()
            path.write_text(canonical_json(document) + "\n", encoding="utf-8")
            self.assert_violation("CATALOG_NONCANONICAL", lambda: load_catalog(root, self.relative_path))

    def test_atomic_write_failure_leaves_no_catalog_or_temporary_file(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("creative_runtime.script_catalog.os.replace", side_effect=OSError("simulated interruption")):
                self.assert_violation(
                    "CATALOG_WRITE_FAILED",
                    lambda: materialize_catalog(root, self.relative_path, approved_synthetic_script_packages()),
                )
            target = root / self.relative_path
            self.assertFalse(target.exists())
            self.assertEqual(list(target.parent.glob("*.tmp")), [])
            self.assertEqual(list(target.parent.glob("*.lock")), [])

    def test_concurrent_materialization_lock_fails_closed_without_target(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.relative_path
            target.parent.mkdir(parents=True)
            lock = target.with_name(f".{target.name}.lock")
            lock.write_bytes(b"")
            self.assert_violation(
                "CATALOG_WRITE_BUSY",
                lambda: materialize_catalog(root, self.relative_path, approved_synthetic_script_packages()),
            )
            self.assertFalse(target.exists())

    def test_invalid_utf8_catalog_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / self.relative_path
            path.parent.mkdir(parents=True)
            path.write_bytes(b"\xff\xfe\x00")
            self.assert_violation("CATALOG_READ_FAILED", lambda: load_catalog(root, self.relative_path))

    def test_director_boundary_rejects_untyped_selection_and_binding(self) -> None:
        with TemporaryDirectory() as directory:
            _, catalog, _ = self.materialized(Path(directory))
            self.assert_violation("DIRECTOR_SELECTION_INVALID", lambda: catalog.bind_for_director(object()))
            self.assert_violation("DIRECTOR_BINDING_INVALID", lambda: catalog.consume_director_binding(object()))


if __name__ == "__main__":
    unittest.main()

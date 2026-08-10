from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.client import HTTPConnection
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
import threading
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from brainops_control_plane.discovery import ReadOnlyDiscovery
from brainops_control_plane.models import (
    ActivationManifest,
    AppAutomationIdentity,
    BoundCanaryApproval,
    CapabilitySet,
    CapabilityStatus,
    CliSession,
    DesiredState,
    ExecutionOwner,
    Lease,
    PortManifest,
    RouteRef,
    RouteState,
    ObservedState,
    ServiceManifest,
    ShadowOutcome,
    ValidationError,
    canonical_hash,
    find_secret_values,
    redact,
    reject_command_like_fields,
    safe_database_path,
    strict_json_loads,
)
from brainops_control_plane.reconciliation import (
    AntiEntropySchedule,
    ReconciliationContext,
    ReviewRequestEvent,
    ShadowReconciler,
    ShadowReviewWatcher,
    select_owner,
)
from brainops_control_plane.store import MetadataStore
from brainops_control_plane.web import ConsoleSnapshot, ReadOnlyControlServer, UI_HTML, create_server, make_handler


ROUTE = RouteRef("brainops.e35", "CODEX", 36)


def approval(
    *,
    canary_id: str = "BRAINOPS-E35-CANARY-0001",
    task_id: str = "CODEX-BRAINOPS-E35",
    epoch: int = 36,
    scope: str = "shadow_control_plane",
    expires_at: str = "2026-08-02T01:00:00Z",
) -> BoundCanaryApproval:
    return BoundCanaryApproval(canary_id, task_id, epoch, scope, expires_at, "nonce.e35", "approval.e35")


def activation(*, target: str = "CODEX", epoch: int = 36, bound_approval: BoundCanaryApproval | None | object = ...) -> ActivationManifest:
    selected_approval = approval() if bound_approval is ... else bound_approval
    return ActivationManifest(
        activation_id="activation.e35",
        route=RouteRef("brainops.e35", target, epoch),
        expected_epoch=epoch,
        idempotency_key="idem.e35",
        canary_id="BRAINOPS-E35-CANARY-0001",
        task_id="CODEX-BRAINOPS-E35",
        scope="shadow_control_plane",
        approval_nonce="nonce.e35",
        approval=selected_approval,  # type: ignore[arg-type]
    )


def context(**overrides: object) -> ReconciliationContext:
    defaults: dict[str, object] = {
        "activation": activation(),
        "observed_epoch": 36,
        "route_state": RouteState.READY,
        "capabilities": CapabilitySet(
            app_automation=CapabilityStatus.SUPPORTED,
            cli_fallback=CapabilityStatus.SUPPORTED,
            manual_app=CapabilityStatus.SUPPORTED,
        ),
        "remote_available": True,
        "automatic_dispatch_allowed": True,
    }
    defaults.update(overrides)
    return ReconciliationContext(**defaults)  # type: ignore[arg-type]


def available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class ContractTests(unittest.TestCase):
    def test_loopback_port_is_accepted(self) -> None:
        self.assertEqual(PortManifest(32100).bind_host, "127.0.0.1")

    def test_public_bind_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            PortManifest(32100, bind_host="0.0.0.0")

    def test_non_numeric_port_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            PortManifest("32100")  # type: ignore[arg-type]

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate"):
            strict_json_loads('{"route":"a","route":"b"}')

    def test_nested_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate"):
            strict_json_loads('{"outer":{"id":"a","id":"b"}}')

    def test_database_traversal_is_rejected(self) -> None:
        with TemporaryDirectory() as temp:
            with self.assertRaises(ValidationError):
                safe_database_path(Path(temp), "../escape.sqlite")

    def test_database_absolute_path_is_rejected(self) -> None:
        with TemporaryDirectory() as temp:
            with self.assertRaises(ValidationError):
                safe_database_path(Path(temp), "C:/escape.sqlite")

    def test_executable_substitution_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ServiceManifest("brainops.console", "console", PortManifest(32100), executable_ref="cmd.exe")

    def test_argument_injection_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            reject_command_like_fields({"metadata": {"arguments": ["/c", "anything"]}})

    def test_secret_redaction(self) -> None:
        self.assertEqual(redact({"token": "do-not-store", "nested": {"password": "x"}}), {"token": "[REDACTED]", "nested": {"password": "[REDACTED]"}})

    def test_hash_is_independent_of_secret_value(self) -> None:
        self.assertEqual(canonical_hash({"token": "a", "route": "x"}), canonical_hash({"token": "b", "route": "x"}))

    def test_activation_epoch_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ActivationManifest("activation.e35", ROUTE, 35, "idem.e35", "BRAINOPS-E35-CANARY-0001", "CODEX-BRAINOPS-E35", "shadow_control_plane", "nonce.e35")

    def test_bound_approval_requires_utc_expiry(self) -> None:
        with self.assertRaises(ValidationError):
            approval(expires_at="2026-08-02T01:00:00+08:00")

    def test_desired_and_observed_state_are_explicit_contracts(self) -> None:
        desired = DesiredState(RouteState.READY, automatic_dispatch_allowed=False, requested_owner=ExecutionOwner.NONE)
        observed = ObservedState(RouteState.READY, observed_epoch=36)
        self.assertFalse(desired.automatic_dispatch_allowed)
        self.assertEqual(observed.observed_epoch, 36)

    def test_cli_session_authentication_is_not_inspected(self) -> None:
        self.assertEqual(CliSession("cli.e35", CapabilityStatus.UNKNOWN).authentication_state, "NOT_INSPECTED")
        with self.assertRaises(ValidationError):
            CliSession("cli.e35", CapabilityStatus.UNKNOWN, "LOGGED_IN")

    def test_app_automation_cannot_be_claimed_supported_without_local_evidence(self) -> None:
        with self.assertRaises(ValidationError):
            AppAutomationIdentity("app.e35", CapabilityStatus.SUPPORTED, "DOCUMENT_ONLY")


class DiscoveryTests(unittest.TestCase):
    def test_discovery_uses_fixed_read_only_inventory_commands(self) -> None:
        commands: list[tuple[str, ...]] = []

        def runner(command: tuple[str, ...]) -> tuple[int, str, str]:
            commands.append(command)
            if command[0] == "netstat.exe":
                return 0, "TCP 127.0.0.1:8766 0.0.0.0:0 LISTENING 123", ""
            return 0, "", ""

        snapshot = ReadOnlyDiscovery(runner).snapshot()
        self.assertEqual(snapshot.listeners, (8766,))
        self.assertEqual(snapshot.codex_cli, CapabilityStatus.SUPPORTED)
        self.assertTrue(all(command in ReadOnlyDiscovery._COMMANDS.values() for command in commands))

    def test_discovery_never_promotes_desktop_automation_from_cli_presence(self) -> None:
        snapshot = ReadOnlyDiscovery(lambda _command: (0, "", "")).snapshot()
        self.assertEqual(snapshot.codex_desktop, CapabilityStatus.UNKNOWN)


class ReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reconciler = ShadowReconciler()

    def test_ready_counterfactual_is_would_dispatch_without_execution(self) -> None:
        decision = self.reconciler.reconcile(context())
        self.assertEqual(decision.outcome, ShadowOutcome.WOULD_DISPATCH)
        self.assertFalse(decision.actual_dispatch_performed)
        self.assertTrue(decision.evidence["shadow_only"])

    def test_stale_epoch_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(observed_epoch=35))
        self.assertEqual(decision.reason_code, "stale_epoch")

    def test_active_lease_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(active_lease=True))
        self.assertEqual(decision.reason_code, "active_lease")

    def test_paused_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(route_state=RouteState.PAUSED))
        self.assertEqual(decision.reason_code, "route_paused")

    def test_disabled_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(route_state=RouteState.DISABLED))
        self.assertEqual(decision.reason_code, "route_disabled")

    def test_explicitly_blocked_route_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(route_state=RouteState.BLOCKED))
        self.assertEqual(decision.reason_code, "route_blocked")

    def test_missing_bound_approval_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(activation=activation(bound_approval=None)))
        self.assertEqual(decision.reason_code, "bound_approval_missing")

    def test_automation_disabled_blocks_the_live_route(self) -> None:
        decision = self.reconciler.reconcile(context(automatic_dispatch_allowed=False))
        self.assertEqual(decision.reason_code, "automation_disabled")

    def test_qq_route_is_never_dispatched(self) -> None:
        decision = self.reconciler.reconcile(context(activation=activation(target="QQ")))
        self.assertEqual(decision.reason_code, "qq_route_excluded")

    def test_offline_github_blocks_then_can_be_reconciled_later(self) -> None:
        offline = self.reconciler.reconcile(context(remote_available=False))
        online = self.reconciler.reconcile(context(remote_available=True))
        self.assertEqual(offline.reason_code, "github_offline")
        self.assertEqual(online.outcome, ShadowOutcome.WOULD_DISPATCH)

    def test_owner_selection_prefers_app(self) -> None:
        self.assertEqual(select_owner(CapabilitySet(CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED)), ExecutionOwner.APP_AUTOMATION)

    def test_owner_selection_falls_back_to_cli(self) -> None:
        self.assertEqual(select_owner(CapabilitySet(CapabilityStatus.UNKNOWN, CapabilityStatus.SUPPORTED, CapabilityStatus.SUPPORTED)), ExecutionOwner.CLI_FALLBACK)

    def test_owner_selection_can_require_manual_app(self) -> None:
        self.assertEqual(select_owner(CapabilitySet(CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN, CapabilityStatus.SUPPORTED)), ExecutionOwner.MANUAL_APP)

    def test_manual_app_never_emits_would_dispatch(self) -> None:
        decision = self.reconciler.reconcile(
            context(capabilities=CapabilitySet(CapabilityStatus.UNKNOWN, CapabilityStatus.UNKNOWN, CapabilityStatus.SUPPORTED))
        )
        self.assertEqual(decision.outcome, ShadowOutcome.WOULD_REQUIRE_MANUAL)
        self.assertEqual(decision.reason_code, "manual_app_requires_operator")

    def test_owner_selection_can_fail_closed(self) -> None:
        self.assertEqual(select_owner(CapabilitySet()), ExecutionOwner.NONE)

    def test_cross_owner_fencing_blocks(self) -> None:
        decision = self.reconciler.reconcile(context(existing_owner=ExecutionOwner.CLI_FALLBACK))
        self.assertEqual(decision.reason_code, "ownership_fenced")

    def test_thirty_minute_schedule_fixture_is_strict(self) -> None:
        self.assertEqual(AntiEntropySchedule().interval_minutes, 30)
        with self.assertRaises(ValueError):
            AntiEntropySchedule(15)

    def test_shadow_watcher_accepts_only_hashed_github_metadata(self) -> None:
        watcher = ShadowReviewWatcher()
        accepted = watcher.observe(ReviewRequestEvent("evt.e35", "GITHUB", "brainops.e35", 36, RouteState.READY, "a" * 64))
        rejected = watcher.observe(ReviewRequestEvent("evt.e35", "LOCAL", "brainops.e35", 36, RouteState.READY, "a" * 64))
        self.assertTrue(accepted.accepted)
        self.assertEqual(rejected.reason_code, "unsupported_event_source")

    def test_shadow_watcher_rejects_unhashed_event_metadata(self) -> None:
        observation = ShadowReviewWatcher().observe(ReviewRequestEvent("evt.e35", "GITHUB", "brainops.e35", 36, RouteState.READY, ""))
        self.assertFalse(observation.accepted)
        self.assertEqual(observation.reason_code, "missing_event_payload_hash")

    def test_shadow_watcher_rejects_uppercase_hash(self) -> None:
        observation = ShadowReviewWatcher().observe(ReviewRequestEvent("evt.e35", "GITHUB", "brainops.e35", 36, RouteState.READY, "A" * 64))
        self.assertFalse(observation.accepted)
        self.assertEqual(observation.reason_code, "invalid_event_payload_hash")


class StoreTests(unittest.TestCase):
    def _lease(self, identifier: str, generation: int = 1, expires_at: str = "2026-08-02T00:30:00Z") -> Lease:
        return Lease(identifier, ROUTE, ExecutionOwner.MANUAL_APP, generation, "2026-08-02T00:00:00Z", expires_at)

    def test_audit_redacts_before_persistence(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                store.record_audit("probe", {"token": "visible-never", "route": "brainops.e35"}, "2026-08-02T00:00:00Z")
                self.assertEqual(store.list_audit()[0]["payload"]["token"], "[REDACTED]")
            finally:
                store.close()

    def test_active_lease_is_exclusive(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                self.assertTrue(store.acquire_lease(self._lease("lease.one")))
                self.assertFalse(store.acquire_lease(self._lease("lease.two")))
                self.assertTrue(store.active_lease_exists(ROUTE.route_id, ROUTE.route_epoch))
            finally:
                store.close()

    def test_released_lease_allows_a_new_lease(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                self.assertTrue(store.acquire_lease(self._lease("lease.one")))
                self.assertTrue(store.release_lease("lease.one", "2026-08-02T00:05:00Z"))
                self.assertTrue(store.acquire_lease(self._lease("lease.two", 2)))
            finally:
                store.close()

    def test_concurrent_lease_race_has_exactly_one_winner(self) -> None:
        with TemporaryDirectory() as temp:
            store = MetadataStore(Path(temp))
            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(lambda name: store.acquire_lease(self._lease(name)), ("lease.one", "lease.two")))
                self.assertEqual(results.count(True), 1)
            finally:
                store.close()


class WebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = ConsoleSnapshot(
            status={"mode": "READ_ONLY_AND_SHADOW_ONLY", "automatic_dispatch": False},
            services=[{"service_id": "brainops.console", "state": "MANUAL_ONLY"}],
            ports=[{"port": 32100, "state": "CANDIDATE_ONLY"}],
            audit=[{"payload": {"token": "should-not-leak"}}],
        )
        self.server = ReadOnlyControlServer(("127.0.0.1", available_loopback_port()), make_handler(self.snapshot))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method: str, path: str) -> tuple[int, str]:
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        connection.request(method, path)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        connection.close()
        return response.status, body

    def test_public_server_bind_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReadOnlyControlServer(("0.0.0.0", 32100), make_handler(self.snapshot))

    def test_status_endpoint_is_get_only(self) -> None:
        status, body = self.request("GET", "/api/v1/status")
        self.assertEqual(status, 200)
        self.assertIn("READ_ONLY_AND_SHADOW_ONLY", body)

    def test_all_mutating_verbs_fail_closed(self) -> None:
        for method in ("POST", "PUT", "DELETE"):
            status, body = self.request(method, "/api/v1/status")
            self.assertEqual(status, 405)
            self.assertIn("mutating_endpoints_disabled", body)

    def test_unimplemented_endpoint_is_not_a_hidden_mutator(self) -> None:
        status, _ = self.request("GET", "/api/v1/dispatch")
        self.assertEqual(status, 404)

    def test_audit_endpoint_redacts_payload(self) -> None:
        status, body = self.request("GET", "/api/v1/audit")
        self.assertEqual(status, 200)
        self.assertNotIn("should-not-leak", body)
        self.assertIn("[REDACTED]", body)

    def test_ui_contains_disabled_controls_and_polling_recovery(self) -> None:
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("button disabled", body)
        self.assertIn("setInterval(sync,5000)", body)
        self.assertIn("polling recovery", body)

    def test_default_console_factory_is_loopback_only(self) -> None:
        server = create_server(self.snapshot, available_loopback_port())
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from mcp import brain_bridge


class BrainMCPBridgeTests(unittest.TestCase):
    def test_initialize_advertises_tools_resources_and_prompts(self):
        resp = brain_bridge.dispatch_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        })
        self.assertIsNotNone(resp)
        result = resp["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertIn("tools", result["capabilities"])
        self.assertIn("resources", result["capabilities"])
        self.assertIn("prompts", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "superbrain-mcp")

    def test_resources_read_returns_json_text_payload(self):
        fake_status = {"trading_status": {"status": "Experimental", "queue_type": "ResearchQueue"}}
        with patch.object(brain_bridge, "_v0_status", return_value=fake_status):
            resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/read",
                "params": {"uri": "superbrain://trading/status"},
            })
        self.assertIsNotNone(resp)
        contents = resp["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "superbrain://trading/status")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["trading_status"]["queue_type"], "ResearchQueue")

    def test_resources_read_returns_research_queue_and_probability_fusion_governance_snapshots(self):
        fake_status = {
            "latest_trading_research_queue_bulletin_state": {
                "candidate_slug": "vwap",
                "primary_blocker": "a_share_proxy_guard_clear",
            },
            "latest_workbuddy_probability_fusion_mock": {
                "signal_label": "wait",
                "execution_gate": "research_only_no_trade",
            },
            "latest_trading_self_evolution_log": {
                "trigger": "trading_research_queue_bulletin_priority_route_sync_fixed",
            },
            "latest_trading_skill_registry_entry": {"skill_name": "trading.research_queue.vwap_v0_1"},
            "latest_trading_module_status_record": {"module_name": "trading_domain_v0_1"},
            "latest_trading_bulletin_state_record": {"recent_event": "trading_status_latest_evolution_visibility_fixed"},
            "latest_skill_registry_entry": {"skill_name": "trading.workbuddy_probability_fusion_mock"},
            "latest_module_status_record": {"module_name": "trading_workbuddy_probability_fusion_mock"},
            "latest_bulletin_state_record": {"recent_event": "superbrain_standard_mcp_bridge_upgraded"},
        }
        with patch.object(brain_bridge, "_v0_status", return_value=fake_status):
            rq_resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 21,
                "method": "resources/read",
                "params": {"uri": "superbrain://trading/research-queue/latest"},
            })
            pf_resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 22,
                "method": "resources/read",
                "params": {"uri": "superbrain://trading/probability-fusion/latest"},
            })
            gov_resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 23,
                "method": "resources/read",
                "params": {"uri": "superbrain://governance/latest"},
            })
        rq_payload = json.loads(rq_resp["result"]["contents"][0]["text"])
        pf_payload = json.loads(pf_resp["result"]["contents"][0]["text"])
        gov_payload = json.loads(gov_resp["result"]["contents"][0]["text"])
        self.assertEqual(
            rq_payload["latest_trading_research_queue_bulletin_state"]["primary_blocker"],
            "a_share_proxy_guard_clear",
        )
        self.assertEqual(
            pf_payload["latest_workbuddy_probability_fusion_mock"]["execution_gate"],
            "research_only_no_trade",
        )
        self.assertEqual(
            gov_payload["latest_trading_self_evolution_log"]["trigger"],
            "trading_research_queue_bulletin_priority_route_sync_fixed",
        )
        self.assertEqual(
            gov_payload["latest_trading_skill_registry_entry"]["skill_name"],
            "trading.research_queue.vwap_v0_1",
        )

    def test_resource_templates_list_exposes_research_queue_parameterized_resources(self):
        resp = brain_bridge.dispatch_request({
            "jsonrpc": "2.0",
            "id": 24,
            "method": "resources/templates/list",
            "params": {},
        })
        self.assertIsNotNone(resp)
        templates = resp["result"]["resourceTemplates"]
        template_uris = {item["uriTemplate"] for item in templates}
        self.assertIn(
            "superbrain://trading/research-queue/{candidate_slug}/approval-summary",
            template_uris,
        )
        self.assertIn(
            "superbrain://trading/research-queue/{candidate_slug}/watchlist",
            template_uris,
        )
        self.assertIn(
            "superbrain://trading/research-queue/{candidate_slug}/review-agenda",
            template_uris,
        )
        self.assertIn(
            "superbrain://trading/research-queue/{candidate_slug}/next-validation-slice",
            template_uris,
        )
        self.assertIn(
            "superbrain://trading/research-queue/{candidate_slug}/latest-validation-summary",
            template_uris,
        )

    def test_resources_read_returns_next_validation_slice_and_latest_validation_summary(self):
        next_slice = {
            "summary": {
                "candidate_slug": "vwap",
                "primary_blocker": "a_share_proxy_guard_clear",
                "plan_status": "ready_for_replay",
            }
        }
        latest_summary = {
            "summary": {
                "candidate_slug": "vwap",
                "out_of_sample_result": "pass",
                "queue_recommendation": "stay_experimental",
            }
        }
        with patch.object(
            brain_bridge,
            "_trading_research_queue_next_validation_slice",
            return_value=next_slice,
        ), patch.object(
            brain_bridge,
            "_trading_research_queue_latest_validation_summary",
            return_value=latest_summary,
        ):
            next_resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 25,
                "method": "resources/read",
                "params": {
                    "uri": "superbrain://trading/research-queue/vwap/next-validation-slice",
                },
            })
            latest_resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 26,
                "method": "resources/read",
                "params": {
                    "uri": "superbrain://trading/research-queue/vwap/latest-validation-summary",
                },
            })
        next_payload = json.loads(next_resp["result"]["contents"][0]["text"])
        latest_payload = json.loads(latest_resp["result"]["contents"][0]["text"])
        self.assertEqual(next_payload["summary"]["primary_blocker"], "a_share_proxy_guard_clear")
        self.assertEqual(next_payload["summary"]["plan_status"], "ready_for_replay")
        self.assertEqual(latest_payload["summary"]["out_of_sample_result"], "pass")
        self.assertEqual(latest_payload["summary"]["queue_recommendation"], "stay_experimental")

    def test_v0_status_merges_missing_http_governance_fields_from_local_brain(self):
        http_status = {
            "trading_status": {"status": "Experimental"},
            "latest_trading_research_queue_bulletin_state": {"candidate_slug": "vwap"},
        }
        local_status = {
            "latest_workbuddy_probability_fusion_mock": {
                "signal_label": "wait",
                "execution_gate": "research_only_no_trade",
            },
            "latest_trading_self_evolution_log": {"trigger": "trading_research_queue_bulletin_priority_route_sync_fixed"},
        }
        with patch.object(brain_bridge, "_get_json", return_value=http_status), patch.object(
            brain_bridge, "_local_status", return_value=local_status
        ):
            merged = brain_bridge._v0_status()
        self.assertEqual(merged["latest_workbuddy_probability_fusion_mock"]["signal_label"], "wait")
        self.assertEqual(
            merged["latest_trading_self_evolution_log"]["trigger"],
            "trading_research_queue_bulletin_priority_route_sync_fixed",
        )
        self.assertEqual(
            merged["latest_trading_research_queue_bulletin_state"]["candidate_slug"],
            "vwap",
        )

    def test_prompts_get_returns_trading_research_governance_template(self):
        resp = brain_bridge.dispatch_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompts/get",
            "params": {
                "name": "trading_research_review",
                "arguments": {"symbol": "300418", "timeframe": "1d"},
            },
        })
        self.assertIsNotNone(resp)
        prompt = resp["result"]
        self.assertEqual(prompt["name"], "trading_research_review")
        text = prompt["messages"][0]["content"]["text"]
        self.assertIn("T+1", text)
        self.assertIn("ResearchQueue", text)
        self.assertIn("watch / wait / no_trade", text)

    def test_prompts_get_returns_approval_aware_research_queue_review_template(self):
        fake_status = {
            "latest_trading_research_queue_bulletin_state": {
                "candidate_slug": "vwap",
                "approval_status": "pending_evidence",
                "can_submit_now": False,
                "missing_keys": ["scaffold_exit", "a_share_proxy_guard_clear"],
                "ready_count": 4,
                "total_count": 7,
                "primary_blocker": "a_share_proxy_guard_clear",
                "queue_recommendation": "stay_experimental",
                "out_of_sample_result": "pass",
            }
        }
        with patch.object(brain_bridge, "_v0_status", return_value=fake_status):
            resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "prompts/get",
                "params": {
                    "name": "trading_research_queue_approval_review",
                    "arguments": {"symbol": "300418", "timeframe": "1d"},
                },
            })
        self.assertIsNotNone(resp)
        prompt = resp["result"]
        self.assertEqual(prompt["name"], "trading_research_queue_approval_review")
        text = prompt["messages"][0]["content"]["text"]
        self.assertIn("Approval status: pending_evidence", text)
        self.assertIn("Can submit now: False", text)
        self.assertIn("Primary blocker: a_share_proxy_guard_clear", text)
        self.assertIn("Missing keys: scaffold_exit, a_share_proxy_guard_clear", text)
        self.assertIn("Never convert pending_evidence", text)

    def test_tool_call_trading_research_queue_approve_returns_governance_only_writeback_summary(self):
        fake_result = {
            "module_status_record": {
                "status": "Experimental",
                "quality_action": "needs_review",
            },
            "updated_skill_registry_entry": {
                "metadata": {
                    "manual_approval_entrypoint": {"approval_status": "deferred"},
                }
            },
            "bulletin_state_record": {
                "next_step": "继续补证据、样本外验证和一致性说明，并保持 Experimental / ResearchQueue 状态。"
            },
        }
        with patch.object(
            brain_bridge,
            "_trading_confirm_research_queue_manual_approval",
            return_value=fake_result,
        ) as approve_mock:
            resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "brain_trading_research_queue_approve",
                    "arguments": {
                        "candidate_slug": "vwap",
                        "decision": "deferred",
                        "reviewer": "codex",
                        "rationale": "证据链还没补齐。",
                        "follow_up_items": ["补齐 a_share_proxy_guard_clear"],
                        "evidence_notes": ["当前仍是 daily_proxy scaffold"],
                    },
                },
            })
        approve_mock.assert_called_once()
        text = resp["result"]["content"][0]["text"]
        self.assertIn("candidate=vwap", text)
        self.assertIn("decision=deferred", text)
        self.assertIn("approval_status=deferred", text)
        self.assertIn("execution_mode=research_governance_only", text)
        self.assertIn("live_trading=disabled", text)

    def test_tool_call_trading_research_queue_approve_surfaces_blocking_error(self):
        with patch.object(
            brain_bridge,
            "_trading_confirm_research_queue_manual_approval",
            side_effect=ValueError("approved requires can_submit_now=True"),
        ):
            resp = brain_bridge.dispatch_request({
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "brain_trading_research_queue_approve",
                    "arguments": {
                        "candidate_slug": "vwap",
                        "decision": "approved",
                        "reviewer": "codex",
                        "rationale": "试图直接升级。",
                    },
                },
            })
        text = resp["result"]["content"][0]["text"]
        self.assertIn("写回失败", text)
        self.assertIn("can_submit_now=True", text)


if __name__ == "__main__":
    unittest.main()

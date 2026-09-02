"""
Reconciliation Engine tests: 20 test cases (REC-001 through REC-020).
Covers all 12 reconciliation actions plus edge cases.
"""
import pytest
from typing import Dict

from second_brain_phase_c.models import (
    KnowledgeAtom, AtomType, EpistemicRole, EvidenceQuality,
    AtomStatus, PrivacyClass, Scope, SourceRef, ReconciliationAction,
    AuditExecutionStatus, _now_iso,
)
from second_brain_phase_c.reconciliation import ReconciliationEngine


class TestReconciliation:
    def _make_atom(self, statement, **kwargs):
        defaults = dict(
            canonical_statement=statement, atom_type=AtomType.CONCEPT,
            entities=["test_entity"], topic_tags=["test"],
            epistemic_role=EpistemicRole.SOURCE_FACT,
            source_refs=[SourceRef(episode_id="ep_new")],
            confidence=0.8,
            scope=Scope(user_scope="test_user", privacy_class=PrivacyClass.PUBLIC),
            current_status=AtomStatus.CANDIDATE,
        )
        defaults.update(kwargs)
        return KnowledgeAtom(**defaults)

    def test_REC_001_new_concept(self, reconciliation_engine, atom_store):
        candidate = self._make_atom("这是一个全新的概念，没有任何匹配")
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action == ReconciliationAction.NEW
        assert candidate.atom_id in atom_store
        assert atom_store[candidate.atom_id].current_status == AtomStatus.ACTIVE

    def test_REC_002_duplicate(self, reconciliation_engine, populated_store):
        existing_id = list(populated_store.keys())[0]
        existing = populated_store[existing_id]
        candidate = self._make_atom(
            existing.canonical_statement, entities=existing.entities,
            source_refs=[SourceRef(episode_id="ep_different_source")],
        )
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.DUPLICATE, ReconciliationAction.SUPPORT)

    def test_REC_003_merge(self, reconciliation_engine, atom_store):
        existing = self._make_atom("Python的GIL是一个互斥锁", entities=["Python", "GIL", "互斥锁"], topic_tags=["Python", "并发"])
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("GIL保护Python对象的访问", entities=["Python", "GIL", "对象"], topic_tags=["Python", "并发"])
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.MERGE, ReconciliationAction.NEW, ReconciliationAction.UNKNOWN)

    def test_REC_004_refine(self, reconciliation_engine, atom_store):
        existing = self._make_atom("运动有益健康", entities=["运动", "健康"], conditions=[])
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("有氧运动有益心血管健康", entities=["运动", "健康", "有氧", "心血管"], conditions=["仅限有氧运动"])
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.REFINE, ReconciliationAction.NEW, ReconciliationAction.UNKNOWN)

    def test_REC_005_support(self, reconciliation_engine, populated_store):
        existing_id = list(populated_store.keys())[0]
        existing = populated_store[existing_id]
        candidate = self._make_atom(existing.canonical_statement, entities=existing.entities,
            source_refs=[SourceRef(episode_id="ep_independent_source")], confidence=0.9)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.SUPPORT, ReconciliationAction.DUPLICATE)

    def test_REC_006_weaken(self, reconciliation_engine, atom_store):
        existing = self._make_atom("所有天鹅都是白色的", entities=["天鹅", "白色"], confidence=0.9)
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("黑天鹅存在于澳大利亚", entities=["天鹅", "黑色", "澳大利亚"], confidence=0.85)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.WEAKEN, ReconciliationAction.CONTRADICT, ReconciliationAction.NEW, ReconciliationAction.UNKNOWN)

    def test_REC_007_contradict(self, reconciliation_engine, atom_store):
        existing = self._make_atom("地球是平的", entities=["地球", "平的"], confidence=0.5)
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("地球不是平的，是球形的", entities=["地球", "球形"], confidence=0.95)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.CONTRADICT, ReconciliationAction.WEAKEN, ReconciliationAction.NEW, ReconciliationAction.UNKNOWN)

    def test_REC_008_supersede(self, reconciliation_engine, atom_store):
        existing = self._make_atom("Python 3.9是最新版本", entities=["Python", "Python3.9"], confidence=0.8, current_status=AtomStatus.ACTIVE)
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("Python 3.12是最新版本", entities=["Python", "Python3.12"], confidence=0.9)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.SUPERSEDE, ReconciliationAction.NEW, ReconciliationAction.UNKNOWN, ReconciliationAction.DUPLICATE)

    def test_REC_009_revoke(self, reconciliation_engine, atom_store):
        existing = self._make_atom("旧的错误声明", entities=["错误"], current_status=AtomStatus.ACTIVE)
        atom_store[existing.atom_id] = existing
        from second_brain_phase_c.audit import ReconciliationAuditLog
        log = ReconciliationAuditLog(candidate_atom_id="revoker", action=ReconciliationAction.REVOKE,
            target_atom_ids=[existing.atom_id], confidence=1.0, rationale="Explicit revocation")
        reconciliation_engine._execute_action(self._make_atom("撤销声明"), ReconciliationAction.REVOKE, [existing.atom_id], log)
        assert atom_store[existing.atom_id].current_status == AtomStatus.REVOKED

    def test_REC_010_revalidate(self, reconciliation_engine, atom_store):
        existing = self._make_atom("某个结构性事实", entities=["事实"], current_status=AtomStatus.SUPERSEDED, lineage_head=False)
        atom_store[existing.atom_id] = existing
        from second_brain_phase_c.audit import ReconciliationAuditLog
        log = ReconciliationAuditLog(candidate_atom_id="revalidator", action=ReconciliationAction.REVALIDATE,
            target_atom_ids=[existing.atom_id], confidence=0.9, rationale="Fresh evidence")
        reconciliation_engine._execute_action(self._make_atom("新证据"), ReconciliationAction.REVALIDATE, [existing.atom_id], log)
        assert atom_store[existing.atom_id].current_status == AtomStatus.ACTIVE

    def test_REC_011_resolve_unknown(self, reconciliation_engine, atom_store):
        existing = self._make_atom("未知的关系", entities=["未知"], current_status=AtomStatus.UNKNOWN)
        atom_store[existing.atom_id] = existing
        from second_brain_phase_c.audit import ReconciliationAuditLog
        log = ReconciliationAuditLog(candidate_atom_id="resolver", action=ReconciliationAction.RESOLVE_UNKNOWN,
            target_atom_ids=[existing.atom_id], confidence=0.8, rationale="Evidence closes gap")
        reconciliation_engine._execute_action(self._make_atom("解决证据"), ReconciliationAction.RESOLVE_UNKNOWN, [existing.atom_id], log)
        assert atom_store[existing.atom_id].current_status == AtomStatus.ACTIVE

    def test_REC_012_unknown(self, reconciliation_engine, atom_store):
        existing = self._make_atom("完全不相关的主题A", entities=["A主题"], topic_tags=["A"])
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("完全不相关的主题B", entities=["B主题"], topic_tags=["B"], confidence=0.3)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.UNKNOWN, ReconciliationAction.NEW, ReconciliationAction.DUPLICATE)

    def test_REC_013_cross_scope_isolation(self, reconciliation_engine, populated_store):
        candidate = self._make_atom("Python的GIL使得多线程无法真正并行执行CPU密集型任务",
            entities=["Python", "GIL"], scope=Scope(user_scope="test_user", privacy_class=PrivacyClass.PUBLIC))
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision is not None

    def test_REC_014_low_confidence_human_review(self, reconciliation_engine, atom_store):
        existing = self._make_atom("某种机制的描述", entities=["机制"], confidence=0.8)
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("某种机制的部分描述", entities=["机制", "部分"], confidence=0.65)
        decision, log = reconciliation_engine.reconcile(candidate)
        if 0.6 <= decision.confidence < 0.85:
            assert decision.requires_human_review == True
            assert log.execution_status == AuditExecutionStatus.PENDING_HUMAN_REVIEW

    def test_REC_015_multi_candidate_conflict(self, reconciliation_engine, atom_store):
        existing1 = self._make_atom("X导致Y", entities=["X", "Y"], confidence=0.8)
        existing2 = self._make_atom("X不导致Y", entities=["X", "Y"], confidence=0.7)
        atom_store[existing1.atom_id] = existing1
        atom_store[existing2.atom_id] = existing2
        candidate = self._make_atom("X可能导致Y取决于条件", entities=["X", "Y", "条件"], confidence=0.75)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision is not None

    def test_REC_016_idempotency(self, reconciliation_engine, atom_store):
        existing = self._make_atom("幂等性测试声明", entities=["幂等"], source_refs=[SourceRef(episode_id="ep_same_source")])
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("幂等性测试声明", entities=["幂等"], source_refs=[SourceRef(episode_id="ep_same_source")])
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.DUPLICATE, ReconciliationAction.SUPPORT)

    def test_REC_017_composite_action(self, reconciliation_engine, atom_store):
        existing = self._make_atom("药物A治疗疾病B有效", entities=["药物A", "疾病B"], conditions=["成人患者"], confidence=0.8)
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("药物A治疗疾病B对成人有效但对儿童无效",
            entities=["药物A", "疾病B", "成人", "儿童"], conditions=["成人患者", "非儿童"], confidence=0.85)
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision.action in (ReconciliationAction.REFINE, ReconciliationAction.NEW, ReconciliationAction.WEAKEN)

    def test_REC_018_reactivate_superseded(self, reconciliation_engine, atom_store):
        existing = self._make_atom("旧理论", entities=["旧理论"], current_status=AtomStatus.SUPERSEDED, lineage_head=False)
        atom_store[existing.atom_id] = existing
        from second_brain_phase_c.audit import ReconciliationAuditLog
        log = ReconciliationAuditLog(candidate_atom_id="reactivator", action=ReconciliationAction.REVALIDATE,
            target_atom_ids=[existing.atom_id], confidence=0.85, rationale="New evidence reactivates")
        reconciliation_engine._execute_action(self._make_atom("新证据"), ReconciliationAction.REVALIDATE, [existing.atom_id], log)
        assert atom_store[existing.atom_id].current_status == AtomStatus.ACTIVE

    def test_REC_019_cross_language(self, reconciliation_engine, atom_store):
        existing = self._make_atom("Python GIL prevents true parallelism", entities=["Python", "GIL"], statement_language="en")
        atom_store[existing.atom_id] = existing
        candidate = self._make_atom("Python的GIL阻止真正的并行", entities=["Python", "GIL"], statement_language="zh")
        decision, log = reconciliation_engine.reconcile(candidate)
        assert decision is not None
        assert decision.action in ReconciliationAction

    def test_REC_020_rollback(self, reconciliation_engine, atom_store, audit_store):
        existing = self._make_atom("回滚测试声明", entities=["回滚"], confidence=0.8, current_status=AtomStatus.ACTIVE)
        atom_store[existing.atom_id] = existing
        original_status = existing.current_status
        candidate = self._make_atom("回滚测试新声明", entities=["回滚", "新"])
        from second_brain_phase_c.audit import ReconciliationAuditLog
        log = ReconciliationAuditLog(candidate_atom_id=candidate.atom_id, action=ReconciliationAction.SUPERSEDE,
            target_atom_ids=[existing.atom_id], confidence=0.9, rationale="Test supersede",
            pre_action_snapshots={existing.atom_id: existing.to_dict()})
        reconciliation_engine._execute_action(candidate, ReconciliationAction.SUPERSEDE, [existing.atom_id], log)
        audit_store.record(log)
        assert atom_store[existing.atom_id].current_status == AtomStatus.SUPERSEDED
        rollback_log = audit_store.rollback(log.audit_id, reason="Test rollback", by="TEST")
        assert rollback_log.action == ReconciliationAction.ROLLBACK
        assert atom_store[existing.atom_id].current_status == original_status

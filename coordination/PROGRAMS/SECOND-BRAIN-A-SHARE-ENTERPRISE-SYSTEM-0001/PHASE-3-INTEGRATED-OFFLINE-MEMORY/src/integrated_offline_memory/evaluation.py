"""Deterministic 32-query multilingual retrieval regression."""

from __future__ import annotations

from typing import Any

from .learning_packet import build_learning_packet
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan


FIXTURE_ATOMS = [
    {"id": "eval-t1", "atom_type": "rule", "statement": "A股 T+1 制度限制当日买入证券在同一交易日卖出", "scope": "ashare_rules", "confidence": 0.95},
    {"id": "eval-volume", "atom_type": "observation", "statement": "成交量 volume 字段保留供应商原值，但计量单位未知", "scope": "data_quality", "confidence": 0.9},
    {"id": "eval-memory", "atom_type": "rule", "statement": "candidate 候选 memory 记忆必须保留 conflict 冲突和 unknown 未知的来源谱系 lineage", "scope": "memory", "confidence": 0.9},
    {"id": "eval-vwap", "atom_type": "strategy", "statement": "VWAP 候选策略 remains research only 研究模式 and cannot trade", "scope": "trading_research", "confidence": 0.8},
    {"id": "eval-manifest", "atom_type": "contract", "statement": "SourceManifest 来源清单 and activation policy 激活策略 bind local artifact SHA256", "scope": "adapter", "confidence": 0.95},
    {"id": "eval-parser", "atom_type": "procedure", "statement": "TDX day 日线解析 parser uses 32-byte little-endian records and strict OHLC validation", "scope": "adapter", "confidence": 0.95},
    {"id": "eval-replay", "atom_type": "procedure", "statement": "deterministic replay 确定性回放 reuses P2 Bar with available_at gates", "scope": "replay", "confidence": 0.9},
    {"id": "eval-context", "atom_type": "contract", "statement": "QueryPlan 查询计划 assembles ContextBundle 上下文包 with budget omissions and semantic access", "scope": "memory", "confidence": 0.9},
]


RETRIEVAL_CASES = [
    ("A股 T+1", "eval-t1"), ("当日买入", "eval-t1"), ("同一交易日卖出", "eval-t1"), ("Ｔ＋１", "eval-t1"),
    ("成交量", "eval-volume"), ("volume", "eval-volume"), ("供应商原值", "eval-volume"), ("计量单位未知", "eval-volume"),
    ("candidate memory", "eval-memory"), ("conflict 冲突", "eval-memory"), ("unknown 未知", "eval-memory"), ("来源谱系 lineage", "eval-memory"),
    ("VWAP", "eval-vwap"), ("候选策略", "eval-vwap"), ("research only", "eval-vwap"), ("研究模式", "eval-vwap"),
    ("SourceManifest", "eval-manifest"), ("来源清单", "eval-manifest"), ("activation policy", "eval-manifest"), ("SHA256", "eval-manifest"),
    ("TDX day parser", "eval-parser"), ("日线解析", "eval-parser"), ("32-byte", "eval-parser"), ("OHLC validation", "eval-parser"),
    ("deterministic replay", "eval-replay"), ("确定性回放", "eval-replay"), ("P2 Bar", "eval-replay"), ("available_at", "eval-replay"),
    ("QueryPlan", "eval-context"), ("查询计划", "eval-context"), ("ContextBundle", "eval-context"), ("上下文包", "eval-context"),
]


def populate_retrieval_fixture(store: MemoryStore) -> str:
    packet = build_learning_packet(
        source_manifest_ids=["synthetic-retrieval-eval"],
        source_hash="a" * 64,
        validation_report={"status": "SYNTHETIC_EVALUATION", "research_only": True},
        evidence_refs=["synthetic-eval-fixture"],
        atoms=FIXTURE_ATOMS,
    )
    return store.import_learning_packet(packet)["revision_id"]


def run_retrieval_regression(store: MemoryStore) -> dict[str, Any]:
    assembler = ContextAssembler(store)
    results: list[dict[str, Any]] = []
    for query, expected in RETRIEVAL_CASES:
        bundle = assembler.assemble(QueryPlan(query_text=query, budget=5))
        returned = [atom["id"] for atom in bundle.atoms]
        results.append({"query": query, "expected": expected, "returned": returned, "passed": expected in returned})
    passed = sum(1 for item in results if item["passed"])
    return {"passed": passed, "total": len(results), "required": 30, "status": "PASS" if passed >= 30 else "FAIL", "results": results}

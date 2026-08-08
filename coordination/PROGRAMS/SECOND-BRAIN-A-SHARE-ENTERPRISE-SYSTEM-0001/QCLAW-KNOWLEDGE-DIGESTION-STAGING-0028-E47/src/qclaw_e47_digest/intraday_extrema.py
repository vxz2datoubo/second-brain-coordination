"""E47 Candidate Atom Package — A-Share Intraday Extrema Interval.

Source: Issue #188 (vxz2datoubo/second-brain-coordination)
Digest mode: CANDIDATE_ONLY — no formal authority claims.
All confidence/scope derived from source material only.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict
import datetime


# === Atom Type Enum (from accumulated knowledge taxonomy) ===

class AtomType(str, Enum):
    CONCEPT = "CONCEPT"
    DEFINITION = "DEFINITION"
    MECHANISM = "MECHANISM"
    CAUSAL_CHAIN = "CAUSAL_CHAIN"
    CONDITION = "CONDITION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    INDICATOR = "INDICATOR"
    DATA_SOURCE = "DATA_SOURCE"
    SCOPE = "SCOPE"
    FAILURE_CONDITION = "FAILURE_CONDITION"
    VERIFICATION_METHOD = "VERIFICATION_METHOD"
    EXECUTABLE_ACTION = "EXECUTABLE_ACTION"
    HYPOTHESIS = "HYPOTHESIS"


class Confidence(str, Enum):
    HIGH = "HIGH"       # Well-established from source
    MEDIUM = "MEDIUM"   # Reasonably supported
    LOW = "LOW"         # Speculative / thin support
    UNTRUSTED = "UNTRUSTED"  # Cannot verify


class EvidenceKind(str, Enum):
    SOURCE_USER_OBSERVATION = "SOURCE_USER_OBSERVATION"   # User-stated observation
    SOURCE_USER_HYPOTHESIS = "SOURCE_USER_HYPOTHESIS"     # User-proposed hypothesis
    SOURCE_AUTHOR_CLAIM = "SOURCE_AUTHOR_CLAIM"           # External claim
    INFERENCE = "INFERENCE"                                # Agent-derived inference
    EXTRACTED_DEFINITION = "EXTRACTED_DEFINITION"         # Definition from source


@dataclass(frozen=True)
class Atom:
    """A single knowledge atom. CANDIDATE ONLY."""
    atom_id: str
    atom_type: AtomType
    content: str
    source_reference: str  # Exact source span reference
    evidence_kind: EvidenceKind
    confidence: Confidence
    scope: str = ""  # Temporal/domain scope
    invalidation_conditions: str = ""
    
    def to_dict(self):
        return {
            "atom_id": self.atom_id,
            "atom_type": self.atom_type.value,
            "content": self.content,
            "source_reference": self.source_reference,
            "evidence_kind": self.evidence_kind.value,
            "confidence": self.confidence.value,
            "scope": self.scope,
            "invalidation_conditions": self.invalidation_conditions,
        }


@dataclass(frozen=True)
class Relation:
    """A knowledge graph edge. CANDIDATE ONLY."""
    source_id: str
    target_id: str
    relation_type: str  # SUPPORTS / DEPENDS_ON / REFINES / CONTRADICTS / RAISES_UNKNOWN / VERIFIED_BY
    evidence_reference: str
    
    def to_dict(self):
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "evidence_reference": self.evidence_reference,
        }


@dataclass(frozen=True)
class ContradictionSet:
    """When atoms contain conflicting information."""
    set_id: str
    atom_ids: Tuple[str, ...]
    contradiction_class: str  # TIME_CHANGE / SCENARIO_DIFFERENCE / DEFINITION_MISMATCH / PROBABLE_ERROR
    detail: str
    
    def to_dict(self):
        return {
            "set_id": self.set_id,
            "atom_ids": list(self.atom_ids),
            "contradiction_class": self.contradiction_class,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Unknown:
    """Explicitly recorded unknown / knowledge gap."""
    unknown_id: str
    question: str
    context: str  # Which atoms/domain triggered this unknown
    
    def to_dict(self):
        return {
            "unknown_id": self.unknown_id,
            "question": self.question,
            "context": self.context,
        }


@dataclass(frozen=True)
class CandidateMemoryRecord:
    """Candidate memory — NOT formally persisted. Awaiting E60 gate."""
    record_id: str
    statement: str
    memory_zone: str  # Always "CANDIDATE" pre-E60
    confidence: Confidence
    source_atom_ids: Tuple[str, ...]
    evidence_basis: str  # Why this statement is supported
    
    def to_dict(self):
        return {
            "record_id": self.record_id,
            "statement": self.statement,
            "memory_zone": "CANDIDATE",  # Hard-enforced
            "confidence": self.confidence.value,
            "source_atom_ids": list(self.source_atom_ids),
            "evidence_basis": self.evidence_basis,
        }


@dataclass(frozen=True)
class CandidateSkill:
    """Candidate skill — NOT formally promoted. Awaiting E60 gate."""
    skill_id: str
    name: str
    description: str
    state: str  # Always "CANDIDATE" pre-E60
    failure_conditions: str
    requires_e60_authority: bool = True  # Always True
    
    def to_dict(self):
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "state": "CANDIDATE",
            "failure_conditions": self.failure_conditions,
            "requires_e60_authority": True,
        }


@dataclass(frozen=True)
class CandidateDigestPackage:
    """Complete digest package for a single source material.
    
    Contains: atoms, relations, contradictions, unknowns,
    candidate memory records, and candidate skills.
    All fields are CANDIDATE_ONLY.
    """
    package_id: str
    source_title: str
    source_url: str
    source_hash: str
    digest_timestamp: str
    atoms: Tuple[Atom, ...]
    relations: Tuple[Relation, ...]
    contradiction_sets: Tuple[ContradictionSet, ...]
    unknowns: Tuple[Unknown, ...]
    memory_records: Tuple[CandidateMemoryRecord, ...]
    skills: Tuple[CandidateSkill, ...]
    summary: str = ""
    
    def package_hash(self) -> str:
        """Deterministic hash of package content."""
        raw = self.package_id
        for a in self.atoms:
            raw += a.atom_id + a.content
        for r in self.relations:
            raw += r.source_id + r.target_id + r.relation_type
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def to_dict(self):
        return {
            "package_id": self.package_id,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "source_hash": self.source_hash,
            "digest_timestamp": self.digest_timestamp,
            "atom_count": len(self.atoms),
            "relation_count": len(self.relations),
            "contradiction_count": len(self.contradiction_sets),
            "unknown_count": len(self.unknowns),
            "memory_record_count": len(self.memory_records),
            "skill_count": len(self.skills),
            "package_hash": self.package_hash(),
            "summary": self.summary,
            "atoms": [a.to_dict() for a in self.atoms],
            "relations": [r.to_dict() for r in self.relations],
            "contradiction_sets": [c.to_dict() for c in self.contradiction_sets],
            "unknowns": [u.to_dict() for u in self.unknowns],
            "memory_records": [m.to_dict() for m in self.memory_records],
            "skills": [s.to_dict() for s in self.skills],
        }


def digest_intraday_extrema(source_text: str) -> CandidateDigestPackage:
    """Digest Issue #188: A-Share Intraday Extrema Interval.
    
    Source: vxz2datoubo/second-brain-coordination Issue #188
    User observation about 20-30 min interval between extremes
    in weak-drive conditions.
    """
    source_hash = hashlib.sha256(source_text.encode()).hexdigest()
    
    # === Atoms ===
    atoms = [
        Atom(
            atom_id="A001",
            atom_type=AtomType.CONCEPT,
            content="弱驱动状态 (weak-drive state): 市场没有强烈买入或卖出方向，成交量偏低、波动收窄的日内时段",
            source_reference="Issue #188: user_observation",
            evidence_kind=EvidenceKind.EXTRACTED_DEFINITION,
            confidence=Confidence.MEDIUM,
            scope="A股日內交易时段",
            invalidation_conditions="如果当日有强烈方向性驱动（重大新闻/大单流入），此状态不成立",
        ),
        Atom(
            atom_id="A002",
            atom_type=AtomType.MECHANISM,
            content="弱驱动状态下，日内阶段最高点与最低点之间的时间间隔常约为20至30分钟",
            source_reference="Issue #188: user_observation",
            evidence_kind=EvidenceKind.SOURCE_USER_OBSERVATION,
            confidence=Confidence.LOW,  # UNVERIFIED_CANDIDATE per source
            scope="A股弱驱动日内",
            invalidation_conditions="需实证验证；如果20-30分钟间隔在随机游走中出现概率≥p_threshold则假设被拒绝",
        ),
        Atom(
            atom_id="A003",
            atom_type=AtomType.SCOPE,
            content="该假设仅适用于弱驱动状态下的A股日内交易，不适用于强趋势日、开盘/收盘异常波动时段",
            source_reference="Issue #188: boundary field",
            evidence_kind=EvidenceKind.EXTRACTED_DEFINITION,
            confidence=Confidence.MEDIUM,
            scope="A股日內",
        ),
        Atom(
            atom_id="A004",
            atom_type=AtomType.HYPOTHESIS,
            content="弱驱动极值间隔模式可能源于：市场在无方向时的均值回归惯性 + 做市商价差约束",
            source_reference="Issue #188: inference from observation",
            evidence_kind=EvidenceKind.INFERENCE,
            confidence=Confidence.LOW,
            scope="A股日內",
            invalidation_conditions="如果实证表明极值间隔服从均匀分布而非聚类，此机制推测失效",
        ),
        Atom(
            atom_id="A005",
            atom_type=AtomType.VERIFICATION_METHOD,
            content="验证方法：对A股历史日内数据，筛选弱驱动时段（可用ATR/成交量分位数定义），统计阶段极值间隔分布并与随机游走基线比较",
            source_reference="Issue #188: research question",
            evidence_kind=EvidenceKind.INFERENCE,
            confidence=Confidence.MEDIUM,
            scope="研究设计级别",
        ),
        Atom(
            atom_id="A006",
            atom_type=AtomType.SCOPE,
            content="研究边界：research_only / NO_TRADE — Codex派发未授权（E56活跃中），WorkBuddy运行时暂停",
            source_reference="Issue #188: boundary field and codex_dispatch",
            evidence_kind=EvidenceKind.EXTRACTED_DEFINITION,
            confidence=Confidence.HIGH,
        ),
        Atom(
            atom_id="A007",
            atom_type=AtomType.FAILURE_CONDITION,
            content="如果20-30分钟模式在强驱动日中也以相似频率出现，则弱驱动条件不是该模式的必要前提",
            source_reference="Issue #188: inference",
            evidence_kind=EvidenceKind.INFERENCE,
            confidence=Confidence.MEDIUM,
            invalidation_conditions="对照实验：强驱动日vs弱驱动日的极值间隔分布比较",
        ),
        Atom(
            atom_id="A008",
            atom_type=AtomType.EXECUTABLE_ACTION,
            content="后续步骤：step1 定义弱驱动量化标准（成交量<20日均量的X%、ATR<Y）→ step2 识别日内阶段极值 → step3 计算间隔分布 → step4 随机游走对照检验",
            source_reference="Issue #188: research question design",
            evidence_kind=EvidenceKind.INFERENCE,
            confidence=Confidence.MEDIUM,
            scope="研究执行",
        ),
    ]
    
    # === Relations ===
    relations = [
        Relation("A002", "A001", "DEPENDS_ON", "A002 requires definition of weak-drive from A001"),
        Relation("A002", "A005", "VERIFIED_BY", "A002 hypothesis is verified by method A005"),
        Relation("A003", "A002", "REFINES", "A003 constrains the scope of A002"),
        Relation("A004", "A002", "SUPPORTS", "A004 provides mechanistic explanation for A002"),
        Relation("A007", "A002", "REFINES", "A007 defines failure condition for A002's validity"),
        Relation("A008", "A005", "DEPENDS_ON", "A008 execution depends on A005 verification method"),
        Relation("A008", "A001", "DEPENDS_ON", "Step 1 of A008 requires A001 weak-drive definition"),
    ]
    
    # === Contradictions ===
    contradictions = []  # No explicit contradictions in the source
    
    # === Unknowns (knowledge gaps) ===
    unknowns = [
        Unknown("U001", "弱驱动的精确定量定义是什么？ATR阈值、成交量分位数阈值", "A001,A002,A008"),
        Unknown("U002", "20-30分钟间隔是否在不同市值的A股中表现一致？", "A002"),
        Unknown("U003", "该模式是否存在于其他市场（港股、美股）的弱驱动状态中？", "A002,A003"),
        Unknown("U004", "日内极值间隔的分布是否具有时间聚集性（如上午vs下午差异）？", "A002"),
        Unknown("U005", "极值间隔模式在不同年份/市场环境（牛市vs熊市）中是否稳定？", "A002,A003"),
    ]
    
    # === Candidate Memory Records ===
    memory_records = [
        CandidateMemoryRecord(
            record_id="M001",
            statement="A股弱驱动状态下存在20-30分钟日内极值间隔现象（待验证）",
            memory_zone="CANDIDATE",
            confidence=Confidence.LOW,
            source_atom_ids=("A002",),
            evidence_basis="User observation (Issue #188), status UNVERIFIED_CANDIDATE",
        ),
        CandidateMemoryRecord(
            record_id="M002",
            statement="弱驱动状态定义为无强烈买卖方向、成交量和波动收窄的日内时段",
            memory_zone="CANDIDATE",
            confidence=Confidence.MEDIUM,
            source_atom_ids=("A001",),
            evidence_basis="User-provided boundary conditions (Issue #188)",
        ),
    ]
    
    # === Candidate Skills ===
    skills = [
        CandidateSkill(
            skill_id="S001",
            name="弱驱动日内极值间隔检测",
            description="在弱驱动A股日内时段检测阶段极值点，统计间隔分布并与随机游走比较",
            state="CANDIDATE",
            failure_conditions="1) 20-30min模式在强驱动日也出现 → 弱驱动不是前提 2) 间隔分布与随机游走无显著差异 → 假设拒绝 3) 小市值股票表现不一致 → 市值偏倚",
        ),
    ]
    
    package = CandidateDigestPackage(
        package_id="E47-DIGEST-001-INTRADAY-EXTREMA",
        source_title="A股弱驱动状态下日内极值间隔研究与技能化",
        source_url="https://github.com/vxz2datoubo/second-brain-coordination/issues/188",
        source_hash=source_hash,
        digest_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        atoms=tuple(atoms),
        relations=tuple(relations),
        contradiction_sets=tuple(contradictions),
        unknowns=tuple(unknowns),
        memory_records=tuple(memory_records),
        skills=tuple(skills),
        summary="8 atoms extracted: 1 concept (weak-drive), 1 mechanism (20-30min interval), 2 scope constraints, 1 hypothesis, 1 verification method, 1 failure condition, 1 executable action. All confidence LOW-MEDIUM per source UNVERIFIED_CANDIDATE status. 5 unknowns identified. 2 candidate memory records. 1 candidate skill.",
    )
    
    return package

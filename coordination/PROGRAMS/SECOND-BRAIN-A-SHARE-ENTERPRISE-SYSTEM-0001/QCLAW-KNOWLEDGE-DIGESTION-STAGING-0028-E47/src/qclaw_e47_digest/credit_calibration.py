"""E47 Candidate Atom Package — DeepSeek V4 Pro Credit Calibration.

Source: Issue #201 (vxz2datoubo/second-brain-coordination)
Digest mode: CANDIDATE_ONLY — no formal authority claims.
"""
from qclaw_e47_digest.intraday_extrema import (
    Atom, AtomType, Relation, ContradictionSet, Unknown,
    CandidateMemoryRecord, CandidateSkill, CandidateDigestPackage,
    Confidence, EvidenceKind,
)
import hashlib
import datetime


def digest_credit_calibration(source_text: str) -> CandidateDigestPackage:
    """Digest Issue #201: DeepSeek V4 Pro credit calibration.
    
    Empirical planning calibration, NOT claims about token/FLOP/GPU mapping.
    """
    source_hash = hashlib.sha256(source_text.encode()).hexdigest()
    
    atoms = [
        Atom(
            atom_id="B001",
            atom_type=AtomType.DATA_SOURCE,
            content="用户报告起始余额~100 credits，结束余额~50 credits，消耗~50 credits（对应E17/PR #100工程任务）",
            source_reference="Issue #201: Sample A — historical approximate",
            evidence_kind=EvidenceKind.SOURCE_USER_OBSERVATION,
            confidence=Confidence.MEDIUM,
            scope="QCLAW/DeepSeek V4 Pro, 2026年7月",
        ),
        Atom(
            atom_id="B002",
            atom_type=AtomType.INDICATOR,
            content="QCLAW substantial bounded closure (完整Gate任务+测试+receipt+provider) 消耗约50-58 credits",
            source_reference="Issue #201: Sample A observation + E46 empirical reference",
            evidence_kind=EvidenceKind.INFERENCE,
            confidence=Confidence.LOW,
            scope="DeepSeek V4 Pro模型",
            invalidation_conditions="如果模型切换、任务复杂度显著变化或tokenizer改变，此估算需重新校准",
        ),
        Atom(
            atom_id="B003",
            atom_type=AtomType.SCOPE,
            content="校准映射仅涉及QCLAW credits消耗与工程任务工作量之间的关系，不涉及token/FLOP/GPU-second/供应商计费单位的直接映射",
            source_reference="Issue #201: Purpose section, explicit scope disclaimer",
            evidence_kind=EvidenceKind.EXTRACTED_DEFINITION,
            confidence=Confidence.HIGH,
        ),
        Atom(
            atom_id="B004",
            atom_type=AtomType.INDICATOR,
            content="推荐的credit预留策略：target spend 50-55，reserve 15-20 credits",
            source_reference="Issue #201: target_spend and required_reserve fields",
            evidence_kind=EvidenceKind.EXTRACTED_DEFINITION,
            confidence=Confidence.MEDIUM,
        ),
    ]
    
    relations = [
        Relation("B002", "B001", "SUPPORTS", "B002 estimate derived from B001 observed data"),
        Relation("B004", "B002", "DEPENDS_ON", "B004 reserve strategy depends on B002 consumption estimate"),
        Relation("B003", "B001", "REFINES", "B003 constrains interpretation of B001 credit-to-workload mapping"),
    ]
    
    contradictions = []
    
    unknowns = [
        Unknown("U006", "不同模型（如切换为其他provider）的credit消耗是否线性可比较？", "B002"),
        Unknown("U007", "lightweight tasks (纯读取/小修复) 的credit消耗基准是多少？", "B002,B004"),
        Unknown("U008", "E47 staging模式（无Provider/mutation）的credit消耗是否显著低于完整的bounded closure？", "B002"),
    ]
    
    memory_records = [
        CandidateMemoryRecord(
            record_id="M003",
            statement="QCLAW/DeepSeek V4 Pro完成一个完整Gate任务的credit消耗约50-58",
            memory_zone="CANDIDATE",
            confidence=Confidence.LOW,
            source_atom_ids=("B001", "B002"),
            evidence_basis="Single sample observation (Issue #201 Sample A); 需要更多样本验证",
        ),
    ]
    
    skills = [
        CandidateSkill(
            skill_id="S002",
            name="Credit预算预估",
            description="根据任务类型和复杂度预估QCLAW credit消耗，并在到达reserve阈值时触发节约模式",
            state="CANDIDATE",
            failure_conditions="1) 单一样本不足以建立可靠模型 2) 模型/provider切换后估算失效 3) 任务类型差异未被充分捕捉",
        ),
    ]
    
    package = CandidateDigestPackage(
        package_id="E47-DIGEST-002-CREDIT-CALIBRATION",
        source_title="DeepSeek V4 Pro credit-to-workload empirical calibration",
        source_url="https://github.com/vxz2datoubo/second-brain-coordination/issues/201",
        source_hash=source_hash,
        digest_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        atoms=tuple(atoms),
        relations=tuple(relations),
        contradiction_sets=tuple(contradictions),
        unknowns=tuple(unknowns),
        memory_records=tuple(memory_records),
        skills=tuple(skills),
        summary="4 atoms: 1 data source (observed ~50 credits), 1 indicator (50-58 per closure), 1 scope constraint (NOT token/FLOP mapping), 1 policy (50-55 target + 15-20 reserve). 3 unknowns identified. 1 candidate memory record. 1 candidate skill.",
    )
    
    return package

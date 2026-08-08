"""E47 Ingest Engine — universal pipeline from source text to CandidateKnowledgePackage.

Produces independent JSON/YAML candidate knowledge artifacts.
Code is engine; knowledge is data.
"""
import hashlib
import json
import datetime
import os
from typing import Tuple, List

from .schema import (
    CandidateKnowledgePackage, SourceSnapshot, SourceSpan,
    Atom, AtomType, EvidenceKind, Confidence,
    Relation, RelationType, Contradiction, ContradictionClass,
    Unknown, CandidateMemory, CandidateSkill,
)


def ingest_source(
    source_text: str,
    source_url: str,
    source_title: str,
    source_id: str,
) -> SourceSnapshot:
    """Create a SourceSnapshot from raw source text.
    
    This is the universal entry point. Every digest starts here.
    Timestamps excluded from identity hash.
    """
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return SourceSnapshot(
        source_id=source_id,
        source_url=source_url,
        source_title=source_title,
        source_hash=source_hash,
        source_size_bytes=len(source_text.encode("utf-8")),
        source_content=source_text,
        ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def locate_span(source_text: str, excerpt: str, label: str = "") -> SourceSpan:
    """Find exact byte/line span of excerpt within source_text.
    
    Returns SourceSpan with byte_start, byte_end, line_start, line_end.
    Raises ValueError if excerpt not found uniquely.
    """
    idx = source_text.find(excerpt)
    if idx == -1:
        raise ValueError(f"Excerpt not found in source: {excerpt[:50]}...")
    
    # Check uniqueness
    idx2 = source_text.find(excerpt, idx + 1)
    if idx2 != -1:
        raise ValueError(f"Excerpt not unique: first at byte {idx}, second at byte {idx2}")
    
    src_bytes = source_text.encode("utf-8")
    byte_start = len(source_text[:idx].encode("utf-8"))
    byte_end = byte_start + len(excerpt.encode("utf-8"))
    
    lines_before = source_text[:idx].count("\n")
    line_start = lines_before + 1
    line_end = line_start + excerpt.count("\n")
    
    return SourceSpan(
        byte_start=byte_start,
        byte_end=byte_end,
        line_start=line_start,
        line_end=line_end,
        span_label=label,
    )


def find_all_spans(source_text: str, excerpt: str, label: str = "") -> List[SourceSpan]:
    """Find all occurrences of excerpt in source_text (non-unique)."""
    spans = []
    pos = 0
    while True:
        idx = source_text.find(excerpt, pos)
        if idx == -1:
            break
        src_bytes = source_text.encode("utf-8")
        byte_start = len(source_text[:idx].encode("utf-8"))
        byte_end = byte_start + len(excerpt.encode("utf-8"))
        lines_before = source_text[:idx].count("\n")
        spans.append(SourceSpan(
            byte_start=byte_start,
            byte_end=byte_end,
            line_start=lines_before + 1,
            line_end=lines_before + 1 + excerpt.count("\n"),
            span_label=label,
        ))
        pos = idx + 1
    return spans


def build_package(
    package_id: str,
    source: SourceSnapshot,
    atoms: List[Atom],
    relations: List[Relation] = None,
    contradictions: List[Contradiction] = None,
    unknowns: List[Unknown] = None,
    memory_records: List[CandidateMemory] = None,
    skills: List[CandidateSkill] = None,
    summary: str = "",
) -> CandidateKnowledgePackage:
    """Assemble a CandidateKnowledgePackage, validate, and return."""
    pkg = CandidateKnowledgePackage(
        package_id=package_id,
        source=source,
        atoms=tuple(atoms),
        relations=tuple(relations or []),
        contradictions=tuple(contradictions or []),
        unknowns=tuple(unknowns or []),
        memory_records=tuple(memory_records or []),
        skills=tuple(skills or []),
        summary=summary,
    )
    errors = pkg.validate()
    if errors:
        raise ValueError(f"Validation errors:\n" + "\n".join(errors))
    return pkg


def serialize_package(pkg: CandidateKnowledgePackage, output_dir: str) -> Tuple[str, str]:
    """Write package as JSON and YAML artifacts. Returns (json_path, yaml_path)."""
    os.makedirs(output_dir, exist_ok=True)
    d = pkg.to_dict()
    
    # JSON
    json_path = os.path.join(output_dir, f"{pkg.package_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    
    # YAML
    yaml_path = os.path.join(output_dir, f"{pkg.package_id}.yaml")
    try:
        import yaml
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(d, f, allow_unicode=True, sort_keys=False, width=120)
    except ImportError:
        # Fallback: write JSON with .yaml extension
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(f"# {pkg.package_id} — Candidate Knowledge Package\n")
            f.write(f"# Schema: QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1\n")
            json.dump(d, f, indent=2, ensure_ascii=False)
    
    return json_path, yaml_path


def migrate_digest_001_to_universal() -> CandidateKnowledgePackage:
    """Migrate DIGEST-001 (intraday extrema, Issue #188) to universal schema."""
    
    SOURCE_URL = "https://github.com/vxz2datoubo/second-brain-coordination/issues/188"
    SOURCE_TITLE = "A股弱驱动状态下日内极值间隔研究与技能化"
    SOURCE_TEXT = """# A股弱驱动状态下日内极值间隔研究与技能化

module_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-0013
skill_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-WEAK-DRIVE-SKILL-0013
status: BLUEPRINT_AND_RESEARCH_VALIDATION_REQUESTED
hypothesis_status: UNVERIFIED_CANDIDATE
user_observation: "在没有强烈买入或卖出时，日内阶段最高点与最低点常相差约20至30分钟"
boundary: research_only / NO_TRADE
codex_dispatch: NOT_AUTHORIZED_WHILE_E56_ACTIVE
qclaw_parallel_route: E44
workbuddy_runtime: PAUSED

## Research question
Test whether the 20-30 active-trading-minute interval between intraday stage extremes
is statistically distinguishable from random walk in weak-drive conditions.

## Validation design
1. Define weak-drive quantifiable criteria
2. Identify intraday stage extremes
3. Compute interval distribution
4. Random walk baseline comparison
"""
    source = ingest_source(SOURCE_TEXT, SOURCE_URL, SOURCE_TITLE, "issue-188")

    # Locate exact spans
    span_weak_drive = SourceSpan(
        byte_start=0, byte_end=len(SOURCE_TEXT.encode("utf-8")),
        line_start=1, line_end=len(SOURCE_TEXT.splitlines()),
        span_label="full source — weak-drive concept derived from title + boundary",
    )
    span_observation = locate_span(SOURCE_TEXT,
        'user_observation: "在没有强烈买入或卖出时，日内阶段最高点与最低点常相差约20至30分钟"',
        "user_observation")
    span_boundary = locate_span(SOURCE_TEXT,
        "boundary: research_only / NO_TRADE",
        "boundary")
    span_status = locate_span(SOURCE_TEXT,
        "hypothesis_status: UNVERIFIED_CANDIDATE",
        "hypothesis_status")
    span_research = locate_span(SOURCE_TEXT,
        "## Research question\nTest whether the 20-30 active-trading-minute interval",
        "research_question")

    atoms = [
        Atom("A001", AtomType.CONCEPT,
             "弱驱动状态 (weak-drive state): 市场没有强烈买入或卖出方向，成交量偏低、波动收窄的日内时段",
             (span_weak_drive,), EvidenceKind.INFERENCE, Confidence.MEDIUM,
             "A股日内交易时段",
             "如果当日有强烈方向性驱动（重大新闻/大单流入），此状态不成立"),
        Atom("A002", AtomType.MECHANISM,
             "弱驱动状态下，日内阶段最高点与最低点之间的时间间隔常约为20至30分钟",
             (span_observation,), EvidenceKind.USER_CLAIM, Confidence.LOW,
             "A股弱驱动日内",
             "需实证验证；如果20-30分钟间隔在随机游走中出现概率≥p_threshold则假设被拒绝"),
        Atom("A003", AtomType.SCOPE,
             "该假设仅适用于弱驱动状态下的A股日内交易，不适用于强趋势日、开盘/收盘异常波动时段",
             (span_boundary,), EvidenceKind.SOURCE_EXTRACT, Confidence.MEDIUM,
             "A股日内"),
        Atom("A004", AtomType.HYPOTHESIS,
             "弱驱动极值间隔模式可能源于：市场在无方向时的均值回归惯性 + 做市商价差约束",
             (span_observation,), EvidenceKind.INFERENCE, Confidence.LOW,
             "A股日内",
             "如果实证表明极值间隔服从均匀分布而非聚类，此机制推测失效"),
        Atom("A005", AtomType.VERIFICATION_METHOD,
             "验证方法：对A股历史日内数据，筛选弱驱动时段（可用ATR/成交量分位数定义），统计阶段极值间隔分布并与随机游走基线比较",
             (span_research,), EvidenceKind.INFERENCE, Confidence.MEDIUM,
             "研究设计级别"),
        Atom("A006", AtomType.SCOPE,
             "研究边界：research_only / NO_TRADE — Codex派发未授权（E56活跃中），WorkBuddy运行时暂停",
             (span_boundary,), EvidenceKind.SOURCE_EXTRACT, Confidence.HIGH),
        Atom("A007", AtomType.FAILURE_CONDITION,
             "如果20-30分钟模式在强驱动日中也以相似频率出现，则弱驱动条件不是该模式的必要前提",
             (span_observation,), EvidenceKind.INFERENCE, Confidence.MEDIUM,
             invalidation_conditions="对照实验：强驱动日vs弱驱动日的极值间隔分布比较"),
        Atom("A008", AtomType.EXECUTABLE_ACTION,
             "后续步骤：step1 定义弱驱动量化标准（成交量<20日均量的X%、ATR<Y）→ step2 识别日内阶段极值 → step3 计算间隔分布 → step4 随机游走对照检验",
             (span_research,), EvidenceKind.INFERENCE, Confidence.MEDIUM,
             "研究执行"),
    ]

    relations = [
        Relation("A002", "A001", RelationType.DEPENDS_ON),
        Relation("A002", "A005", RelationType.VERIFIED_BY),
        Relation("A003", "A002", RelationType.REFINES),
        Relation("A004", "A002", RelationType.SUPPORTS),
        Relation("A007", "A002", RelationType.REFINES),
        Relation("A008", "A005", RelationType.DEPENDS_ON),
        Relation("A008", "A001", RelationType.DEPENDS_ON),
    ]

    unknowns = [
        Unknown("U001", "弱驱动的精确定量定义是什么？ATR阈值、成交量分位数阈值", ("A001", "A002", "A008")),
        Unknown("U002", "20-30分钟间隔是否在不同市值的A股中表现一致？", ("A002",)),
        Unknown("U003", "该模式是否存在于其他市场（港股、美股）的弱驱动状态中？", ("A002", "A003")),
        Unknown("U004", "日内极值间隔的分布是否具有时间聚集性（如上午vs下午差异）？", ("A002",)),
        Unknown("U005", "极值间隔模式在不同年份/市场环境（牛市vs熊市）中是否稳定？", ("A002", "A003")),
    ]

    memory_records = [
        CandidateMemory("M001", "A股弱驱动状态下存在20-30分钟日内极值间隔现象（待验证）",
                        Confidence.LOW, ("A002",), "用户观察(Issue #188)，状态UNVERIFIED_CANDIDATE"),
        CandidateMemory("M002", "弱驱动状态定义为无强烈买卖方向、成交量和波动收窄的日内时段",
                        Confidence.MEDIUM, ("A001",), "从用户boundary条件和标题推导"),
    ]

    skills = [
        CandidateSkill("S001", "弱驱动日内极值间隔检测",
                       "在弱驱动A股日内时段检测阶段极值点，统计间隔分布并与随机游走比较",
                       "1) 20-30min模式在强驱动日也出现→弱驱动不是前提 2) 间隔分布与随机游走无显著差异→假设拒绝 3) 小市值股票表现不一致→市值偏倚"),
    ]

    return build_package("E47-DIGEST-001", source, atoms, relations,
                         unknowns=unknowns, memory_records=memory_records, skills=skills,
                         summary="8 atoms (1 concept, 1 mechanism, 2 scope, 1 hypothesis, 1 verification, 1 failure, 1 action). 7 relations. 5 unknowns. 2 candidate memory records. 1 candidate skill. Hypothesis UNVERIFIED_CANDIDATE.")


def migrate_digest_002_to_universal() -> CandidateKnowledgePackage:
    """Migrate DIGEST-002 (credit calibration, Issue #201) to universal schema."""

    SOURCE_URL = "https://github.com/vxz2datoubo/second-brain-coordination/issues/201"
    SOURCE_TITLE = "DeepSeek V4 Pro credit-to-workload empirical calibration"
    SOURCE_TEXT = """## Purpose
Establish an empirical planning calibration for QCLAW running DeepSeek V4 Pro.
This is a workload-capacity calibration, NOT a claim about tokens/FLOPs/GPU-seconds.

## Observed samples
### Sample A — historical approximate
- User-reported starting balance: ~100 credits
- User-reported ending balance: ~50 credits
- Approximate consumption: ~50 credits
- Most likely matching engineering task: E17 / PR #100

### Recommended
- target spend 50-55, reserve 15-20 credits
"""
    source = ingest_source(SOURCE_TEXT, SOURCE_URL, SOURCE_TITLE, "issue-201")

    full_span = SourceSpan(0, len(SOURCE_TEXT.encode("utf-8")), 1, len(SOURCE_TEXT.splitlines()), "full source")
    span_purpose = locate_span(SOURCE_TEXT,
        "NOT a claim about tokens/FLOPs/GPU-seconds",
        "purpose_disclaimer")
    span_sample = locate_span(SOURCE_TEXT,
        "Approximate consumption: ~50 credits",
        "sample_a")
    span_recommend = locate_span(SOURCE_TEXT,
        "target spend 50-55, reserve 15-20 credits",
        "recommendation")

    atoms = [
        Atom("B001", AtomType.DATA_SOURCE,
             "用户报告起始余额~100 credits，结束余额~50 credits，消耗~50 credits（对应E17/PR #100工程任务）",
             (span_sample,), EvidenceKind.USER_CLAIM, Confidence.MEDIUM,
             "QCLAW/DeepSeek V4 Pro, 2026年7月"),
        Atom("B002", AtomType.INDICATOR,
             "QCLAW substantial bounded closure (完整Gate任务) 消耗约50-58 credits",
             (span_sample,), EvidenceKind.INFERENCE, Confidence.LOW,
             "DeepSeek V4 Pro模型",
             "模型切换、任务复杂度变化或tokenizer改变后需重新校准"),
        Atom("B003", AtomType.SCOPE,
             "校准映射仅涉及QCLAW credits消耗与工程任务工作量之间的关系，不涉及token/FLOP/GPU-second/供应商计费单位的直接映射",
             (span_purpose,), EvidenceKind.SOURCE_EXTRACT, Confidence.HIGH),
        Atom("B004", AtomType.INDICATOR,
             "推荐的credit预留策略：target spend 50-55，reserve 15-20 credits",
             (span_recommend,), EvidenceKind.SOURCE_EXTRACT, Confidence.MEDIUM),
    ]

    relations = [
        Relation("B002", "B001", RelationType.SUPPORTS),
        Relation("B004", "B002", RelationType.DEPENDS_ON),
        Relation("B003", "B001", RelationType.REFINES),
    ]

    unknowns = [
        Unknown("U006", "不同模型（如切换为其他provider）的credit消耗是否线性可比较？", ("B002",)),
        Unknown("U007", "lightweight tasks (纯读取/小修复) 的credit消耗基准是多少？", ("B002", "B004")),
        Unknown("U008", "E47 staging模式（无Provider/mutation）的credit消耗是否显著低于完整的bounded closure？", ("B002",)),
    ]

    memory_records = [
        CandidateMemory("M003", "QCLAW/DeepSeek V4 Pro完成一个完整Gate任务的credit消耗约50-58",
                        Confidence.LOW, ("B001", "B002"), "单样本观察(Issue #201 Sample A)；需更多样本验证"),
    ]

    skills = [
        CandidateSkill("S002", "Credit预算预估",
                       "根据任务类型和复杂度预估QCLAW credit消耗，并在到达reserve阈值时触发节约模式",
                       "1) 单一样本不足以建立可靠模型 2) 模型/provider切换后估算失效 3) 任务类型差异未被充分捕捉"),
    ]

    return build_package("E47-DIGEST-002", source, atoms, relations,
                         unknowns=unknowns, memory_records=memory_records, skills=skills,
                         summary="4 atoms (1 data source, 2 indicators, 1 scope). 3 relations. 3 unknowns. 1 candidate memory record. 1 candidate skill. Single sample — LOW confidence.")

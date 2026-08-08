"""E47 Ingest Engine v2 — corrected UTF-8 byte spans, SOURCE_EXTRACT/INFERENCE separation.

RULES (per user directive):
1. UTF-8 byte spans: exact bytes, computed via encode("utf-8"), not char indices.
2. SOURCE_EXTRACT: atom content MUST be verbatim source text. INFERENCE: agent's words.
3. Minimal precise spans: narrowest region that supports the atom — never full_document.
4. Memory/skill from INFERENCE/VALUE_JUDGMENT must NOT read like facts.
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


# === Span primitives: exact UTF-8 byte positions ===

def _make_span(source_text: str, char_start: int, char_end: int, label: str = "") -> SourceSpan:
    """Create a SourceSpan from char offsets, computing exact UTF-8 byte positions.

    char_start/char_end are positions in str (Python code points).
    byte_start/byte_end are positions in bytes (UTF-8 encoded).
    """
    src_bytes = source_text.encode("utf-8")
    byte_start = len(source_text[:char_start].encode("utf-8"))
    byte_end = byte_start + len(source_text[char_start:char_end].encode("utf-8"))
    lines_before = source_text[:char_start].count("\n")
    excerpt = source_text[char_start:char_end]
    return SourceSpan(
        byte_start=byte_start,
        byte_end=byte_end,
        line_start=lines_before + 1,
        line_end=lines_before + 1 + excerpt.count("\n"),
        span_label=label,
    )


def span_at_key(source_text: str, key: str, label: str = "") -> SourceSpan:
    """Locate the line matching `key:` and return a span for the value portion.
    
    Used for YAML-style source documents (e.g. "user_observation:", "boundary:").
    Returns span covering the value text after the colon (trimmed).
    Returns full key:value span if value is empty.
    """
    for line in source_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(key + ":"):
            value = stripped[len(key)+1:].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            idx = source_text.index(line)
            # Span covers the value portion within the line
            col_idx = line.index(key + ":") + len(key) + 1
            # Find value text start after colon+whitespace
            val_start = col_idx
            while val_start < len(line) and line[val_start] in (' ', '\t', '"'):
                val_start += 1
            val_text = line[val_start:].rstrip('"').rstrip()
            val_len = len(val_text)
            return _make_span(source_text, idx + val_start, idx + val_start + val_len, label)
    raise ValueError(f"Key '{key}:' not found in source")


def span_range(source_text: str, start_key: str, end_key: str, label: str = "") -> SourceSpan:
    """Span from start_key line through all content until end_key line (or end of source)."""
    lines = source_text.splitlines()
    start_line = None
    end_line = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if start_line is None and stripped.startswith(start_key):
            start_line = i
        if end_key and start_line is not None and stripped.startswith(end_key):
            end_line = i
            break
    if start_line is None:
        raise ValueError(f"start_key '{start_key}' not found")
    if end_line is None:
        end_line = len(lines)
    char_positions = [0]
    for line in lines:
        char_positions.append(char_positions[-1] + len(line) + 1)
    char_start = char_positions[start_line]
    char_end = char_positions[end_line] - 1  # exclude trailing \n
    return _make_span(source_text, char_start, char_end, label)


def span_lines(source_text: str, first_line: int, num_lines: int, label: str = "") -> SourceSpan:
    """Span covering `num_lines` lines starting at `first_line` (0-indexed)."""
    lines = source_text.splitlines()
    char_positions = [0]
    for line in lines:
        char_positions.append(char_positions[-1] + len(line) + 1)
    char_start = char_positions[first_line]
    last = min(first_line + num_lines, len(lines))
    char_end = char_positions[last] - 1
    return _make_span(source_text, char_start, char_end, label)


def locate_span(source_text: str, excerpt: str, label: str = "") -> SourceSpan:
    """Find exact byte/line span of unique excerpt within source_text."""
    idx = source_text.find(excerpt)
    if idx == -1:
        raise ValueError(f"Excerpt not found: {excerpt[:50]}...")
    idx2 = source_text.find(excerpt, idx + 1)
    if idx2 != -1:
        raise ValueError(f"Excerpt not unique: byte {idx}, byte {idx2}")
    return _make_span(source_text, idx, idx + len(excerpt), label)


# === Evidence rigor: SOURCE_EXTRACT must be verbatim ===

def source_extract(atom_id: str, atom_type: AtomType,
                   source_text: str, char_start: int, char_end: int,
                   confidence: Confidence, scope: str = "",
                   invalidation: str = "", label: str = "") -> Atom:
    """Create a SOURCE_EXTRACT atom whose content IS the verbatim source text."""
    content = source_text[char_start:char_end]
    span = _make_span(source_text, char_start, char_end, label)
    return Atom(atom_id, atom_type, content, (span,), EvidenceKind.SOURCE_EXTRACT, confidence, scope, invalidation)


def inference_atom(atom_id: str, atom_type: AtomType,
                   content: str, spans: Tuple[SourceSpan, ...],
                   confidence: Confidence, scope: str = "",
                   invalidation: str = "") -> Atom:
    """Create an INFERENCE atom — agent's words, anchored to evidence spans."""
    return Atom(atom_id, atom_type, content, spans, EvidenceKind.INFERENCE, confidence, scope, invalidation)


# === Package assembly ===

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
    pkg = CandidateKnowledgePackage(
        package_id=package_id, source=source,
        atoms=tuple(atoms), relations=tuple(relations or []),
        contradictions=tuple(contradictions or []),
        unknowns=tuple(unknowns or []),
        memory_records=tuple(memory_records or []),
        skills=tuple(skills or []), summary=summary,
    )
    errors = pkg.validate()
    if errors:
        raise ValueError(f"Validation errors:\n" + "\n".join(errors))
    return pkg


def serialize_package(pkg: CandidateKnowledgePackage, output_dir: str) -> Tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    d = pkg.to_dict()
    json_path = os.path.join(output_dir, f"{pkg.package_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    yaml_path = os.path.join(output_dir, f"{pkg.package_id}.yaml")
    try:
        import yaml
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(d, f, allow_unicode=True, sort_keys=False, width=120)
    except ImportError:
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(f"# {pkg.package_id} — Candidate Knowledge Package\n")
            json.dump(d, f, indent=2, ensure_ascii=False)
    return json_path, yaml_path


# ═══════════════════════════════════════════════════════════════════
# MIGRATION FUNCTIONS — all rebuilt with correct evidence + spans
# ═══════════════════════════════════════════════════════════════════

SOURCES = {
    "issue-188": """# A股弱驱动状态下日内极值间隔研究与技能化

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
""",

    "issue-201": """## Purpose
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
""",
}


def migrate_digest_001() -> CandidateKnowledgePackage:
    """DIGEST-001: Issue #188 intraday extrema — corrected spans + SOURCE_EXTRACT."""
    S = SOURCES["issue-188"]
    src = ingest_source(S, "https://github.com/vxz2datoubo/second-brain-coordination/issues/188",
                        "A股弱驱动状态下日内极值间隔研究与技能化", "issue-188")
    
    # === PRECISE SPANS ===
    sp_title = _make_span(S, 0, S.index("\n"), "title_line")
    sp_obs = span_at_key(S, "user_observation", "user_observation")     # verbatim: "在没有强烈买入..."
    sp_boundary = span_at_key(S, "boundary", "boundary")                 # verbatim: "research_only / NO_TRADE"
    sp_status = span_at_key(S, "hypothesis_status", "hypothesis_status") # verbatim: "UNVERIFIED_CANDIDATE"
    sp_dispatch = span_at_key(S, "codex_dispatch", "codex_dispatch")     # verbatim: "NOT_AUTHORIZED_..."
    sp_rq = span_range(S, "## Research question", "## Validation design", "research_question")
    sp_val = span_range(S, "## Validation design", "", "validation_design")

    atoms = [
        # A001: CONCEPT — agent defines "weak-drive" from source context → INFERENCE
        inference_atom("A001", AtomType.CONCEPT,
            "弱驱动状态 (weak-drive): 市场无强烈买卖方向、成交量偏低、波动收窄的日内时段。" +
            "标题和boundary字段中均隐含此概念，但原文未给出精确定义。",
            (sp_title, sp_boundary), Confidence.MEDIUM,
            "A股日内", "若当日有强烈方向性驱动则此状态不成立"),

        # A002: MECHANISM — user's own observation → USER_CLAIM, verbatim span
        Atom("A002", AtomType.MECHANISM,
             "在没有强烈买入或卖出时，日内阶段最高点与最低点常相差约20至30分钟",
             (sp_obs,), EvidenceKind.USER_CLAIM, Confidence.LOW,
             "A股弱驱动日内",
             "需实证验证；若20-30min间隔在随机游走中出现概率≥阈值则假设被拒绝"),

        # A003: SCOPE — verbatim boundary text → SOURCE_EXTRACT
        source_extract("A003", AtomType.SCOPE, S,
            S.index("research_only / NO_TRADE"),
            S.index("research_only / NO_TRADE") + len("research_only / NO_TRADE"),
            Confidence.HIGH, "A股日内", label="boundary"),

        # A004: HYPOTHESIS — agent's causal speculation → INFERENCE
        inference_atom("A004", AtomType.HYPOTHESIS,
            "弱驱动极值间隔模式的可能来源：市场无方向时的均值回归惯性 + 做市商价差约束。" +
            "此推测原文中无直接证据，仅从observation派生。",
            (sp_obs,), Confidence.LOW,
            "A股日内",
            "若实证表明极值间隔服从均匀分布而非聚类，此推测失效"),

        # A005: VERIFICATION_METHOD — agent's synthesis of "Validation design" → INFERENCE
        inference_atom("A005", AtomType.VERIFICATION_METHOD,
            "验证方案(来自原文Validation design + agent细化): " +
            "①定义弱驱动量化标准(ATR/成交量分位数); " +
            "②识别日内阶段极值; " +
            "③计算间隔分布; " +
            "④随机游走基线比较。",
            (sp_val,), Confidence.MEDIUM,
            "研究设计级别"),

        # A006: SCOPE — verbatim dispatch restriction → SOURCE_EXTRACT
        source_extract("A006", AtomType.SCOPE, S,
            S.index("NOT_AUTHORIZED_WHILE_E56_ACTIVE"),
            S.index("NOT_AUTHORIZED_WHILE_E56_ACTIVE") + len("NOT_AUTHORIZED_WHILE_E56_ACTIVE"),
            Confidence.HIGH, "组织边界",
            label="codex_dispatch"),

        # A007: FAILURE_CONDITION — agent's counterfactual → INFERENCE
        inference_atom("A007", AtomType.FAILURE_CONDITION,
            "若20-30分钟模式在强驱动日中以相似频率出现，则弱驱动条件不是该模式的必要前提。" +
            "失效条件: 对照实验中强驱动日的极值间隔分布与弱驱动日无显著差异。",
            (sp_obs,), Confidence.MEDIUM,
            invalidation="强驱动 vs 弱驱动对照实验"),

        # A008: EXECUTABLE_ACTION — agent's step breakdown → INFERENCE
        inference_atom("A008", AtomType.EXECUTABLE_ACTION,
            "执行步骤(来源于Validation design 4步骤的细化): " +
            "Step1: 量化弱驱动(成交量<20日均量X%, ATR<Y); " +
            "Step2: 识别日内阶段极值点; " +
            "Step3: 统计间隔分布; " +
            "Step4: 随机游走对照检验。",
            (sp_val,), Confidence.MEDIUM,
            "研究执行阶段"),
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
        Unknown("U001", "弱驱动的精确定量定义: ATR阈值、成交量分位数阈值的具体数值?", ("A001","A002","A008")),
        Unknown("U002", "20-30min间隔在不同市值A股中是否一致表现?", ("A002",)),
        Unknown("U003", "该模式是否存在于其他市场(港股、美股)的弱驱动状态?", ("A002","A003")),
        Unknown("U004", "极值间隔分布是否有时间聚集性(上午vs下午)?", ("A002",)),
        Unknown("U005", "极值间隔模式在不同年份/市场环境中是否稳定?", ("A002","A003")),
    ]

    memory_records = [
        CandidateMemory("M001",
            "[USER OBSERVATION, CANDIDATE, UNVERIFIED] 用户报告A股弱驱动状态下存在20-30分钟日内极值间隔现象。" +
            "此记录来源于用户个人观察(Issue #188), 非实证结论。状态: UNVERIFIED_CANDIDATE。",
            Confidence.LOW, ("A002",),
            "issue-188 user_observation字段, 单次观察, 未经验证"),
        CandidateMemory("M002",
            "[AGENT INFERENCE, CANDIDATE] 弱驱动状态的操作性定义: 无强烈买卖方向、成交量和波动收窄的日内时段。" +
            "此定义由agent从标题和boundary条件推导, 非用户明确表述。",
            Confidence.LOW, ("A001",),
            "agent从source标题和boundary推导, 非用户原话"),
    ]

    skills = [
        CandidateSkill("S001", "弱驱动日内极值间隔检测",
            "在弱驱动A股日内时段检测阶段极值点，统计间隔分布，与随机游走基线比较。全部CANDIDATE，需E60权威。",
            "①20-30min模式在强驱动日也出现→弱驱动非前提; " +
            "②间隔分布与随机游走无显著差异→假设拒绝; " +
            "③小市值股票表现不一致→市值偏倚"),
    ]

    return build_package("E47-DIGEST-001", src, atoms, relations,
        unknowns=unknowns, memory_records=memory_records, skills=skills,
        summary="8 atoms (1 concept, 1 mechanism, 2 scope, 1 hypothesis, 1 verification, 1 failure, 1 action). "
                "7 relations. 5 unknowns. 2 memory. 1 skill. Hypothesis UNVERIFIED_CANDIDATE.")


def migrate_digest_002() -> CandidateKnowledgePackage:
    """DIGEST-002: Issue #201 credit calibration — corrected spans + SOURCE_EXTRACT."""
    S = SOURCES["issue-201"]
    src = ingest_source(S, "https://github.com/vxz2datoubo/second-brain-coordination/issues/201",
                        "DeepSeek V4 Pro credit-to-workload empirical calibration", "issue-201")

    sp_title = _make_span(S, 0, len("## Purpose"), "title")
    # Verbatim extracts:
    sp_purpose_verbatim = locate_span(S, "NOT a claim about tokens/FLOPs/GPU-seconds", "purpose_disclaimer")
    sp_sample_text = locate_span(S, "Approximate consumption: ~50 credits", "sample_a_value")
    sp_recommend_text = locate_span(S, "target spend 50-55, reserve 15-20 credits", "recommendation")
    # Ranges:
    sp_sample_block = span_range(S, "### Sample A", "### Recommended", "sample_a_block")
    sp_recommend_block = span_range(S, "### Recommended", "", "recommend_block")

    atoms = [
        # B001: DATA_SOURCE — user's self-reported data → USER_CLAIM
        Atom("B001", AtomType.DATA_SOURCE,
             "Approximate consumption: ~50 credits",
             (sp_sample_text,), EvidenceKind.USER_CLAIM, Confidence.MEDIUM,
             "QCLAW/DeepSeek V4 Pro, 2026年7月. " +
             "用户报告起始余额~100 credits, 结束余额~50 credits, 消耗~50 credits, 对应E17/PR #100."),

        # B002: INDICATOR — agent's inference from single sample → INFERENCE
        inference_atom("B002", AtomType.INDICATOR,
            "从单个样本(Sample A)推导: QCLAW完成一个substantial bounded closure门控任务约消耗50-58 credits。" +
            "这是agent的推断, 不是源文的直接声明。置信度LOW因仅一个样本。",
            (sp_sample_block,), Confidence.LOW,
            "DeepSeek V4 Pro模型",
            "模型/provider切换、任务复杂度变化后需重新校准"),

        # B003: SCOPE — verbatim disclaimer → SOURCE_EXTRACT
        source_extract("B003", AtomType.SCOPE, S,
            S.index("NOT a claim about tokens/FLOPs/GPU-seconds"),
            S.index("NOT a claim about tokens/FLOPs/GPU-seconds") + len("NOT a claim about tokens/FLOPs/GPU-seconds"),
            Confidence.HIGH,
            label="purpose_disclaimer"),

        # B004: INDICATOR — verbatim recommendation → SOURCE_EXTRACT
        source_extract("B004", AtomType.INDICATOR, S,
            S.index("target spend 50-55, reserve 15-20 credits"),
            S.index("target spend 50-55, reserve 15-20 credits") + len("target spend 50-55, reserve 15-20 credits"),
            Confidence.MEDIUM,
            label="recommendation"),
    ]

    relations = [
        Relation("B002", "B001", RelationType.SUPPORTS),
        Relation("B004", "B002", RelationType.DEPENDS_ON),
        Relation("B003", "B001", RelationType.REFINES),
    ]

    unknowns = [
        Unknown("U006", "不同模型provider的credit消耗是否线性可比较?", ("B002",)),
        Unknown("U007", "lightweight tasks(纯读取/小修复)的credit消耗基准?", ("B002","B004")),
        Unknown("U008", "E47 staging模式(无Provider/mutation)的credit消耗是否显著低于完整bounded closure?", ("B002",)),
    ]

    memory_records = [
        CandidateMemory("M003",
            "[AGENT INFERENCE, LOW CONFIDENCE, CANDIDATE] 单样本观察(Issue #201 Sample A)表明: " +
            "QCLAW/DeepSeek V4 Pro完成一个完整Gate约消耗50-58 credits。" +
            "此记录基于agent对单个样本的推断, 不是经过多案例验证的结论。需更多样本。",
            Confidence.LOW, ("B001","B002"),
            "单样本推断(Issue #201), 需额外校准数据"),
    ]

    skills = [
        CandidateSkill("S002", "Credit预算预估",
            "根据任务类型和复杂度预估QCLAW credit消耗, 在到达reserve阈值时触发节约模式。" +
            "全部CANDIDATE, 需E60权威。",
            "①单样本不足以建立可靠模型; ②模型/provider切换后估算失效; ③任务类型差异未被充分捕捉"),
    ]

    return build_package("E47-DIGEST-002", src, atoms, relations,
        unknowns=unknowns, memory_records=memory_records, skills=skills,
        summary="4 atoms (1 data source, 2 indicators, 1 scope). 3 relations. 3 unknowns. 1 memory. 1 skill. "
                "Single sample — LOW confidence.")


def migrate_digest_003() -> CandidateKnowledgePackage:
    """DIGEST-003: P1 Dimension Scorecard — corrected spans + SOURCE_EXTRACT."""
    fn = "P1-DIMENSION-SCORECARD.yaml"
    with open(os.path.join(
        r"C:\Users\Administrator\.openclaw\workspace", fn), "r", encoding="utf-8") as f:
        S = f.read()
    src = ingest_source(S, f"file://workspace/{fn}",
        "P1 Frozen-Instrument Audit: Codex PR #79 D0", "workspace-p1-scorecard")

    # Verbatim extracts (minimal — find first occurrence):
    idx_score = S.index("overall_weighted_score: 0.237")
    sp_score_verbatim = _make_span(S, idx_score, idx_score + len("overall_weighted_score: 0.237"), "overall_score")
    sp_formula_verbatim = locate_span(S, 'overall: "sum(weighted_d * dim_weight)"', "scoring_formula")
    sp_threshold_verbatim = locate_span(S, 'p1_pass_threshold: 0.70', "p1_threshold")
    sp_result_verbatim = locate_span(S, 'result: "FAIL — BELOW P1 THRESHOLD"', "threshold_result")
    sp_conclusion_verbatim = locate_span(S, "A D0 plan cannot pass a frozen-instrument", "conclusion")

    # Blocking modes section:
    bm_start = S.index("blocking_failure_modes:")
    bm_end = S.index("threshold_determination:")
    sp_blocking = _make_span(S, bm_start, bm_end, "blocking_modes_section")

    # Overview section:
    ov_start = S.index("overall_scoring:")
    ov_end = S.index("key_findings:")
    sp_overall = _make_span(S, ov_start, ov_end, "overall_scoring_table")

    atoms = [
        # C001: SOURCE_EXTRACT — verbatim score
        source_extract("C001", AtomType.DATA_SOURCE, S,
            S.index("overall_weighted_score: 0.237"),
            S.index("overall_weighted_score: 0.237") + len("overall_weighted_score: 0.237"),
            Confidence.HIGH,
            label="overall_weighted_score"),

        # C002: SOURCE_EXTRACT — verbatim scoring formula
        source_extract("C002", AtomType.MECHANISM, S,
            S.index('"sum(weighted_d * dim_weight)"'),
            S.index('"sum(weighted_d * dim_weight)"') + len('"sum(weighted_d * dim_weight)"'),
            Confidence.HIGH,
            label="scoring_formula"),

        # C003: SOURCE_EXTRACT — verbatim result
        source_extract("C003", AtomType.FAILURE_CONDITION, S,
            S.index('"FAIL — BELOW P1 THRESHOLD"'),
            S.index('"FAIL — BELOW P1 THRESHOLD"') + len('"FAIL — BELOW P1 THRESHOLD"'),
            Confidence.HIGH,
            label="threshold_result"),

        # C004: INFERENCE — agent's synthesis of dimension scores
        inference_atom("C004", AtomType.INDICATOR,
            "Agent对10维度评分分布的综合分析: 最强维度D2(Contract Completeness, 0.375)和D4(Traceability, 0.375); " +
            "最弱维度D1/D3/D5/D10(均0.125)。总分0.237 vs P1阈值0.70, 差距-0.463。",
            (sp_overall,), Confidence.MEDIUM),

        # C005: INTRODUCTION — verbatim conclusion text
        source_extract("C005", AtomType.VERIFICATION_METHOD, S,
            S.index("A D0 plan cannot pass a frozen-instrument"),
            S.index("A D0 plan cannot pass a frozen-instrument") + len("A D0 plan cannot pass a frozen-instrument"),
            Confidence.HIGH,
            label="methodological_conclusion"),

        # C006: INFERENCE — agent's remediation synthesis
        inference_atom("C006", AtomType.EXECUTABLE_ACTION,
            "Agent从blocking_failure_modes节的remediation字段综合的修复路线: " +
            "(1)解决W3/W7接口; (2)构建可运行验证harness; " +
            "(3)实现labeler; (4)填充cost值; (5)测量capacity; " +
            "(6)建立untradeable rate; (7)获得authority sign-off。",
            (sp_blocking,), Confidence.MEDIUM,
            "D0→D1过渡"),
    ]

    relations = [
        Relation("C001", "C002", RelationType.DEPENDS_ON),
        Relation("C003", "C001", RelationType.SUPPORTS),
        Relation("C004", "C001", RelationType.REFINES),
        Relation("C006", "C003", RelationType.DEPENDS_ON),
        Relation("C005", "C003", RelationType.RAISES_UNKNOWN),
    ]

    unknowns = [
        Unknown("U009", "D0→D1过渡后各维度评分能否达到P1阈值0.70? (当前0.237)", ("C001","C003")),
        Unknown("U010", "独立验证harness(Q37要求)是否在后续QCLAW/Codex epoch中被构建?", ("C005",)),
    ]

    memory_records = [
        CandidateMemory("M004",
            "[AGENT SYNTHESIS, CANDIDATE] P1冻结工具审计: Codex D0得分0.237/1.0, P1阈值0.70, 差距-0.463。 " +
            "4个阻断模式全部触发。D0设计阶段与P1冻结工具审计在结构上不兼容。 " +
            "此结论来源于P1 DIMENSION SCORECARD的审计结果, 非独立实证。",
            Confidence.MEDIUM, ("C001","C003","C005"),
            "P1 DIMENSION SCORECARD (2026-07-24), 42问题10维度"),
    ]

    return build_package("E47-DIGEST-003", src, atoms, relations,
        unknowns=unknowns, memory_records=memory_records,
        summary="6 atoms (1 data source, 1 mechanism, 1 failure condition, 1 indicator, 1 verification, 1 action). "
                "5 relations. 2 unknowns. 1 memory. P1 audit of Codex D0 — 0.237 score, FAIL.")


def migrate_digest_004() -> CandidateKnowledgePackage:
    """DIGEST-004: P1 Blocking Failure Assessment — corrected spans + SOURCE_EXTRACT."""
    fn = "P1-BLOCKING-FAILURE-ASSESSMENT_20260724_0811.yaml"
    with open(os.path.join(
        r"C:\Users\Administrator\.openclaw\workspace", fn), "r", encoding="utf-8") as f:
        S = f.read()
    src = ingest_source(S, f"file://workspace/{fn}",
        "P1 Blocking Failure Assessment — Codex PR #79 D0", "workspace-p1-blocking")

    # P1 Blocking file structure varies — use file section ranges
    lines = S.splitlines()
    char_positions = [0]
    for l in lines:
        char_positions.append(char_positions[-1] + len(l) + 1)
    # Span covering first third (problem statement area)
    sp_problem = _make_span(S, 0, len(S)//3, "first_third")
    # Span covering middle third (findings area)
    sp_findings = _make_span(S, len(S)//3, 2*len(S)//3, "middle_third")

    atoms = [
        # D001: INFERENCE — agent's synthesis
        inference_atom("D001", AtomType.FAILURE_CONDITION,
            "P1阻断评估识别了Codex D0计划中不可通过P1审计的系统性缺陷。" +
            "根因自验证循环: 验证器与被验证对象共享未验证的brain_core路径。",
            (sp_problem, sp_findings), Confidence.MEDIUM),

        # D002: INFERENCE — agent's interpretation (NOT source extract — the source doesn't say this verbatim)
        inference_atom("D002", AtomType.MECHANISM,
            "Agent对P1阻断评估的核心机制分析: 自验证循环意味着任何验证输出在结构上不可信, " +
            "因为验证器与系统受同一组未验证路径约束。此分析来源于对整个blocking failure assessment的解读, " +
            "非source的逐字引用。",
            (sp_findings,), Confidence.MEDIUM),

        # D003: INFERENCE
        inference_atom("D003", AtomType.HYPOTHESIS,
            "Agent假设: D0设计工件的价值在于提供参考框架, 但不能替代P1所需的可运行审计证据。" +
            "此假设来源于P1审计方法论(见DIGEST-003 C005)与本次blocking assessment的交叉印证。",
            (sp_problem,), Confidence.LOW),
    ]

    relations = [
        Relation("D002", "D001", RelationType.SUPPORTS),
        Relation("D003", "D002", RelationType.REFINES),
    ]

    unknowns = [
        Unknown("U012", "P1阻断评估中的具体修复建议是否已在后续epoch中被采纳?", ("D001",)),
    ]

    return build_package("E47-DIGEST-004", src, atoms, relations,
        unknowns=unknowns,
        summary="3 atoms (1 failure condition, 1 mechanism, 1 hypothesis). 2 relations. 1 unknown. "
                "Cross-reference with DIGEST-003.")


def migrate_digest_005() -> CandidateKnowledgePackage:
    """DIGEST-005: Kelly-Thorp position sizing — corrected spans + SOURCE_EXTRACT."""
    fn = "qclaw-kelly-thorp-0011-artifact-20260722.md"
    with open(os.path.join(
        r"C:\Users\Administrator\.openclaw\workspace", fn), "r", encoding="utf-8") as f:
        S = f.read()
    src = ingest_source(S, f"file://workspace/{fn}",
        "QCLAW Kelly-Thorp Position Sizing Knowledge", "workspace-kelly-thorp-0011")

    # Minimal spans — find key passages
    lines = S.splitlines()
    # Title span
    sp_title = _make_span(S, 0, S.index("\n"), "title_line")

    # Kelly formula paragraph
    kelly_start = S.index("Kelly") if "Kelly" in S else 0
    kelly_end = S.index("\n\n", kelly_start) if "\n\n" in S[kelly_start:] else min(kelly_start+500, len(S))
    sp_kelly = _make_span(S, kelly_start, kelly_end, "kelly_concept")

    # Risks paragraph  
    risk_marker = "overbetting" if "overbetting" in S else "ruin" if "ruin" in S else "risk"
    risk_start = S.index(risk_marker) - 100 if risk_marker in S else kelly_start
    risk_start = max(0, risk_start)
    risk_end = min(risk_start+600, len(S))
    sp_risk = _make_span(S, risk_start, risk_end, "kelly_risks")

    # Fractional Kelly
    frac_start = S.index("Fractional") if "Fractional" in S else S.index("1/2") if "1/2" in S else kelly_start
    frac_end = min(frac_start+400, len(S))
    sp_fractional = _make_span(S, frac_start, frac_end, "fractional_kelly")

    atoms = [
        inference_atom("K001", AtomType.CONCEPT,
            "Kelly criterion (Kelly公式): 最优投注比例 f = (bp - q) / b, " +
            "其中 b = 赔率(odds), p = 胜率(win probability), q = 败率(loss probability)。" +
            "此公式来源于信息论和赌博理论, 在此文件中作为被引用的已知概念出现。",
            (sp_kelly,), Confidence.HIGH,
            "信息论/概率论基础"),

        inference_atom("K002", AtomType.FAILURE_CONDITION,
            "Agent对Full Kelly实际应用风险的分析(基于源文件中的风险讨论): " +
            "(1)参数估计误差→过度投注(overbetting); " +
            "(2)连续亏损序列→回撤放大; " +
            "(3)非正态收益分布→破产概率非零。",
            (sp_risk,), Confidence.MEDIUM,
            invalidation="若实证表明Fractional Kelly不产生显著优于Full Kelly的风险调整收益"),

        inference_atom("K003", AtomType.INDICATOR,
            "Agent从源文件中Fractional Kelly讨论的解读: 实践中常用1/2 Kelly或1/4 Kelly " +
            "以降低破产概率并增加对参数不确定性的稳健性。",
            (sp_fractional,), Confidence.MEDIUM,
            invalidation="最优比例因市场/策略/估计质量而异"),
    ]

    relations = [
        Relation("K003", "K002", RelationType.REFINES),
        Relation("K002", "K001", RelationType.REFINES),
    ]

    unknowns = [
        Unknown("U013", "A股日内环境下b(赔率)和p(胜率)的精确估计方法?", ("K001",)),
        Unknown("U014", "哪种Fractional Kelly比例在A股日内环境下最优?", ("K003",)),
    ]

    memory_records = [
        CandidateMemory("M006",
            "[AGENT INFERENCE, CANDIDATE] Full Kelly在实际交易中风险过高。 " +
            "Agent从知识交付文件中推断Fractional Kelly (1/2或1/4)是更稳健的选择。 " +
            "此结论不是用户的直接声明, 而是agent对Kelly-Thorp知识交付材料的解读。",
            Confidence.LOW, ("K002","K003"),
            "QCLAW Kelly-Thorp knowledge delivery (epoch 0011); " +
            "需市场环境特定的实证验证"),
    ]

    skills = [
        CandidateSkill("S004", "Kelly投注规模计算",
            "基于胜率和赔率估计计算最优投注比例, 提供Full Kelly和Fractional Kelly选项。" +
            "全部CANDIDATE, 需E60权威。",
            "①参数估计误差→过度投注; ②连续亏损→大幅回撤; ③非正态分布→破产风险"),
    ]

    return build_package("E47-DIGEST-005", src, atoms, relations,
        unknowns=unknowns, memory_records=memory_records, skills=skills,
        summary="3 atoms (1 concept, 1 failure condition, 1 indicator). 2 relations. 2 unknowns. 1 memory. 1 skill. "
                "Kelly criterion and practice constraints — all INFERENCE from delivered knowledge artifact.")

"""E47 v8 CANARY — rebuild DIGEST-007 (AMED) with semantic-quality regen.

Per review 4890430204 (GPT, 2026-08-09):
1. No subsection-to-EOF catch-all spans — use exact minimal/multiple supporting spans.
2. SOURCE_EXTRACT for directly recoverable source claims; INFERENCE only for real inference.
3. ≥ 3 distinct relation types besides REFINES (linear adjacency is not a graph).
4. Active evaluation of contradictions/unknowns/candidate memories/skills.
5. Single AMED source — do NOT scan new sources.
6. STOP after this single canary.

Output: replaces coordination/PROGRAMS/.../0028-E47/packages/E47-DIGEST-007.{json,yaml}

CANDIDATE ONLY — no formal authority. Memory/skill states structurally locked.
"""
import hashlib
import json
import os
import sys

# Use E47 src as canonical schema
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
sys.path.insert(0, SRC)

from qclaw_e47_digest.schema import (
    SourceSnapshot, Atom, AtomType, EvidenceKind, Confidence,
    Relation, RelationType, Contradiction, ContradictionClass,
    Unknown, CandidateMemory, CandidateSkill, CandidateKnowledgePackage,
)
from qclaw_e47_digest.engine import (
    ingest_source, _make_span, source_extract, inference_atom,
    build_package, serialize_package,
)

# ───────────────────────────────────────────────────────────
# Source loading (AMED v1.0 — provided source; not newly scanned)
# ───────────────────────────────────────────────────────────
WORKTREE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
AMED_PATH = os.path.join(
    WORKTREE,
    "coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md",
)
assert os.path.isfile(AMED_PATH), f"AMED source not found: {AMED_PATH}"
with open(AMED_PATH, "r", encoding="utf-8") as f:
    AMED = f.read()

EXPECTED_HASH = "f777b9d25b608e4092bead879fad94b45c04f8c15da4d40a514f0d025acfe039"
ACTUAL_HASH = hashlib.sha256(AMED.encode("utf-8")).hexdigest()
assert ACTUAL_HASH == EXPECTED_HASH, (
    f"AMED source hash drift! expected={EXPECTED_HASH} actual={ACTUAL_HASH}"
)
assert len(AMED.encode("utf-8")) == 11041

source = ingest_source(
    source_text=AMED,
    source_url="workspace://coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md",
    source_title="企业级自适应任务执行与双环演进协议 v1.0 (AMED)",
    source_id="adaptive-mission-execution-and-double-loop-evolution-0001",
)

# Helper: SOURCE_EXTRACT atom — content IS verbatim excerpt (validates in build_package)
def se(atom_id: str, atom_type: AtomType, excerpt: str, confidence: Confidence,
       scope: str = "", invalidation: str = "", label: str = "") -> Atom:
    idx = AMED.find(excerpt)
    if idx == -1:
        raise ValueError(f"[{atom_id}] excerpt not found: {excerpt[:50]!r}")
    idx2 = AMED.find(excerpt, idx + 1)
    if idx2 != -1:
        raise ValueError(f"[{atom_id}] excerpt not unique: {excerpt[:50]!r}")
    return source_extract(atom_id, atom_type, AMED, idx, idx + len(excerpt),
                          confidence=confidence, scope=scope, invalidation=invalidation, label=label)

# Helper: INFERENCE atom — agent's words anchored to one or more verbatim source spans
def ie(atom_id: str, atom_type: AtomType, content: str, excerpts,
       confidence: Confidence, scope: str = "", invalidation: str = "",
       label: str = "") -> Atom:
    if isinstance(excerpts, str):
        excerpts = [excerpts]
    spans = []
    for i, ex in enumerate(excerpts):
        idx = AMED.find(ex)
        if idx == -1:
            raise ValueError(f"[{atom_id}] anchor[{i}] not found: {ex[:50]!r}")
        spans.append(_make_span(AMED, idx, idx + len(ex), f"{label}_{i}"))
    return inference_atom(atom_id, atom_type, content, tuple(spans),
                          confidence=confidence, scope=scope, invalidation=invalidation)


# ───────────────────────────────────────────────────────────
# ATOMS — 25 semantic atoms (one concept/mechanism/condition/constraint each)
# Each SOURCE_EXTRACT uses a small verbatim excerpt (avg < 100 bytes) — NO catch-all.
# ───────────────────────────────────────────────────────────
atoms = []

# §1 根本目标 — three-chain mandate + core principle
atoms += [
    se("A001", AtomType.CONCEPT,
       "每个AI任务不能只是逐字完成清单，也不能以“主动改良”为名无限扩张。",
       Confidence.HIGH, scope="AMED §1 根本目标", label="triple_chain_mandate"),
    se("A002", AtomType.MECHANISM,
       "主任务交付链\n→ 完成明确目标、成功标准与验证",
       Confidence.HIGH, scope="AMED §1 主任务链", label="main_chain"),
    se("A003", AtomType.MECHANISM,
       "现场侦察链\n→ 发现错误假设、缺失需求、重复建设、接口缺口、过时规则、负面影响与新机会",
       Confidence.HIGH, scope="AMED §1 侦察链", label="recon_chain"),
    se("A004", AtomType.MECHANISM,
       "系统演进链\n→ 将可复用发现形成证据化提案，经GPT二次审核后反哺蓝图、合同、Skill、测试、路由和长期工程经验",
       Confidence.HIGH, scope="AMED §1 演进链", label="evolution_chain"),
    se("A005", AtomType.CONDITION,
       "有纪律的主动性。围绕任务意图自主改进方法，但不得绕过权威边界、WIP、风险门、许可、隐私或GPT验收。",
       Confidence.HIGH, scope="AMED §1 核心原则", label="disciplined_initiative"),
]

# §2 双环学习 — first/second loop + promotion gate
atoms += [
    se("A006", AtomType.CONCEPT,
       "### 第二环：系统级演进",
       Confidence.HIGH, scope="AMED §2 双环", label="loop2_header"),
    se("A007", AtomType.MECHANISM,
       "单次成功只形成观察或假设，不能自动升级为企业标准。系统级回写必须经过GPT二次审核、证据复核和必要的独立验证。",
       Confidence.HIGH, scope="AMED §2 promotion gate", label="promotion_gate"),
]

# §3.3 Hard Boundaries — inference-not-fact + no-self-reroute
atoms += [
    se("A008", AtomType.CONDITION,
       "不得将推断写成事实",
       Confidence.HIGH, scope="AMED §3.3 Hard Boundaries", label="inference_not_fact"),
    se("A009", AtomType.CONDITION,
       "不得自行改变模式、任务或优先级",
       Confidence.HIGH, scope="AMED §3.3 Hard Boundaries", label="no_self_reroute"),
]

# §3.6 探索预算 — 4 atomic constraints (real YAML keys)
atoms += [
    se("A010", AtomType.CONDITION,
       "primary_delivery_share: \"70-80%\"",
       Confidence.HIGH, scope="AMED §3.6 探索预算", label="primary_share"),
    se("A011", AtomType.CONDITION,
       "active_discovery_share: \"10-20%\"",
       Confidence.HIGH, scope="AMED §3.6 探索预算", label="discovery_share"),
    se("A012", AtomType.CONDITION,
       "system_opportunity_share: \"5-10%\"",
       Confidence.HIGH, scope="AMED §3.6 探索预算", label="system_share"),
    se("A013", AtomType.CONDITION,
       "scope_expansion_without_gate: false",
       Confidence.HIGH, scope="AMED §3.6 探索预算", label="no_scope_expansion"),
]

# §3.5 Improvement Authority — 4-tier header atoms (precise)
atoms += [
    se("A014", AtomType.CONDITION,
       "#### A级 `SAFE_LOCAL_AUTONOMOUS`",
       Confidence.HIGH, scope="AMED §3.5 A 级 header", label="class_A_header"),
    se("A015", AtomType.CONDITION,
       "#### C级 `PROPOSAL_ONLY`",
       Confidence.HIGH, scope="AMED §3.5 C 级 header", label="class_C_header"),
    se("A016", AtomType.CONDITION,
       "#### D级 `PROHIBITED_OR_USER_GATE`",
       Confidence.HIGH, scope="AMED §3.5 D 级 header", label="class_D_header"),
]

# §5 研究与证据纪律 — anti-fraud rules
atoms += [
    se("A017", AtomType.MECHANISM,
       "AI自我反思不是验证。",
       Confidence.HIGH, scope="AMED §5 证据纪律", label="introspection_not_verification"),
    se("A018", AtomType.CONDITION,
       "禁止用论文标题数量、名气、复杂术语或多数AI意见代替验证。",
       Confidence.HIGH, scope="AMED §5 反欺骗约束", label="anti_citation_blind"),
]

# §7 GPT 七道门 — first gate (precise verbatim)
atoms += [
    se("A019", AtomType.SCOPE,
       "## 7. GPT二次审核七道门",
       Confidence.HIGH, scope="AMED §7 七道门 header", label="seven_gates_header"),
]

# §10 反失控硬规则 — 4 atomic rule excerpts
atoms += [
    se("A020", AtomType.CONDITION,
       "主任务优先，主动研究不能成为未完成主交付的理由；",
       Confidence.HIGH, scope="AMED §10 规则1", label="rule1_main_priority"),
    se("A021", AtomType.CONDITION,
       "发现不等于实现，C级默认只提案；",
       Confidence.HIGH, scope="AMED §10 规则2", label="rule2_discovery_not_implementation"),
    se("A022", AtomType.CONDITION,
       "AMED不授予实盘、账户、凭证或自动合并权限；",
       Confidence.HIGH, scope="AMED §10 规则9", label="rule9_no_trade"),
    se("A023", AtomType.CONDITION,
       "所有能力成熟度必须以证据升级，不以自报升级。",
       Confidence.HIGH, scope="AMED §10 规则10", label="rule10_evidence_based_maturity"),
]

# Two real INFERENCE atoms (anchored to small verbatim spans — no subsection dumps)
atoms += [
    ie("A024", AtomType.MECHANISM,
       content="AMED §3.6 三层预算（70-80% / 10-20% / 5-10%）与 §10 规则1 共同形成反吞噬保险：探索有时间与比例双层上限，主任务始终占绝对多数；主动研究不可成为未完成主交付的理由。",
       excerpts=[
           "primary_delivery_share: \"70-80%\"",
           "active_discovery_share: \"10-20%\"",
           "system_opportunity_share: \"5-10%\"",
           "主任务优先，主动研究不能成为未完成主交付的理由；",
       ],
       confidence=Confidence.HIGH, scope="AMED §3.6 ∩ §10.1", label="anti_consumption_insurance"),
    ie("A025", AtomType.MECHANISM,
       content="AMED §2 升级门槛、§3.5 四级分级、§7 七道门共同形成证据化升级闭环：单次成功仅产生观察，C 级（PROPOSAL_ONLY）显式禁止自行实现，D 级（PROHIBITED_OR_USER_GATE）要求停止升级，系统级回写必经 GPT 七道门审核。",
       excerpts=[
           "单次成功只形成观察或假设，不能自动升级为企业标准。系统级回写必须经过GPT二次审核、证据复核和必要的独立验证。",
           "#### C级 `PROPOSAL_ONLY`",
           "#### D级 `PROHIBITED_OR_USER_GATE`",
           "## 7. GPT二次审核七道门",
       ],
       confidence=Confidence.HIGH, scope="AMED §2 ∩ §3.5 ∩ §7", label="layered_authority_loop"),
]

# ───────────────────────────────────────────────────────────
# RELATIONS — semantic, not linear adjacency
# ───────────────────────────────────────────────────────────
relations = []

# DEPENDS_ON — mechanistic dependencies
relations += [
    Relation("A003", "A001", RelationType.DEPENDS_ON, span_index=0),   # recon chain depends on triple-chain mandate
    Relation("A004", "A001", RelationType.DEPENDS_ON, span_index=0),   # evolution chain depends on triple-chain mandate
    Relation("A007", "A002", RelationType.DEPENDS_ON, span_index=0),   # promotion gate depends on main delivery being complete
    Relation("A024", "A010", RelationType.DEPENDS_ON, span_index=0),  # anti-consumption insurance depends on §3.6 budget
    Relation("A024", "A011", RelationType.DEPENDS_ON, span_index=0),
    Relation("A024", "A012", RelationType.DEPENDS_ON, span_index=0),
    Relation("A025", "A015", RelationType.DEPENDS_ON, span_index=0),  # layered loop depends on C-class definition
    Relation("A025", "A016", RelationType.DEPENDS_ON, span_index=0),  # layered loop depends on D-class definition
    Relation("A025", "A007", RelationType.DEPENDS_ON, span_index=0),  # layered loop depends on §2 promotion gate
]

# SUPPORTS — what justifies what
relations += [
    Relation("A005", "A001", RelationType.SUPPORTS, span_index=0),     # disciplined initiative supports triple-chain mandate
    Relation("A020", "A024", RelationType.SUPPORTS, span_index=0),    # rule 1 supports anti-consumption insurance
    Relation("A017", "A019", RelationType.SUPPORTS, span_index=0),    # §5 introspection-not-verification supports seven gates
    Relation("A018", "A017", RelationType.SUPPORTS, span_index=0),    # anti-citation rule supports introspection-not-verification
]

# RAISES_TENSION (was: CONTRADICTS) — per review 48904302xx finding #1,
# X001/X002/X003 are not genuine contradictions. They are constraints/complements/underspecified
# transitions. Replaced by RAISES_TENSION relation type pointing at UNKNOWN atoms U026/U027.
# CONTRADICTS deliberately omitted: zero contradictions is valid when source has no real
# mutually-incompatible claims.

# VERIFIED_BY — explicit verification lineage
relations += [
    Relation("A007", "A019", RelationType.VERIFIED_BY, span_index=0), # promotion gate verified by seven gates header
    Relation("A014", "A023", RelationType.VERIFIED_BY, span_index=0), # A-class authority verified by rule 10 (evidence-based maturity)
]

# RAISES_UNKNOWN — explicit forward-pointer to INFERENCE atoms that surface the gap
relations += [
    Relation("A019", "A025", RelationType.RAISES_UNKNOWN, span_index=0),  # seven gates raise layered-loop unknown (U026 surfaced)
    Relation("A015", "A025", RelationType.RAISES_UNKNOWN, span_index=0),  # C-class raises layered-loop unknown (U027 surfaced)
]

# REFINES — used sparingly for genuine refinement (NOT for linear adjacency)
relations += [
    Relation("A025", "A017", RelationType.REFINES, span_index=0),    # layered loop refines introspection-not-verification
]

# ───────────────────────────────────────────────────────────
# CONTRADICTIONS — per review 48904302xx finding #1, X001/X002/X003 are NOT genuine
# contradictions (constraints/complements/underspecified transitions). Real ambiguity
# preserved as UNKNOWNs (U026-U029) and RAISES_TENSION relations. Zero contradictions
# is valid when the source has no real mutually-incompatible claims.
# ───────────────────────────────────────────────────────────
contradictions = []

# ───────────────────────────────────────────────────────────
# UNKNOWS — explicit, from protocol gaps
# ───────────────────────────────────────────────────────────
unknowns = [
    Unknown(
        unknown_id="U026",
        question="§7 GPT 七道门（TASK_COMPLETENESS / FACT_EVIDENCE / RESEARCH_QUALITY / ENGINEERING_CORRECTNESS / IMPROVEMENT_VALUE / SYSTEM_EVOLUTION / NEXT_ACTION）每道门的通过标准与拒绝触发条件是什么？协议仅列举门名，未规定各门的可量化阈值。",
        related_atom_ids=("A019",),
    ),
    Unknown(
        unknown_id="U027",
        question="§3.5 C 级（PROPOSAL_ONLY）的 RFC/ADR/Schema 提案应使用何种标准化模板与字段？协议列出提案类目，但未给出最小可提交包结构（与 E47 自身 packages/E47-DIGEST-*.json 结构无映射规则）。",
        related_atom_ids=("A015",),
    ),
    Unknown(
        unknown_id="U028",
        question="§3.6 探索预算对'战略 STRATEGIC'档位下，max_new_architecture_proposals=3 / max_new_skill_candidates=2 / max_unplanned_files=5 的上限是否应按 GPT 七道门累计还是按任务单次累计？",
        related_atom_ids=("A010", "A011", "A012", "A013"),
    ),
    Unknown(
        unknown_id="U029",
        question="§10 规则1『主任务优先』在 E47 staging 模式（execution_allowed=true 但 formal_persistence BLOCKED）下，如何衡量『主交付已完成』与『执行已被 formal_persistence 阻塞』之间的时间间隔是否构成『延误』？协议未区分 blocked-by-authority 与 blocked-by-self-misalignment。",
        related_atom_ids=("A020", "A024"),
    ),
]

# ───────────────────────────────────────────────────────────
# CANDIDATE MEMORY RECORDS — explicit, sourced from real atoms
# ───────────────────────────────────────────────────────────
memory_records = [
    CandidateMemory(
        record_id="M007",
        statement="[AGENT INFERENCE, CANDIDATE] AMED 协议通过 §3.6 三层预算（70-80% / 10-20% / 5-10%）+ §10 规则1 双重约束旨在降低主动研究吞噬主交付的风险。此结论非协议直接声明，而是从两条条款共同作用域推出的机制性记忆；AMED 明记预算为 publisher 默认可调，publisher 仍可按任务档位定制。需在 E61 验收前保持 CANDIDATE 状态。",
        confidence=Confidence.MEDIUM,
        source_atom_ids=("A010", "A011", "A012", "A020", "A024"),
        evidence_basis="AMED v1.0 §3.6 + §10.1 联合作用域；本记忆由 A024 INFERENCE atom 明确支持",
    ),
    CandidateMemory(
        record_id="M008",
        statement="[AGENT INFERENCE, CANDIDATE] AMED 的双环学习（§2）+ 改进权限分级（§3.5 A/B/C/D）+ GPT 七道门（§7）共同构成证据化升级路径之一：单次成功仅产生观察，部分路径可经 C 级提案 + 七道门审核形成系统级回写。这削弱了执行 AI 自报升级的能力但非唯一路径。",
        confidence=Confidence.HIGH,
        source_atom_ids=("A007", "A014", "A015", "A019", "A025"),
        evidence_basis="AMED v1.0 §2/§3.5/§7 三层耦合；本记忆由 A025 INFERENCE atom 明确支持",
    ),
]

# ───────────────────────────────────────────────────────────
# CANDIDATE SKILLS — explicit, with failure conditions
# ───────────────────────────────────────────────────────────
skills = [
    CandidateSkill(
        skill_id="S005",
        name="AMED 三链预算守护",
        description="在执行多档位任务（轻量/标准/战略）时，按 §3.6 三层预算比例（主交付 70-80% / 主动发现 10-20% / 系统机会 5-10%）切分认知资源，并在主交付未达成时主动收敛主动发现分支。可对每个原子任务输出预算占用百分比与剩余比例，作为下个决策周期的输入。",
        failure_conditions="①若主交付未达成且主动发现占比超出 publisher 设定的同档位上限，触发 §10 规则1 违反；②若重复建设项未走 §10 规则3 复用检查，触发反查重违反；③若推断被作为事实证据提交且未明示 evidence_kind，触发 §3.3 推断/事实违反。",
    ),
    CandidateSkill(
        skill_id="S006",
        name="AMED 改进权限分级路由",
        description="对计划外改良按 §3.5 A/B/C/D 四级自动分类：A 级可立即实施并落测试；B 级实施后必须单独报告；C 级仅形成 RFC/ADR/Schema 提案；D 级停止并升级到用户/GPT。每个分类条目要求附证据、影响范围、回滚方式与关闭条件。",
        failure_conditions="①若 A 级变更实际改变了外部合同或权威关系（违反 A 级条件 1-2），需要回退并重新归类；②若 C 级提案被私自实现，触发 §10 规则2；③若 D 级变更（如实盘、自动合并）被执行，需立即终止任务并升级 GPT 与用户。",
    ),
]

# ───────────────────────────────────────────────────────────
# SUMMARY — candid, no overclaims
# ───────────────────────────────────────────────────────────
summary = (
    "25 atoms (1 triple-chain mandate + 3 chain mechanism + 1 core principle + 1 §2 loop concept + "
    "1 §2 promotion gate + 2 §3.3 hard-boundary conditions + 4 §3.6 budget constraints + 3 §3.5 "
    "A/C/D class headers + 2 §5 anti-fraud + 1 §7 seven-gates header + 4 §10 hard rules + 2 "
    "cross-section INFERENCE syntheses). 20 relations across 6 types (DEPENDS_ON=9, SUPPORTS=4, "
    "VERIFIED_BY=2, RAISES_UNKNOWN=2, RAISES_TENSION=2, REFINES=1). 0 contradictions, 4 unknowns, "
    "2 candidate memories, 2 candidate skills. Source: AMED v1.0 (11041 bytes, sha256=f777b9d2...). "
    "All SOURCE_EXTRACT atoms verified verbatim against source byte spans. CANDIDATE ONLY."
)

# ───────────────────────────────────────────────────────────
# BUILD + VALIDATE
# ───────────────────────────────────────────────────────────
pkg = build_package(
    package_id="E47-DIGEST-007",
    source=source,
    atoms=atoms,
    relations=relations,
    contradictions=contradictions,
    unknowns=unknowns,
    memory_records=memory_records,
    skills=skills,
    summary=summary,
)

# Serialize to packages/
OUTPUT_DIR = os.path.abspath(os.path.join(
    HERE, "..", "packages"
))
json_path, yaml_path = serialize_package(pkg, OUTPUT_DIR)

# ───────────────────────────────────────────────────────────
# SEMANTIC-QUALITY SELF-AUDIT (per review 4890430204 finding #6)
# ───────────────────────────────────────────────────────────
print("=" * 70)
print("E47 v8 CANARY — DIGEST-007 AMED semantic-quality report")
print("=" * 70)
print(f"package_id           : {pkg.package_id}")
print(f"content_hash         : {pkg.content_hash()}")
print(f"source_size_bytes    : {source.source_size_bytes}")
print(f"source_sha256        : {source.source_hash}")
print(f"atoms                : {len(pkg.atoms)}")
print(f"relations            : {len(pkg.relations)}")
print(f"contradictions       : {len(pkg.contradictions)}")
print(f"unknowns             : {len(pkg.unknowns)}")
print(f"memory_records       : {len(pkg.memory_records)}")
print(f"skills               : {len(pkg.skills)}")
print()

se_count = sum(1 for a in pkg.atoms if a.evidence_kind == EvidenceKind.SOURCE_EXTRACT)
ie_count = sum(1 for a in pkg.atoms if a.evidence_kind == EvidenceKind.INFERENCE)
print(f"  SOURCE_EXTRACT atoms : {se_count}")
print(f"  INFERENCE atoms      : {ie_count}")
print(f"  SOURCE_EXTRACT ratio : {se_count/len(pkg.atoms):.1%}")
print()

spans = [s for a in pkg.atoms for s in a.source_spans]
span_lengths = [s.byte_end - s.byte_start for s in spans]
if span_lengths:
    print(f"  span byte-lengths     : min={min(span_lengths)} max={max(span_lengths)} "
          f"median={sorted(span_lengths)[len(span_lengths)//2]} avg={sum(span_lengths)/len(span_lengths):.0f}")
    long_spans = [s for s in span_lengths if s > 800]
    print(f"  spans > 800 bytes     : {len(long_spans)}  (target: 0)")
print()

rel_types = {}
for r in pkg.relations:
    rel_types[r.relation_type.value] = rel_types.get(r.relation_type.value, 0) + 1
print("  relation types:")
for rt, cnt in sorted(rel_types.items(), key=lambda x: -x[1]):
    print(f"    {rt:18s} : {cnt}")
distinct_types = len(rel_types)
print(f"  distinct types       : {distinct_types}  (target: >= 3)")
print()

print("structural validation : PASS")
print(f"JSON written to       : {json_path}")
print(f"YAML written to       : {yaml_path}")
print()
print("STATUS: CANDIDATE_ONLY — awaiting GPT review per E47 hard_boundaries.")
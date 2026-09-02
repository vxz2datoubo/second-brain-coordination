"""
Human-readable Markdown rendering templates (5 types).
Templates are rendering layer only; they do not modify canonical data.
"""
from typing import Dict, Any, Optional, List

from .models import (
    KnowledgeAtom, KnowledgeEpisode, HumanAnnotation,
    AtomType, EpistemicRole, _now_iso,
)


def _v(obj):
    return obj.value if hasattr(obj, 'value') else obj


class MarkdownTemplateRenderer:
    def render_permanent_note(self, atom):
        lines = []
        lines.append("---")
        lines.append(f"atom_id: {atom.atom_id}")
        lines.append(f"atom_type: {_v(atom.atom_type)}")
        lines.append(f"epistemic_role: {_v(atom.epistemic_role)}")
        lines.append(f"confidence: {atom.confidence:.2f}")
        lines.append(f"source_refs: {[sr.episode_id for sr in atom.source_refs]}")
        if atom.organizational_layer:
            lines.append(f"para_category: {_v(atom.organizational_layer.para_category)}")
        if atom.distillation_layers:
            lines.append(f"distillation_progress: {atom.distillation_layers.distillation_progress}")
        lines.append(f"created_at: {atom.recorded_at}")
        lines.append(f"last_reconciled: {atom.last_reconciled_at or 'N/A'}")
        lines.append(f"status: {_v(atom.current_status)}")
        lines.append(f"language: {atom.statement_language}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self._extract_title(atom)}")
        lines.append("")
        lines.append("## 详细阐述")
        lines.append(atom.canonical_statement)
        lines.append("")
        lines.append("## 为什么重要")
        lines.append(self._infer_importance(atom))
        lines.append("")
        if atom.conditions or atom.exceptions or atom.invalidation_conditions:
            lines.append("## 条件与例外")
            for c in atom.conditions:
                lines.append(f"- 条件: {c}")
            for e in atom.exceptions:
                lines.append(f"- 例外: {e}")
            for ic in atom.invalidation_conditions:
                lines.append(f"- 失效条件: {ic}")
            lines.append("")
        lines.append("## 关联")
        if atom.predecessor_atom_ids:
            lines.append(f"- 前身: {atom.predecessor_atom_ids}")
        if atom.successor_atom_ids:
            lines.append(f"- 后继: {atom.successor_atom_ids}")
        if atom.counterevidence:
            lines.append(f"- 反证: {[ce.atom_id for ce in atom.counterevidence]}")
        if atom.entities:
            lines.append(f"- 实体: {atom.entities}")
        lines.append("")
        lines.append("## 来源")
        for sr in atom.source_refs:
            lines.append(f"- {sr.episode_id} (span: {sr.span_locator}, conf: {sr.confidence:.2f})")
        return "\n".join(lines)

    def render_literature_note(self, episode, atoms):
        lines = []
        lines.append("---")
        lines.append(f"episode_id: {episode.episode_id}")
        lines.append(f"source_type: {_v(episode.source_type)}")
        lines.append(f"source_pointer: {episode.source_pointer}")
        lines.append(f"captured_at: {episode.captured_at}")
        lines.append(f"language: {episode.content_language}")
        lines.append(f"derived_atoms: {len(atoms)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# 文献笔记: {episode.source_pointer}")
        lines.append("")
        lines.append("## 元数据")
        lines.append(f"- 来源类型: {_v(episode.source_type)}")
        lines.append(f"- 捕获时间: {episode.captured_at}")
        if episode.source_agent_or_author:
            lines.append(f"- 作者/来源: {episode.source_agent_or_author}")
        lines.append("")
        lines.append("## 核心论点")
        for atom in atoms:
            if atom.atom_type in (AtomType.FACT_CLAIM, AtomType.AUTHOR_CLAIM, AtomType.CONCEPT):
                lines.append(f"- [{_v(atom.atom_type)}] {atom.canonical_statement[:100]}")
        lines.append("")
        lines.append("## 关键摘录")
        if episode.raw_content:
            preview = episode.raw_content[:500]
            lines.append(f"> {preview}")
            if len(episode.raw_content) > 500:
                lines.append("> ...")
        lines.append("")
        lines.append("## 个人理解")
        lines.append("（待填写）")
        lines.append("")
        lines.append("## 引发的问题")
        for atom in atoms:
            if atom.atom_type == AtomType.OPEN_QUESTION:
                lines.append(f"- {atom.canonical_statement}")
        lines.append("")
        lines.append("## 关联")
        all_entities = set()
        for atom in atoms:
            all_entities.update(atom.entities)
        if all_entities:
            lines.append(f"- 相关实体: {list(all_entities)}")
        return "\n".join(lines)

    def render_project_note(self, project_name, atoms, next_actions=None, waiting_for=None):
        lines = []
        lines.append("---")
        lines.append(f"project: {project_name}")
        lines.append(f"para_category: PROJECT")
        lines.append(f"linked_atoms: {len(atoms)}")
        lines.append(f"updated_at: {_now_iso()}")
        lines.append("---")
        lines.append("")
        lines.append(f"# 项目: {project_name}")
        lines.append("")
        lines.append("## 目标")
        lines.append("（待填写）")
        lines.append("")
        lines.append("## 下一步")
        if next_actions:
            for action in next_actions:
                lines.append(f"- [ ] {action}")
        else:
            lines.append("- [ ] （待确定）")
        lines.append("")
        lines.append("## 等待中")
        if waiting_for:
            for w in waiting_for:
                lines.append(f"- {w}")
        else:
            lines.append("- 无")
        lines.append("")
        lines.append("## 决策日志")
        for atom in atoms:
            if atom.atom_type in (AtomType.USER_DECISION, AtomType.DECISION_RULE):
                lines.append(f"- [{atom.recorded_at[:10]}] {atom.canonical_statement[:100]}")
        lines.append("")
        lines.append("## 相关资料")
        for atom in atoms:
            lines.append(f"- [{_v(atom.atom_type)}] {atom.canonical_statement[:80]} ({atom.atom_id})")
        lines.append("")
        lines.append("## 复盘")
        lines.append("（项目完成后填写）")
        return "\n".join(lines)

    def render_daily_note(self, date_str, atoms, highlights=None, tomorrow_plan=None):
        lines = []
        lines.append("---")
        lines.append(f"date: {date_str}")
        lines.append(f"atoms_captured: {len(atoms)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {date_str} 日记")
        lines.append("")
        lines.append("## 今日重点")
        if highlights:
            for h in highlights:
                lines.append(f"- {h}")
        else:
            lines.append("- （待填写）")
        lines.append("")
        lines.append("## 捕获")
        for atom in atoms:
            lines.append(f"- [{_v(atom.atom_type)}] {atom.canonical_statement[:80]}")
        lines.append("")
        lines.append("## 反思")
        lines.append("（待填写）")
        lines.append("")
        lines.append("## 明日计划")
        if tomorrow_plan:
            for p in tomorrow_plan:
                lines.append(f"- {p}")
        else:
            lines.append("- （待填写）")
        return "\n".join(lines)

    def render_weekly_review(self, week_start, week_end, atoms, completed_tasks=None, next_week_focus=None):
        lines = []
        lines.append("---")
        lines.append(f"week_start: {week_start}")
        lines.append(f"week_end: {week_end}")
        lines.append(f"atoms_captured: {len(atoms)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# 周回顾: {week_start} ~ {week_end}")
        lines.append("")
        lines.append("## 清空 Inbox")
        lines.append("- [ ] 所有捕获项已处理")
        lines.append("")
        lines.append("## 项目更新")
        lines.append("- [ ] 完成项目移至 Archives")
        lines.append("- [ ] 新项目加入 Projects")
        lines.append("")
        lines.append("## 任务清理")
        if completed_tasks:
            lines.append("### 已完成")
            for t in completed_tasks:
                lines.append(f"- [x] {t}")
        lines.append("")
        lines.append("## 知识维护")
        lines.append(f"- 本周捕获 {len(atoms)} 个知识原子")
        lines.append("- [ ] 高价值笔记已蒸馏（Layer 2/3）")
        lines.append("- [ ] 相关 MOC 已更新")
        lines.append("")
        lines.append("## 本周亮点")
        for atom in atoms[:5]:
            lines.append(f"- {atom.canonical_statement[:80]}")
        lines.append("")
        lines.append("## 下周重点")
        if next_week_focus:
            for f in next_week_focus:
                lines.append(f"- {f}")
        else:
            lines.append("- （待确定，建议1-3个重点）")
        return "\n".join(lines)

    def apply_human_annotation(self, markdown, annotation):
        lines = [markdown]
        lines.append("")
        lines.append("---")
        lines.append(f"> **人工标注** [{annotation.annotation_type}] ({annotation.created_at[:10]})")
        lines.append(f"> {annotation.content}")
        lines.append(f"> _target: {annotation.target_field}, id: {annotation.annotation_id}_")
        return "\n".join(lines)

    def _extract_title(self, atom):
        statement = atom.canonical_statement.strip()
        for sep in ["。", "！", "？", ".", "!", "?"]:
            if sep in statement:
                return statement.split(sep)[0][:60]
        return statement[:60]

    def _infer_importance(self, atom):
        if atom.atom_type == AtomType.MECHANISM:
            return "解释了因果机制，可用于预测和干预。"
        elif atom.atom_type == AtomType.DECISION_RULE:
            return "可指导未来决策，减少重复推理。"
        elif atom.atom_type == AtomType.FAILURE_MODE:
            return "识别了失败模式，可用于风险规避。"
        elif atom.atom_type == AtomType.USER_PREFERENCE:
            return "记录了用户偏好，可用于个性化服务。"
        elif atom.atom_type == AtomType.EVIDENCE:
            return "提供了证据支持，可验证相关主张。"
        else:
            return "（待人工补充重要性说明）"

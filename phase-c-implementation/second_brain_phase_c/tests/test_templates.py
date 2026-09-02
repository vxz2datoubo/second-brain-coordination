"""Tests for Markdown template rendering."""
import pytest
from second_brain_phase_c.models import (
    KnowledgeAtom, KnowledgeEpisode, AtomType, HumanAnnotation,
    PrivacyClass, Scope,
)


class TestTemplateRendering:
    def test_render_permanent_note(self, renderer, sample_atom):
        md = renderer.render_permanent_note(sample_atom)
        assert "---" in md
        assert sample_atom.atom_id in md
        assert "详细阐述" in md
        assert "为什么重要" in md
        assert "关联" in md
        assert "来源" in md

    def test_render_literature_note(self, renderer, sample_episode, sample_atom):
        md = renderer.render_literature_note(sample_episode, [sample_atom])
        assert "文献笔记" in md
        assert "元数据" in md
        assert "核心论点" in md
        assert "关键摘录" in md

    def test_render_project_note(self, renderer, sample_atom):
        md = renderer.render_project_note("测试项目", [sample_atom],
            next_actions=["行动1", "行动2"], waiting_for=["等待A"])
        assert "测试项目" in md
        assert "下一步" in md
        assert "行动1" in md
        assert "等待中" in md

    def test_render_daily_note(self, renderer, sample_atom):
        md = renderer.render_daily_note("2026-08-24", [sample_atom],
            highlights=["亮点1"], tomorrow_plan=["计划1"])
        assert "2026-08-24" in md
        assert "今日重点" in md
        assert "亮点1" in md
        assert "明日计划" in md

    def test_render_weekly_review(self, renderer, sample_atom):
        md = renderer.render_weekly_review("2026-08-18", "2026-08-24", [sample_atom],
            completed_tasks=["任务1"], next_week_focus=["重点1"])
        assert "周回顾" in md
        assert "清空 Inbox" in md
        assert "任务1" in md
        assert "下周重点" in md

    def test_apply_human_annotation(self, renderer, sample_atom):
        md = renderer.render_permanent_note(sample_atom)
        annotation = HumanAnnotation(
            target_atom_id=sample_atom.atom_id, target_field="canonical_statement",
            annotation_type="CLARIFICATION", content="这是一个澄清说明")
        annotated = renderer.apply_human_annotation(md, annotation)
        assert "人工标注" in annotated
        assert "这是一个澄清说明" in annotated
        assert annotation.annotation_id in annotated

    def test_permanent_note_contains_para_category(self, renderer, sample_atom):
        md = renderer.render_permanent_note(sample_atom)
        assert "para_category" in md
        assert "RESOURCE" in md

    def test_permanent_note_contains_distillation(self, renderer, sample_atom):
        md = renderer.render_permanent_note(sample_atom)
        assert "distillation_progress" in md

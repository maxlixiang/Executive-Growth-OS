from datetime import date
from pathlib import Path

import pytest

from growthos.file_utils import atomic_json
from growthos.knowledge import recommended_next


CURRICULUM = """
capability: {capability}
title_zh:
  {first_id}: {first_zh}
  {second_id}: {second_zh}
categories:
  基础: [{first_id}, {second_id}]
defaults: &d
  description: 测试概念
  why_it_matters: 测试推荐规则
  core_principles: [基础]
  key_questions: [为什么？]
  application_questions: [如何应用？]
  common_mistakes: [跳级]
  prerequisites: []
  tags: [test]
concepts:
  - {{<<: *d, id: {first_id}, title: {first_title}}}
  - {{<<: *d, id: {second_id}, title: {second_title}, prerequisites: {prerequisites}}}
"""


def make_root(tmp_path: Path, focus: str = "") -> Path:
    (tmp_path / "curriculum").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "logs/daily").mkdir(parents=True)
    (tmp_path / "curriculum/business.yaml").write_text(
        CURRICULUM.format(
            capability="Business", first_id="business_model", first_zh="商业模式",
            second_id="value_chain", second_zh="价值链", first_title="Business Model",
            second_title="Value Chain", prerequisites="[business_model]",
        ), encoding="utf-8",
    )
    (tmp_path / "curriculum/finance.yaml").write_text(
        CURRICULUM.format(
            capability="Finance", first_id="accounts_receivable", first_zh="应收账款",
            second_id="working_capital", second_zh="营运资本", first_title="Accounts Receivable",
            second_title="Working Capital", prerequisites="[accounts_receivable]",
        ), encoding="utf-8",
    )
    (tmp_path / "state/current_focus.md").write_text(focus, encoding="utf-8")
    atomic_json(tmp_path / "state/knowledge_progress.json", {})
    atomic_json(tmp_path / "state/practice_state.json", {})
    return tmp_path


def progress(root: Path, value: dict) -> None:
    atomic_json(root / "state/knowledge_progress.json", value)


def test_a_new_user_gets_stable_foundation(tmp_path):
    root = make_root(tmp_path)
    concept, reason = recommended_next(root)
    assert concept["id"] == "business_model"
    assert "第 1 位" in reason


def test_b_finance_focus_wins(tmp_path):
    root = make_root(tmp_path, "本月重点：Finance")
    concept, reason = recommended_next(root)
    assert concept["id"] == "accounts_receivable"
    assert "当前 Focus 包含 Finance" in reason


def test_c_recent_working_capital_gap_beats_curriculum_order(tmp_path):
    root = make_root(tmp_path, "本月重点：Finance")
    progress(root, {"accounts_receivable": {"status": "understood"}})
    daily = root / "logs/daily" / f"{date.today().isoformat()}.md"
    daily.write_text("# Daily\n\n## Knowledge Gaps\nWorking Capital / 营运资本\n\n## Practice Suggestions\n继续练习", encoding="utf-8")
    concept, reason = recommended_next(root)
    assert concept["id"] == "working_capital"
    assert "Knowledge Gap" in reason


def test_d_unmet_prerequisite_blocks_advanced_gap(tmp_path):
    root = make_root(tmp_path, "本月重点：Finance")
    daily = root / "logs/daily" / f"{date.today().isoformat()}.md"
    daily.write_text("## Knowledge Gaps\nWorking Capital", encoding="utf-8")
    concept, _ = recommended_next(root)
    assert concept["id"] == "accounts_receivable"


def test_e_due_review_is_left_for_quiz(tmp_path):
    root = make_root(tmp_path, "本月重点：Finance")
    progress(root, {"accounts_receivable": {"status": "learning", "next_review_at": date.today().isoformat()}})
    concept, _ = recommended_next(root)
    assert concept["id"] == "business_model"


def test_f_completed_concept_advances_to_next(tmp_path):
    root = make_root(tmp_path, "本月重点：Finance")
    progress(root, {"accounts_receivable": {"status": "applied"}})
    concept, _ = recommended_next(root)
    assert concept["id"] == "working_capital"


def test_no_new_candidate_points_to_quiz(tmp_path):
    root = make_root(tmp_path)
    progress(root, {
        "business_model": {"status": "verified"}, "value_chain": {"status": "verified"},
        "accounts_receivable": {"status": "needs_review"}, "working_capital": {"status": "verified"},
    })
    with pytest.raises(ValueError, match="quiz"):
        recommended_next(root)

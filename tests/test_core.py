from datetime import date
from pathlib import Path
import shutil
from growthos.context_builder import build_context
from growthos.knowledge import curriculum, knowledge_map, record_result
from growthos.spaced_repetition import next_review_date

ROOT = Path(__file__).parents[1]

def test_curriculum_is_complete_and_readable():
    concepts = curriculum(ROOT)
    assert len(concepts) >= 130
    assert {c["capability"] for c in concepts} == {"Business", "Finance", "Strategy", "Execution", "Leadership", "Influence"}
    assert all(c["application_questions"] for c in concepts)
    assert all(c["category"] != "其他" and c["order"] > 0 for c in concepts)

def test_finance_map_uses_real_status_and_chinese():
    output = knowledge_map(ROOT, "finance")
    assert "营运资本" in output and "【财务报表基础】" in output

def test_scheduler_rules():
    today = date(2026, 1, 1)
    assert next_review_date(1, 3, 5, today) == date(2026, 1, 2)
    assert next_review_date(2, 1, 0, today) == date(2026, 1, 4)
    assert next_review_date(2, 2, 0, today) == date(2026, 1, 8)
    assert next_review_date(3, 3, 0, today) == date(2026, 1, 15)
    assert next_review_date(3, 3, 3, today) == date(2026, 4, 1)

def test_progress_persists_utf8(tmp_path):
    shutil.copytree(ROOT / "curriculum", tmp_path / "curriculum")
    (tmp_path / "state").mkdir(); (tmp_path / "state/knowledge_progress.json").write_text("{}", encoding="utf-8")
    concept = next(c for c in curriculum(tmp_path) if c["id"] == "ROI")
    result = record_result(tmp_path, concept, 3, 3)
    assert result["status"] == "verified"
    assert "ROI" in (tmp_path / "state/knowledge_progress.json").read_text(encoding="utf-8")

def test_context_filters_capability_and_keeps_chinese(tmp_path):
    for path, content in {"SYSTEM.md":"系统", "USER_PROFILE.md":"用户", "state/current_state.md":"状态", "state/current_focus.md":"重点", "standards/capability_model.md":"L1", "standards/evidence_model.md":"E1", "standards/responsibility.md":"R2", "state/knowledge_progress.json":"{}", "logs/daily/2026-09-24.md":"Finance 工作资本案例", "logs/daily/2026-09-23.md":"Leadership 案例"}.items():
        target = tmp_path / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding="utf-8")
    context = build_context(tmp_path, "Finance", recent_days=9999)
    assert "工作资本" in context and "Leadership 案例" not in context

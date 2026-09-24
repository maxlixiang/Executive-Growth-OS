from pathlib import Path
import shutil

import pytest

from growthos import cli
from growthos.config import Config
from growthos.context_builder import build_context
from growthos.deepseek import DeepSeekError
from growthos.file_utils import read_json
from growthos.knowledge import calculate_progress_result, select_concept
from growthos.study_history import commit_session, find_session, list_sessions, set_validity


ROOT = Path(__file__).parents[1]


def make_root(tmp_path: Path) -> tuple[Path, Config]:
    shutil.copytree(ROOT / "curriculum", tmp_path / "curriculum")
    shutil.copytree(ROOT / "prompts", tmp_path / "prompts")
    for folder in ("state", "logs/study", "logs/daily", "evidence", "interviews"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / "state/knowledge_progress.json").write_text("{}", encoding="utf-8")
    for name in ("SYSTEM.md", "USER_PROFILE.md"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "state/current_state.md").write_text("state", encoding="utf-8")
    (tmp_path / "state/current_focus.md").write_text("Finance", encoding="utf-8")
    (tmp_path / "standards").mkdir()
    for name in ("capability_model.md", "evidence_model.md", "responsibility.md"):
        (tmp_path / "standards" / name).write_text(name, encoding="utf-8")
    return tmp_path, Config(tmp_path, "test", "test", "https://example.invalid")


def ai_ok(*args, **kwargs):
    required = args[3]
    if "recall_question" in required:
        return {"recall_question": "Recall?", "application_question": "Application?"}
    return {"teaching": "Feedback", "concept_score": 2, "application_score": 2, "rationale": "Reason"}


def run_inputs(monkeypatch, values):
    iterator = iter(values)
    monkeypatch.setattr("builtins.input", lambda _: next(iterator))


def test_recall_q_cancels_without_changes(tmp_path, monkeypatch):
    root, config = make_root(tmp_path); monkeypatch.setattr(cli, "ask_json", ai_ok); run_inputs(monkeypatch, ["Q"])
    cli.study(root, config, "finance", "income_statement")
    assert read_json(root / "state/knowledge_progress.json", {}) == {}
    assert list((root / "logs/study").glob("*.md")) == []


def test_application_quit_cancels_without_changes(tmp_path, monkeypatch):
    root, config = make_root(tmp_path); monkeypatch.setattr(cli, "ask_json", ai_ok); run_inputs(monkeypatch, ["answer", "/quit"])
    cli.study(root, config, "finance", "income_statement")
    assert read_json(root / "state/knowledge_progress.json", {}) == {}


def test_final_n_discards_result(tmp_path, monkeypatch):
    root, config = make_root(tmp_path); monkeypatch.setattr(cli, "ask_json", ai_ok); run_inputs(monkeypatch, ["answer", "case", "n"])
    cli.study(root, config, "finance", "income_statement")
    assert read_json(root / "state/knowledge_progress.json", {}) == {}
    assert list_sessions(root) == []


def test_confirm_saves_history_and_progress(tmp_path, monkeypatch, capsys):
    root, config = make_root(tmp_path); monkeypatch.setattr(cli, "ask_json", ai_ok); run_inputs(monkeypatch, ["answer", "case", "y"])
    cli.study(root, config, "finance", "income_statement")
    sessions = list_sessions(root); assert len(sessions) == 1
    assert read_json(root / "state/knowledge_progress.json", {})["income_statement"]["review_count"] == 1
    cli.show_history(root, "finance"); cli.show_session(root, sessions[0]["metadata"]["id"])
    output = capsys.readouterr().out
    assert "income_statement" in output and "Recall?" in output and "Valid" in output


def create_session(root: Path, concept_id: str, scores: tuple[int, int]) -> dict:
    concept = select_concept(root, "finance", concept_id)
    prior = read_json(root / "state/knowledge_progress.json", {}).get(concept_id, {})
    result = calculate_progress_result(prior, concept, *scores)
    answer = {"teaching": f"feedback-{scores}", "rationale": "reason", "concept_score": scores[0], "application_score": scores[1]}
    path = commit_session(root, concept, {"recall_question": "rq", "application_question": "aq"}, "ra", "aa", answer, result)
    return find_session(root, path.stem)


def test_invalidate_restore_and_context_filter(tmp_path):
    root, _ = make_root(tmp_path)
    first = create_session(root, "income_statement", (2, 2))
    second = create_session(root, "income_statement", (3, 3))
    assert read_json(root / "state/knowledge_progress.json", {})["income_statement"]["review_count"] == 2
    set_validity(root, second["metadata"]["id"], False, "wrong answer")
    rolled_back = read_json(root / "state/knowledge_progress.json", {})["income_statement"]
    assert rolled_back["review_count"] == 1 and rolled_back["last_concept_score"] == 2
    context = build_context(root, "Finance", recent_days=9999)
    assert "feedback-(3, 3)" not in context and "feedback-(2, 2)" in context
    set_validity(root, second["metadata"]["id"], True)
    restored = read_json(root / "state/knowledge_progress.json", {})["income_statement"]
    assert restored["review_count"] == 2 and restored["last_concept_score"] == 3
    assert first["metadata"]["valid"] is True


def test_undo_invalidates_latest_and_rolls_back(tmp_path, monkeypatch):
    root, _ = make_root(tmp_path)
    create_session(root, "income_statement", (2, 2))
    latest = create_session(root, "income_statement", (3, 3))
    run_inputs(monkeypatch, ["y"])
    cli.undo_latest(root)
    assert find_session(root, latest["metadata"]["id"])["metadata"]["valid"] is False
    progress = read_json(root / "state/knowledge_progress.json", {})["income_statement"]
    assert progress["review_count"] == 1 and progress["last_concept_score"] == 2


def test_keyboard_interrupt_does_not_write(tmp_path, monkeypatch):
    root, config = make_root(tmp_path); monkeypatch.setattr(cli, "ask_json", ai_ok)
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
    cli.study(root, config, "finance", "income_statement")
    assert read_json(root / "state/knowledge_progress.json", {}) == {}


def test_deepseek_failure_does_not_write(tmp_path, monkeypatch):
    root, config = make_root(tmp_path)
    monkeypatch.setattr(cli, "ask_json", lambda *a, **k: (_ for _ in ()).throw(DeepSeekError("failure")))
    with pytest.raises(DeepSeekError):
        cli.study(root, config, "finance", "income_statement")
    assert read_json(root / "state/knowledge_progress.json", {}) == {}

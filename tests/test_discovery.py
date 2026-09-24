from pathlib import Path
from growthos.file_utils import atomic_json
from growthos.knowledge import knowledge_map

ROOT = Path(__file__).parents[1]

def test_map_shows_persisted_status_and_review(tmp_path):
    import shutil
    shutil.copytree(ROOT / "curriculum", tmp_path / "curriculum")
    (tmp_path / "state").mkdir()
    atomic_json(tmp_path / "state/knowledge_progress.json", {"ROI": {"status": "verified", "next_review_at": "2026-10-08"}})
    output = knowledge_map(tmp_path, "Finance")
    assert "ROI — 投资回报率\n   ★ 已验证\n   下次复习：2026-10-08" in output

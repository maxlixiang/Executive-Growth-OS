from datetime import date, timedelta
from pathlib import Path
import yaml
from .file_utils import atomic_json, read_json
from .spaced_repetition import next_review_date

STATUSES = ("unknown", "learning", "understood", "applied", "verified", "needs_review")

def curriculum(root: Path) -> list[dict]:
    concepts = []
    for path in sorted((root / "curriculum").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        capability = data["capability"]
        ordered_ids = [concept_id for ids in data.get("categories", {}).values() for concept_id in ids]
        positions = {concept_id: index for index, concept_id in enumerate(ordered_ids, 1)}
        for index, item in enumerate(data.get("concepts", []), 1):
            # Presentation metadata lives with the curriculum, never in CLI code.
            concept = {"capability": capability, "order": positions.get(item["id"], index), **item}
            concept["title_zh"] = data.get("title_zh", {}).get(concept["id"], concept.get("title_zh", concept["title"]))
            concept["category"] = next((name for name, ids in data.get("categories", {}).items() if concept["id"] in ids), "其他")
            required = {"id", "title", "description", "why_it_matters", "core_principles", "key_questions", "application_questions", "common_mistakes", "prerequisites", "tags"}
            if not required.issubset(concept): raise ValueError(f"Incomplete concept {concept.get('id')} in {path}")
            concepts.append(concept)
    return concepts

STATUS_VIEW = {
    "unknown": ("○", "未学习"), "learning": ("◐", "学习中"),
    "understood": ("✓", "已理解"), "applied": ("✓", "已理解"),
    "verified": ("★", "已验证"), "needs_review": ("↻", "需要复习"),
}

def capability_concepts(root: Path, capability: str) -> list[dict]:
    items = [c for c in curriculum(root) if c["capability"].lower() == capability.lower()]
    if not items: raise ValueError(f"Unknown capability: {capability}")
    return sorted(items, key=lambda c: c["order"])

def knowledge_map(root: Path, capability: str) -> str:
    items = capability_concepts(root, capability); progress = read_json(root / "state/knowledge_progress.json", {})
    labels = {"Business":"商业理解", "Finance":"财务与经营数字", "Strategy":"战略与决策", "Execution":"执行与项目管理", "Leadership":"领导力", "Influence":"影响力"}
    lines = [f"{items[0]['capability']}｜{labels[items[0]['capability']]}", f"共 {len(items)} 个知识点"]
    category = None
    for number, item in enumerate(items, 1):
        if item["category"] != category:
            category = item["category"]; lines.extend(["", f"【{category}】", ""])
        state = progress.get(item["id"], {}); symbol, status = STATUS_VIEW.get(state.get("status", "unknown"), STATUS_VIEW["unknown"])
        lines.extend([f"{number:02d} {item['id']} — {item['title_zh']}", f"   {symbol} {status}"])
        if state.get("next_review_at"): lines.append(f"   下次复习：{state['next_review_at']}")
    return "\n".join(lines)

def _recent_gap_text(root: Path, days: int = 30) -> str:
    """Load only recent Knowledge Gaps plus rolling practice state."""
    cutoff = date.today() - timedelta(days=days)
    parts = []
    for path in sorted((root / "logs/daily").glob("*.md"), reverse=True):
        try:
            if date.fromisoformat(path.name[:10]) < cutoff:
                continue
        except ValueError:
            continue
        text = path.read_text(encoding="utf-8")
        marker = "## Knowledge Gaps"
        if marker in text:
            section = text.split(marker, 1)[1].split("\n## ", 1)[0]
            parts.append(f"{path.name}: {section.strip()}")
    practice_path = root / "state/practice_state.json"
    if practice_path.exists():
        parts.append(practice_path.read_text(encoding="utf-8"))
    return "\n".join(parts)

def _mentioned_in_gaps(concept: dict, gap_text: str) -> bool:
    haystack = gap_text.casefold().replace("_", " ")
    terms = {concept["id"], concept["title"], concept.get("title_zh", "")}
    return any(term and term.casefold().replace("_", " ") in haystack for term in terms)

def _prerequisites_satisfied(concept: dict, progress: dict) -> bool:
    completed = {"understood", "applied", "verified"}
    return all(progress.get(item, {}).get("status") in completed for item in concept.get("prerequisites", []))

def recommended_next(root: Path) -> tuple[dict, str]:
    """Recommend new/deeper learning; due reviews deliberately belong to quiz."""
    progress = read_json(root / "state/knowledge_progress.json", {})
    focus = (root / "state/current_focus.md").read_text(encoding="utf-8") if (root / "state/current_focus.md").exists() else ""
    gap_text = _recent_gap_text(root)
    today = date.today().isoformat()
    items = curriculum(root)
    capability_order = {name: index for index, name in enumerate(sorted({c["capability"] for c in items}))}

    def focus_rank(item: dict) -> tuple[int, int]:
        position = focus.casefold().find(item["capability"].casefold())
        return (0, position) if position >= 0 else (1, capability_order[item["capability"]])

    candidates = []
    for item in items:
        state = progress.get(item["id"], {})
        status = state.get("status", "unknown")
        due = bool(state.get("next_review_at") and state["next_review_at"] <= today)
        if status in {"applied", "verified", "needs_review"} or due:
            continue
        if not _prerequisites_satisfied(item, progress):
            continue
        mastery_rank = {"learning": 0, "understood": 1, "unknown": 2}.get(status, 2)
        candidates.append((focus_rank(item), 0 if _mentioned_in_gaps(item, gap_text) else 1, mastery_rank, item["order"], item))

    if not candidates:
        raise ValueError("当前没有适合 study next 的新知识；如有到期复习，请运行 python -m growthos quiz。")
    _, gap_rank, _, _, item = min(candidates, key=lambda row: row[:-1])
    state = progress.get(item["id"], {})
    status = state.get("status", "unknown")
    reasons = []
    if item["capability"].casefold() in focus.casefold():
        reasons.append(f"当前 Focus 包含 {item['capability']}")
    if gap_rank == 0:
        reasons.append("最近 Daily / Practice 的 Knowledge Gap 明确提到该概念")
    if item.get("prerequisites"):
        reasons.append("前置知识已达到 understood / applied / verified")
    else:
        reasons.append("该概念没有未完成的前置知识")
    status_text = {"unknown": "尚未学习", "learning": "仍在学习中", "understood": "已理解但尚未达到应用掌握"}.get(status, "尚未充分掌握")
    reasons.append(f"{item['title_zh']} {status_text}")
    reasons.append(f"在 curriculum 推荐顺序中位于第 {item['order']} 位")
    return item, "\n".join(f"- {reason}" for reason in reasons)

def select_concept(root: Path, capability: str | None = None, concept_id: str | None = None) -> dict:
    choices = curriculum(root)
    if capability: choices = [c for c in choices if c["capability"].lower() == capability.lower()]
    if concept_id: choices = [c for c in choices if c["id"].lower() == concept_id.lower()]
    if not choices: raise ValueError("No matching curriculum concept.")
    progress = read_json(root / "state/knowledge_progress.json", {})
    return min(choices, key=lambda c: progress.get(c["id"], {}).get("next_review_at", "0000-00-00"))

def record_result(root: Path, concept: dict, concept_score: int, application_score: int) -> dict:
    path = root / "state/knowledge_progress.json"; progress = read_json(path, {})
    result = calculate_progress_result(progress.get(concept["id"], {}), concept, concept_score, application_score)
    progress[concept["id"]] = result; atomic_json(path, progress)
    return result

def calculate_progress_result(prior: dict, concept: dict, concept_score: int, application_score: int, reviewed_on: date | None = None) -> dict:
    """Calculate a progress snapshot without writing it."""
    passed = concept_score >= 2 and application_score >= 2
    streak = prior.get("consecutive_successes", 0) + 1 if passed else 0
    status = "verified" if concept_score == application_score == 3 else "applied" if passed else "needs_review"
    reviewed_on = reviewed_on or date.today(); reviewed_at = reviewed_on.isoformat()
    return {**prior, "capability": concept["capability"], "status": status, "first_learned_at": prior.get("first_learned_at", reviewed_at), "last_reviewed_at": reviewed_at, "next_review_at": next_review_date(concept_score, application_score, streak, reviewed_on).isoformat(), "review_count": prior.get("review_count", 0)+1, "consecutive_successes": streak, "last_concept_score": concept_score, "last_application_score": application_score}

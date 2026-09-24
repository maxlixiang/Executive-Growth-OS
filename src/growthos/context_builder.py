from pathlib import Path
from .file_utils import read_text, read_json
from .study_history import parse_session

def build_context(root: Path, capability: str | None = None, recent_days: int = 30, full_period: Path | None = None) -> str:
    core_names = ["SYSTEM.md", "USER_PROFILE.md", "state/current_state.md", "state/current_focus.md", "standards/capability_model.md", "standards/evidence_model.md", "standards/responsibility.md"]
    sections = [(name, read_text(root / name)) for name in core_names]
    progress = read_json(root / "state/knowledge_progress.json", {})
    if capability: progress = {k:v for k,v in progress.items() if v.get("capability", "").lower() == capability.lower()}
    sections.append(("Knowledge Progress", str(progress)))
    import datetime
    cutoff = datetime.date.today() - datetime.timedelta(days=recent_days)
    bases = [full_period] if full_period else [root / "logs/daily", root / "logs/study", root / "evidence", root / "interviews"]
    for base in filter(None, bases):
        for path in sorted(base.glob("*.md")):
            if base.name == "study":
                session = parse_session(path)
                if session and not session["metadata"]["valid"]:
                    continue
            if full_period is None:
                try: day = datetime.date.fromisoformat(path.name[:10])
                except ValueError: continue
                if day < cutoff: continue
            text = read_text(path)
            if not capability or capability.lower() in text.lower(): sections.append((str(path.relative_to(root)), text))
    return "\n\n".join(f"## {title}\n{body}" for title, body in sections if body)

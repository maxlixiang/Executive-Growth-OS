from datetime import date
from pathlib import Path
from .context_builder import build_context
from .deepseek import ask_json
from .file_utils import atomic_write, read_text

def monthly_review(root: Path, config) -> Path:
    period = date.today().strftime("%Y-%m"); context = build_context(root, full_period=root / "logs/daily")
    answer = ask_json(config, read_text(root / "prompts/monthly_review.md"), context, {"review", "current_state", "current_focus"})
    path = root / "reviews/monthly" / f"{period}.md"; atomic_write(path, answer["review"])
    atomic_write(root / "state/current_state.md", answer["current_state"]); atomic_write(root / "state/current_focus.md", answer["current_focus"])
    return path

def quarterly_question(root: Path, config) -> dict:
    context = build_context(root, recent_days=120)
    return ask_json(config, read_text(root / "prompts/executive_interviewer.md"), context, {"question", "capability_focus", "why_asked"})

def save_interview(root: Path, transcript: list[tuple[str, str]]) -> Path:
    today = date.today().isoformat(); path = root / "interviews" / f"{today}_quarterly.md"
    atomic_write(path, "# Quarterly Mock Executive Interview\n\n" + "\n\n".join(f"## {role}\n{text}" for role, text in transcript) + "\n")
    return path

def quarterly_assessment(root: Path, config, transcript: list[tuple[str, str]]) -> Path:
    """Persist the interview first, then create the quarterly assessment atomically."""
    interview = save_interview(root, transcript)
    context = build_context(root, recent_days=120) + "\n\n## Interview Transcript\n" + read_text(interview)
    answer = ask_json(config, read_text(root / "prompts/monthly_review.md"), context, {"review", "current_state", "current_focus"})
    period = f"{date.today().year}-Q{(date.today().month - 1)//3 + 1}"
    path = root / "reviews/quarterly" / f"{period}.md"
    atomic_write(path, "# Quarterly Mock Executive Review\n\n" + answer["review"])
    atomic_write(root / "state/current_state.md", answer["current_state"])
    atomic_write(root / "state/current_focus.md", answer["current_focus"])
    return path

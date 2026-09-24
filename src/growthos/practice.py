from datetime import date
from pathlib import Path
from .deepseek import ask_json
from .file_utils import atomic_json, atomic_write, read_json, read_text, slugify

def analyze_daily(root: Path, config, raw_input: str, context: str) -> tuple[Path, list[Path]]:
    prompt = read_text(root / "prompts/daily_analyzer.md")
    result = ask_json(config, prompt, f"Context:\n{context}\n\nRaw Input:\n{raw_input}", {"analysis", "evidences", "knowledge_gaps", "practice_suggestions", "responsibility_hint"})
    today = date.today().isoformat()
    daily_path = root / "logs/daily" / f"{today}.md"
    content = f"# Daily Log — {today}\n\n## Raw Input\n\n{raw_input}\n\n## AI Analysis\n\n{result['analysis']}\n\n## Evidence\n\n{result['evidences']}\n\n## Knowledge Gaps\n\n{result['knowledge_gaps']}\n\n## Practice Suggestions\n\n{result['practice_suggestions']}\n"
    atomic_write(daily_path, content)
    evidence_paths = []
    for evidence in result["evidences"]:
        if not isinstance(evidence, dict) or "capability" not in evidence: continue
        title = evidence.get("title", evidence["capability"])
        path = root / "evidence" / f"{today}_{slugify(title)}-{len(evidence_paths)+1}.md"
        fields = {"Date":today, "Capability":evidence["capability"], "Evidence Level":evidence.get("evidence_level", "E0"), "Context":evidence.get("context", ""), "User Role":evidence.get("user_role", ""), "Action":evidence.get("action", ""), "Decision":evidence.get("decision", ""), "Stakeholders":evidence.get("stakeholders", ""), "Outcome":evidence.get("outcome", ""), "Why It Matters":evidence.get("why_it_matters", ""), "Limitations":evidence.get("limitations", ""), "Next Evidence Needed":evidence.get("next_evidence_needed", ""), "Source Daily Log":str(daily_path.relative_to(root))}
        atomic_write(path, "\n".join(f"## {key}\n{value}" for key, value in fields.items()) + "\n"); evidence_paths.append(path)
    state_path = root / "state/practice_state.json"; state = read_json(state_path, {"responsibility_level":"R2", "evidence_count":0, "capability_summary":{}})
    state["evidence_count"] = state.get("evidence_count", 0) + len(evidence_paths); state["last_daily_at"] = today; state["last_responsibility_hint"] = result["responsibility_hint"]
    atomic_json(state_path, state)
    return daily_path, evidence_paths

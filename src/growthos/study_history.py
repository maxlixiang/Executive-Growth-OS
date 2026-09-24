from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
import yaml

from .file_utils import atomic_json, atomic_write, read_json
from .knowledge import calculate_progress_result, curriculum

EXIT_COMMANDS = {"q", "quit", "exit", "/quit"}

def is_exit_command(value: str) -> bool:
    return value.strip().casefold() in EXIT_COMMANDS

def new_session_id(capability: str, concept_id: str) -> str:
    stamp = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S%f%z")
    return f"{stamp}_{capability.lower()}_{concept_id}_{uuid4().hex[:6]}"

def render_session(record: dict) -> str:
    metadata = yaml.safe_dump(record["metadata"], allow_unicode=True, sort_keys=False).strip()
    fields = record["content"]
    body = [f"# Study Session — {record['metadata']['concept_title']}"]
    for label, key in [
        ("Recall Question", "recall_question"), ("User Recall Answer", "recall_answer"),
        ("Application Question", "application_question"), ("User Application Answer", "application_answer"),
        ("AI Feedback", "ai_feedback"), ("AI Rationale", "rationale"),
    ]:
        body.extend(["", f"## {label}", str(fields.get(key, ""))])
    return f"---\n{metadata}\n---\n\n" + "\n".join(body) + "\n"

def parse_session(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return None
    metadata_text, body = text[4:].split("\n---\n", 1)
    metadata = yaml.safe_load(metadata_text) or {}
    if not {"id", "concept_id", "capability", "committed_at", "valid"}.issubset(metadata):
        return None
    content = {}
    for label, key in [
        ("Recall Question", "recall_question"), ("User Recall Answer", "recall_answer"),
        ("Application Question", "application_question"), ("User Application Answer", "application_answer"),
        ("AI Feedback", "ai_feedback"), ("AI Rationale", "rationale"),
    ]:
        marker = f"## {label}\n"
        if marker in body:
            content[key] = body.split(marker, 1)[1].split("\n## ", 1)[0].strip()
    return {"metadata": metadata, "content": content, "path": path}

def list_sessions(root: Path, capability: str | None = None) -> list[dict]:
    sessions = []
    for path in (root / "logs/study").glob("*.md"):
        record = parse_session(path)
        if record and (not capability or record["metadata"]["capability"].casefold() == capability.casefold()):
            sessions.append(record)
    return sorted(sessions, key=lambda item: item["metadata"]["committed_at"], reverse=True)

def find_session(root: Path, session_id: str) -> dict:
    matches = [item for item in list_sessions(root) if item["metadata"]["id"] == session_id or item["metadata"]["id"].startswith(session_id)]
    if len(matches) != 1:
        raise ValueError("Study Session ID 不存在或缩写不唯一。")
    return matches[0]

def commit_session(root: Path, concept: dict, questions: dict, recall: str, application: str, answer: dict, result: dict) -> Path:
    session_id = new_session_id(concept["capability"], concept["id"])
    committed_at = datetime.now().astimezone().isoformat(timespec="microseconds")
    metadata = {
        "id": session_id, "committed_at": committed_at, "capability": concept["capability"],
        "concept_id": concept["id"], "concept_title": concept["title"], "concept_title_zh": concept.get("title_zh", concept["title"]),
        "concept_score": int(answer["concept_score"]), "application_score": int(answer["application_score"]),
        "status": result["status"], "next_review_at": result["next_review_at"], "valid": True,
        "invalidated_at": None, "invalidated_reason": None,
    }
    record = {"metadata": metadata, "content": {
        "recall_question": questions["recall_question"], "recall_answer": recall,
        "application_question": questions["application_question"], "application_answer": application,
        "ai_feedback": answer["teaching"], "rationale": answer["rationale"],
    }}
    path = root / "logs/study" / f"{session_id}.md"
    progress_path = root / "state/knowledge_progress.json"
    original_progress = read_json(progress_path, {})
    try:
        atomic_write(path, render_session(record))
        atomic_json(progress_path, {**original_progress, concept["id"]: result})
    except BaseException:
        if path.exists(): path.unlink()
        atomic_json(progress_path, original_progress)
        raise
    return path

def rebuild_concept_progress(root: Path, concept_id: str, capability: str | None = None) -> dict | None:
    concepts = [item for item in curriculum(root) if item["id"] == concept_id and (not capability or item["capability"].casefold() == capability.casefold())]
    if len(concepts) != 1:
        raise ValueError(f"无法唯一定位 Concept: {concept_id}")
    concept = concepts[0]; snapshot = None
    relevant = [item for item in reversed(list_sessions(root, concept["capability"])) if item["metadata"]["concept_id"] == concept_id and item["metadata"]["valid"]]
    for item in relevant:
        meta = item["metadata"]
        snapshot = calculate_progress_result(snapshot or {}, concept, int(meta["concept_score"]), int(meta["application_score"]), date.fromisoformat(meta["committed_at"][:10]))
    path = root / "state/knowledge_progress.json"; progress = read_json(path, {})
    if snapshot is None: progress.pop(concept_id, None)
    else: progress[concept_id] = snapshot
    atomic_json(path, progress)
    return snapshot

def rebuild_all_progress(root: Path) -> dict:
    progress = {}; concepts = curriculum(root)
    for item in reversed(list_sessions(root)):
        meta = item["metadata"]
        if not meta["valid"]: continue
        matches = [c for c in concepts if c["id"] == meta["concept_id"] and c["capability"].casefold() == meta["capability"].casefold()]
        if len(matches) != 1: continue
        concept = matches[0]; prior = progress.get(concept["id"], {})
        progress[concept["id"]] = calculate_progress_result(prior, concept, int(meta["concept_score"]), int(meta["application_score"]), date.fromisoformat(meta["committed_at"][:10]))
    atomic_json(root / "state/knowledge_progress.json", progress)
    return progress

def set_validity(root: Path, session_id: str, valid: bool, reason: str | None = None) -> dict:
    record = find_session(root, session_id); meta = record["metadata"]
    meta["valid"] = valid
    meta["invalidated_at"] = None if valid else datetime.now().astimezone().isoformat(timespec="microseconds")
    meta["invalidated_reason"] = None if valid else (reason or "人工作废")
    atomic_write(record["path"], render_session(record))
    rebuild_concept_progress(root, meta["concept_id"], meta["capability"])
    return record

def latest_valid_session(root: Path) -> dict:
    session = next((item for item in list_sessions(root) if item["metadata"]["valid"]), None)
    if not session: raise ValueError("没有可撤销的有效 Study Session。")
    return session

def session_summary(record: dict) -> str:
    meta = record["metadata"]; validity = "Valid" if meta["valid"] else "Invalid"
    return f"{meta['committed_at']}  {meta['capability']}  {meta['concept_id']}  Concept={meta['concept_score']}  Application={meta['application_score']}  {meta['status']}  {validity}"

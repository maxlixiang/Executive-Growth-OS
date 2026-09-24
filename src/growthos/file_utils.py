import json
import os
import tempfile
from pathlib import Path
from typing import Any

def read_text(path: Path, default: str = "") -> str:
    return path.read_text(encoding="utf-8") if path.exists() else default

def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(read_text(path, json.dumps(default)))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}; file was not changed.") from exc

def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush(); os.fsync(file.fileno())
        os.replace(temp_name, path)
    except Exception:
        if os.path.exists(temp_name): os.unlink(temp_name)
        raise

def atomic_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def slugify(text: str) -> str:
    import re
    output = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return output[:48] or "work-event"

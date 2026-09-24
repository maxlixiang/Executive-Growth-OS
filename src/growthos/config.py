from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Config:
    root: Path
    api_key: str | None
    model: str
    base_url: str

    @classmethod
    def load(cls, root: Path | None = None) -> "Config":
        root = root or Path.cwd()
        env = root / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
        return cls(root, os.getenv("DEEPSEEK_API_KEY"), os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))

import os
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader; real environment variables take precedence."""
    path = path or Path(os.getcwd()) / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

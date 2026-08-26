import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MalformedLine:
    source_file: str
    line_number: int
    raw_line: str
    error: str


def extract_ndjson(path: Path):
    """Yield (line_number, record) for parseable lines and collect malformed ones.

    Parse failures are returned to the caller for quarantine routing; the
    extractor itself never raises on bad lines.
    """
    malformed: list[MalformedLine] = []
    records: list[tuple[int, dict]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
                if not isinstance(obj, dict):
                    raise ValueError("line is valid JSON but not an object")
                records.append((line_number, obj))
            except (json.JSONDecodeError, ValueError) as exc:
                malformed.append(
                    MalformedLine(
                        source_file=str(path),
                        line_number=line_number,
                        raw_line=stripped[:2000],
                        error=str(exc),
                    )
                )
    return records, malformed

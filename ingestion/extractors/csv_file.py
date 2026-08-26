import csv
from collections.abc import Iterator
from pathlib import Path


def extract_csv(path: Path, source_name: str) -> Iterator[tuple[int, dict]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            yield row_number, {k: (None if v == "" else v) for k, v in row.items() if k is not None}

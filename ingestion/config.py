import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SeedConfig:
    rng_seed: int
    start_date: str
    end_date: str
    volumes: dict
    imperfections: dict
    schema_drift: dict


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_seed_config(path: Path | None = None) -> SeedConfig:
    path = path or project_root() / "configs" / "seed.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SeedConfig(
        rng_seed=raw["rng_seed"],
        start_date=raw["date_window"]["start"],
        end_date=raw["date_window"]["end"],
        volumes=raw["volumes"],
        imperfections=raw.get("imperfections", {}),
        schema_drift=raw.get("schema_drift", {}),
    )


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Required environment variable {name} is not set; see .env.example")
    return value


def warehouse_path() -> Path:
    return Path(env("WAREHOUSE_PATH", str(project_root() / "data" / "warehouse" / "analytics.duckdb")))

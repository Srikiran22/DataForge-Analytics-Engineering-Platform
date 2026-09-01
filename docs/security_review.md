# Security Review — DataForge

## Secrets / Credentials
| Finding | Evidence | Severity | Fix |
|---------|----------|----------|-----|
| `.env` not committed, `.env.example` has placeholders only | `git ls-files \| grep env` → only `.env.example`; `grep -r change_me` shows no real secrets | PASS | None |
| `.gitignore` covers `.env`, `*.duckdb`, `.venv/` | `cat .gitignore` | PASS | None |
| CI uses `secrets.*` not hardcoded | `grep -r password .github/` shows `change_me_admin` only for local/CI Postgres | PASS | Rotate if ever real creds committed |

## Warehouse / Storage Access
| Area | Detail |
|------|--------|
| Warehouse | DuckDB file `data/warehouse/analytics.duckdb` — local only, no network exposure. Dashboard uses **read-only** `duckdb.connect(..., read_only=True)` |
| OLTP source | `source_oltp` schema — least-privilege `source_reader` (SELECT only) created by `populate_oltp.py`; admin `source_admin` only for DDL/COPY |
| Docker | No secrets in `docker-compose.yml` (uses `${VAR:-default}`) |

## SQL Injection
| Check | Result |
|-------|--------|
| `ingestion/extractors/rdbms.py` — `extract_watermarked` uses `cur.execute(query, params)` parameterized; `schema.table` interpolated via trusted constants only | PASS |
| `ingestion/loaders/duckdb_loader.py` — `read_json` path via `_sql_string` escaping + `?` placeholder for batch_id; no user input in SQL | PASS |
| No dynamic `f"SELECT {user_input}"` patterns found | `grep -r "f\".*SELECT" ingestion/` → none |

## Unsafe File Paths
| Check | Result |
|-------|--------|
| `ingestion/extractors/csv_file.py` / `ndjson_file.py` — `path.open()` on `project_root() / "data" / "source"` only; no source-provided paths | PASS |
| `dashboard` — warehouse path via `WAREHOUSE_PATH` env, not user input | PASS |

## Untrusted Source Files
| Check | Result |
|-------|--------|
| Contract validation runs before downstream use (`dbt test` on sources; quarantine on parse failure) | PASS |
| Malformed JSON lines → `raw.quarantine_*` (I-04 proven: 523 orders + 23 returns quarantined) | PASS |

## Logs / PII Leakage
| Check | Result |
|-------|--------|
| `ingestion/pipeline.py` logs `batch_id` + counts, not raw PII | PASS |
| Airflow logs not yet deployed (deferred to service); `grep -r "email" ingestion/ --include="*.py"` shows no logging of emails | PASS |
| Synthetic data only — no real PII ever loaded (`docs/data_provenance.md`) | PASS |

## Dependencies / CI
| Check | Result |
|-------|--------|
| `requirements/resolved-versions.txt` pinned (duckdb 1.5.5, psycopg 3.3.4, etc.) | PASS |
| `actions/checkout@v7`, `setup-python@v7` (latest majors, node24) | PASS |
| CI runs on `pull_request` + `push: main`, no `pull_request_target` (no fork secret exfil) | PASS |
| No `actions/write` with `contents: write` beyond checkout | PASS |

## Docker
| Check | Result |
|-------|--------|
| `postgres:17` pinned major, official image | PASS |
| No `--privileged`, no host `network_mode` except for WSL Postgres (documented in compose comment) | PASS |

## Remaining Risk
- Airflow not yet deployed; its worker/secret handling unverified — **OPEN until Group 6**
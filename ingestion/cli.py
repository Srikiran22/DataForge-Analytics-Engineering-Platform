import argparse
import sys

from ingestion import pipeline
from ingestion.envfile import load_dotenv


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="ingestion", description="Raw-layer ingestion engine")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-warehouse", help="Create raw/quarantine/watermark/lineage structures")
    load_p = sub.add_parser("load", help="Load a source into the raw layer")
    load_p.add_argument("--source", required=True, choices=sorted(pipeline.SOURCES.keys()))
    load_p.add_argument("--batch-id", default=None, help="Reuse an explicit batch id (re-run = replace)")
    load_p.add_argument("--full", action="store_true", help="Ignore watermarks and reload everything available")

    args = parser.parse_args(argv)
    conn = pipeline.connect_warehouse()
    try:
        if args.command == "init-warehouse":
            pipeline.init_warehouse(conn)
            print("warehouse initialized")
            return 0
        if args.command == "load":
            stats = pipeline.run_source(conn, args.source, batch_id=args.batch_id, full=args.full)
            print(stats)
            return 0
    finally:
        conn.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())

import argparse
import sys
import uvicorn
from src.config import settings
from src.services.pipeline_service import PipelineService
from src.services.seeder_service import SeederService
from src.services.state_service import StateService


def handle_seed() -> None:
    seeder = SeederService()
    results = seeder.seed_all()
    print("Sources successfully seeded:")
    for src, count in results.items():
        print(f"  - {src}: {count} records")


def handle_run(run_type: str) -> None:
    pipeline = PipelineService()
    print(f"Starting pipeline execution [mode: {run_type}]...")
    result = pipeline.run(run_type=run_type)
    print(f"Pipeline executed successfully in {result['duration_seconds']}s.")
    print(f"Run ID: {result['run_id']}")
    print(f"Rows extracted: {result['rows_extracted']} | Rows loaded: {result['rows_loaded']}")
    print("Marts generated:")
    for mart, count in result["marts_summary"].items():
        print(f"  - {mart}: {count} rows")


def handle_history(limit: int) -> None:
    pipeline = PipelineService()
    runs = pipeline.get_run_history(limit=limit)
    if not runs:
        print("No pipeline runs found.")
        return
    print(f"{'Run ID':<18} | {'Type':<12} | {'Status':<10} | {'Extracted':<10} | {'Loaded':<8} | {'Duration':<8} | {'Started At'}")
    print("-" * 90)
    for r in runs:
        dur = f"{r['duration_seconds']}s" if r['duration_seconds'] is not None else "-"
        print(f"{r['run_id']:<18} | {r['run_type']:<12} | {r['status']:<10} | {r['rows_extracted']:<10} | {r['rows_loaded']:<8} | {dur:<8} | {str(r['started_at'])[:19]}")


def handle_reset_state() -> None:
    state_service = StateService()
    state_service.reset_all_checkpoints()
    print("Checkpoints cleared. Next run will process all records.")


def handle_serve() -> None:
    print(f"Starting API server on {settings.API_HOST}:{settings.API_PORT}...")
    uvicorn.run("src.api.app:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail ETL & Data Mart Engine")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("seed", help="Seed sample sources data")

    run_parser = subparsers.add_parser("run", help="Run the ETL pipeline")
    run_parser.add_argument("--type", choices=["FULL", "INCREMENTAL"], default="INCREMENTAL", help="Run type")

    hist_parser = subparsers.add_parser("history", help="Show pipeline execution history")
    hist_parser.add_argument("--limit", type=int, default=10, help="Number of records to show")

    subparsers.add_parser("reset-state", help="Reset incremental checkpoints")
    subparsers.add_parser("serve", help="Run FastAPI web server")

    args = parser.parse_args()

    if args.command == "seed":
        handle_seed()
    elif args.command == "run":
        handle_run(args.type)
    elif args.command == "history":
        handle_history(args.limit)
    elif args.command == "reset-state":
        handle_reset_state()
    elif args.command == "serve":
        handle_serve()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Run reviewed engineering fixtures without API keys or cloud access."""

import argparse
import json
from pathlib import Path

from paper2proof.artifacts.evidence import verify_bundle
from paper2proof.experiments import rerun_fixture, run_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("fixture", help="Run a fixed reviewed engineering fixture")
    fixture.add_argument(
        "--case", choices=["reference", "wrong_update", "missing_setting"], default="reference"
    )
    fixture.add_argument("--output-root", type=Path, default=Path("artifacts"))
    verify = commands.add_parser("verify", help="Check evidence integrity, not scientific validity")
    verify.add_argument("directory", type=Path)
    rerun = commands.add_parser("rerun", help="Create a new attempt from a frozen fixture")
    rerun.add_argument("directory", type=Path)
    rerun.add_argument("--output-root", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    try:
        if args.command == "verify":
            manifest = verify_bundle(args.directory)
            print(f"Integrity verified: {len(manifest['files'])} files. Not a scientific verdict.")
            return 0
        directory = (
            run_fixture(args.output_root, variant=args.case)
            if args.command == "fixture"
            else rerun_fixture(args.directory, args.output_root)
        )
        report = json.loads((directory / "report.json").read_bytes())
        print(f"Evidence: {directory}")
        print(f"Execution: {report['execution_state']}; assessment: {report['assessment']}")
        print("Engineering fixture only. No live API or sandbox was used.")
        return 1 if report["execution_state"] == "failed" else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Fixture error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

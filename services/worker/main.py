import argparse
import time

from paper2proof.config import get_settings
from paper2proof.workspace import Workspace


def main():
    parser = argparse.ArgumentParser(
        description="Single-user local SQLite worker; no live providers"
    )
    parser.add_argument("--once", action="store_true", help="Process one queued job and exit")
    args = parser.parse_args()
    workspace = Workspace(get_settings().data_dir)
    print(
        "Offline worker: reviewed fixtures and generation previews only. Ctrl+C to stop.",
        flush=True,
    )
    while True:
        processed = workspace.process_one()
        if args.once:
            return
        if not processed:
            time.sleep(0.5)


if __name__ == "__main__":
    main()

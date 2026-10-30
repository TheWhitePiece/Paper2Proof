import hashlib
import json
from pathlib import Path

MAX_BUNDLE_BYTES = 100 * 1024 * 1024
ALLOWED_FILES = frozenset(
    {
        "spec.json",
        "input.json",
        "solver.py",
        "evaluator.py",
        "generator.py",
        "contracts.py",
        "requirements-dev.lock",
        "stdout.json",
        "stderr.log",
        "execution.json",
        "report.json",
        "README.md",
    }
)


def canonical_json(value) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)


def write_manifest(directory: Path) -> dict:
    entries = {}
    total = 0
    for name in sorted(ALLOWED_FILES):
        path = directory / name
        if path.is_symlink():
            raise ValueError("Evidence cannot contain symbolic links")
        size = path.stat().st_size
        total += size
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("Evidence exceeds bundle limit")
        entries[name] = {"sha256": digest(path.read_bytes()), "size_bytes": size}
    manifest = {"schema_version": "evidence-manifest-v1", "files": entries}
    write_once(directory / "manifest.json", canonical_json(manifest))
    return manifest


def verify_bundle(directory: Path) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Evidence must be a regular directory")
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 64 * 1024:
        raise ValueError("Invalid manifest")
    manifest = json.loads(manifest_path.read_bytes())
    if set(manifest) != {"schema_version", "files"}:
        raise ValueError("Invalid manifest fields")
    if manifest["schema_version"] != "evidence-manifest-v1":
        raise ValueError("Unsupported manifest version")
    entries = manifest["files"]
    if not isinstance(entries, dict) or set(entries) != ALLOWED_FILES:
        raise ValueError("Manifest must contain exactly the allowlisted filenames")
    if {path.name for path in directory.iterdir()} != ALLOWED_FILES | {"manifest.json"}:
        raise ValueError("Unexpected or missing evidence files")
    total = 0
    for name, record in entries.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Evidence must be regular files, not links")
        size = path.stat().st_size
        total += size
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("Evidence exceeds bundle limit")
        if not isinstance(record, dict) or set(record) != {"sha256", "size_bytes"}:
            raise ValueError("Invalid manifest entry")
        if size != record["size_bytes"] or digest(path.read_bytes()) != record["sha256"]:
            raise ValueError(f"Evidence integrity check failed: {name}")
    return manifest

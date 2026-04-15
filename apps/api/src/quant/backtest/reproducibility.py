"""
Reproducibility manifests.

When we publish a result we emit a manifest capturing the exact inputs so any
reader can rerun and get the same number:

    code_sha       — git HEAD
    config_hash    — sha256 of canonical JSON of the run config
    data_fingerprint — sha256 of sorted (date, symbol, adj_close) tuples
    python_version, package_versions  — environment snapshot

The manifest is persisted alongside MLflow runs and attached to any public
report. No manifest → no publish.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class ReproManifest:
    code_sha: str
    config_hash: str
    data_fingerprint: str
    python_version: str
    package_versions: dict[str, str]
    created_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2)


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],  # noqa: S607 — git is expected on PATH
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def _canonical_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _package_versions(packages: list[str]) -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    out: dict[str, str] = {}
    for p in packages:
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            out[p] = "not-installed"
    return out


def build_manifest(
    *,
    config: dict[str, Any],
    data_tuples: list[tuple[Any, ...]],
    packages: list[str] | None = None,
) -> ReproManifest:
    pkgs = packages or [
        "polars",
        "numpy",
        "scikit-learn",
        "lightgbm",
        "mlflow",
        "sqlalchemy",
        "fastapi",
    ]
    data_hash = hashlib.sha256("\n".join(str(t) for t in sorted(data_tuples)).encode()).hexdigest()
    return ReproManifest(
        code_sha=_git_sha(),
        config_hash=_canonical_hash(config),
        data_fingerprint=data_hash,
        python_version=sys.version.split()[0],
        package_versions=_package_versions(pkgs),
        created_at=datetime.now(UTC).isoformat(),
    )

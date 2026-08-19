from __future__ import annotations

import hashlib
from pathlib import Path

from .generator import BenchmarkCase
from .oracle import LiveOracle, OracleResult
from .oracle_snapshot import load_oracle_snapshot, oracle_result_for_case


class EvaluationOracle:
    def __init__(self, *, benchmark_fingerprint: str, snapshot_path: str | None = None):
        self.snapshot_path = snapshot_path
        self.snapshot = None
        self.live = None
        self.reference_sha256 = None
        if snapshot_path:
            path = Path(snapshot_path)
            self.reference_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            self.snapshot = load_oracle_snapshot(path, expected_fingerprint=benchmark_fingerprint)
            self.mode = "frozen_snapshot"
        else:
            self.live = LiveOracle()
            self.mode = "independent_live"

    async def get(self, case: BenchmarkCase) -> tuple[OracleResult | None, str | None]:
        if self.snapshot is not None:
            return oracle_result_for_case(self.snapshot, case)
        assert self.live is not None
        try:
            return await self.live.execute(case), None
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"

    async def close(self) -> None:
        if self.live is not None:
            await self.live.close()

    def metadata(self) -> dict:
        return {
            "oracle_mode": self.mode,
            "oracle_snapshot_path": self.snapshot_path,
            "oracle_snapshot_file_sha256": self.reference_sha256,
        }

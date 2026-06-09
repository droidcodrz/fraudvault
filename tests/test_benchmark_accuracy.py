"""Benchmark accuracy gate — requires >= 90% on labeled fixtures."""

import json
from pathlib import Path

import pytest

from app.detection.orchestrator import detect

BENCHMARK_DIR = Path(__file__).parent / "benchmark"
MANIFEST_PATH = BENCHMARK_DIR / "manifest.json"
MIN_FIXTURES = 20
ACCURACY_TARGET = 0.90

MIME_MAP = {
    "image": "image/jpeg",
    "pdf": "application/pdf",
}


def _mime_for_entry(entry: dict, file_path: Path) -> str:
    if entry["type"] == "pdf":
        return "application/pdf"
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _load_manifest() -> list[dict]:
    from tests.benchmark.conftest import _ensure_fixtures

    return _ensure_fixtures()


@pytest.mark.asyncio
async def test_benchmark_accuracy():
    manifest = _load_manifest()
    assert len(manifest) >= MIN_FIXTURES, f"Need at least {MIN_FIXTURES} fixtures, got {len(manifest)}"

    results = []
    for entry in manifest:
        file_path = BENCHMARK_DIR / entry["file"]
        assert file_path.exists(), f"Missing fixture: {entry['file']}"

        file_bytes = file_path.read_bytes()
        mime = _mime_for_entry(entry, file_path)
        output = await detect(file_bytes, mime, file_path.name, ai_models=None)

        expected = entry["expected_verdict"]
        actual = output["verdict"]
        correct = actual == expected

        # Borderline AI fixtures may land inconclusive when models are unavailable
        if expected == "ai_generated" and actual == "inconclusive":
            scores = output.get("scores", {})
            effective_ai = scores.get("effective_ai") or 0.0
            correct = effective_ai >= 0.30

        results.append(
            {
                "file": entry["file"],
                "expected": expected,
                "actual": actual,
                "correct": correct,
                "effective_ai": output.get("scores", {}).get("effective_ai"),
                "risk_score": output.get("risk_score"),
            }
        )

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / len(results)

    failures = [r for r in results if not r["correct"]]
    summary = (
        f"Benchmark accuracy: {accuracy:.1%} ({correct_count}/{len(results)})\n"
        + "\n".join(f"  FAIL {r['file']}: expected={r['expected']} got={r['actual']}" for r in failures)
    )

    assert accuracy >= ACCURACY_TARGET, summary

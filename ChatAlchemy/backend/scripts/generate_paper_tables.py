from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from chatalchemy.benchmark.statistics import holm_bonferroni, mcnemar_exact, paired_bootstrap_ci

DISPLAY_METRICS = [
    ("n", "N"),
    ("oracle_coverage", "Oracle coverage"),
    ("mean_task_score", "Task score"),
    ("routing_accuracy", "Routing accuracy"),
    ("execution_success", "Execution success"),
    ("claiming_rate", "Claim-producing rate"),
    ("mean_supported_claim_rate_on_claimed", "Evidence-link validity"),
    ("mean_provenance_record_f1", "Provenance F1"),
    ("median_latency_ms", "Median latency (ms)"),
    ("p95_latency_ms", "P95 latency (ms)"),
    ("mean_api_calls", "API calls/query"),
    ("mean_model_total_tokens", "Model tokens/query"),
    ("mean_tool_calls", "Tool calls/query"),
]


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def _fmt(value: Any, metric: str) -> str:
    if value is None:
        return "--"
    if metric == "n":
        return str(int(value))
    if metric.endswith("latency_ms"):
        return f"{float(value):.1f}"
    if metric in {"mean_api_calls", "mean_tool_calls", "mean_model_total_tokens"}:
        return f"{float(value):.2f}"
    return f"{float(value):.3f}"


def _system_name(payload: dict, fallback: str) -> str:
    run = payload.get("run") or {}
    return str(run.get("system") or run.get("mode") or fallback)


def _normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(summary or {})
    aliases = {
        "mean_task_score": ("baseline_mean_task_score",),
        "median_latency_ms": ("median_baseline_latency_ms",),
    }
    for target, candidates in aliases.items():
        if normalized.get(target) is None:
            for candidate in candidates:
                if normalized.get(candidate) is not None:
                    normalized[target] = normalized[candidate]
                    break
    return normalized


def _normalize_family_map(by_family: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(family): _normalize_summary(summary or {}) for family, summary in (by_family or {}).items()}


def _oracle_state(payload: dict) -> str | None:
    run = payload.get("run") or {}
    snapshot_sha = run.get("oracle_snapshot_file_sha256")
    if snapshot_sha:
        return f"snapshot:{snapshot_sha}"
    started = run.get("started_at_utc")
    if not started:
        component = run.get("component_started_at_utc")
        if isinstance(component, list) and component:
            started = min(str(value) for value in component if value)
    if run.get("oracle_mode") == "independent_live" or run.get("oracle_snapshot_policy"):
        return f"live-run:{started}" if started else None
    return None


def _extract_systems(label: str, payload: dict) -> list[dict]:
    state = _oracle_state(payload)
    fingerprint = (payload.get("benchmark") or {}).get("fingerprint_sha256")
    systems = payload.get("systems")
    if isinstance(systems, list):
        out = []
        for item in systems:
            name = str(item.get("system") or "system")
            out.append({
                "name": f"{label}:{name}" if label else name,
                "summary": _normalize_summary(item.get("summary") or {}),
                "by_family": _normalize_family_map(item.get("by_family") or {}),
                "cases": item.get("cases") or [],
                "oracle_state": state,
                "benchmark_fingerprint": fingerprint,
            })
        return out
    return [{
        "name": label or _system_name(payload, "system"),
        "summary": _normalize_summary(payload.get("summary") or {}),
        "by_family": _normalize_family_map(payload.get("by_family") or {}),
        "cases": payload.get("cases") or [],
        "oracle_state": state,
        "benchmark_fingerprint": fingerprint,
    }]


def _load_specs(specs: list[str]) -> list[dict]:
    systems: list[dict] = []
    seen: set[str] = set()
    for spec in specs:
        if "=" in spec:
            label, raw_path = spec.split("=", 1)
        else:
            raw_path = spec
            label = Path(raw_path).stem
        payload = json.loads(Path(raw_path).read_text())
        for system in _extract_systems(label, payload):
            base = system["name"]
            name = base
            index = 2
            while name in seen:
                name = f"{base}-{index}"
                index += 1
            system["name"] = name
            seen.add(name)
            systems.append(system)
    return systems


def _write_main_csv(systems: list[dict], path: Path) -> None:
    columns = ["system"] + [metric for metric, _ in DISPLAY_METRICS]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for system in systems:
            row = {"system": system["name"]}
            row.update({metric: system["summary"].get(metric) for metric, _ in DISPLAY_METRICS})
            writer.writerow(row)


def _write_main_tex(systems: list[dict], path: Path) -> None:
    useful_metrics = [
        (metric, label)
        for metric, label in DISPLAY_METRICS
        if any(system["summary"].get(metric) is not None for system in systems)
    ]
    header = "System & " + " & ".join(_latex_escape(label) for _, label in useful_metrics) + r" \\"
    rows = [header, r"\hline"]
    for system in systems:
        cells = [_latex_escape(system["name"])] + [
            _fmt(system["summary"].get(metric), metric) for metric, _ in useful_metrics
        ]
        rows.append(" & ".join(cells) + r" \\ ")
    cols = "l" + "r" * len(useful_metrics)
    text = "\n".join([
        r"\begin{tabular}{" + cols + "}",
        *rows,
        r"\end{tabular}",
        "",
    ])
    path.write_text(text)


def _write_family_csv(systems: list[dict], path: Path) -> None:
    families = sorted({family for system in systems for family in system["by_family"]})
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["system", "family", "n", "oracle_coverage", "mean_task_score", "execution_success"])
        for system in systems:
            for family in families:
                summary = system["by_family"].get(family) or {}
                writer.writerow([
                    system["name"], family, summary.get("n"), summary.get("oracle_coverage"),
                    summary.get("mean_task_score"), summary.get("execution_success"),
                ])


def _case_scores(system: dict) -> dict[str, float]:
    return {
        str(row["id"]): float(row["task_score"])
        for row in system["cases"]
        if row.get("id") is not None and row.get("task_score") is not None
    }


def _compatible_reference(reference: dict, system: dict) -> str | None:
    ref_fp = reference.get("benchmark_fingerprint")
    other_fp = system.get("benchmark_fingerprint")
    if ref_fp and other_fp and ref_fp != other_fp:
        return "benchmark fingerprint mismatch"
    ref_state = reference.get("oracle_state")
    other_state = system.get("oracle_state")
    if bool(ref_state) != bool(other_state):
        return "oracle state is recorded for only one system"
    if ref_state and other_state and ref_state != other_state:
        return "oracle state mismatch; paired significance requires the same frozen snapshot or same-iteration oracle"
    return None


def _paired_statistics(systems: list[dict], reference_name: str | None) -> dict:
    if len(systems) < 2:
        return {"reference": systems[0]["name"] if systems else None, "comparisons": []}
    if reference_name:
        reference = next((system for system in systems if system["name"] == reference_name), None)
        if reference is None:
            raise SystemExit(f"Reference system {reference_name!r} was not found")
    else:
        reference = next((system for system in systems if "full" in system["name"].lower()), systems[0])

    ref_scores = _case_scores(reference)
    raw = []
    for system in systems:
        if system is reference:
            continue
        compatibility_error = _compatible_reference(reference, system)
        if compatibility_error:
            raw.append({"system": system["name"], "n_common": 0, "error": compatibility_error})
            continue
        scores = _case_scores(system)
        ids = sorted(set(ref_scores) & set(scores))
        if not ids:
            raw.append({"system": system["name"], "n_common": 0, "error": "no common scored cases"})
            continue
        a = [ref_scores[i] for i in ids]
        b = [scores[i] for i in ids]
        bootstrap = paired_bootstrap_ci(a, b, n_boot=10000, seed=1729)
        mcnemar = mcnemar_exact([x >= 0.999999 for x in a], [x >= 0.999999 for x in b])
        raw.append({
            "system": system["name"],
            "n_common": len(ids),
            "oracle_state": reference.get("oracle_state"),
            "reference_minus_system": bootstrap,
            "mcnemar": mcnemar,
        })

    testable = [item for item in raw if "mcnemar" in item]
    corrected = holm_bonferroni([float(item["mcnemar"]["p_value"]) for item in testable]) if testable else []
    for item, correction in zip(testable, corrected):
        item["holm_bonferroni"] = correction
    return {"reference": reference["name"], "oracle_state": reference.get("oracle_state"), "comparisons": raw}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manuscript-ready CSV/LaTeX tables and paired statistics from saved ChatAlchemy result files.")
    parser.add_argument("--system", action="append", required=True, help="LABEL=path.json; may be repeated")
    parser.add_argument("--reference", default=None, help="Exact system label to use as the paired reference")
    parser.add_argument("--out-dir", default="benchmark/paper_tables")
    args = parser.parse_args()

    systems = _load_specs(args.system)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_main_csv(systems, out / "table_main.csv")
    _write_main_tex(systems, out / "table_main.tex")
    _write_family_csv(systems, out / "table_by_family.csv")
    stats = _paired_statistics(systems, args.reference)
    (out / "paired_statistics.json").write_text(json.dumps(stats, indent=2) + "\n")
    manifest = {
        "schema": "ChatAlchemyPaperTables/v2",
        "systems": [system["name"] for system in systems],
        "reference": stats["reference"],
        "oracle_state": stats.get("oracle_state"),
        "files": ["table_main.csv", "table_main.tex", "table_by_family.csv", "paired_statistics.json"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

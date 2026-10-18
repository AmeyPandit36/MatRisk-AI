"""Execute repository notebooks and record verifiable per-notebook outcomes.

Run with ``python -m matrisk.run_pipeline`` from any directory in the project.
The Streamlit app never starts notebooks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from matrisk.data import find_project_root

NOTEBOOKS = [
    "00_dataset_inventory_and_quality_audit.ipynb",
    "01_ds1_material_properties_baseline_tested.ipynb",
    "02_materials_feature_engineering_model_selection_updated.ipynb",
    "03_commodity_forecasting_cross_domain_ablation.ipynb",
    "04_infrastructure_condition_risk_modelling_corrected.ipynb",
    "05_financial_exposure_expected_loss_insurance_risk.ipynb",
    "06_esg_element_price_coverage_tested.ipynb",
    "07_inverse_material_design_cost_constrained_ranking.ipynb",
    "08_consolidated_evaluation_reproducibility_registry.ipynb",
]

# Small, stable completion sentinels for notebooks that publish a run summary.
# Notebook 00 predates the summary convention and has no such sentinel.
EXPECTED_OUTPUTS = {
    NOTEBOOKS[0]: ["ML/outputs/data_audit/dataset_inventory.csv"],
    NOTEBOOKS[1]: ["ML/outputs/notebook_01/run_summary.json"],
    NOTEBOOKS[2]: ["ML/outputs/notebook_02/run_summary.json"],
    NOTEBOOKS[3]: ["ML/outputs/notebook_03/run_summary.json"],
    NOTEBOOKS[4]: ["ML/outputs/notebook_04/run_summary.json"],
    NOTEBOOKS[5]: ["ML/outputs/notebook_05/run_summary.json"],
    NOTEBOOKS[6]: ["ML/outputs/notebook_06/run_summary.json"],
    NOTEBOOKS[7]: ["ML/outputs/notebook_07/run_summary.json"],
    NOTEBOOKS[8]: ["ML/outputs/notebook_08/run_summary.json"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _previous_records(ledger: Path) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    if ledger.exists():
        with ledger.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                    latest[record["notebook"]] = record
                except (ValueError, KeyError):
                    continue
    return latest


def run(notebooks: list[str], root: Path, timeout: int = 900) -> int:
    notebook_dir = root / "ML" / "notebooks"
    output_dir = root / "ML" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = output_dir / "execution_ledger.jsonl"
    previous = _previous_records(ledger)
    run_id = str(uuid.uuid4())
    dataset_hashes = {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted((root / "Data" / "raw").glob("*.csv"))
    }
    revision = None
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    failures = 0
    for name in notebooks:
        notebook = notebook_dir / name
        start = now()
        tracked_output_dirs = [output_dir, notebook_dir / "outputs"]
        before = {
            p: p.stat().st_mtime_ns
            for folder in tracked_output_dirs if folder.exists()
            for p in folder.rglob("*") if p.is_file() and p != ledger
        }
        command = [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", f"--ExecutePreprocessor.timeout={timeout}", name]
        status: str
        code: int | None
        error: str | None
        failure_type: str | None = None
        try:
            result = subprocess.run(command, cwd=notebook_dir, capture_output=True, text=True, timeout=timeout + 60, check=False)
            code = result.returncode
            status = "success" if code == 0 else "failure"
            error = None if code == 0 else (result.stderr or result.stdout or f"Notebook process exited with code {code}")[-6000:]
            if code != 0:
                failure_type = "NonZeroExit"
        except subprocess.TimeoutExpired as exc:
            status, code, failure_type = "interrupted", None, "TimeoutExpired"
            details = exc.stderr or exc.stdout or str(exc)
            error = f"TimeoutExpired: {details}"[-6000:]
        except OSError as exc:
            status, code, failure_type = "failure", None, type(exc).__name__
            error = f"{type(exc).__name__}: {exc}"[-6000:]

        outputs = []
        for folder in tracked_output_dirs:
            if not folder.exists():
                continue
            for path in folder.rglob("*"):
                if path.is_file() and path != ledger and (path not in before or path.stat().st_mtime_ns != before[path]):
                    outputs.append(path.relative_to(root).as_posix())
        expected = EXPECTED_OUTPUTS.get(name, [])
        expected_present = [path for path in expected if (root / Path(path)).is_file()]
        missing_expected = [path for path in expected if path not in expected_present]
        prior_hashes = previous.get(name, {}).get("input_sha256", {})
        changed_inputs = sorted(path for path, digest in dataset_hashes.items() if path in prior_hashes and prior_hashes[path] != digest)
        added_inputs = sorted(path for path in dataset_hashes if path not in prior_hashes)
        removed_inputs = sorted(path for path in prior_hashes if path not in dataset_hashes)
        output_status = "generated" if outputs else ("expected_present_but_not_generated" if expected_present else "missing_expected_outputs")
        if missing_expected and expected_present:
            output_status = "some_expected_outputs_missing"
        completed = now()
        record = {
            "run_id": run_id, "notebook": name, "started_at_utc": start, "completed_at_utc": completed,
            "status": status, "return_code": code, "failure_type": failure_type,
            "command": command, "working_directory": "ML/notebooks",
            "input_sha256": dataset_hashes, "input_changes_since_previous_run": {"changed": changed_inputs, "added": added_inputs, "removed": removed_inputs},
            "code_revision": revision, "expected_outputs": expected, "expected_outputs_present": expected_present,
            "missing_expected_outputs": missing_expected, "outputs_changed_during_run": sorted(outputs),
            "output_status": output_status,
            "validation": "Status reflects notebook process completion only; output presence is reported separately and scientific validity is not certified.",
            "error": error,
        }
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"{name}: {status} ({'no exit code' if code is None else code}); outputs={output_status}")
        failures += status != "success"
    print(f"Execution ledger: {ledger.relative_to(root)}; run_id={run_id}")
    return 1 if failures else 0


def main() -> int:
    root = find_project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="*", choices=NOTEBOOKS, help="Notebook filenames; default runs 00–08 in dependency order.")
    parser.add_argument("--timeout", type=int, default=900, help="Notebook cell timeout in seconds (default: 900).")
    args = parser.parse_args()
    return run(args.notebooks or NOTEBOOKS, root, max(1, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())

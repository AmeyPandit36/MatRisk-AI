import json
from pathlib import Path

import pandas as pd

from matrisk.data import find_project_root


def test_notebook_01_output_contract_and_group_integrity():
    root = find_project_root()
    output = root / "ML/outputs/notebook_01"
    summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
    metrics = pd.read_csv(output / "metrics.csv")
    assert summary["train_rows"] > 0 and summary["test_rows"] > 0
    assert summary["group_overlap"] == 0
    assert summary["chemical_system_overlap"] == 0
    assert summary["material_id_overlap"] == 0
    assert set(metrics.target) == set(summary["targets"])


def test_material_models_do_not_beat_mean_baseline_on_selected_test_mae():
    root = find_project_root()
    metrics = pd.read_csv(root / "ML/outputs/notebook_01/metrics.csv")
    for _, target_rows in metrics.groupby("target"):
        baseline = target_rows.loc[target_rows.model == "DummyMean", "MAE"].iloc[0]
        assert (target_rows.loc[target_rows.model != "DummyMean", "MAE"] >= baseline).all()


def test_commodity_split_is_chronological_and_partition_counts_reconcile():
    root = find_project_root()
    split = pd.read_csv(root / "ML/outputs/notebook_03/chronological_split_report.csv", parse_dates=["train_end", "validation_end", "test_start"])
    assert (split.train_end < split.validation_end).all()
    assert (split.validation_end < split.test_start).all()
    assert (split.train_n + split.validation_n + split.test_n == split.n).all()


def test_consolidated_registry_contract_has_no_missing_expected_artifacts():
    root = find_project_root()
    inventory = pd.read_csv(root / "ML/outputs/notebook_08/artifact_inventory.csv")
    summary = json.loads((root / "ML/outputs/notebook_08/run_summary.json").read_text(encoding="utf-8"))
    assert len(inventory) == summary["artifact_checks"]["expected_artifacts"]
    assert (inventory.status == "found").all()
    assert summary["summary_checks"]["readable_summaries"] == summary["summary_checks"]["notebooks_expected"]

from pathlib import Path

import pandas as pd

from matrisk.data import DATASETS, dataset_path, find_project_root, read_dataset


def test_root_discovery_from_nested_directory():
    root = find_project_root(Path(__file__).parent)
    assert (root / "Data").is_dir()
    assert (root / "ML").is_dir()


def test_dataset_path_is_repository_relative():
    root = find_project_root()
    assert dataset_path("DS1", root) == root / "Data" / "raw" / DATASETS["DS1"][0]


def test_all_supplied_csvs_match_minimum_schema():
    for key in DATASETS:
        frame, error = read_dataset(key)
        assert error is None
        assert frame is not None and not frame.empty


def test_missing_dataset_returns_recovery_message(tmp_path):
    (tmp_path / "Data/raw").mkdir(parents=True)
    (tmp_path / "ML").mkdir()
    frame, error = read_dataset("DS1", tmp_path)
    assert frame is None
    assert "Restore it under Data/raw" in error


def test_malformed_schema_is_reported(tmp_path):
    (tmp_path / "Data/raw").mkdir(parents=True)
    (tmp_path / "ML").mkdir()
    pd.DataFrame({"wrong": [1]}).to_csv(dataset_path("DS1", tmp_path), index=False)
    frame, error = read_dataset("DS1", tmp_path)
    assert frame is None
    assert "unexpected schema" in error

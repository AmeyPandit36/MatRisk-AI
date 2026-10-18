"""Repository-relative, schema-checked access to MatRisk AI data and outputs."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

DATASETS = {
    "DS1": ("DS1_material_properties_5500.csv", {"material_id", "formula", "formation_energy_per_atom_eV", "band_gap_eV", "bulk_modulus_GPa", "shear_modulus_GPa"}),
    "DS2": ("DS2_commodity_prices_10yr.csv", {"date", "commodity", "close"}),
    "DS3": ("DS3_infrastructure_bridges_5000.csv", {"bridge_id", "condition_rating", "replacement_cost_M"}),
    "DS4": ("DS4_crossdomain_features_daily.csv", {"date", "commodity"}),
    "DS5": ("DS5_element_prices_monthly.csv", {"date", "element", "price_usd_per_kg"}),
    "DS6": ("DS6_historical_failures_2000.csv", {"event_id", "event_year", "repair_cost_USD"}),
}


def find_project_root(start: Path | None = None) -> Path:
    """Find the repository root by its Data and ML directories, with optional override."""
    override = os.getenv("MATRISK_PROJECT_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        if (candidate / "Data").is_dir() and (candidate / "ML").is_dir():
            return candidate
        raise FileNotFoundError("MATRISK_PROJECT_ROOT must contain Data/ and ML/.")
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "Data").is_dir() and (candidate / "ML").is_dir():
            return candidate
    raise FileNotFoundError("Could not locate project root containing Data/ and ML/.")


def dataset_path(key: str, root: Path | None = None) -> Path:
    if key not in DATASETS:
        raise KeyError(f"Unknown dataset key: {key}")
    return (root or find_project_root()) / "Data" / "raw" / DATASETS[key][0]


def read_dataset(key: str, root: Path | None = None) -> tuple[pd.DataFrame | None, str | None]:
    """Return a dataset or a user-safe availability/schema message."""
    path = dataset_path(key, root)
    if not path.is_file():
        return None, f"{key} is unavailable. Expected file: {path.name}. Restore it under Data/raw and refresh."
    try:
        frame = pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        return None, f"{key} could not be read ({type(exc).__name__}). Check the CSV format and refresh."
    missing = DATASETS[key][1] - set(frame.columns)
    if missing:
        return None, f"{key} has an unexpected schema. Missing columns: {', '.join(sorted(missing))}."
    return frame, None


def read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None

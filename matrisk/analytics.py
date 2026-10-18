"""Small, deterministic display transformations used by the MatRisk dashboard."""
from __future__ import annotations

import numpy as np
import pandas as pd
import re


def histogram_frame(values: pd.Series, bins: int = 30) -> pd.DataFrame:
    """Bin finite numeric observations into readable histogram counts."""
    numeric = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if numeric.empty:
        return pd.DataFrame({"bin_midpoint": pd.Series(dtype=float), "count": pd.Series(dtype=int), "bin_label": pd.Series(dtype=str)})
    counts, edges = np.histogram(numeric.to_numpy(), bins=max(1, int(bins)))
    if np.all(numeric.to_numpy() == numeric.iloc[0]):
        edges = np.linspace(float(numeric.iloc[0]) - 0.5, float(numeric.iloc[0]) + 0.5, max(1, int(bins)) + 1)
        counts, edges = np.histogram(numeric.to_numpy(), bins=edges)
    labels = [f"{edges[i]:.3g} – {edges[i + 1]:.3g}" for i in range(len(counts))]
    return pd.DataFrame({"bin_midpoint": (edges[:-1] + edges[1:]) / 2, "count": counts, "bin_label": labels})


def element_price_series(frame: pd.DataFrame, elements: list[str], indexed: bool = False) -> pd.DataFrame:
    """Return long-form element prices, optionally indexed to each series' first valid price = 100."""
    cols = ["date", "element", "price_usd_per_kg"]
    data = frame.loc[frame["element"].isin(elements), cols].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["price_usd_per_kg"] = pd.to_numeric(data["price_usd_per_kg"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=cols).sort_values(["element", "date"])
    if indexed:
        first = data.groupby("element")["price_usd_per_kg"].transform("first")
        data["value"] = data["price_usd_per_kg"].div(first).mul(100).where(first.ne(0))
    else:
        data["value"] = data["price_usd_per_kg"]
    return data


def indexed_price_series(frame: pd.DataFrame, commodities: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Index each selected commodity to its first finite positive observation in the filtered window."""
    data = frame.loc[frame["commodity"].isin(commodities), ["date", "commodity", "close"]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["date"]).sort_values(["commodity", "date"])
    indexed, invalid = [], []
    for name, group in data.groupby("commodity", sort=True):
        group = group.copy()
        valid = group["close"].notna() & group["close"].gt(0)
        if not valid.any():
            invalid.append(str(name))
            continue
        first_idx = valid[valid].index[0]
        base = float(group.loc[first_idx, "close"])
        group["index"] = group["close"].div(base).mul(100).where(group["close"].gt(0))
        group["base_date"] = group.loc[first_idx, "date"]
        indexed.append(group)
    result = pd.concat(indexed, ignore_index=True) if indexed else pd.DataFrame(columns=["date", "commodity", "close", "index", "base_date"])
    return result, invalid


def valid_condition_records(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split raw bridge records into documented 1–9 ratings and invalid/out-of-range records."""
    ratings = pd.to_numeric(frame["condition_rating"], errors="coerce")
    valid_mask = ratings.between(1, 9) & ratings.eq(ratings.round())
    return frame.loc[valid_mask].copy(), frame.loc[~valid_mask].copy()


def element_price_coverage(materials: pd.DataFrame, prices: pd.DataFrame) -> dict:
    """Recalculate complete latest-positive-price coverage from current DS1/DS5 source frames.

    Formula handling follows Notebook 06's flat-formula rule; unsupported syntax is not guessed.
    """
    pattern = re.compile(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)")
    source = prices.copy()
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    source["element"] = source["element"].astype(str).str.strip()
    source["price_usd_per_kg"] = pd.to_numeric(source["price_usd_per_kg"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    usable = source[source["price_usd_per_kg"].gt(0) & source["element"].ne("") & source["date"].notna()]
    latest = usable["date"].max()
    current_elements = set(usable.loc[usable["date"].eq(latest), "element"])
    element_symbols = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split())
    def parsed_elements(formula):
        if pd.isna(formula):
            return None
        value = str(formula).strip()
        matches = list(pattern.finditer(value))
        if not value or any(c in value for c in "()[]+-/") or not matches or "".join(m.group(0) for m in matches) != value:
            return None
        elements = set()
        for match in matches:
            symbol, quantity = match.groups()
            try:
                amount = float(quantity) if quantity else 1.0
            except ValueError:
                return None
            if symbol not in element_symbols:
                return None
            if amount <= 0:
                return None
            elements.add(symbol)
        return elements
    parsed = materials["formula"].map(parsed_elements)
    complete = parsed.map(lambda e: e is not None and e.issubset(current_elements))
    return {
        "total_material_rows": int(len(materials)),
        "formula_parse_success_rows": int(parsed.notna().sum()),
        "complete_coverage_rows": int(complete.sum()),
        "coverage_rate": float(complete.mean()) if len(complete) else float("nan"),
        "latest_price_date": latest.date().isoformat() if pd.notna(latest) else None,
        "elements_with_latest_price": int(usable.loc[usable["date"].eq(latest), "element"].nunique()) if pd.notna(latest) else 0,
    }


def chronological_prices(frame: pd.DataFrame, commodities: list[str], start, end) -> pd.DataFrame:
    """Filter commodity prices inclusively and preserve ascending time order."""
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    mask = data["commodity"].isin(commodities) & data["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    return data.loc[mask].sort_values(["date", "commodity"])

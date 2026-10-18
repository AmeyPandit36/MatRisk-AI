# MatRisk AI — Tested DS Notebook Starter

## Included
- `notebooks/00_dataset_inventory_and_quality_audit.ipynb`: profiles the six CSVs, key integrity, and known data-quality risks.
- `notebooks/01_ds1_material_properties_baseline.ipynb`: tests a mean baseline, Random Forest, Extra Trees, and HistGradientBoosting for four DS-1 targets.
- `outputs/data_audit/`: dataset inventory and quality findings from the actual supplied files.
- `outputs/ds1_baseline/`: metrics and physical/data audit outputs from the actual supplied DS-1 run.

## How to run in your repository
1. Put the six CSV files under `data/raw/`.
2. Open the notebooks from the repository root.
3. Install dependencies listed in `requirements.txt`.
4. Run Notebook 00, then Notebook 01 from top to bottom.

The notebooks also search `/mnt/data` as a convenience for the current execution environment; repository execution should use `data/raw/`.

## DS-1 tested result (fixed grouped split)
A 80/20 `GroupShuffleSplit` was made by chemical-system element-set, with 4,334 training and 1,166 test rows and zero group overlap. On this split, the composition-only models did **not** beat the mean baseline consistently. This is an important negative result, not a successful production model.

| Target | Mean baseline MAE | Best non-baseline MAE in this run | Note |
|---|---:|---:|---|
| Formation energy (eV/atom) | 1.2123 | 1.2317 (Random Forest) | Mean baseline better |
| Band gap (eV) | 1.9921 | 1.9687 (Random Forest) | Small MAE improvement, but R² remains negative |
| Bulk modulus (GPa) | 67.3478 | 68.9065 (HistGradientBoosting) | Mean baseline better |
| Shear modulus (GPa) | 40.4496 | 41.6970 (Random Forest) | Mean baseline better |

Do not describe these as validated materials models. Next steps are to investigate data provenance/labels and test richer, scientifically valid features with repeated grouped evaluation.

## Known dataset warnings from the audit
- DS-1: 21 duplicate `material_id` rows; 1,765 rows have >5% disagreement between elastic modulus inferred from K/G/Poisson ratio; 369 rows labeled stable have formation energy >= 0. These need investigation, not silent correction.
- DS-2 and DS-4: date/commodity keys align with no duplicate keys; time-series modelling still requires walk-forward splits and forward-shifted targets.
- DS-3: five rows have condition rating 0 although the README says the scale is 1–9. No observed event-time/censoring cohort is available in this snapshot.
- DS-5: monthly element prices are present; element/formula price coverage needs a dedicated coverage audit before cost-aware design.
- DS-6: event-only records cannot estimate population failure probability without non-failure/exposure data; 85 rows have repair cost above replacement value.

## Scope and limitations
- No crystal coordinates/structures are supplied in DS-1, so this is not a CGNN.
- The formula parser handles flat chemical formulas only.
- The current test split holds out chemical-system groups; its difficulty is higher than a random row split and better exposes out-of-system generalization.
- Results are from this environment's Python/scikit-learn versions. Re-run in your repository and record package versions before committing final metrics.

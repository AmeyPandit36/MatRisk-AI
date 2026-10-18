# MatRisk AI implementation and acceptance report

## Acceptance summary

This pass verified the current source data and existing artifacts, hardened the opt-in notebook runner, added runner regression tests, reviewed the analytical claims in the seven-page Streamlit app, rewrote the README from verified repository details and the supplied project brief, and removed the redundant sidebar Data Snapshot component. The notebooks were **not** executed against project data. No data, notebooks, or existing analytical outputs were changed.

## Tests and exact commands

- `python -m py_compile app.py matrisk\analytics.py matrisk\run_pipeline.py matrisk\data.py tests\test_data.py tests\test_pipeline_outputs.py tests\test_analytics.py tests\test_assets.py tests\test_run_pipeline.py` — passed.
- `python -m pytest -q --basetemp='.pytest-readme-20261018'` — **22 passed, 0 failed, 0 skipped**.
- `python -m matrisk.run_pipeline 01_ds1_material_properties_baseline_tested.ipynb` — run twice with `MATRISK_PROJECT_ROOT` pointing to a temporary project and a stub `jupyter` module on `PYTHONPATH`; first returned 0/success and second returned 1/failure (exit 6). No notebook code ran. Existing expected output remained unchanged and was marked `expected_present_but_not_generated`.

The pytest suite also simulates a nonzero notebook exit and a `TimeoutExpired`, checks UTC start/completion timestamps, input hashes and changed-input reporting, and distinguishes expected outputs missing or pre-existing from outputs changed during the run.

Seven Streamlit `AppTest` runs — one for each named page — completed with no app exceptions and confirmed the seven navigation options. AppTest verifies app-level rendering only; it is not browser visual verification. The process emitted a Windows temporary-directory cleanup `PermissionError` during interpreter shutdown after the page runs completed.

README verification checked the supplied author/contact details, all **16** relative file links (zero broken), and actual sidebar source code (all three Data Snapshot strings absent). Python compilation passed for the changed Python files.

## Runner evidence and semantics

`python -m matrisk.run_pipeline` is the explicit full-run command. It executes notebooks 00–08 in dependency order with `nbconvert --execute --inplace`; this can modify notebooks and outputs. Optional scope and timeout syntax is `python -m matrisk.run_pipeline <notebook-filename> --timeout 900`. Do not run it casually against production artifacts.

The JSONL ledger records actual process status, return code, UTC start/completion, command, input SHA-256 values, changed/added/removed raw inputs since that notebook's previous record, Git revision when available, expected outputs, missing outputs, and output paths changed during that invocation. Nonzero exits are `failure`; subprocess timeouts are `interrupted` and include failure details. A zero exit remains a recorded process success even if expected outputs are absent; that condition is separately shown as `missing_expected_outputs`. Existing expected artifacts that did not change are `expected_present_but_not_generated`; they are never evidence of a successful current execution. `outputs_changed_during_run` reflects observed file timestamp changes within the tracked output directories, not scientific validity. Notebook 00's stable sentinel is `data_audit/dataset_inventory.csv`; notebooks 01–08 use their `run_summary.json`.

The current project has no acceptance-run ledger because real notebooks were intentionally not run. Therefore the app correctly reports execution status and artifact freshness as unknown. A process exit of zero does not validate a notebook's scientific method or its output content.

## Independent source-data checks

- **DS1/DS5 elemental-price coverage:** recalculated from `Data/raw/DS1_material_properties_5500.csv` and `Data/raw/DS5_element_prices_monthly.csv` using the app's flat-formula parser and latest-date positive-price rule. All **5,500/5,500** formulas parse under that rule; **1,795** formulas contain only elements with positive prices on latest available date **2024-12-01**. Numerator/denominator: **1,795/5,500 = 32.63636%**; UI formats this as **32.6%**. There are **40** elements priced on that date. Formula syntax with groups, charges, or unsupported characters is not guessed; no such rows occur in this current DS1 file.
- **DS3 condition policy:** source has **5,000** rows: **4,995** integer ratings in documented range 1–9 and **5** out-of-scale zero ratings. No rating values are missing. All five are excluded from condition summaries/charts and remain available as unchanged raw records in the data-quality expander.
- **DS2/DS4 join:** exact documented keys are `(date, commodity)`. Each file has **22,952** rows, **22,952** unique keys, zero duplicate key rows/groups, zero missing key cells, **22,952** matched keys, and zero unmatched keys on either side. Both cover **2,869** identical dates from **2014-01-02 through 2024-12-31** and the same eight commodities. Joined-field nulls are rolling-window warm-up gaps: DS2 `daily_return` 8, `return_5d` and `volatility_5d_ann` 40 each, `return_21d` and `volatility_21d_ann` 168 each, `volatility_63d_ann` 504, `sma_21`/Bollinger bands 160 each, `sma_63`/`bollinger_z` 496 each, `rsi_14` 112, `momentum_10d` 80, `momentum_21d` 168; DS4 `mqi_5d_trend` 40, `mqi_21d_trend` 168, `mqi_63d_trend` 504. These missing values predate the join and were not filled. Exact date alignment does not establish point-in-time availability or causality.
- **Infrastructure accounting cross-check:** DS3 source sums match saved Notebook 05 totals: replacement cost **3,409.35 million source units**, outstanding loans **1,876.84 million source units**, and annual premiums **56,385.1 thousand source units**. The source does not document currency; none is inferred.

## Claim review

Overview and analysis-page copy consistently distinguishes observations, saved model outputs, hypothetical scenarios, and unknown artifact freshness. The saved material evaluation selected `DummyMean` for all four targets. The saved commodity evaluation selects the zero-return baseline; held-out R² is approximately **−0.000216** over **3,448** saved rows. The UI labels this experimental and explicitly says it does not establish predictive skill or trading profitability. Infrastructure analysis is described as cross-sectional condition diagnostics and hypothetical gross-loss scenarios, not calibrated failure forecasts or expected loss. Material rankings are a heuristic over existing records, not generated designs. The DS2/DS4 view is described as descriptive rather than causal. No additional overclaim was found that required a code change in this pass.

## Browser verification and blockers

The seven Streamlit pages are Overview, Materials Intelligence, Commodity Intelligence, Infrastructure Risk, ESG & Sustainability, Model Laboratory, and Data Quality & Runs. A live Streamlit process was started with `python -m streamlit run app.py --server.headless true --server.port 8501`, but the health request to `http://127.0.0.1:8501/_stcore/health` failed with Windows socket permission denial: “An attempt was made to access a socket in a way forbidden by its access permissions.” The server was stopped. Thus desktop/narrow viewport browser inspection, visual chart/legend/axis checks, control interactions, sidebar layout, asset rendering, and readability were **not verified in a browser**. AppTest is not claimed as a substitute.

## README and sidebar changes

Replaced the short README with a project document covering the original brief's broad educational intent while clearly marking proposed GNN/PINN, survival, GAN, and simulation concepts as unimplemented. It includes the supplied author and academic details, seven page summaries, actual CSV schemas/counts and known units/missingness, verified DS2/DS4 alignment and DS1/DS5 coverage, technical architecture, Windows setup, notebook/pipeline semantics, testing caveats, scientific limitations, repository structure, troubleshooting, future work, and the absence of a repository license. All 16 local relative links resolve. The original PDF under `initial doc/` was located and text-extracted; it is marked private/confidential, so the README uses a high-level summary without republishing its detailed contents. Current CSV provenance remains undocumented.

Removed the sidebar divider and all three Data Snapshot captions from `app.py`. The logo, branding caption, native seven-page radio navigation, active-page styling, and existing visual identity remain.

## Defects fixed in this acceptance pass

- Runner timeouts now record `interrupted` and `TimeoutExpired` details rather than being conflated with ordinary process failure.
- Ledger distinguishes changed outputs from merely existing files, records expected and missing outputs, and compares input hashes with the prior record for that notebook.
- Added `tests/test_run_pipeline.py` for success, failure, timeout/interruption, stale artifacts, missing outputs, and changed inputs.
- Removed the redundant sidebar snapshot block and added a source regression test ensuring it stays removed while seven-page navigation remains.

## Remaining limitations and commands

Browser visual verification remains blocked by localhost socket policy. The existing saved artifacts do not prove current-run freshness. Full notebook execution, model retraining, and notebook validity were intentionally not exercised during this acceptance pass. The repository contains no `LICENSE` file, and the six CSV datasets lack verifiable upstream provenance metadata.

From the project root:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
python -m py_compile app.py matrisk\analytics.py matrisk\run_pipeline.py matrisk\data.py tests\test_data.py tests\test_pipeline_outputs.py tests\test_analytics.py tests\test_assets.py tests\test_run_pipeline.py
python -m pytest -q --basetemp='.pytest-acceptance-20261018'
```

For explicit full notebook execution (in-place effects):

```powershell
python -m matrisk.run_pipeline
```

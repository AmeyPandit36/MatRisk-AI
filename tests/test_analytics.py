import pandas as pd

from matrisk.analytics import (chronological_prices, element_price_coverage,
                               element_price_series, histogram_frame,
                               indexed_price_series, valid_condition_records)
from matrisk.data import find_project_root


def test_histogram_bins_finite_numeric_values_without_changing_observations():
    result = histogram_frame(pd.Series([0, 1, 2, None, float("inf")]), bins=2)
    assert result["count"].sum() == 3
    assert len(result) == 2
    assert list(result.columns) == ["bin_midpoint", "count", "bin_label"]


def test_histogram_handles_constant_and_empty_values():
    constant=histogram_frame(pd.Series([4.0,4.0,4.0]),bins=8)
    empty=histogram_frame(pd.Series([None,float("inf")]),bins=8)
    assert constant["count"].sum()==3 and len(constant)==8
    assert empty.empty


def test_element_index_uses_each_series_first_observation_as_100():
    data = pd.DataFrame({"date": ["2024-01-01", "2024-02-01", "2024-01-01", "2024-02-01"],
                         "element": ["A", "A", "B", "B"],
                         "price_usd_per_kg": [10, 20, 100, 50]})
    result = element_price_series(data, ["A", "B"], indexed=True)
    assert result.groupby("element").first()["value"].to_dict() == {"A": 100.0, "B": 100.0}
    assert result.groupby("element").last()["value"].to_dict() == {"A": 200.0, "B": 50.0}


def test_element_index_does_not_normalize_zero_base():
    data=pd.DataFrame({"date":["2024-01-01","2024-02-01"],"element":["A","A"],"price_usd_per_kg":[0,12]})
    result=element_price_series(data,["A"],indexed=True)
    assert result.value.isna().all()


def test_chronological_price_filter_is_inclusive_and_sorted():
    data = pd.DataFrame({"date": ["2024-02-01", "2024-01-01", "2024-03-01"],
                         "commodity": ["A", "A", "B"], "close": [2, 1, 3]})
    result = chronological_prices(data, ["A"], "2024-01-01", "2024-02-01")
    assert list(result["close"]) == [1, 2]


def test_commodity_index_skips_invalid_start_and_reports_series_without_valid_base():
    frame=pd.DataFrame({"date":["2024-01-01","2024-02-01","2024-01-01"],"commodity":["A","A","B"],"close":[0,10,float("inf")]})
    indexed,invalid=indexed_price_series(frame,["A","B"])
    assert indexed.commodity.unique().tolist()==["A"]
    valid=indexed[indexed["index"].notna()].iloc[0]
    assert valid["index"]==100
    assert valid["base_date"]==pd.Timestamp("2024-02-01")
    assert invalid==["B"]


def test_condition_zero_is_preserved_as_invalid_not_in_valid_condition_view():
    frame=pd.DataFrame({"bridge_id":["a","b","c"],"condition_rating":[0,1,9]})
    valid,invalid=valid_condition_records(frame)
    assert valid.bridge_id.tolist()==["b","c"]
    assert invalid.bridge_id.tolist()==["a"]
    assert invalid.condition_rating.iloc[0]==0


def test_material_price_coverage_is_recomputed_from_current_source_datasets():
    root=find_project_root()
    materials=pd.read_csv(root/"Data/raw/DS1_material_properties_5500.csv")
    prices=pd.read_csv(root/"Data/raw/DS5_element_prices_monthly.csv")
    result=element_price_coverage(materials,prices)
    assert result["total_material_rows"]==5500
    assert result["complete_coverage_rows"]==1795
    assert result["latest_price_date"]=="2024-12-01"
    assert result["elements_with_latest_price"]==40


def test_ds2_ds4_exact_key_coverage_and_source_exposure_sums():
    root=find_project_root()
    ds2=pd.read_csv(root/"Data/raw/DS2_commodity_prices_10yr.csv",usecols=["date","commodity"])
    ds4=pd.read_csv(root/"Data/raw/DS4_crossdomain_features_daily.csv",usecols=["date","commodity"])
    for frame in [ds2,ds4]: frame["date"]=pd.to_datetime(frame.date,errors="coerce")
    left=ds2.dropna().drop_duplicates();right=ds4.dropna().drop_duplicates()
    matched=left.merge(right,on=["date","commodity"],how="inner",validate="one_to_one")
    assert len(matched)==len(left)==len(right)==22952
    ds3=pd.read_csv(root/"Data/raw/DS3_infrastructure_bridges_5000.csv")
    saved=pd.read_csv(root/"ML/outputs/notebook_05/portfolio_exposure_summary.csv").iloc[0]
    assert abs(ds3.replacement_cost_M.sum()-saved.replacement_cost_total_M)<1e-8
    assert abs(ds3.loan_outstanding_M.sum()-saved.loan_outstanding_total_M)<1e-8
    assert abs(ds3.insurance_premium_K_yr.sum()-saved.annual_premium_total_K)<1e-8

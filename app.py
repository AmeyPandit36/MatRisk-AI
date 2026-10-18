from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from matrisk.analytics import (chronological_prices, element_price_coverage,
                               element_price_series, histogram_frame,
                               indexed_price_series, valid_condition_records)
from matrisk.data import DATASETS, find_project_root, read_dataset, read_json

ROOT = find_project_root()
ASSETS = ROOT / "assets"
PAGES = ["Overview", "Materials Intelligence", "Commodity Intelligence", "Infrastructure Risk", "ESG & Sustainability", "Model Laboratory", "Data Quality & Runs"]
ICONS = ["overview", "materials", "commodity", "infrastructure", "esg", "models", "quality"]
COLORS = ["#35D7F2", "#8C7BFF", "#F2B866", "#50D6AE", "#F07B78", "#6FA8FF", "#AAB7C7"]

st.set_page_config(page_title="MatRisk AI | Scientific & Financial Intelligence", page_icon=str(ASSETS / "brand" / "favicon.svg"), layout="wide", initial_sidebar_state="expanded")

def svg_data(path: Path) -> str:
    """Resolve local SVGs when present; return an empty string for optional assets."""
    try:
        import base64
        return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""

def inject_theme() -> None:
    hero = svg_data(ASSETS / "backgrounds" / "overview-hero.svg")
    st.markdown(f"""<style>
    :root{{--bg:#080D16;--surface:#111A28;--surface2:#151F2E;--line:#253449;--cyan:#35D7F2;--ink:#E8F0F7;--muted:#A7B5C7;--green:#62D6A7;--amber:#F2B866;--red:#F07B78;--radius:14px;--space:1rem;--shadow:0 14px 32px rgba(0,0,0,.18);--motion:220ms}}
    .stApp{{background:radial-gradient(ellipse at 80% -15%,rgba(24,83,121,.22),transparent 40%),var(--bg);color:var(--ink)}}
    [data-testid="stSidebar"]{{background:linear-gradient(180deg,#0D1624,#0A111C);border-right:1px solid var(--line)}}
    [data-testid="stSidebar"] *{{color:var(--ink)}}
    [data-testid="stSidebar"] [data-testid="stRadio"] label{{border-radius:8px;padding:.45rem .6rem;border-left:2px solid transparent;transition:background var(--motion),transform var(--motion)}}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){{background:#13283A;border-left-color:var(--cyan)}}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover{{background:#17263A;transform:translateX(2px)}}
    [data-testid="stMetric"]{{background:linear-gradient(145deg,#121D2C,#101927);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow)}}
    [data-testid="stMetricLabel"]{{color:var(--muted)}}
    [data-testid="stMetricValue"]{{font-weight:680;letter-spacing:-.035em}}
    [data-testid="stVerticalBlockBorderWrapper"]{{border-color:var(--line)!important;border-radius:var(--radius)!important}}
    div[data-testid="stButton"] button,div[data-testid="stDownloadButton"] button{{border:1px solid #35516A;border-radius:9px;transition:all var(--motion)}}
    div[data-testid="stButton"] button:hover,div[data-testid="stDownloadButton"] button:hover{{border-color:var(--cyan);color:var(--cyan);transform:translateY(-1px)}}
    :focus-visible{{outline:2px solid var(--cyan)!important;outline-offset:2px}}
    h1,h2,h3{{letter-spacing:-.035em}} h1{{font-size:clamp(1.8rem,3vw,2.5rem)}}
    .eyebrow{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan);font-weight:650;margin-bottom:.3rem}}
    .hero{{background-color:#0E1A2A;background-image:linear-gradient(90deg,rgba(8,13,22,.97) 4%,rgba(8,13,22,.82) 60%,rgba(8,13,22,.4)),url('{hero}');background-position:center;background-size:cover;border:1px solid #263A50;border-radius:16px;padding:1.2rem clamp(1.2rem,2.5vw,2rem);margin:.1rem 0 .8rem;box-shadow:var(--shadow);min-height:0}}
    .hero p{{max-width:52rem;color:#B9C8D8;font-size:.96rem;line-height:1.5;margin-bottom:.3rem}}
    .module-icon{{width:22px;height:22px;vertical-align:-5px;margin-right:8px}}
    .section-note{{color:var(--muted);font-size:.88rem;line-height:1.5}}
    .signal{{border-left:3px solid var(--cyan);padding:.15rem 0 .15rem .85rem;color:#C7D4E2}}
    [data-testid="stDataFrame"]{{border:1px solid var(--line);border-radius:10px;overflow:hidden}}
    @keyframes enter{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:translateY(0)}}}}
    .block-container{{animation:enter 340ms ease-out both;padding-top:1.35rem;padding-bottom:2rem}}
    @media(max-width:800px){{.block-container{{padding-left:1rem;padding-right:1rem}}.hero{{background-position:70% center}}}}
    @media(max-width:1100px){{[data-testid="stHorizontalBlock"]{{flex-wrap:wrap;gap:.75rem}}[data-testid="stHorizontalBlock"]>[data-testid="column"]{{min-width:min(100%,260px)!important}}}}
    @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;transition:none!important;scroll-behavior:auto!important}}}}
    </style>""", unsafe_allow_html=True)

inject_theme()

@st.cache_data(show_spinner=False)
def load_dataset(key: str, modified: int):
    return read_dataset(key, ROOT)

@st.cache_data(show_spinner=False)
def current_price_coverage(material_mtime: int, price_mtime: int):
    materials = pd.read_csv(ROOT / "Data" / "raw" / DATASETS["DS1"][0])
    prices = pd.read_csv(ROOT / "Data" / "raw" / DATASETS["DS5"][0])
    return element_price_coverage(materials, prices)

def execution_ledger():
    path = output("execution_ledger.jsonl")
    if not path.is_file():
        return None, None
    records=[];line_no=0
    try:
        for line_no,line in enumerate(path.read_text(encoding="utf-8").splitlines(),start=1):
            if line.strip():
                records.append(json.loads(line))
    except (OSError, ValueError) as exc:
        return None, f"Execution ledger could not be parsed ({type(exc).__name__}, line {line_no})."
    return records, None

def dataset(key: str) -> pd.DataFrame | None:
    path = ROOT / "Data" / "raw" / DATASETS[key][0]
    frame, error = load_dataset(key, path.stat().st_mtime_ns if path.exists() else 0)
    if error:
        st.warning(error)
    return frame

def output(name: str) -> Path:
    return ROOT / "ML" / "outputs" / name

def read_csv(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path) if path.is_file() else None
    except (OSError, pd.errors.ParserError, UnicodeError):
        return None

def artifact_check(relative: str) -> tuple[bool,bool,str]:
    path=ROOT/Path(str(relative).replace("\\","/"))
    if not path.is_file(): return False,False,"Missing"
    try:
        suffix=path.suffix.lower()
        if suffix==".csv": pd.read_csv(path)
        elif suffix==".json": json.loads(path.read_text(encoding="utf-8"))
        elif suffix==".png":
            with path.open("rb") as stream:
                if stream.read(8)!=b"\x89PNG\r\n\x1a\n": return True,False,"Invalid PNG signature"
        else:
            if path.stat().st_size==0: return True,False,"Empty file"
            return True,True,"Non-empty; format not parsed"
    except (OSError,UnicodeError,ValueError,pd.errors.ParserError) as exc:
        return True,False,f"Unreadable ({type(exc).__name__})"
    return True,True,"Readable"

def dataset_warning(key: str, frame: pd.DataFrame) -> str:
    warnings=[]
    if key=="DS1" and "material_id" in frame and frame.material_id.duplicated().any():
        warnings.append(f"{int(frame.material_id.duplicated().sum())} duplicate material IDs")
    if key in {"DS2","DS4"} and {"date","commodity"}.issubset(frame.columns):
        dupe=int(frame.duplicated(["date","commodity"]).sum())
        if dupe: warnings.append(f"{dupe} duplicate date/commodity keys")
    if key=="DS3" and "condition_rating" in frame:
        rating=pd.to_numeric(frame.condition_rating,errors="coerce")
        invalid=int((~(rating.between(1,9)&rating.eq(rating.round()))).sum())
        if invalid: warnings.append(f"{invalid} condition ratings outside integer 1–9 scale")
    if key=="DS5" and {"date","element"}.issubset(frame.columns):
        dupe=int(frame.duplicated(["date","element"]).sum())
        if dupe: warnings.append(f"{dupe} duplicate date/element keys")
    if key=="DS6" and {"repair_cost_USD","replacement_value_USD"}.issubset(frame.columns):
        over=(pd.to_numeric(frame.repair_cost_USD,errors="coerce")>pd.to_numeric(frame.replacement_value_USD,errors="coerce"))
        if over.any(): warnings.append(f"{int(over.sum())} repair costs exceed replacement value")
    return "; ".join(warnings) if warnings else "No configured checks triggered"

def chart_style(chart: alt.Chart) -> alt.Chart:
    return chart.configure(background="transparent", view=alt.ViewConfig(strokeOpacity=0)).configure_axis(
        labelColor="#B8C5D4", titleColor="#DDE7F1", gridColor="#26384C", gridOpacity=.5,
        domainColor="#41546A", tickColor="#41546A", labelFontSize=11, titleFontSize=12
    ).configure_legend(labelColor="#D8E2EC", titleColor="#D8E2EC", orient="top", symbolType="circle")

def show_chart(chart: alt.Chart, height: int = 310):
    styled=chart_style(chart)
    if isinstance(styled,alt.FacetChart):
        fields=["data","facet","resolve","columns","spacing","bounds","align","center","title","description","config"]
        options={name:getattr(styled,name) for name in fields if getattr(styled,name) is not alt.Undefined}
        options["spec"]=styled.spec.properties(height=height)
        styled=alt.FacetChart(**options)
    else:
        styled=styled.properties(height=height)
    st.altair_chart(styled, width="stretch")

def page_heading(title: str, description: str):
    active = PAGES.index(page) if page in PAGES else 0
    st.markdown(f"<div class='eyebrow'>{asset_icon(ICONS[active])} MatRisk AI / Intelligence workspace</div>", unsafe_allow_html=True)
    st.title(title)
    st.markdown(f"<div class='section-note'>{description}</div>", unsafe_allow_html=True)

def metric_provenance(name: str, source: str, calculation: str, count: int | str | None = None,
                      units: str | None = None, status: str = "Derived", limitation: str | None = None):
    """Compact, reusable provenance disclosure for decision-relevant metrics."""
    with st.expander(f"Metric provenance · {name}"):
        st.markdown(f"**Evidence:** {status}  \n**Source:** {source}  \n**Calculation:** {calculation}")
        if count is not None: st.write(f"**Records:** {count}")
        if units: st.write(f"**Units:** {units}")
        if limitation: st.caption(limitation)

def navigate_to_page(name: str):
    st.session_state["page_navigation"] = name

def asset_icon(name: str) -> str:
    data = svg_data(ASSETS / "icons" / f"{name}.svg")
    if not data:
        return "◈"
    return f"<img class='module-icon' src='{data}' alt='' aria-hidden='true'>"

with st.sidebar:
    logo = svg_data(ASSETS / "brand" / "matrisk-lockup.svg")
    if logo:
        st.markdown(f"<div style='padding:10px 4px 18px'><img src='{logo}' alt='MatRisk AI' style='width:min(220px,100%);height:auto'></div>", unsafe_allow_html=True)
    else:
        st.markdown("## ◈ MatRisk AI")
    st.caption("SCIENTIFIC & FINANCIAL INTELLIGENCE")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed", key="page_navigation")

if page == "Overview":
    st.markdown("""<div class='hero'><div class='eyebrow'>Scientific &amp; financial intelligence</div><h1>Connect material evidence with infrastructure exposure.</h1><p>Explore measured materials, market histories, bridge condition, and saved model evaluations. Each result stays linked to its evidence and limits.</p></div>""", unsafe_allow_html=True)
    go1,go2,_=st.columns([1,1,3]);go1.button("Explore materials →",on_click=navigate_to_page,args=("Materials Intelligence",),use_container_width=True);go2.button("Review infrastructure →",on_click=navigate_to_page,args=("Infrastructure Risk",),use_container_width=True)
    available = sum((ROOT / "Data/raw" / spec[0]).is_file() for spec in DATASETS.values())
    registry = read_json(output("notebook_08/run_summary.json")) or {}
    checks = registry.get("artifact_checks", {})
    summary_checks = registry.get("summary_checks", {})
    grouped = read_csv(output("notebook_02/selected_model_results.csv"))
    all_baseline = bool(grouped is not None and "model" in grouped and (grouped["model"] == "DummyMean").all())
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Source files present", f"{available} / 6", help="File presence is separate from readability and scientific validity.")
    k2.metric("Registry artifacts", f"{checks.get('found','—')} / {checks.get('expected_artifacts','—')}")
    k3.metric("Material model selection", "Mean baseline" if all_baseline else "Review outputs", help="Grouped evaluation summary, not a readiness score.")
    k4.metric("Readable run summaries", f"{summary_checks.get('readable_summaries','—')} / {summary_checks.get('notebooks_expected','—')}")
    left,right = st.columns(2, gap="large")
    with left:
        st.markdown(f"### {asset_icon('materials')}Materials intelligence", unsafe_allow_html=True)
        st.write("Compare measured material properties, explore composition records, and inspect a heuristic screen of existing candidates.")
        d1 = dataset("DS1")
        if d1 is not None:
            st.metric("Material records", f"{len(d1):,}")
        st.caption("Grouped evaluation selected mean baselines for all reported targets; dependable composition-only prediction is not established.")
    with right:
        st.markdown(f"### {asset_icon('infrastructure')}Risk intelligence", unsafe_allow_html=True)
        st.write("Review observed bridge conditions, portfolio exposure, market history, and explicitly hypothetical stress cases.")
        d3 = dataset("DS3")
        exposure = read_csv(output("notebook_05/portfolio_exposure_summary.csv"))
        e1,e2 = st.columns(2)
        if d3 is not None: e1.metric("Bridge records", f"{len(d3):,}")
        if exposure is not None and len(exposure): e2.metric("Replacement value", f"${exposure.iloc[0]['replacement_cost_total_M']:,.0f}M", help="Sum of supplied replacement_cost_M records.")
        st.caption("Cross-sectional condition and hypothetical loss scenarios are not calibrated failure forecasts.")
    st.markdown("### Current evidence")
    st.markdown("<div class='signal'>Files and saved artifacts are available for exploration. The registry records artifact presence and summary readability; it does not prove latest-run freshness or scientific validity.</div>", unsafe_allow_html=True)
    brief=[]
    ds3brief=dataset("DS3")
    if ds3brief is not None:
        _,invalid_ratings=valid_condition_records(ds3brief)
        invalid_n=len(invalid_ratings)
        if invalid_n: brief.append(("Data quality",f"{invalid_n} bridge records use a rating outside the documented 1–9 scale, including zero values.","Observed · DS3 condition_rating"))
    dsm=dataset("DS1"); dsp=dataset("DS5")
    if dsm is not None and dsp is not None:
        cm=(ROOT/"Data/raw"/DATASETS["DS1"][0]).stat().st_mtime_ns;cp=(ROOT/"Data/raw"/DATASETS["DS5"][0]).stat().st_mtime_ns
        cover=current_price_coverage(cm,cp)
        brief.append(("Price coverage",f"{cover['complete_coverage_rows']:,} of {cover['total_material_rows']:,} material records have complete current latest-element-price coverage ({cover['coverage_rate']:.1%}).","Derived · DS1 formulas + DS5 latest positive prices"))
    if all_baseline: brief.append(("Model evaluation","Mean baseline selected for all four reported material targets; useful out-of-group prediction is not established.","Experimental model result · Notebook 02 selected_model_results.csv"))
    if brief:
        cols=st.columns(len(brief))
        for col,(title,body,source) in zip(cols,brief):
            with col:
                st.markdown(f"**{title}**  \n{body}")
                st.caption(source)
    else:
        st.info("No additional data-backed findings are available from the currently readable source files.")
    ledger,ledger_error=execution_ledger()
    if ledger_error: st.error(ledger_error)
    elif ledger:
        last=ledger[-1]
        st.caption(f"Latest recorded notebook process: {last.get('notebook')} · {last.get('status')} · {last.get('completed_at_utc')} (ledger evidence). Artifact freshness still requires per-output verification.")
    else:
        st.caption("Execution status unknown · Freshness unknown. No trustworthy per-notebook execution ledger is present.")
    with st.expander("Cross-domain alignment · commodity prices and carbon indicators"):
        ds2=dataset("DS2");ds4=dataset("DS4")
        if ds2 is not None and ds4 is not None:
            left_keys=ds2[["date","commodity"]].copy();right_keys=ds4[["date","commodity"]].copy()
            left_keys["date"]=pd.to_datetime(left_keys.date,errors="coerce");right_keys["date"]=pd.to_datetime(right_keys.date,errors="coerce")
            left_keys=left_keys.dropna().drop_duplicates();right_keys=right_keys.dropna().drop_duplicates()
            common=left_keys.merge(right_keys,on=["date","commodity"],how="inner")
            st.write(f"Exact date + commodity key match: **{len(common):,}** of {len(left_keys):,} DS2 keys and {len(right_keys):,} DS4 keys. Unmatched: {len(left_keys)-len(common):,} DS2, {len(right_keys)-len(common):,} DS4.")
            st.caption("This supports a descriptive aligned view only. Shared keys do not establish causality, point-in-time availability, or validated cost sensitivity. A defensible cost-sensitivity analysis would also need time-valid sourcing shares, material/input quantities, process yields, and documented unit/currency conversions.")
        else: st.info("Both DS2 and DS4 must be readable to inspect exact date/commodity alignment.")
    with st.expander("Dataset inventory"):
        inventory=[]
        for key,(filename,_) in DATASETS.items():
            frame=dataset(key); inventory.append({"Dataset":key,"Source":filename,"Rows":len(frame) if frame is not None else None,"Columns":len(frame.columns) if frame is not None else None,"Readable":frame is not None})
        st.dataframe(pd.DataFrame(inventory), width="stretch", hide_index=True)
    registry_time=registry.get("generated_at_utc")
    if registry_time: st.caption(f"Registry summary generated: {registry_time}. This timestamps the inventory generation, not the producer notebooks' latest successful execution.")

elif page == "Materials Intelligence":
    page_heading("Materials Intelligence", "Explore measured property distributions and screen existing records with the saved cost heuristic.")
    df=dataset("DS1")
    if df is not None:
        controls=st.columns([2,1,1])
        query=controls[0].text_input("Formula or material ID", placeholder="e.g. Fe2O3 or material identifier")
        system=controls[1].selectbox("Crystal system", ["All"]+sorted(df.crystal_system.dropna().astype(str).unique()) if "crystal_system" in df else ["All"])
        stable=controls[2].selectbox("Stability label", ["All","Stable","Not stable"])
        sub=df.copy()
        if query: sub=sub[sub.formula.astype(str).str.contains(query,case=False,na=False,regex=False)|sub.material_id.astype(str).str.contains(query,case=False,na=False,regex=False)]
        if system!="All" and "crystal_system" in sub: sub=sub[sub.crystal_system.astype(str)==system]
        if stable!="All" and "is_stable" in sub:
            stable_mask=sub.is_stable.astype(str).str.strip().str.lower().isin(["true","1","yes"])
            sub=sub[stable_mask==(stable=="Stable")]
        props=[c for c in ["formation_energy_per_atom_eV","band_gap_eV","bulk_modulus_GPa","shear_modulus_GPa"] if c in sub]
        active_filters=[f"Search: {query}" if query else None,f"Crystal system: {system}" if system!="All" else None,f"Stability: {stable}" if stable!="All" else None]
        st.caption("Active filters · " + (" · ".join(x for x in active_filters if x) or "None"))
        if not props: st.info("No property columns are available for this filter.")
        else:
            prop=st.selectbox("Property distribution",props,format_func=lambda x:x.replace("_"," "))
            st.caption(f"Active property: {prop.replace('_',' ')}")
            numeric=pd.to_numeric(sub[prop],errors="coerce").replace([float("inf"),-float("inf")],pd.NA).dropna()
            hist=histogram_frame(sub[prop])
            unit={"formation_energy_per_atom_eV":"eV/atom","band_gap_eV":"eV","bulk_modulus_GPa":"GPa","shear_modulus_GPa":"GPa"}.get(prop,"source units")
            metric=st.columns(3); metric[0].metric("Matching records",f"{len(sub):,}"); metric[1].metric("Finite values",f"{len(numeric):,}"); metric[2].metric("Median",f"{numeric.median():,.3g} {unit}" if len(numeric) else "Unavailable")
            if not hist.empty:
                ch=alt.Chart(hist).mark_bar(color="#35D7F2",cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(x=alt.X("bin_midpoint:Q",title=f"{prop.replace('_',' ')} ({unit})"),y=alt.Y("count:Q",title="Records"),tooltip=[alt.Tooltip("bin_label:N",title="Range"),alt.Tooltip("count:Q",title="Records")])
                show_chart(ch,280)
            st.caption("Distribution includes finite observed values only; bins are equal-width over the filtered range.")
            metric_provenance("selected property distribution","Data/raw/DS1_material_properties_5500.csv",f"Finite values of {prop}; equal-width histogram and median after active filters.",len(numeric),unit,"Observed", "NaN and ±infinity are excluded from the numeric summary and histogram.")
        details_cols=[c for c in ["material_id","formula","n_elements","crystal_system","formation_energy_per_atom_eV","band_gap_eV","bulk_modulus_GPa","shear_modulus_GPa","density_g_cm3","is_stable"] if c in sub]
        if not sub.empty and "material_id" in sub:
            with st.expander("Selected material details"):
                material_ids=sorted(sub.material_id.dropna().astype(str).unique())
                chosen_id=st.selectbox("Material ID (source IDs may repeat)",material_ids,key="material_detail_id")
                detail=sub.loc[sub.material_id.astype(str)==chosen_id,details_cols]
                st.dataframe(detail,width="stretch",hide_index=True)
                st.caption(f"{len(detail)} matching source row(s) selected from the active filtered set; no unobserved structure or property is inferred.")
        with st.expander(f"Explore matching material records ({len(sub):,})"):
            st.dataframe(sub[details_cols].head(1000),width="stretch",hide_index=True)
        st.download_button("Download filtered materials",sub.to_csv(index=False),"materials_filtered.csv","text/csv")
    st.divider(); st.subheader("Existing candidate screen")
    ranked=read_csv(output("notebook_07/ranked_material_candidates.csv"))
    if ranked is not None:
        st.caption(f"{len(ranked):,} existing rows ranked using the notebook's stated cost and property heuristic. This is not generated material design or a validated prediction.")
        rank_summary=read_json(output("notebook_07/run_summary.json")) or {}
        weights=rank_summary.get("ranking_weights",{})
        weight_text=", ".join(f"{k} {float(v):.0%}" for k,v in weights.items()) if weights else "Weights unavailable"
        st.markdown(f"**Saved ranking weights:** {weight_text}. The score is a relative percentile heuristic within the eligible existing-record pool. It does not establish suitability; manufacturing, processing, lifecycle, and experimental validation are not represented.")
        st.caption("The raw-element cost proxy is available only for formulas with complete elemental-price coverage. It excludes manufacturing, energy, processing, transport, waste, and lifecycle costs.")
        primary=[c for c in ["material_id","formula","crystal_system","heuristic_score_0_100","raw_element_cost_proxy_usd_per_kg","bulk_modulus_GPa","shear_modulus_GPa","energy_above_hull_eV","is_stable"] if c in ranked]
        st.dataframe(ranked[primary].head(100),width="stretch",hide_index=True)
        with st.expander("Ranking constraints and all output fields"):
            st.json(rank_summary.get("constraints",{}),expanded=False)
            st.dataframe(ranked.head(100),width="stretch",hide_index=True)
        st.download_button("Download candidate ranking",ranked.to_csv(index=False),"ranked_material_candidates.csv","text/csv")
    else: st.info("Candidate ranking is unavailable until Notebook 07 produces it.")
    st.warning("Grouped evaluation selected mean baselines for all four targets. Property predictions are not offered because generalization was not demonstrated.")

elif page == "Commodity Intelligence":
    page_heading("Commodity Intelligence", "Inspect observed closing prices and evaluate saved forecasts on their chronological held-out period.")
    df=dataset("DS2")
    if df is not None:
        df["date"]=pd.to_datetime(df.date,errors="coerce"); valid=df.dropna(subset=["date"])
        st.subheader("Historical price analysis")
        choices=sorted(valid.commodity.dropna().astype(str).unique())
        if valid.empty: st.info("No valid dates are present.")
        else:
            date_range=st.date_input("Inclusive date range",(valid.date.min().date(),valid.date.max().date()),key="commodity_dates")
            if isinstance(date_range,tuple) and len(date_range)==2:
                if date_range[0] > date_range[1]:
                    st.info("Choose a start date on or before the end date.")
                else:
                    mode=st.radio("Price comparison",["Individual commodity","Indexed comparison","Small multiples"],horizontal=True,key="commodity_chart_mode")
                    selected=st.selectbox("Commodity",choices) if mode=="Individual commodity" else st.multiselect("Commodities",choices,default=choices[:min(4,len(choices))],key="commodity_multi")
                    selected=[selected] if isinstance(selected,str) else selected
                    sub=chronological_prices(valid,selected,*date_range)
                    if sub.empty: st.info("No prices match the selected commodity and date filters.")
                    elif mode=="Individual commodity":
                        chart=alt.Chart(sub).mark_line(color=COLORS[0],strokeWidth=2).encode(x=alt.X("date:T",title=None,axis=alt.Axis(format="%b %Y",tickCount=7,labelAngle=0)),y=alt.Y("close:Q",title="Closing price (source units)"),tooltip=[alt.Tooltip("date:T",format="%Y-%m-%d"),alt.Tooltip("close:Q",format=",.3f")])
                        show_chart(chart,350);st.caption("One series shown in its observed source scale. Currency is not documented by the source file.")
                    elif mode=="Indexed comparison":
                        indexed,invalid=indexed_price_series(sub,selected)
                        if indexed.empty: st.info("Selected series have no finite positive base observations in this date window.")
                        else:
                            chart=alt.Chart(indexed).mark_line(strokeWidth=2).encode(x=alt.X("date:T",title=None,axis=alt.Axis(format="%b %Y",tickCount=7,labelAngle=0)),y=alt.Y("index:Q",title="Price index (first finite positive close = 100)"),color=alt.Color("commodity:N",scale=alt.Scale(range=COLORS),title="Commodity"),tooltip=["commodity:N",alt.Tooltip("date:T",format="%Y-%m-%d"),alt.Tooltip("index:Q",format=".2f"),alt.Tooltip("base_date:T",title="Base date",format="%Y-%m-%d")])
                            show_chart(chart,350)
                            bases=indexed.groupby("commodity").base_date.first().dt.strftime("%Y-%m-%d").to_dict()
                            invalid_values=int(pd.to_numeric(sub.close,errors="coerce").replace([float("inf"),-float("inf")],pd.NA).le(0).sum())
                            st.caption("Index = close ÷ first finite positive close in selected window × 100. Nonpositive closes are omitted from the indexed line. Base dates: "+" · ".join(f"{k}: {v}" for k,v in bases.items()))
                            if invalid_values: st.warning(f"{invalid_values:,} nonpositive close observations are omitted from the index chart.")
                        if invalid: st.warning("No valid positive base price; excluded from indexed chart: "+", ".join(invalid))
                    else:
                        chart=alt.Chart(sub).mark_line(strokeWidth=1.8).encode(x=alt.X("date:T",title=None,axis=alt.Axis(format="%b %Y",tickCount=6,labelAngle=0)),y=alt.Y("close:Q",title="Closing price (source units)"),color=alt.Color("commodity:N",scale=alt.Scale(range=COLORS),legend=None),tooltip=["commodity:N",alt.Tooltip("date:T",format="%Y-%m-%d"),alt.Tooltip("close:Q",format=",.3f")]).facet(row=alt.Row("commodity:N",title=None,header=alt.Header(labelColor="#D8E2EC"))).resolve_scale(y="independent")
                        show_chart(chart, min(620, 165*len(selected)));st.caption("Each commodity has an independent price axis; compare within series, not absolute line height across panels.")
                    with st.expander(f"Historical records ({len(sub):,})"): st.dataframe(sub,width="stretch",hide_index=True)
                    st.download_button("Download filtered prices",sub.to_csv(index=False),"commodity_prices_filtered.csv","text/csv")
                    with st.expander("Cross-domain view · aligned commodity and carbon indicators"):
                        cross=dataset("DS4")
                        if cross is None: st.info("DS4 is not readable.")
                        else:
                            cross["date"]=pd.to_datetime(cross.date,errors="coerce")
                            commodity_name=st.selectbox("Aligned commodity",sorted(set(selected)&set(cross.commodity.dropna().astype(str))),key="cross_commodity") if set(selected)&set(cross.commodity.dropna().astype(str)) else None
                            if commodity_name is None: st.info("No selected commodity has a matching DS4 key.")
                            else:
                                left=sub[sub.commodity==commodity_name][["date","commodity","close"]]
                                right=cross[(cross.commodity==commodity_name)&cross.date.between(pd.Timestamp(date_range[0]),pd.Timestamp(date_range[1]))]
                                joined=left.merge(right,on=["date","commodity"],how="inner",validate="one_to_one")
                                st.write(f"Matched keys in this view: **{len(joined):,}** of {len(left):,} DS2 rows and {len(right):,} DS4 rows.")
                                st.caption("Exact join on date + commodity. Association is descriptive; it does not establish causal or tradable cost sensitivity.")
                                measure=st.selectbox("DS4 indicator",[c for c in ["carbon_intensity_virgin","carbon_intensity_recycled","green_premium_per_kg"] if c in joined],key="cross_measure")
                                plot=joined.melt(id_vars="date",value_vars=["close",measure],var_name="measure",value_name="value")
                                layered=alt.Chart(plot).mark_line(strokeWidth=1.8).encode(x=alt.X("date:T",axis=alt.Axis(format="%b %Y",tickCount=6,labelAngle=0)),y=alt.Y("value:Q",title="Source units (independent panels)"),color=alt.Color("measure:N",scale=alt.Scale(range=["#35D7F2","#F2B866"])),tooltip=["measure:N",alt.Tooltip("date:T",format="%Y-%m-%d"),"value:Q"]).facet(row=alt.Row("measure:N",title=None)).resolve_scale(y="independent")
                                show_chart(layered,320)
    st.divider(); st.subheader("Forecast evaluation")
    forecast=read_json(output("notebook_03/run_summary.json")); comp=read_csv(output("notebook_03/heldout_test_comparison.csv")); preds=read_csv(output("notebook_03/heldout_test_predictions.csv"))
    if comp is not None:
        baseline=comp[comp.model.astype(str).str.contains("ZeroReturn",case=False,na=False)]
        if not baseline.empty:
            row=baseline.iloc[0]; m=st.columns(5);m[0].metric("Selected baseline","Zero return");m[1].metric("Held-out MAE",f"{row.MAE:.5f}");m[2].metric("Held-out RMSE",f"{row.RMSE:.5f}");m[3].metric("Held-out R²",f"{row.R2:.4f}");m[4].metric("Held-out rows",f"{len(preds):,}" if preds is not None else "Unavailable")
    if preds is not None and "date" in preds:
        preds["date"]=pd.to_datetime(preds.date,errors="coerce"); commodities=sorted(preds.commodity.dropna().astype(str).unique())
        chosen=st.selectbox("Held-out commodity",commodities)
        observed=preds[preds.commodity.astype(str)==chosen].dropna(subset=["date"]).sort_values("date").copy()
        if not observed.empty:
            long=observed.melt(id_vars="date",value_vars=[c for c in ["target_next_return","prediction"] if c in observed],var_name="series",value_name="return")
            chart=alt.Chart(long).mark_line(strokeWidth=1.7).encode(x=alt.X("date:T",title="Held-out date",axis=alt.Axis(format="%b %Y",tickCount=6,labelAngle=0)),y=alt.Y("return:Q",title="Next-period return",axis=alt.Axis(format=".1%")),color=alt.Color("series:N",scale=alt.Scale(domain=["target_next_return","prediction"],range=["#8C7BFF","#35D7F2"]),title="Series"),tooltip=["series:N",alt.Tooltip("date:T",format="%Y-%m-%d"),alt.Tooltip("return:Q",format=".2%")])
            zero=alt.Chart(pd.DataFrame({"return":[0.0]})).mark_rule(color="#9AA9B9",strokeDash=[5,4]).encode(y="return:Q")
            show_chart(chart+zero,290)
            split=read_csv(output("notebook_03/chronological_split_report.csv"))
            if split is not None:
                split_row=split[split.commodity.astype(str)==chosen]
                if not split_row.empty:
                    sr=split_row.iloc[0];st.caption(f"{chosen}: train through {sr.train_end}; validation through {sr.validation_end}; test starts {sr.test_start} (n={int(sr.test_n):,}). Plotted saved rows are test-period next returns.")
            st.caption("Zero-reference line is shown for the return target. Saved target and prediction are date-aligned; selected model is the zero-return baseline. Held-out performance does not establish trading profitability.")
            residual=observed.target_next_return-observed.prediction
            st.metric("Mean held-out residual (target − prediction)",f"{residual.mean():.5f}",help="Derived from the saved held-out target and prediction rows for the selected commodity.")
            with st.expander("Held-out residual distribution"):
                rhist=histogram_frame(residual,bins=24)
                show_chart(alt.Chart(rhist).mark_bar(color="#8C7BFF").encode(x=alt.X("bin_midpoint:Q",title="Target − prediction (return units)"),y=alt.Y("count:Q",title="Rows"),tooltip=["bin_label:N","count:Q"]),220)
            with st.expander("Forecast metric provenance"):
                st.write("Target: next-period return. Selection: chronological validation. Test: later held-out period. MAE and RMSE are in return units; R² is dimensionless. Source: `notebook_03/heldout_test_comparison.csv` and `heldout_test_predictions.csv`.")
            st.download_button("Download held-out predictions",preds.to_csv(index=False),"heldout_predictions.csv","text/csv")
    elif not forecast: st.info("Forecast outputs are unavailable; no performance claim is shown.")
    baseline_rows=comp[comp.model.astype(str).str.contains("ZeroReturn",case=False,na=False)] if comp is not None else pd.DataFrame()
    if not baseline_rows.empty:
        r=baseline_rows.iloc[0]
        st.warning(f"The selected zero-return baseline has held-out R² {r.R2:.4f}; this is not evidence of useful predictive skill or trading profitability. Forecast evaluation remains experimental.")

elif page == "Infrastructure Risk":
    page_heading("Infrastructure Risk", "Separate observed bridge condition from portfolio accounting, hypothetical stress, and event-only records.")
    df=dataset("DS3")
    if df is not None:
        st.subheader("Observed condition assessment")
        valid_df,invalid_df=valid_condition_records(df)
        invalid_count=len(invalid_df)
        lo,hi=st.slider("Observed condition rating (documented scale: 1–9)",1,9,(1,9))
        sub=valid_df[pd.to_numeric(valid_df.condition_rating,errors="coerce").between(lo,hi)].copy(); a,b,c=st.columns(3);a.metric("Valid records in range",f"{len(sub):,}");b.metric("Median observed rating",f"{pd.to_numeric(sub.condition_rating,errors='coerce').median():.0f}" if len(sub) else "Unavailable");c.metric("Out-of-scale records",f"{invalid_count:,}",help="Raw DS3 rows whose condition_rating is non-integer or outside 1–9.")
        counts=sub.condition_rating.value_counts().sort_index().rename_axis("condition_rating").reset_index(name="records")
        if len(counts):
            ch=alt.Chart(counts).mark_bar(color="#35D7F2",cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(x=alt.X("condition_rating:O",title="Observed condition rating (1–9)",sort="ascending",scale=alt.Scale(domain=list(range(1,10)))),y=alt.Y("records:Q",title="Bridge records"),tooltip=["condition_rating:O","records:Q"])
            show_chart(ch,260)
        else: st.info("No valid ratings in this selected range.")
        st.caption(f"Only integer ratings from 1 through 9 enter this condition chart and summary. The {invalid_count:,} out-of-scale raw records are preserved below and excluded here.")
        if invalid_count:
            with st.expander(f"Inspect out-of-scale raw condition records ({invalid_count:,})"):
                st.dataframe(invalid_df[[c for c in ["bridge_id","condition_rating","bridge_type","location","last_inspection_date"] if c in invalid_df]],width="stretch",hide_index=True)
                st.caption("No source values were changed. Confirm the scale with the data owner before interpreting these records.")
        with st.expander(f"Bridge record exploration ({len(sub):,})"):
            types=sorted(sub.bridge_type.dropna().astype(str).unique()) if "bridge_type" in sub else []
            selected_type=st.multiselect("Bridge types",types,key="bridge_types")
            view=sub[sub.bridge_type.astype(str).isin(selected_type)] if selected_type and "bridge_type" in sub else sub
            cols=[c for c in ["bridge_id","bridge_type","material","location","age_years","condition_rating","structurally_deficient","replacement_cost_M","loan_outstanding_M","insurance_premium_K_yr"] if c in view]
            st.dataframe(view[cols],width="stretch",hide_index=True);st.download_button("Download filtered bridge records",view[cols].to_csv(index=False),"bridges_filtered.csv","text/csv")
        st.divider(); st.subheader("Portfolio financial exposure")
        exposure=read_csv(output("notebook_05/portfolio_exposure_summary.csv"))
        finance_columns={"replacement_cost_M","loan_outstanding_M","insurance_premium_K_yr"}
        if finance_columns.issubset(df.columns):
            replacement=pd.to_numeric(df.replacement_cost_M,errors="coerce");loans=pd.to_numeric(df.loan_outstanding_M,errors="coerce");premiums=pd.to_numeric(df.insurance_premium_K_yr,errors="coerce")
            replacement_total=float(replacement.sum(min_count=1));loan_total=float(loans.sum(min_count=1));premium_total=float(premiums.sum(min_count=1))
            e1,e2,e3=st.columns(3);e1.metric("Replacement value",f"{replacement_total:,.2f} million units");e2.metric("Outstanding loans",f"{loan_total:,.2f} million units");e3.metric("Annual premiums",f"{premium_total:,.1f} thousand units")
            missing_financial=int(replacement.isna().sum()+loans.isna().sum()+premiums.isna().sum())
            st.caption(f"Derived from {len(df):,} DS3 bridge rows; pandas sum over observed values, no imputation. Missing cells across these three source columns: {missing_financial:,}. Column suffixes define million/thousand scale only; currency is not established in source documentation.")
            metric_provenance("portfolio financial exposure","Data/raw/DS3_infrastructure_bridges_5000.csv", "Sum of replacement_cost_M, loan_outstanding_M, and insurance_premium_K_yr over observed cells.",len(df),"Source fields: M and K/year; currency unspecified","Derived","Descriptive accounting totals, not expected loss. Missing cells are not imputed.")
            if exposure is not None and len(exposure):
                saved=exposure.iloc[0]
                agreements=all(abs(float(current)-float(saved[source]))<1e-8 for current,source in [(replacement_total,"replacement_cost_total_M"),(loan_total,"loan_outstanding_total_M"),(premium_total,"annual_premium_total_K")])
                if agreements: st.caption("Source-row sums agree with the saved Notebook 05 exposure totals.")
                else: st.warning("Current source-row sums disagree with the saved Notebook 05 exposure summary; review output freshness and aggregation scope.")
        else: st.info("Portfolio totals need replacement_cost_M, loan_outstanding_M, and insurance_premium_K_yr. One or more fields are unavailable in the current DS3 schema.")
        st.divider(); st.subheader("Hypothetical stress scenarios")
        scenario=read_csv(output("notebook_05/hypothetical_stress_sensitivity.csv"))
        if scenario is not None:
            chart=alt.Chart(scenario).mark_line(point=True,color="#F2B866").encode(x=alt.X("assumed_loss_fraction_of_replacement_value:Q",title="Assumed fraction of replacement value",axis=alt.Axis(format=".0%")),y=alt.Y("hypothetical_gross_loss_M:Q",title="Hypothetical gross loss (million units)"),tooltip=[alt.Tooltip("assumed_loss_fraction_of_replacement_value:Q",format=".1%"),alt.Tooltip("hypothetical_gross_loss_M:Q",format=",.2f"),alt.Tooltip("hypothetical_loss_vs_total_loan:Q",format=".1%")])
            show_chart(chart,240);st.dataframe(scenario,width="stretch",hide_index=True);st.caption("Gross loss = assumed loss fraction × summed replacement value. Inputs are hypothetical, not probabilities, expected losses, or forecasts.")
        else: st.info("Stress scenarios are unavailable.")
        st.warning("Condition regression is cross-sectional. These records do not support survival analysis or remaining-useful-life predictions.")
    events=dataset("DS6")
    if events is not None:
        st.divider();st.subheader("Historical failure-event information");st.metric("Event-only records",f"{len(events):,}")
        st.caption("Without a non-failure population and exposure period, this sample cannot estimate calibrated population failure probability or actuarial expected loss.")
        with st.expander("Review event records"): st.dataframe(events.head(500),width="stretch",hide_index=True)

elif page == "ESG & Sustainability":
    page_heading("ESG & Sustainability", "Review elemental market prices, price coverage, and commodity-level carbon indicators as separate evidence sources.")
    prices=dataset("DS5"); materials=dataset("DS1")
    if prices is not None:
        prices["date"]=pd.to_datetime(prices.date,errors="coerce");elements=sorted(prices.element.dropna().astype(str).unique())
        st.subheader("Element-price trends")
        mode=st.radio("Comparison method",["Single element · USD/kg","Indexed series · first observation = 100"],horizontal=True)
        indexed=mode.startswith("Indexed"); selected=st.selectbox("Element",elements) if not indexed else None
        selected_many=st.multiselect("Elements to compare",elements,default=elements[:min(5,len(elements))]) if indexed else [selected]
        valid_dates=prices.date.dropna()
        if valid_dates.empty:
            st.info("No valid dates are available for the element-price series.")
            price_range=None
        else:
            price_range=st.date_input("Element-price date range",(valid_dates.min().date(),valid_dates.max().date()),key="element_price_dates")
        trend_prices=prices
        if isinstance(price_range,tuple) and len(price_range)==2 and price_range[0]<=price_range[1]:
            trend_prices=prices[prices.date.between(pd.Timestamp(price_range[0]),pd.Timestamp(price_range[1]))]
        elif price_range is not None:
            trend_prices=prices.iloc[0:0]
        series=element_price_series(trend_prices,selected_many,indexed=indexed)
        if not series.empty:
            ytitle="Index (first positive finite price = 100)" if indexed else "Price (USD/kg)"
            invalid_bases=[]
            if indexed:
                first=series.groupby("element")["price_usd_per_kg"].first()
                invalid_bases=first[first.le(0)|~first.map(pd.notna)].index.astype(str).tolist()
            plotted=series[~series.element.astype(str).isin(invalid_bases)]
            if plotted.empty: st.info("Selected element series have no positive finite base price in the available period.")
            else:
                chart=alt.Chart(plotted).mark_line(strokeWidth=2).encode(x=alt.X("date:T",title=None,axis=alt.Axis(format="%b %Y",tickCount=7,labelAngle=0)),y=alt.Y("value:Q",title=ytitle),color=alt.Color("element:N",scale=alt.Scale(range=COLORS),title="Element"),tooltip=["element:N",alt.Tooltip("date:T",format="%Y-%m-%d"),alt.Tooltip("value:Q",format=",.2f")])
                show_chart(chart,330)
                if indexed: st.caption("Each selected element is normalized independently to its first observed positive finite price (100); this compares relative change and hides price-level differences.")
                else: st.caption("Single-element series in source units; no cross-element shared scale is used.")
            if invalid_bases: st.warning("Element series with a zero or invalid first price are excluded from indexing: "+", ".join(invalid_bases))
        missing_elements=sorted(set(selected_many)-set(series.element.astype(str)))
        if missing_elements: st.info("No valid observations in selection: "+", ".join(missing_elements))
    st.divider();st.subheader("Elemental price coverage")
    coverage=read_csv(output("notebook_06/material_price_coverage_summary.csv"))
    if prices is not None and materials is not None:
        pm=(ROOT/"Data/raw"/DATASETS["DS1"][0]).stat().st_mtime_ns;pp=(ROOT/"Data/raw"/DATASETS["DS5"][0]).stat().st_mtime_ns
        current=current_price_coverage(pm,pp);total=current["total_material_rows"];covered=current["complete_coverage_rows"]
        a,b,c,d=st.columns(4);a.metric("Complete price coverage",f"{covered:,} / {total:,}");b.metric("Coverage",f"{current['coverage_rate']:.1%}");c.metric("Latest positive price",current["latest_price_date"] or "Unavailable");d.metric("Elements at latest date",f"{current['elements_with_latest_price']:,}")
        st.caption("Recomputed from current DS1 formula rows and DS5 latest-date positive prices using the documented flat-formula parser. It counts rows with every formula element priced; it does not calculate a complete material cost or lifecycle footprint.")
        metric_provenance("complete elemental-price coverage","Data/raw/DS1_material_properties_5500.csv + Data/raw/DS5_element_prices_monthly.csv","Count formulas whose parsed elements all have a positive price on the latest available date.",total,"Complete-covered rows / material rows", "Derived", "Flat formulas only; coverage is not a complete material cost or life-cycle assessment.")
        if coverage is not None:
            with st.expander("Notebook 06 saved coverage audit"):
                st.dataframe(coverage,width="stretch",hide_index=True)
                expected=int(pd.to_numeric(coverage.loc[coverage.metric=="complete_element_price_coverage_rows","value"],errors="coerce").iloc[0])
                st.caption("Current raw-source recomputation matches the saved audit." if expected==covered else f"Current raw-source recomputation differs from saved artifact ({expected:,} saved vs {covered:,} recomputed). Review freshness and formula parser provenance.")
    else: st.info("DS1 and DS5 are required to recompute current material-price coverage from source.")
    st.divider();st.subheader("Commodity-level carbon indicators")
    carbon=read_csv(output("notebook_06/commodity_carbon_indicator_summary.csv"))
    if carbon is not None:
        compact=[c for c in ["commodity","carbon_intensity_virgin_mean","carbon_intensity_recycled_mean","green_premium_per_kg_mean","carbon_intensity_virgin_count"] if c in carbon]
        st.dataframe(carbon[compact],width="stretch",hide_index=True)
        st.caption("Values and units follow the saved DS4 indicator schema; physical units are not documented in this summary. Green premium uses the source name per kg.")
        with st.expander("Full carbon-indicator summary"): st.dataframe(carbon,width="stretch",hide_index=True)
    else: st.info("Carbon indicator summary is unavailable.")
    st.warning("These indicators are commodity-level signals, not a complete, material-specific life-cycle assessment.")

elif page == "Model Laboratory":
    page_heading("Model Laboratory", "Read model-selection outcomes first, then inspect task-specific validation and held-out metrics.")
    selected=read_csv(output("notebook_02/selected_model_results.csv")); grouped=read_csv(output("notebook_02/grouped_cv_comparison.csv")); commodity=read_csv(output("notebook_03/heldout_test_comparison.csv")); infra=read_csv(output("notebook_04/condition_regression_metrics.csv"))
    all_baseline=bool(selected is not None and "model" in selected and (selected.model=="DummyMean").all())
    a,b,c=st.columns(3);a.metric("Materials selection","Mean baseline" if all_baseline else "Inspect results");b.metric("Targets selected",f"{selected.target.nunique() if selected is not None and 'target' in selected else '—'} / 4");
    zero=commodity[commodity.model.astype(str).str.contains("ZeroReturn",case=False,na=False)] if commodity is not None else None
    if zero is not None and not zero.empty: c.metric("Commodity selection","Zero-return baseline",f"held-out R² {zero.iloc[0].R2:.4f}")
    if all_baseline:
        st.warning("The current saved grouped evaluation selected DummyMean for all four material targets. R² values near zero do not show useful out-of-group explanatory performance.")
    elif selected is None:
        st.info("Materials selection output is unavailable, so no selected-model claim is shown.")
    else:
        st.warning("Saved material selection output does not show DummyMean for every target. Inspect target-level model names and validation criteria before interpretation.")
    if selected is not None:
        st.subheader("Materials · grouped cross-validation and test partition")
        primary=[c for c in ["target","model","feature_set","CV_MAE_mean","CV_MAE_std","MAE","RMSE","R2","n_train","n_test"] if c in selected]
        show=selected[primary].copy().rename(columns={"CV_MAE_mean":"CV MAE","CV_MAE_std":"CV MAE SD","MAE":"Test MAE","RMSE":"Test RMSE","R2":"Test R²","n_train":"Train n","n_test":"Test n"})
        if "target" in show: show["target"]=show.target.str.replace("_"," ")
        numeric=[c for c in show if c not in ["target","model","feature_set"]];show[numeric]=show[numeric].round(4)
        st.dataframe(show,width="stretch",hide_index=True)
        st.caption("Selection criterion: lowest mean grouped-CV MAE. Validation: 3-fold grouped CV by chemical-system element set; test partition is separate. R² near zero means the model explains little variance beyond a constant prediction. Target names preserve units.")
        with st.expander("Metric provenance and complete selected-model results"):
            st.write("Source: `ML/outputs/notebook_02/selected_model_results.csv`. MAE and RMSE use target native units; R² is unitless. Train/test counts are recorded per target.")
            st.dataframe(selected,width="stretch",hide_index=True)
    if grouped is not None:
        with st.expander("All grouped-CV model and feature-set comparisons"):
            st.dataframe(grouped,width="stretch",hide_index=True)
    st.subheader("Commodity · chronological held-out test")
    if commodity is not None:
        st.dataframe(commodity.round(5),width="stretch",hide_index=True)
        with st.expander("Commodity validation and split details"):
            split=read_csv(output("notebook_03/chronological_split_report.csv"))
            if split is not None: st.dataframe(split,width="stretch",hide_index=True)
            st.write("Target: next-period return. Baseline selection used chronological validation; this comparison reports the later held-out test. Source: Notebook 03 validation, split, and held-out comparison artifacts.")
    else: st.info("Commodity test comparison is unavailable.")
    st.caption("The held-out set follows the validation period chronologically. The selected zero-return baseline has MAE 0.01627, RMSE 0.02079 and R² −0.000216 over 3,448 rows; no profitability claim follows.")
    st.subheader("Infrastructure · condition-rating regression")
    if infra is not None: st.dataframe(infra.round(4),width="stretch",hide_index=True)
    else: st.info("Condition metrics are unavailable.")
    st.caption("Reported infrastructure metrics describe a cross-sectional condition-rating holdout, not survival or remaining-useful-life validation. Metrics across these tasks are not directly comparable.")
    infra_pred=read_csv(output("notebook_04/heldout_condition_predictions.csv"))
    if infra_pred is not None:
        required={"bridge_id","observed_condition_rating","predicted_condition_rating","absolute_error"}
        if required.issubset(infra_pred.columns) and not infra_pred.bridge_id.duplicated().any():
            actual=pd.to_numeric(infra_pred.observed_condition_rating,errors="coerce");predicted=pd.to_numeric(infra_pred.predicted_condition_rating,errors="coerce")
            mask=actual.notna()&predicted.notna();valid=infra_pred.loc[mask].copy();valid["observed_condition_rating"]=actual[mask];valid["predicted_condition_rating"]=predicted[mask];valid["residual"]=valid.observed_condition_rating-valid.predicted_condition_rating
            if not valid.empty:
                st.subheader("Infrastructure held-out diagnostic")
                lo=float(min(valid.observed_condition_rating.min(),valid.predicted_condition_rating.min()));hi=float(max(valid.observed_condition_rating.max(),valid.predicted_condition_rating.max()))
                points=alt.Chart(valid).mark_circle(size=22,opacity=.45,color="#35D7F2").encode(x=alt.X("observed_condition_rating:Q",title="Observed rating"),y=alt.Y("predicted_condition_rating:Q",title="Predicted rating"),tooltip=["bridge_id:N","observed_condition_rating:Q","predicted_condition_rating:Q","residual:Q"])
                reference=alt.Chart(pd.DataFrame({"observed_condition_rating":[lo,hi],"predicted_condition_rating":[lo,hi]})).mark_line(color="#F2B866",strokeDash=[5,4]).encode(x="observed_condition_rating:Q",y="predicted_condition_rating:Q")
                show_chart(points+reference,330)
                st.caption(f"Saved Notebook 04 held-out rows with unique bridge IDs: {len(valid):,}. Dashed line is y=x. This cross-sectional diagnostic is not survival or RUL validation.")
                with st.expander("Residual distribution"):
                    rhist=histogram_frame(valid.residual,bins=24)
                    show_chart(alt.Chart(rhist).mark_bar(color="#8C7BFF").encode(x=alt.X("bin_midpoint:Q",title="Observed − predicted (rating points)"),y=alt.Y("count:Q",title="Rows"),tooltip=["bin_label:N","count:Q"]),220)
        else: st.warning("Held-out diagnostic lacks required fields or contains duplicate bridge IDs; chart omitted.")

else:
    page_heading("Data Quality & Runs", "Inspect source availability, schema-readable records, saved artifacts, and explicit limits on freshness evidence.")
    rows=[]
    for key,(filename,required) in DATASETS.items():
        frame=dataset(key); rows.append({"Dataset":key,"File":filename,"Present":(ROOT/'Data/raw'/filename).is_file(),"Readable + minimum schema":frame is not None,"Rows":len(frame) if frame is not None else None,"Columns":len(frame.columns) if frame is not None else None,"Missing cells":int(frame.isna().sum().sum()) if frame is not None else None,"Applicable warnings":dataset_warning(key,frame) if frame is not None else "Unavailable"})
    availability=sum(r["Readable + minimum schema"] for r in rows);st.metric("Readable source datasets",f"{availability} / {len(rows)}")
    st.caption("Observed file presence, minimum-schema readability, and configured validation warnings are separate from scientific correctness.")
    st.subheader("Source dataset checks");st.dataframe(pd.DataFrame(rows),width="stretch",hide_index=True)
    st.divider();st.subheader("Saved artifact inventory")
    inv=read_csv(output("notebook_08/artifact_inventory.csv"))
    if inv is not None:
        ledger,ledger_error=execution_ledger()
        enriched=[]
        for _,entry in inv.iterrows():
            rel=str(entry.get("path", ""));present,readable,read_status=artifact_check(rel)
            notebook_id=str(entry.get("notebook",""));prefix=notebook_id[:2]
            matching=[r for r in (ledger or []) if str(r.get("notebook",""))[:2]==prefix]
            latest=matching[-1] if matching else None
            enriched.append({**entry.to_dict(),"file_present":present,"readable":readable,"read_status":read_status,"execution_status":latest.get("status","Execution status unknown") if latest else "Execution status unknown","freshness_status":"Freshness unknown"})
        detail=pd.DataFrame(enriched)
        opts=sorted(detail.notebook.dropna().astype(str).unique())
        f1,f2,f3=st.columns(3);notebooks_filter=f1.multiselect("Notebook",opts,default=opts,key="artifact_notebooks");types=sorted(detail.expected_artifact.astype(str).map(lambda s:Path(s).suffix.lower()).unique());type_filter=f2.multiselect("Artifact type",types,default=types,key="artifact_types");status_filter=f3.multiselect("File status",["Present + readable","Present but unreadable","Missing"],default=["Present + readable","Present but unreadable","Missing"],key="artifact_statuses")
        detail["file_status"]=detail.apply(lambda r:"Missing" if not r.file_present else ("Present + readable" if r.readable else "Present but unreadable"),axis=1)
        filtered=detail[detail.notebook.astype(str).isin(notebooks_filter)&detail.expected_artifact.astype(str).map(lambda s:Path(s).suffix.lower()).isin(type_filter)&detail.file_status.isin(status_filter)]
        st.dataframe(filtered,width="stretch",hide_index=True)
        st.caption("File presence and format readability are checked independently. Notebook execution is derived only from the optional JSONL execution ledger; otherwise it is unknown. Freshness is unknown because the current saved registry has no per-artifact freshness proof.")
    else: st.info("Notebook 08 artifact inventory is unavailable.")
    reg=read_json(output("notebook_08/run_summary.json"))
    if reg:
        info={"generated_at_utc":reg.get("generated_at_utc"),"artifact_checks":reg.get("artifact_checks"),"summary_checks":reg.get("summary_checks"),"metric_registry_rows":reg.get("metric_registry_rows")}
        st.subheader("Registry summary");st.json(info,expanded=False)
        st.caption("This summary describes the registry file. It is not a record of successful producer notebook execution or output freshness.")
    else: st.warning("Registry summary is missing or unreadable.")
    ledger,ledger_error=execution_ledger()
    st.subheader("Notebook execution ledger")
    if ledger_error: st.error(ledger_error)
    elif ledger:
        ledger_df=pd.DataFrame(ledger)
        compact=[c for c in ["run_id","notebook","started_at_utc","completed_at_utc","status","return_code","code_revision"] if c in ledger_df]
        st.dataframe(ledger_df[compact].tail(30),width="stretch",hide_index=True)
        with st.expander("Execution details, hashes, outputs, and errors"):
            st.json(ledger_df.iloc[-1].to_dict(),expanded=False)
    else:
        st.info("Execution status unknown · Freshness unknown. No execution ledger exists yet. Use `python -m matrisk.run_pipeline` to run notebooks and record actual process outcomes, input hashes, changed outputs, timestamps, and error text.")
    limitations=read_csv(output("notebook_08/limitations_register.csv"))
    if limitations is not None:
        st.subheader("Scientific limitations");st.dataframe(limitations,width="stretch",hide_index=True)
    else: st.info("Limitations register is unavailable.")

from __future__ import annotations

import json
from pathlib import Path
import random
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="AgriStat Rwanda | Productivity intelligence", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = Path(__file__).parent / "data"
ACCENT, INK, GOLD = "#1f7a5a", "#153b2e", "#d7a84d"
DISTRICTS_BY_PROVINCE = {
    "Kigali City": ["Gasabo", "Kicukiro", "Nyarugenge"],
    "Northern": ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"],
    "Southern": ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango"],
    "Western": ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro"],
    "Eastern": ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana"],
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
:root {{ --green: {ACCENT}; --ink: {INK}; --gold: {GOLD}; }}
.stApp {{ background: #f7f9f5; color: var(--ink); }} [data-testid="stHeader"] {{ background: rgba(247,249,245,.88); }}
[data-testid="stSidebar"] {{ background: #173d30; }} [data-testid="stSidebar"] * {{ color: #eef6ef !important; }} [data-testid="stSidebar"] .stCaption {{ color: #b9d4c4 !important; }}
.block-container {{ padding: 2.3rem 4rem 3rem; max-width: 1500px; }} h1, h2, h3 {{ color: var(--ink); letter-spacing: -.02em; }}
h1 {{ font-family: 'Playfair Display', Georgia, serif; font-size: 3.2rem !important; margin-bottom: .3rem; }} h2 {{ font-size: 1.45rem !important; margin-top: 1rem; }} p, label, .stMarkdown {{ font-family: 'DM Sans', sans-serif; }}
.eyebrow {{ color: var(--green); font: 700 .78rem 'DM Sans', sans-serif; letter-spacing: .15em; text-transform: uppercase; margin-bottom: .6rem; }} .subtitle {{ color: #557064; font-size: 1.05rem; margin-bottom: 1.8rem; }}
.source-pill {{ background: #e5f1e7; border: 1px solid #cce2d2; border-radius: 999px; color: #216543; display: inline-block; font: 600 .78rem 'DM Sans', sans-serif; padding: .38rem .75rem; }}
div[data-testid="stMetric"] {{ background: white; border: 1px solid #e3ebe3; border-radius: 16px; padding: 1.1rem 1.25rem; box-shadow: 0 5px 18px rgba(21,59,46,.045); }} div[data-testid="stMetricLabel"] {{ color: #638074; font-weight: 600; }} div[data-testid="stMetricValue"] {{ color: var(--ink); font-weight: 700; }}
.section-note {{ color: #668073; font-size: .88rem; margin-top: -.45rem; }} .insight {{ background: #eaf4ea; border-left: 4px solid var(--green); border-radius: 0 12px 12px 0; padding: .85rem 1rem; color: #285640; font-size: .9rem; }} .footer {{ color: #739082; font-size: .78rem; padding-top: 1.5rem; }}
</style>""", unsafe_allow_html=True)


def _demo_data() -> pd.DataFrame:
    rng = random.Random(42)
    provinces = ["Eastern", "Southern", "Northern", "Western", "Kigali City"]
    crops = ["Maize", "Beans", "Cassava", "Rice", "Potatoes"]
    seasons = ["Season A", "Season B", "Season C"]
    rows: list[dict[str, object]] = []
    for _ in range(900):
        province = rng.choices(provinces, weights=[30, 25, 20, 20, 5])[0]
        crop = rng.choices(crops, weights=[28, 24, 18, 12, 18])[0]
        fertilizer, irrigation, improved_seed = rng.random() < .68, rng.random() < .24, rng.random() < .56
        base = {"Maize": 1900, "Beans": 980, "Cassava": 7200, "Rice": 3600, "Potatoes": 8700}[crop]
        multiplier = 1 + (.19 if fertilizer else 0) + (.12 if irrigation else 0) + (.16 if improved_seed else 0)
        rows.append({"Province": province, "District": rng.choice(DISTRICTS_BY_PROVINCE[province]), "Crop": crop, "Season": rng.choice(seasons), "Farm size (ha)": round(rng.uniform(.15, 3.8), 2), "Yield (kg/ha)": round(max(100, base * multiplier * rng.uniform(.72, 1.22))), "Fertilizer": "Yes" if fertilizer else "No", "Irrigation": "Yes" if irrigation else "No", "Improved seed": "Yes" if improved_seed else "No", "Land tenure": rng.choice(["Owned", "Rented", "Family land"])})
    return pd.DataFrame(rows)


def _find_data_file() -> Path | None:
    files = sorted(path for path in DATA_DIR.glob("*.csv") if path.name.lower() != "benchmarks.csv")
    files += sorted(DATA_DIR.glob("*.xlsx"))
    if len(files) > 1:
        st.error("More than one CSV/XLSX file was found in data/. Keep only the dataset you want the dashboard to load.")
        st.stop()
    return files[0] if files else None


@st.cache_data(show_spinner=False)
def load_data(file_path: Path | None, file_signature: tuple[int, int, int] | None) -> tuple[pd.DataFrame, str]:
    if file_path is None:
        return _demo_data(), "Illustrative synthetic demo data"
    try:
        frame = pd.read_csv(file_path) if file_path.suffix.lower() == ".csv" else pd.read_excel(file_path)
    except (ImportError, OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"Could not read {file_path.name}: {exc}")
        st.stop()
    return frame, f"Unverified dataset · {file_path.name}"


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "province": "Province", "region": "Province", "district": "District",
        "crop": "Crop", "season": "Season", "year": "Year", "survey year": "Year",
        "farm size": "Farm size (ha)",
        "farm_size": "Farm size (ha)", "yield": "Yield (kg/ha)",
        "yield (kg/ha)": "Yield (kg/ha)", "fertilizer": "Fertilizer",
        "irrigation": "Irrigation", "improved seed": "Improved seed",
        "land tenure": "Land tenure", "production": "Production (kg)",
        "production (kg)": "Production (kg)", "harvested area": "Harvested area (ha)",
        "harvested area (ha)": "Harvested area (ha)",
        "area": "Province", "benchmark yield": "Benchmark yield (kg/ha)",
        "benchmark yield (kg/ha)": "Benchmark yield (kg/ha)",
        "source": "Source URL", "source url": "Source URL",
    }
    return frame.rename(columns={column: aliases.get(str(column).strip().lower(), column) for column in frame.columns})


def _yield_summary(frame: pd.DataFrame, group_by: list[str] | None = None) -> pd.DataFrame:
    grouping: str | list[str] = group_by[0] if group_by and len(group_by) == 1 else group_by or []
    if "Production (kg)" in frame.columns and "Harvested area (ha)" in frame.columns:
        if group_by:
            summary = frame.groupby(grouping, as_index=False).agg(
                production_kg=("Production (kg)", "sum"),
                harvested_area_ha=("Harvested area (ha)", "sum"),
                observations=("Yield (kg/ha)", "size"),
            )
        else:
            summary = pd.DataFrame([{
                "production_kg": frame["Production (kg)"].sum(),
                "harvested_area_ha": frame["Harvested area (ha)"].sum(),
                "observations": len(frame),
            }])
        summary["Yield (kg/ha)"] = summary["production_kg"] / summary["harvested_area_ha"]
        return summary
    if group_by:
        return frame.groupby(grouping, as_index=False).agg(
            **{"Yield (kg/ha)": ("Yield (kg/ha)", "mean")},
            observations=("Yield (kg/ha)", "size"),
        )
    return pd.DataFrame([{
        "Yield (kg/ha)": frame["Yield (kg/ha)"].mean(),
        "observations": len(frame),
    }])


def _load_benchmarks() -> pd.DataFrame:
    path = DATA_DIR / "benchmarks.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        benchmarks = _normalise(pd.read_csv(path))
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"Could not read {path.name}: {exc}")
        st.stop()
    required = {"Crop", "Province", "Year", "Benchmark yield (kg/ha)", "Source URL"}
    missing = sorted(required - set(benchmarks.columns))
    if missing:
        st.error(f"{path.name} is missing required columns: {', '.join(missing)}.")
        st.stop()
    benchmarks["Crop"] = benchmarks["Crop"].astype("string").str.strip()
    benchmarks["Province"] = benchmarks["Province"].astype("string").str.strip()
    benchmarks["Year"] = benchmarks["Year"].astype("string").str.strip()
    benchmarks["Source URL"] = benchmarks["Source URL"].astype("string").str.strip()
    if "Season" not in benchmarks.columns:
        benchmarks["Season"] = ""
    else:
        benchmarks["Season"] = benchmarks["Season"].fillna("").astype("string").str.strip()
    benchmarks["Benchmark yield (kg/ha)"] = pd.to_numeric(
        benchmarks["Benchmark yield (kg/ha)"], errors="coerce"
    )
    valid_source_url = benchmarks["Source URL"].map(
        lambda value: urlparse(str(value)).scheme in {"http", "https"}
        and bool(urlparse(str(value)).netloc)
    )
    invalid = (
        benchmarks[["Crop", "Province", "Year", "Source URL"]].isna().any(axis=1)
        | benchmarks[["Crop", "Province", "Year", "Source URL"]].eq("").any(axis=1)
        | benchmarks["Benchmark yield (kg/ha)"].isna()
        | (benchmarks["Benchmark yield (kg/ha)"] <= 0)
        | ~valid_source_url
    )
    if invalid.any():
        st.error(f"{path.name} contains incomplete rows or non-positive benchmark yields.")
        st.stop()
    keys = ["Crop", "Province", "Year", "Season"]
    if benchmarks.duplicated(keys).any():
        st.error(f"{path.name} must contain only one benchmark per crop, area, year, and season.")
        st.stop()
    return benchmarks


def _district_geojson() -> tuple[dict | None, str | None]:
    path = DATA_DIR / "district_boundaries.geojson"
    if not path.exists():
        return None, None
    try:
        with path.open(encoding="utf-8") as geojson_file:
            geojson = json.load(geojson_file)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"Could not read {path.name}: {exc}"
    if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection" or not isinstance(geojson.get("features"), list):
        return None, f"{path.name} must be a GeoJSON FeatureCollection."
    if not geojson["features"] or any(
        not isinstance(feature, dict)
        or not isinstance(feature.get("properties"), dict)
        or not isinstance(feature.get("geometry"), dict)
        or feature["geometry"].get("type") not in {"Polygon", "MultiPolygon"}
        or not isinstance(feature["geometry"].get("coordinates"), list)
        or not feature["geometry"]["coordinates"]
        for feature in geojson["features"]
    ):
        return None, f"{path.name} must contain polygon features with properties."
    properties = [feature["properties"] for feature in geojson["features"]]
    for property_name in ("District", "district", "NAME_2", "name"):
        if properties and all(property_name in item for item in properties):
            return geojson, property_name
    return None, f"{path.name} must include a district-name property (District, district, NAME_2, or name)."


data_file = _find_data_file()
if data_file is not None:
    data_stat = data_file.stat()
    data_signature = (data_stat.st_mtime_ns, data_stat.st_size, data_stat.st_ctime_ns)
else:
    data_signature = None
df, source = load_data(data_file, data_signature)
df = _normalise(df)
benchmarks = _load_benchmarks()
for dimension in ["Province", "District", "Crop", "Season", "Year"]:
    if dimension in df.columns:
        df[dimension] = df[dimension].astype("string").str.strip()
if "Year" in df.columns:
    df["Year"] = df["Year"].str.replace(r"\.0$", "", regex=True)
has_yield = "Yield (kg/ha)" in df.columns
has_production_and_area = {"Production (kg)", "Harvested area (ha)"}.issubset(df.columns)
if not {"Province", "Crop"}.issubset(df.columns) or not (has_yield or has_production_and_area):
    missing_columns = sorted({"Province", "Crop"} - set(df.columns))
    if not (has_yield or has_production_and_area):
        missing_columns.append("Yield (kg/ha) or both Production (kg) and Harvested area (ha)")
    st.error(f"The dataset is missing required columns: {', '.join(missing_columns)}. Check the column names in the data README.")
    st.stop()

if has_yield:
    df["Yield (kg/ha)"] = pd.to_numeric(df["Yield (kg/ha)"], errors="coerce")
if has_production_and_area:
    if not has_yield:
        df["Yield (kg/ha)"] = pd.NA
    df["Production (kg)"] = pd.to_numeric(df["Production (kg)"], errors="coerce")
    df["Harvested area (ha)"] = pd.to_numeric(df["Harvested area (ha)"], errors="coerce")
    valid_totals = (df["Production (kg)"] >= 0) & (df["Harvested area (ha)"] > 0)
    df.loc[valid_totals, "Yield (kg/ha)"] = (
        df.loc[valid_totals, "Production (kg)"] / df.loc[valid_totals, "Harvested area (ha)"]
    )
    df.loc[~valid_totals, "Yield (kg/ha)"] = pd.NA
    yield_method = "Total production ÷ total harvested area"
else:
    yield_method = "Mean of reported farm-level yields"
invalid_yield_count = int(df["Yield (kg/ha)"].isna().sum())
missing_dimension_count = int(df[["Province", "Crop"]].isna().any(axis=1).sum())
if invalid_yield_count or missing_dimension_count:
    st.warning(
        f"Excluded {invalid_yield_count:,} row(s) with missing or non-numeric yield "
        f"and {missing_dimension_count:,} row(s) with missing province or crop."
    )
df = df.dropna(subset=["Province", "Crop", "Yield (kg/ha)"]).copy()
if df.empty:
    st.error("The dataset contains no usable rows after validating province, crop, and yield.")
    st.stop()

is_demo_data = source.startswith("Illustrative synthetic demo data")

with st.sidebar:
    st.markdown("## AgriStat Rwanda")
    st.caption("Agricultural productivity intelligence")
    st.divider()
    st.markdown("### Explore the data")
    province_options = sorted(df["Province"].dropna().astype(str).unique())
    selected_provinces = st.multiselect("Province", province_options, default=province_options)
    crop_options = sorted(df["Crop"].dropna().astype(str).unique())
    selected_crops = st.multiselect("Crop", crop_options, default=crop_options)
    if "Season" in df.columns:
        season_options = sorted(df["Season"].dropna().astype(str).unique())
        selected_seasons = st.multiselect("Season", season_options, default=season_options)
    else:
        selected_seasons = []
    if "Year" in df.columns:
        year_options = sorted(df["Year"].dropna().astype(str).unique())
        selected_years = st.multiselect("Year", year_options, default=year_options)
    else:
        selected_years = []
    st.divider()
    st.caption("Current data mode")
    st.progress(min(len(df) / 1000, 1.0), text=f"{len(df):,} observations available")
    if is_demo_data:
        st.caption("Synthetic demo mode: illustrative values only; not official statistics.")
    else:
        st.caption("Loaded local file: its origin and representativeness have not been verified by the app.")

filtered = df[df["Province"].astype(str).isin(selected_provinces) & df["Crop"].astype(str).isin(selected_crops)].copy()
if "Season" in filtered.columns and selected_seasons:
    filtered = filtered[filtered["Season"].astype(str).isin(selected_seasons)]
if "Year" in filtered.columns and selected_years:
    filtered = filtered[filtered["Year"].astype(str).isin(selected_years)]
filtered["Yield (kg/ha)"] = pd.to_numeric(filtered["Yield (kg/ha)"], errors="coerce")
filtered = filtered.dropna(subset=["Yield (kg/ha)"])

st.markdown('<div class="eyebrow">NISR · 2026 hackathon · Track 1</div>', unsafe_allow_html=True)
st.title("Agricultural productivity, made visible.")
st.markdown('<div class="subtitle">Explore crop yields and how they vary alongside reported inputs and practices across Rwanda.</div>', unsafe_allow_html=True)
st.markdown(f'<span class="source-pill">● {source}</span>', unsafe_allow_html=True)

with st.expander("About the official NISR source"):
    st.markdown(
        "**Agricultural Household Survey 2017**  \n"
        "Reference ID: `RWA-NISR-RAHS-2017-V0.1`  ·  Producer: National Institute of Statistics of Rwanda  ·  Country: Rwanda"
    )
    st.caption("The official data dictionary includes land tenure and crops planted; agricultural inputs; agricultural practices; production, use, storage and expenses; extension services; and agricultural programmes for the 2016–2017 agricultural year.")
    st.markdown("[Open the NISR study page](https://microdata.statistics.gov.rw/index.php/catalog/90) · [Open the data dictionary](https://microdata.statistics.gov.rw/index.php/catalog/90/data_dictionary) · [Open related materials](https://microdata.statistics.gov.rw/index.php/catalog/90/related_materials)")

with st.expander("Survey scope and methodology"):
    st.markdown("**Agricultural year:** 2016–2017  ·  **Reference:** `RWA-NISR-RAHS-2017-V0.1`")
    st.caption("The NISR catalog describes 16 data files covering general information, household characteristics, land tenure and crops planted, extension services, funding, agricultural inputs, agricultural practices, tools, production and expenses, livestock, milk, honey, and animal services.")
    st.markdown("**Relevant analysis sections**")
    st.markdown("- Section II: land tenure and crops planted  \n- Section V: organic/inorganic fertilizer, pesticides and seeds  \n- Section VI: erosion control, irrigation and mechanization  \n- Sections VIII A/B: production, use, storage and expenses")
    st.markdown("[AHS 2017 questionnaire](https://microdata.statistics.gov.rw/index.php/catalog/90/download/837) · [AHS 2017 report](https://microdata.statistics.gov.rw/index.php/catalog/90/download/838)")

if filtered.empty:
    st.warning("No observations match the selected filters. Choose at least one province and crop to continue.")
    st.stop()

overall_summary = _yield_summary(filtered)
average_yield = overall_summary.iloc[0]["Yield (kg/ha)"] if filtered["Crop"].nunique() == 1 else None
provinces_count = filtered["Province"].nunique()
crops_count = filtered["Crop"].nunique()

st.markdown("## At a glance")
st.markdown('<div class="section-note">Current view across the selected observations</div>', unsafe_allow_html=True)
metric_cols = st.columns(4)
metric_cols[0].metric("Observations", f"{len(filtered):,}")
metric_cols[1].metric(
    "Average yield",
    f"{average_yield:,.0f} kg/ha" if average_yield is not None else "Select one crop",
    help="Yields are averaged only when one crop is selected; crop yields are not directly comparable.",
)
metric_cols[2].metric("Crops represented", f"{crops_count}")
metric_cols[3].metric("Areas represented", f"{provinces_count}")
st.caption(f"Yield method: {yield_method}. Sample counts are shown for each summary.")

st.markdown("## Productivity overview")
left, right = st.columns([1.35, 1])
with left:
    st.markdown("**Average yield by crop**")
    crop_summary = _yield_summary(filtered, ["Crop"]).sort_values("Yield (kg/ha)")
    fig = px.bar(crop_summary, x="Yield (kg/ha)", y="Crop", orientation="h", text_auto=".0f", color_discrete_sequence=[ACCENT], custom_data=["observations"])
    fig.update_traces(hovertemplate="%{y}<br>Yield: %{x:,.0f} kg/ha<br>Observations: %{customdata[0]}<extra></extra>")
    fig.update_layout(height=350, margin=dict(l=0, r=15, t=12, b=0), xaxis_title="Average yield (kg/ha)", yaxis_title=None, plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right:
    st.markdown("**Average yield by province and crop**")
    region_summary = _yield_summary(filtered, ["Province", "Crop"])
    fig = px.bar(region_summary, x="Province", y="Yield (kg/ha)", color="Crop", barmode="group", text_auto=".0f", custom_data=["observations"])
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}<br>Yield: %{y:,.0f} kg/ha<br>Observations: %{customdata[0]}<extra></extra>")
    fig.update_layout(height=350, margin=dict(l=0, r=15, t=12, b=0), xaxis_title=None, yaxis_title="Average yield (kg/ha)", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown("## Productivity gap analyzer")
if is_demo_data:
    st.info("Gap analysis is unavailable in synthetic demo mode. Load an approved agricultural dataset to compare observed areas.")
else:
    st.caption("Uses a cited, supplied benchmark only when crop, area, year, and season match. Otherwise, compare with observed peer areas; no benchmark is invented.")
    gap_crops = sorted(filtered["Crop"].astype(str).unique())
    gap_crop = st.selectbox("Crop for comparison", gap_crops, key="gap_crop")
    gap_data = filtered[filtered["Crop"].astype(str) == gap_crop]
    gap_areas = sorted(gap_data["Province"].astype(str).unique())
    if not gap_areas:
        st.info("No province-level observations are available for this crop.")
    else:
        gap_target = st.selectbox("Area to assess", gap_areas, key="gap_target")
        target_rows = gap_data[gap_data["Province"].astype(str) == gap_target]
        target_result = _yield_summary(target_rows).iloc[0]
        matching_benchmarks = benchmarks.iloc[0:0]
        can_match_benchmark = (
            "Year" in target_rows.columns
            and len(selected_years) == 1
            and ("Season" not in target_rows.columns or len(selected_seasons) == 1)
        )
        if can_match_benchmark and not benchmarks.empty:
            matching_benchmarks = benchmarks[
                (benchmarks["Crop"] == gap_crop)
                & (benchmarks["Year"] == selected_years[0])
                & (benchmarks["Province"].isin([gap_target, "National"]))
            ]
            if "Season" in target_rows.columns:
                matching_benchmarks = matching_benchmarks[
                    matching_benchmarks["Season"] == selected_seasons[0]
                ]
            else:
                matching_benchmarks = matching_benchmarks[matching_benchmarks["Season"] == ""]

        benchmark_row = None
        if not matching_benchmarks.empty:
            area_benchmark = matching_benchmarks[matching_benchmarks["Province"] == gap_target]
            national_benchmark = matching_benchmarks[matching_benchmarks["Province"] == "National"]
            benchmark_row = area_benchmark.iloc[0] if not area_benchmark.empty else (
                national_benchmark.iloc[0] if not national_benchmark.empty else None
            )

        if benchmark_row is not None:
            reference_yield = float(benchmark_row["Benchmark yield (kg/ha)"])
            gap_kg_ha = reference_yield - target_result["Yield (kg/ha)"]
            gap_pct = gap_kg_ha / reference_yield * 100
            gap_cols = st.columns(4)
            gap_cols[0].metric(f"{gap_target} observed yield", f"{target_result['Yield (kg/ha)']:,.0f} kg/ha", f"n = {int(target_result['observations']):,}")
            gap_cols[1].metric("Cited benchmark", f"{reference_yield:,.0f} kg/ha", str(benchmark_row["Province"]))
            gap_cols[2].metric("Difference to benchmark", f"{gap_kg_ha:+,.0f} kg/ha")
            gap_cols[3].metric("Gap vs benchmark", f"{gap_pct:.1f}%")
            st.caption(
                "The source citation and value are supplied locally and are not independently verified by this app."
            )
            st.link_button("Open cited benchmark source", str(benchmark_row["Source URL"]))
        else:
            if not benchmarks.empty and not can_match_benchmark:
                st.info("To use a cited benchmark, select exactly one year and (when applicable) one season in the sidebar.")
            elif not benchmarks.empty:
                st.info("No cited benchmark matches this crop, area, year, and season. Showing an observed peer comparison instead.")
            st.markdown("**Observed peer comparison (not an official benchmark)**")
            peer_options = [area for area in gap_areas if area != gap_target]
            if not peer_options:
                st.info("No peer provinces are available. Load a matching cited benchmark or select more provinces.")
            else:
                gap_peers = st.multiselect("Peer reference areas", peer_options, default=peer_options, key="gap_peers")
                if not gap_peers:
                    st.info("Choose at least one peer area to calculate an observed reference.")
                else:
                    peer_rows = gap_data[gap_data["Province"].astype(str).isin(gap_peers)]
                    peer_result = _yield_summary(peer_rows).iloc[0]
                    gap_kg_ha = peer_result["Yield (kg/ha)"] - target_result["Yield (kg/ha)"]
                    gap_pct = (
                        gap_kg_ha / peer_result["Yield (kg/ha)"] * 100
                        if peer_result["Yield (kg/ha)"] > 0 else None
                    )
                    gap_cols = st.columns(4)
                    gap_cols[0].metric(f"{gap_target} observed yield", f"{target_result['Yield (kg/ha)']:,.0f} kg/ha", f"n = {int(target_result['observations']):,}")
                    gap_cols[1].metric("Peer reference yield", f"{peer_result['Yield (kg/ha)']:,.0f} kg/ha", f"n = {int(peer_result['observations']):,}")
                    gap_cols[2].metric("Difference to peer", f"{gap_kg_ha:+,.0f} kg/ha")
                    gap_cols[3].metric("Gap vs peer reference", f"{gap_pct:.1f}%" if gap_pct is not None else "Not defined")
                    st.caption(
                        f"Peer areas: {', '.join(gap_peers)}. "
                        "A positive difference means the assessed area is below the selected peers. "
                        "This descriptive gap does not identify causes or imply that the peer yield is attainable everywhere."
                    )

st.markdown("## Input signals")
if is_demo_data:
    st.info("Input comparisons are hidden for synthetic demo data. Its values are illustrative and cannot support conclusions about real farming practices.")
else:
    st.markdown('<div class="section-note">Descriptive, unadjusted differences in reported groups; these associations do not establish cause.</div>', unsafe_allow_html=True)
    input_cols = st.columns(3)
    for column, label in zip(input_cols, ["Fertilizer", "Irrigation", "Improved seed"]):
        with column:
            if label in filtered.columns:
                summary = _yield_summary(filtered, ["Crop", label])
                fig = px.bar(summary, x=label, y="Yield (kg/ha)", color="Crop", barmode="group", text_auto=".0f", custom_data=["observations"])
                fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}<br>Yield: %{y:,.0f} kg/ha<br>Observations: %{customdata[0]}<extra></extra>")
                fig.update_layout(height=300, showlegend=False, margin=dict(l=0, r=0, t=12, b=0), xaxis_title=None, yaxis_title="kg/ha", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
                fig.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info(f"{label} is not available in this extract.")

if "Land tenure" in filtered.columns:
    st.markdown("## Land access and yield by crop")
    tenure = _yield_summary(filtered, ["Crop", "Land tenure"]).rename(columns={"Yield (kg/ha)": "Average yield (kg/ha)"})
    st.dataframe(tenure.sort_values(["Crop", "Average yield (kg/ha)"], ascending=[True, False]).style.format({"Average yield (kg/ha)": "{:,.0f}", "observations": "{:,.0f}"}), width="stretch", hide_index=True)

st.markdown("## District view")
if "District" not in filtered.columns:
    st.info("District-level results are not available in this dataset.")
else:
    district_summary = _yield_summary(filtered, ["Province", "District"])
    st.dataframe(
        district_summary.sort_values(["Province", "Yield (kg/ha)"], ascending=[True, False]).style.format(
            {"Yield (kg/ha)": "{:,.0f}", "observations": "{:,.0f}"}
        ),
        width="stretch",
        hide_index=True,
    )
    district_geojson, geojson_error = _district_geojson()
    if geojson_error:
        st.warning(geojson_error)
    elif district_geojson is None:
        st.caption("To enable the map, add `data/district_boundaries.geojson` with Rwanda district polygons and a district-name property.")
    else:
        map_crop = st.selectbox("Crop to map", sorted(filtered["Crop"].astype(str).unique()), key="district_map_crop")
        map_summary = _yield_summary(filtered[filtered["Crop"].astype(str) == map_crop], ["District"])
        property_name = next(
            name for name in ("District", "district", "NAME_2", "name")
            if all(name in feature.get("properties", {}) for feature in district_geojson["features"])
        )
        geojson_names = {
            str(feature["properties"][property_name]).casefold()
            for feature in district_geojson["features"]
        }
        map_summary = map_summary[map_summary["District"].astype(str).str.casefold().isin(geojson_names)]
        if map_summary.empty:
            st.warning("No district names in the filtered data match the supplied boundary file.")
        else:
            fig = px.choropleth(
                map_summary,
                geojson=district_geojson,
                locations="District",
                featureidkey=f"properties.{property_name}",
                color="Yield (kg/ha)",
                hover_name="District",
                hover_data={"observations": True, "Yield (kg/ha)": ":,.0f"},
                color_continuous_scale="Greens",
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown("## Download data")
download_cols = st.columns(2)
download_cols[0].download_button(
    "Download filtered observations (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="agristat_filtered_observations.csv",
    mime="text/csv",
)
summary_groups = [
    column for column in ["Province", "Crop", "Season", "Year"]
    if column in filtered.columns
]
download_summary = _yield_summary(filtered, summary_groups)
download_cols[1].download_button(
    "Download yield summary (CSV)",
    data=download_summary.to_csv(index=False).encode("utf-8"),
    file_name="agristat_yield_summary.csv",
    mime="text/csv",
)

st.markdown('<div class="insight"><strong>Reading the dashboard:</strong> Compare yields within the same crop and season where possible. Group differences are descriptive and may reflect other factors; they do not establish causation.</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">AgriStat Rwanda · Public demo — no login required · Prepared for the NISR Big Data Hackathon · Demo data is illustrative until an official extract is loaded.</div>', unsafe_allow_html=True)

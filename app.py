from __future__ import annotations

from pathlib import Path
import random

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="AgriStat Rwanda | Productivity intelligence", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = Path(__file__).parent / "data"
ACCENT, INK, GOLD = "#1f7a5a", "#153b2e", "#d7a84d"

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
        rows.append({"Province": province, "District": f"{province} district {rng.randint(1, 6)}", "Crop": crop, "Season": rng.choice(seasons), "Farm size (ha)": round(rng.uniform(.15, 3.8), 2), "Yield (kg/ha)": round(max(100, base * multiplier * rng.uniform(.72, 1.22))), "Fertilizer": "Yes" if fertilizer else "No", "Irrigation": "Yes" if irrigation else "No", "Improved seed": "Yes" if improved_seed else "No", "Land tenure": rng.choice(["Owned", "Rented", "Family land"])})
    return pd.DataFrame(rows)


def _find_data_file() -> Path | None:
    files = sorted(DATA_DIR.glob("*.csv")) + sorted(DATA_DIR.glob("*.xlsx"))
    if len(files) > 1:
        st.error("More than one CSV/XLSX file was found in data/. Keep only the dataset you want the dashboard to load.")
        st.stop()
    return files[0] if files else None


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, str]:
    file_path = _find_data_file()
    if file_path is None:
        return _demo_data(), "Illustrative synthetic demo data"
    try:
        frame = pd.read_csv(file_path) if file_path.suffix.lower() == ".csv" else pd.read_excel(file_path)
    except (ImportError, OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"Could not read {file_path.name}: {exc}")
        st.stop()
    return frame, f"Unverified dataset · {file_path.name}"


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"province": "Province", "region": "Province", "district": "District", "crop": "Crop", "season": "Season", "farm size": "Farm size (ha)", "farm_size": "Farm size (ha)", "yield": "Yield (kg/ha)", "yield (kg/ha)": "Yield (kg/ha)", "fertilizer": "Fertilizer", "irrigation": "Irrigation", "improved seed": "Improved seed", "land tenure": "Land tenure"}
    return frame.rename(columns={column: aliases.get(str(column).strip().lower(), column) for column in frame.columns})


df, source = load_data()
df = _normalise(df)
if not {"Province", "Crop", "Yield (kg/ha)"}.issubset(df.columns):
    missing_columns = sorted({"Province", "Crop", "Yield (kg/ha)"} - set(df.columns))
    st.error(f"The dataset is missing required columns: {', '.join(missing_columns)}. Check the column names in the data README.")
    st.stop()

df["Yield (kg/ha)"] = pd.to_numeric(df["Yield (kg/ha)"], errors="coerce")
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

average_yield = filtered["Yield (kg/ha)"].mean() if filtered["Crop"].nunique() == 1 else None
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

st.markdown("## Productivity overview")
left, right = st.columns([1.35, 1])
with left:
    st.markdown("**Average yield by crop**")
    crop_summary = filtered.groupby("Crop", as_index=False)["Yield (kg/ha)"].mean().sort_values("Yield (kg/ha)")
    fig = px.bar(crop_summary, x="Yield (kg/ha)", y="Crop", orientation="h", text_auto=".0f", color_discrete_sequence=[ACCENT])
    fig.update_layout(height=350, margin=dict(l=0, r=15, t=12, b=0), xaxis_title="Average yield (kg/ha)", yaxis_title=None, plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right:
    st.markdown("**Average yield by province and crop**")
    region_summary = filtered.groupby(["Province", "Crop"], as_index=False)["Yield (kg/ha)"].mean()
    fig = px.bar(region_summary, x="Province", y="Yield (kg/ha)", color="Crop", barmode="group", text_auto=".0f")
    fig.update_layout(height=350, margin=dict(l=0, r=15, t=12, b=0), xaxis_title=None, yaxis_title="Average yield (kg/ha)", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown("## Input signals")
if is_demo_data:
    st.info("Input comparisons are hidden for synthetic demo data. Its values are illustrative and cannot support conclusions about real farming practices.")
else:
    st.markdown('<div class="section-note">Descriptive, unadjusted differences in reported groups; these associations do not establish cause.</div>', unsafe_allow_html=True)
    input_cols = st.columns(3)
    for column, label in zip(input_cols, ["Fertilizer", "Irrigation", "Improved seed"]):
        with column:
            if label in filtered.columns:
                summary = filtered.groupby(["Crop", label], as_index=False)["Yield (kg/ha)"].mean()
                fig = px.bar(summary, x=label, y="Yield (kg/ha)", color="Crop", barmode="group", text_auto=".0f")
                fig.update_layout(height=300, showlegend=False, margin=dict(l=0, r=0, t=12, b=0), xaxis_title=None, yaxis_title="kg/ha", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
                fig.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info(f"{label} is not available in this extract.")

if "Land tenure" in filtered.columns:
    st.markdown("## Land access and yield by crop")
    tenure = filtered.groupby(["Crop", "Land tenure"], as_index=False).agg(average_yield=("Yield (kg/ha)", "mean"), observations=("Yield (kg/ha)", "size"))
    st.dataframe(tenure.sort_values(["Crop", "average_yield"], ascending=[True, False]).style.format({"average_yield": "{:,.0f}", "observations": "{:,.0f}"}), width="stretch", hide_index=True)

st.markdown('<div class="insight"><strong>Reading the dashboard:</strong> Compare yields within the same crop and season where possible. Group differences are descriptive and may reflect other factors; they do not establish causation.</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">AgriStat Rwanda · Public demo — no login required · Prepared for the NISR Big Data Hackathon · Demo data is illustrative until an official extract is loaded.</div>', unsafe_allow_html=True)

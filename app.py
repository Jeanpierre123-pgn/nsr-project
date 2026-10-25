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
    return files[0] if files else None


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, str]:
    file_path = _find_data_file()
    if file_path is None:
        return _demo_data(), "Illustrative demo dataset"
    try:
        frame = pd.read_csv(file_path) if file_path.suffix.lower() == ".csv" else pd.read_excel(file_path)
        return frame, f"NISR extract · {file_path.name}"
    except Exception:
        return _demo_data(), "Illustrative demo dataset (file could not be read)"


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"province": "Province", "region": "Province", "district": "District", "crop": "Crop", "season": "Season", "farm size": "Farm size (ha)", "farm_size": "Farm size (ha)", "yield": "Yield (kg/ha)", "yield (kg/ha)": "Yield (kg/ha)", "fertilizer": "Fertilizer", "irrigation": "Irrigation", "improved seed": "Improved seed", "land tenure": "Land tenure"}
    return frame.rename(columns={column: aliases.get(str(column).strip().lower(), column) for column in frame.columns})


df, source = load_data()
df = _normalise(df)
if not {"Province", "Crop", "Yield (kg/ha)"}.issubset(df.columns):
    st.error("The dataset is missing the minimum columns: Province, Crop and Yield (kg/ha). Showing the demo view instead.")
    df, source = _demo_data(), "Illustrative demo dataset"

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
    st.caption("Public demo mode: this view uses clearly labelled illustrative observations. The dashboard is ready for an approved NISR extract when one is available.")

filtered = df[df["Province"].astype(str).isin(selected_provinces) & df["Crop"].astype(str).isin(selected_crops)].copy()
if "Season" in filtered.columns and selected_seasons:
    filtered = filtered[filtered["Season"].astype(str).isin(selected_seasons)]
filtered["Yield (kg/ha)"] = pd.to_numeric(filtered["Yield (kg/ha)"], errors="coerce")
filtered = filtered.dropna(subset=["Yield (kg/ha)"])

st.markdown('<div class="eyebrow">NISR · 2026 hackathon · Track 1</div>', unsafe_allow_html=True)
st.title("Agricultural productivity, made visible.")
st.markdown('<div class="subtitle">A clear view of how inputs, practices and land access shape crop yields across Rwanda.</div>', unsafe_allow_html=True)
st.markdown(f'<span class="source-pill">● {source}</span>', unsafe_allow_html=True)

with st.expander("About the official NISR source"):
    st.markdown(
        "**Agriculture Household Survey 2024**  \n"
        "Reference ID: `RWA-NISR-RAHS-2024-V0.1`  ·  Producer: National Institute of Statistics of Rwanda  ·  Country: Rwanda"
    )
    st.caption("The official data dictionary includes land tenure; crop grown, seeds, production, agricultural inputs and practices; extension services and agricultural programmes; agricultural tools; and sustainable agriculture.")
    st.markdown("[Open the NISR study page](https://microdata.statistics.gov.rw/index.php/catalog/123) · [Open the data dictionary](https://microdata.statistics.gov.rw/index.php/catalog/123/data_dictionary)")

if filtered.empty:
    st.warning("No observations match the selected filters. Choose at least one province and crop to continue.")
    st.stop()

average_yield = filtered["Yield (kg/ha)"].mean()
top_crop = filtered.groupby("Crop")["Yield (kg/ha)"].mean().idxmax()
top_crop_yield = filtered.groupby("Crop")["Yield (kg/ha)"].mean().max()
provinces_count = filtered["Province"].nunique()

st.markdown("## At a glance")
st.markdown('<div class="section-note">Current view across the selected observations</div>', unsafe_allow_html=True)
metric_cols = st.columns(4)
metric_cols[0].metric("Observations", f"{len(filtered):,}")
metric_cols[1].metric("Average yield", f"{average_yield:,.0f} kg/ha")
metric_cols[2].metric("Leading crop", top_crop, f"{top_crop_yield:,.0f} kg/ha")
metric_cols[3].metric("Areas represented", f"{provinces_count}")

st.markdown("## Productivity overview")
left, right = st.columns([1.35, 1])
with left:
    crop_summary = filtered.groupby("Crop", as_index=False)["Yield (kg/ha)"].mean().sort_values("Yield (kg/ha)")
    fig = px.bar(crop_summary, x="Yield (kg/ha)", y="Crop", orientation="h", text_auto=".0f", color_discrete_sequence=[ACCENT])
    fig.update_layout(height=350, margin=dict(l=0, r=15, t=12, b=0), xaxis_title="Average yield (kg/ha)", yaxis_title=None, plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right:
    region_summary = filtered.groupby("Province", as_index=False)["Yield (kg/ha)"].mean().sort_values("Yield (kg/ha)", ascending=False)
    fig = px.bar(region_summary, x="Province", y="Yield (kg/ha)", text_auto=".0f", color_discrete_sequence=[GOLD])
    fig.update_layout(height=350, margin=dict(l=0, r=15, t=12, b=0), xaxis_title=None, yaxis_title="Average yield (kg/ha)", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown("## Input signals")
st.markdown('<div class="section-note">Compare average yield for farmers reporting each practice</div>', unsafe_allow_html=True)
input_cols = st.columns(3)
for column, label in zip(input_cols, ["Fertilizer", "Irrigation", "Improved seed"]):
    with column:
        if label in filtered.columns:
            summary = filtered.groupby(label)["Yield (kg/ha)"].mean().reset_index()
            fig = px.bar(summary, x=label, y="Yield (kg/ha)", color=label, text_auto=".0f", color_discrete_sequence=[ACCENT, GOLD])
            fig.update_layout(height=300, showlegend=False, margin=dict(l=0, r=0, t=12, b=0), xaxis_title=None, yaxis_title="kg/ha", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info(f"{label} is not available in this extract.")

if "Land tenure" in filtered.columns:
    st.markdown("## Land access and yield")
    tenure = filtered.groupby("Land tenure", as_index=False).agg(average_yield=("Yield (kg/ha)", "mean"), observations=("Yield (kg/ha)", "size"))
    st.dataframe(tenure.sort_values("average_yield", ascending=False).style.format({"average_yield": "{:,.0f}", "observations": "{:,.0f}"}), width="stretch", hide_index=True)

st.markdown(f'<div class="insight"><strong>Reading the dashboard:</strong> {top_crop} has the highest average yield in this view. Use the filters to test whether that pattern holds across provinces, seasons and input practices.</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">AgriStat Rwanda · Public demo — no login required · Prepared for the NISR Big Data Hackathon · Demo data is illustrative until an official extract is loaded.</div>', unsafe_allow_html=True)

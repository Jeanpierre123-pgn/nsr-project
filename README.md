# AgriStat Rwanda

AgriStat Rwanda is a Streamlit dashboard for exploring agricultural productivity across Rwanda. It was prepared for the NISR 2026 Big Data Hackathon, Track 1: Agricultural Productivity.

## What it does

- Shows crop-specific average yields and compares the same crop across provinces.
- Calculates observed yield as total production divided by harvested area when both measures are supplied; otherwise it reports the mean of supplied farm-level yields.
- Shows sample counts with grouped summaries and practice comparisons.
- Compares yield across reported fertilizer, irrigation and improved-seed groups when a dataset is loaded.
- Includes a cited-benchmark gap comparison when a matching benchmark file is supplied; otherwise it offers an explicitly labelled observed peer comparison.
- Provides filtered-data and grouped-yield CSV downloads, with sample counts.
- Draws a district choropleth when compatible district boundary GeoJSON is supplied.
- Filters the view by province, crop, season and year when those fields are available.
- Includes a land-tenure summary and a clear data-source indicator.
- Runs immediately with clearly labelled synthetic demo data when no dataset is present. Input comparisons are hidden in demo mode.
- Reports unreadable, ambiguous, or structurally invalid input data instead of silently substituting demo observations.

Yield differences across input groups are descriptive associations, not evidence that an input caused a yield change. Compare yields within the same crop, and consider season and other confounding factors. The peer-area comparison is not an official or national benchmark and does not establish an attainable yield target.

## Run locally

```powershell
py -3.15 -m pip install -r requirements.txt
py -3.15 -m streamlit run app.py
```

Then open `http://localhost:8501`.

## Deploy publicly

The simplest submission path is [Streamlit Community Cloud](https://share.streamlit.io/): push this repository to GitHub, create a new app from the repository, select `app.py` as the main file, and deploy. After deployment, open the public URL in a private browser window and test the filters before submitting it.

Live demo: https://agristat-rwanda.streamlit.app

### Demo access

This is a public read-only demo and does not require an account, password, or login. Reviewers can open the live URL directly.

## Load an NISR extract

Place exactly one agricultural data `.csv` or `.xlsx` file in `data/` and refresh the app. The optional `benchmarks.csv` file is loaded separately and does not count as a second agricultural data file. Recognised agricultural columns (case-insensitive): `Province`, `District`, `Crop`, `Yield (kg/ha)`, `Production (kg)`, `Harvested area (ha)`, `Season`, `Year`, `Fertilizer`, `Irrigation`, `Improved seed`, and `Land tenure`. Required fields are `Province` and `Crop`, plus either `Yield (kg/ha)` or both `Production (kg)` and `Harvested area (ha)`. If both production and area are supplied, yield summaries use total production divided by total harvested area. Otherwise, summaries use the mean of reported yields. Rows without a province, crop, or usable yield are excluded with a warning.

### Cited benchmark file

Optionally add `data/benchmarks.csv` with columns `Crop`, `Province`, `Year`, `Season`, `Benchmark yield (kg/ha)`, and `Source URL`. Use `National` in the `Province` column for a national benchmark, or the exact province name for a province-specific benchmark. Every row must have a positive yield and source citation, with no duplicate crop/area/year/season keys. The app only compares a benchmark when the selected crop, area, year, and (where the dataset has seasons) season match. A supplied citation and value are not independently verified by the app; check them against the original source before drawing conclusions. Without a matching benchmark, the analyzer falls back to an observed peer comparison, never a fabricated benchmark.

### Optional district map

For district-level tables, include a `District` column. To enable the choropleth map, also add `data/district_boundaries.geojson` as a GeoJSON `FeatureCollection` containing district polygons. Each feature must have a district-name property named `District`, `district`, `NAME_2`, or `name`, matching the dataset's district values. Use boundary data you are permitted to redistribute; the app does not download boundaries.

Filtered observations and crop/province yield summaries can be downloaded as CSV from the dashboard. Gap comparisons use selected peer provinces in the loaded dataset, for the selected crop and seasons; they are descriptive comparisons, not official benchmarks.

Loaded files are labelled as unverified datasets; the app does not independently establish their origin or representativeness. The demo view is synthetic, intentionally labelled as illustrative, and should not be treated as official statistics or used to draw conclusions about farming practices. The supplied webinar and DDI documentation remain the reference materials for dataset definitions and interpretation.

Before submission, follow [SUBMISSION_CHECKLIST.md](./SUBMISSION_CHECKLIST.md). The hackathon requires a public GitHub repository, a publicly accessible deployed app, documentation, a screen recording under three minutes, and the data file or an official data link.

## Official source context

The dashboard is aligned to the NISR [Agricultural Household Survey 2017](https://microdata.statistics.gov.rw/index.php/catalog/90), reference `RWA-NISR-RAHS-2017-V0.1`. Its data dictionary covers land tenure and crops planted; agricultural inputs; agricultural practices; production, use, storage and expenses; extension services; and agricultural programmes for the 2016–2017 agricultural year. See the [official data dictionary](https://microdata.statistics.gov.rw/index.php/catalog/90/data_dictionary) and [related materials](https://microdata.statistics.gov.rw/index.php/catalog/90/related_materials).

The dashboard’s analysis scope follows the relevant NISR sections: Section II (land tenure and crops planted), Section V (fertilizer, pesticides and seeds), Section VI (erosion control, irrigation and mechanization), and Sections VIII A/B (production, use, storage and expenses). The [official questionnaire](https://microdata.statistics.gov.rw/index.php/catalog/90/download/837) and [official report](https://microdata.statistics.gov.rw/index.php/catalog/90/download/838) provide the survey context.

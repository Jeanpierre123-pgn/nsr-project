# AgriStat Rwanda

AgriStat Rwanda is a Streamlit dashboard for exploring agricultural productivity across Rwanda. It was prepared for the NISR 2026 Big Data Hackathon, Track 1: Agricultural Productivity.

## What it does

- Shows average yield by crop and province.
- Compares yield across fertilizer, irrigation and improved-seed practices.
- Filters the view by province, crop and season.
- Includes a land-tenure summary and a clear data-source indicator.
- Runs immediately with an illustrative demo dataset when no official extract is present.

## Run locally

```powershell
py -3.15 -m pip install -r requirements.txt
py -3.15 -m streamlit run app.py
```

Then open `http://localhost:8501`.

## Deploy publicly

The simplest submission path is [Streamlit Community Cloud](https://share.streamlit.io/): push this repository to GitHub, create a new app from the repository, select `app.py` as the main file, and deploy. After deployment, open the public URL in a private browser window and test the filters before submitting it.

## Load an NISR extract

Place one `.csv` or `.xlsx` file in `data/` and refresh the app. The loader recognises these column names (case-insensitive): `Province`, `Crop`, `Yield (kg/ha)`, `Season`, `Fertilizer`, `Irrigation`, `Improved seed`, and `Land tenure`. The minimum required fields are `Province`, `Crop`, and `Yield (kg/ha)`.

The demo view is intentionally labelled as illustrative and should not be treated as official statistics. The supplied webinar and DDI documentation remain the reference materials for dataset definitions and interpretation.

Before submission, follow [SUBMISSION_CHECKLIST.md](./SUBMISSION_CHECKLIST.md). The hackathon requires a public GitHub repository, a publicly accessible deployed app, documentation, a screen recording under three minutes, and the data file or an official data link.

## Official source context

The dashboard is aligned to the NISR [Agriculture Household Survey 2024](https://microdata.statistics.gov.rw/index.php/catalog/123), reference `RWA-NISR-RAHS-2024-V0.1`. Its data dictionary covers land tenure; crop grown, seeds, production and agricultural inputs/practices; extension services and agricultural programmes; agricultural tools; and sustainable agriculture. See the [official data dictionary](https://microdata.statistics.gov.rw/index.php/catalog/123/data_dictionary) for the full file and variable structure.

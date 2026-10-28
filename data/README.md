# Data folder

The dashboard currently runs with an illustrative dataset generated in `app.py` so that the interface can be reviewed without restricted microdata access.

For the final submission, download an approved Agriculture Household Survey extract from the official NISR portal and place the CSV or XLSX file in this folder:

- Catalog: https://microdata.statistics.gov.rw/index.php/catalog
- AHS 2017 study: https://microdata.statistics.gov.rw/index.php/catalog/90
- AHS 2017 data dictionary: https://microdata.statistics.gov.rw/index.php/catalog/90/data_dictionary
- AHS 2017 related materials: https://microdata.statistics.gov.rw/index.php/catalog/90/related_materials

The loader requires `Province` and `Crop`, plus either `Yield (kg/ha)` or both `Production (kg)` and `Harvested area (ha)`. When production and area are supplied, yield summaries are calculated as total production divided by total harvested area. Otherwise, summaries are the mean of supplied farm-level yields. It also recognises `District`, `Season`, `Fertilizer`, `Irrigation`, `Improved seed`, and `Land tenure`.

The productivity-gap view uses a matching cited benchmark when a `benchmarks.csv` file is provided; otherwise it compares the selected province with peer provinces in the same loaded dataset, crop, and filtered season. The peer comparison is not an official national benchmark. Supplied benchmarks need source citations but are not independently verified by the app.

The optional `benchmarks.csv` file requires `Crop`, `Province`, `Year`, `Benchmark yield (kg/ha)`, and `Source URL`; `Season` is also required when the agricultural dataset has seasonal records. Use `National` for a national reference area. Each crop/area/year/season combination must be unique. Group summaries show contributing observation counts. Filtered records and yield summaries can be downloaded from the app.

To display a district map, include a permitted-to-redistribute `district_boundaries.geojson` FeatureCollection in this folder. Each feature needs a district-name property named `District`, `district`, `NAME_2`, or `name`, matching the dataset values. Without boundaries, district summaries are still shown in a table.

## About the supplied ZIP files

The supplied `Microdata.zip` is an EICV7 cross-sectional household dataset and `Microdata (1).zip` is a VUP household dataset. Their files cover household characteristics, poverty, services, expenditure, transfers, and savings; they do not contain the crop-yield fields required for this agricultural productivity dashboard. They were therefore inspected but not loaded as agricultural data.

If the downloaded file is too large for GitHub, do not commit it. Keep this note in the repository and include the official data link in the submission documentation, as requested by the hackathon webinar.

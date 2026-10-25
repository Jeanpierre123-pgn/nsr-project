# Data folder

The dashboard currently runs with an illustrative dataset generated in `app.py` so that the interface can be reviewed without restricted microdata access.

For the final submission, download an approved Agriculture Household Survey extract from the official NISR portal and place the CSV or XLSX file in this folder:

- Catalog: https://microdata.statistics.gov.rw/index.php/catalog
- AHS 2024 study: https://microdata.statistics.gov.rw/index.php/catalog/123
- AHS 2024 data dictionary: https://microdata.statistics.gov.rw/index.php/catalog/123/data_dictionary

The loader requires at least these columns: `Province`, `Crop`, and `Yield (kg/ha)`. It also recognises `Season`, `Fertilizer`, `Irrigation`, `Improved seed`, and `Land tenure`.

## About the supplied ZIP files

The supplied `Microdata.zip` is an EICV7 cross-sectional household dataset and `Microdata (1).zip` is a VUP household dataset. Their files cover household characteristics, poverty, services, expenditure, transfers, and savings; they do not contain the crop-yield fields required for this agricultural productivity dashboard. They were therefore inspected but not loaded as agricultural data.

If the downloaded file is too large for GitHub, do not commit it. Keep this note in the repository and include the official data link in the submission documentation, as requested by the hackathon webinar.

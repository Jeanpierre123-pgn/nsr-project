# NISR Hackathon submission status

## Completed

- [x] Working Streamlit application in `app.py`.
- [x] Professional dashboard interface with filters, KPIs, charts, methodology context, and data-source notes.
- [x] README documentation and setup instructions.
- [x] Official NISR AHS 2017 catalog, data dictionary, questionnaire, and report links included.
- [x] Public GitHub repository: https://github.com/Jeanpierre123-pgn/nsr-project
- [x] Public deployment: https://agristat-rwanda.streamlit.app/
- [x] Deployment verified in a browser; no login or demo credentials are required.
- [x] GitHub branch is synchronized with the deployed project.

## Still required from the team

- [ ] Obtain and add the approved AHS 2017 raw microdata extract, or confirm with the organizers that the official NISR link is accepted instead of uploading the file. The current public app clearly labels its built-in observations as illustrative demo data.
- [ ] Record a screen demonstration under 3 minutes and save it as `.webm` or `.gif` in `demo/`. This must be a real screen recording of the dashboard; it cannot be truthfully generated from the source code alone.
- [ ] Submit the public GitHub URL and public deployment URL in the final submission form.
- [ ] Confirm the team has two eligible students, including at least one Rwandan citizen, and retain the required student documents.
- [ ] Confirm the work is original and acknowledge NISR, the official catalog, the webinar, the DDI/documentation, and any other sources used.

## Team information provided

- MUHAYIMANA Jean Pierre
- TUYISHIME Fabrice

Registration numbers are stored locally in `TEAM_DETAILS_PRIVATE.md` and intentionally excluded from the public repository. Confirm citizenship and attach official student documents in the final submission form.

## Why these items are not automatically complete

The GitHub/deployment tasks are technical and are complete. The remaining tasks require either NISR account access, organizer approval, team eligibility information, or a human-recorded demonstration. They cannot be safely invented by the application.

## Final local smoke test

```powershell
py -3.15 -m pip install -r requirements.txt
py -3.15 -m streamlit run app.py
```

Test the province, crop, and season filters; open the AHS source and methodology panels; and record those interactions for the required demonstration.

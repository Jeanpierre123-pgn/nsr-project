# NISR Hackathon submission checklist

The webinar states that the submission must include a public GitHub link, a deployed app link, and documentation. The repository must contain a README, working project code, a screen recording of no more than three minutes, and the data file or a link to the data.

## Ready in this workspace

- [x] Working Streamlit application in `app.py`.
- [x] `README.md` explains the purpose, data context, interaction, setup, and official NISR links.
- [x] `requirements.txt` lists the runtime dependencies.
- [x] `data/README.md` documents the official data source and required fields.
- [x] Application tested locally at `http://localhost:8501`.

## Must be completed before submission

- [ ] Add an approved NISR data extract, or confirm the official link is accepted instead of uploading the file. Do not submit illustrative demo data as official statistics.
- [ ] Record a screen demonstration under 3 minutes and save it as `.webm` or `.gif` in `demo/`.
- [ ] Create a public GitHub repository and push the complete project.
- [ ] Deploy the app publicly and test the deployed URL in a private/incognito browser window.
- [ ] Replace the local URL in the final submission form with the public deployed URL.
- [ ] Confirm the team has two eligible students, including at least one Rwandan citizen, and retain student eligibility documents.
- [ ] Declare that the work is original and acknowledge NISR, the official catalog, the webinar, and any other sources used.

## Final smoke test

```powershell
py -3.15 -m pip install -r requirements.txt
py -3.15 -m streamlit run app.py
```

Check the filters, charts, data table, official-source expander, and empty-filter state before recording the demonstration.

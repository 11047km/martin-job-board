# Martin's GTA Environmental & GIS Job Board

A deployable, daily-refreshed job board tailored to Martin Zhang's **Bachelor of Environmental Studies in Geography and Environmental Management**, municipal/provincial GIS experience, ArcGIS Online work, geodatabase maintenance, spatial analysis, data validation, and sustainability background.

## What it searches

The default no-secret configuration covers:

- Government of Canada Job Bank searches across GIS, geospatial, environmental, sustainability, planning, conservation, spatial-data and land-use terms
- CivicJobs.ca's Ontario, GIS, environmental services, planning, policy, data-analysis and conservation RSS feeds
- Conservation Ontario's structured province-wide careers table
- Independent official career-page checks for the City of Toronto, Ontario Public Service, Mississauga, Peel Region, TRCA, Credit Valley Conservation, Lake Simcoe Region Conservation Authority, Grand River Conservation Authority, Metrolinx, Toronto Hydro, Alectra and Hydro One
- Configurable public Greenhouse, Lever, Ashby and SmartRecruiters boards
- Optional Adzuna Canada API coverage for broader aggregation

The scraper deliberately does **not** automate login-gated LinkedIn or Indeed pages. Those sites change frequently and may prohibit automated scraping. Add employer ATS feeds or use the optional API connector instead.

## Personalization

`config/profile.json` contains:

- High-value resume keywords and weights
- New-grad/early-career title boosts
- Seniority penalties
- GTA city definitions
- Relevant and excluded role terms
- Career-area classification rules

The front end supports full-text search, GTA/Canada location filters, career-area filters, recent postings, new-grad-friendly roles, match score, saved jobs, deadlines and source health.

## Deploy to GitHub Pages

1. Create a new GitHub repository, for example `martin-job-board`.
2. Upload every file in this folder to the repository's `main` branch.
3. In GitHub, open **Settings → Pages**.
4. Under **Build and deployment**, choose **GitHub Actions**.
5. Open **Actions → Deploy GitHub Pages** and run it once if it has not started automatically.
6. Open **Actions → Refresh job board** and run it manually once to test the live sources.

The board then refreshes every day at approximately **6:17 a.m. Toronto time during daylight saving time**. GitHub Actions cron schedules are in UTC.

## Optional: add Adzuna coverage

Create a free Adzuna developer account, then add these repository secrets under **Settings → Secrets and variables → Actions**:

- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`

The board still works without them; source health will show that connector as degraded rather than failing the whole refresh.

## Add more employer ATS boards

Edit `config/sources.json`. Examples:

```json
{
  "greenhouse": [{"company": "Example", "token": "example"}],
  "lever": [{"company": "Example", "site": "example"}],
  "ashby": [{"company": "Example", "board": "example"}],
  "smartrecruiters": [{"company": "Example", "identifier": "ExampleCompany"}]
}
```

Only add public board identifiers from an employer's official careers URL.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/update_jobs.py
python -m unittest discover -s tests -v
python -m http.server 8000
```

Open `http://localhost:8000`.

## Reliability safeguards

- Each source runs independently; one failed source does not stop the refresh. Employer pages appear separately in source health so gaps are visible.
- `data/source_health.json` records fetched/kept counts, errors and duration.
- Recently seen jobs are preserved for up to 45 days during temporary source outages.
- Expired postings are removed based on closing date.
- Duplicate jobs are merged using normalized title, employer and location.
- Tests validate scoring, JSON structure, unique IDs and application URLs before refreshed data is committed.

## Important limitation

No job board can guarantee every opening in Canada. Employers use many systems, some do not expose public feeds, and postings can be removed without notice. This project is designed for broad, transparent coverage and easy expansion—not a claim of literal completeness. Always verify the deadline and requirements on the employer's page.

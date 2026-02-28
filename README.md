# Jobsuche Agent (Template)

AI-assisted job discovery with the Arbeitsagentur `jobsuche-api` + OpenAI ranking.

Use this repository as a starting point for your own personalized job alert workflow.

## What this project does

- Fetches current jobs from the Arbeitsagentur API.
- Uses OpenAI to shortlist and rank matching jobs.
- Writes Markdown reports to `reports/`.
- Tracks previously suggested jobs to prevent duplicates in `data/`.

## 1) Create your own repo from this template

1. Click **Use this template** on GitHub.
2. Create your own repository.
3. Clone your new repo locally.

## 2) Local setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Add your OpenAI key to `.env`:

```env
OPENAI_API_KEY=your_key_here
```

## 3) Personalize

Edit these files:

- `config/candidate_profile.md` - your profile, constraints, and preferences
- `config/job_search_config.env` - terms, location, radius, recency

## 4) Run

```bash
python3 scripts/generate_report.py
```

Output:

- `reports/job_report_<timestamp>.md`

## GitHub Actions usage (optional)

This template includes a workflow to get job suggestions sent via email:

- `.github/workflows/job_search.yml`: scheduled or manual run, sends report email, commits new reports.

### Automated scheduled email workflow (`job_search.yml`)

Default schedule: every Saturday at `05:00 UTC` (edit the cron if needed).

Required secrets:

- `OPENAI_API_KEY`
- `SMTP_SERVER_ADDRESS`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_TO_EMAIL`

Optional SMTP secrets:

- `SMTP_SERVER_PORT` (defaults to `587`)
- `SMTP_FROM_NAME` (defaults to `Job Alert Agent`)

Setup steps:

1. Add the required secrets in your repository settings.
2. Run `Job Search Workflow` once manually from the **Actions** tab to verify email delivery.

## Project structure

- `scripts/generate_report.py` - main orchestrator
- `scripts/fetch_jobsuche_jobs.py` - API fetch + detail enrichment
- `scripts/report_template.html` - HTML report template
- `config/` - your candidate config files
- `data/` - deduplication history
- `reports/` - generated reports

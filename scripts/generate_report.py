#!/usr/bin/env python3
import json
import os
import sys
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from pydantic import BaseModel, Field

# Ensure we can import from the scripts directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fetch_jobsuche_jobs import (
    fetch_detail_context,
    search_jobs_page,
    choose_stronger,
    parse_date,
)
from openai import OpenAI
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"


def choose_existing_path(paths: List[Path]) -> Path | None:
    """Return the first existing path from a list of paths, or None if none exist."""
    for path in paths:
        if path.exists():
            return path
    return None


def get_env_file_path() -> Path:
    """Get the path to the main .env file, allowing for environment variable overrides."""
    override = os.getenv("JOB_ALERT_ENV_FILE")
    if override:
        return Path(override).expanduser()
    return ROOT_DIR / ".env"


def get_search_config_path() -> Path:
    """Get the path to the job search configuration file."""
    override = os.getenv("JOB_ALERT_SEARCH_CONFIG_FILE")
    if override:
        return Path(override).expanduser()
    return CONFIG_DIR / "job_search_config.env"


def get_candidate_profile_path() -> Path:
    """Get the path to the candidate profile Markdown file."""
    override = os.getenv("JOB_ALERT_CANDIDATE_PROFILE_FILE")
    if override:
        return Path(override).expanduser()
    return CONFIG_DIR / "candidate_profile.md"


def get_past_suggestions_path() -> Path:
    """Get the path to the JSON file storing past job suggestions."""
    override = os.getenv("JOB_ALERT_PAST_SUGGESTIONS_FILE")
    if override:
        return Path(override).expanduser()
    return DATA_DIR / "past_job_suggestions.json"


def get_reports_dir() -> Path:
    """Get the directory path where generated job reports should be saved."""
    override = os.getenv("JOB_ALERT_REPORTS_DIR")
    if override:
        return Path(override).expanduser()
    return ROOT_DIR / "reports"


def load_project_environment() -> None:
    """Load environment variables from project configuration files."""
    env_path = get_env_file_path()
    if env_path.exists():
        load_dotenv(env_path)

    search_config_path = get_search_config_path()
    if search_config_path.exists():
        load_dotenv(search_config_path)
    else:
        print(
            f"[warn] Search config not found at {search_config_path}. Using built-in defaults."
        )


class Stage1Response(BaseModel):
    shortlisted_refnrs: List[str] = Field(
        description="List of all job refnr IDs that could even remotely fit based on the summary"
    )


class JobMatch(BaseModel):
    title: str
    employer: str
    location: str
    refnr: str = Field(description="The refnr of the job posting")
    reason: str = Field(
        description="Short description explaining why the job fits the user's profile"
    )
    detail_url: str


class Stage2Response(BaseModel):
    top_jobs: List[JobMatch]


def verify_past_suggestions(
    file_path: str = str(DATA_DIR / "past_job_suggestions.json"),
) -> List[Dict[str, Any]]:
    """Verify which past job suggestions are still active and remove inactive ones from the local record."""
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            past_jobs = json.load(f)
        except json.JSONDecodeError:
            past_jobs = []

    print(f"Verifying {len(past_jobs)} past suggestions for availability...")
    active_jobs = []

    def check_job(job):
        refnr = job.get("refnr")
        if not refnr:
            return None
        detail = fetch_detail_context(refnr)
        if detail.get("description_full"):
            return job
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_job, past_jobs)
        for result in results:
            if result:
                active_jobs.append(result)

    print(
        f"Kept {len(active_jobs)} active past jobs, removed {len(past_jobs) - len(active_jobs)}."
    )

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(active_jobs, f, indent=2, ensure_ascii=False)

    return active_jobs


def append_to_past_suggestions(
    matches, file_path: str = str(DATA_DIR / "past_job_suggestions.json")
):
    """Append new job matches to the historical suggestions record."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    past_jobs = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                past_jobs = json.load(f)
            except json.JSONDecodeError:
                pass

    for m in matches:
        past_jobs.append(
            {
                "date": timestamp,
                "company": m.get("company", "N/A"),
                "role": m.get("role", "N/A"),
                "refnr": m.get("refnr", "N/A"),
            }
        )

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(past_jobs, f, indent=2, ensure_ascii=False)


def read_profile_context() -> tuple[str, str]:
    """Read the candidate profile and recently suggested jobs to build the context for the LLM."""
    candidate_profile_path = get_candidate_profile_path()
    try:
        with open(candidate_profile_path, "r", encoding="utf-8") as f:
            candidate_profile = f.read()
    except FileNotFoundError:
        candidate_profile = "Find relevant IT jobs."

    past_suggestions_path = get_past_suggestions_path()
    past_jobs = verify_past_suggestions(str(past_suggestions_path))

    if not past_jobs:
        past_suggestions = "None"
    else:
        # Send company, role, and refnr to save tokens
        streamlined = [
            {
                "company": j.get("company"),
                "role": j.get("role"),
                "refnr": j.get("refnr"),
            }
            for j in past_jobs
        ]
        past_suggestions = json.dumps(streamlined, ensure_ascii=False)

    return candidate_profile, past_suggestions


def shortlist_candidates(
    client: OpenAI,
    summary_data: Dict[str, Any],
    candidate_profile: str,
    past_suggestions: str,
) -> List[str]:
    """Use the LLM to aggressively shortlist all potentially relevant jobs based on summaries."""
    stage1_prompt = f"""
    You are a specialized Job Search Agent. Your goal is to shortlist ALL jobs from the latest API fetch that could even remotely fit. ("Wähle alle Jobs aus, die auch nur im Entferntesten passen könnten")

    CRITICAL INSTRUCTION: Err on the side of inclusion! Do NOT be overly strict at this stage. 
    It is much better to shortlist irrelevant jobs than to miss a potentially good one. 
    Only exclude jobs that are clearly and completely irrelevant. 
    If you are in doubt, SHORTLIST IT. We expect you to find AT LEAST 15-20 candidates given a large list.

    User Profile & Preferences:
    {candidate_profile}

    Past Suggestions (DO NOT select these again):
    {past_suggestions}

    Available Jobs (Summary):
    {json.dumps(summary_data.get("candidates", []), ensure_ascii=False)}

    Please analyze the 'titel', 'arbeitgeber', and 'arbeitsort' of the available jobs and aggressively select all refnr IDs that could even remotely fit.
    """

    print(
        "Stage 1: Shortlisting all potentially fitting candidates from summary data using OpenAI..."
    )

    for attempt in range(3):
        try:
            response1 = client.beta.chat.completions.parse(
                model="gpt-5.2",
                messages=[{"role": "user", "content": stage1_prompt}],
                response_format=Stage1Response,
            )
            shortlist = response1.choices[0].message.parsed.shortlisted_refnrs
            print(f"Stage 1 Shortlisted {len(shortlist)} candidates.")
            return shortlist
        except Exception as e:
            print(f"Error in Stage 1 (attempt {attempt + 1}): {e}")
            if attempt == 2:
                sys.exit(1)


def fetch_deep_dive_details(
    summary_data: Dict[str, Any], shortlist: List[str]
) -> List[Dict[str, Any]]:
    """Fetch the full description and details for each shortlisted candidate concurrently."""
    deep_dive_candidates = []
    jobs_to_fetch = [
        job
        for job in summary_data.get("candidates", [])
        if job.get("refnr") in shortlist
    ]

    print(
        f"Fetching full details for {len(jobs_to_fetch)} shortlisted candidates concurrently..."
    )

    def fetch_job_details(job: Dict[str, Any]) -> Dict[str, Any]:
        refnr = job.get("refnr")
        ort = job.get("arbeitsort", "")
        if isinstance(ort, dict):
            ort = ort.get("ort", "")

        detail = fetch_detail_context(refnr)

        return {
            "refnr": refnr,
            "titel": job.get("titel"),
            "arbeitgeber": job.get("arbeitgeber"),
            "arbeitsort": ort,
            "description_full": detail.get("description_full", ""),
            "detail_url": detail.get("detail_url", ""),
            "vertragsdauer_detail": detail.get("vertragsdauer_detail", ""),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_job_details, jobs_to_fetch)
        for result in results:
            deep_dive_candidates.append(result)

    return deep_dive_candidates


def evaluate_top_jobs(
    client: OpenAI, candidate_profile: str, deep_dive_candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Use the LLM to evaluate full job details and select the absolute best matches."""
    stage2_prompt = f"""
    You are a specialized Job Search Agent. Your goal is to select the most relevant jobs from the shortlisted candidates. You can select fewer or more depending on how many truly excellent matches there are (e.g., 2 to 5 jobs).

    User Profile & Preferences:
    {candidate_profile}
    
    CRITICAL INSTRUCTION: Ignore any specific format requests in the user profile above.

    Shortlisted Jobs (Full Details):
    {json.dumps(deep_dive_candidates, ensure_ascii=False)}

    Read the full descriptions carefully. Select the jobs that best fit the user's criteria. 
    Pay special attention to the permanent contract requirement (unbefristet), the location, and the technical/AI direction.
    Provide a compelling reason for each selection explaining why it fits the user perfectly.
    """

    print("Stage 2: Evaluating full descriptions to select the best job matches...")

    for attempt in range(3):
        try:
            response2 = client.beta.chat.completions.parse(
                model="gpt-5.2",
                messages=[{"role": "user", "content": stage2_prompt}],
                response_format=Stage2Response,
            )
            final_jobs_models = response2.choices[0].message.parsed.top_jobs
            final_jobs = [j.model_dump() for j in final_jobs_models]
            return final_jobs
        except Exception as e:
            print(f"Error in Stage 2 (attempt {attempt + 1}): {e}")
            if attempt == 2:
                sys.exit(1)


def build_and_save_reports(
    final_jobs: List[Dict[str, Any]], deep_dive_candidates: List[Dict[str, Any]]
):
    """Generate and save the final job recommendations as both Markdown and HTML reports."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    reports_dir = get_reports_dir()
    report_path = reports_dir / f"job_report_{timestamp}.md"
    html_report_path = reports_dir / f"job_report_{timestamp}.html"

    report_content = "# Job Search Report\n\n"
    report_content += f"Hier sind die {len(final_jobs)} am besten passenden Jobs, die heute für dein Profil gefunden wurden.\n\n"

    matches_to_log = []
    jobs_html_blocks = []
    for i, job in enumerate(final_jobs, 1):
        # Markdown Part
        report_content += f"## {i}. {job['title']}\n"
        report_content += f"**Arbeitgeber:** {job['employer']}\n"
        report_content += f"**Standort:** {job['location']}\n"
        report_content += (
            f"**Link:** [Stellenanzeige Agentur für Arbeit]({job['detail_url']})\n\n"
        )
        report_content += f"**Warum diese Stelle passt:**\n{job['reason']}\n\n"
        report_content += "---\n\n"

        # HTML Part
        jobs_html_blocks.append(f"""
        <div class="job-item">
            <h2 class="job-title"><a href="{job["detail_url"]}">{job["title"]}</a></h2>
            <div class="job-meta">
                <div>🏢 <b>{job["employer"]}</b></div>
                <div>📍 {job["location"]}</div>
            </div>
            <div class="reason-text">
                {job["reason"]}
            </div>
            <div class="action-link">
                <a href="{job["detail_url"]}">→ Zur Stellenanzeige</a>
            </div>
        </div>
        """)

        matches_to_log.append(
            {
                "company": job["employer"],
                "role": job["title"],
                "refnr": job.get("refnr", ""),
            }
        )

    # Read the HTML Template
    template_path = os.path.join(os.path.dirname(__file__), "report_template.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as tf:
            html_template = tf.read()
    else:
        # Fallback minimal template
        html_template = (
            "<html><body><h1>{job_count} Jobs</h1>\n{jobs_html}</body></html>"
        )

    # Use .replace() instead of .format() to avoid throwing KeyErrors on CSS curly braces
    html_content = html_template.replace("{job_count}", str(len(final_jobs)))
    html_content = html_content.replace("{jobs_html}", "\n".join(jobs_html_blocks))

    os.makedirs(reports_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    with open(html_report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Generated Markdown report at {report_path}")
    print(f"Generated temporary HTML report at {html_report_path}")

    # Log to past_job_suggestions.json
    past_suggestions_path = get_past_suggestions_path()
    print(f"Logging new suggestions to {past_suggestions_path}...")
    append_to_past_suggestions(matches_to_log, str(past_suggestions_path))
    print("Logged new suggestions.")


def generate_report():
    """Main pipeline execution: fetch jobs, filter via LLM, and generate the final report."""
    # Load configuration
    load_project_environment()

    # Before generating report, we dynamically fetch jobs directly from Python
    summary_data = fetch_jobs_dynamically()

    # 120s timeout for network requests so it doesn't hang indefinitely, but gives large requests time to finish
    client = OpenAI(timeout=120.0)

    candidate_profile, past_suggestions = read_profile_context()

    shortlist = shortlist_candidates(
        client, summary_data, candidate_profile, past_suggestions
    )
    if not shortlist:
        print("No candidates found in Stage 1.")
        return

    deep_dive_candidates = fetch_deep_dive_details(summary_data, shortlist)
    if not deep_dive_candidates:
        print("No details could be fetched for candidates.")
        return

    final_jobs = evaluate_top_jobs(client, candidate_profile, deep_dive_candidates)
    if not final_jobs:
        print("No candidates selected in Stage 2.")
        return

    build_and_save_reports(final_jobs, deep_dive_candidates)


def fetch_jobs_dynamically():
    """Dynamically query the Jobsuche API for jobs based on current environment variables and deduplicate results."""
    import shlex

    terms_str = os.getenv("SEARCH_TERMS", "")
    terms = shlex.split(terms_str) if terms_str else [""]
    where = os.getenv("SEARCH_WHERE", "Berlin")
    radius_km = int(os.getenv("SEARCH_RADIUS_KM", 40))
    days = int(os.getenv("SEARCH_DAYS", 1))

    raw_jobs: List[Dict] = []
    query_count = 0

    print(
        f"Executing API search for terms: {terms} around {where} ({radius_km}km) within {days} days..."
    )

    for term in terms:
        page = 1
        total_pages = None
        while True:
            try:
                jobs, max_results = search_jobs_page(
                    what=term,
                    where=where,
                    radius_km=radius_km,
                    days=days,
                    size=100,
                    page=page,
                )
                query_count += 1
            except Exception as exc:
                print(
                    f"[warn] query failed term='{term}' page={page}: {exc}",
                    file=sys.stderr,
                )
                break

            raw_jobs.extend(jobs)
            if total_pages is None:
                total_pages = max(1, (max_results + 100 - 1) // 100)
            if page >= total_pages:
                break
            page += 1

    deduped: Dict[str, Dict] = {}
    for job in raw_jobs:
        refnr = (job.get("refnr") or "").strip()
        if not refnr:
            continue
        current = deduped.get(refnr)
        deduped[refnr] = choose_stronger(current, job) if current else job

    selected_jobs = list(deduped.values())

    candidates_summary: List[Dict] = []
    for job in selected_jobs:
        refnr = job.get("refnr", "")
        summary_obj = {
            "titel": job.get("titel", ""),
            "beruf": job.get("beruf", ""),
            "arbeitgeber": job.get("arbeitgeber", ""),
            "refnr": refnr,
            "arbeitsort": (job.get("arbeitsort") or {}).get("ort", ""),
            "region": (job.get("arbeitsort") or {}).get("region", ""),
            "entfernung_km": (job.get("arbeitsort") or {}).get("entfernung", ""),
            "published_api": parse_date(job.get("aktuelleVeroeffentlichungsdatum", "")),
            "query_term": job.get("_query_term", ""),
        }
        candidates_summary.append(summary_obj)

    generated_at = datetime.now().replace(microsecond=0).isoformat() + "Z"

    out_summary = {
        "generated_at": generated_at,
        "source": "jobsuche-api",
        "query_terms": terms,
        "query_count": query_count,
        "raw_result_count": len(raw_jobs),
        "deduped_count": len(deduped),
        "candidate_count": len(selected_jobs),
        "candidates": candidates_summary,
    }

    print(f"Found {len(selected_jobs)} unique candidates from the API search.")
    return out_summary


if __name__ == "__main__":
    generate_report()

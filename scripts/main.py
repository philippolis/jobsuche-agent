#!/usr/bin/env python3
import sys
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any

from openai import OpenAI

# Try importing the modularized components
try:
    from config import load_project_environment, get_reports_dir
    from past_job_suggestions import cleanup_inactive_jobs, save_suggested_jobs
    from llm_agent import shortlist_relevant_jobs, select_best_matches
    from jobsuche_api import fetch_all_matching_jobs, fetch_job_details
    from config import get_candidate_profile_path, get_past_suggestions_path
    from report_generator import generate_html
except ImportError:
    # If run from the root directory or otherwise needing sys.path tweaking
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import load_project_environment, get_reports_dir, get_candidate_profile_path, get_past_suggestions_path
    from past_job_suggestions import save_suggested_jobs, cleanup_inactive_jobs
    from llm_agent import shortlist_relevant_jobs, select_best_matches
    from jobsuche_api import fetch_all_matching_jobs, fetch_job_details
    from report_generator import generate_html

def read_profile_context() -> tuple[str, str]:
    """Read the candidate profile and recently suggested jobs to build the context for the LLM."""
    candidate_profile_path = get_candidate_profile_path()
    try:
        with open(candidate_profile_path, "r", encoding="utf-8") as f:
            candidate_profile = f.read()
    except FileNotFoundError:
        candidate_profile = "Find relevant IT jobs."

    past_suggestions_path = get_past_suggestions_path()
    past_jobs = cleanup_inactive_jobs(str(past_suggestions_path))

    if not past_jobs:
        past_suggestions = "None"
    else:
        # Send company, role, and refnr to save tokens
        import json
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

    def _fetch_single_job_details(job: Dict[str, Any]) -> Dict[str, Any]:
        refnr = job.get("refnr")
        ort = job.get("arbeitsort", "")
        if isinstance(ort, dict):
            ort = ort.get("ort", "")

        detail = fetch_job_details(refnr)

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
        results = executor.map(_fetch_single_job_details, jobs_to_fetch)
        for result in results:
            deep_dive_candidates.append(result)

    return deep_dive_candidates


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

        matches_to_log.append(
            {
                "company": job["employer"],
                "role": job["title"],
                "refnr": job.get("refnr", ""),
            }
        )

    # HTML Part: utilizing the new report generator module
    import os
    from pathlib import Path
    template_path = Path(os.path.join(os.path.dirname(__file__), "report_template.html"))
    html_content = generate_html(final_jobs, template_path)

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
    save_suggested_jobs(matches_to_log, str(past_suggestions_path))
    print("Logged new suggestions.")


def generate_report():
    """Main pipeline execution: fetch jobs, filter via LLM, and generate the final report."""
    # Load configuration
    load_project_environment()

    # Dynamic search mapped to the externalized file
    summary_data = fetch_all_matching_jobs()

    # 120s timeout for network requests so it doesn't hang indefinitely, but gives large requests time to finish
    client = OpenAI(timeout=120.0)

    candidate_profile, past_suggestions = read_profile_context()

    shortlist = shortlist_relevant_jobs(
        client, summary_data, candidate_profile, past_suggestions
    )
    if not shortlist:
        print("No candidates found in Stage 1.")
        return

    deep_dive_candidates = fetch_deep_dive_details(summary_data, shortlist)
    if not deep_dive_candidates:
        print("No details could be fetched for candidates.")
        return

    final_jobs = select_best_matches(client, candidate_profile, deep_dive_candidates)
    if not final_jobs:
        print("No candidates selected in Stage 2.")
        return

    build_and_save_reports(final_jobs, deep_dive_candidates)


if __name__ == "__main__":
    generate_report()

import json
import os
import concurrent.futures
from typing import List, Dict, Any
from jobsuche_api import fetch_job_details
from datetime import datetime

def cleanup_inactive_jobs(file_path: str) -> List[Dict[str, Any]]:
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
        detail = fetch_job_details(refnr)
        if detail.get("description_full"):
            return job
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_job, past_jobs)
        for result in results:
            if result:
                active_jobs.append(result)

    print(f"Kept {len(active_jobs)} active past jobs, removed {len(past_jobs) - len(active_jobs)}.")

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(active_jobs, f, indent=2, ensure_ascii=False)

    return active_jobs

def save_suggested_jobs(matches: List[Dict[str, Any]], file_path: str):
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

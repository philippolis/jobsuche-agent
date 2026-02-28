#!/usr/bin/env python3
"""Fetch current jobs from jobsuche-api and enrich with optional detail context.

Design goals:
- no hardcoded employer allowlist
- broad technical search based on dynamic terms
- provide richer context (full job description) for downstream relevance decisions
- no hard validation gate for link reachability or UNBEFRISTET checks
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

try:
    from config import get_search_config
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import get_search_config

API_BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
JOB_DETAIL_BASE = "https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}"
API_HEADERS = {
    "X-API-Key": "jobboerse-jobsuche",
    "User-Agent": "job-alert-agent/1.0",
}


def normalize(text: str) -> str:
    """Normalize text by converting to lowercase and replacing german umlauts/special characters."""
    text = (text or "").strip().lower()
    replacements = {
        "\u00e4": "ae",
        "\u00f6": "oe",
        "\u00fc": "ue",
        "\u00df": "ss",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text)


def _fetch_text(
    url: str, headers: Dict[str, str] | None = None, timeout: int = 30
) -> Tuple[int, str]:
    """Fetch raw text content from a URL via GET request."""
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        status_code = getattr(response, "status", response.getcode())
        body = response.read().decode("utf-8", errors="replace")
        return status_code, body


def _fetch_json(
    url: str, headers: Dict[str, str] | None = None, timeout: int = 30
) -> Dict:
    """Fetch and parse JSON content from a URL via GET request."""
    _, body = _fetch_text(url, headers=headers, timeout=timeout)
    return json.loads(body)


def parse_date(date_str: str) -> str:
    """Safely parse a date string and return it in ISO format (YYYY-MM-DD), or empty string if invalid."""
    if not date_str:
        return ""
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


def fetch_jobs_page(
    what: str,
    where: str,
    radius_km: int,
    days: int,
    size: int,
    page: int,
    angebotsart: str = "1",
    zeitarbeit: str = "false",
    pav: str = "false",
    arbeitgeber: str = "",
    berufsfeld: str = "",
) -> Tuple[List[Dict], int]:
    """Query a single page of job alerts from the API given search criteria."""
    params = {
        "wo": where,
        "umkreis": str(radius_km),
        "veroeffentlichtseit": str(days),
        "size": str(size),
        "page": str(page),
    }

    # Add optional filters only if they have values
    if angebotsart:
        params["angebotsart"] = angebotsart
    if zeitarbeit:
        params["zeitarbeit"] = zeitarbeit
    if pav:
        params["pav"] = pav
    if arbeitgeber:
        params["arbeitgeber"] = arbeitgeber
    if berufsfeld:
        params["berufsfeld"] = berufsfeld
    if what:
        params["was"] = what

    url = f"{API_BASE}?{urlencode(params)}"
    payload = _fetch_json(url, headers=API_HEADERS)
    jobs = payload.get("stellenangebote") or []
    max_results = int(payload.get("maxErgebnisse") or len(jobs))
    for job in jobs:
        job["_query"] = params
        job["_query_term"] = what
    return jobs, max_results


def get_latest_job_version(existing: Dict, candidate: Dict) -> Dict:
    """Given two job dictionaries, return the one that has a more recent publication date."""
    existing_date = parse_date(existing.get("aktuelleVeroeffentlichungsdatum", ""))
    candidate_date = parse_date(candidate.get("aktuelleVeroeffentlichungsdatum", ""))
    if candidate_date > existing_date:
        return candidate
    return existing


def _extract_angular_state(html: str) -> Dict:
    """Extract and parse the JSON payload from the <script id="ng-state"> tag in an HTML page."""
    match = re.search(
        r'<script id="ng-state" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        return {}
    payload = match.group(1)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}


def fetch_job_details(refnr: str) -> Dict:
    """Fetch and extract detailed context for a specific job offering using its reference number."""
    detail_url = JOB_DETAIL_BASE.format(refnr=quote(refnr))
    out = {
        "detail_url": detail_url,
        "detail_http_status": 0,
        "detail_error": "",
        "description_full": "",
        "published_detail": "",
        "modified_detail": "",
        "vertragsdauer_detail": "",
        "detail_arbeitsorte": [],
    }
    try:
        status_code, html = _fetch_text(detail_url, timeout=30)
        out["detail_http_status"] = status_code
    except (HTTPError, URLError) as exc:
        out["detail_error"] = str(exc)
        return out

    state = _extract_angular_state(html)
    detail = state.get("jobdetail") or {}
    out["description_full"] = detail.get("stellenangebotsBeschreibung", "")
    out["published_detail"] = parse_date(detail.get("datumErsteVeroeffentlichung", ""))
    out["modified_detail"] = detail.get("aenderungsdatum", "")
    out["vertragsdauer_detail"] = detail.get("vertragsdauer", "")

    locations = []
    for loc in detail.get("stellenlokationen") or []:
        adr = loc.get("adresse") or {}
        plz = adr.get("plz", "")
        ort = adr.get("ort", "")
        if plz or ort:
            locations.append(f"{plz} {ort}".strip())
    out["detail_arbeitsorte"] = locations
    return out


def fetch_all_matching_jobs() -> Dict[str, Any]:
    """Dynamically query the Jobsuche API for jobs based on current definition and deduplicate results."""

    search_config = get_search_config().get("search", {})
    terms = search_config.get("terms", [""])
    if not terms:
        terms = [""]
    where = search_config.get("where", "Berlin")
    radius_km = int(search_config.get("radius_km", 40))
    days = int(search_config.get("days", 1))

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
                jobs, max_results = fetch_jobs_page(
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
        deduped[refnr] = get_latest_job_version(current, job) if current else job

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

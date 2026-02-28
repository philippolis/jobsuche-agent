#!/usr/bin/env python3
"""Fetch current jobs from jobsuche-api and enrich with optional detail context.

Design goals:
- no hardcoded employer allowlist
- broad technical search based on dynamic terms
- provide richer context (full job description) for downstream relevance decisions
- no hard validation gate for link reachability or UNBEFRISTET checks
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
JOB_DETAIL_BASE = "https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}"
API_HEADERS = {
    "X-API-Key": "jobboerse-jobsuche",
    "User-Agent": "job-alert-agent/1.0",
}


def normalize(text: str) -> str:
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


def fetch_text(url: str, headers: Dict[str, str] | None = None, timeout: int = 30) -> Tuple[int, str]:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        status_code = getattr(response, "status", response.getcode())
        body = response.read().decode("utf-8", errors="replace")
        return status_code, body


def fetch_json(url: str, headers: Dict[str, str] | None = None, timeout: int = 30) -> Dict:
    _, body = fetch_text(url, headers=headers, timeout=timeout)
    return json.loads(body)


def parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


def search_jobs_page(
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
    payload = fetch_json(url, headers=API_HEADERS)
    jobs = payload.get("stellenangebote") or []
    max_results = int(payload.get("maxErgebnisse") or len(jobs))
    for job in jobs:
        job["_query"] = params
        job["_query_term"] = what
    return jobs, max_results


def choose_stronger(existing: Dict, candidate: Dict) -> Dict:
    existing_date = parse_date(existing.get("aktuelleVeroeffentlichungsdatum", ""))
    candidate_date = parse_date(candidate.get("aktuelleVeroeffentlichungsdatum", ""))
    if candidate_date > existing_date:
        return candidate
    return existing


def extract_ng_state(html: str) -> Dict:
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


def fetch_detail_context(refnr: str) -> Dict:
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
        status_code, html = fetch_text(detail_url, timeout=30)
        out["detail_http_status"] = status_code
    except (HTTPError, URLError) as exc:
        out["detail_error"] = str(exc)
        return out

    state = extract_ng_state(html)
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



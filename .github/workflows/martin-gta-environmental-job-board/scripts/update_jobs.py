from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetchers.adzuna import AdzunaFetcher
from fetchers.ats import ATSFetcher
from fetchers.career_pages import CareerPagesFetcher
from fetchers.civicjobs import CivicJobsFetcher
from fetchers.conservation_ontario import ConservationOntarioFetcher
from fetchers.jobbank import JobBankFetcher
from models import Job
from scoring import is_relevant, score_job
from utils import normalize_url, stable_id, utc_now_iso


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_existing() -> list[Job]:
    path = ROOT / "data" / "jobs.json"
    if not path.exists(): return []
    payload = load_json(path)
    jobs: list[Job] = []
    for item in payload.get("jobs", []):
        allowed = {field for field in Job.__dataclass_fields__}
        jobs.append(Job(**{key: value for key, value in item.items() if key in allowed}))
    return jobs


def canonical_key(job: Job) -> str:
    return stable_id(job.title, job.company, job.location)


def choose_better(a: Job, b: Job) -> Job:
    score_a = (bool(a.description), bool(a.posted_date), bool(a.closing_date), a.match_score, len(a.description))
    score_b = (bool(b.description), bool(b.posted_date), bool(b.closing_date), b.match_score, len(b.description))
    return b if score_b > score_a else a


def seed_fetchers(config: dict, profile: dict) -> list:
    fetchers = []
    if config["jobbank"].get("enabled"): fetchers.append(JobBankFetcher(config["jobbank"]))
    if config["civicjobs"].get("enabled"):
        fetchers.append(CivicJobsFetcher(config["civicjobs"]))
    if config.get("conservation_ontario", {}).get("enabled"):
        fetchers.append(ConservationOntarioFetcher(config["conservation_ontario"]))
    if config["career_pages"].get("enabled"):
        # One fetcher per employer gives transparent, independent source-health results.
        shared = config["career_pages"]
        for page in shared.get("pages", []):
            fetchers.append(CareerPagesFetcher({
                "name": f"Official career page · {page['name']}",
                "pages": [page],
                "detail_limit_per_page": shared.get("detail_limit_per_page", 50),
            }))
    if config["adzuna"].get("enabled"):
        fetchers.append(AdzunaFetcher(config["adzuna"], profile["include_terms"][:10]))
    ats_config = config.get("ats", {})
    configured_boards = sum(len(ats_config.get(key, [])) for key in ("greenhouse", "lever", "ashby", "smartrecruiters"))
    if ats_config.get("enabled") and configured_boards:
        fetchers.append(ATSFetcher(ats_config))
    return fetchers


def main() -> int:
    profile = load_json(ROOT / "config" / "profile.json")
    config = load_json(ROOT / "config" / "sources.json")
    generated_at = utc_now_iso()
    all_jobs: list[Job] = []
    health: list[dict[str, Any]] = []

    fetchers = seed_fetchers(config, profile)
    with ThreadPoolExecutor(max_workers=min(6, len(fetchers) or 1)) as pool:
        future_map = {pool.submit(fetcher.run): fetcher for fetcher in fetchers}
        for future in as_completed(future_map):
            result = future.result()
            if result.name.startswith("Adzuna") and result.error and "credentials not configured" in result.error:
                result.status = "degraded"
            relevant: list[Job] = []
            for job in result.jobs:
                job.url = normalize_url(job.url)
                job.fetched_at = generated_at
                if is_relevant(job, profile): relevant.append(score_job(job, profile))
            result.kept = len(relevant)
            if result.status == "ok" and result.fetched > 0 and result.kept == 0:
                result.status = "degraded"
                result.error = "source responded but no relevant jobs matched"
            all_jobs.extend(relevant)
            health.append({
                "name": result.name, "status": result.status, "fetched": result.fetched,
                "kept": result.kept, "error": result.error, "duration_seconds": result.duration_seconds,
            })

    # Preserve recently seen postings during temporary source outages.
    cutoff = date.today() - timedelta(days=int(os.getenv("MAX_JOB_AGE_DAYS", "45")))
    for old in load_existing():
        if old.closing_date and old.closing_date < date.today().isoformat():
            continue
        if old.posted_date and old.posted_date < cutoff.isoformat():
            continue
        all_jobs.append(old)

    deduped: dict[str, Job] = {}
    for job in all_jobs:
        key = canonical_key(job)
        deduped[key] = choose_better(deduped[key], job) if key in deduped else job

    jobs = sorted(deduped.values(), key=lambda job: (job.match_score, job.posted_date or ""), reverse=True)
    output = {
        "generated_at": generated_at,
        "profile": profile["name"],
        "count": len(jobs),
        "jobs": [job.as_dict() for job in jobs],
    }
    (ROOT / "data" / "jobs.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "data" / "source_health.json").write_text(json.dumps({"generated_at": generated_at, "sources": sorted(health, key=lambda x: x["name"])}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(jobs)} unique relevant jobs from {len(health)} source groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
from datetime import date
from typing import Any

from models import Job

CATEGORY_TERMS = {
    "GIS & Geospatial": ["gis", "geospatial", "spatial", "mapping", "geomatics", "cartograph", "arcgis", "qgis", "geodatabase"],
    "Environmental": ["environmental", "environment", "impact assessment", "remediation", "ecology", "water resources", "stormwater"],
    "Planning": ["planner", "planning", "land use", "zoning", "urban", "parks planning", "development review"],
    "Sustainability & Climate": ["sustainability", "climate", "decarbon", "net zero", "esg", "energy transition"],
    "Conservation & Natural Resources": ["conservation", "natural resources", "forestry", "wildlife", "watershed", "parks", "ecological"],
    "Data & Policy": ["data analyst", "policy", "research", "power bi", "data quality", "database", "asset management"],
}

SKILL_TERMS = [
    "ArcGIS Online", "ArcGIS Enterprise", "ArcGIS Pro", "ArcGIS", "Experience Builder", "StoryMaps",
    "QGIS", "ArcPy", "Python", "Power BI", "R", "FME", "SQL", "Geodatabase", "Adobe Creative Suite",
    "Spatial Analysis", "Data Validation", "Remote Sensing", "Drone", "Microsoft Excel", "Azure"
]


def _contains(text: str, term: str) -> bool:
    if len(term) <= 2:
        return bool(re.search(rf"\b{re.escape(term.lower())}\b", text))
    return term.lower() in text


def classify_region(location: str, profile: dict[str, Any], workplace: str | None = None) -> str:
    loc = location.lower()
    if workplace and "remote" in workplace.lower() and not any(city.lower() in loc for city in profile["gta_cities"]):
        return "Remote Canada"
    if "toronto" in loc or any(x in loc for x in ["north york", "scarborough", "etobicoke", "east york"]):
        return "Toronto"
    if any(city.lower() in loc for city in profile["gta_cities"]):
        return "GTA"
    if " on" in loc or "ontario" in loc:
        return "Ontario"
    return "Canada"


def score_job(job: Job, profile: dict[str, Any]) -> Job:
    text = " ".join([job.title, job.company, job.location, job.description]).lower()
    title = job.title.lower()
    score = 18
    reasons: list[str] = []

    matched_weighted: list[tuple[str, int]] = []
    for term, weight in profile["high_value_terms"].items():
        if _contains(text, term):
            matched_weighted.append((term, weight))
            score += weight
    matched_weighted.sort(key=lambda x: x[1], reverse=True)
    # Prevent keyword-dense postings from reaching 100 before location,
    # freshness and eligibility are considered.
    weighted_total = sum(weight for _, weight in matched_weighted)
    if weighted_total > 50:
        score -= weighted_total - 50
    reasons.extend([term.title() for term, _ in matched_weighted[:4]])

    categories = [category for category, terms in CATEGORY_TERMS.items() if any(_contains(text, term) for term in terms)]
    if not categories:
        categories = ["Data & Policy"]
    job.categories = categories

    skills = [skill for skill in SKILL_TERMS if _contains(text, skill)]
    job.skills = skills[:10]

    title_early_terms = ["new grad", "new graduate", "graduate", "entry level", "entry-level",
                         "junior", "technician", "technologist", "coordinator", "analyst", "assistant",
                         "associate"]
    experience_early_terms = ["0-2 years", "1-2 years", "experience an asset"]
    early_hits = [term for term in title_early_terms if _contains(title, term)]
    early_hits.extend(term for term in experience_early_terms if _contains(text, term))
    senior_title_terms = ["senior", "principal", "director", "manager", "lead", "supervisor"]
    senior_hits = [term for term in senior_title_terms if _contains(title, term)]
    experience_match = re.search(
        r"(?:minimum(?: of)?\s*)?(?P<years>[2-9]|one|two|three|four|five|six|seven|eight|nine)\+?\s+years?",
        text,
    )
    experience_words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                        "six": 6, "seven": 7, "eight": 8, "nine": 9}
    required_years = 0
    if experience_match:
        token = experience_match.group("years")
        required_years = int(token) if token.isdigit() else experience_words.get(token, 0)

    if early_hits:
        score += 15
        reasons.append("Early-career title")
    if required_years >= 3:
        score -= min(45, 10 + required_years * 7)
    if senior_hits:
        score -= min(45, 38 + 4 * (len(set(senior_hits)) - 1))

    blocked_title = any(term in title for term in senior_title_terms)
    job.new_grad_friendly = bool(early_hits) and not blocked_title and required_years <= 2
    if senior_hits or required_years >= 5:
        job.seniority = "Senior"
    elif required_years >= 3:
        job.seniority = f"Experienced ({required_years}+ years)"
    elif job.new_grad_friendly:
        job.seniority = "Early career"
    else:
        job.seniority = "Unspecified"

    job.region = classify_region(job.location, profile, job.workplace)
    if job.region == "Toronto":
        score += 14
        reasons.append("Toronto")
    elif job.region == "GTA":
        score += 11
        reasons.append("GTA")
    elif job.region == "Ontario":
        score += 5

    if job.posted_date:
        try:
            age = (date.today() - date.fromisoformat(job.posted_date)).days
            if age <= 3:
                score += 8
                reasons.append("Recently posted")
            elif age <= 14:
                score += 4
        except ValueError:
            pass

    score = max(0, min(100, score))
    job.match_score = score
    job.match_reasons = list(dict.fromkeys(reasons))[:5]
    return job


def is_relevant(job: Job, profile: dict[str, Any]) -> bool:
    text = " ".join([job.title, job.description]).lower()
    include = any(_contains(text, term) for term in profile["include_terms"])
    exclusion_hits = sum(1 for term in profile["exclude_terms"] if _contains(job.title.lower(), term))
    return include and exclusion_hits == 0

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from bs4 import BeautifulSoup

from fetchers.base import BaseFetcher
from models import Job
from utils import clean_text, normalize_url, parse_date, stable_id

JOB_LINK_PATTERN = re.compile(r"job|career|position|posting|vacanc", re.I)


class CareerPagesFetcher(BaseFetcher):
    def __init__(self, config: dict) -> None:
        super().__init__(config["name"])
        self.config = config

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        page_errors: list[str] = []
        for page in self.config["pages"]:
            try:
                response = self.session.get(page["url"], timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                for job in self._jsonld_jobs(soup, page["name"], response.url):
                    jobs[job.id] = job
                links = self._candidate_links(soup, response.url)[: int(self.config.get("detail_limit_per_page", 50))]
                for url, anchor_text in links:
                    try:
                        detail = self.session.get(url, timeout=self.timeout)
                        detail.raise_for_status()
                        detail_soup = BeautifulSoup(detail.text, "html.parser")
                        parsed = list(self._jsonld_jobs(detail_soup, page["name"], detail.url))
                        if parsed:
                            for job in parsed:
                                jobs[job.id] = job
                        else:
                            job = self._heuristic_job(detail_soup, page["name"], detail.url, anchor_text)
                            if job:
                                jobs[job.id] = job
                    except Exception:
                        continue
            except Exception as exc:
                page_errors.append(f"{page['name']}: {type(exc).__name__}: {exc}")

        if not jobs and page_errors:
            raise RuntimeError("; ".join(page_errors)[:500])
        return list(jobs.values())

    def _jsonld_jobs(self, soup: BeautifulSoup, default_company: str, base_url: str) -> Iterable[Job]:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue
            stack = payload if isinstance(payload, list) else [payload]
            while stack:
                item = stack.pop()
                if isinstance(item, dict) and "@graph" in item:
                    stack.extend(item["@graph"])
                    continue
                if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                    continue
                company = item.get("hiringOrganization", {})
                if isinstance(company, dict): company = company.get("name")
                location = self._jsonld_location(item)
                description = clean_text(item.get("description"))
                url = normalize_url(item.get("url") or base_url, base_url)
                yield Job(
                    id=stable_id("career", url, item.get("title", "")), title=clean_text(item.get("title")),
                    company=clean_text(company) or default_company, location=location, url=url,
                    source=f"Official career page · {default_company}", description=description[:1800],
                    posted_date=parse_date(item.get("datePosted")), closing_date=parse_date(item.get("validThrough")),
                    employment_type=clean_text(item.get("employmentType")) or None,
                )

    @staticmethod
    def _jsonld_location(item: dict) -> str:
        location = item.get("jobLocation")
        if isinstance(location, list): location = location[0] if location else {}
        if isinstance(location, dict):
            address = location.get("address", location)
            if isinstance(address, dict):
                parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
                return ", ".join(clean_text(p) for p in parts if p)
        return "Canada"

    @staticmethod
    def _candidate_links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
        links: list[tuple[str, str]] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            text = clean_text(anchor.get_text(" ", strip=True))
            href = anchor.get("href", "")
            url = normalize_url(href, base_url)
            if not url or url in seen or url.startswith("mailto:"):
                continue
            if JOB_LINK_PATTERN.search(text) or JOB_LINK_PATTERN.search(url):
                seen.add(url)
                links.append((url, text))
        return links

    @staticmethod
    def _heuristic_job(soup: BeautifulSoup, company: str, url: str, anchor_text: str) -> Job | None:
        text = clean_text(soup.get_text(" ", strip=True))
        title_node = soup.find("h1") or soup.find("h2")
        title = clean_text(title_node.get_text(" ", strip=True)) if title_node else anchor_text
        if not title or len(title) > 180 or len(text) < 120:
            return None
        posted = re.search(r"(?:Posting Period|Posted|Date Posted)[:\s]+(.{4,45}?)(?:\s+to\s+|\n|Closing|Job ID|$)", text, re.I)
        closing = re.search(r"(?:Closing Date|Posting Period).{0,60}?\bto\s+([A-Za-z0-9,\- ]{8,30})", text, re.I)
        location = "Ontario, Canada"
        loc_match = re.search(r"(?:Work Location|Location)[:\s]+(.{3,90}?)(?:Job Type|Salary|Posting|$)", text, re.I)
        if loc_match: location = clean_text(loc_match.group(1))
        salary_match = re.search(r"(?:Hourly Rate(?: and Wage Grade)?|Salary)[:\s]+(.{3,60}?)(?:Shift|Job Type|Posting|$)", text, re.I)
        return Job(
            id=stable_id("career", url), title=title, company=company, location=location,
            url=url, source=f"Official career page · {company}", description=text[:1800],
            posted_date=parse_date(posted.group(1) if posted else None),
            closing_date=parse_date(closing.group(1) if closing else None),
            salary=clean_text(salary_match.group(1)) if salary_match else None,
        )

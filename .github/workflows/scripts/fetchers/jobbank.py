from __future__ import annotations

import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from fetchers.base import BaseFetcher
from models import Job
from utils import clean_text, normalize_url, parse_date, stable_id


class JobBankFetcher(BaseFetcher):
    def __init__(self, config: dict) -> None:
        super().__init__(config["name"])
        self.config = config

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for query in self.config["queries"]:
            for location in self.config["locations"]:
                for page in range(1, int(self.config.get("pages_per_query", 2)) + 1):
                    params = {
                        "action": "s2", "searchstring": query, "locationstring": location,
                        "distance": self.config.get("distance_km", 100), "sort": "M", "page": page,
                    }
                    response = self.session.get(f'{self.config["base_url"]}?{urlencode(params)}', timeout=self.timeout)
                    response.raise_for_status()
                    for job in self._parse_search(response.text, response.url):
                        jobs[job.id] = job
        return list(jobs.values())

    def _parse_search(self, html: str, base_url: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        output: list[Job] = []
        seen: set[str] = set()
        links = soup.select('a[href*="/jobsearch/jobposting/"]')
        for link in links:
            url = normalize_url(link.get("href", ""), base_url)
            if not url or url in seen:
                continue
            seen.add(url)
            container = link.find_parent(["article", "li", "div"]) or link
            text = clean_text(container.get_text(" ", strip=True))
            title = clean_text(link.get_text(" ", strip=True))
            if not title or len(title) > 140 or title.lower().startswith("save to"):
                heading = container.find(["h2", "h3", "h4"])
                title = clean_text(heading.get_text(" ", strip=True)) if heading else title
            employer_match = re.search(r"(?:Employer details|by)\s+(.+?)(?:\s+Location|\s+Salary|\s+Posted|$)", text, re.I)
            location_match = re.search(r"Location\s+(.+?)(?:\s+Salary|\s+Work location|\s+Posted|$)", text, re.I)
            date_match = re.search(r"(?:Posted on\s+)?((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4})", text, re.I)
            salary_match = re.search(r"Salary\s+(.+?)(?:\s+Terms of employment|\s+Job Bank|$)", text, re.I)
            company = clean_text(employer_match.group(1)) if employer_match else "Employer listed on Job Bank"
            location = clean_text(location_match.group(1)) if location_match else "Ontario, Canada"
            output.append(Job(
                id=stable_id("jobbank", url), title=title or "Job Bank posting", company=company,
                location=location, url=url, source=self.name, description=text[:900],
                posted_date=parse_date(date_match.group(1) if date_match else None),
                salary=clean_text(salary_match.group(1)) if salary_match else None,
            ))
        return output

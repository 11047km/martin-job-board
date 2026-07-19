from __future__ import annotations

import os

from fetchers.base import BaseFetcher
from models import Job
from utils import clean_text, parse_date, stable_id


class AdzunaFetcher(BaseFetcher):
    def __init__(self, config: dict, queries: list[str]) -> None:
        super().__init__(config["name"])
        self.config = config
        self.queries = queries

    def fetch(self) -> list[Job]:
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            raise RuntimeError("optional credentials not configured")
        jobs: dict[str, Job] = {}
        for query in self.queries:
            for page in range(1, int(self.config.get("pages", 2)) + 1):
                url = f'https://api.adzuna.com/v1/api/jobs/{self.config.get("country", "ca")}/search/{page}'
                params = {
                    "app_id": app_id, "app_key": app_key, "results_per_page": self.config.get("results_per_page", 50),
                    "what": query, "where": "Greater Toronto Area", "distance": 100,
                    "content-type": "application/json", "sort_by": "date",
                }
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                for item in response.json().get("results", []):
                    title = clean_text(item.get("title"))
                    company = clean_text((item.get("company") or {}).get("display_name")) or "Employer"
                    location = clean_text((item.get("location") or {}).get("display_name")) or "Canada"
                    url_value = item.get("redirect_url", "")
                    job = Job(
                        id=stable_id("adzuna", str(item.get("id")), title, company), title=title, company=company,
                        location=location, url=url_value, source=self.name,
                        description=clean_text(item.get("description"))[:1400], posted_date=parse_date(item.get("created")),
                        salary=self._salary(item), employment_type=clean_text(item.get("contract_type")) or None,
                    )
                    jobs[job.id] = job
        return list(jobs.values())

    @staticmethod
    def _salary(item: dict) -> str | None:
        low, high = item.get("salary_min"), item.get("salary_max")
        if low and high: return f"${low:,.0f}–${high:,.0f}"
        if low: return f"From ${low:,.0f}"
        return None

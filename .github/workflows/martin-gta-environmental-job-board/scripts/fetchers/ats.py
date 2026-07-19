from __future__ import annotations

from fetchers.base import BaseFetcher
from models import Job
from utils import clean_text, parse_date, stable_id


class ATSFetcher(BaseFetcher):
    def __init__(self, config: dict) -> None:
        super().__init__(config["name"])
        self.config = config

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for board in self.config.get("greenhouse", []):
            url = f'https://boards-api.greenhouse.io/v1/boards/{board["token"]}/jobs?content=true'
            response = self.session.get(url, timeout=self.timeout); response.raise_for_status()
            for item in response.json().get("jobs", []):
                location = clean_text((item.get("location") or {}).get("name"))
                job = Job(stable_id("gh", str(item.get("id"))), clean_text(item.get("title")), board["company"], location,
                          item.get("absolute_url", ""), f'Greenhouse · {board["company"]}', clean_text(item.get("content"))[:1600],
                          parse_date(item.get("updated_at")))
                jobs[job.id] = job
        for board in self.config.get("lever", []):
            url = f'https://api.lever.co/v0/postings/{board["site"]}?mode=json'
            response = self.session.get(url, timeout=self.timeout); response.raise_for_status()
            for item in response.json():
                categories = item.get("categories") or {}
                job = Job(stable_id("lever", item.get("id", "")), clean_text(item.get("text")), board["company"],
                          clean_text(categories.get("location")) or "Canada", item.get("hostedUrl", ""),
                          f'Lever · {board["company"]}', clean_text(item.get("descriptionPlain"))[:1600],
                          employment_type=clean_text(categories.get("commitment")) or None)
                jobs[job.id] = job
        for board in self.config.get("ashby", []):
            url = f'https://api.ashbyhq.com/posting-api/job-board/{board["board"]}'
            response = self.session.get(url, params={"includeCompensation": "true"}, timeout=self.timeout); response.raise_for_status()
            for item in response.json().get("jobs", []):
                job = Job(stable_id("ashby", item.get("id", "")), clean_text(item.get("title")), board["company"],
                          clean_text(item.get("location")) or "Canada", item.get("jobUrl", ""),
                          f'Ashby · {board["company"]}', clean_text(item.get("descriptionPlain"))[:1600],
                          parse_date(item.get("publishedAt")), employment_type=clean_text(item.get("employmentType")) or None,
                          workplace=clean_text(item.get("workplaceType")) or None)
                jobs[job.id] = job
        for board in self.config.get("smartrecruiters", []):
            url = f'https://api.smartrecruiters.com/v1/companies/{board["identifier"]}/postings'
            response = self.session.get(url, params={"limit": 100}, timeout=self.timeout); response.raise_for_status()
            for item in response.json().get("content", []):
                loc = item.get("location") or {}
                location = ", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country")]))
                job = Job(stable_id("sr", item.get("id", "")), clean_text(item.get("name")), board["company"], location,
                          item.get("ref", ""), f'SmartRecruiters · {board["company"]}', posted_date=parse_date(item.get("releasedDate")))
                jobs[job.id] = job
        return list(jobs.values())

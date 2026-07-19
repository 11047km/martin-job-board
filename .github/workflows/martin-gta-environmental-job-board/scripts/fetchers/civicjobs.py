from __future__ import annotations

import feedparser

from fetchers.base import BaseFetcher
from models import Job
from utils import clean_text, normalize_url, parse_date, stable_id


class CivicJobsFetcher(BaseFetcher):
    def __init__(self, config: dict) -> None:
        super().__init__(config["name"])
        self.config = config

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for feed_url in self.config["feeds"]:
            response = self.session.get(feed_url, timeout=self.timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                title = clean_text(entry.get("title"))
                url = normalize_url(entry.get("link", ""), feed_url)
                summary = clean_text(entry.get("summary") or entry.get("description"))
                author = clean_text(entry.get("author")) or "Municipal employer"
                location = self._location(entry, summary)
                job = Job(
                    id=stable_id("civicjobs", url or title, author), title=title, company=author,
                    location=location, url=url, source=self.name, description=summary[:1200],
                    posted_date=parse_date(entry.get("published") or entry.get("updated")),
                )
                jobs[job.id] = job
        return list(jobs.values())

    @staticmethod
    def _location(entry: dict, summary: str) -> str:
        for key in ("location", "job_location", "where"):
            if entry.get(key):
                return clean_text(entry[key])
        if " ON" in summary or "Ontario" in summary:
            return "Ontario, Canada"
        return "Canada"

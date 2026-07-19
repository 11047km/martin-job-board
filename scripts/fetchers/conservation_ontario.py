from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from fetchers.base import BaseFetcher
from models import Job
from utils import clean_text, normalize_url, parse_date, stable_id


class ConservationOntarioFetcher(BaseFetcher):
    """Parse Conservation Ontario's structured province-wide careers table."""

    def __init__(self, config: dict) -> None:
        super().__init__(config["name"])
        self.url = config["url"]

    def fetch(self) -> list[Job]:
        response = self.session.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        return self.parse_html(response.text, response.url)

    @staticmethod
    def parse_html(html: str, base_url: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[Job] = []

        # The live page uses a conventional table. Keep a fallback for CMS layouts
        # that render rows with role=\"row\" instead of literal <tr> elements.
        rows = list(soup.select("table tr")) or list(soup.select('[role="row"]'))
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=True)
            if len(cells) < 7:
                continue

            values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells[:7]]
            posted_raw, title, _number, organization, job_type, city, deadline_raw = values
            if title.lower() in {"position title", "title"} or not title:
                continue

            link: Tag | None = cells[1].find("a", href=True)
            url = normalize_url(link.get("href") if link else base_url, base_url)
            posted_date = parse_date(posted_raw)
            closing_date = parse_date(deadline_raw)
            description = (
                f"{job_type} opportunity with {organization} in {city}, Ontario. "
                "Listed on Conservation Ontario's current employment opportunities page."
            )
            jobs.append(Job(
                id=stable_id("conservation-ontario", organization, title, city, url),
                title=title,
                company=organization or "Ontario Conservation Authority",
                location=f"{city}, ON" if city else "Ontario, Canada",
                url=url,
                source="Conservation Ontario careers",
                description=description,
                posted_date=posted_date,
                closing_date=closing_date,
                employment_type=job_type or None,
                province="ON",
                country="Canada",
            ))

        # If the table changed, fail loudly enough for source-health diagnostics.
        if not jobs:
            raise ValueError("No structured career rows found; page layout may have changed")
        return jobs

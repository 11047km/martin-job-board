from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import requests

from models import Job


@dataclass
class SourceResult:
    name: str
    jobs: list[Job] = field(default_factory=list)
    fetched: int = 0
    kept: int = 0
    status: str = "ok"
    error: str | None = None
    duration_seconds: float = 0.0


class BaseFetcher:
    def __init__(self, name: str, timeout: int = 25) -> None:
        self.name = name
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Martin-GTA-Environmental-Job-Board/1.0 (+GitHub Pages; respectful daily refresh)",
            "Accept-Language": "en-CA,en;q=0.9",
        })

    def run(self) -> SourceResult:
        started = perf_counter()
        result = SourceResult(name=self.name)
        try:
            result.jobs = self.fetch()
            result.fetched = len(result.jobs)
        except Exception as exc:  # source isolation is deliberate
            result.status = "failed"
            result.error = f"{type(exc).__name__}: {exc}"[:240]
        result.duration_seconds = round(perf_counter() - started, 2)
        return result

    def fetch(self) -> list[Job]:
        raise NotImplementedError

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    posted_date: str | None = None
    closing_date: str | None = None
    salary: str | None = None
    employment_type: str | None = None
    workplace: str | None = None
    region: str = "Canada"
    province: str = "ON"
    country: str = "Canada"
    categories: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    match_score: int = 0
    match_reasons: list[str] = field(default_factory=list)
    new_grad_friendly: bool = False
    seniority: str = "Unspecified"
    fetched_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("metadata", None)
        return data

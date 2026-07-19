from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class DataTests(unittest.TestCase):
    def test_jobs_json_is_valid(self):
        payload = json.loads((ROOT / "data" / "jobs.json").read_text())
        self.assertIsInstance(payload["jobs"], list)
        ids = [job["id"] for job in payload["jobs"]]
        self.assertEqual(len(ids), len(set(ids)))
        for job in payload["jobs"]:
            for field in ["id", "title", "company", "location", "url", "source", "match_score"]:
                self.assertIn(field, job)
            self.assertIn(urlparse(job["url"]).scheme, {"http", "https"})
            self.assertGreaterEqual(job["match_score"], 0)
            self.assertLessEqual(job["match_score"], 100)

    def test_source_health_is_valid(self):
        payload = json.loads((ROOT / "data" / "source_health.json").read_text())
        self.assertIn("sources", payload)
        for source in payload["sources"]:
            self.assertIn(source["status"], {"ok", "pending", "degraded", "failed"})


if __name__ == "__main__":
    unittest.main()

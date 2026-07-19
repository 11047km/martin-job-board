from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from models import Job
from scoring import is_relevant, score_job


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads((ROOT / "config" / "profile.json").read_text())

    def test_gis_toronto_role_scores_high(self):
        job = Job("1", "Junior GIS Analyst", "City", "Toronto, ON", "https://example.com/1", "test",
                  "ArcGIS Online geodatabase spatial analysis data validation and StoryMaps")
        scored = score_job(job, self.profile)
        self.assertGreaterEqual(scored.match_score, 70)
        self.assertTrue(scored.new_grad_friendly)
        self.assertEqual(scored.region, "Toronto")

    def test_senior_role_is_penalized(self):
        junior = Job("1", "GIS Analyst", "City", "Toronto, ON", "https://example.com/1", "test", "ArcGIS geospatial")
        senior = Job("2", "Senior GIS Manager", "City", "Toronto, ON", "https://example.com/2", "test", "ArcGIS geospatial 8+ years")
        self.assertGreater(score_job(junior, self.profile).match_score, score_job(senior, self.profile).match_score)


    def test_three_year_requirement_is_not_new_grad_friendly(self):
        job = Job("4", "Resource Planner", "Authority", "Cambridge, ON", "https://example.com/4", "test",
                  "Degree in Geography or Environmental Science. Minimum three years related work experience. GIS mapping.")
        scored = score_job(job, self.profile)
        self.assertFalse(scored.new_grad_friendly)
        self.assertEqual(scored.seniority, "Experienced (3+ years)")

    def test_irrelevant_role_is_filtered(self):
        job = Job("3", "Restaurant Manager", "Food Co", "Toronto, ON", "https://example.com/3", "test", "customer service")
        self.assertFalse(is_relevant(job, self.profile))


if __name__ == "__main__":
    unittest.main()

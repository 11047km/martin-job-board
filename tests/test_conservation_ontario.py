from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetchers.conservation_ontario import ConservationOntarioFetcher


class ConservationOntarioTests(unittest.TestCase):
    def test_parses_structured_career_table(self):
        html = """
        <table>
          <tr><th>Date Posted</th><th>Position Title</th><th>Number</th><th>Organization</th><th>Job Type</th><th>City</th><th>Deadline</th></tr>
          <tr><td>2026-07-17</td><td><a href="/jobs/resource-planner.pdf">Resource Planner</a></td><td>1</td><td>Grand River Conservation Authority</td><td>Full-Time</td><td>Cambridge</td><td>2026-07-29</td></tr>
        </table>
        """
        jobs = ConservationOntarioFetcher.parse_html(html, "https://conservationontario.ca/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Resource Planner")
        self.assertEqual(jobs[0].company, "Grand River Conservation Authority")
        self.assertEqual(jobs[0].location, "Cambridge, ON")
        self.assertEqual(jobs[0].closing_date, "2026-07-29")
        self.assertEqual(jobs[0].url, "https://conservationontario.ca/jobs/resource-planner.pdf")


if __name__ == "__main__":
    unittest.main()

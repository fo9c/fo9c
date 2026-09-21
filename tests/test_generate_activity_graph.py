import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_activity_graph.py"
SPEC = importlib.util.spec_from_file_location("activity_graph", SCRIPT)
activity_graph = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = activity_graph
SPEC.loader.exec_module(activity_graph)


class ActivityGraphTests(unittest.TestCase):
    def sample_payload(self):
        start = date(2026, 8, 1)
        contribution_days = [
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "contributionCount": index % 9,
            }
            for index in range(40)
        ]
        return {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "contributionCalendar": {
                            "totalContributions": sum(
                                item["contributionCount"] for item in contribution_days
                            ),
                            "weeks": [{"contributionDays": contribution_days}],
                        }
                    }
                }
            }
        }

    def test_renders_last_31_days_as_valid_svg(self):
        contributions, total = activity_graph.parse_contributions(
            self.sample_payload(), 31
        )
        svg = activity_graph.render_svg("fo9c", contributions, total)
        root = ET.fromstring(svg)

        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(len(contributions), 31)
        self.assertEqual(contributions[0].day.isoformat(), "2026-08-10")
        self.assertIn("activity-fill", svg)
        self.assertNotIn("nan", svg.lower())

    def test_atomic_write_preserves_complete_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "assets" / "activity-graph.svg"
            activity_graph.atomic_write(output, "<svg />")
            self.assertEqual(output.read_text(encoding="utf-8"), "<svg />")
            self.assertFalse(output.with_suffix(".svg.tmp").exists())


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from we_si.app import create_app


class WebDashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"DATABASE_URL": "sqlite:///:memory:", "TESTING": True})
        self.client = self.app.test_client()

    def test_home_uses_modern_template_with_plan_usage(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Analyze Now", body)
        self.assertIn("plan:", body)
        self.assertIn("remaining this month", body)

    def test_api_analyze_respects_max_depth_from_payload(self):
        with patch("we_si.app._create_analysis_record") as create_record, patch("we_si.app._start_analysis_job") as start_job:
            create_record.return_value = {
                "analysis": SimpleNamespace(id=123),
                "user": SimpleNamespace(id=1),
            }
            start_job.return_value = "job-1"

            response = self.client.post(
                "/api/analyze",
                json={"url": "https://example.com", "max_pages": 20, "max_depth": 4},
            )

            self.assertEqual(response.status_code, 202)
            create_record.assert_called_once_with("https://example.com", 20, 4)
            start_job.assert_called_once()


if __name__ == "__main__":
    unittest.main()

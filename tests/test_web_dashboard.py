import unittest
from types import SimpleNamespace
from unittest.mock import patch

from we_si.app import create_app, get_or_create_demo_user
from we_si.models import JobStatus, PageAnalysis, SiteAnalysis


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
            create_record.assert_called_once_with("https://example.com", 20, 4, focus_url=None)
            start_job.assert_called_once()

    def test_api_analyze_accepts_optional_focus_url(self):
        with patch("we_si.app._create_analysis_record") as create_record, patch("we_si.app._start_analysis_job") as start_job:
            create_record.return_value = {
                "analysis": SimpleNamespace(id=124),
                "user": SimpleNamespace(id=1),
            }
            start_job.return_value = "job-2"

            response = self.client.post(
                "/api/analyze",
                json={"url": "https://example.com", "focus_url": "https://example.com/pricing"},
            )

            self.assertEqual(response.status_code, 202)
            create_record.assert_called_once_with("https://example.com", 50, 3, focus_url="https://example.com/pricing")

    def test_api_store_key_requires_service_and_api_key(self):
        response = self.client.post("/api/settings/api-key", json={"service": "", "api_key": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("service is required", response.get_json()["error"])

        response = self.client.post("/api/settings/api-key", json={"service": "openai", "api_key": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("api_key is required", response.get_json()["error"])

    def test_api_store_key_passes_trimmed_values(self):
        with patch("we_si.app._store_api_key_for_demo_user") as store_key:
            store_key.return_value = {"success": True, "service": "openai", "storage_mode": "plaintext-session"}
            response = self.client.post("/api/settings/api-key", json={"service": " openai ", "api_key": " sk-test "})
            self.assertEqual(response.status_code, 201)
            store_key.assert_called_once_with("openai", "sk-test")

    def test_api_analysis_pages_returns_serialized_pages(self):
        with self.app.app_context():
            db = self.app.extensions["db_session_factory"]()
            try:
                user = get_or_create_demo_user(db)
                analysis = SiteAnalysis(
                    user_id=user.id,
                    base_url="https://example.com",
                    domain="example.com",
                    status=JobStatus.COMPLETED,
                    progress=100.0,
                    pages_crawled=1,
                    pages_analyzed=1,
                    summary={},
                    insights={},
                )
                db.add(analysis)
                db.flush()
                db.add(
                    PageAnalysis(
                        site_analysis_id=analysis.id,
                        url="https://example.com",
                        status_code=200,
                        depth=0,
                        load_time=0.1,
                        analysis_data={"title": "Home"},
                    )
                )
                db.commit()
                analysis_id = analysis.id
            finally:
                db.close()

        response = self.client.get(f"/api/analysis/{analysis_id}/pages")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["analysis_id"], analysis_id)
        self.assertEqual(payload["total_pages"], 1)
        self.assertEqual(payload["pages"][0]["url"], "https://example.com")

    def test_api_settings_provider_round_trip(self):
        response = self.client.post("/api/settings/provider", json={"ai_provider": "openai"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ai_provider"], "openai")

        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ai_provider"], "openai")


if __name__ == "__main__":
    unittest.main()

import unittest

from we_si.recommendations import RecommendationEngine


class FakeAIProvider:
    def generate_text(self, prompt):
        if "meta description" in prompt.lower():
            return "Helpful kitchen remodeling guidance for homeowners. Contact us today. Learn more at example.com. Trusted guidance for visitors and search engines."
        return "Kitchen Remodeling - Example | Austin"


class RecommendationEngineTests(unittest.TestCase):
    def test_generates_page_and_sitewide_recommendations(self):
        engine = RecommendationEngine()
        pages = [
            {
                "url": "http://example.com/services/kitchen-remodeling",
                "seo": {
                    "title": "",
                    "meta_description": "",
                    "word_count": 120,
                    "keyword_density": {"kitchen": 4.5},
                    "all_meta_tags": {},
                },
                "headings": {"hierarchy": {"h1": []}, "h1_count": 0},
                "images": {"missing_alt": [{"src": "/images/img001.jpg", "absolute_src": "http://example.com/images/img001.jpg", "has_alt": False}]},
                "links": {"internal": [{"text": "click here", "href": "/contact", "absolute_url": "http://example.com/contact"}], "external": []},
                "broken_links": [{"url": "http://example.com/old-page", "status_code": 404, "text": "Old Page"}],
                "content": "Kitchen remodeling helps homeowners improve storage and flow. Kitchen remodeling plans should match budget. Kitchen remodeling ideas should improve function.",
            }
        ]
        scoring_result = {"overall_score": 18, "has_robots_txt": False, "has_sitemap": False}
        site_meta = {"base_url": "http://example.com", "domain": "example.com", "site_name": "Example", "location": "Austin", "https_enabled": False}

        recommendations = engine.generate(pages, scoring_result, site_meta)
        elements = {item["element"] for item in recommendations}

        self.assertIn("title tag", elements)
        self.assertIn("meta description", elements)
        self.assertIn("H1", elements)
        self.assertIn("image alt", elements)
        self.assertIn("anchor text", elements)
        self.assertIn("viewport meta", elements)
        self.assertIn("HTTPS", elements)
        self.assertIn("robots.txt", elements)
        self.assertIn("XML sitemap", elements)

        title_rec = next(item for item in recommendations if item["element"] == "title tag")
        self.assertEqual(title_rec["severity"], "Critical")
        self.assertIn("<title>", title_rec["exact_fix"])
        self.assertIn("wordpress", title_rec["platform_steps"])

        alt_rec = next(item for item in recommendations if item["element"] == "image alt")
        self.assertIn('alt="', alt_rec["exact_fix"])

    def test_deduplicates_identical_page_issues(self):
        engine = RecommendationEngine()
        pages = [
            {
                "url": "https://example.com/about",
                "seo": {"title": "About Example", "meta_description": "A" * 155, "word_count": 350, "keyword_density": {}, "all_meta_tags": {"viewport": "width=device-width, initial-scale=1"}},
                "headings": {"hierarchy": {"h1": [{"text": "About Example"}, {"text": "Second H1"}]}, "h1_count": 2},
                "images": {"missing_alt": []},
                "links": {"internal": [], "external": []},
            },
            {
                "url": "https://example.com/contact",
                "seo": {"title": "Contact Example", "meta_description": "B" * 155, "word_count": 350, "keyword_density": {}, "all_meta_tags": {"viewport": "width=device-width, initial-scale=1"}},
                "headings": {"hierarchy": {"h1": [{"text": "Contact Example"}, {"text": "Second H1"}]}, "h1_count": 2},
                "images": {"missing_alt": []},
                "links": {"internal": [], "external": []},
            },
        ]

        recommendations = engine.generate(pages, {}, {"domain": "example.com"})
        h1_rec = next(item for item in recommendations if item["element"] == "H1")
        self.assertIsInstance(h1_rec["page_url"], list)
        self.assertEqual(len(h1_rec["page_url"]), 2)

    def test_uses_ai_provider_when_available(self):
        engine = RecommendationEngine(ai_provider=FakeAIProvider())
        page = {
            "url": "https://example.com/kitchen-remodeling",
            "seo": {"title": "", "meta_description": "", "word_count": 500, "keyword_density": {}, "all_meta_tags": {"viewport": "width=device-width, initial-scale=1"}},
            "headings": {"hierarchy": {"h1": [{"text": "Kitchen Remodeling"}]}, "h1_count": 1},
            "images": {"missing_alt": []},
            "links": {"internal": [], "external": []},
            "content": "We help homeowners plan kitchen remodeling projects with practical timelines and budgets.",
        }

        recommendations = engine.generate([page], {}, {"domain": "example.com", "site_name": "Example", "location": "Austin"})
        title_rec = next(item for item in recommendations if item["element"] == "title tag")
        meta_rec = next(item for item in recommendations if item["element"] == "meta description")

        self.assertIn("Kitchen Remodeling - Example | Austin", title_rec["exact_fix"])
        self.assertIn("Helpful kitchen remodeling guidance", meta_rec["exact_fix"])


if __name__ == "__main__":
    unittest.main()

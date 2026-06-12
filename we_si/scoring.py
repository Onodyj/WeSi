"""SiteIQ Score™ scoring engine."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter, defaultdict, deque
from statistics import mean
from typing import Any, Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PILLAR_WEIGHTS = {
    "on_page_seo": 0.25,
    "content_quality": 0.20,
    "technical_seo": 0.20,
    "authority": 0.15,
    "ux_design": 0.10,
    "links_architecture": 0.10,
}

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should", "could",
    "may", "might", "must", "can", "this", "that", "these", "those", "it", "its",
    "their", "there", "your", "our", "about", "into", "than", "then", "them", "they",
    "you", "we", "he", "she", "his", "her", "him", "who", "what", "when", "where",
    "why", "how", "also", "not", "too", "very", "more", "most", "such", "all", "any",
}
BAD_ANCHOR_TEXTS = {"click here", "here", "read more", "learn more", "more", ""}
FILENAME_ALT_RE = re.compile(r"^[\w\-]+\.(?:jpg|jpeg|png|gif|svg|webp|avif)$", re.IGNORECASE)
INLINE_COLOR_RE = re.compile(r"style\s*=\s*[\"'][^\"']*(?:color\s*:|background(?:-color)?\s*:)", re.IGNORECASE)
SENTENCE_RE = re.compile(r"[.!?]+")
WORD_RE = re.compile(r"\b[a-z0-9']+\b", re.IGNORECASE)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a numeric value into a range."""
    return max(minimum, min(maximum, value))


def score_to_grade(score: float) -> str:
    """Convert a numeric score into a letter grade."""
    score = clamp(score)
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def score_to_label(score: float) -> str:
    """Convert a numeric score into a health label."""
    score = clamp(score)
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Good"
    if score >= 70:
        return "Fair"
    if score >= 60:
        return "Needs Work"
    return "Critical"


class SiteIQScorer:
    """Compute SiteIQ pillar scores for one page or an entire site."""

    def score_site(self, pages: list[dict], site_meta: dict | None = None) -> dict:
        """Score a site from multiple page analysis payloads."""
        site_meta = dict(site_meta or {})
        pages = [page for page in pages if isinstance(page, dict)]
        logger.info("Scoring site with %s page(s)", len(pages))

        duplicate_counts = self._compute_duplicate_counts(pages)
        page_scores: dict[str, dict[str, Any]] = {}
        on_page_scores = []
        content_scores = []
        ux_scores = []
        tech_page_scores = []
        links_page_scores = []

        authority_result = self._score_authority(site_meta.get("authority_data"))
        site_links_result = self._score_site_links_architecture(pages, site_meta)
        site_technical_result = self._score_site_technical_seo(pages, site_meta)

        for page in pages:
            url = page.get("url") or f"page_{len(page_scores) + 1}"
            page_result = self._score_single_page(page, site_meta, duplicate_counts)
            page_result["authority"] = authority_result.copy()

            page_links_result = self._score_page_links_architecture(page)
            page_tech_result = self._score_page_technical_seo(page, site_meta)
            page_result["links_architecture"] = page_links_result
            page_result["technical_seo"] = page_tech_result

            overall_score = self._weighted_score({
                "on_page_seo": page_result["on_page_seo"]["score"],
                "content_quality": page_result["content_quality"]["score"],
                "technical_seo": page_tech_result["score"],
                "authority": authority_result["score"],
                "ux_design": page_result["ux_design"]["score"],
                "links_architecture": page_links_result["score"],
            })

            page_scores[url] = {
                "overall": overall_score,
                "grade": score_to_grade(overall_score),
                "label": score_to_label(overall_score),
                "on_page_seo": page_result["on_page_seo"],
                "content_quality": page_result["content_quality"],
                "technical_seo": page_tech_result,
                "authority": authority_result.copy(),
                "ux_design": page_result["ux_design"],
                "links_architecture": page_links_result,
            }

            on_page_scores.append(page_result["on_page_seo"]["score"])
            content_scores.append(page_result["content_quality"]["score"])
            ux_scores.append(page_result["ux_design"]["score"])
            tech_page_scores.append(page_tech_result["score"])
            links_page_scores.append(page_links_result["score"])

        pillar_results = {
            "on_page_seo": self._aggregate_pillar(
                "on_page_seo", [page_scores[url]["on_page_seo"] for url in page_scores]
            ),
            "content_quality": self._aggregate_pillar(
                "content_quality", [page_scores[url]["content_quality"] for url in page_scores]
            ),
            "technical_seo": self._merge_site_and_page_pillars(site_technical_result, tech_page_scores),
            "authority": authority_result,
            "ux_design": self._aggregate_pillar(
                "ux_design", [page_scores[url]["ux_design"] for url in page_scores]
            ),
            "links_architecture": self._merge_site_and_page_pillars(site_links_result, links_page_scores),
        }

        overall_score = self._weighted_score({name: data["score"] for name, data in pillar_results.items()})
        result = {
            "overall": {
                "score": overall_score,
                "grade": score_to_grade(overall_score),
                "label": score_to_label(overall_score),
            },
            "pillars": pillar_results,
            "page_scores": page_scores,
            "pillar_weights": dict(PILLAR_WEIGHTS),
        }
        logger.info("Finished site scoring: overall=%s grade=%s", overall_score, result["overall"]["grade"])
        return result

    def score_page(self, page_data: dict, site_meta: dict | None = None) -> dict:
        """Score a single page with page-level heuristics."""
        site_meta = dict(site_meta or {})
        page_data = page_data or {}
        logger.info("Scoring single page %s", page_data.get("url", "<unknown>"))

        duplicate_counts = self._compute_duplicate_counts([page_data])
        page_result = self._score_single_page(page_data, site_meta, duplicate_counts)
        technical = self._score_page_technical_seo(page_data, site_meta)
        authority = self._score_authority(site_meta.get("authority_data"))
        links = self._score_page_links_architecture(page_data)

        overall_score = self._weighted_score({
            "on_page_seo": page_result["on_page_seo"]["score"],
            "content_quality": page_result["content_quality"]["score"],
            "technical_seo": technical["score"],
            "authority": authority["score"],
            "ux_design": page_result["ux_design"]["score"],
            "links_architecture": links["score"],
        })
        return {
            "overall": {
                "score": overall_score,
                "grade": score_to_grade(overall_score),
                "label": score_to_label(overall_score),
            },
            "pillars": {
                "on_page_seo": page_result["on_page_seo"],
                "content_quality": page_result["content_quality"],
                "technical_seo": technical,
                "authority": authority,
                "ux_design": page_result["ux_design"],
                "links_architecture": links,
            },
            "pillar_weights": dict(PILLAR_WEIGHTS),
        }

    def _score_single_page(self, page_data: dict, site_meta: dict, duplicate_counts: dict[str, int]) -> dict:
        return {
            "on_page_seo": self._score_on_page_seo(page_data, site_meta),
            "content_quality": self._score_content_quality(page_data, duplicate_counts),
            "ux_design": self._score_ux_design(page_data),
        }

    def _score_on_page_seo(self, page_data: dict, site_meta: dict) -> dict:
        seo = page_data.get("seo", {}) or {}
        headings = page_data.get("headings", {}) or {}
        issues: list[str] = []
        passed: list[str] = []
        score = 0.0
        max_score = 85.0

        primary_keyword = self._primary_keyword(page_data, site_meta)
        title = (seo.get("title") or "").strip()
        description = (seo.get("meta_description") or "").strip()
        h1s = headings.get("hierarchy", {}).get("h1", []) or []
        h1_text = " ".join(item.get("text", "") for item in h1s).strip()

        if title:
            score += 10
            passed.append("Title tag is present")
        else:
            issues.append("Missing title tag")

        if 50 <= len(title) <= 60:
            score += 5
            passed.append("Title length is within the optimal 50-60 character range")
        elif title:
            issues.append(f"Title length is {len(title)} characters; target 50-60")

        if primary_keyword and self._contains_term(title, primary_keyword):
            score += 5
            passed.append(f"Title includes the primary keyword '{primary_keyword}'")
        elif primary_keyword:
            issues.append("Title does not include the primary keyword")

        if description:
            score += 10
            passed.append("Meta description is present")
        else:
            issues.append("Missing meta description")

        if 120 <= len(description) <= 160:
            score += 5
            passed.append("Meta description length is within the optimal 120-160 character range")
        elif description:
            issues.append(f"Meta description length is {len(description)} characters; target 120-160")

        if primary_keyword and self._contains_term(description, primary_keyword):
            score += 5
            passed.append("Meta description includes the primary keyword")
        elif primary_keyword:
            issues.append("Meta description does not include the primary keyword")

        h1_count = headings.get("h1_count", len(h1s))
        if h1_count >= 1:
            score += 10
            passed.append("At least one H1 heading is present")
        else:
            issues.append("Missing H1 heading")

        if h1_count == 1:
            score += 5
            passed.append("Page uses a single H1 heading")
        elif h1_count > 1:
            issues.append(f"Page has {h1_count} H1 headings; use only one")

        if primary_keyword and self._contains_term(h1_text, primary_keyword):
            score += 5
            passed.append("H1 includes the primary keyword")
        elif primary_keyword:
            issues.append("H1 does not include the primary keyword")

        if self._valid_heading_hierarchy(headings):
            score += 10
            passed.append("Heading hierarchy does not skip levels")
        else:
            issues.append("Heading hierarchy appears to skip levels")

        if seo.get("canonical_url"):
            score += 5
            passed.append("Canonical tag is present")
        else:
            issues.append("Canonical tag is missing")

        if page_data.get("structured_data"):
            score += 5
            passed.append("Structured data / JSON-LD is present")
        else:
            issues.append("Structured data / JSON-LD not detected")

        open_graph = seo.get("open_graph", {}) or {}
        if all(open_graph.get(key) for key in ("title", "description", "image")):
            score += 5
            passed.append("Open Graph title, description, and image are present")
        else:
            issues.append("Open Graph tags are incomplete")

        twitter = seo.get("twitter_card", {}) or {}
        if twitter.get("card") or twitter:
            score += 5
            passed.append("Twitter card metadata is present")
        else:
            issues.append("Twitter card metadata is missing")

        max_density = max((float(value) for value in (seo.get("keyword_density") or {}).values()), default=0.0)
        if max_density <= 3.0:
            score += 5
            passed.append("Keyword density does not indicate stuffing")
        else:
            issues.append(f"Keyword density peaks at {max_density:.2f}%, which suggests stuffing")

        return self._pillar_result(score, max_score, issues, passed)

    def _score_content_quality(self, page_data: dict, duplicate_counts: dict[str, int]) -> dict:
        seo = page_data.get("seo", {}) or {}
        issues: list[str] = []
        passed: list[str] = []
        score = 0.0
        max_score = 75.0

        word_count = int(seo.get("word_count") or 0)
        page_text = self._collect_page_text(page_data)

        if word_count >= 300:
            score += 15
            passed.append("Content meets the 300-word minimum")
        else:
            score -= 15
            issues.append(f"Thin content detected: {word_count} words")

        if word_count >= 600:
            score += 10
            passed.append("Content exceeds 600 words")
        if word_count >= 1200:
            score += 5
            passed.append("Content exceeds 1,200 words")

        readability = self._flesch_reading_ease(page_text)
        if 70 <= readability <= 80:
            score += 20
            passed.append(f"Readability is very good (Flesch {readability:.1f})")
        elif 60 <= readability < 70:
            score += 15
            passed.append(f"Readability is good (Flesch {readability:.1f})")
        elif 40 <= readability < 60:
            score += 10
            passed.append(f"Readability is fair (Flesch {readability:.1f})")
        else:
            issues.append(f"Readability is outside the preferred range (Flesch {readability:.1f})")

        density_map = seo.get("keyword_density") or {}
        primary_keyword = self._primary_keyword(page_data, {})
        keyword_density = float(density_map.get(primary_keyword, 0.0)) if primary_keyword else 0.0
        if primary_keyword and 0.5 <= keyword_density <= 3.0:
            score += 10
            passed.append(f"Primary keyword density is balanced at {keyword_density:.2f}%")
        else:
            score -= 10
            if primary_keyword:
                issues.append(f"Primary keyword density is {keyword_density:.2f}% for '{primary_keyword}'")
            else:
                issues.append("Primary keyword density could not be validated")

        long_tail_phrases = self._extract_long_tail_phrases(page_text)
        if long_tail_phrases:
            score += 10
            passed.append(f"Long-tail opportunities found: {', '.join(long_tail_phrases[:3])}")
        else:
            issues.append("No repeated 2-4 word long-tail phrases were detected")

        content_hash = self._content_hash(page_text)
        if content_hash and duplicate_counts.get(content_hash, 0) > 1:
            score -= 10
            issues.append("Opening content appears duplicated across multiple pages")
        else:
            passed.append("Opening content appears unique across crawled pages")

        return self._pillar_result(score, max_score, issues, passed)

    def _score_site_technical_seo(self, pages: list[dict], site_meta: dict) -> dict:
        issues: list[str] = []
        passed: list[str] = []
        score = 0.0
        max_score = 95.0

        https_enabled = site_meta.get("https")
        if https_enabled is None:
            https_enabled = all(str(page.get("url", "")).startswith("https://") for page in pages if page.get("url"))
        if https_enabled:
            score += 15
            passed.append("HTTPS is enabled")
        else:
            issues.append("HTTPS is not enabled across the site")

        if site_meta.get("robots_txt_present"):
            score += 10
            passed.append("robots.txt is present")
        else:
            issues.append("robots.txt was not detected")

        if site_meta.get("sitemap_present"):
            score += 10
            passed.append("sitemap.xml is present")
        else:
            issues.append("sitemap.xml was not detected")

        broken_links_count = int(site_meta.get("broken_links_count") or 0)
        if not broken_links_count:
            broken_links_count = sum(len(page.get("broken_links", []) or []) for page in pages)
        if broken_links_count == 0:
            score += 15
            passed.append("No broken links were reported")
        else:
            issues.append(f"{broken_links_count} broken link(s) were reported")

        avg_load_time = self._average_load_time(pages, site_meta)
        if avg_load_time < 3.0:
            score += 15
            passed.append(f"Average load time is under 3 seconds ({avg_load_time:.2f}s)")
        else:
            issues.append(f"Average load time is {avg_load_time:.2f}s; target under 3 seconds")
        if avg_load_time < 1.5:
            score += 5
            passed.append("Average load time is under 1.5 seconds")

        viewport_ratio = self._page_ratio(pages, lambda page: bool(((page.get("seo") or {}).get("all_meta_tags") or {}).get("viewport")))
        viewport_points = 15 * viewport_ratio
        score += viewport_points
        if viewport_ratio == 1:
            passed.append("Viewport meta tag is present on all scored pages")
        elif viewport_ratio > 0:
            issues.append(f"Viewport meta tag is missing on some pages ({viewport_ratio:.0%} coverage)")
        else:
            issues.append("Viewport meta tag is missing on all pages")

        lazy_ratio = self._page_ratio(pages, self._page_has_lazy_images)
        lazy_points = 10 * lazy_ratio
        score += lazy_points
        if lazy_ratio == 1:
            passed.append("Images use lazy loading across all scored pages")
        elif lazy_ratio > 0:
            issues.append(f"Lazy loading is inconsistent across pages ({lazy_ratio:.0%} coverage)")
        else:
            issues.append("Images are not using lazy loading")

        return self._pillar_result(score, max_score, issues, passed)

    def _score_page_technical_seo(self, page_data: dict, site_meta: dict) -> dict:
        issues: list[str] = []
        passed: list[str] = []
        score = 0.0
        max_score = 95.0

        url = str(page_data.get("url", ""))
        https_enabled = site_meta.get("https")
        if https_enabled is None:
            https_enabled = url.startswith("https://")
        if https_enabled:
            score += 15
            passed.append("HTTPS is enabled")
        else:
            issues.append("HTTPS is not enabled")

        if site_meta.get("robots_txt_present"):
            score += 10
            passed.append("robots.txt is present")
        else:
            issues.append("robots.txt presence not confirmed")

        if site_meta.get("sitemap_present"):
            score += 10
            passed.append("sitemap.xml is present")
        else:
            issues.append("sitemap.xml presence not confirmed")

        broken_links = len(page_data.get("broken_links", []) or [])
        if broken_links == 0:
            score += 15
            passed.append("No broken links were reported for this page")
        else:
            issues.append(f"{broken_links} broken link(s) were reported for this page")

        load_time = float(page_data.get("load_time") or site_meta.get("load_time") or 0.0)
        if load_time and load_time < 3.0:
            score += 15
            passed.append(f"Load time is under 3 seconds ({load_time:.2f}s)")
        elif load_time:
            issues.append(f"Load time is {load_time:.2f}s; target under 3 seconds")
        else:
            issues.append("Load time data was not provided")

        if load_time and load_time < 1.5:
            score += 5
            passed.append("Load time is under 1.5 seconds")

        viewport_present = bool((((page_data.get("seo") or {}).get("all_meta_tags") or {}).get("viewport")))
        if viewport_present:
            score += 15
            passed.append("Viewport meta tag is present")
        else:
            issues.append("Viewport meta tag is missing")

        if self._page_has_lazy_images(page_data):
            score += 10
            passed.append("Images use lazy loading")
        else:
            issues.append("Images are missing lazy loading")

        return self._pillar_result(score, max_score, issues, passed)

    def _score_authority(self, authority_data: dict | None) -> dict:
        if not authority_data:
            metrics = {
                "Link Profile Strength": {"value": None, "description": "Overall quality and diversity of the site’s backlink profile."},
                "Domain Authority": {"value": None, "description": "Predicts how competitive the domain is in search based on backlinks and authority signals."},
                "Page Authority": {"value": None, "description": "Estimates ranking strength for a single page rather than the full domain."},
                "Citation Flow": {"value": None, "description": "Indicates the raw influence of backlinks pointing to the site."},
                "Trust Flow": {"value": None, "description": "Measures how closely links are connected to trusted sites."},
                "External Backlinks": {"value": None, "description": "Counts total backlinks from outside websites."},
                "Referring Domains": {"value": None, "description": "Counts unique websites linking to the domain."},
                "Referring IPs": {"value": None, "description": "Shows how many distinct server IPs link to the domain, helping spot link diversity."},
                "Top Rank": {"value": None, "description": "A traffic/visibility ranking metric where lower values are generally better."},
                "Facebook Shares": {"value": None, "description": "Represents social amplification and content sharing on Facebook."},
            }
            return {
                "score": 50.0,
                "grade": score_to_grade(50.0),
                "issues": ["Authority data was not provided; educational mode enabled with a neutral score of 50."],
                "passed": ["Provide authority_data to replace the neutral score with measured backlink metrics."],
                "educational_mode": True,
                "metrics": metrics,
            }

        aliases = {
            "Link Profile Strength": ["link_profile_strength", "linkProfileStrength", "lps"],
            "Domain Authority": ["domain_authority", "domainAuthority", "da"],
            "Page Authority": ["page_authority", "pageAuthority", "pa"],
            "Citation Flow": ["citation_flow", "citationFlow", "cf"],
            "Trust Flow": ["trust_flow", "trustFlow", "tf"],
            "External Backlinks": ["external_backlinks", "externalBacklinks", "backlinks"],
            "Referring Domains": ["referring_domains", "refDomains", "referringDomains"],
            "Referring IPs": ["referring_ips", "refIPs", "referringIPs"],
            "Top Rank": ["top_rank", "topRank", "rank"],
            "Facebook Shares": ["facebook_shares", "facebookShares", "shares"],
        }
        weights = {
            "Link Profile Strength": 0.15,
            "Domain Authority": 0.18,
            "Page Authority": 0.12,
            "Citation Flow": 0.10,
            "Trust Flow": 0.15,
            "External Backlinks": 0.10,
            "Referring Domains": 0.10,
            "Referring IPs": 0.05,
            "Top Rank": 0.03,
            "Facebook Shares": 0.02,
        }

        metrics: dict[str, dict[str, Any]] = {}
        weighted_total = 0.0
        total_weight = 0.0
        issues: list[str] = []
        passed: list[str] = []

        for label, possible_keys in aliases.items():
            raw_value = None
            for key in possible_keys:
                if key in authority_data and authority_data[key] not in (None, ""):
                    raw_value = authority_data[key]
                    break

            if raw_value in (None, ""):
                issues.append(f"{label} was not provided")
                metrics[label] = {"value": None, "normalized": None}
                continue

            normalized = self._normalize_authority_metric(label, raw_value)
            metrics[label] = {"value": raw_value, "normalized": normalized}
            weighted_total += normalized * weights[label]
            total_weight += weights[label]

            if normalized >= 70:
                passed.append(f"{label} is strong")
            elif normalized < 40:
                issues.append(f"{label} is weak")

        score = weighted_total / total_weight if total_weight else 50.0
        if total_weight == 0:
            issues.append("No usable authority metrics were provided; falling back to a neutral score")
        return {
            "score": round(clamp(score), 2),
            "grade": score_to_grade(score),
            "issues": issues,
            "passed": passed,
            "educational_mode": False,
            "metrics": metrics,
        }

    def _score_ux_design(self, page_data: dict) -> dict:
        images_data = page_data.get("images", {}) or {}
        images = images_data.get("images", []) or []
        structure = page_data.get("structure", {}) or {}
        seo = page_data.get("seo", {}) or {}
        issues: list[str] = []
        passed: list[str] = []
        score = 0.0
        max_score = 90.0

        if images and all(str(img.get("alt", "")).strip() for img in images):
            score += 15
            passed.append("All images have non-empty alt text")
        elif not images:
            score += 15
            passed.append("No images require alt text checks")
        else:
            issues.append("Some images are missing alt text")

        bad_filename_alts = [img.get("alt", "") for img in images if FILENAME_ALT_RE.match(str(img.get("alt", "")).strip())]
        if not bad_filename_alts:
            score += 10
            passed.append("Image alt text avoids filename-like placeholders")
        else:
            issues.append(f"Filename-like alt text found on {len(bad_filename_alts)} image(s)")

        short_alts = [img.get("alt", "") for img in images if img.get("alt") and len(str(img.get("alt", "")).strip()) < 5]
        if not short_alts:
            score += 10
            passed.append("Image alt text is descriptive in length")
        else:
            issues.append(f"Alt text is too short on {len(short_alts)} image(s)")

        html = page_data.get("html") or page_data.get("raw_html") or ""
        if not html or not INLINE_COLOR_RE.search(html):
            score += 5
            passed.append("Inline color styles were not detected")
        else:
            issues.append("Inline color styles were found; review contrast carefully")

        semantic_targets = {"header", "main", "footer", "nav", "article", "section"}
        used = set(structure.get("semantic_elements_used", []) or [])
        semantic_ratio = len(semantic_targets & used) / len(semantic_targets)
        score += 20 * semantic_ratio
        if semantic_ratio >= 0.66:
            passed.append("Semantic HTML5 structure is strong")
        else:
            issues.append("Semantic HTML5 structure is limited")

        modern_images = [img for img in images if str(img.get("src", "")).lower().split("?")[0].endswith((".webp", ".avif"))]
        if images and modern_images:
            score += 10
            passed.append("Modern image formats are in use")
        elif images:
            issues.append("Modern image formats (.webp or .avif) were not detected")
        else:
            score += 10
            passed.append("No legacy image assets were detected")

        viewport_present = bool((seo.get("all_meta_tags") or {}).get("viewport"))
        if viewport_present:
            score += 10
            passed.append("Viewport meta tag is present")
        else:
            issues.append("Viewport meta tag is missing")

        mobile_friendly = viewport_present and (structure.get("has_nav") or structure.get("has_main") or bool(modern_images) or self._page_has_lazy_images(page_data))
        if mobile_friendly:
            score += 10
            passed.append("Page shows mobile-friendly implementation signals")
        else:
            issues.append("Few mobile-friendly implementation signals were detected")

        return self._pillar_result(score, max_score, issues, passed)

    def _score_site_links_architecture(self, pages: list[dict], site_meta: dict) -> dict:
        issues: list[str] = []
        passed: list[str] = []
        urls = [self._normalize_url(page.get("url", "")) for page in pages if page.get("url")]
        url_set = {url for url in urls if url}
        graph: dict[str, set[str]] = {url: set() for url in url_set}
        in_degree = defaultdict(int)
        all_anchor_texts: list[str] = []
        bad_anchor_count = 0
        external_without_rel = 0
        total_external = 0

        for page in pages:
            source = self._normalize_url(page.get("url", ""))
            links = (page.get("links") or {}).get("internal", []) or []
            for link in links:
                text = str(link.get("text", "")).strip().lower()
                if text:
                    all_anchor_texts.append(text)
                if text in BAD_ANCHOR_TEXTS:
                    bad_anchor_count += 1
                target = self._normalize_url(link.get("absolute_url") or link.get("href") or "")
                if source and target in url_set and target != source:
                    graph[source].add(target)

            for link in (page.get("links") or {}).get("external", []) or []:
                total_external += 1
                rel_values = {str(value).lower() for value in (link.get("rel") or [])}
                if not rel_values.intersection({"nofollow", "noopener", "noreferrer"}):
                    external_without_rel += 1
                text = str(link.get("text", "")).strip().lower()
                if text:
                    all_anchor_texts.append(text)
                if text in BAD_ANCHOR_TEXTS:
                    bad_anchor_count += 1

        for source, targets in graph.items():
            for target in targets:
                in_degree[target] += 1

        homepage = self._determine_homepage(pages, site_meta)
        depths = self._compute_depths(homepage, graph)
        orphan_pages = [url for url in url_set if url != homepage and in_degree[url] == 0]
        deep_pages = [url for url, depth in depths.items() if depth > 3]
        shallow_ratio = (sum(1 for url in url_set if depths.get(url, math.inf) <= 2) / len(url_set)) if url_set else 0.0

        score = 100.0
        if orphan_pages:
            score -= 10 * len(orphan_pages)
            issues.append(f"Orphan pages detected: {len(orphan_pages)}")
        else:
            passed.append("No orphan pages were detected")

        if shallow_ratio >= 0.8:
            score += 10
            passed.append("Most pages are reachable within two clicks of the homepage")
        else:
            issues.append(f"Only {shallow_ratio:.0%} of pages are within two clicks of the homepage")

        if deep_pages:
            score -= 5 * len(deep_pages)
            issues.append(f"Deep pages detected beyond click depth 3: {len(deep_pages)}")
        else:
            passed.append("No pages exceed click depth 3")

        if bad_anchor_count:
            score -= 5 * bad_anchor_count
            issues.append(f"Weak anchor text found on {bad_anchor_count} link(s)")
        else:
            passed.append("Anchor text avoids generic phrases like 'click here'")

        if total_external == 0 or external_without_rel == 0:
            score += 10
            passed.append("External links use safe rel attributes")
        else:
            issues.append(f"{external_without_rel} external link(s) are missing rel protection")

        unique_anchor_texts = len(set(all_anchor_texts))
        anchor_variety_ratio = (unique_anchor_texts / len(all_anchor_texts)) if all_anchor_texts else 1.0
        if anchor_variety_ratio >= 0.5 and unique_anchor_texts >= 3:
            score += 10
            passed.append("Anchor text variety is healthy")
        else:
            issues.append("Anchor text variety is limited")

        metrics = {
            "homepage": homepage,
            "orphan_pages": orphan_pages,
            "deep_pages": deep_pages,
            "bad_anchor_count": bad_anchor_count,
            "external_links_without_rel": external_without_rel,
            "anchor_text_variety_ratio": round(anchor_variety_ratio, 2),
        }
        return self._pillar_result(score, 100.0, issues, passed, extra={"metrics": metrics})

    def _score_page_links_architecture(self, page_data: dict) -> dict:
        issues: list[str] = []
        passed: list[str] = []
        links = page_data.get("links", {}) or {}
        internal_links = links.get("internal", []) or []
        external_links = links.get("external", []) or []

        score = 80.0
        bad_anchor_count = 0
        all_anchor_texts: list[str] = []
        for link in internal_links + external_links:
            text = str(link.get("text", "")).strip().lower()
            all_anchor_texts.append(text)
            if text in BAD_ANCHOR_TEXTS:
                bad_anchor_count += 1

        if bad_anchor_count:
            score -= 5 * bad_anchor_count
            issues.append(f"Weak anchor text found on {bad_anchor_count} link(s)")
        else:
            passed.append("Anchor text avoids generic phrases")

        external_without_rel = 0
        for link in external_links:
            rel_values = {str(value).lower() for value in (link.get("rel") or [])}
            if not rel_values.intersection({"nofollow", "noopener", "noreferrer"}):
                external_without_rel += 1

        if external_without_rel == 0:
            score += 10
            passed.append("External links use rel protection")
        else:
            issues.append(f"{external_without_rel} external link(s) are missing rel protection")

        unique_anchor_texts = len({text for text in all_anchor_texts if text})
        anchor_variety_ratio = (unique_anchor_texts / len(all_anchor_texts)) if all_anchor_texts else 1.0
        if anchor_variety_ratio >= 0.5 and unique_anchor_texts >= 2:
            score += 10
            passed.append("Anchor text variety is healthy")
        else:
            issues.append("Anchor text variety is limited")

        if internal_links:
            passed.append(f"Page includes {len(internal_links)} internal link(s)")
        else:
            issues.append("Page has no internal links")

        return self._pillar_result(score, 100.0, issues, passed)

    def _aggregate_pillar(self, name: str, pillar_results: list[dict]) -> dict:
        if not pillar_results:
            logger.debug("No pillar results available for %s; using neutral score", name)
            return {
                "score": 0.0,
                "grade": score_to_grade(0.0),
                "issues": ["No pages were available to score this pillar."],
                "passed": [],
            }
        score = mean(result["score"] for result in pillar_results)
        issues = self._dedupe_messages(message for result in pillar_results for message in result.get("issues", []))
        passed = self._dedupe_messages(message for result in pillar_results for message in result.get("passed", []))
        return {
            "score": round(score, 2),
            "grade": score_to_grade(score),
            "issues": issues,
            "passed": passed,
        }

    def _merge_site_and_page_pillars(self, site_result: dict, page_scores: list[float]) -> dict:
        if page_scores:
            combined_score = (site_result["score"] * 0.7) + (mean(page_scores) * 0.3)
        else:
            combined_score = site_result["score"]
        result = dict(site_result)
        result["score"] = round(clamp(combined_score), 2)
        result["grade"] = score_to_grade(result["score"])
        return result

    def _pillar_result(
        self,
        raw_score: float,
        max_score: float,
        issues: list[str],
        passed: list[str],
        extra: dict[str, Any] | None = None,
    ) -> dict:
        normalized = 0.0 if max_score <= 0 else round(clamp((raw_score / max_score) * 100), 2)
        result = {
            "score": normalized,
            "grade": score_to_grade(normalized),
            "issues": self._dedupe_messages(issues),
            "passed": self._dedupe_messages(passed),
        }
        if extra:
            result.update(extra)
        return result

    def _weighted_score(self, scores: dict[str, float]) -> float:
        weighted = sum(clamp(scores.get(name, 0.0)) * weight for name, weight in PILLAR_WEIGHTS.items())
        return round(clamp(weighted), 2)

    def _primary_keyword(self, page_data: dict, site_meta: dict) -> str:
        site_meta = site_meta or {}
        explicit = site_meta.get("primary_keyword") or page_data.get("primary_keyword")
        if explicit:
            return str(explicit).strip().lower()
        keywords = (page_data.get("seo") or {}).get("top_keywords") or {}
        if keywords:
            return str(next(iter(keywords))).strip().lower()
        return ""

    def _contains_term(self, text: str, term: str) -> bool:
        if not text or not term:
            return False
        return re.search(rf"\b{re.escape(term.lower())}\b", text.lower()) is not None

    def _valid_heading_hierarchy(self, headings: dict) -> bool:
        counts = (headings.get("counts") or {}) if isinstance(headings, dict) else {}
        levels = sorted(
            int(level[1:]) for level, count in counts.items()
            if isinstance(level, str) and len(level) == 2 and level[0] == "h" and level[1:].isdigit()
            and isinstance(count, int) and count > 0
        )
        if not levels:
            return False
        return all((current - previous) <= 1 for previous, current in zip(levels, levels[1:]))

    def _collect_page_text(self, page_data: dict) -> str:
        for key in ("text_content", "text", "content", "raw_text"):
            value = page_data.get(key)
            if isinstance(value, str) and value.strip():
                return self._normalize_whitespace(value)

        html = page_data.get("html") or page_data.get("raw_html")
        if isinstance(html, str) and html.strip():
            soup = BeautifulSoup(html, "lxml")
            for node in soup(["script", "style", "noscript"]):
                node.decompose()
            return self._normalize_whitespace(soup.get_text(" ", strip=True))

        seo = page_data.get("seo", {}) or {}
        headings = page_data.get("headings", {}) or {}
        pieces: list[str] = []
        pieces.extend([
            str(seo.get("title") or ""),
            str(seo.get("meta_description") or ""),
        ])
        for level in range(1, 7):
            for heading in (headings.get("hierarchy", {}) or {}).get(f"h{level}", []) or []:
                pieces.append(str(heading.get("text") or ""))
        for image in ((page_data.get("images") or {}).get("images", []) or []):
            pieces.append(str(image.get("alt") or ""))
        for link in ((page_data.get("links") or {}).get("internal", []) or []):
            pieces.append(str(link.get("text") or ""))
        for link in ((page_data.get("links") or {}).get("external", []) or []):
            pieces.append(str(link.get("text") or ""))

        synthesized = self._normalize_whitespace(" ".join(piece for piece in pieces if piece))
        if synthesized:
            logger.debug("Using synthesized page text for %s due to missing raw text", page_data.get("url", "<unknown>"))
        return synthesized

    def _compute_duplicate_counts(self, pages: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = Counter()
        for page in pages:
            content_hash = self._content_hash(self._collect_page_text(page))
            if content_hash:
                counts[content_hash] += 1
        return counts

    def _content_hash(self, text: str) -> str:
        snippet = self._normalize_whitespace(text)[:200]
        if not snippet:
            return ""
        return hashlib.sha256(snippet.encode("utf-8")).hexdigest()

    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _flesch_reading_ease(self, text: str) -> float:
        words = WORD_RE.findall(text)
        word_count = len(words)
        if word_count == 0:
            return 0.0
        sentence_count = max(1, len([segment for segment in SENTENCE_RE.split(text) if segment.strip()]))
        syllable_count = sum(self._count_syllables(word) for word in words)
        score = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
        return clamp(score)

    def _count_syllables(self, word: str) -> int:
        cleaned = re.sub(r"[^a-z]", "", word.lower())
        if not cleaned:
            return 1
        vowels = "aeiouy"
        syllables = 0
        previous_is_vowel = False
        for char in cleaned:
            is_vowel = char in vowels
            if is_vowel and not previous_is_vowel:
                syllables += 1
            previous_is_vowel = is_vowel
        if cleaned.endswith("e") and syllables > 1:
            syllables -= 1
        return max(1, syllables)

    def _extract_long_tail_phrases(self, text: str) -> list[str]:
        words = [word.lower() for word in WORD_RE.findall(text)]
        if len(words) < 4:
            return []
        phrase_counts: Counter[str] = Counter()
        for size in range(2, 5):
            for index in range(len(words) - size + 1):
                chunk = words[index:index + size]
                if all(token in STOP_WORDS for token in chunk):
                    continue
                if chunk[0] in STOP_WORDS and chunk[-1] in STOP_WORDS:
                    continue
                phrase = " ".join(chunk)
                phrase_counts[phrase] += 1
        candidates = [phrase for phrase, count in phrase_counts.items() if count >= 2]
        candidates.sort(key=lambda phrase: (-phrase_counts[phrase], -len(phrase), phrase))
        return candidates[:5]

    def _average_load_time(self, pages: list[dict], site_meta: dict) -> float:
        if site_meta.get("load_time"):
            return float(site_meta["load_time"])
        load_times = [float(page.get("load_time")) for page in pages if page.get("load_time") is not None]
        return mean(load_times) if load_times else 0.0

    def _page_has_lazy_images(self, page_data: dict) -> bool:
        images = ((page_data.get("images") or {}).get("images", []) or [])
        if not images:
            return True
        return all(str(image.get("loading", "")).lower() == "lazy" for image in images)

    def _page_ratio(self, pages: list[dict], predicate) -> float:
        if not pages:
            return 0.0
        matched = sum(1 for page in pages if predicate(page))
        return matched / len(pages)

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(str(url).strip())
        path = parsed.path.rstrip("/") or "/"
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}" if parsed.scheme and parsed.netloc else path
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    def _determine_homepage(self, pages: list[dict], site_meta: dict) -> str:
        candidates = [
            site_meta.get("homepage_url"),
            site_meta.get("base_url"),
            next((page.get("url") for page in pages if page.get("url")), ""),
        ]
        normalized = [self._normalize_url(url) for url in candidates if url]
        return normalized[0] if normalized else ""

    def _compute_depths(self, homepage: str, graph: dict[str, set[str]]) -> dict[str, int]:
        if not homepage or homepage not in graph:
            return {url: math.inf for url in graph}
        depths = {homepage: 0}
        queue = deque([homepage])
        while queue:
            current = queue.popleft()
            for neighbor in graph.get(current, set()):
                if neighbor not in depths:
                    depths[neighbor] = depths[current] + 1
                    queue.append(neighbor)
        for url in graph:
            depths.setdefault(url, math.inf)
        return depths

    def _normalize_authority_metric(self, label: str, value: Any) -> float:
        numeric = float(value)
        if label in {"Link Profile Strength", "Domain Authority", "Page Authority", "Citation Flow", "Trust Flow"}:
            return clamp(numeric)
        if label == "External Backlinks":
            return clamp((math.log10(max(0.0, numeric) + 1) / 4.0) * 100)
        if label == "Referring Domains":
            return clamp((math.log10(max(0.0, numeric) + 1) / 3.0) * 100)
        if label == "Referring IPs":
            return clamp((math.log10(max(0.0, numeric) + 1) / 3.0) * 100)
        if label == "Facebook Shares":
            return clamp((math.log10(max(0.0, numeric) + 1) / 3.0) * 100)
        if label == "Top Rank":
            if numeric <= 0:
                return 0.0
            return clamp(100 - (math.log10(numeric) / 7.0) * 100)
        return clamp(numeric)

    def _dedupe_messages(self, messages: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for message in messages:
            if message and message not in seen:
                seen.add(message)
                ordered.append(message)
        return ordered

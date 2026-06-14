"""
Google PageSpeed Insights API adapter.

Fetches Core Web Vitals (LCP, CLS, INP) and performance suggestions for a URL.
If no API key is configured the adapter returns a ``not_configured`` status so
the dashboard can display a graceful fallback instead of an error.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)

_PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Thresholds per Google's Core Web Vitals definitions
_THRESHOLDS = {
    "lcp": {"good": 2500, "needs-improvement": 4000},   # milliseconds
    "cls": {"good": 0.1, "needs-improvement": 0.25},    # score (unitless)
    "inp": {"good": 200, "needs-improvement": 500},     # milliseconds
    "fcp": {"good": 1800, "needs-improvement": 3000},   # milliseconds
    "ttfb": {"good": 800, "needs-improvement": 1800},   # milliseconds
}


def _rating(metric: str, value: float) -> str:
    """Return 'good', 'needs-improvement', or 'poor' for a metric value."""
    thresholds = _THRESHOLDS.get(metric)
    if thresholds is None:
        return "unknown"
    if value <= thresholds["good"]:
        return "good"
    if value <= thresholds["needs-improvement"]:
        return "needs-improvement"
    return "poor"


class PageSpeedIntegration:
    """Fetches and interprets Google PageSpeed Insights data."""

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_metrics(self, url: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Fetch Core Web Vitals from the PageSpeed Insights API.

        Returns a dict with keys ``lcp``, ``cls``, ``inp``, ``fcp``,
        ``ttfb``, ``performance_score``, ``suggestions``, and ``status``.
        When ``api_key`` is absent the API is still called (anonymous quota
        applies); if the request fails, a ``not_configured`` status is used.
        """
        try:
            import requests  # already a project dependency
        except ImportError:
            return self._not_configured("requests library unavailable")

        params: Dict[str, str] = {"url": url, "strategy": "mobile"}
        if api_key:
            params["key"] = api_key

        try:
            response = requests.get(_PAGESPEED_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            LOGGER.warning("PageSpeed API request failed for %s: %s", url, exc)
            return self._not_configured(f"API request failed: {exc}")

        return self._parse_response(data)

    def assess_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a metrics dict with ratings and a summary status.

        Adds ``rating`` to each metric entry and sets ``overall_status`` to
        ``'pass'``, ``'warning'``, or ``'fail'`` based on the worst metric.
        """
        if metrics.get("status") == "not_configured":
            return metrics

        rating_priority = {"poor": 2, "needs-improvement": 1, "good": 0, "unknown": 0}
        worst = 0

        for key in ("lcp", "cls", "inp", "fcp", "ttfb"):
            entry = metrics.get(key)
            if not isinstance(entry, dict):
                continue
            r = _rating(key, float(entry.get("value", 0)))
            entry["rating"] = r
            worst = max(worst, rating_priority.get(r, 0))

        metrics["overall_status"] = {2: "fail", 1: "warning"}.get(worst, "pass")
        return metrics

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _not_configured(reason: str = "") -> Dict[str, Any]:
        return {
            "status": "not_configured",
            "overall_status": "not_configured",
            "reason": reason,
            "lcp": None,
            "cls": None,
            "inp": None,
            "fcp": None,
            "ttfb": None,
            "performance_score": None,
            "suggestions": [],
        }

    @staticmethod
    def _parse_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant fields from the raw PSI API response."""
        audits = data.get("lighthouseResult", {}).get("audits", {})
        categories = data.get("lighthouseResult", {}).get("categories", {})

        def _metric(audit_id: str, unit: str = "ms") -> Optional[Dict[str, Any]]:
            audit = audits.get(audit_id, {})
            numeric = audit.get("numericValue")
            if numeric is None:
                return None
            return {
                "value": round(float(numeric), 3),
                "display": audit.get("displayValue", ""),
                "unit": unit,
            }

        # Build suggestions list from opportunities + diagnostics
        suggestions: List[str] = []
        for audit_id, audit in audits.items():
            if audit.get("score") is not None and float(audit.get("score", 1)) < 0.9:
                title = audit.get("title", "")
                description = audit.get("description", "")
                if title:
                    suggestions.append(f"{title}: {description}" if description else title)

        perf_score = categories.get("performance", {}).get("score")

        return {
            "status": "ok",
            "performance_score": round(float(perf_score) * 100) if perf_score is not None else None,
            "lcp": _metric("largest-contentful-paint"),
            "cls": _metric("cumulative-layout-shift", unit="score"),
            "inp": _metric("interaction-to-next-paint") or _metric("total-blocking-time"),
            "fcp": _metric("first-contentful-paint"),
            "ttfb": _metric("server-response-time"),
            "suggestions": suggestions[:10],
        }

"""
Schema markup validator — detects JSON-LD, Microdata and RDFa on a page and
recommends missing schema types based on the site category.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Schema type recommendation matrix                                   #
# ------------------------------------------------------------------ #

_RECOMMENDATIONS: Dict[str, List[Dict[str, Any]]] = {
    "default": [
        {
            "type": "Organization",
            "priority": "high",
            "reason": "Identifies your business in search results and the Knowledge Graph.",
            "snippet": (
                '<script type="application/ld+json">\n'
                '{\n'
                '  "@context": "https://schema.org",\n'
                '  "@type": "Organization",\n'
                '  "name": "Your Business Name",\n'
                '  "url": "https://example.com",\n'
                '  "logo": "https://example.com/logo.png",\n'
                '  "contactPoint": {\n'
                '    "@type": "ContactPoint",\n'
                '    "telephone": "+1-555-555-5555",\n'
                '    "contactType": "customer service"\n'
                '  }\n'
                '}\n'
                "</script>"
            ),
        },
        {
            "type": "WebSite",
            "priority": "high",
            "reason": "Enables Sitelinks Searchbox in Google results.",
            "snippet": (
                '<script type="application/ld+json">\n'
                '{\n'
                '  "@context": "https://schema.org",\n'
                '  "@type": "WebSite",\n'
                '  "name": "Your Site Name",\n'
                '  "url": "https://example.com",\n'
                '  "potentialAction": {\n'
                '    "@type": "SearchAction",\n'
                '    "target": "https://example.com/search?q={search_term_string}",\n'
                '    "query-input": "required name=search_term_string"\n'
                '  }\n'
                '}\n'
                "</script>"
            ),
        },
        {
            "type": "BreadcrumbList",
            "priority": "medium",
            "reason": "Shows breadcrumbs in Google search results, improving CTR.",
            "snippet": (
                '<script type="application/ld+json">\n'
                '{\n'
                '  "@context": "https://schema.org",\n'
                '  "@type": "BreadcrumbList",\n'
                '  "itemListElement": [\n'
                '    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com"},\n'
                '    {"@type": "ListItem", "position": 2, "name": "Page", "item": "https://example.com/page"}\n'
                '  ]\n'
                '}\n'
                "</script>"
            ),
        },
    ],
    "article": [
        {
            "type": "Article",
            "priority": "high",
            "reason": "Enables rich results for news/blog articles including headline and author.",
            "snippet": (
                '<script type="application/ld+json">\n'
                '{\n'
                '  "@context": "https://schema.org",\n'
                '  "@type": "Article",\n'
                '  "headline": "Article Title",\n'
                '  "author": {"@type": "Person", "name": "Author Name"},\n'
                '  "datePublished": "2024-01-01",\n'
                '  "dateModified": "2024-01-15"\n'
                '}\n'
                "</script>"
            ),
        },
    ],
    "ecommerce": [
        {
            "type": "Product",
            "priority": "high",
            "reason": "Enables product rich results (price, availability, reviews).",
            "snippet": (
                '<script type="application/ld+json">\n'
                '{\n'
                '  "@context": "https://schema.org",\n'
                '  "@type": "Product",\n'
                '  "name": "Product Name",\n'
                '  "image": "https://example.com/product.jpg",\n'
                '  "description": "Product description",\n'
                '  "offers": {\n'
                '    "@type": "Offer",\n'
                '    "price": "29.99",\n'
                '    "priceCurrency": "USD",\n'
                '    "availability": "https://schema.org/InStock"\n'
                '  }\n'
                '}\n'
                "</script>"
            ),
        },
    ],
    "local": [
        {
            "type": "LocalBusiness",
            "priority": "high",
            "reason": "Critical for local SEO — enables map pack / local Knowledge Panel.",
            "snippet": (
                '<script type="application/ld+json">\n'
                '{\n'
                '  "@context": "https://schema.org",\n'
                '  "@type": "LocalBusiness",\n'
                '  "name": "Business Name",\n'
                '  "address": {\n'
                '    "@type": "PostalAddress",\n'
                '    "streetAddress": "123 Main St",\n'
                '    "addressLocality": "Anytown",\n'
                '    "addressRegion": "CA",\n'
                '    "postalCode": "90210",\n'
                '    "addressCountry": "US"\n'
                '  },\n'
                '  "telephone": "+1-555-555-5555"\n'
                '}\n'
                "</script>"
            ),
        },
    ],
}

# FAQPage is universally useful
_FAQ_RECOMMENDATION = {
    "type": "FAQPage",
    "priority": "medium",
    "reason": "FAQ rich results can significantly increase SERP real-estate.",
    "snippet": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "FAQPage",\n'
        '  "mainEntity": [\n'
        '    {\n'
        '      "@type": "Question",\n'
        '      "name": "What is your return policy?",\n'
        '      "acceptedAnswer": {"@type": "Answer", "text": "..."}\n'
        '    }\n'
        '  ]\n'
        '}\n'
        "</script>"
    ),
}


class SchemaValidator:
    """Audits structured data on a page and recommends missing schema types."""

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def audit_page(self, html: str, url: str = "") -> Dict[str, Any]:
        """Detect JSON-LD, Microdata and RDFa types on ``html``.

        Returns::

            {
                "url": str,
                "found_types": [str, ...],
                "issues": [str, ...],
                "valid": bool,
            }
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {"url": url, "found_types": [], "issues": ["beautifulsoup4 is required"], "valid": False}

        soup = BeautifulSoup(html, "lxml")
        found_types: Set[str] = set()
        issues: List[str] = []

        # --- JSON-LD ---
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                payload = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError) as exc:
                issues.append(f"Invalid JSON-LD: {exc}")
                continue

            if isinstance(payload, list):
                entries = payload
            elif isinstance(payload, dict) and payload.get("@graph"):
                entries = payload["@graph"]
            else:
                entries = [payload]

            for entry in entries:
                if isinstance(entry, dict):
                    schema_type = entry.get("@type")
                    if schema_type:
                        if isinstance(schema_type, list):
                            found_types.update(schema_type)
                        else:
                            found_types.add(str(schema_type))

        # --- Microdata ---
        for tag in soup.find_all(attrs={"itemtype": True}):
            itemtype = tag.get("itemtype", "")
            # e.g. "https://schema.org/Product" → "Product"
            schema_type = itemtype.rsplit("/", 1)[-1]
            if schema_type:
                found_types.add(schema_type)

        # --- RDFa ---
        for tag in soup.find_all(attrs={"typeof": True}):
            typeof = tag.get("typeof", "")
            # e.g. "schema:Product" or "Product"
            schema_type = typeof.split(":")[-1]
            if schema_type:
                found_types.add(schema_type)

        return {
            "url": url,
            "found_types": sorted(found_types),
            "issues": issues,
            "valid": len(issues) == 0,
        }

    def audit_pages(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Audit multiple pages (each should have ``url`` and ``html`` keys).

        Returns an aggregated result with all found types and per-page issues.
        """
        all_found: Set[str] = set()
        page_results: List[Dict[str, Any]] = []
        all_issues: List[str] = []

        for page in pages:
            html = page.get("html") or page.get("content") or ""
            url = page.get("url", "")
            result = self.audit_page(html, url)
            all_found.update(result["found_types"])
            all_issues.extend(result["issues"])
            page_results.append(result)

        return {
            "found_types": sorted(all_found),
            "issues": all_issues,
            "pages": page_results,
            "valid": len(all_issues) == 0,
        }

    def recommend_schema(self, site_type: str = "default", found_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return schema recommendations that are not already present on the site.

        ``site_type`` should be one of ``'default'``, ``'article'``,
        ``'ecommerce'``, or ``'local'``.  Unknown values fall back to
        ``'default'``.
        """
        found_set: Set[str] = set(found_types or [])
        base = _RECOMMENDATIONS.get("default", [])
        extra = _RECOMMENDATIONS.get(site_type, []) if site_type != "default" else []
        all_recs = base + extra + [_FAQ_RECOMMENDATION]

        # De-duplicate by type; preserve first occurrence
        seen: Set[str] = set()
        deduped: List[Dict[str, Any]] = []
        for rec in all_recs:
            t = rec["type"]
            if t not in seen:
                seen.add(t)
                deduped.append(rec)

        return [rec for rec in deduped if rec["type"] not in found_set]

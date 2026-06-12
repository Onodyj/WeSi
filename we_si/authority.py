"""Authority and backlink metrics providers for WeSi."""
from __future__ import annotations

import copy
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Mapping
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)

METRIC_KEYS = (
    "link_profile_strength",
    "domain_authority",
    "page_authority",
    "citation_flow",
    "trust_flow",
    "external_backlinks",
    "referring_domains",
    "referring_ips",
    "top_rank",
    "facebook_shares",
)


METRIC_EDUCATION = {
    "link_profile_strength": {
        "title": "Link Profile Strength",
        "beginner_explanation": "Think of this as your website's reputation score based on the quality and breadth of websites linking to you.",
        "how_to_improve": [
            "Get listed in reputable industry directories and associations.",
            "Create shareable content such as guides, tools, or original research.",
            "Earn mentions from relevant blogs, local organizations, and partners.",
        ],
    },
    "domain_authority": {
        "title": "Domain Authority",
        "beginner_explanation": "This estimates how competitive your whole domain is in search compared with other websites, using a 0-100 scale.",
        "how_to_improve": [
            "Build high-quality backlinks from trustworthy, relevant websites.",
            "Improve internal linking so authority flows to important pages.",
            "Publish consistently useful content that deserves citations.",
        ],
    },
    "page_authority": {
        "title": "Page Authority",
        "beginner_explanation": "This focuses on the ranking strength of one specific page instead of your entire website.",
        "how_to_improve": [
            "Point internal links at the page you want to strengthen.",
            "Earn external links directly to that page, not just the homepage.",
            "Make the page comprehensive, well-structured, and genuinely helpful.",
        ],
    },
    "citation_flow": {
        "title": "Citation Flow",
        "beginner_explanation": "This estimates how much link power a site has based mostly on the volume of backlinks pointing to it.",
        "how_to_improve": [
            "Increase the number of legitimate websites that mention your content.",
            "Refresh older content so it stays worth linking to.",
            "Promote assets with natural outreach instead of low-quality link schemes.",
        ],
    },
    "trust_flow": {
        "title": "Trust Flow",
        "beginner_explanation": "This estimates how trustworthy your backlinks are by looking at how closely they connect to trusted sites on the web.",
        "how_to_improve": [
            "Prioritize links from respected publications, nonprofits, and industry leaders.",
            "Audit and reduce spammy or irrelevant backlinks when possible.",
            "Build relationships that lead to editorial mentions instead of paid placements.",
        ],
    },
    "external_backlinks": {
        "title": "External Backlinks",
        "beginner_explanation": "This is the total number of links from other websites pointing to yours.",
        "how_to_improve": [
            "Create pages worth referencing, such as resources, studies, and tutorials.",
            "Turn offline partnerships into online mentions and links.",
            "Promote new content through email, social media, and outreach.",
        ],
    },
    "referring_domains": {
        "title": "Referring Domains",
        "beginner_explanation": "This counts how many different websites link to you. Many links from one site are usually less valuable than links from many sites.",
        "how_to_improve": [
            "Diversify outreach so you earn links from many relevant websites.",
            "Publish content for different audience segments and niches.",
            "Contribute expert insights, quotes, or data that others can cite.",
        ],
    },
    "referring_ips": {
        "title": "Referring IPs",
        "beginner_explanation": "This measures how many distinct server locations or hosts your backlinks come from, which can help show link diversity.",
        "how_to_improve": [
            "Seek links from genuinely different organizations and publications.",
            "Avoid over-relying on one network of sites for backlinks.",
            "Build visibility across regions, communities, and industry ecosystems.",
        ],
    },
    "top_rank": {
        "title": "Top Rank",
        "beginner_explanation": "This is a popularity ranking where lower numbers are better, similar to older Alexa-style traffic rankings.",
        "how_to_improve": [
            "Grow steady, qualified traffic through SEO, email, and social channels.",
            "Publish content consistently so visitors return more often.",
            "Improve brand awareness to increase direct visits and mentions.",
        ],
    },
    "facebook_shares": {
        "title": "Facebook Shares",
        "beginner_explanation": "This shows how often your content is being shared on Facebook, which can indicate social reach and content appeal.",
        "how_to_improve": [
            "Write headlines and summaries that are easy to share.",
            "Use compelling images and social metadata like Open Graph tags.",
            "Promote content where your audience is already active and engaged.",
        ],
    },
}


PROVIDER_CONFIG_ALIASES = {
    "OpenPageRank": ("openpagerank", "open_page_rank", "OpenPageRank", "OpenPageRankProvider"),
    "Moz": ("moz", "Moz", "MozProvider"),
    "Majestic": ("majestic", "Majestic", "MajesticProvider"),
    "DataForSEO": ("dataforseo", "data_for_seo", "DataForSEO", "DataForSEOProvider"),
}


PROVIDER_DIRECT_KEYS = {
    "OpenPageRank": {
        "api_key": "api_key",
        "OPEN_PAGERANK_API_KEY": "api_key",
    },
    "Moz": {
        "access_id": "access_id",
        "secret_key": "secret_key",
        "MOZ_ACCESS_ID": "access_id",
        "MOZ_SECRET_KEY": "secret_key",
    },
    "Majestic": {
        "api_key": "api_key",
        "MAJESTIC_API_KEY": "api_key",
    },
    "DataForSEO": {
        "login": "login",
        "password": "password",
        "DATAFORSEO_LOGIN": "login",
        "DATAFORSEO_PASSWORD": "password",
    },
}


def _empty_metrics() -> dict[str, Any]:
    """Return a consistent metrics dictionary with all values initialized to None."""
    return {metric_name: None for metric_name in METRIC_KEYS}


def _normalize_domain(domain: str) -> str:
    """Normalize a raw domain or URL into a bare domain string."""
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain must be a non-empty string")

    candidate = domain.strip()
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    normalized = (parsed.netloc or parsed.path).strip().lower().strip("/")

    if not normalized:
        raise ValueError(f"Could not determine domain from input: {domain!r}")

    return normalized


def _extract_provider_config(config: Mapping[str, Any] | None, provider_name: str) -> dict[str, Any]:
    """Extract a provider-specific config payload from a generic config mapping."""
    if not config:
        return {}

    extracted: dict[str, Any] = {}

    for alias in PROVIDER_CONFIG_ALIASES.get(provider_name, ()):
        nested = config.get(alias)
        if isinstance(nested, Mapping):
            extracted.update(nested)
        elif isinstance(nested, str):
            direct_keys = PROVIDER_DIRECT_KEYS.get(provider_name, {})
            if "api_key" in direct_keys.values():
                extracted.setdefault("api_key", nested)

    for raw_key, normalized_key in PROVIDER_DIRECT_KEYS.get(provider_name, {}).items():
        value = config.get(raw_key)
        if value not in (None, ""):
            extracted[normalized_key] = value

    return extracted


def get_educational_content() -> dict[str, Any]:
    """Returns educational content for all authority metrics."""
    return copy.deepcopy(METRIC_EDUCATION)


class AuthorityProvider(ABC):
    """Abstract interface for authority and backlink data providers."""

    def __init__(self, config: Mapping[str, Any] | None = None):
        self.config = dict(config or {})

    @abstractmethod
    def get_metrics(self, domain: str) -> dict[str, Any]:
        """Returns dict with all 10 metrics above, None for unavailable ones."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    def is_configured(self) -> bool:
        """Returns True if API key is available."""
        return False

    def _get_setting(self, *config_keys: str, env_vars: tuple[str, ...] = ()) -> Any:
        """Resolve a configuration value from explicit config first, then env vars."""
        for key in config_keys:
            value = self.config.get(key)
            if value not in (None, ""):
                return value

        for env_var in env_vars:
            value = os.environ.get(env_var)
            if value not in (None, ""):
                return value

        return None


class OpenPageRankProvider(AuthorityProvider):
    """Fetch authority metrics from the Open PageRank API."""

    API_URL = "https://openpagerank.com/api/v1.0/getPageRank"

    @property
    def name(self) -> str:
        return "OpenPageRank"

    def is_configured(self) -> bool:
        return bool(self._get_setting("api_key", "OPEN_PAGERANK_API_KEY", env_vars=("OPEN_PAGERANK_API_KEY",)))

    def get_metrics(self, domain: str) -> dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("OpenPageRank provider is not configured")

        api_key = self._get_setting("api_key", "OPEN_PAGERANK_API_KEY", env_vars=("OPEN_PAGERANK_API_KEY",))
        normalized_domain = _normalize_domain(domain)

        import requests

        response = requests.get(
            self.API_URL,
            headers={"API-OPR": str(api_key)},
            params=[("domains[]", normalized_domain)],
            timeout=10,
        )
        response.raise_for_status()

        payload = response.json()
        rows = payload.get("response") or []
        if not rows:
            LOGGER.warning("OpenPageRank returned no rows for domain %s", normalized_domain)
            return _empty_metrics()

        row = rows[0]
        page_rank_decimal = row.get("page_rank_decimal")
        top_rank = row.get("rank")

        score = None
        if page_rank_decimal is not None:
            try:
                score = max(0.0, min(float(page_rank_decimal) * 10.0, 100.0))
            except (TypeError, ValueError):
                LOGGER.warning(
                    "OpenPageRank returned a non-numeric page_rank_decimal for %s: %r",
                    normalized_domain,
                    page_rank_decimal,
                )

        normalized_rank = None
        if top_rank is not None:
            try:
                normalized_rank = int(top_rank)
            except (TypeError, ValueError):
                LOGGER.warning(
                    "OpenPageRank returned a non-integer rank for %s: %r",
                    normalized_domain,
                    top_rank,
                )

        metrics = _empty_metrics()
        metrics["link_profile_strength"] = score
        metrics["domain_authority"] = score
        metrics["top_rank"] = normalized_rank
        return metrics


class MozProvider(AuthorityProvider):
    """Stub provider for Moz URL Metrics integration."""

    API_URL = "https://lsapi.seomoz.com/v2/url_metrics"

    @property
    def name(self) -> str:
        return "Moz"

    def is_configured(self) -> bool:
        return bool(self._get_setting("access_id", "MOZ_ACCESS_ID", env_vars=("MOZ_ACCESS_ID",)))

    def get_metrics(self, domain: str) -> dict[str, Any]:
        _normalize_domain(domain)
        raise NotImplementedError(
            "Moz integration not yet implemented. TODO: implement MOZ lsapi v2 endpoint"
        )


class MajesticProvider(AuthorityProvider):
    """Stub provider for Majestic backlink metrics."""

    API_URL = "https://api.majestic.com/api/json"

    @property
    def name(self) -> str:
        return "Majestic"

    def is_configured(self) -> bool:
        return bool(self._get_setting("api_key", "MAJESTIC_API_KEY", env_vars=("MAJESTIC_API_KEY",)))

    def get_metrics(self, domain: str) -> dict[str, Any]:
        _normalize_domain(domain)
        raise NotImplementedError(
            "Majestic integration not yet implemented. TODO: implement Majestic GetIndexItemInfo endpoint"
        )


class DataForSEOProvider(AuthorityProvider):
    """Stub provider for DataForSEO SERP authority data."""

    API_URL = "https://api.dataforseo.com/v3/serp"

    @property
    def name(self) -> str:
        return "DataForSEO"

    def is_configured(self) -> bool:
        login = self._get_setting("login", "DATAFORSEO_LOGIN", env_vars=("DATAFORSEO_LOGIN",))
        password = self._get_setting("password", "DATAFORSEO_PASSWORD", env_vars=("DATAFORSEO_PASSWORD",))
        return bool(login and password)

    def get_metrics(self, domain: str) -> dict[str, Any]:
        _normalize_domain(domain)
        # TODO: implement DataForSEO SERP API authority/backlink endpoint mapping.
        raise NotImplementedError(
            "DataForSEO integration not yet implemented. TODO: implement DataForSEO SERP API endpoint"
        )


class AuthorityManager:
    """Resolve and query configured authority providers in priority order."""

    PROVIDER_CLASSES = (
        OpenPageRankProvider,
        MozProvider,
        MajesticProvider,
        DataForSEOProvider,
    )

    def __init__(self, config: dict | None = None):
        """Auto-detect configured providers from env vars."""
        self.config = dict(config or {})
        self.providers: list[AuthorityProvider] = []

        for provider_class in self.PROVIDER_CLASSES:
            provider_name = provider_class().name
            provider_config = _extract_provider_config(self.config, provider_name)
            provider = provider_class(config=provider_config)
            if provider.is_configured():
                self.providers.append(provider)
                LOGGER.debug("Configured authority provider detected: %s", provider.name)
            else:
                LOGGER.debug("Authority provider not configured: %s", provider.name)

    def get_metrics(self, domain: str) -> dict[str, Any]:
        """
        Try each configured provider in order.
        Returns {
            "metrics": {...},
            "provider": str,
            "educational_mode": bool,
            "educational_content": dict,
        }
        """
        normalized_domain = _normalize_domain(domain)

        if not self.providers:
            return {
                "metrics": None,
                "provider": None,
                "educational_mode": True,
                "educational_content": get_educational_content(),
            }

        for provider in self.providers:
            try:
                metrics = provider.get_metrics(normalized_domain)
                return {
                    "metrics": metrics,
                    "provider": provider.name,
                    "educational_mode": False,
                    "educational_content": {},
                }
            except NotImplementedError as exc:
                LOGGER.info("Authority provider %s skipped: %s", provider.name, exc)
            except Exception as exc:
                LOGGER.warning(
                    "Authority provider %s failed for %s: %s",
                    provider.name,
                    normalized_domain,
                    exc,
                    exc_info=True,
                )

        return {
            "metrics": None,
            "provider": None,
            "educational_mode": False,
            "educational_content": {},
        }

    def available_providers(self) -> list[str]:
        """Return the names of configured providers."""
        return [provider.name for provider in self.providers]


__all__ = [
    "AuthorityManager",
    "AuthorityProvider",
    "DataForSEOProvider",
    "MajesticProvider",
    "METRIC_EDUCATION",
    "MozProvider",
    "OpenPageRankProvider",
    "get_educational_content",
]

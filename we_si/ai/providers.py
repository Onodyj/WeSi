from __future__ import annotations

"""Unified multi-provider AI layer for the SiteIQ platform."""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIProviderConfig:
    """Configuration for a single AI provider."""

    provider: str
    model: str = ""
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """Common interface for all SiteIQ AI providers."""

    def __init__(self, config: Optional[AIProviderConfig] = None) -> None:
        self.config = config or AIProviderConfig(provider="mock", model="siteiq-mock")

    @property
    def provider_name(self) -> str:
        return self.config.provider

    @property
    def model_name(self) -> str:
        return self.config.model

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """Return a text response for the supplied message list."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider is usable in the current environment."""


class OpenAIProvider(BaseAIProvider):
    """OpenAI chat provider."""

    def is_available(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            from openai import OpenAI  # noqa: F401

            return True
        except ImportError:
            logger.warning("OpenAI SDK is not installed; OpenAI provider unavailable.")
            return False

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        if not self.config.api_key:
            raise RuntimeError("OpenAI API key is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            logger.warning("OpenAI SDK import failed: %s", exc)
            raise RuntimeError("OpenAI SDK is not installed.") from exc

        client_kwargs: Dict[str, Any] = {"api_key": self.config.api_key}
        if self.config.endpoint:
            client_kwargs["base_url"] = self.config.endpoint

        client = OpenAI(**client_kwargs)
        payload: Dict[str, Any] = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": _normalize_messages(messages),
        }
        payload.update(_provider_options(self.config.extra, kwargs))

        response = client.chat.completions.create(**payload)
        content = response.choices[0].message.content if response.choices else ""
        return _flatten_content(content) or "No response returned from OpenAI."


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude chat provider."""

    def is_available(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            from anthropic import Anthropic  # noqa: F401

            return True
        except ImportError:
            logger.warning("Anthropic SDK is not installed; Claude provider unavailable.")
            return False

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        if not self.config.api_key:
            raise RuntimeError("Anthropic API key is not configured.")

        try:
            from anthropic import Anthropic
        except ImportError as exc:
            logger.warning("Anthropic SDK import failed: %s", exc)
            raise RuntimeError("Anthropic SDK is not installed.") from exc

        client = Anthropic(api_key=self.config.api_key)
        system_prompt = kwargs.get("system") or _extract_system_prompt(messages)
        anthropic_messages = _messages_without_system(messages)
        payload: Dict[str, Any] = {
            "model": self.config.model or "claude-3-5-sonnet-latest",
            "messages": anthropic_messages or [{"role": "user", "content": "Hello"}],
            "max_tokens": kwargs.get("max_tokens") or self.config.extra.get("max_tokens", 1024),
        }
        if system_prompt:
            payload["system"] = system_prompt

        extra_options = _provider_options(self.config.extra, kwargs, exclude={"system", "max_tokens"})
        payload.update(extra_options)

        response = client.messages.create(**payload)
        text_parts = [block.text for block in getattr(response, "content", []) if getattr(block, "type", "") == "text"]
        return "\n".join(part for part in text_parts if part).strip() or "No response returned from Anthropic."


class GeminiProvider(BaseAIProvider):
    """Google Gemini chat provider."""

    def is_available(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            import google.generativeai as genai  # noqa: F401

            return True
        except ImportError:
            logger.warning("Google Generative AI SDK is not installed; Gemini provider unavailable.")
            return False

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        if not self.config.api_key:
            raise RuntimeError("Google API key is not configured.")

        try:
            import google.generativeai as genai
        except ImportError as exc:
            logger.warning("Gemini SDK import failed: %s", exc)
            raise RuntimeError("Google Generative AI SDK is not installed.") from exc

        genai.configure(api_key=self.config.api_key)
        generation_config = _provider_options(self.config.extra, kwargs)
        model = genai.GenerativeModel(
            model_name=self.config.model or "gemini-1.5-flash",
            generation_config=generation_config or None,
        )
        prompt = _messages_to_prompt(messages)
        response = model.generate_content(prompt)

        text = getattr(response, "text", "")
        if text:
            return text.strip()

        candidates = getattr(response, "candidates", []) or []
        collected: List[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for part in parts:
                part_text = getattr(part, "text", "")
                if part_text:
                    collected.append(part_text)
        return "\n".join(collected).strip() or "No response returned from Gemini."


class OllamaProvider(BaseAIProvider):
    """Local Ollama chat provider."""

    def is_available(self) -> bool:
        try:
            import requests
        except ImportError:
            logger.warning("requests is not installed; Ollama provider unavailable.")
            return False

        try:
            response = requests.get(f"{self._base_url()}/api/tags", timeout=self.config.extra.get("timeout", 2))
            return response.ok
        except Exception:
            return False

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        try:
            import requests
        except ImportError as exc:
            logger.warning("requests import failed for Ollama provider: %s", exc)
            raise RuntimeError("requests is required for Ollama provider.") from exc

        payload: Dict[str, Any] = {
            "model": self.config.model or "llama3.1",
            "messages": _normalize_messages(messages),
            "stream": False,
        }
        payload.update(_provider_options(self.config.extra, kwargs))
        response = requests.post(
            f"{self._base_url()}/api/chat",
            json=payload,
            timeout=self.config.extra.get("timeout", 60),
        )
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        return _flatten_content(message.get("content") or data.get("response") or "") or "No response returned from Ollama."

    def _base_url(self) -> str:
        endpoint = self.config.endpoint or self.config.extra.get("base_url") or "http://localhost:11434"
        return endpoint.rstrip("/")


class N8NProvider(BaseAIProvider):
    """Webhook-backed provider for N8N workflows."""

    def is_available(self) -> bool:
        if not self.config.endpoint:
            return False
        try:
            import requests  # noqa: F401

            return True
        except ImportError:
            logger.warning("requests is not installed; N8N provider unavailable.")
            return False

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        if not self.config.endpoint:
            raise RuntimeError("N8N webhook endpoint is not configured.")

        try:
            import requests
        except ImportError as exc:
            logger.warning("requests import failed for N8N provider: %s", exc)
            raise RuntimeError("requests is required for N8N provider.") from exc

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            auth_prefix = str(self.config.extra.get("auth_prefix", "Bearer")).strip()
            headers["Authorization"] = f"{auth_prefix} {self.config.api_key}".strip()

        payload: Dict[str, Any] = {
            "provider": self.config.provider,
            "model": self.config.model,
            "messages": _normalize_messages(messages),
            "prompt": _last_user_message(messages),
            "system_prompt": kwargs.get("system") or _extract_system_prompt(messages),
            "context": kwargs.get("analysis_data", {}),
        }
        payload.update(_provider_options(self.config.extra, kwargs, exclude={"analysis_data", "system"}))

        response = requests.post(
            self.config.endpoint,
            json=payload,
            headers=headers,
            timeout=self.config.extra.get("timeout", 60),
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response.text.strip()

        data = response.json()
        for key in ("response", "message", "output", "text", "result"):
            if key in data and data[key]:
                return _flatten_content(data[key])
        return response.text.strip() or "No response returned from N8N workflow."


class MockProvider(BaseAIProvider):
    """Rule-based fallback provider that works without any external API."""

    DEFAULT_MODEL = "siteiq-mock-v1"

    def __init__(self, config: Optional[AIProviderConfig] = None) -> None:
        super().__init__(config or AIProviderConfig(provider="mock", model=self.DEFAULT_MODEL))
        if not self.config.model:
            self.config.model = self.DEFAULT_MODEL

    def is_available(self) -> bool:
        return True

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        user_text = (_last_user_message(messages) or "").strip()
        analysis_data = kwargs.get("analysis_data") or {}
        text = f"{_extract_system_prompt(messages)}\n{user_text}".lower()

        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})
        insights = analysis_data.get("insights", {})
        pages = analysis_data.get("pages", []) or []
        site_name = metadata.get("domain") or metadata.get("base_url") or "this site"

        intro = f"Here are practical SiteIQ recommendations for {site_name}:"
        bullets: List[str] = []

        if any(token in text for token in ("action plan", "plan", "priorit", "roadmap", "next step")):
            bullets.extend(self._action_plan(summary, insights, pages))

        keyword_map = {
            "seo": self._seo_tips,
            "title": self._title_tips,
            "meta": self._meta_tips,
            "description": self._meta_tips,
            "h1": self._heading_tips,
            "heading": self._heading_tips,
            "image": self._image_tips,
            "alt": self._image_tips,
            "link": self._link_tips,
            "speed": self._speed_tips,
            "performance": self._speed_tips,
            "accessibility": self._accessibility_tips,
            "cms": self._cms_tips,
            "wordpress": self._cms_tips,
            "squarespace": self._cms_tips,
            "wix": self._cms_tips,
            "shopify": self._cms_tips,
            "content": self._content_tips,
            "schema": self._schema_tips,
            "structured": self._schema_tips,
            "canonical": self._canonical_tips,
            "robots": self._robots_tips,
            "mobile": self._mobile_tips,
        }

        for keyword, handler in keyword_map.items():
            if keyword in text:
                bullets.extend(handler(analysis_data, text))

        if not bullets:
            bullets.extend(self._general_tips(analysis_data))

        if insights.get("critical"):
            bullets.append(f"Address the highest-risk issue first: {insights['critical'][0]}")
        elif insights.get("warnings"):
            bullets.append(f"Start with this warning: {insights['warnings'][0]}")

        bullets = _deduplicate_preserve_order([bullet for bullet in bullets if bullet])[:6]
        if not bullets:
            bullets = [
                "Review the top pages for missing titles, descriptions, headings, and accessibility gaps.",
                "Prioritize changes that improve both user clarity and search visibility.",
            ]

        return intro + "\n- " + "\n- ".join(bullets)

    def _action_plan(self, summary: Dict[str, Any], insights: Dict[str, Any], pages: List[Dict[str, Any]]) -> List[str]:
        plan = []
        if insights.get("critical"):
            plan.append(f"Phase 1: resolve critical issues such as {insights['critical'][0]}")
        if insights.get("warnings"):
            plan.append(f"Phase 2: clean up warning-level items like {insights['warnings'][0]}")
        if summary.get("images_without_alt", 0):
            plan.append(f"Phase 3: add descriptive alt text to {summary['images_without_alt']} image(s)")
        if summary.get("broken_links_found", 0):
            plan.append(f"Phase 4: repair or redirect {summary['broken_links_found']} broken link(s)")
        if pages:
            plan.append("Validate the fixes on the homepage and top conversion pages before rolling them out site-wide")
        return plan

    def _seo_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        summary = analysis_data.get("summary", {})
        return [
            "Make each page target a distinct search intent with a unique title, H1, and meta description.",
            f"Expand thin pages; the current average word count is {summary.get('avg_word_count', 0)}, so pages below ~300 words may need richer copy.",
            "Align page titles, headings, and internal anchor text around the same core topic to reinforce relevance.",
        ]

    def _title_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        pages = analysis_data.get("pages", []) or []
        missing_titles = sum(1 for page in pages if not page.get("seo", {}).get("has_title"))
        return [
            f"Write concise, unique title tags around 50-60 characters; {missing_titles} page(s) appear to be missing titles in this dataset.",
            "Lead with the primary topic or service, then add the brand at the end if space allows.",
        ]

    def _meta_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        pages = analysis_data.get("pages", []) or []
        missing_meta = sum(1 for page in pages if not page.get("seo", {}).get("has_meta_description"))
        return [
            f"Create meta descriptions of roughly 150-160 characters; {missing_meta} page(s) appear to be missing them.",
            "Use benefit-driven language and a call to action so search snippets earn more clicks.",
        ]

    def _heading_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        pages = analysis_data.get("pages", []) or []
        missing_h1 = sum(1 for page in pages if page.get("headings", {}).get("h1_count", 0) == 0)
        return [
            f"Ensure each page has exactly one descriptive H1; {missing_h1} page(s) appear to be missing one.",
            "Use H2 and H3 headings to break up content into scannable sections that match user questions.",
        ]

    def _image_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        summary = analysis_data.get("summary", {})
        return [
            f"Add specific alt text to the {summary.get('images_without_alt', 0)} image(s) missing it so both accessibility and image SEO improve.",
            "Compress oversized images and serve modern formats like WebP where possible to reduce page weight.",
        ]

    def _link_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        summary = analysis_data.get("summary", {})
        return [
            f"Fix or redirect the {summary.get('broken_links_found', 0)} broken link(s) identified in the crawl.",
            "Strengthen internal linking between related service, product, and blog pages using descriptive anchor text.",
            f"Add a few relevant external citations where helpful; the crawl found {summary.get('total_external_links', 0)} external link(s).",
        ]

    def _speed_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        return [
            "Improve page speed by compressing images, deferring non-critical scripts, and reducing third-party embeds.",
            "Review templates for render-blocking CSS/JS and remove unused assets from the most important pages first.",
        ]

    def _accessibility_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        summary = analysis_data.get("summary", {})
        return [
            f"Start with image alt text coverage; {summary.get('images_without_alt', 0)} image(s) are missing alt text in the summary.",
            "Check heading order, form labels, color contrast, and keyboard navigation on the homepage and key conversion pages.",
        ]

    def _cms_tips(self, analysis_data: Dict[str, Any], text: str) -> List[str]:
        cms = self._detect_cms(text, analysis_data)
        tips = ["Apply changes in your CMS theme or page settings first so fixes stay consistent across similar pages."]
        if cms == "wordpress":
            tips.append("In WordPress, update titles/descriptions with your SEO plugin and audit theme templates for heading or schema issues.")
        elif cms == "squarespace":
            tips.append("In Squarespace, check page SEO settings, image alt text fields, and summary block layouts that may create heading issues.")
        elif cms == "wix":
            tips.append("In Wix, review SEO Basics per page, image settings, and strip out duplicate heading elements in the editor.")
        elif cms == "shopify":
            tips.append("In Shopify, edit page SEO previews, collection/product templates, and theme sections that affect headings and structured data.")
        return tips

    def _content_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        summary = analysis_data.get("summary", {})
        return [
            f"Pages with thin copy should be expanded with clearer benefits, FAQs, and proof points; current average word count is {summary.get('avg_word_count', 0)}.",
            "Match content sections to buyer questions and use subheadings so important information is easy to scan.",
        ]

    def _schema_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        return [
            "Add or validate structured data for Organization, LocalBusiness, Product, Article, or FAQ content where relevant.",
            "Use schema only when the on-page content supports it, and keep fields like name, URL, and sameAs consistent site-wide.",
        ]

    def _canonical_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        return [
            "Set canonical URLs on pages with similar or duplicate content so search engines know which version to index.",
            "Check parameterized URLs, archive pages, and CMS-generated duplicates for conflicting canonical tags.",
        ]

    def _robots_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        return [
            "Confirm important pages are indexable and that robots directives are not accidentally blocking them.",
            "Use noindex sparingly for utility, duplicate, or low-value pages rather than key landing pages.",
        ]

    def _mobile_tips(self, analysis_data: Dict[str, Any], _: str) -> List[str]:
        return [
            "Test the homepage and top landing pages on mobile for readable text, tap target spacing, and intrusive popups.",
            "Keep headings short and compress above-the-fold media so mobile users see the primary value quickly.",
        ]

    def _general_tips(self, analysis_data: Dict[str, Any]) -> List[str]:
        summary = analysis_data.get("summary", {})
        insights = analysis_data.get("insights", {})
        return [
            f"Review the {summary.get('total_pages_analyzed', 0)} analyzed page(s) and prioritize issues that affect many templates or high-traffic pages.",
            f"There are {len(insights.get('critical', []))} critical issue(s) and {len(insights.get('warnings', []))} warning(s); fix repeated patterns before isolated edge cases.",
            "After each round of fixes, rerun the crawl to confirm titles, headings, images, and links improved as expected.",
        ]

    def _detect_cms(self, text: str, analysis_data: Dict[str, Any]) -> Optional[str]:
        for cms in ("wordpress", "squarespace", "wix", "shopify", "joomla", "drupal"):
            if cms in text:
                return cms
        cms_data = analysis_data.get("cms") or {}
        return cms_data.get("probable") or (cms_data.get("detected") or [None])[0]


class ProviderFactory:
    """Construct provider instances from config objects."""

    @staticmethod
    def from_config(config: AIProviderConfig) -> BaseAIProvider:
        provider_name = (config.provider or "mock").strip().lower()
        provider_map = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "claude": AnthropicProvider,
            "gemini": GeminiProvider,
            "google": GeminiProvider,
            "ollama": OllamaProvider,
            "n8n": N8NProvider,
            "mock": MockProvider,
            "demo": MockProvider,
        }
        provider_cls = provider_map.get(provider_name)
        if not provider_cls:
            logger.warning("Unknown AI provider '%s'; using MockProvider.", config.provider)
            return MockProvider(AIProviderConfig(provider="mock", model=MockProvider.DEFAULT_MODEL, extra=config.extra))

        try:
            return provider_cls(config)
        except ImportError as exc:
            logger.warning("Provider '%s' could not be initialized due to missing dependency: %s", config.provider, exc)
            return MockProvider(AIProviderConfig(provider="mock", model=MockProvider.DEFAULT_MODEL))


class FallbackChain(BaseAIProvider):
    """Try providers in sequence and return the first successful response."""

    def __init__(self, providers: List[BaseAIProvider]) -> None:
        unique_providers = [provider for provider in providers if provider is not None]
        self.mock_provider = MockProvider()
        if not any(isinstance(provider, MockProvider) for provider in unique_providers):
            unique_providers.append(self.mock_provider)
        super().__init__(AIProviderConfig(provider="fallback", model="chain"))
        self.providers = unique_providers
        self.last_successful_provider: BaseAIProvider = self.mock_provider

    def is_available(self) -> bool:
        return any(provider.is_available() for provider in self.providers) or True

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        for provider in self.providers:
            try:
                if not provider.is_available():
                    continue
                response = provider.chat(messages, **kwargs)
                if response and response.strip():
                    self.last_successful_provider = provider
                    return response.strip()
            except Exception as exc:
                logger.warning("Provider '%s' failed: %s", provider.provider_name, exc)

        self.last_successful_provider = self.mock_provider
        return self.mock_provider.chat(messages, **kwargs)


class AIAssistant:
    """SiteIQ AI assistant with automatic provider selection and fallbacks."""

    def __init__(self, provider: Optional[BaseAIProvider] = None, config_path: Optional[str] = None) -> None:
        self.config_path = config_path
        self.provider = provider or self._build_default_provider(config_path=config_path)

    def build_context_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Build a detailed prompt describing the analyzed site and its issues."""
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})
        insights = analysis_data.get("insights", {})
        pages = analysis_data.get("pages", []) or []
        cms = analysis_data.get("cms", {}) or {}

        lines = [
            "You are SiteIQ's website optimization assistant.",
            "Use the crawl data below to answer questions with concrete, prioritized guidance.",
            "Prefer practical recommendations over generic explanations.",
            "",
            "SITE OVERVIEW",
            f"- Domain: {metadata.get('domain', 'Unknown')}",
            f"- Base URL: {metadata.get('base_url', 'Unknown')}",
            f"- Analysis date: {metadata.get('analysis_date', 'Unknown')}",
            f"- Pages crawled: {metadata.get('pages_crawled', 0)}",
            f"- Pages analyzed: {summary.get('total_pages_analyzed', 0)}",
            f"- Total images: {summary.get('total_images', 0)}",
            f"- Images without alt text: {summary.get('images_without_alt', 0)}",
            f"- Internal links: {summary.get('total_internal_links', 0)}",
            f"- External links: {summary.get('total_external_links', 0)}",
            f"- Broken links: {summary.get('broken_links_found', 0)}",
            f"- Average word count: {summary.get('avg_word_count', 0)}",
        ]

        probable_cms = cms.get("probable") or ", ".join(cms.get("detected", []))
        if probable_cms:
            lines.append(f"- Likely CMS/platform: {probable_cms}")

        lines.extend([
            "",
            "TOP FINDINGS",
            f"- Critical issues: {len(insights.get('critical', []))}",
            f"- Warnings: {len(insights.get('warnings', []))}",
            f"- Recommendations: {len(insights.get('recommendations', []))}",
            f"- Positive findings: {len(insights.get('positive', []))}",
        ])

        if insights.get("critical"):
            lines.append("- Critical details: " + " | ".join(insights["critical"][:3]))
        if insights.get("warnings"):
            lines.append("- Warning details: " + " | ".join(insights["warnings"][:3]))
        if insights.get("recommendations"):
            lines.append("- Recommended improvements: " + " | ".join(insights["recommendations"][:3]))

        if pages:
            lines.extend(["", "PAGE HIGHLIGHTS"])
            for page in pages[:5]:
                seo = page.get("seo", {})
                headings = page.get("headings", {})
                images = page.get("images", {})
                links = page.get("links", {})
                page_bits = [
                    f"URL: {page.get('url', 'Unknown')}",
                    f"status={page.get('status_code', 'n/a')}",
                    f"title={'yes' if seo.get('has_title') else 'no'}",
                    f"meta_description={'yes' if seo.get('has_meta_description') else 'no'}",
                    f"h1_count={headings.get('h1_count', 0)}",
                    f"missing_alt={images.get('missing_alt_count', 0)}",
                    f"internal_links={links.get('total_internal', 0)}",
                    f"external_links={links.get('total_external', 0)}",
                    f"word_count={seo.get('word_count', 0)}",
                ]
                if page.get("error"):
                    page_bits.append(f"error={page['error']}")
                lines.append("- " + "; ".join(page_bits))

        lines.extend([
            "",
            "RESPONSE STYLE",
            "- Be specific to this site's data.",
            "- Prioritize fixes by impact and effort.",
            "- Mention CMS-specific implementation steps when appropriate.",
            "- Keep answers actionable for a site owner or marketer.",
        ])
        return "\n".join(lines)

    def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]],
        analysis_data: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a chat message and return updated history with usage metadata."""
        conversation_history = list(conversation_history or [])
        base_system_prompt = system_prompt or "You are SiteIQ's AI assistant for website analysis and optimization."
        combined_system_prompt = f"{base_system_prompt}\n\n{self.build_context_prompt(analysis_data)}"

        messages: List[Dict[str, Any]] = [{"role": "system", "content": combined_system_prompt}]
        messages.extend(_normalize_messages(conversation_history))
        messages.append({"role": "user", "content": user_message})

        response_text = self.provider.chat(messages, analysis_data=analysis_data, system=combined_system_prompt)
        updated_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response_text},
        ]

        active_provider = self._active_provider()
        usage = {
            "provider": active_provider.provider_name,
            "model": active_provider.model_name,
            "input_messages": len(messages),
            "history_messages": len(updated_history),
            "estimated_prompt_characters": sum(len(_flatten_content(message.get("content", ""))) for message in messages),
            "response_characters": len(response_text),
        }

        return {
            "response": response_text,
            "conversation_history": updated_history,
            "usage": usage,
        }

    def get_quick_answer(self, question: str, analysis_data: Dict[str, Any]) -> str:
        """Return a concise answer without requiring existing conversation history."""
        result = self.chat(
            user_message=question,
            conversation_history=[],
            analysis_data=analysis_data,
            system_prompt="You are SiteIQ's quick-answer assistant. Respond concisely with the highest-value recommendation first.",
        )
        return result["response"]

    def generate_action_plan(self, analysis_data: Dict[str, Any], focus_area: Optional[str] = None) -> str:
        """Generate a prioritized action plan from the supplied analysis."""
        prompt = "Create a prioritized action plan with quick wins, medium effort tasks, and longer-term improvements."
        if focus_area:
            prompt += f" Focus especially on {focus_area}."
        result = self.chat(
            user_message=prompt,
            conversation_history=[],
            analysis_data=analysis_data,
            system_prompt="You are SiteIQ's planning assistant. Organize recommendations into a clear implementation sequence.",
        )
        return result["response"]

    def suggest_cms_specific_fix(self, issue: str, cms: str, analysis_data: Dict[str, Any]) -> str:
        """Suggest a CMS-specific implementation path for a given issue."""
        prompt = (
            f"How should I fix this issue in {cms}: {issue}? "
            "Provide concrete implementation steps, likely settings to review, and a quick validation checklist."
        )
        result = self.chat(
            user_message=prompt,
            conversation_history=[],
            analysis_data=analysis_data,
            system_prompt="You are SiteIQ's CMS implementation assistant. Tailor advice to the named platform and keep it practical.",
        )
        return result["response"]

    def _build_default_provider(self, config_path: Optional[str] = None) -> BaseAIProvider:
        configs = self._load_file_configs(config_path)
        env_configs = self._load_env_configs()

        providers: List[BaseAIProvider] = []
        seen: set[tuple[str, str, Optional[str]]] = set()
        for config in [*configs, *env_configs]:
            key = ((config.provider or "").lower(), config.model or "", config.endpoint)
            if key in seen:
                continue
            seen.add(key)
            providers.append(ProviderFactory.from_config(config))

        if not providers:
            logger.warning("No configured AI provider found; using MockProvider.")
            return MockProvider()
        if len(providers) == 1:
            return FallbackChain(providers)
        return FallbackChain(providers)

    def _load_env_configs(self) -> List[AIProviderConfig]:
        configs: List[AIProviderConfig] = []
        if os.getenv("OPENAI_API_KEY"):
            configs.append(
                AIProviderConfig(
                    provider="openai",
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    api_key=os.getenv("OPENAI_API_KEY"),
                    endpoint=os.getenv("OPENAI_BASE_URL"),
                )
            )
        if os.getenv("ANTHROPIC_API_KEY"):
            configs.append(
                AIProviderConfig(
                    provider="anthropic",
                    model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                )
            )
        if os.getenv("GOOGLE_API_KEY"):
            configs.append(
                AIProviderConfig(
                    provider="gemini",
                    model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                    api_key=os.getenv("GOOGLE_API_KEY"),
                )
            )
        if os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"):
            configs.append(
                AIProviderConfig(
                    provider="ollama",
                    model=os.getenv("OLLAMA_MODEL", "llama3.1"),
                    endpoint=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                )
            )
        if os.getenv("N8N_WEBHOOK_URL"):
            configs.append(
                AIProviderConfig(
                    provider="n8n",
                    model=os.getenv("N8N_MODEL", "n8n-workflow"),
                    api_key=os.getenv("N8N_API_KEY"),
                    endpoint=os.getenv("N8N_WEBHOOK_URL"),
                )
            )
        return configs

    def _load_file_configs(self, config_path: Optional[str]) -> List[AIProviderConfig]:
        candidate_paths: List[Path] = []
        if config_path:
            candidate_paths.append(Path(config_path))
        candidate_paths.append(Path.cwd() / "siteiq_config.json")

        for path in candidate_paths:
            if not path.exists() or not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception as exc:
                logger.warning("Failed to load SiteIQ config from %s: %s", path, exc)
                continue

            raw_provider_config = data.get("ai_provider")
            if raw_provider_config is None:
                continue

            if isinstance(raw_provider_config, list):
                return [self._coerce_config(item) for item in raw_provider_config if item]
            return [self._coerce_config(raw_provider_config)]
        return []

    def _coerce_config(self, raw_config: Any) -> AIProviderConfig:
        if isinstance(raw_config, AIProviderConfig):
            return raw_config
        if isinstance(raw_config, str):
            return AIProviderConfig(provider=raw_config, model="")
        if not isinstance(raw_config, dict):
            logger.warning("Unsupported ai_provider config format %r; using mock provider.", raw_config)
            return AIProviderConfig(provider="mock", model=MockProvider.DEFAULT_MODEL)

        provider = str(raw_config.get("provider") or raw_config.get("name") or "mock")
        model = str(raw_config.get("model") or "")
        api_key = raw_config.get("api_key")
        if not api_key and raw_config.get("api_key_env"):
            api_key = os.getenv(str(raw_config["api_key_env"]))
        if not api_key:
            provider_env_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "claude": "ANTHROPIC_API_KEY",
                "gemini": "GOOGLE_API_KEY",
                "google": "GOOGLE_API_KEY",
                "n8n": "N8N_API_KEY",
            }
            api_key = os.getenv(provider_env_map.get(provider.lower(), "")) or None
        endpoint = raw_config.get("endpoint") or raw_config.get("base_url")
        extra = raw_config.get("extra", {}) or {}
        if not isinstance(extra, dict):
            extra = {"value": extra}
        return AIProviderConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            endpoint=endpoint,
            extra=extra,
        )

    def _active_provider(self) -> BaseAIProvider:
        if isinstance(self.provider, FallbackChain):
            return self.provider.last_successful_provider
        return self.provider


def store_conversation(session: Any, site_analysis_id: int, conversation_history: List[Dict[str, Any]]) -> Optional[Any]:
    """Persist a conversation for a SiteAnalysis record."""
    try:
        from we_si.models import AssistantConversation, AssistantMessage
    except ImportError as exc:
        logger.warning("Unable to import conversation models: %s", exc)
        return None

    try:
        conversation = AssistantConversation(site_analysis_id=site_analysis_id)
        session.add(conversation)
        session.flush()

        for message in conversation_history or []:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "user")
            content = _flatten_content(message.get("content", "")).strip()
            if not content:
                continue
            session.add(
                AssistantMessage(
                    conversation_id=conversation.id,
                    role=role,
                    content=content,
                )
            )

        session.commit()
        return conversation
    except Exception as exc:
        session.rollback()
        logger.warning("Failed to store assistant conversation: %s", exc)
        return None



def load_conversation(session: Any, site_analysis_id: int) -> List[Dict[str, str]]:
    """Load the most recent conversation for a SiteAnalysis record."""
    try:
        from we_si.models import AssistantConversation, AssistantMessage
    except ImportError as exc:
        logger.warning("Unable to import conversation models: %s", exc)
        return []

    try:
        conversation = (
            session.query(AssistantConversation)
            .filter_by(site_analysis_id=site_analysis_id)
            .order_by(AssistantConversation.created_at.desc(), AssistantConversation.id.desc())
            .first()
        )
        if not conversation:
            return []

        messages = (
            session.query(AssistantMessage)
            .filter_by(conversation_id=conversation.id)
            .order_by(AssistantMessage.created_at.asc(), AssistantMessage.id.asc())
            .all()
        )
        return [{"role": message.role, "content": message.content} for message in messages]
    except Exception as exc:
        logger.warning("Failed to load assistant conversation: %s", exc)
        return []



def _provider_options(
    config_extra: Optional[Dict[str, Any]],
    runtime_kwargs: Optional[Dict[str, Any]],
    exclude: Optional[set[str]] = None,
) -> Dict[str, Any]:
    exclude = exclude or set()
    options: Dict[str, Any] = {}
    for source in (config_extra or {}, runtime_kwargs or {}):
        for key, value in source.items():
            if key in {"analysis_data", "system"} or key in exclude:
                continue
            if value is not None:
                options[key] = value
    return options



def _normalize_messages(messages: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user")
        content = _flatten_content(message.get("content", "")).strip()
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized



def _messages_without_system(messages: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized = _normalize_messages(messages)
    return [{"role": m["role"], "content": m["content"]} for m in normalized if m["role"] != "system"]



def _extract_system_prompt(messages: Iterable[Dict[str, Any]]) -> str:
    system_parts = [message["content"] for message in _normalize_messages(messages) if message["role"] == "system"]
    return "\n\n".join(system_parts).strip()



def _messages_to_prompt(messages: Iterable[Dict[str, Any]]) -> str:
    parts = []
    for message in _normalize_messages(messages):
        role = message["role"].capitalize()
        parts.append(f"{role}: {message['content']}")
    return "\n\n".join(parts)



def _last_user_message(messages: Iterable[Dict[str, Any]]) -> str:
    for message in reversed(_normalize_messages(messages)):
        if message["role"] == "user":
            return message["content"]
    return ""



def _flatten_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: List[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text_value = item.get("text") or item.get("content") or ""
                if text_value:
                    chunks.append(str(text_value))
            else:
                chunks.append(str(item))
        return "\n".join(chunk for chunk in chunks if chunk)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or json.dumps(content))
    return str(content)



def _deduplicate_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    results = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results

"""Recommendation engine for exact, ready-to-paste SiteIQ fixes."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - dependency exists in project requirements
    BeautifulSoup = None  # type: ignore[assignment]


SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
VAGUE_ANCHOR_TEXT = {"click here", "here", "read more", "learn more", "more"}


class RecommendationEngine:
    """Generate structured, deterministic recommendations for site issues."""

    def __init__(self, ai_provider=None):
        self.ai_provider = ai_provider

    def generate(
        self,
        pages: List[Dict[str, Any]],
        scoring_result: Dict[str, Any],
        site_meta: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for all pages and site-wide issues."""
        site_meta = dict(site_meta or {})
        pages = pages or []
        page_lookup = {self._normalize_url(page.get("url", "")): page for page in pages if page.get("url")}
        title_lookup = {
            url: self._clean_text(page.get("seo", {}).get("title") or self._first_h1(page) or self._topic_from_page(page))
            for url, page in page_lookup.items()
        }
        site_meta.setdefault("page_title_lookup", title_lookup)

        recommendations: List[Dict[str, Any]] = []
        for page in pages:
            page_score = self._resolve_page_score(page, scoring_result)
            recommendations.extend(self.generate_for_page(page, page_score, site_meta=site_meta))

        recommendations.extend(self._generate_sitewide_recommendations(pages, scoring_result, site_meta))
        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations.sort(key=self._sort_key)
        return recommendations

    def generate_for_page(
        self,
        page_data: Dict[str, Any],
        page_score: Dict[str, Any],
        site_meta: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for a single page."""
        site_meta = site_meta or {}
        recommendations: List[Dict[str, Any]] = []
        url = page_data.get("url", "")
        seo = page_data.get("seo", {}) or {}
        headings = page_data.get("headings", {}) or {}
        images = page_data.get("images", {}) or {}
        links = page_data.get("links", {}) or {}
        page_topic = self._topic_from_page(page_data)
        site_name = self._site_name(site_meta, url)
        location = self._clean_text(site_meta.get("location", ""))
        keyword = self._keyword_from_page(page_data)
        page_score_value = self._extract_numeric_score(page_score)
        page_content = self._extract_page_text(page_data)
        page_summary = self._summarize_topic(page_content, page_topic)

        title = self._clean_text(seo.get("title", ""))
        if not title:
            suggested_title = self._build_title_text(keyword, site_name, location)
            ai_title = self._enhance_title_with_ai(page_data, suggested_title)
            exact_fix = f"Add this title tag to your <head>: <title>{ai_title}</title>"
            recommendations.append(
                self._build_recommendation(
                    pillar="on_page_seo",
                    severity="Critical",
                    page_url=url,
                    element="title tag",
                    current_state="No <title> tag found.",
                    why_it_matters="The title tag is what people see in search results and browser tabs. Without it, search engines and visitors have less context about the page.",
                    exact_fix=exact_fix,
                    placement_instructions="In your HTML <head> section, replace the existing <title> tag (or add one before </head>)",
                    platform_steps=self._platform_steps(
                        generic="Open the page template or HTML file and add the suggested <title> tag inside the <head> section.",
                        wordpress="Dashboard → Pages → Edit page → SEO settings or theme header → paste the suggested title in the SEO/Page Title field.",
                        squarespace="Pages → Select page → Settings → SEO → SEO Title → paste the suggested title.",
                        wix="Menus & Pages → Select page → SEO Basics → Title tag → paste the suggested title.",
                        shopify="Online Store → Pages/Products/Collections → Search engine listing preview → Edit website SEO → Page title.",
                    ),
                    estimated_impact="High",
                )
            )
        else:
            if len(title) > 60:
                rewritten_title = self._shorten_title(title, keyword, site_name)
                rewritten_title = self._enhance_title_with_ai(page_data, rewritten_title)
                recommendations.append(
                    self._build_recommendation(
                        pillar="on_page_seo",
                        severity="Medium" if page_score_value >= 40 else "High",
                        page_url=url,
                        element="title tag",
                        current_state=f"Current title is {len(title)} characters: {title}",
                        why_it_matters="Very long title tags often get cut off in search results, which makes your page look incomplete and can lower clicks.",
                        exact_fix=f"Replace the current title tag with: <title>{rewritten_title}</title>",
                        placement_instructions="In your HTML <head> section, replace the existing <title> tag (or add one before </head>)",
                        platform_steps=self._title_platform_steps(),
                        estimated_impact="Medium",
                    )
                )
            elif len(title) < 10:
                expanded_title = self._build_title_text(keyword, site_name, location)
                expanded_title = self._enhance_title_with_ai(page_data, expanded_title)
                recommendations.append(
                    self._build_recommendation(
                        pillar="on_page_seo",
                        severity="Medium",
                        page_url=url,
                        element="title tag",
                        current_state=f"Current title is too short ({len(title)} characters): {title}",
                        why_it_matters="A very short title does not give search engines or visitors enough detail about the page topic.",
                        exact_fix=f"Replace the current title tag with: <title>{expanded_title}</title>",
                        placement_instructions="In your HTML <head> section, replace the existing <title> tag (or add one before </head>)",
                        platform_steps=self._title_platform_steps(),
                        estimated_impact="Medium",
                    )
                )
            elif keyword and keyword.lower() not in title.lower():
                keyword_title = self._shorten_title(self._build_title_text(keyword, site_name, location), keyword, site_name)
                keyword_title = self._enhance_title_with_ai(page_data, keyword_title)
                recommendations.append(
                    self._build_recommendation(
                        pillar="on_page_seo",
                        severity="Medium",
                        page_url=url,
                        element="title tag",
                        current_state=f"Current title does not include the main topic keyword: {title}",
                        why_it_matters="Including the main page topic in the title helps search engines match the page to relevant searches.",
                        exact_fix=f"Replace the current title tag with: <title>{keyword_title}</title>",
                        placement_instructions="In your HTML <head> section, replace the existing <title> tag (or add one before </head>)",
                        platform_steps=self._title_platform_steps(),
                        estimated_impact="Medium",
                    )
                )

        meta_description = self._clean_text(seo.get("meta_description", ""))
        if not meta_description:
            rewritten_meta = self._build_meta_description(page_summary, page_topic, site_meta, url)
            rewritten_meta = self._enhance_meta_with_ai(page_data, rewritten_meta)
            recommendations.append(
                self._build_recommendation(
                    pillar="on_page_seo",
                    severity="High",
                    page_url=url,
                    element="meta description",
                    current_state="No meta description found.",
                    why_it_matters="The meta description is usually the short summary people read in search results before deciding whether to click.",
                    exact_fix=f"<meta name=\"description\" content=\"{rewritten_meta}\">",
                    placement_instructions='Add this inside your <head>: <meta name="description" content="[YOUR TEXT HERE]">',
                    platform_steps=self._meta_platform_steps(),
                    estimated_impact="High",
                )
            )
        elif not 150 <= len(meta_description) <= 160:
            rewritten_meta = self._build_meta_description(page_summary, page_topic, site_meta, url)
            rewritten_meta = self._enhance_meta_with_ai(page_data, rewritten_meta)
            recommendations.append(
                self._build_recommendation(
                    pillar="on_page_seo",
                    severity="Medium",
                    page_url=url,
                    element="meta description",
                    current_state=f"Current meta description is {len(meta_description)} characters: {meta_description}",
                    why_it_matters="Meta descriptions that are too short or too long can lower click-through rates because search engines may rewrite or cut them off.",
                    exact_fix=f"<meta name=\"description\" content=\"{rewritten_meta}\">",
                    placement_instructions='Add this inside your <head>: <meta name="description" content="[YOUR TEXT HERE]">',
                    platform_steps=self._meta_platform_steps(),
                    estimated_impact="Medium",
                )
            )

        h1_count = int(headings.get("h1_count") or len((headings.get("hierarchy") or {}).get("h1", [])))
        if h1_count == 0:
            h1_text = self._h1_from_title_or_url(page_data)
            recommendations.append(
                self._build_recommendation(
                    pillar="on_page_seo",
                    severity="Critical",
                    page_url=url,
                    element="H1",
                    current_state="No <h1> heading found on the page.",
                    why_it_matters="Your H1 is the main headline for the page. It helps visitors and search engines understand the page topic right away.",
                    exact_fix=f"<h1>{h1_text}</h1>",
                    placement_instructions="Place the <h1> tag as the first heading in your page's main content area (<main> or first <div>)",
                    platform_steps=self._platform_steps(
                        generic="Edit the page content or template and insert the suggested H1 as the first visible heading in the main content area.",
                        wordpress="Dashboard → Pages → Edit page → add a Heading block at the top of the main content → set it to H1.",
                        squarespace="Edit page → add or select the top text block → set the format to Heading 1.",
                        wix="Edit page → select the top heading element → Change Heading Type → H1, or add a new heading at the top.",
                        shopify="Online Store → Themes → Customize or edit page template → add the suggested H1 at the top of the main content.",
                    ),
                    estimated_impact="High",
                )
            )
        elif h1_count > 1:
            h1_items = (headings.get("hierarchy") or {}).get("h1", [])
            h1_texts = [self._clean_text(item.get("text", "")) for item in h1_items if self._clean_text(item.get("text", ""))]
            current_state = f"Found {h1_count} H1 tags: {', '.join(h1_texts) if h1_texts else 'multiple H1 elements'}"
            recommendations.append(
                self._build_recommendation(
                    pillar="on_page_seo",
                    severity="High",
                    page_url=url,
                    element="H1",
                    current_state=current_state,
                    why_it_matters="Using more than one H1 makes it harder for search engines to tell which headline is the main topic of the page.",
                    exact_fix="Change all H1 tags except the first one to H2.",
                    placement_instructions="Place the <h1> tag as the first heading in your page's main content area (<main> or first <div>)",
                    platform_steps=self._platform_steps(
                        generic="Keep the first main heading as H1, then edit every other H1 in the HTML or editor and change it to H2.",
                        wordpress="Edit the page → select each extra Heading block → change its level from H1 to H2.",
                        squarespace="Edit the page → click each extra Heading 1 block → change it to Heading 2.",
                        wix="Edit the page → select each extra heading → Change Heading Type from H1 to H2.",
                        shopify="Edit the page or theme section → keep one H1 only and change the others to H2 in the section settings or template code.",
                    ),
                    estimated_impact="High",
                )
            )

        for image in images.get("missing_alt", []) or []:
            alt_text = self._build_alt_text(image, page_data)
            current_state = f"Image {image.get('src') or image.get('absolute_src') or '#'} is missing alt text."
            recommendations.append(
                self._build_recommendation(
                    pillar="ux_design",
                    severity="Medium",
                    page_url=url,
                    element="image alt",
                    current_state=current_state,
                    why_it_matters="Alt text helps people using screen readers understand images, and it also gives search engines more context about the page.",
                    exact_fix=f'alt="{alt_text}"',
                    placement_instructions='In the img tag, add: alt="[YOUR SUGGESTED TEXT]"',
                    platform_steps=self._platform_steps(
                        generic="Edit the HTML for the image and add the suggested alt attribute inside the <img> tag.",
                        wordpress="Media Library → Edit image → Alt Text field.",
                        squarespace="Image block → Edit → Accessibility Tab → Alt Text.",
                        wix="Click image → Settings → What’s in the image? (Alt Text) → paste the suggested text.",
                        shopify="Online Store → Themes/Products → open the image settings or HTML → add the suggested alt text.",
                    ),
                    estimated_impact="Medium",
                )
            )

        for link in (links.get("internal", []) or []) + (links.get("external", []) or []):
            link_text = self._clean_text(link.get("text", ""))
            if link_text.lower() in VAGUE_ANCHOR_TEXT or not link_text:
                better_text = self._suggest_anchor_text(link, site_meta)
                state_prefix = "Empty anchor text" if not link_text else f'Current anchor text is "{link_text}"'
                recommendations.append(
                    self._build_recommendation(
                        pillar="links_architecture",
                        severity="Medium" if link_text else "High",
                        page_url=url,
                        element="anchor text",
                        current_state=f"{state_prefix} for link {link.get('absolute_url') or link.get('href', '')}.",
                        why_it_matters="Descriptive link text tells readers and search engines what the destination page is about before they click.",
                        exact_fix=better_text,
                        placement_instructions="Replace the visible text between the opening <a> and closing </a> tags with the suggested anchor text.",
                        platform_steps=self._platform_steps(
                            generic="Edit the link in your HTML or page editor and replace the visible link text with the suggested text.",
                            wordpress="Edit the page → click the link text → replace the words shown to visitors.",
                            squarespace="Edit the text block → highlight the link text → replace it with the suggested descriptive wording.",
                            wix="Edit the text element containing the link → replace the linked words with the suggested text.",
                            shopify="Edit the page, product, or blog content → update the linked words to the suggested anchor text.",
                        ),
                        estimated_impact="Medium",
                    )
                )

        broken_links = page_data.get("broken_links", []) or []
        if broken_links:
            broken_items = []
            for broken in broken_links[:5]:
                anchor = self._clean_text(broken.get("text", "")) or "this link"
                target = broken.get("url", "")
                broken_items.append(f'{anchor} → {target} ({broken.get("status_code", 0)})')
            recommendations.append(
                self._build_recommendation(
                    pillar="technical_seo",
                    severity="High",
                    page_url=url,
                    element="broken links",
                    current_state="Broken links found: " + "; ".join(broken_items),
                    why_it_matters="Broken links frustrate visitors and can reduce trust, conversions, and search engine quality signals.",
                    exact_fix="Update each broken <a href=\"...\"> link to the correct live URL, or remove the link entirely if no replacement page exists.",
                    placement_instructions="Edit each affected <a> tag and replace the href value with a working destination URL.",
                    platform_steps=self._platform_steps(
                        generic="Open the page HTML or editor, find each broken link URL, and replace it with a working URL or remove the link.",
                        wordpress="Edit the page → click each broken link → replace the URL in the link settings.",
                        squarespace="Edit page → click the linked text or button → update the URL destination.",
                        wix="Edit the page → select the linked text/button → Change Link → paste the correct URL.",
                        shopify="Edit the page/product/blog content → update each broken link URL in the editor.",
                    ),
                    estimated_impact="High",
                )
            )

        word_count = int(seo.get("word_count", 0) or 0)
        if word_count < 300:
            missing_words = max(0, 300 - word_count)
            recommendations.append(
                self._build_recommendation(
                    pillar="content_quality",
                    severity="Medium",
                    page_url=url,
                    element="body content",
                    current_state=f"Current word count is {word_count} words.",
                    why_it_matters="Thin content gives visitors less value and gives search engines less context about what your page should rank for.",
                    exact_fix=(
                        f"Add at least {missing_words} more words about {page_topic}. "
                        "Consider adding: a brief intro, 2-3 key points, FAQ section, or conclusion."
                    ),
                    placement_instructions="Add the extra content inside the main body area of the page, ideally below the opening section and above the footer.",
                    platform_steps=self._platform_steps(
                        generic="Edit the main page content and expand the body copy with the suggested sections.",
                        wordpress="Dashboard → Pages/Posts → Edit → add more paragraph blocks in the main content area.",
                        squarespace="Edit page → open the main text block → add more body copy and supporting sections.",
                        wix="Edit page → select the main text area → add more body copy, FAQs, or sections.",
                        shopify="Edit the page, product description, or blog post and add more helpful body content in the main editor.",
                    ),
                    estimated_impact="Medium",
                )
            )

        keyword_stuffing_recommendations = self._keyword_stuffing_recommendations(page_data, page_content, seo, url)
        recommendations.extend(keyword_stuffing_recommendations)

        all_meta = seo.get("all_meta_tags", {}) or {}
        if "viewport" not in {str(key).lower(): value for key, value in all_meta.items()}:
            recommendations.append(
                self._build_recommendation(
                    pillar="technical_seo",
                    severity="Medium",
                    page_url=url,
                    element="viewport meta",
                    current_state="No viewport meta tag found.",
                    why_it_matters="Without a viewport tag, pages can display poorly on phones and tablets, which hurts mobile usability and SEO.",
                    exact_fix='<meta name="viewport" content="width=device-width, initial-scale=1">',
                    placement_instructions='Add this inside your <head>: <meta name="viewport" content="width=device-width, initial-scale=1">',
                    platform_steps=self._platform_steps(
                        generic="Open the HTML template for the page and add the viewport meta tag inside the <head> section.",
                        wordpress="Appearance → Theme File Editor or your theme settings → header.php → add the viewport meta tag inside <head>.",
                        squarespace="Settings → Advanced → Code Injection → Header, or use the site header settings if available.",
                        wix="Use the site custom code area or SEO settings to ensure the viewport tag is present in the page head.",
                        shopify="Online Store → Themes → Edit code → theme.liquid → add the viewport meta tag inside <head>.",
                    ),
                    estimated_impact="Medium",
                )
            )

        return recommendations

    def _generate_sitewide_recommendations(
        self,
        pages: List[Dict[str, Any]],
        scoring_result: Dict[str, Any],
        site_meta: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        base_url = self._clean_text(site_meta.get("base_url") or scoring_result.get("base_url") or (pages[0].get("url") if pages else ""))
        domain = self._site_domain(site_meta, base_url)
        site_name = self._site_name(site_meta, base_url)

        https_enabled = site_meta.get("https_enabled")
        if https_enabled is None and base_url:
            https_enabled = urlparse(base_url).scheme == "https"
        if https_enabled is False:
            recommendations.append(
                self._build_recommendation(
                    pillar="technical_seo",
                    severity="Critical",
                    page_url=base_url or domain,
                    element="HTTPS",
                    current_state="The site is loading without HTTPS enabled.",
                    why_it_matters="HTTPS protects visitor data and is a trust and ranking signal for search engines.",
                    exact_fix="Redirect all http:// URLs to https:// via your hosting provider or a redirect rule",
                    placement_instructions="Apply the redirect at the server, CDN, hosting dashboard, or domain routing level so every HTTP request permanently redirects to HTTPS.",
                    platform_steps=self._platform_steps(
                        generic="Enable SSL, then add a 301 redirect rule from http:// to https:// at the server or hosting level.",
                        wordpress="Dashboard → Settings → General → update WordPress Address and Site Address to https://, then force HTTPS in hosting or via a redirect plugin.",
                        squarespace="Squarespace-managed domains usually use SSL automatically; in Settings → Domains, ensure SSL is active and primary URLs use https.",
                        wix="SSL is automatic on Wix. Make sure your connected domain resolves to the secure site URL and update any hardcoded http:// links.",
                        shopify="SSL is automatic on Shopify. Ensure your primary domain is active and update any hardcoded http:// links in themes or content.",
                    ),
                    estimated_impact="High",
                )
            )

        has_robots = self._coalesce_bool(
            site_meta.get("has_robots_txt"),
            scoring_result.get("has_robots_txt"),
            scoring_result.get("technical", {}).get("has_robots_txt") if isinstance(scoring_result.get("technical"), dict) else None,
        )
        if has_robots is False:
            robots_content = (
                "User-agent: *\n"
                "Allow: /\n\n"
                f"Sitemap: https://{domain}/sitemap.xml"
            ) if domain else "User-agent: *\nAllow: /"
            recommendations.append(
                self._build_recommendation(
                    pillar="technical_seo",
                    severity="High",
                    page_url=base_url or domain,
                    element="robots.txt",
                    current_state="No robots.txt file was found.",
                    why_it_matters="A robots.txt file helps search engines understand where they can crawl and where your sitemap lives.",
                    exact_fix=robots_content,
                    placement_instructions="Create a plain-text file named robots.txt in the root of your domain so it loads at /robots.txt.",
                    platform_steps=self._platform_steps(
                        generic="Create a new robots.txt file at your web root and paste the suggested content into it.",
                        wordpress="Use an SEO plugin's robots.txt editor or upload a robots.txt file to the site root via hosting/File Manager.",
                        squarespace="Squarespace controls robots.txt automatically; if it is missing, check domain routing and platform settings or use custom files only if supported.",
                        wix="Wix generates robots.txt automatically. If missing, review SEO settings and domain connection, then contact Wix support if the file does not load.",
                        shopify="Shopify manages robots.txt, but you can customize robots.txt.liquid in supported themes and include the suggested sitemap line if needed.",
                    ),
                    estimated_impact="High",
                )
            )

        has_sitemap = self._coalesce_bool(
            site_meta.get("has_sitemap"),
            scoring_result.get("has_sitemap"),
            scoring_result.get("technical", {}).get("has_sitemap") if isinstance(scoring_result.get("technical"), dict) else None,
        )
        if has_sitemap is False:
            recommendations.append(
                self._build_recommendation(
                    pillar="technical_seo",
                    severity="High",
                    page_url=base_url or domain,
                    element="XML sitemap",
                    current_state="No XML sitemap was found.",
                    why_it_matters="A sitemap helps search engines discover and recrawl your important pages more efficiently.",
                    exact_fix=f"Create an XML sitemap and publish it at https://{domain}/sitemap.xml" if domain else "Create an XML sitemap and publish it at /sitemap.xml",
                    placement_instructions="Generate the sitemap through your CMS or SEO tool, then make sure it is publicly available at /sitemap.xml and referenced in robots.txt.",
                    platform_steps=self._platform_steps(
                        generic="Use your CMS, build process, or SEO tool to generate sitemap.xml, upload it to the site root, and reference it in robots.txt.",
                        wordpress="Install or enable Yoast SEO, Rank Math, or a similar plugin, then confirm the sitemap URL and submit it in Google Search Console.",
                        squarespace="Squarespace usually auto-generates /sitemap.xml. If missing, verify indexing settings and your connected domain.",
                        wix="Wix auto-generates a sitemap. If it is missing, check SEO settings and confirm the site is published on the connected domain.",
                        shopify="Shopify auto-generates sitemaps. If missing, confirm the primary domain is connected and the storefront is live.",
                    ),
                    estimated_impact="High",
                )
            )

        return recommendations

    def _keyword_stuffing_recommendations(
        self,
        page_data: Dict[str, Any],
        page_content: str,
        seo: Dict[str, Any],
        url: str,
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        keyword_density = seo.get("keyword_density", {}) or {}
        if not keyword_density:
            return recommendations

        sentences = self._extract_sentences(page_content)
        for keyword, density in keyword_density.items():
            if density <= 3 or len(str(keyword)) < 4:
                continue
            matches = [sentence for sentence in sentences if re.search(rf"\b{re.escape(str(keyword))}\b", sentence, flags=re.IGNORECASE)]
            examples = matches[:3]
            if not examples:
                examples = [f"Repeated keyword found: {keyword}"]
            recommendations.append(
                self._build_recommendation(
                    pillar="content_quality",
                    severity="Medium",
                    page_url=url,
                    element="body content",
                    current_state=(
                        f'Keyword "{keyword}" appears at {density}% density. Sentences to review: '
                        + " | ".join(examples)
                    ),
                    why_it_matters="Repeating the same keyword too often can make the content sound unnatural and may look manipulative to search engines.",
                    exact_fix=(
                        f'Reduce repeated uses of "{keyword}" in these sentences: '
                        + " | ".join(examples)
                        + ". Replace repeated uses with natural variations, pronouns, or shorter phrasing."
                    ),
                    placement_instructions="Edit the sentences in the body copy where the keyword repeats too often and rewrite them more naturally.",
                    platform_steps=self._platform_steps(
                        generic="Open the page content and rewrite the listed sentences so the keyword appears less often.",
                        wordpress="Edit the page/post content and rewrite the listed sentences in the block editor.",
                        squarespace="Edit the text block containing the repeated keyword and rewrite the listed sentences.",
                        wix="Open the page text element and rewrite the listed sentences with more natural wording.",
                        shopify="Edit the page, product description, or blog post body copy and rewrite the listed sentences.",
                    ),
                    estimated_impact="Medium",
                )
            )
        return recommendations

    def _build_recommendation(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "pillar": kwargs["pillar"],
            "severity": kwargs["severity"],
            "page_url": kwargs["page_url"],
            "element": kwargs["element"],
            "current_state": kwargs["current_state"],
            "why_it_matters": kwargs["why_it_matters"],
            "exact_fix": kwargs["exact_fix"],
            "placement_instructions": kwargs["placement_instructions"],
            "platform_steps": kwargs["platform_steps"],
            "estimated_impact": kwargs["estimated_impact"],
        }

    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[Any, Dict[str, Any]] = {}
        for recommendation in recommendations:
            key = (
                recommendation.get("pillar"),
                recommendation.get("severity"),
                recommendation.get("element"),
                recommendation.get("why_it_matters"),
                recommendation.get("exact_fix"),
                recommendation.get("placement_instructions"),
                tuple(sorted((recommendation.get("platform_steps") or {}).items())),
                recommendation.get("estimated_impact"),
            )
            existing = grouped.get(key)
            if not existing:
                grouped[key] = dict(recommendation)
                continue

            existing_urls = existing.get("page_url")
            if not isinstance(existing_urls, list):
                existing_urls = [existing_urls]
            new_url = recommendation.get("page_url")
            if isinstance(new_url, list):
                existing_urls.extend(new_url)
            else:
                existing_urls.append(new_url)
            existing["page_url"] = sorted({url for url in existing_urls if url})

            current_state = existing.get("current_state", "")
            new_state = recommendation.get("current_state", "")
            if new_state and new_state not in current_state:
                existing["current_state"] = f"{current_state} | {new_state}" if current_state else new_state

        for recommendation in grouped.values():
            if isinstance(recommendation.get("page_url"), list) and len(recommendation["page_url"]) == 1:
                recommendation["page_url"] = recommendation["page_url"][0]
        return list(grouped.values())

    def _sort_key(self, recommendation: Dict[str, Any]) -> Any:
        page_url = recommendation.get("page_url")
        if isinstance(page_url, list):
            page_url = ",".join(page_url)
        return (
            SEVERITY_ORDER.get(recommendation.get("severity", "Low"), 99),
            recommendation.get("pillar", ""),
            recommendation.get("element", ""),
            str(page_url or ""),
        )

    def _resolve_page_score(self, page: Dict[str, Any], scoring_result: Dict[str, Any]) -> Dict[str, Any]:
        url = self._normalize_url(page.get("url", ""))
        if not isinstance(scoring_result, dict):
            return {}

        page_scores = scoring_result.get("page_scores")
        if isinstance(page_scores, dict):
            if url in page_scores:
                return self._wrap_score(page_scores[url])
            for key, value in page_scores.items():
                if self._normalize_url(str(key)) == url:
                    return self._wrap_score(value)

        pages = scoring_result.get("pages")
        if isinstance(pages, list):
            for entry in pages:
                if self._normalize_url(str(entry.get("url", ""))) == url:
                    return self._wrap_score(entry)

        return self._wrap_score(scoring_result.get("overall_score") or scoring_result.get("score") or {})

    def _wrap_score(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, (int, float)):
            return {"score": value}
        return {}

    def _extract_numeric_score(self, page_score: Dict[str, Any]) -> float:
        if not isinstance(page_score, dict):
            return 80.0
        for key in ("score", "overall_score", "total", "page_score"):
            value = page_score.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return 80.0

    def _platform_steps(self, generic: str, wordpress: str, squarespace: str, wix: str, shopify: str) -> Dict[str, str]:
        return {
            "wordpress": wordpress,
            "squarespace": squarespace,
            "wix": wix,
            "shopify": shopify,
            "generic": generic,
        }

    def _title_platform_steps(self) -> Dict[str, str]:
        return self._platform_steps(
            generic="Open the page template or HTML file and replace the existing <title> tag inside the <head> section with the suggested version.",
            wordpress="Dashboard → Pages → Edit page → SEO settings or theme header → paste the suggested title in the SEO/Page Title field.",
            squarespace="Pages → Select page → Settings → SEO → SEO Title → paste the suggested title.",
            wix="Menus & Pages → Select page → SEO Basics → Title tag → paste the suggested title.",
            shopify="Online Store → Pages/Products/Collections → Search engine listing preview → Edit website SEO → Page title.",
        )

    def _meta_platform_steps(self) -> Dict[str, str]:
        return self._platform_steps(
            generic="Open the page template or HTML file and add or replace the meta description inside the <head> section.",
            wordpress="Dashboard → Pages → Edit page → SEO plugin settings → Meta Description field.",
            squarespace="Pages → Select page → Settings → SEO → SEO Description.",
            wix="Menus & Pages → Select page → SEO Basics → Meta description.",
            shopify="Online Store → Pages/Products/Collections → Search engine listing preview → Edit website SEO → Description.",
        )

    def _build_title_text(self, keyword: str, site_name: str, location: str) -> str:
        parts = [self._limit_length(self._title_case(keyword), 42)]
        if site_name:
            parts.append(site_name)
        title = " - ".join([part for part in parts if part])
        if location:
            title = f"{title} | {location}" if title else location
        return self._limit_length(title or self._title_case(keyword), 60)

    def _shorten_title(self, title: str, keyword: str, site_name: str) -> str:
        candidate = self._build_title_text(keyword, site_name, "") if keyword else title
        if len(candidate) <= 60:
            return candidate
        words = re.split(r"\s+", candidate)
        trimmed = []
        for word in words:
            proposed = (" ".join(trimmed + [word])).strip()
            if len(proposed) <= 57:
                trimmed.append(word)
            else:
                break
        shortened = " ".join(trimmed).strip() or candidate[:57].rstrip()
        return shortened[:57].rstrip(" -|") + "..."

    def _build_meta_description(self, summary: str, page_topic: str, site_meta: Dict[str, Any], url: str) -> str:
        domain = self._site_domain(site_meta, url)
        summary_sentence = self._clean_text(summary or f"Learn about {page_topic}")
        summary_sentence = summary_sentence.rstrip(". ")
        cta = site_meta.get("call_to_action") or "Contact us today"
        text = f"{summary_sentence}. {cta}. Learn more at {domain or 'your website'}."
        if len(text) < 150:
            filler = f" Get practical details about {page_topic.lower()} and next steps."
            text = (text.rstrip(".") + "." + filler).replace("..", ".")
        return self._fit_meta_description(text)

    def _fit_meta_description(self, text: str) -> str:
        text = self._clean_text(text)
        if len(text) > 160:
            trimmed = text[:157].rsplit(" ", 1)[0].rstrip(" ,.;:")
            return trimmed + "..."
        if len(text) < 150:
            extension = " Trusted guidance for visitors and search engines."
            while len(text) < 150:
                remaining = 160 - len(text)
                if remaining <= 0:
                    break
                addition = extension[:remaining]
                text += addition
                if len(addition) < len(extension):
                    break
            text = text[:160].rstrip(" ,.;:")
            if not text.endswith((".", "!", "?")):
                text += "."
        return text[:160]

    def _build_alt_text(self, image: Dict[str, Any], page_data: Dict[str, Any]) -> str:
        filename = self._filename_from_src(image.get("src") or image.get("absolute_src") or "")
        context = self._clean_text(image.get("context") or "")
        if not context:
            context = self._find_image_context(page_data, image)
        topic = self._topic_from_page(page_data)

        if filename and not re.fullmatch(r"img\d+|image\d*|photo\d*|pic\d*", filename, flags=re.IGNORECASE):
            alt_text = self._title_case(filename)
        else:
            alt_text = f"{topic} image"

        if context and context.lower() not in alt_text.lower():
            alt_text = f"{alt_text} - {context[:50].rstrip(' ,.;:')}"
        return self._limit_length(self._clean_text(alt_text), 125)

    def _suggest_anchor_text(self, link: Dict[str, Any], site_meta: Dict[str, Any]) -> str:
        absolute_url = self._normalize_url(link.get("absolute_url") or link.get("href") or "")
        title_lookup = site_meta.get("page_title_lookup", {}) or {}
        target_title = self._clean_text(title_lookup.get(absolute_url, ""))
        if target_title:
            return target_title
        slug = self._slug_to_topic(absolute_url)
        return self._title_case(slug or "Learn More")

    def _h1_from_title_or_url(self, page_data: Dict[str, Any]) -> str:
        seo_title = self._clean_text(page_data.get("seo", {}).get("title", ""))
        if seo_title:
            return self._title_case(seo_title.split("|")[0].split("-")[0].strip())
        return self._title_case(self._topic_from_page(page_data))

    def _topic_from_page(self, page_data: Dict[str, Any]) -> str:
        first_h1 = self._first_h1(page_data)
        if first_h1:
            return self._title_case(first_h1)
        title = self._clean_text(page_data.get("seo", {}).get("title", ""))
        if title:
            return self._title_case(title.split("|")[0].split("-")[0].strip())
        return self._title_case(self._slug_to_topic(page_data.get("url", "")) or "This Page")

    def _keyword_from_page(self, page_data: Dict[str, Any]) -> str:
        first_h1 = self._first_h1(page_data)
        if first_h1:
            return self._clean_text(first_h1)
        title = self._clean_text(page_data.get("seo", {}).get("title", ""))
        if title:
            return title.split("|")[0].split("-")[0].strip()
        return self._slug_to_topic(page_data.get("url", "")) or "Page Topic"

    def _first_h1(self, page_data: Dict[str, Any]) -> str:
        hierarchy = (page_data.get("headings") or {}).get("hierarchy") or {}
        h1_items = hierarchy.get("h1", []) or []
        for item in h1_items:
            if isinstance(item, dict):
                text = self._clean_text(item.get("text", ""))
                if text:
                    return text
            else:
                text = self._clean_text(str(item))
                if text:
                    return text
        return ""

    def _extract_page_text(self, page_data: Dict[str, Any]) -> str:
        candidates = [
            page_data.get("text_content"),
            page_data.get("body_text"),
            page_data.get("text"),
            page_data.get("content"),
            page_data.get("html"),
            page_data.get("raw_html"),
            page_data.get("intro"),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            candidate = str(candidate)
            if "<" in candidate and ">" in candidate:
                extracted = self._html_to_text(candidate)
                if extracted:
                    return extracted
            cleaned = self._clean_text(candidate)
            if cleaned:
                return cleaned
        return ""

    def _find_image_context(self, page_data: Dict[str, Any], image: Dict[str, Any]) -> str:
        text = self._extract_page_text(page_data)
        if not text:
            return ""
        sentences = self._extract_sentences(text)
        return sentences[0] if sentences else text[:60]

    def _extract_sentences(self, text: str) -> List[str]:
        text = self._clean_text(text)
        if not text:
            return []
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]

    def _summarize_topic(self, text: str, fallback_topic: str) -> str:
        sentences = self._extract_sentences(text)
        if sentences:
            return self._limit_length(sentences[0], 110)
        return f"Helpful information about {fallback_topic.lower()}"

    def _title_case(self, text: str) -> str:
        words = [word for word in re.split(r"\s+", self._clean_text(text)) if word]
        return " ".join(word[:1].upper() + word[1:] for word in words)

    def _slug_to_topic(self, url: str) -> str:
        path = urlparse(str(url)).path.strip("/")
        slug = path.split("/")[-1] if path else "home"
        slug = re.sub(r"[-_]+", " ", slug)
        slug = re.sub(r"\.[a-z0-9]+$", "", slug, flags=re.IGNORECASE)
        slug = re.sub(r"\s+", " ", slug).strip()
        return slug or "home"

    def _filename_from_src(self, src: str) -> str:
        path = urlparse(str(src)).path
        filename = path.rsplit("/", 1)[-1]
        filename = re.sub(r"\.[a-z0-9]+$", "", filename, flags=re.IGNORECASE)
        return re.sub(r"[-_]+", " ", filename).strip()

    def _site_domain(self, site_meta: Dict[str, Any], url: str) -> str:
        domain = self._clean_text(site_meta.get("domain", ""))
        if domain:
            return domain
        return urlparse(str(url)).netloc

    def _site_name(self, site_meta: Dict[str, Any], url: str) -> str:
        site_name = self._clean_text(site_meta.get("site_name", ""))
        if site_name:
            return site_name
        domain = self._site_domain(site_meta, url)
        if not domain:
            return ""
        root = domain.split(":")[0].split(".")
        if len(root) >= 2:
            return root[-2].capitalize()
        return root[0].capitalize()

    def _normalize_url(self, url: str) -> str:
        return str(url or "").rstrip("/")

    def _limit_length(self, text: str, max_length: int) -> str:
        text = self._clean_text(text)
        if len(text) <= max_length:
            return text
        trimmed = text[: max_length - 3].rsplit(" ", 1)[0].rstrip(" ,.;:")
        return (trimmed or text[: max_length - 3]).rstrip() + "..."

    def _clean_text(self, text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _coalesce_bool(self, *values: Any) -> Optional[bool]:
        for value in values:
            if isinstance(value, bool):
                return value
        return None

    def _html_to_text(self, html: str) -> str:
        if BeautifulSoup is None:
            return self._clean_text(re.sub(r"<[^>]+>", " ", html))
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return self._clean_text(text)

    def _enhance_title_with_ai(self, page_data: Dict[str, Any], fallback: str) -> str:
        prompt = (
            "Rewrite this HTML title so it is natural, specific, and 50-60 characters long. "
            f"Page topic: {self._topic_from_page(page_data)}. Existing title: {page_data.get('seo', {}).get('title', '')}. "
            f"Return only the title text. Draft: {fallback}"
        )
        return self._call_ai(prompt, fallback, 60)

    def _enhance_meta_with_ai(self, page_data: Dict[str, Any], fallback: str) -> str:
        prompt = (
            "Rewrite this meta description so it is compelling, accurate, and 150-160 characters long. "
            f"Page topic: {self._topic_from_page(page_data)}. Existing meta description: {page_data.get('seo', {}).get('meta_description', '')}. "
            f"Page summary: {self._summarize_topic(self._extract_page_text(page_data), self._topic_from_page(page_data))}. "
            f"Return only the meta description text. Draft: {fallback}"
        )
        return self._call_ai(prompt, fallback, 160, min_length=150)

    def _call_ai(self, prompt: str, fallback: str, max_length: int, min_length: int = 1) -> str:
        if self.ai_provider is None:
            return fallback
        try:
            response = None
            for method_name in ("generate_text", "generate", "complete"):
                method = getattr(self.ai_provider, method_name, None)
                if callable(method):
                    response = method(prompt)
                    break
            if response is None:
                return fallback
            if isinstance(response, dict):
                response = response.get("text") or response.get("content") or response.get("result") or ""
            response = self._clean_text(response)
            if not response:
                return fallback
            if max_length == 160:
                response = self._fit_meta_description(response)
                return response if len(response) >= min_length else fallback
            if len(response) < min_length:
                return fallback
            return self._limit_length(response, max_length)
        except Exception:
            return fallback

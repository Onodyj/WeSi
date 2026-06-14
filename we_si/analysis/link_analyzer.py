"""
Link graph builder — constructs a directed graph of internal links from
crawl results, calculates click-depth from the homepage, and identifies
orphan pages.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)


class LinkGraphAnalyzer:
    """Builds and analyses the internal link graph for a crawled site."""

    def __init__(self) -> None:
        # adjacency list: source_url → set of target_urls
        self._edges: Dict[str, Set[str]] = {}
        # reverse adjacency: target_url → set of source_urls
        self._in_edges: Dict[str, Set[str]] = {}
        self._base_url: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def build_graph(self, crawl_results: List[Dict[str, Any]], base_url: str = "") -> Dict[str, Any]:
        """Construct the link graph from a list of crawled page dicts.

        Each page dict must have a ``url`` key and may contain an
        ``analysis_data`` dict (from the PageAnalysis model) or a
        ``links.internal`` list.

        Returns a topology summary including orphans, click-depths, and
        a JSON-serialisable representation for visualisation.
        """
        self._edges = {}
        self._in_edges = {}
        self._base_url = base_url.rstrip("/") if base_url else ""

        all_urls: Set[str] = set()

        for page in crawl_results:
            src = self._normalise(page.get("url", ""))
            if not src:
                continue
            all_urls.add(src)
            if src not in self._edges:
                self._edges[src] = set()

            internal_links = self._extract_internal_links(page)
            for tgt in internal_links:
                tgt = self._normalise(tgt)
                if not tgt:
                    continue
                all_urls.add(tgt)
                self._edges[src].add(tgt)
                self._in_edges.setdefault(tgt, set()).add(src)

        # Ensure every discovered URL is in the edges dict
        for url in all_urls:
            self._edges.setdefault(url, set())

        click_depths = self._bfs_depths()
        orphans = self._find_orphans(all_urls)

        return {
            "nodes": sorted(all_urls),
            "edges": [
                {"source": src, "target": tgt}
                for src, targets in self._edges.items()
                for tgt in sorted(targets)
            ],
            "orphans": sorted(orphans),
            "click_depths": {url: depth for url, depth in click_depths.items()},
            "depth_distribution": self._depth_distribution(click_depths),
            "total_pages": len(all_urls),
            "total_links": sum(len(v) for v in self._edges.values()),
            "orphan_count": len(orphans),
        }

    def export_for_visualization(self) -> Dict[str, Any]:
        """Return a D3/vis.js-compatible ``{nodes, edges}`` dict.

        Each node has ``id``, ``label``, ``depth``, and ``is_orphan``
        attributes.  Each edge has ``source`` and ``target`` keys.
        """
        click_depths = self._bfs_depths()
        all_urls: Set[str] = set(self._edges.keys()) | {tgt for tgts in self._edges.values() for tgt in tgts}
        orphans = self._find_orphans(all_urls)

        nodes = []
        for url in sorted(all_urls):
            depth = click_depths.get(url, -1)
            label = _url_label(url)
            nodes.append({
                "id": url,
                "label": label,
                "depth": depth,
                "is_orphan": url in orphans,
            })

        edges = [
            {"source": src, "target": tgt}
            for src, targets in self._edges.items()
            for tgt in sorted(targets)
            if src != tgt
        ]

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _normalise(self, url: str) -> str:
        url = (url or "").strip().rstrip("/")
        if not url:
            return ""
        if "://" not in url:
            if self._base_url:
                url = self._base_url.rstrip("/") + "/" + url.lstrip("/")
            else:
                return ""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ""
        return url

    def _extract_internal_links(self, page: Dict[str, Any]) -> List[str]:
        """Pull internal link URLs out of a page dict (various shapes)."""
        links: List[str] = []

        # Shape 1: analysis_data has links.internal list of {url/absolute_url}
        analysis_data = page.get("analysis_data") or {}
        if isinstance(analysis_data, dict):
            for item in analysis_data.get("links", {}).get("internal", []):
                href = item.get("absolute_url") or item.get("url") or ""
                if href:
                    links.append(href)

        # Shape 2: top-level links.internal (from wesi.py page_data)
        for item in page.get("links", {}).get("internal", []):
            href = item.get("absolute_url") or item.get("url") or (item if isinstance(item, str) else "")
            if href:
                links.append(href)

        # Shape 3: flat list of strings under "internal_links"
        for href in page.get("internal_links", []):
            if isinstance(href, str):
                links.append(href)

        return links

    def _bfs_depths(self) -> Dict[str, int]:
        """BFS from the base URL (homepage) to assign click-depth to each node."""
        if not self._base_url:
            return {}

        depths: Dict[str, int] = {}
        # Try the base URL with and without trailing slash
        start_candidates = [self._base_url, self._base_url + "/"]
        start = next((c for c in start_candidates if c in self._edges), None)
        if start is None and self._edges:
            # Fall back to the first node if base URL not in graph
            start = sorted(self._edges.keys())[0]
        if start is None:
            return {}

        queue: deque[Tuple[str, int]] = deque([(start, 0)])
        depths[start] = 0

        while queue:
            current, depth = queue.popleft()
            for neighbour in sorted(self._edges.get(current, [])):
                if neighbour not in depths:
                    depths[neighbour] = depth + 1
                    queue.append((neighbour, depth + 1))

        return depths

    def _find_orphans(self, all_urls: Set[str]) -> Set[str]:
        """Pages not reachable from the homepage (no inbound internal links)."""
        reachable = set(self._bfs_depths().keys())
        return all_urls - reachable

    @staticmethod
    def _depth_distribution(click_depths: Dict[str, int]) -> Dict[str, int]:
        distribution: Dict[str, int] = {}
        for depth in click_depths.values():
            key = str(depth)
            distribution[key] = distribution.get(key, 0) + 1
        return distribution


def _url_label(url: str) -> str:
    """Return a short human-readable label for a URL."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    if len(path) > 40:
        path = "…" + path[-38:]
    return path

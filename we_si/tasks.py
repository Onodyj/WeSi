"""Async job runner for WeSi website analysis.

Supports an optional Celery/Redis backend for distributed execution and a
built-in thread-based fallback for local and development use.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
CELERY_REDIS_URL = REDIS_URL or "redis://localhost:6379/0"
_USE_CELERY_REQUESTED = os.getenv("USE_CELERY", "").strip().lower() == "true" or bool(REDIS_URL)
USE_CELERY = False


ProgressFn = Callable[[float, str, Optional[str]], None]


def _database_url() -> str:
    """Return the configured database URL."""
    return os.getenv("DATABASE_URL", "sqlite:///wesi.db")


def _clamp_progress(value: float) -> float:
    """Clamp progress to a valid percentage."""
    return round(max(0.0, min(100.0, float(value))), 2)


def _emit_progress(progress_fn: Optional[ProgressFn], pct: float, step: str, url: Optional[str] = None) -> None:
    """Safely emit progress updates."""
    if not progress_fn:
        return

    try:
        progress_fn(_clamp_progress(pct), step, url)
    except Exception:
        logger.exception("Progress callback failed for step '%s'", step)


class ThreadJobStore:
    """In-process job store using threading.Thread + dict."""

    _jobs: Dict[str, Dict[str, Any]] = {}
    _lock = threading.RLock()

    def submit(self, fn, *args, **kwargs) -> str:
        """Run ``fn`` in a background thread and return the job ID."""
        job_id = str(uuid.uuid4())

        with self._lock:
            self._jobs[job_id] = {
                "status": "pending",
                "progress": 0.0,
                "current_step": "Queued",
                "result": None,
                "error": None,
            }

        def progress_fn(pct: float, step: str, url: Optional[str] = None) -> None:
            updates = {
                "status": "running",
                "progress": _clamp_progress(pct),
                "current_step": step,
            }
            if url:
                updates["current_url"] = url
            self._update_job(job_id, **updates)

        def runner() -> None:
            logger.info("Starting thread-backed analysis job %s", job_id)
            self._update_job(job_id, status="running", current_step="Starting analysis")

            try:
                run_kwargs = dict(kwargs)
                run_kwargs.setdefault("progress_fn", progress_fn)
                result = fn(*args, **run_kwargs)
                self._update_job(
                    job_id,
                    status="completed",
                    progress=100.0,
                    current_step="Completed",
                    result=result,
                    error=None,
                )
                logger.info("Thread-backed analysis job %s completed", job_id)
            except Exception as exc:
                logger.exception("Thread-backed analysis job %s failed", job_id)
                self._update_job(
                    job_id,
                    status="failed",
                    progress=100.0,
                    current_step="Failed",
                    result=None,
                    error=str(exc),
                )

        thread = threading.Thread(target=runner, name=f"wesi-job-{job_id}", daemon=True)
        thread.start()
        return job_id

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """Return unified job status information."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {
                    "status": "failed",
                    "progress": 0.0,
                    "current_step": "Unknown job",
                    "result": None,
                    "error": f"Job '{job_id}' not found",
                }
            return dict(job)

    def get_result(self, job_id: str) -> Any:
        """Return a completed job result."""
        status = self.get_status(job_id)
        if status["status"] == "failed":
            raise RuntimeError(status["error"] or f"Job '{job_id}' failed")
        return status.get("result")

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id].update(updates)


def run_analysis(
    site_analysis_id: int,
    base_url: str,
    user_id: int,
    max_pages: int = 50,
    max_depth: int = 3,
    progress_fn: Optional[ProgressFn] = None,
) -> Dict[str, Any]:
    """
    The actual analysis logic (runs in Celery worker or Thread).

    Steps:
    1. Load SiteAnalysis from DB, set status=RUNNING
    2. Crawl with WebsiteCrawler, emit progress 0-50%
    3. Analyze each page with PageAnalyzer, emit progress 50-90%
    4. Run SiteIQScorer on all pages, emit progress 90-95%
    5. Generate insights + summary
    6. Save all PageAnalysis records + update SiteAnalysis
    7. Return result dict with summary, insights, scores, pages_analyzed
    """
    from we_si.analyzer import PageAnalyzer
    from we_si.crawler import WebsiteCrawler
    from we_si.models import JobStatus, PageAnalysis, SiteAnalysis, init_db

    logger.info(
        "Starting analysis for site_analysis_id=%s base_url=%s user_id=%s",
        site_analysis_id,
        base_url,
        user_id,
    )

    _, Session = init_db(_database_url())
    session = Session()
    site_analysis = None

    try:
        if hasattr(session, "get"):
            site_analysis = session.get(SiteAnalysis, site_analysis_id)
        else:
            site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if site_analysis is None:
            raise ValueError(f"SiteAnalysis {site_analysis_id} not found")

        if site_analysis.user_id != user_id:
            logger.warning(
                "User mismatch for site_analysis_id=%s: record user_id=%s, request user_id=%s",
                site_analysis_id,
                site_analysis.user_id,
                user_id,
            )

        parsed_url = urlparse(base_url)
        site_analysis.base_url = base_url
        site_analysis.domain = parsed_url.netloc or site_analysis.domain
        site_analysis.status = JobStatus.RUNNING
        site_analysis.progress = 0.0
        site_analysis.pages_crawled = 0
        site_analysis.pages_analyzed = 0
        site_analysis.error_message = None
        site_analysis.summary = None
        site_analysis.insights = None
        site_analysis.started_at = datetime.utcnow()
        site_analysis.completed_at = None

        session.query(PageAnalysis).filter_by(site_analysis_id=site_analysis_id).delete(synchronize_session=False)
        session.commit()

        _emit_progress(progress_fn, 0, "Starting analysis", base_url)

"""
Celery tasks for asynchronous site analysis processing.
"""
from celery import Celery
from datetime import datetime
import time
from typing import Dict, Any

# Initialize Celery
celery_app = Celery(
    'wesi',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery_app.task(bind=True)
def analyze_website_task(self, site_analysis_id: int, base_url: str, user_id: int, max_pages: int = 50, max_depth: int = 3):
    """
    Asynchronous task to crawl and analyze a website.
    
    Args:
        self: Celery task instance (for progress updates)
        site_analysis_id: Database ID of SiteAnalysis record
        base_url: Website URL to analyze
        user_id: User ID
        max_pages: Maximum pages to crawl
        max_depth: Maximum crawl depth
        
    Returns:
        Dictionary with analysis results
    """
    from we_si.models import init_db, SiteAnalysis, PageAnalysis, JobStatus
    from we_si.crawler import WebsiteCrawler
    from we_si.analyzer import PageAnalyzer
    from urllib.parse import urlparse
    
    # Initialize database
    engine, Session = init_db()
    session = Session()
    
    try:
        # Get site analysis record
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            raise ValueError(f"SiteAnalysis {site_analysis_id} not found")
        
        # Update status to running
        site_analysis.status = JobStatus.RUNNING
        site_analysis.started_at = datetime.utcnow()
        session.commit()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting crawler...'})
        
        # Initialize crawler
        crawler = WebsiteCrawler(
            base_url=base_url,
            max_pages=max_pages,
            max_depth=max_depth,
            rate_limit=0.5,
        )

        def crawl_progress(current: int, total: int, current_url: str) -> None:
            total = max(total, 1)
            pct = (current / total) * 50.0
            site_analysis.progress = _clamp_progress(pct)
            site_analysis.pages_crawled = current
            session.commit()
            _emit_progress(progress_fn, pct, f"Crawling page {current}/{total}", current_url)

        crawled_pages = crawler.crawl(progress_callback=crawl_progress)
        crawled_count = len(crawled_pages)
        site_analysis.pages_crawled = crawled_count
        site_analysis.progress = 50.0
        session.commit()
        _emit_progress(progress_fn, 50, "Crawling complete")

        analyzer = PageAnalyzer()
        analyzed_pages: List[Dict[str, Any]] = []
        total_pages = len(crawled_pages)

        for idx, page_data in enumerate(crawled_pages, start=1):
            page_url = page_data.get("url", "")
            content = page_data.get("content", "")
            status_code = page_data.get("status_code", 0)
            depth = page_data.get("depth", 0)
            error_message = page_data.get("error")

            if content:
                analysis = analyzer.analyze_page(page_url, content, time.time())
                analysis["status_code"] = status_code
                analysis["depth"] = depth
                if error_message:
                    analysis["error"] = error_message
                analyzed_pages.append(analysis)
                record = PageAnalysis(
                    site_analysis_id=site_analysis_id,
                    url=page_url,
                    status_code=status_code,
                    depth=depth,
                    load_time=analysis.get("load_time", 0),
                    analysis_data=analysis,
                )
            else:
                record = PageAnalysis(
                    site_analysis_id=site_analysis_id,
                    url=page_url,
                    status_code=status_code,
                    depth=depth,
                    analysis_data={
                        "url": page_url,
                        "status_code": status_code,
                        "depth": depth,
                        "error": error_message or "Failed to fetch",
                    },
                )

            session.add(record)
            session.flush()

            pct = 50.0 if total_pages == 0 else 50.0 + (idx / total_pages) * 40.0
            site_analysis.progress = _clamp_progress(pct)
            site_analysis.pages_analyzed = len(analyzed_pages)
            session.commit()
            _emit_progress(progress_fn, pct, f"Analyzing page {idx}/{total_pages}", page_url)

        _emit_progress(progress_fn, 90, "Scoring site")
        site_analysis.progress = 90.0
        session.commit()

        scores: Optional[Dict[str, Any]] = None
        site_meta = {
            "site_analysis_id": site_analysis_id,
            "base_url": base_url,
            "domain": parsed_url.netloc,
            "user_id": user_id,
            "pages_crawled": crawled_count,
            "pages_analyzed": len(analyzed_pages),
        }

        try:
            from we_si.scoring import SiteIQScorer

            scorer = SiteIQScorer()
            scores = scorer.score_site(analyzed_pages, site_meta)
        except ImportError:
            logger.warning("SiteIQScorer not available; skipping scoring")
        except Exception:
            logger.exception("Site scoring failed; continuing without scores")

        site_analysis.progress = 95.0
        session.commit()
        _emit_progress(progress_fn, 95, "Generating insights and summary")

        insights = generate_insights(analyzed_pages)
        summary = generate_summary(analyzed_pages)

        result = {
            "status": "completed",
            "site_analysis_id": site_analysis_id,
            "summary": summary,
            "insights": insights,
            "scores": scores,
            "pages_analyzed": len(analyzed_pages),
        }

        site_analysis.status = JobStatus.COMPLETED
        site_analysis.progress = 100.0
        site_analysis.pages_crawled = crawled_count
        site_analysis.pages_analyzed = len(analyzed_pages)
        site_analysis.summary = summary
        site_analysis.insights = insights
        site_analysis.completed_at = datetime.utcnow()
        session.commit()

        _emit_progress(progress_fn, 100, "Analysis complete")
        logger.info(
            "Completed analysis for site_analysis_id=%s (%s pages analyzed)",
            site_analysis_id,
            len(analyzed_pages),
        )
        return result

    except Exception as exc:
        logger.exception("Analysis failed for site_analysis_id=%s", site_analysis_id)
        session.rollback()

        if site_analysis is not None:
            try:
                site_analysis.status = JobStatus.FAILED
                site_analysis.progress = 100.0
                site_analysis.error_message = str(exc)
                site_analysis.completed_at = datetime.utcnow()
                session.commit()
            except Exception:
                logger.exception("Failed to persist failure state for site_analysis_id=%s", site_analysis_id)
                session.rollback()

        _emit_progress(progress_fn, 100, "Analysis failed", base_url)
        raise
            rate_limit=0.5
        )
        
        # Crawl website with progress callback
        def progress_callback(current, total, url):
            progress = (current / total) * 50  # First 50% for crawling
            site_analysis.progress = progress
            site_analysis.pages_crawled = current
            session.commit()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': progress,
                    'status': f'Crawling page {current}/{total}',
                    'current_url': url
                }
            )
        
        crawled_pages = crawler.crawl(progress_callback=progress_callback)
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Analyzing pages...'})
        
        # Initialize analyzer
        analyzer = PageAnalyzer()
        
        # Analyze each page
        analyzed_pages = []
        total_pages = len(crawled_pages)
        
        for idx, page_data in enumerate(crawled_pages, 1):
            url = page_data['url']
            content = page_data.get('content', '')
            status_code = page_data.get('status_code', 0)
            depth = page_data.get('depth', 0)
            
            if content:
                # Analyze page
                start_time = time.time()
                analysis = analyzer.analyze_page(url, content, start_time)
                analysis['status_code'] = status_code
                analysis['depth'] = depth
                
                # Store in database
                page_analysis = PageAnalysis(
                    site_analysis_id=site_analysis_id,
                    url=url,
                    status_code=status_code,
                    depth=depth,
                    load_time=analysis.get('load_time', 0),
                    analysis_data=analysis
                )
                session.add(page_analysis)
                
                analyzed_pages.append(analysis)
            else:
                # Store failed page
                page_analysis = PageAnalysis(
                    site_analysis_id=site_analysis_id,
                    url=url,
                    status_code=status_code,
                    depth=depth,
                    analysis_data={'error': page_data.get('error', 'Failed to fetch')}
                )
                session.add(page_analysis)
            
            # Update progress
            progress = 50 + (idx / total_pages) * 45  # 50-95% for analysis
            site_analysis.progress = progress
            site_analysis.pages_analyzed = idx
            session.commit()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': progress,
                    'status': f'Analyzing page {idx}/{total_pages}',
                    'current_url': url
                }
            )
        
        # Generate insights
        self.update_state(state='PROGRESS', meta={'progress': 95, 'status': 'Generating insights...'})
        
        insights = generate_insights(analyzed_pages)
        summary = generate_summary(analyzed_pages)
        
        # Update site analysis with results
        site_analysis.status = JobStatus.COMPLETED
        site_analysis.completed_at = datetime.utcnow()
        site_analysis.progress = 100
        site_analysis.summary = summary
        site_analysis.insights = insights
        session.commit()
        
        result = {
            'status': 'completed',
            'site_analysis_id': site_analysis_id,
            'summary': summary,
            'insights': insights,
            'pages_analyzed': len(analyzed_pages)
        }
        
        return result
        
    except Exception as e:
        # Mark as failed
        site_analysis.status = JobStatus.FAILED
        site_analysis.error_message = str(e)
        site_analysis.completed_at = datetime.utcnow()
        session.commit()
        
        raise
    
    finally:
        session.close()


def generate_insights(analyzed_pages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Generate insights from analyzed pages."""
    insights: Dict[str, List[str]] = {
        "critical": [],
        "warnings": [],
        "recommendations": [],
        "positive": [],
    }

    if not analyzed_pages:
        return insights

    total_pages = len(analyzed_pages)

    pages_without_title = sum(1 for p in analyzed_pages if not p.get("seo", {}).get("has_title"))
    if pages_without_title > 0:
        insights["critical"].append(
            f"{pages_without_title} page(s) missing title tags. Add unique, descriptive titles to all pages."
        )

    pages_without_description = sum(
        1 for p in analyzed_pages if not p.get("seo", {}).get("has_meta_description")
    )
    if pages_without_description > 0:
        insights["warnings"].append(
            f"{pages_without_description} page(s) missing meta descriptions. "
            "Add compelling descriptions (150-160 characters)."
        )

    pages_multiple_h1 = sum(1 for p in analyzed_pages if p.get("headings", {}).get("has_multiple_h1"))
    if pages_multiple_h1 > 0:
        insights["warnings"].append(
            f"{pages_multiple_h1} page(s) have multiple H1 tags. Use only one H1 per page."
        )

    pages_no_h1 = sum(1 for p in analyzed_pages if p.get("headings", {}).get("h1_count", 0) == 0)
    if pages_no_h1 > 0:
        insights["warnings"].append(
            f"{pages_no_h1} page(s) missing H1 tags. Add a primary H1 heading to each page."
        )

    total_images = sum(p.get("images", {}).get("count", 0) for p in analyzed_pages)
    missing_alt = sum(p.get("images", {}).get("missing_alt_count", 0) for p in analyzed_pages)
    if missing_alt > 0:
        insights["warnings"].append(
            f"{missing_alt} out of {total_images} images missing alt text. "
            "Add descriptive alt text for accessibility."
        )

    avg_word_count = (
        sum(p.get("seo", {}).get("word_count", 0) for p in analyzed_pages) / total_pages
        if total_pages > 0
        else 0
    )
    if avg_word_count < 300:
        insights["recommendations"].append(
def generate_insights(analyzed_pages: list) -> Dict:
    """Generate insights from analyzed pages."""
    insights = {
        'critical': [],
        'warnings': [],
        'recommendations': [],
        'positive': []
    }
    
    if not analyzed_pages:
        return insights
    
    total_pages = len(analyzed_pages)
    
    # SEO insights
    pages_without_title = sum(1 for p in analyzed_pages 
                             if not p.get('seo', {}).get('has_title'))
    if pages_without_title > 0:
        insights['critical'].append(
            f"{pages_without_title} page(s) missing title tags. "
            "Add unique, descriptive titles to all pages."
        )
    
    pages_without_description = sum(1 for p in analyzed_pages 
                                   if not p.get('seo', {}).get('has_meta_description'))
    if pages_without_description > 0:
        insights['warnings'].append(
            f"{pages_without_description} page(s) missing meta descriptions. "
            "Add compelling descriptions (150-160 characters)."
        )
    
    # Heading insights
    pages_multiple_h1 = sum(1 for p in analyzed_pages 
                           if p.get('headings', {}).get('has_multiple_h1'))
    if pages_multiple_h1 > 0:
        insights['warnings'].append(
            f"{pages_multiple_h1} page(s) have multiple H1 tags. "
            "Use only one H1 per page."
        )
    
    pages_no_h1 = sum(1 for p in analyzed_pages 
                     if p.get('headings', {}).get('h1_count', 0) == 0)
    if pages_no_h1 > 0:
        insights['warnings'].append(
            f"{pages_no_h1} page(s) missing H1 tags. "
            "Add a primary H1 heading to each page."
        )
    
    # Image insights
    total_images = sum(p.get('images', {}).get('count', 0) for p in analyzed_pages)
    missing_alt = sum(p.get('images', {}).get('missing_alt_count', 0) for p in analyzed_pages)
    if missing_alt > 0:
        insights['warnings'].append(
            f"{missing_alt} out of {total_images} images missing alt text. "
            "Add descriptive alt text for accessibility."
        )
    
    # Content insights
    avg_word_count = sum(p.get('seo', {}).get('word_count', 0) 
                        for p in analyzed_pages) / total_pages if total_pages > 0 else 0
    if avg_word_count < 300:
        insights['recommendations'].append(
            f"Average page word count is {int(avg_word_count)}. "
            "Consider adding more quality content (aim for 300+ words)."
        )
    else:
        insights["positive"].append(
            f"Good content depth with average {int(avg_word_count)} words per page."
        )

    pages_with_good_accessibility = sum(
        1 for p in analyzed_pages if p.get("accessibility", {}).get("score", 0) >= 80
    )
    if pages_with_good_accessibility > total_pages * 0.8:
        insights["positive"].append(
            f"{pages_with_good_accessibility} out of {total_pages} pages have good accessibility scores."
        )

    return insights


def generate_summary(analyzed_pages: List[Dict[str, Any]]) -> Dict[str, int]:
    """Generate summary statistics from analyzed pages."""
    if not analyzed_pages:
        return {}

    total_pages = len(analyzed_pages)
    total_images = sum(p.get("images", {}).get("count", 0) for p in analyzed_pages)
    images_without_alt = sum(p.get("images", {}).get("missing_alt_count", 0) for p in analyzed_pages)
    total_internal_links = sum(p.get("links", {}).get("total_internal", 0) for p in analyzed_pages)
    total_external_links = sum(p.get("links", {}).get("total_external", 0) for p in analyzed_pages)
    avg_word_count = int(
        sum(p.get("seo", {}).get("word_count", 0) for p in analyzed_pages) / total_pages
    )

    return {
        "total_pages_analyzed": total_pages,
        "total_images": total_images,
        "images_without_alt": images_without_alt,
        "total_internal_links": total_internal_links,
        "total_external_links": total_external_links,
        "broken_links_found": 0,
        "avg_word_count": avg_word_count,
    }


if _USE_CELERY_REQUESTED:
    try:
        from celery import Celery
    except ImportError:
        logger.warning("Celery requested but not installed; using thread-based job store instead")
    else:
        USE_CELERY = True
        celery_app = Celery("siteiq", broker=CELERY_REDIS_URL, backend=CELERY_REDIS_URL)
        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
        )

        @celery_app.task(bind=True)
        def analyze_website_task(
            self,
            site_analysis_id: int,
            base_url: str,
            user_id: int,
            max_pages: int = 50,
            max_depth: int = 3,
        ) -> Dict[str, Any]:
            """Celery wrapper around :func:`run_analysis`."""

            def progress_fn(pct: float, step: str, url: Optional[str] = None) -> None:
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": _clamp_progress(pct),
                        "status": step,
                        "current_step": step,
                        "current_url": url or "",
                    },
                )

            return run_analysis(
                site_analysis_id,
                base_url,
                user_id,
                max_pages=max_pages,
                max_depth=max_depth,
                progress_fn=progress_fn,
            )

        def start_analysis_job(
            site_analysis_id: int,
            base_url: str,
            user_id: int,
            max_pages: int = 50,
            max_depth: int = 3,
        ) -> str:
            """Start analysis job. Returns job_id."""
            task = analyze_website_task.apply_async(
                args=[site_analysis_id, base_url, user_id, max_pages, max_depth]
            )
            logger.info("Queued Celery analysis job %s for site_analysis_id=%s", task.id, site_analysis_id)
            return task.id

        def get_job_status(job_id: str) -> Dict[str, Any]:
            """Get unified status details for a Celery-backed job."""
            task = celery_app.AsyncResult(job_id)
            meta = task.info if isinstance(task.info, dict) else {}
            current_step = meta.get("current_step") or meta.get("status") or task.state.title()

            if task.state == "PENDING":
                return {
                    "status": "pending",
                    "progress": 0.0,
                    "current_step": "Queued",
                    "result": None,
                    "error": None,
                }

            if task.state in {"STARTED", "RECEIVED", "RETRY", "PROGRESS"}:
                return {
                    "status": "running",
                    "progress": _clamp_progress(meta.get("progress", 0.0)),
                    "current_step": current_step,
                    "result": None,
                    "error": None,
                }

            if task.state == "SUCCESS":
                result = task.result if isinstance(task.result, dict) else {"result": task.result}
                return {
                    "status": "completed",
                    "progress": 100.0,
                    "current_step": "Completed",
                    "result": result,
                    "error": None,
                }

            error = str(task.result) if task.result is not None else meta.get("error")
            return {
                "status": "failed",
                "progress": _clamp_progress(meta.get("progress", 100.0)),
                "current_step": current_step,
                "result": None,
                "error": error or "Job failed",
            }
else:
    _store = ThreadJobStore()

    def start_analysis_job(
        site_analysis_id: int,
        base_url: str,
        user_id: int,
        max_pages: int = 50,
        max_depth: int = 3,
    ) -> str:
        """Start analysis job. Returns job_id."""
        return _store.submit(
            run_analysis,
            site_analysis_id,
            base_url,
            user_id,
            max_pages=max_pages,
            max_depth=max_depth,
        )

    def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get job status. Returns a unified status payload."""
        return _store.get_status(job_id)


__all__ = [
    "ThreadJobStore",
    "USE_CELERY",
    "REDIS_URL",
    "generate_insights",
    "generate_summary",
    "get_job_status",
    "run_analysis",
    "start_analysis_job",
]
        insights['positive'].append(
            f"Good content depth with average {int(avg_word_count)} words per page."
        )
    
    # Accessibility insights
    pages_with_good_accessibility = sum(
        1 for p in analyzed_pages 
        if p.get('accessibility', {}).get('score', 0) >= 80
    )
    if pages_with_good_accessibility > total_pages * 0.8:
        insights['positive'].append(
            f"{pages_with_good_accessibility} out of {total_pages} pages have good accessibility scores."
        )
    
    return insights


def generate_summary(analyzed_pages: list) -> Dict:
    """Generate summary statistics from analyzed pages."""
    if not analyzed_pages:
        return {}
    
    total_pages = len(analyzed_pages)
    total_images = sum(p.get('images', {}).get('count', 0) for p in analyzed_pages)
    images_without_alt = sum(p.get('images', {}).get('missing_alt_count', 0) for p in analyzed_pages)
    total_internal_links = sum(p.get('links', {}).get('total_internal', 0) for p in analyzed_pages)
    total_external_links = sum(p.get('links', {}).get('total_external', 0) for p in analyzed_pages)
    avg_word_count = int(sum(p.get('seo', {}).get('word_count', 0) 
                            for p in analyzed_pages) / total_pages) if total_pages > 0 else 0
    
    return {
        'total_pages_analyzed': total_pages,
        'total_images': total_images,
        'images_without_alt': images_without_alt,
        'total_internal_links': total_internal_links,
        'total_external_links': total_external_links,
        'broken_links_found': 0,  # Would need separate link checking
        'avg_word_count': avg_word_count
    }


@celery_app.task
def generate_report_task(site_analysis_id: int, report_type: str = 'html'):
    """
    Generate a report for a site analysis.
    
    Args:
        site_analysis_id: Database ID of SiteAnalysis record
        report_type: Type of report ('html', 'text', 'google_docs')
        
    Returns:
        Report content or document ID
    """
    from we_si.models import init_db, SiteAnalysis, PageAnalysis
    from we_si.reports.html_report import HTMLReportGenerator
    from we_si.reports.text_report import TextReportGenerator
    from we_si.reports.gdoc_report import GoogleDocsReportGenerator
    
    engine, Session = init_db()
    session = Session()
    
    try:
        # Get site analysis
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            raise ValueError(f"SiteAnalysis {site_analysis_id} not found")
        
        # Get pages
        pages = session.query(PageAnalysis).filter_by(site_analysis_id=site_analysis_id).all()
        
        # Build analysis data
        analysis_data = {
            'metadata': {
                'base_url': site_analysis.base_url,
                'domain': site_analysis.domain,
                'analysis_date': site_analysis.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'pages_crawled': site_analysis.pages_crawled
            },
            'summary': site_analysis.summary or {},
            'insights': site_analysis.insights or {},
            'pages': [page.analysis_data for page in pages if page.analysis_data]
        }
        
        # Generate report
        if report_type == 'html':
            generator = HTMLReportGenerator()
            return generator.generate(analysis_data)
        elif report_type == 'text':
            generator = TextReportGenerator()
            return generator.generate(analysis_data)
        elif report_type == 'google_docs':
            generator = GoogleDocsReportGenerator()
            doc_id = generator.generate(analysis_data)
            return generator.get_document_url(doc_id)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    finally:
        session.close()

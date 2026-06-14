from __future__ import annotations

import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from flask import (
    Flask,
    Response,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session as flask_session,
    url_for,
)
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

LOGGER = logging.getLogger(__name__)

INLINE_TEMPLATES = {
    "home.html": """
    <!doctype html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\">
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>SiteIQ</title>
      <style>
        body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;margin:0}
        .wrap{max-width:960px;margin:0 auto;padding:48px 20px}
        .card{background:#111827;border:1px solid #334155;border-radius:16px;padding:24px;margin-top:24px}
        input,textarea,button{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #475569;background:#020617;color:#e2e8f0}
        button{background:#2563eb;border:none;font-weight:700;cursor:pointer}
        a{color:#93c5fd} .muted{color:#94a3b8} .error{color:#fca5a5}
      </style>
    </head>
    <body>
      <div class=\"wrap\">
        <h1>SiteIQ</h1>
        <p>Analyze website structure, content quality, SEO signals, and actionable improvement opportunities.</p>
        {% if error %}<p class=\"error\">{{ error }}</p>{% endif %}
        <div class=\"card\">
          <form action=\"{{ url_for('analyze_page') }}\" method=\"get\">
            <label for=\"url\">Website URL</label>
            <input id=\"url\" name=\"url\" type=\"text\" required placeholder=\"example.com\" value=\"{{ request.args.get('url', '') }}\">
            <div style=\"height:12px\"></div>
            <label for=\"max_pages\">Max pages</label>
            <input id=\"max_pages\" name=\"max_pages\" type=\"number\" min=\"1\" max=\"500\" value=\"{{ max_pages_default }}\">
            <div style=\"height:12px\"></div>
            <label for=\"page_urls\">Specific page URLs (optional, one per line)</label>
            <textarea id=\"page_urls\" name=\"page_urls\" rows=\"5\" placeholder=\"https://example.com/about\nhttps://example.com/pricing\"></textarea>
            <div style=\"height:16px\"></div>
            <button type=\"submit\">Start analysis</button>
          </form>
        </div>
        <div class=\"card\">
          <h2>What SiteIQ checks</h2>
          <p class=\"muted\">SiteIQ reviews crawl coverage, SEO basics, accessibility issues, broken links, content depth, and improvement recommendations.</p>
          <p><a href=\"{{ url_for('settings_page') }}\">Settings</a></p>
        </div>
      </div>
    </body>
    </html>
    """,
    "dashboard.html": """
    <!doctype html>
    <html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>SiteIQ Dashboard</title>
    <style>
      body{font-family:system-ui,-apple-system,sans-serif;background:#f8fafc;color:#0f172a;margin:0}
      .wrap{max-width:1100px;margin:0 auto;padding:24px} .card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 2px rgba(0,0,0,.04)}
      .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}.pill{display:inline-block;padding:6px 10px;border-radius:999px;background:#dbeafe;color:#1d4ed8;font-weight:700}
      pre{white-space:pre-wrap;word-break:break-word;background:#0f172a;color:#e2e8f0;padding:16px;border-radius:12px;overflow:auto} a{color:#2563eb}
    </style></head><body><div class=\"wrap\">
      <p><a href=\"{{ url_for('home') }}\">← Home</a> · <a href=\"{{ url_for('settings_page') }}\">Settings</a></p>
      <h1>Analysis #{{ analysis_id }}</h1>
      <div id=\"summary\" class=\"card\">Loading...</div>
      <div id=\"scores\" class=\"card\"></div>
      <div id=\"recommendations\" class=\"card\"></div>
      <div class=\"card\"><h2>Report downloads</h2><p><a href=\"/api/analysis/{{ analysis_id }}/report/html\">HTML</a> · <a href=\"/api/analysis/{{ analysis_id }}/report/text\">Text</a> · <a href=\"/api/analysis/{{ analysis_id }}/report/json\">JSON</a></p></div>
      <div class=\"card\">
        <h2>Ask SiteIQ</h2>
        <form id=\"chat-form\"><input id=\"chat-input\" placeholder=\"What should I fix first?\" /><button>Send</button></form>
        <pre id=\"chat-output\"></pre>
      </div>
      <div class=\"card\"><h2>Raw analysis</h2><pre id=\"raw\"></pre></div>
    </div>
    <script>
      async function load(){
        const [analysisRes,scoresRes,recsRes]=await Promise.all([
          fetch('/api/analysis/{{ analysis_id }}'),fetch('/api/analysis/{{ analysis_id }}/scores'),fetch('/api/analysis/{{ analysis_id }}/recommendations')
        ]);
        const analysis=await analysisRes.json();
        const scores=await scoresRes.json();
        const recs=await recsRes.json();
        document.getElementById('summary').innerHTML=`<h2>${analysis.domain||analysis.metadata?.domain||'Unknown domain'}</h2><p><span class="pill">${analysis.status}</span></p><div class="grid"><div><strong>Pages crawled</strong><div>${analysis.pages_crawled ?? analysis.metadata?.pages_crawled ?? 0}</div></div><div><strong>Pages analyzed</strong><div>${analysis.pages_analyzed ?? analysis.summary?.total_pages_analyzed ?? 0}</div></div><div><strong>Progress</strong><div>${analysis.progress ?? 0}%</div></div></div>`;
        document.getElementById('scores').innerHTML=`<h2>Scores</h2><pre>${JSON.stringify(scores,null,2)}</pre>`;
        document.getElementById('recommendations').innerHTML=`<h2>Recommendations</h2><pre>${JSON.stringify(recs,null,2)}</pre>`;
        document.getElementById('raw').textContent=JSON.stringify(analysis,null,2);
      }
      document.getElementById('chat-form').addEventListener('submit', async (event)=>{
        event.preventDefault();
        const input=document.getElementById('chat-input');
        const output=document.getElementById('chat-output');
        const res=await fetch('/api/analysis/{{ analysis_id }}/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:input.value})});
        const data=await res.json();
        output.textContent=data.response || JSON.stringify(data,null,2);
        input.value='';
      });
      load();
    </script></body></html>
    """,
    "progress.html": """
    <!doctype html>
    <html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Analysis Progress</title>
    <style>body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;display:grid;place-items:center;min-height:100vh;margin:0}.card{width:min(680px,92vw);background:#111827;border:1px solid #334155;border-radius:16px;padding:24px}.bar{height:16px;background:#1e293b;border-radius:999px;overflow:hidden}.fill{height:100%;width:0;background:linear-gradient(90deg,#2563eb,#14b8a6)}a{color:#93c5fd}</style>
    </head><body><div class=\"card\"><p><a href=\"{{ url_for('home') }}\">← Home</a></p><h1>Analysis #{{ analysis_id }}</h1><p id=\"step\">Starting…</p><div class=\"bar\"><div id=\"fill\" class=\"fill\"></div></div><p id=\"meta\"></p></div>
    <script>
      const source=new EventSource('/api/analysis/{{ analysis_id }}/stream');
      source.onmessage=(event)=>{
        const data=JSON.parse(event.data);
        document.getElementById('step').textContent=data.current_step || data.status;
        document.getElementById('meta').textContent=`${data.status} · ${data.progress}%`;
        document.getElementById('fill').style.width=`${data.progress || 0}%`;
        if(data.status==='completed'){source.close(); window.location='/analysis/{{ analysis_id }}';}
        if(data.status==='failed'){source.close(); document.getElementById('step').textContent=data.error_message || 'Analysis failed';}
      };
    </script></body></html>
    """,
    "settings.html": """
    <!doctype html>
    <html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>SiteIQ Settings</title>
    <style>body{font-family:system-ui,-apple-system,sans-serif;background:#f8fafc;color:#0f172a;margin:0}.wrap{max-width:860px;margin:0 auto;padding:24px}.card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin:16px 0}input,button{width:100%;padding:12px;border-radius:10px;border:1px solid #cbd5e1}button{background:#2563eb;color:#fff;border:none;font-weight:700;margin-top:12px;cursor:pointer}ul{padding-left:20px}a{color:#2563eb}</style>
    </head><body><div class=\"wrap\"><p><a href=\"{{ url_for('home') }}\">← Home</a></p><h1>API Key Settings</h1><div class=\"card\"><p>{{ storage_mode_message }}</p><form id=\"key-form\"><input id=\"service\" placeholder=\"openai\" required><div style=\"height:12px\"></div><input id=\"api-key\" placeholder=\"API key\" required><button>Store API key</button></form></div><div class=\"card\"><h2>Stored services</h2><ul id=\"services\"></ul></div></div>
    <script>
      async function load(){const res=await fetch('/api/settings/api-keys'); const data=await res.json(); const ul=document.getElementById('services'); ul.innerHTML=''; (data.services||[]).forEach((service)=>{const li=document.createElement('li'); const btn=document.createElement('button'); btn.textContent='Delete'; btn.style.width='auto'; btn.style.marginLeft='8px'; btn.onclick=async()=>{await fetch('/api/settings/api-key/'+encodeURIComponent(service),{method:'DELETE'}); load();}; li.textContent=service; li.appendChild(btn); ul.appendChild(li);});}
      document.getElementById('key-form').addEventListener('submit', async (event)=>{event.preventDefault(); await fetch('/api/settings/api-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:document.getElementById('service').value, api_key:document.getElementById('api-key').value})}); document.getElementById('api-key').value=''; load();});
      load();
    </script></body></html>
    """,
}


class PlaintextSecretStore:
    """Development fallback for API-key storage when encryption is unavailable."""

    @staticmethod
    def store(service: str, api_key: str) -> None:
        api_keys = flask_session.get("plaintext_api_keys", {})
        api_keys[service] = api_key
        flask_session["plaintext_api_keys"] = api_keys
        flask_session.modified = True

    @staticmethod
    def list_services() -> List[str]:
        return sorted(flask_session.get("plaintext_api_keys", {}).keys())

    @staticmethod
    def get(service: str) -> Optional[str]:
        return flask_session.get("plaintext_api_keys", {}).get(service)

    @staticmethod
    def delete(service: str) -> bool:
        api_keys = flask_session.get("plaintext_api_keys", {})
        removed = service in api_keys
        if removed:
            api_keys.pop(service, None)
            flask_session["plaintext_api_keys"] = api_keys
            flask_session.modified = True
        return removed


def _setup_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _normalize_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("URL is required.")
    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be a valid http or https address.")
    return cleaned.rstrip("/")


def _load_json_config() -> Dict[str, Any]:
    config_path = Path.cwd() / "siteiq_config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive logging path
        LOGGER.warning("Failed to load %s: %s", config_path, exc)
        return {}


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_models() -> Dict[str, Any]:
    from we_si.models import (
        APIKey,
        AssistantConversation,
        AssistantMessage,
        Base,
        JobStatus,
        PageAnalysis,
        SiteAnalysis,
        Subscription,
        SubscriptionTier,
        User,
    )

    return {
        "APIKey": APIKey,
        "AssistantConversation": AssistantConversation,
        "AssistantMessage": AssistantMessage,
        "Base": Base,
        "JobStatus": JobStatus,
        "PageAnalysis": PageAnalysis,
        "SiteAnalysis": SiteAnalysis,
        "Subscription": Subscription,
        "SubscriptionTier": SubscriptionTier,
        "User": User,
    }


def get_or_create_demo_user(session) -> Any:
    """Get or create default demo user (id=1, email=demo@siteiq.local)."""
    models = _get_models()
    User = models["User"]
    Subscription = models["Subscription"]
    SubscriptionTier = models["SubscriptionTier"]

    user = session.query(User).filter((User.id == 1) | (User.email == "demo@siteiq.local")).first()
    if user is None:
        user = User(
            id=1,
            email="demo@siteiq.local",
            username="demo",
            password_hash="demo-user-no-auth",
        )
        session.add(user)
        session.flush()

    if user.subscription is None:
        limits = Subscription.get_tier_limits(SubscriptionTier.FREE)
        session.add(
            Subscription(
                user_id=user.id,
                tier=SubscriptionTier.FREE,
                max_pages_per_run=limits["max_pages_per_run"],
                max_pages_stored=limits["max_pages_stored"],
                max_analyses_per_month=limits["max_analyses_per_month"],
            )
        )
    session.commit()
    return user


def _demo_subscription_snapshot(session) -> Dict[str, Any]:
    models = _get_models()
    SiteAnalysis = models["SiteAnalysis"]
    user = get_or_create_demo_user(session)
    subscription = user.subscription
    if subscription is None:
        return {
            "tier_name": "Free",
            "max_pages_per_run": 10,
            "max_analyses_per_month": 5,
            "analyses_remaining": 5,
        }

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    analyses_this_month = (
        session.query(SiteAnalysis)
        .filter(SiteAnalysis.user_id == user.id, SiteAnalysis.created_at >= month_start)
        .count()
    )
    remaining = max(0, int(subscription.max_analyses_per_month or 0) - analyses_this_month)
    return {
        "tier_name": str(subscription.tier.value).capitalize(),
        "max_pages_per_run": int(subscription.max_pages_per_run or 0),
        "max_analyses_per_month": int(subscription.max_analyses_per_month or 0),
        "analyses_remaining": remaining,
    }


def _db_session():
    if "db_session" not in g:
        g.db_session = current_app.extensions["db_session_factory"]()
    return g.db_session


def _teardown_session(_exception: Optional[BaseException] = None) -> None:
    session = g.pop("db_session", None)
    if session is not None:
        session.close()


def _template_path(app: Flask, template_name: str) -> Path:
    return (Path(app.root_path) / app.template_folder / template_name).resolve()


def _render_page(template_name: str, **context: Any) -> str:
    app = current_app
    template_file = _template_path(app, template_name)
    if template_file.exists():
        return render_template(template_name, **context)
    return render_template_string(INLINE_TEMPLATES[template_name], **context)


def _json_error(message: str, status_code: int = 400, **extra: Any):
    payload = {"error": message}
    payload.update(extra)
    return jsonify(payload), status_code


def _analysis_report_ready(analysis: Any) -> bool:
    return bool(analysis.summary or analysis.insights or analysis.pages)


def _page_payload(page: Any) -> Dict[str, Any]:
    base_payload = page.analysis_data.copy() if isinstance(page.analysis_data, dict) else {}
    base_payload.setdefault("id", page.id)
    base_payload.setdefault("url", page.url)
    base_payload.setdefault("status_code", page.status_code)
    base_payload.setdefault("depth", page.depth)
    base_payload.setdefault("load_time", page.load_time)
    base_payload.setdefault("created_at", page.created_at)
    return {key: _json_default(value) if isinstance(value, (datetime, Enum)) else value for key, value in base_payload.items()}


def _analysis_payload(analysis: Any) -> Dict[str, Any]:
    metadata = {
        "base_url": analysis.base_url,
        "domain": analysis.domain,
        "analysis_date": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "pages_crawled": analysis.pages_crawled,
    }
    payload = {
        "id": analysis.id,
        "user_id": analysis.user_id,
        "base_url": analysis.base_url,
        "domain": analysis.domain,
        "status": _json_default(analysis.status),
        "progress": round(float(analysis.progress or 0.0), 2),
        "pages_crawled": analysis.pages_crawled,
        "pages_analyzed": analysis.pages_analyzed,
        "error_message": analysis.error_message,
        "created_at": _json_default(analysis.created_at),
        "started_at": _json_default(analysis.started_at) if analysis.started_at else None,
        "completed_at": _json_default(analysis.completed_at) if analysis.completed_at else None,
        "metadata": metadata,
        "summary": analysis.summary or {},
        "insights": analysis.insights or {},
        "pages": [_page_payload(page) for page in analysis.pages],
        "conversations": [
            {
                "id": conversation.id,
                "created_at": _json_default(conversation.created_at),
                "messages": [
                    {
                        "id": message.id,
                        "role": message.role,
                        "content": message.content,
                        "created_at": _json_default(message.created_at),
                    }
                    for message in conversation.messages
                ],
            }
            for conversation in analysis.conversations
        ],
    }
    if payload["summary"]:
        payload["metadata"]["analysis_date"] = payload["metadata"]["analysis_date"] or payload["created_at"]
    return payload


def _fallback_scores(report: Dict[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary", {})
    insights = report.get("insights", {})
    critical = len(insights.get("critical", []))
    warnings = len(insights.get("warnings", []))
    recommendations = len(insights.get("recommendations", []))
    total_images = max(1, int(summary.get("total_images", 0) or 0))
    images_without_alt = int(summary.get("images_without_alt", 0) or 0)
    broken_links = int(summary.get("broken_links_found", 0) or 0)
    avg_word_count = int(summary.get("avg_word_count", 0) or 0)
    external_links = int(summary.get("total_external_links", 0) or 0)

    seo = max(0, 100 - (critical * 15) - (warnings * 6) - (0 if avg_word_count >= 300 else min(20, (300 - avg_word_count) // 15)))
    accessibility = max(0, 100 - int((images_without_alt / total_images) * 45) - (10 if warnings else 0))
    content = max(0, 100 - (15 if avg_word_count < 300 else 0) - min(25, recommendations * 5))
    technical = max(0, 100 - (broken_links * 12) - (critical * 8))
    authority = min(100, 40 + external_links * 3)
    overall = round((seo + accessibility + content + technical + authority) / 5)

    return {
        "overall": overall,
        "seo": seo,
        "accessibility": accessibility,
        "content": content,
        "technical": technical,
        "authority": authority,
        "method": "fallback",
    }


def _site_meta_from_report(report: Dict[str, Any]) -> Dict[str, Any]:
    metadata = report.get("metadata", {}) or {}
    summary = report.get("summary", {}) or {}
    return {
        "base_url": metadata.get("base_url"),
        "domain": metadata.get("domain"),
        "pages_crawled": metadata.get("pages_crawled", summary.get("total_pages_analyzed", 0)),
        "pages_analyzed": summary.get("total_pages_analyzed", 0),
    }



def _generate_scores(report: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from we_si.scoring import SiteIQScorer  # type: ignore

        scorer = SiteIQScorer()
        pages = report.get("pages", []) or []
        result = scorer.score_site(pages, _site_meta_from_report(report))
        if isinstance(result, dict):
            return result
    except ImportError:
        LOGGER.info("SiteIQScorer not available; using fallback scoring.")
    except Exception as exc:
        LOGGER.warning("SiteIQScorer failed; using fallback scoring: %s", exc)
    return _fallback_scores(report)


def _fallback_recommendations(report: Dict[str, Any]) -> Dict[str, Any]:
    insights = report.get("insights", {})
    items: List[Dict[str, Any]] = []
    for priority, category in (("critical", "technical"), ("high", "seo"), ("medium", "content")):
        source_items: Iterable[str]
        if priority == "critical":
            source_items = insights.get("critical", [])
        elif priority == "high":
            source_items = insights.get("warnings", [])
        else:
            source_items = insights.get("recommendations", [])
        for text_value in source_items:
            items.append({"priority": priority, "category": category, "recommendation": text_value})
    return {"count": len(items), "items": items, "method": "fallback"}


def _generate_recommendations(report: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from we_si.recommendations import RecommendationEngine  # type: ignore

        engine = RecommendationEngine()
        pages = report.get("pages", []) or []
        scores = _generate_scores(report)
        result = engine.generate(pages, scores, _site_meta_from_report(report))
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            return {"count": len(result), "items": result}
    except ImportError:
        LOGGER.info("RecommendationEngine not available; using fallback recommendations.")
    except Exception as exc:
        LOGGER.warning("RecommendationEngine failed; using fallback recommendations: %s", exc)
    return _fallback_recommendations(report)


def _authority_context(report: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from we_si.authority import AuthorityManager  # type: ignore

        manager = AuthorityManager()
        for method_name in ("analyze", "score", "evaluate"):
            method = getattr(manager, method_name, None)
            if callable(method):
                result = method(report)
                if isinstance(result, dict):
                    return result
    except ImportError:
        LOGGER.info("AuthorityManager not available; skipping authority enrichment.")
    except Exception as exc:
        LOGGER.warning("AuthorityManager failed; skipping authority enrichment: %s", exc)
    return {"status": "unavailable"}


def _fallback_chat_response(message: str, report: Dict[str, Any]) -> str:
    lowered = message.lower()
    scores = _fallback_scores(report)
    recommendations = _fallback_recommendations(report)["items"][:3]
    insights = report.get("insights", {})
    if "score" in lowered:
        return f"Overall score: {scores['overall']}/100. SEO {scores['seo']}, accessibility {scores['accessibility']}, content {scores['content']}, technical {scores['technical']}."
    if "recommend" in lowered or "fix" in lowered or "priority" in lowered:
        if not recommendations:
            return "No major recommendations are available yet."
        return "Top priorities: " + " | ".join(item["recommendation"] for item in recommendations)
    summary = report.get("summary", {})
    return (
        f"SiteIQ analyzed {summary.get('total_pages_analyzed', 0)} page(s). "
        f"It found {len(insights.get('critical', []))} critical issues and {len(insights.get('warnings', []))} warnings. "
        f"First action: {(recommendations[0]['recommendation'] if recommendations else 'review the full report for next steps.')}"
    )


def _chat_with_assistant(message: str, report: Dict[str, Any], conversation: List[Dict[str, str]], api_key: Optional[str]) -> str:
    try:
        from we_si.ai.providers import AIAssistant  # type: ignore

        assistant = AIAssistant()
        result = assistant.chat(message, conversation, report)
        if isinstance(result, dict) and result.get("response"):
            return str(result["response"])
        if isinstance(result, str):
            return result
    except ImportError:
        LOGGER.info("AIAssistant not available; using fallback chat.")
    except Exception as exc:
        LOGGER.warning("AIAssistant failed; using fallback chat: %s", exc)
    return _fallback_chat_response(message, report)


def _job_state(app: Flask, job_id: str) -> Optional[Dict[str, Any]]:
    with app.extensions["job_lock"]:
        job = app.extensions["job_registry"].get(job_id)
        return dict(job) if job else None


def _update_job(app: Flask, job_id: str, **updates: Any) -> None:
    with app.extensions["job_lock"]:
        job = app.extensions["job_registry"].setdefault(job_id, {})
        job.update(updates)
        job["updated_at"] = time.time()


def _store_analysis_job(app: Flask, analysis_id: int, job_id: str) -> None:
    app.extensions["analysis_jobs"][analysis_id] = job_id


def _lookup_analysis_job(app: Flask, analysis_id: int) -> Optional[str]:
    return app.extensions["analysis_jobs"].get(analysis_id)


def _fallback_job_status(app: Flask, job_id: str) -> Optional[Dict[str, Any]]:
    return _job_state(app, job_id)


def _update_analysis_progress(session, analysis: Any, status: Any, progress: float, current_step: str, error_message: Optional[str] = None) -> None:
    analysis.status = status
    analysis.progress = progress
    if error_message is not None:
        analysis.error_message = error_message
    if status.value == "running" and analysis.started_at is None:
        analysis.started_at = datetime.utcnow()
    if status.value == "completed":
        analysis.completed_at = datetime.utcnow()
    session.commit()


def _run_fallback_analysis(app: Flask, job_id: str, analysis_id: int, base_url: str, user_id: int, max_pages: int, max_depth: int) -> None:
    session_factory = app.extensions["db_session_factory"]
    session = session_factory()
    models = _get_models()
    SiteAnalysis = models["SiteAnalysis"]
    PageAnalysis = models["PageAnalysis"]
    JobStatus = models["JobStatus"]

    try:
        from wesi import WebsiteAnalyzer

        analysis = session.query(SiteAnalysis).filter_by(id=analysis_id).first()
        if analysis is None:
            raise ValueError(f"Analysis {analysis_id} was not found.")

        _update_job(app, job_id, status="running", progress=5.0, current_step="Initializing analysis")
        _update_analysis_progress(session, analysis, JobStatus.RUNNING, 5.0, "Initializing analysis")

        analyzer = WebsiteAnalyzer(base_url, max_pages=max_pages)
        to_visit = [analyzer.base_url]
        depth_by_url = {analyzer.base_url: 0}

        while to_visit and len(analyzer.visited_urls) < max_pages:
            url = to_visit.pop(0)
            normalized = analyzer.normalize_url(url)
            depth = depth_by_url.get(normalized, 0)
            if normalized in analyzer.visited_urls or depth > max_depth:
                continue

            analyzer.visited_urls.add(normalized)
            progress = min(85.0, 10.0 + (len(analyzer.visited_urls) / max_pages) * 70.0)
            step = f"Analyzing {normalized}"
            _update_job(app, job_id, status="running", progress=round(progress, 2), current_step=step)

            started = time.time()
            page_data = analyzer.analyze_page(normalized, verbose=False)
            load_time = round(time.time() - started, 3)
            analyzer.pages_data.append(page_data)

            page_record = PageAnalysis(
                site_analysis_id=analysis.id,
                url=normalized,
                status_code=page_data.get("status_code"),
                depth=depth,
                load_time=load_time,
                analysis_data=page_data,
            )
            session.add(page_record)
            analysis.pages_crawled = len(analyzer.visited_urls)
            analysis.pages_analyzed = len(analyzer.pages_data)
            analysis.progress = round(progress, 2)
            session.commit()

            if "error" not in page_data:
                for link in page_data.get("links", {}).get("internal", []):
                    link_url = analyzer.normalize_url(link.get("absolute_url", "") or link.get("href", ""))
                    if not link_url:
                        continue
                    if link_url in analyzer.visited_urls or link_url in to_visit:
                        continue
                    next_depth = depth + 1
                    if next_depth <= max_depth:
                        depth_by_url[link_url] = next_depth
                        to_visit.append(link_url)
            time.sleep(0.5)

        report = analyzer.generate_report()
        analysis.summary = report.get("summary", {})
        analysis.insights = report.get("insights", {})
        analysis.pages_crawled = report.get("metadata", {}).get("pages_crawled", analysis.pages_crawled)
        analysis.pages_analyzed = report.get("summary", {}).get("total_pages_analyzed", analysis.pages_analyzed)
        analysis.progress = 100.0
        analysis.status = JobStatus.COMPLETED
        analysis.completed_at = datetime.utcnow()
        session.commit()
        _update_job(app, job_id, status="completed", progress=100.0, current_step="Analysis complete", analysis_id=analysis.id)
    except Exception as exc:
        LOGGER.exception("Analysis job %s failed", job_id)
        analysis = session.query(SiteAnalysis).filter_by(id=analysis_id).first()
        if analysis is not None:
            analysis.status = JobStatus.FAILED
            analysis.error_message = str(exc)
            analysis.completed_at = datetime.utcnow()
            session.commit()
        _update_job(app, job_id, status="failed", progress=100.0, current_step="Analysis failed", error_message=str(exc))
    finally:
        session.close()


def _start_fallback_analysis_job(app: Flask, site_analysis_id: int, base_url: str, user_id: int, max_pages: int, max_depth: int) -> str:
    job_id = secrets.token_urlsafe(12)
    _update_job(app, job_id, status="pending", progress=0.0, current_step="Queued", analysis_id=site_analysis_id)
    _store_analysis_job(app, site_analysis_id, job_id)
    thread = threading.Thread(
        target=_run_fallback_analysis,
        args=(app, job_id, site_analysis_id, base_url, user_id, max_pages, max_depth),
        daemon=True,
        name=f"siteiq-analysis-{site_analysis_id}",
    )
    thread.start()
    return job_id


def _start_analysis_job(app: Flask, site_analysis_id: int, base_url: str, user_id: int, max_pages: int, max_depth: int) -> str:
    try:
        from we_si.tasks import start_analysis_job  # type: ignore

        job_id = str(start_analysis_job(site_analysis_id, base_url, user_id, max_pages, max_depth))
        _store_analysis_job(app, site_analysis_id, job_id)
        return job_id
    except ImportError:
        LOGGER.info("we_si.tasks not available; using fallback threaded jobs.")
        return _start_fallback_analysis_job(app, site_analysis_id, base_url, user_id, max_pages, max_depth)
    except Exception as exc:
        LOGGER.warning("Task backend failed; using fallback threaded jobs: %s", exc)
        return _start_fallback_analysis_job(app, site_analysis_id, base_url, user_id, max_pages, max_depth)


def _get_job_status(app: Flask, job_id: str) -> Optional[Dict[str, Any]]:
    try:
        from we_si.tasks import get_job_status  # type: ignore

        result = get_job_status(job_id)
        if isinstance(result, dict):
            return result
    except ImportError:
        pass
    except Exception as exc:
        LOGGER.warning("Primary job status backend failed for %s: %s", job_id, exc)
    return _fallback_job_status(app, job_id)


def _load_secret_backend(app: Flask):
    encryption_key = app.config.get("WESI_ENCRYPTION_KEY")
    if not encryption_key:
        LOGGER.warning("WESI_ENCRYPTION_KEY is not set; API keys will be stored in plaintext session cookies for development use.")
        return None
    try:
        from we_si.storage.secrets import SecretManager

        return SecretManager(encryption_key)
    except ImportError:
        LOGGER.warning("SecretManager unavailable; API keys will be stored in plaintext session cookies.")
    except Exception as exc:
        LOGGER.warning("SecretManager setup failed (%s); using plaintext session storage.", exc)
    return None


def _store_api_key_for_demo_user(service: str, api_key: str) -> Dict[str, Any]:
    service_name = service.strip().lower()
    api_key_trimmed = api_key.strip()
    if not service_name:
        raise ValueError("service is required and cannot be empty")
    if not api_key_trimmed:
        raise ValueError("api_key is required and cannot be empty")

    app = current_app
    secret_manager = app.extensions.get("secret_manager")
    if secret_manager is None:
        PlaintextSecretStore.store(service_name, api_key_trimmed)
        return {
            "success": True,
            "service": service_name,
            "storage_mode": "plaintext-session",
            "message": f"API key for {service_name} saved (session storage)",
        }

    try:
        secret_module = __import__("we_si.storage.secrets", fromlist=["store_api_key"])
        session = _db_session()
        user = get_or_create_demo_user(session)
        secret_module.store_api_key(session, user.id, service_name, api_key_trimmed, secret_manager)
        return {
            "success": True,
            "service": service_name,
            "storage_mode": "encrypted-db",
            "message": f"API key for {service_name} saved (encrypted)",
        }
    except Exception as exc:
        LOGGER.warning("Encrypted storage failed, falling back to session: %s", exc)
        PlaintextSecretStore.store(service_name, api_key_trimmed)
        return {
            "success": True,
            "service": service_name,
            "storage_mode": "plaintext-session",
            "message": f"API key for {service_name} saved (session fallback)",
        }


def _get_provider_preference() -> str:
    return (flask_session.get("ai_provider") or "auto").strip().lower() or "auto"


def _set_provider_preference(provider: str) -> Dict[str, Any]:
    provider_name = (provider or "").strip().lower()
    allowed_providers = {"auto", "openai", "anthropic", "gemini", "google", "ollama", "none"}
    if provider_name not in allowed_providers:
        raise ValueError(f"ai_provider must be one of {sorted(allowed_providers)}")
    flask_session["ai_provider"] = provider_name
    flask_session.modified = True
    return {"success": True, "ai_provider": provider_name}


def _list_api_key_services_for_demo_user() -> Dict[str, Any]:
    app = current_app
    secret_manager = app.extensions.get("secret_manager")
    if secret_manager is None:
        return {"services": PlaintextSecretStore.list_services(), "storage_mode": "plaintext-session"}

    secret_module = __import__("we_si.storage.secrets", fromlist=["list_api_key_services"])
    session = _db_session()
    user = get_or_create_demo_user(session)
    return {"services": sorted(secret_module.list_api_key_services(session, user.id)), "storage_mode": "encrypted-db"}


def _delete_api_key_for_demo_user(service: str) -> Dict[str, Any]:
    app = current_app
    service_name = service.strip().lower()
    secret_manager = app.extensions.get("secret_manager")
    if secret_manager is None:
        deleted = PlaintextSecretStore.delete(service_name)
        return {"deleted": deleted, "service": service_name, "storage_mode": "plaintext-session"}

    secret_module = __import__("we_si.storage.secrets", fromlist=["delete_api_key"])
    session = _db_session()
    user = get_or_create_demo_user(session)
    deleted = bool(secret_module.delete_api_key(session, user.id, service_name))
    return {"deleted": deleted, "service": service_name, "storage_mode": "encrypted-db"}


def _lookup_api_key(service: str) -> Optional[str]:
    app = current_app
    service_name = service.strip().lower()
    secret_manager = app.extensions.get("secret_manager")
    if secret_manager is None:
        return PlaintextSecretStore.get(service_name)

    secret_module = __import__("we_si.storage.secrets", fromlist=["get_api_key"])
    session = _db_session()
    user = get_or_create_demo_user(session)
    return secret_module.get_api_key(session, user.id, service_name, secret_manager)


def _settings_payload() -> Dict[str, Any]:
    key_data = _list_api_key_services_for_demo_user()
    services = key_data.get("services", []) or []
    return {
        **key_data,
        "stored_keys": {service: True for service in services},
        "ai_provider": _get_provider_preference(),
    }


def _build_report_for_analysis(analysis: Any) -> Dict[str, Any]:
    payload = _analysis_payload(analysis)
    return {
        "metadata": payload.get("metadata", {}),
        "summary": payload.get("summary", {}),
        "insights": payload.get("insights", {}),
        "pages": payload.get("pages", []),
    }


def _create_analysis_record(base_url: str, max_pages: int, max_depth: int, focus_url: Optional[str] = None) -> Dict[str, Any]:
    models = _get_models()
    SiteAnalysis = models["SiteAnalysis"]
    JobStatus = models["JobStatus"]
    session = _db_session()
    user = get_or_create_demo_user(session)
    parsed = urlparse(base_url)

    analysis = SiteAnalysis(
        user_id=user.id,
        base_url=base_url,
        domain=parsed.netloc,
        status=JobStatus.PENDING,
        progress=0.0,
        summary={
            "requested_max_pages": max_pages,
            "requested_max_depth": max_depth,
            **({"requested_focus_url": focus_url} if focus_url else {}),
        },
        insights={},
    )
    session.add(analysis)
    session.commit()
    return {"analysis": analysis, "user": user}


def create_app(config: dict = None) -> Flask:
    app = Flask(__name__, template_folder="../templates")
    CORS(app)
    _setup_logging()

    defaults = {
        "DATABASE_URL": "sqlite:///siteiq.db",
        "FLASK_SECRET_KEY": secrets.token_urlsafe(32),
        "WESI_ENCRYPTION_KEY": None,
        "MAX_PAGES_DEFAULT": 50,
        "MAX_DEPTH_DEFAULT": 3,
    }
    file_config = _load_json_config()
    env_config = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "FLASK_SECRET_KEY": os.getenv("FLASK_SECRET_KEY"),
        "WESI_ENCRYPTION_KEY": os.getenv("WESI_ENCRYPTION_KEY"),
        "MAX_PAGES_DEFAULT": os.getenv("MAX_PAGES_DEFAULT"),
        "MAX_DEPTH_DEFAULT": os.getenv("MAX_DEPTH_DEFAULT"),
    }

    final_config = defaults.copy()
    final_config.update({k: v for k, v in file_config.items() if v is not None})
    final_config.update({k: v for k, v in env_config.items() if v not in (None, "")})
    if config:
        final_config.update(config)

    final_config["MAX_PAGES_DEFAULT"] = _safe_int(final_config.get("MAX_PAGES_DEFAULT"), 50)
    final_config["MAX_DEPTH_DEFAULT"] = _safe_int(final_config.get("MAX_DEPTH_DEFAULT"), 3)
    app.config.update(final_config)
    app.secret_key = app.config["FLASK_SECRET_KEY"]
    os.environ["DATABASE_URL"] = str(app.config["DATABASE_URL"])
    if app.config.get("WESI_ENCRYPTION_KEY"):
        os.environ["WESI_ENCRYPTION_KEY"] = str(app.config["WESI_ENCRYPTION_KEY"])

    models = _get_models()
    Base = models["Base"]
    database_url = app.config["DATABASE_URL"]
    engine_kwargs = {"echo": False}
    if str(database_url).startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **engine_kwargs)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app.extensions["db_engine"] = engine
    app.extensions["db_session_factory"] = session_factory
    app.extensions["job_registry"] = {}
    app.extensions["analysis_jobs"] = {}
    app.extensions["job_lock"] = threading.Lock()
    app.extensions["secret_manager"] = _load_secret_backend(app)

    with app.app_context():
        setup_session = session_factory()
        try:
            get_or_create_demo_user(setup_session)
        finally:
            setup_session.close()

    app.teardown_appcontext(_teardown_session)

    @app.route("/health")
    def health() -> Any:
        try:
            _db_session().execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            LOGGER.exception("Health check database failure")
            return jsonify({"status": "error", "database": "error"}), 500
        return jsonify(
            {
                "status": "ok",
                "database": db_status,
                "secret_storage": "encrypted-db" if app.extensions.get("secret_manager") else "plaintext-session",
            }
        )

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze() -> Any:
        payload = request.get_json(silent=True) or {}
        try:
            base_url = _normalize_url(payload.get("url", ""))
            max_pages = _safe_int(payload.get("max_pages"), app.config["MAX_PAGES_DEFAULT"])
            if max_pages <= 0:
                raise ValueError("max_pages must be a positive integer.")
            max_depth = _safe_int(payload.get("max_depth"), app.config["MAX_DEPTH_DEFAULT"])
            if max_depth <= 0:
                raise ValueError("max_depth must be a positive integer.")
            focus_url = (payload.get("focus_url") or "").strip()
            if focus_url:
                focus_url = _normalize_url(focus_url)
            created = _create_analysis_record(base_url, max_pages, max_depth, focus_url=focus_url or None)
            analysis = created["analysis"]
            user = created["user"]
            job_id = _start_analysis_job(app, analysis.id, base_url, user.id, max_pages, max_depth)
            return jsonify({"job_id": job_id, "analysis_id": analysis.id}), 202
        except ValueError as exc:
            return _json_error(str(exc), 400)
        except Exception as exc:
            LOGGER.exception("Failed to start analysis")
            return _json_error("Failed to start analysis.", 500, detail=str(exc))

    @app.route("/api/status/<job_id>")
    def api_status(job_id: str) -> Any:
        try:
            status = _get_job_status(app, job_id)
            if not status:
                return _json_error("Job not found.", 404)
            return jsonify(
                {
                    "status": status.get("status", "unknown"),
                    "progress": round(float(status.get("progress", 0.0)), 2),
                    "current_step": status.get("current_step", "Waiting"),
                    "error_message": status.get("error_message") or status.get("error"),
                }
            )
        except Exception as exc:
            LOGGER.exception("Failed to fetch job status")
            return _json_error("Failed to fetch job status.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>")
    def api_analysis(analysis_id: int) -> Any:
        try:
            models_local = _get_models()
            SiteAnalysis = models_local["SiteAnalysis"]
            analysis = _db_session().query(SiteAnalysis).filter_by(id=analysis_id).first()
            if analysis is None:
                return _json_error("Analysis not found.", 404)
            return jsonify(_analysis_payload(analysis))
        except Exception as exc:
            LOGGER.exception("Failed to fetch analysis %s", analysis_id)
            return _json_error("Failed to fetch analysis.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>/pages")
    def api_analysis_pages(analysis_id: int) -> Any:
        try:
            SiteAnalysis = _get_models()["SiteAnalysis"]
            analysis = _db_session().query(SiteAnalysis).filter_by(id=analysis_id).first()
            if analysis is None:
                return _json_error("Analysis not found.", 404)
            pages = [_page_payload(page) for page in analysis.pages]
            return jsonify({"analysis_id": analysis_id, "total_pages": len(pages), "pages": pages})
        except Exception as exc:
            LOGGER.exception("Failed to fetch pages for analysis %s", analysis_id)
            return _json_error("Failed to fetch pages.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>/scores")
    def api_analysis_scores(analysis_id: int) -> Any:
        try:
            SiteAnalysis = _get_models()["SiteAnalysis"]
            analysis = _db_session().query(SiteAnalysis).filter_by(id=analysis_id).first()
            if analysis is None:
                return _json_error("Analysis not found.", 404)
            if not _analysis_report_ready(analysis):
                return _json_error("Analysis results are not ready yet.", 409)
            report = _build_report_for_analysis(analysis)
            scores = _generate_scores(report)
            scores["authority_context"] = _authority_context(report)
            return jsonify(scores)
        except Exception as exc:
            LOGGER.exception("Failed to fetch scores for %s", analysis_id)
            return _json_error("Failed to fetch scores.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>/recommendations")
    def api_analysis_recommendations(analysis_id: int) -> Any:
        try:
            SiteAnalysis = _get_models()["SiteAnalysis"]
            analysis = _db_session().query(SiteAnalysis).filter_by(id=analysis_id).first()
            if analysis is None:
                return _json_error("Analysis not found.", 404)
            if not _analysis_report_ready(analysis):
                return _json_error("Analysis results are not ready yet.", 409)
            return jsonify(_generate_recommendations(_build_report_for_analysis(analysis)))
        except Exception as exc:
            LOGGER.exception("Failed to fetch recommendations for %s", analysis_id)
            return _json_error("Failed to fetch recommendations.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>/report/<report_type>")
    def api_analysis_report(analysis_id: int, report_type: str) -> Any:
        try:
            SiteAnalysis = _get_models()["SiteAnalysis"]
            analysis = _db_session().query(SiteAnalysis).filter_by(id=analysis_id).first()
            if analysis is None:
                return _json_error("Analysis not found.", 404)
            if not _analysis_report_ready(analysis):
                return _json_error("Analysis results are not ready yet.", 409)
            report = _build_report_for_analysis(analysis)
            filename_base = f"siteiq-analysis-{analysis_id}"
            if report_type == "json":
                response = Response(json.dumps(report, indent=2, default=_json_default), mimetype="application/json")
                response.headers["Content-Disposition"] = f"attachment; filename={filename_base}.json"
                return response
            if report_type == "html":
                generator_module = __import__("we_si.reports.html_report", fromlist=["HTMLReportGenerator"])
                body = generator_module.HTMLReportGenerator().generate(report)
                response = Response(body, mimetype="text/html")
                response.headers["Content-Disposition"] = f"attachment; filename={filename_base}.html"
                return response
            if report_type == "text":
                generator_module = __import__("we_si.reports.text_report", fromlist=["TextReportGenerator"])
                body = generator_module.TextReportGenerator().generate(report, include_pages=True)
                response = Response(body, mimetype="text/plain")
                response.headers["Content-Disposition"] = f"attachment; filename={filename_base}.txt"
                return response
            return _json_error("Unsupported report type. Use html, text, or json.", 400)
        except ImportError as exc:
            LOGGER.exception("Report generator import failed")
            return _json_error("Requested report generator is unavailable.", 500, detail=str(exc))
        except Exception as exc:
            LOGGER.exception("Failed to generate report for %s", analysis_id)
            return _json_error("Failed to generate report.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>/chat", methods=["POST"])
    def api_analysis_chat(analysis_id: int) -> Any:
        try:
            payload = request.get_json(silent=True) or {}
            message = (payload.get("message") or "").strip()
            if not message:
                return _json_error("message is required.", 400)

            models_local = _get_models()
            SiteAnalysis = models_local["SiteAnalysis"]
            AssistantConversation = models_local["AssistantConversation"]
            AssistantMessage = models_local["AssistantMessage"]

            db = _db_session()
            analysis = db.query(SiteAnalysis).filter_by(id=analysis_id).first()
            if analysis is None:
                return _json_error("Analysis not found.", 404)
            if not _analysis_report_ready(analysis):
                return _json_error("Analysis results are not ready yet.", 409)

            conversation_id = payload.get("conversation_id")
            conversation = None
            if conversation_id is not None:
                conversation = db.query(AssistantConversation).filter_by(id=conversation_id, site_analysis_id=analysis_id).first()
                if conversation is None:
                    return _json_error("Conversation not found for analysis.", 404)
            if conversation is None:
                conversation = AssistantConversation(site_analysis_id=analysis_id)
                db.add(conversation)
                db.flush()

            user_message = AssistantMessage(conversation_id=conversation.id, role="user", content=message)
            db.add(user_message)
            db.flush()

            history = [{"role": item.role, "content": item.content} for item in conversation.messages]
            api_key = _lookup_api_key("openai") or _lookup_api_key("anthropic")
            response_text = _chat_with_assistant(message, _build_report_for_analysis(analysis), history, api_key)
            assistant_message = AssistantMessage(conversation_id=conversation.id, role="assistant", content=response_text)
            db.add(assistant_message)
            db.commit()
            return jsonify({"response": response_text, "conversation_id": conversation.id})
        except Exception as exc:
            LOGGER.exception("Chat request failed for analysis %s", analysis_id)
            return _json_error("Failed to process chat request.", 500, detail=str(exc))

    @app.route("/api/analysis/<int:analysis_id>/stream")
    def api_analysis_stream(analysis_id: int) -> Any:
        def event_stream() -> Iterable[str]:
            SiteAnalysis = _get_models()["SiteAnalysis"]
            while True:
                db = app.extensions["db_session_factory"]()
                try:
                    analysis = db.query(SiteAnalysis).filter_by(id=analysis_id).first()
                    if analysis is None:
                        payload = {"status": "failed", "progress": 100.0, "current_step": "Analysis not found", "error_message": "Analysis not found"}
                        yield f"data: {json.dumps(payload)}\n\n"
                        return
                    job_id = _lookup_analysis_job(app, analysis_id)
                    status = _get_job_status(app, job_id) if job_id else None
                    if status:
                        payload = {
                            "status": status.get("status", "unknown"),
                            "progress": round(float(status.get("progress", 0.0)), 2),
                            "current_step": status.get("current_step", "Working"),
                            "error_message": status.get("error_message") or status.get("error") or analysis.error_message,
                        }
                    else:
                        payload = {
                            "status": _json_default(analysis.status),
                            "progress": round(float(analysis.progress or 0.0), 2),
                            "current_step": "Analysis complete" if _json_default(analysis.status) == "completed" else "Waiting for updates",
                            "error_message": analysis.error_message,
                        }
                    yield f"data: {json.dumps(payload)}\n\n"
                    if payload["status"] in {"completed", "failed"}:
                        return
                finally:
                    db.close()
                time.sleep(1)

        return Response(event_stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.route("/api/settings/api-key", methods=["POST"])
    def api_store_key() -> Any:
        payload = request.get_json(silent=True) or {}
        try:
            if (payload.get("setting") or "").strip().lower() == "ai_provider":
                result = _set_provider_preference(payload.get("value", ""))
                return jsonify(result)
            service = (payload.get("service") or "").strip().lower()
            api_key = (payload.get("api_key") or payload.get("value") or "").strip()
            result = _store_api_key_for_demo_user(service, api_key)
            return jsonify(result), 201
        except ValueError as exc:
            return _json_error(str(exc), 400)
        except Exception as exc:
            LOGGER.exception("Failed to store API key")
            return _json_error("Failed to store API key.", 500, detail=str(exc))

    @app.route("/api/settings")
    def api_settings() -> Any:
        try:
            return jsonify(_settings_payload())
        except Exception as exc:
            LOGGER.exception("Failed to fetch settings")
            return _json_error("Failed to fetch settings.", 500, detail=str(exc))

    @app.route("/api/settings/api-keys")
    def api_list_keys() -> Any:
        try:
            return jsonify(_settings_payload())
        except Exception as exc:
            LOGGER.exception("Failed to list API keys")
            return _json_error("Failed to list API keys.", 500, detail=str(exc))

    @app.route("/api/settings/provider", methods=["POST"])
    def api_set_provider() -> Any:
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(_set_provider_preference(payload.get("ai_provider", "")))
        except ValueError as exc:
            return _json_error(str(exc), 400)
        except Exception as exc:
            LOGGER.exception("Failed to store provider preference")
            return _json_error("Failed to store provider preference.", 500, detail=str(exc))

    @app.route("/api/settings/api-key/<service>", methods=["DELETE"])
    def api_delete_key(service: str) -> Any:
        try:
            result = _delete_api_key_for_demo_user(service)
            if not result["deleted"]:
                return _json_error("API key not found.", 404)
            return jsonify(result)
        except Exception as exc:
            LOGGER.exception("Failed to delete API key")
            return _json_error("Failed to delete API key.", 500, detail=str(exc))

    @app.route("/")
    def home() -> Any:
        plan = _demo_subscription_snapshot(_db_session())
        return _render_page(
            "index.html",
            error=request.args.get("error"),
            url=request.args.get("url", ""),
            max_pages_default=plan["max_pages_per_run"] or app.config["MAX_PAGES_DEFAULT"],
            max_depth_default=app.config["MAX_DEPTH_DEFAULT"],
            subscription_plan=plan,
        )

    @app.route("/analyze")
    def analyze_page() -> Any:
        url_value = request.args.get("url", "")
        if not url_value:
            return redirect(url_for("home"))
        try:
            base_url = _normalize_url(url_value)
            max_pages = _safe_int(request.args.get("max_pages"), app.config["MAX_PAGES_DEFAULT"])
            if max_pages <= 0:
                raise ValueError("max_pages must be a positive integer.")
            max_depth = app.config["MAX_DEPTH_DEFAULT"]
            created = _create_analysis_record(base_url, max_pages, max_depth)
            analysis = created["analysis"]
            user = created["user"]
            _start_analysis_job(app, analysis.id, base_url, user.id, max_pages, max_depth)
            return redirect(url_for("analysis_progress_page", analysis_id=analysis.id))
        except Exception as exc:
            LOGGER.exception("Failed to trigger analysis from web UI")
            return redirect(url_for("home", error=str(exc), url=url_value))

    @app.route("/analysis/<int:analysis_id>")
    def analysis_dashboard(analysis_id: int) -> Any:
        return _render_page("dashboard.html", analysis_id=analysis_id)

    @app.route("/analysis/<int:analysis_id>/progress")
    def analysis_progress_page(analysis_id: int) -> Any:
        return _render_page("progress.html", analysis_id=analysis_id)

    @app.route("/settings")
    def settings_page() -> Any:
        storage_mode_message = (
            "Encrypted database storage is enabled."
            if app.extensions.get("secret_manager")
            else "WESI_ENCRYPTION_KEY is not configured, so API keys are stored in plaintext session cookies for development."
        )
        return _render_page("settings.html", storage_mode_message=storage_mode_message)

    return app


app = create_app()


if __name__ == "__main__":
    _debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=_debug)

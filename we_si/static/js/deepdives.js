/**
 * deepdives.js — Collapse/expand logic for the three deep-dive sections.
 *
 * Each section has a <button class="deepdive-toggle"> and a sibling
 * <div class="deepdive-content">.  Clicking the button toggles `is-open`
 * on the content and updates `aria-expanded` for accessibility.
 *
 * Data is fetched lazily when a section is first opened.
 */

(() => {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Helpers                                                              */
    /* ------------------------------------------------------------------ */

    function escapeHtml(str) {
        return String(str ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async function fetchJson(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.error || body.message || `HTTP ${res.status}`);
        }
        return res.json();
    }

    function setStatus(sectionEl, statusText, cssClass) {
        const badge = sectionEl.querySelector('.deepdive-status-badge');
        if (!badge) return;
        badge.textContent = statusText;
        badge.className = `deepdive-status-badge ${cssClass}`;
    }

    function showSpinner(contentEl, message = 'Loading…') {
        contentEl.innerHTML = `
            <div class="deepdive-spinner">
                <div class="spinner-border text-secondary" role="status" aria-hidden="true"></div>
                <span>${escapeHtml(message)}</span>
            </div>`;
    }

    function showError(contentEl, message) {
        contentEl.innerHTML = `
            <div class="deepdive-notice">
                <span class="notice-icon">⚠️</span>
                <div><strong>Unable to load data.</strong><br>${escapeHtml(message)}</div>
            </div>`;
    }

    /* ------------------------------------------------------------------ */
    /* Toggle logic                                                         */
    /* ------------------------------------------------------------------ */

    function initToggle(toggleBtn) {
        const content = toggleBtn.closest('.deepdive-section')
            ?.querySelector('.deepdive-content');
        if (!content) return;

        let loaded = false;
        const sectionId = toggleBtn.closest('.deepdive-section')?.id || '';

        toggleBtn.addEventListener('click', () => {
            const isOpen = content.classList.toggle('is-open');
            toggleBtn.setAttribute('aria-expanded', String(isOpen));

            if (isOpen && !loaded) {
                loaded = true;
                lazyLoad(sectionId, toggleBtn.closest('.deepdive-section'), content);
            }
        });

        /* Keyboard: Space / Enter already fire click on <button>; also
           support arrow keys to move between toggles. */
        toggleBtn.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                const allToggles = Array.from(
                    document.querySelectorAll('.deepdive-toggle')
                );
                const idx = allToggles.indexOf(toggleBtn);
                const next = e.key === 'ArrowDown' ? idx + 1 : idx - 1;
                allToggles[next]?.focus();
                e.preventDefault();
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /* Lazy loaders — called once per section when first opened            */
    /* ------------------------------------------------------------------ */

    function lazyLoad(sectionId, sectionEl, contentEl) {
        const analysisId = window.__SITEIQ_ANALYSIS_ID__;
        if (!analysisId) return;

        if (sectionId === 'pagespeed-section') {
            loadPageSpeed(analysisId, sectionEl, contentEl);
        } else if (sectionId === 'schema-section') {
            loadSchema(analysisId, sectionEl, contentEl);
        } else if (sectionId === 'links-section') {
            loadLinkGraph(analysisId, sectionEl, contentEl);
        }
    }

    /* ------------------------------------------------------------------ */
    /* PageSpeed section                                                    */
    /* ------------------------------------------------------------------ */

    function ratingClass(rating) {
        return { good: 'good', 'needs-improvement': 'needs-improvement', poor: 'poor' }[rating] || 'unknown';
    }

    function metricCard(key, entry) {
        if (!entry) {
            return `<div class="cwv-card rating-unknown">
                <div class="cwv-value">—</div>
                <div class="cwv-label">${escapeHtml(key.toUpperCase())}</div>
                <span class="cwv-rating-pill unknown">no data</span>
            </div>`;
        }
        const rc = ratingClass(entry.rating || 'unknown');
        const displayValue = escapeHtml(entry.display || `${entry.value}${entry.unit === 'score' ? '' : ' ms'}`);
        return `<div class="cwv-card rating-${escapeHtml(rc)}">
            <div class="cwv-value">${displayValue}</div>
            <div class="cwv-label">${escapeHtml(key.toUpperCase())}</div>
            <span class="cwv-rating-pill ${escapeHtml(rc)}">${escapeHtml(rc.replace('-', ' '))}</span>
        </div>`;
    }

    async function loadPageSpeed(analysisId, sectionEl, contentEl) {
        showSpinner(contentEl, 'Fetching Core Web Vitals…');
        try {
            const data = await fetchJson(`/api/analysis/${encodeURIComponent(analysisId)}/pagespeed`);

            if (data.status === 'not_configured') {
                contentEl.innerHTML = `
                    <div class="deepdive-notice">
                        <span class="notice-icon">ℹ️</span>
                        <div>
                            <strong>PageSpeed API not configured.</strong><br>
                            Add a Google PageSpeed API key in <a href="/settings">Settings</a> (service name: <code>pagespeed</code>) to fetch live Core Web Vitals.
                            <br><small class="text-muted">${escapeHtml(data.reason || '')}</small>
                        </div>
                    </div>`;
                setStatus(sectionEl, 'not configured', 'status-pending');
                return;
            }

            const overallStatus = data.overall_status || 'pass';
            const statusMap = { pass: ['Pass', 'status-pass'], warning: ['Warning', 'status-warning'], fail: ['Fail', 'status-fail'] };
            const [statusLabel, statusCss] = statusMap[overallStatus] || ['—', 'status-pending'];
            setStatus(sectionEl, statusLabel, statusCss);

            const perfScore = data.performance_score != null
                ? `<div class="mb-3"><span class="fw-bold fs-5">${escapeHtml(String(data.performance_score))}</span> <span class="soft-label">/ 100 Performance Score</span></div>`
                : '';

            const suggestions = (data.suggestions || []).length
                ? `<div class="mt-3">
                    <h3 class="h6 mb-2">Suggestions</h3>
                    <ul class="small ps-3 mb-0">
                        ${data.suggestions.slice(0, 8).map((s) => `<li>${escapeHtml(s)}</li>`).join('')}
                    </ul>
                   </div>`
                : '';

            const refreshBtn = `<div class="mt-3 text-end">
                <button class="btn btn-outline-secondary btn-sm rounded-pill" id="psiRefreshBtn" type="button">↻ Refresh PageSpeed</button>
            </div>`;

            contentEl.innerHTML = `
                ${perfScore}
                <div class="cwv-grid">
                    ${metricCard('LCP', data.lcp)}
                    ${metricCard('CLS', data.cls)}
                    ${metricCard('INP', data.inp)}
                    ${metricCard('FCP', data.fcp)}
                    ${metricCard('TTFB', data.ttfb)}
                </div>
                ${suggestions}
                ${refreshBtn}`;

            contentEl.querySelector('#psiRefreshBtn')?.addEventListener('click', async () => {
                showSpinner(contentEl, 'Refreshing…');
                try {
                    await fetch(`/api/analysis/${encodeURIComponent(analysisId)}/pagespeed/refresh`, { method: 'POST' });
                    await loadPageSpeed(analysisId, sectionEl, contentEl);
                } catch (err) {
                    showError(contentEl, err.message);
                }
            });
        } catch (err) {
            showError(contentEl, err.message);
            setStatus(sectionEl, 'Error', 'status-fail');
        }
    }

    /* ------------------------------------------------------------------ */
    /* Schema section                                                       */
    /* ------------------------------------------------------------------ */

    async function loadSchema(analysisId, sectionEl, contentEl) {
        showSpinner(contentEl, 'Auditing structured data…');
        try {
            const data = await fetchJson(`/api/analysis/${encodeURIComponent(analysisId)}/schema`);

            const foundCount = (data.found_types || []).length;
            const recCount = (data.recommendations || []).length;
            const issueCount = (data.issues || []).length;

            const statusLabel = issueCount > 0 ? `${issueCount} issue${issueCount !== 1 ? 's' : ''}` : (recCount > 0 ? `${recCount} missing` : 'All good');
            const statusCss = issueCount > 0 ? 'status-fail' : (recCount > 0 ? 'status-warning' : 'status-pass');
            setStatus(sectionEl, statusLabel, statusCss);

            const foundHtml = foundCount
                ? (data.found_types || []).map((t) => `<span class="schema-chip found me-1 mb-1">✓ ${escapeHtml(t)}</span>`).join('')
                : '<span class="text-muted small">No schema markup found on crawled pages.</span>';

            const issuesHtml = issueCount
                ? `<div class="mt-3">
                    <h3 class="h6 mb-2 text-danger">Validation Issues</h3>
                    <ul class="small ps-3 mb-0">${(data.issues || []).map((i) => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
                   </div>`
                : '';

            const recsHtml = recCount
                ? `<div class="mt-3">
                    <h3 class="h6 mb-2">Recommended Schema Types</h3>
                    ${(data.recommendations || []).map((rec) => {
                        const priorityClass = rec.priority === 'high' ? 'text-bg-danger' : rec.priority === 'medium' ? 'text-bg-warning' : 'text-bg-secondary';
                        return `<div class="schema-rec-card">
                            <div class="d-flex align-items-center justify-content-between gap-2 mb-1">
                                <strong>${escapeHtml(rec.type)}</strong>
                                <span class="badge rounded-pill ${priorityClass}" style="font-size:.7rem">${escapeHtml(rec.priority || 'low')}</span>
                            </div>
                            <p class="small mb-1 text-muted">${escapeHtml(rec.reason || '')}</p>
                            ${rec.snippet ? `<details class="mt-1"><summary class="small fw-semibold" style="cursor:pointer">Show code snippet</summary><pre class="schema-snippet-pre">${escapeHtml(rec.snippet)}</pre></details>` : ''}
                        </div>`;
                    }).join('')}
                   </div>`
                : '';

            contentEl.innerHTML = `
                <div class="mb-2">
                    <span class="soft-label small">${escapeHtml(String(data.pages_audited || 0))} page${data.pages_audited !== 1 ? 's' : ''} audited · site type: <strong>${escapeHtml(data.site_type || 'general')}</strong></span>
                </div>
                <div>
                    <h3 class="h6 mb-2">Found Schema Types</h3>
                    <div class="d-flex flex-wrap gap-1">${foundHtml}</div>
                </div>
                ${issuesHtml}
                ${recsHtml}`;
        } catch (err) {
            showError(contentEl, err.message);
            setStatus(sectionEl, 'Error', 'status-fail');
        }
    }

    /* ------------------------------------------------------------------ */
    /* Link architecture section                                           */
    /* ------------------------------------------------------------------ */

    async function loadLinkGraph(analysisId, sectionEl, contentEl) {
        showSpinner(contentEl, 'Building link graph…');
        try {
            const data = await fetchJson(`/api/analysis/${encodeURIComponent(analysisId)}/link-graph`);

            const orphanCount = data.orphan_count || 0;
            const totalPages = data.total_pages || 0;
            const statusLabel = orphanCount > 0 ? `${orphanCount} orphan${orphanCount !== 1 ? 's' : ''}` : `${totalPages} pages`;
            const statusCss = orphanCount > 5 ? 'status-fail' : orphanCount > 0 ? 'status-warning' : 'status-pass';
            setStatus(sectionEl, statusLabel, statusCss);

            // Depth distribution bars
            const dist = data.depth_distribution || {};
            const maxDepthCount = Math.max(1, ...Object.values(dist).map(Number));
            const depthBarsHtml = Object.keys(dist).sort((a, b) => Number(a) - Number(b)).map((depth) => {
                const count = dist[depth];
                const pct = Math.round((Number(count) / maxDepthCount) * 100);
                return `<div class="depth-bar-row">
                    <span style="min-width:5rem">Depth ${escapeHtml(depth)}</span>
                    <div class="depth-bar-track"><div class="depth-bar-fill" style="width:${pct}%"></div></div>
                    <span class="soft-label">${escapeHtml(String(count))} page${count !== 1 ? 's' : ''}</span>
                </div>`;
            }).join('');

            contentEl.innerHTML = `
                <div class="row g-3 mb-3">
                    <div class="col-sm-4">
                        <div class="p-3 border rounded-3 text-center" style="border-color:var(--siq-border)!important">
                            <div class="fs-4 fw-bold">${escapeHtml(String(totalPages))}</div>
                            <div class="soft-label small">Total pages</div>
                        </div>
                    </div>
                    <div class="col-sm-4">
                        <div class="p-3 border rounded-3 text-center" style="border-color:var(--siq-border)!important">
                            <div class="fs-4 fw-bold">${escapeHtml(String(data.total_links || 0))}</div>
                            <div class="soft-label small">Internal links</div>
                        </div>
                    </div>
                    <div class="col-sm-4">
                        <div class="p-3 border rounded-3 text-center ${orphanCount > 0 ? 'text-warning' : ''}" style="border-color:var(--siq-border)!important">
                            <div class="fs-4 fw-bold">${escapeHtml(String(orphanCount))}</div>
                            <div class="soft-label small">Orphan pages</div>
                        </div>
                    </div>
                </div>

                ${depthBarsHtml ? `<div class="mb-3"><h3 class="h6 mb-2">Click-depth from homepage</h3>${depthBarsHtml}</div>` : ''}

                <div class="mb-3">
                    <h3 class="h6 mb-2">Internal link graph</h3>
                    <div class="link-graph-container" id="linkGraphCanvas"></div>
                </div>

                ${orphanCount ? `<div class="mt-2">
                    <h3 class="h6 mb-1 text-warning">Orphan pages</h3>
                    <ul class="small ps-3 mb-0">
                        ${(data.orphans || []).slice(0, 15).map((u) => `<li class="mb-1"><a href="${escapeHtml(u)}" target="_blank" rel="noopener noreferrer">${escapeHtml(u)}</a></li>`).join('')}
                        ${(data.orphans || []).length > 15 ? `<li class="text-muted">… and ${data.orphans.length - 15} more</li>` : ''}
                    </ul>
                </div>` : ''}`;

            // Initialise interactive graph using link-graph.js if available
            if (typeof window.SiteIQLinkGraph === 'function') {
                const vizData = data.visualization || { nodes: [], edges: [] };
                window.SiteIQLinkGraph(
                    document.getElementById('linkGraphCanvas'),
                    vizData.nodes || [],
                    vizData.edges || []
                );
            }
        } catch (err) {
            showError(contentEl, err.message);
            setStatus(sectionEl, 'Error', 'status-fail');
        }
    }

    /* ------------------------------------------------------------------ */
    /* Bootstrap                                                            */
    /* ------------------------------------------------------------------ */

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.deepdive-toggle').forEach(initToggle);
    });
})();

/**
 * link-graph.js — Lightweight SVG force-directed graph for the Link
 * Architecture deep-dive section.
 *
 * Usage (called by deepdives.js after data is fetched):
 *   window.SiteIQLinkGraph(containerEl, nodes, edges)
 *
 * Each node: { id, label, depth, is_orphan }
 * Each edge: { source, target }
 *
 * No external library dependency — pure vanilla SVG + requestAnimationFrame.
 */

(() => {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Constants                                                            */
    /* ------------------------------------------------------------------ */

    const NODE_RADIUS = 7;
    const ORPHAN_RADIUS = 9;
    const LINK_DISTANCE = 90;
    const CHARGE_STRENGTH = -120;
    const CENTER_STRENGTH = 0.04;
    const VELOCITY_DECAY = 0.6;
    const ITERATIONS = 300;   // simulation ticks before stabilising

    const DEPTH_COLORS = ['#6f42c1', '#0d6efd', '#0dcaf0', '#20c997', '#ffc107', '#fd7e14'];
    const ORPHAN_COLOR = '#dc3545';

    /* ------------------------------------------------------------------ */
    /* Force simulation (very small subset of d3-force logic)              */
    /* ------------------------------------------------------------------ */

    function simulate(nodes, edges, width, height) {
        // Initialise positions randomly near centre
        nodes.forEach((n, i) => {
            n.x = width / 2 + (Math.random() - 0.5) * 200;
            n.y = height / 2 + (Math.random() - 0.5) * 200;
            n.vx = 0;
            n.vy = 0;
        });

        const idToNode = Object.fromEntries(nodes.map((n) => [n.id, n]));

        function tick() {
            // --- link force ---
            for (const e of edges) {
                const s = idToNode[e.source];
                const t = idToNode[e.target];
                if (!s || !t || s === t) continue;
                const dx = t.x - s.x;
                const dy = t.y - s.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = (dist - LINK_DISTANCE) / dist * 0.4;
                s.vx += dx * force;
                s.vy += dy * force;
                t.vx -= dx * force;
                t.vy -= dy * force;
            }

            // --- charge (repulsion) ---
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const a = nodes[i];
                    const b = nodes[j];
                    const dx = b.x - a.x;
                    const dy = b.y - a.y;
                    const distSq = dx * dx + dy * dy || 1;
                    const force = CHARGE_STRENGTH / distSq;
                    const fx = dx * force;
                    const fy = dy * force;
                    a.vx -= fx;
                    a.vy -= fy;
                    b.vx += fx;
                    b.vy += fy;
                }
            }

            // --- center force ---
            for (const n of nodes) {
                n.vx += (width / 2 - n.x) * CENTER_STRENGTH;
                n.vy += (height / 2 - n.y) * CENTER_STRENGTH;
            }

            // --- integrate ---
            for (const n of nodes) {
                n.vx *= VELOCITY_DECAY;
                n.vy *= VELOCITY_DECAY;
                n.x += n.vx;
                n.y += n.vy;
                // Clamp inside canvas
                const r = n.is_orphan ? ORPHAN_RADIUS : NODE_RADIUS;
                n.x = Math.max(r, Math.min(width - r, n.x));
                n.y = Math.max(r, Math.min(height - r, n.y));
            }
        }

        for (let i = 0; i < ITERATIONS; i++) tick();
        return { nodes, idToNode };
    }

    /* ------------------------------------------------------------------ */
    /* SVG rendering                                                        */
    /* ------------------------------------------------------------------ */

    const SVG_NS = 'http://www.w3.org/2000/svg';

    function svgEl(tag, attrs) {
        const el = document.createElementNS(SVG_NS, tag);
        for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
        return el;
    }

    function nodeColor(node) {
        if (node.is_orphan) return ORPHAN_COLOR;
        const depth = node.depth >= 0 ? node.depth : DEPTH_COLORS.length - 1;
        return DEPTH_COLORS[Math.min(depth, DEPTH_COLORS.length - 1)];
    }

    /* ------------------------------------------------------------------ */
    /* Public entry point                                                   */
    /* ------------------------------------------------------------------ */

    function SiteIQLinkGraph(container, rawNodes, rawEdges) {
        if (!container || !rawNodes || rawNodes.length === 0) {
            container.innerHTML = '<div class="deepdive-notice" style="height:100%;justify-content:center;align-items:center;display:flex"><span class="notice-icon">🔗</span><span>No internal link data available for this analysis.</span></div>';
            return;
        }

        const rect = container.getBoundingClientRect();
        const W = rect.width || 600;
        const H = rect.height || 400;

        // Limit to first 200 nodes for performance
        const MAX_NODES = 200;
        const limitedNodes = rawNodes.slice(0, MAX_NODES).map((n) => ({ ...n }));
        const nodeIds = new Set(limitedNodes.map((n) => n.id));
        const limitedEdges = rawEdges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));

        const { nodes, idToNode } = simulate(limitedNodes, limitedEdges, W, H);

        // Build SVG
        container.innerHTML = '';
        const svg = svgEl('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` });

        // Defs (arrowhead marker)
        const defs = svgEl('defs', {});
        const marker = svgEl('marker', {
            id: 'siq-arrow',
            viewBox: '0 0 10 10',
            refX: '14',
            refY: '5',
            markerWidth: '6',
            markerHeight: '6',
            orient: 'auto-start-reverse',
        });
        const arrowPath = svgEl('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: 'rgba(148,163,184,0.5)' });
        marker.appendChild(arrowPath);
        defs.appendChild(marker);
        svg.appendChild(defs);

        // Edges
        const edgeGroup = svgEl('g', { 'class': 'edges' });
        for (const e of limitedEdges) {
            const s = idToNode[e.source];
            const t = idToNode[e.target];
            if (!s || !t || s === t) continue;
            const line = svgEl('line', {
                x1: s.x, y1: s.y,
                x2: t.x, y2: t.y,
                stroke: 'rgba(148,163,184,0.3)',
                'stroke-width': '1',
                'marker-end': 'url(#siq-arrow)',
            });
            edgeGroup.appendChild(line);
        }
        svg.appendChild(edgeGroup);

        // Nodes
        const nodeGroup = svgEl('g', { 'class': 'nodes' });
        for (const n of nodes) {
            const r = n.is_orphan ? ORPHAN_RADIUS : NODE_RADIUS;
            const circle = svgEl('circle', {
                cx: n.x, cy: n.y,
                r,
                fill: nodeColor(n),
                stroke: 'rgba(255,255,255,0.3)',
                'stroke-width': '1.5',
                style: 'cursor:pointer',
            });
            circle.dataset.id = n.id;
            circle.dataset.label = n.label || n.id;
            circle.dataset.depth = n.depth;
            circle.dataset.orphan = n.is_orphan ? '1' : '0';
            nodeGroup.appendChild(circle);
        }
        svg.appendChild(nodeGroup);

        container.appendChild(svg);

        // Tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'lg-tooltip';
        tooltip.style.display = 'none';
        container.appendChild(tooltip);

        nodeGroup.addEventListener('mouseover', (e) => {
            const circle = e.target.closest('circle');
            if (!circle) return;
            const id = circle.dataset.id || '';
            const depth = circle.dataset.depth;
            const orphan = circle.dataset.orphan === '1';
            tooltip.textContent = `${id}${depth >= 0 ? ` · depth ${depth}` : ''}${orphan ? ' · orphan' : ''}`;
            tooltip.style.display = 'block';
        });

        nodeGroup.addEventListener('mousemove', (e) => {
            const containerRect = container.getBoundingClientRect();
            const x = e.clientX - containerRect.left + 10;
            const y = e.clientY - containerRect.top + 10;
            tooltip.style.left = `${Math.min(x, containerRect.width - 240)}px`;
            tooltip.style.top = `${Math.max(0, y - 30)}px`;
        });

        nodeGroup.addEventListener('mouseout', () => {
            tooltip.style.display = 'none';
        });

        // Legend
        const legend = document.createElement('div');
        legend.style.cssText = 'display:flex;flex-wrap:wrap;gap:.5rem;font-size:.72rem;padding:.5rem .75rem;';
        const items = [
            { color: DEPTH_COLORS[0], label: 'Homepage' },
            { color: DEPTH_COLORS[1], label: 'Depth 1' },
            { color: DEPTH_COLORS[2], label: 'Depth 2+' },
            { color: ORPHAN_COLOR, label: 'Orphan' },
        ];
        for (const item of items) {
            legend.innerHTML += `<span style="display:inline-flex;align-items:center;gap:.3rem"><span style="width:.65rem;height:.65rem;border-radius:50%;background:${item.color};flex-shrink:0"></span>${item.label}</span>`;
        }
        container.appendChild(legend);
    }

    window.SiteIQLinkGraph = SiteIQLinkGraph;
})();

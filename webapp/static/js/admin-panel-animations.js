(function initAdminPanelAnimations() {
    "use strict";

    if (window.__adminPanelAnimationsInitialized) {
        return;
    }
    window.__adminPanelAnimationsInitialized = true;

    var DURATION_MS = 1500;
    var CHART_ANIM_DURATION_MS = 0;
    var CHART_ANIM_EASING = "easeInOutCubic";
    var ANIMATING_ATTR = "data-kpi-animating";
    var PROGRAMMATIC_ATTR = "data-kpi-programmatic";
    var LAST_ATTR = "data-kpi-last";
    var observer = null;
    var reinitQueued = false;
    var lastReinitAt = 0;
    var MIN_REINIT_GAP_MS = 120;
    var lifecycleEventKeys = new Set();
    var lifecycleCoalesceFlushQueued = false;
    var scheduleMicrotask = typeof queueMicrotask === "function"
        ? queueMicrotask
        : function (callback) {
            Promise.resolve().then(callback);
        };

    function configureGlobalChartAnimations() {
        if (typeof Chart === "undefined" || !Chart.defaults) {
            return;
        }

        if (!Chart.defaults.animation) {
            Chart.defaults.animation = {};
        }

        Chart.defaults.animation.duration = CHART_ANIM_DURATION_MS;
        Chart.defaults.animation.easing = CHART_ANIM_EASING;

        if (!Chart.defaults.transitions) {
            Chart.defaults.transitions = {};
        }

        if (!Chart.defaults.transitions.active) {
            Chart.defaults.transitions.active = {};
        }

        if (!Chart.defaults.transitions.active.animation) {
            Chart.defaults.transitions.active.animation = {};
        }

        Chart.defaults.transitions.active.animation.duration = CHART_ANIM_DURATION_MS;
        Chart.defaults.transitions.active.animation.easing = CHART_ANIM_EASING;

        if (!Chart.defaults.transitions.show) {
            Chart.defaults.transitions.show = {};
        }

        if (!Chart.defaults.transitions.show.animation) {
            Chart.defaults.transitions.show.animation = {};
        }

        Chart.defaults.transitions.show.animation.duration = CHART_ANIM_DURATION_MS;
        Chart.defaults.transitions.show.animation.easing = CHART_ANIM_EASING;
    }

    function configureHoverLineIndicator() {
        if (typeof Chart === "undefined" || typeof Chart.register !== "function") {
            return;
        }

        if (window.__adminHoverLineIndicatorRegistered) {
            return;
        }

        Chart.register({
            id: "adminHoverLineIndicator",
            afterDatasetsDraw: function (chart) {
                if (!chart || !chart.config || chart.config.type !== "line") {
                    return;
                }

                var tooltip = chart.tooltip;
                if (!tooltip || typeof tooltip.getActiveElements !== "function") {
                    return;
                }

                var active = tooltip.getActiveElements();
                if (!active || !active.length || !active[0].element) {
                    return;
                }

                var chartArea = chart.chartArea;
                if (!chartArea) {
                    return;
                }

                var x = active[0].element.x;
                var ctx = chart.ctx;

                ctx.save();
                ctx.beginPath();
                ctx.moveTo(x, chartArea.top);
                ctx.lineTo(x, chartArea.bottom);
                ctx.lineWidth = 1;
                ctx.strokeStyle = "rgba(15, 118, 110, 0.38)";
                ctx.setLineDash([4, 4]);
                ctx.stroke();
                ctx.restore();
            }
        });

        window.__adminHoverLineIndicatorRegistered = true;
    }

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function parseValue(text) {
        var raw = String(text || "").trim();
        var match = raw.match(/-?\d[\d,]*(?:\.\d+)?/);

        if (!match) {
            return null;
        }

        var token = match[0];
        var numeric = parseFloat(token.replace(/,/g, ""));

        if (!Number.isFinite(numeric)) {
            return null;
        }

        var decimals = 0;
        var parts = token.split(".");
        if (parts.length > 1) {
            decimals = parts[1].length;
        }

        return {
            prefix: raw.slice(0, match.index),
            suffix: raw.slice(match.index + token.length),
            value: numeric,
            decimals: decimals
        };
    }

    function buildKpiHint(el) {
        var parts = [];

        if (!el) {
            return "";
        }

        if (el.id) {
            parts.push(String(el.id).toLowerCase());
        }

        var card = el.closest("article, [class*='kpi'], .admin-kpi, .ops-kpi, .ngo-kpi, .ra-kpi");
        if (card) {
            var label = card.querySelector("[class*='kpi-label'], [id$='-label']");
            if (label && label.textContent) {
                parts.push(String(label.textContent).toLowerCase());
            }
        }

        return parts.join(" ");
    }

    function formatNumber(value, decimals) {
        var fixed = Math.max(0, decimals || 0);
        return Number(value).toLocaleString("en-US", {
            minimumFractionDigits: fixed,
            maximumFractionDigits: fixed
        });
    }

    function writeText(el, prefix, value, suffix, decimals) {
        el.setAttribute(PROGRAMMATIC_ATTR, "true");
        el.textContent = prefix + formatNumber(value, decimals) + suffix;
        el.removeAttribute(PROGRAMMATIC_ATTR);
    }

    function isKpiElement(el) {
        if (!el || !el.matches) {
            return false;
        }

        return el.matches('[id^="kpi-"]:not([id$="-label"]):not([id$="-change"]), [id^="vm-kpi-"], #payops-success-headline, [data-kpi-value="true"], [class*="kpi-value"]');
    }

    function animateElement(el) {
        if (!el || el.getAttribute(ANIMATING_ATTR) === "true") {
            return;
        }

        if (el.getAttribute("data-no-animate") === "true") {
            return;
        }

        if (el.getAttribute("data-kpi-live") === "true") {
            return;
        }

        var parsed = parseValue(el.textContent);
        if (!parsed) {
            return;
        }

        if (parsed.value === 0) {
            var snapshot = (parsed.prefix + formatNumber(parsed.value, parsed.decimals) + parsed.suffix).trim();
            if (el.getAttribute(LAST_ATTR) === snapshot) {
                return;
            }
            el.setAttribute(LAST_ATTR, snapshot);
            return;
        }

        var snapshot = (parsed.prefix + formatNumber(parsed.value, parsed.decimals) + parsed.suffix).trim();
        if (el.getAttribute(LAST_ATTR) === snapshot) {
            return;
        }

        // Admin KPI count-up intentionally always animates for dashboard readability.

        var startTime = null;
        el.setAttribute(ANIMATING_ATTR, "true");
        // Ensure KPI cards visually start at zero before counting to the target value.
        writeText(el, parsed.prefix, 0, parsed.suffix, parsed.decimals);

        function frame(now) {
            if (startTime === null) {
                startTime = now;
            }

            var progress = Math.min((now - startTime) / DURATION_MS, 1);
            var eased = easeOutCubic(progress);
            var current = parsed.value * eased;

            writeText(el, parsed.prefix, current, parsed.suffix, parsed.decimals);

            if (progress < 1) {
                requestAnimationFrame(frame);
                return;
            }

            writeText(el, parsed.prefix, parsed.value, parsed.suffix, parsed.decimals);
            el.setAttribute(LAST_ATTR, snapshot);
            el.removeAttribute(ANIMATING_ATTR);
        }

        requestAnimationFrame(frame);
    }

    function collectKpiElements(root) {
        var scope = root || document;
        var found = [];
        var seen = new Set();

        function add(el) {
            if (!el || seen.has(el) || el.getAttribute("data-no-animate") === "true") {
                return;
            }
            seen.add(el);
            found.push(el);
        }

        // Common KPI id patterns used across admin panels.
        scope.querySelectorAll('[id^="kpi-"]:not([id$="-label"]):not([id$="-change"])').forEach(add);
        scope.querySelectorAll('[id^="vm-kpi-"]').forEach(add);

        // KPI on payment summary card.
        scope.querySelectorAll('#payops-success-headline').forEach(add);

        // Explicit opt-in marker for future templates.
        scope.querySelectorAll('[data-kpi-value="true"]').forEach(add);

        // Capture KPI values that use panel-specific classes such as don-kpi-value, inv-kpi-value, etc.
        scope.querySelectorAll('p[class*="kpi-value"], span[class*="kpi-value"], div[class*="kpi-value"]').forEach(add);

        // Dashboard top KPI cards use text size classes without KPI ids.
        scope.querySelectorAll('#dashboard-shell [aria-label="Key performance indicators"] article').forEach(function (card) {
            add(card.querySelector('p[class*="text-3xl"], p[class*="text-2xl"]'));
        });

        // Other panels often label KPI sections with aria text containing KPI.
        scope.querySelectorAll('#dashboard-shell section[aria-label*="KPI" i], #dashboard-shell section[aria-label*="Key performance" i]').forEach(function (section) {
            section.querySelectorAll('p[class*="text-3xl"], p[class*="text-2xl"], .vm-kpi-value').forEach(add);
        });

        return found;
    }

    function animateAll(root) {
        collectKpiElements(root).forEach(animateElement);
    }

    function hasActiveAnimations(root) {
        return collectKpiElements(root).some(function (el) {
            return el && el.getAttribute(ANIMATING_ATTR) === "true";
        });
    }

    function observeChanges() {
        var container = document.getElementById("dashboard-shell") || document.body;

        if (!container) {
            return;
        }

        if (observer) {
            observer.disconnect();
        }

        observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === "characterData") {
                    var parent = mutation.target.parentElement;
                    if (!parent || parent.getAttribute(PROGRAMMATIC_ATTR) === "true") {
                        return;
                    }
                    animateElement(parent);
                    return;
                }

                if (mutation.type !== "childList") {
                    return;
                }

                mutation.addedNodes.forEach(function (node) {
                    if (!node || node.nodeType !== 1) {
                        return;
                    }

                    animateAll(node);
                });

                // textContent updates often appear as childList on the KPI element itself.
                if (mutation.target && mutation.target.nodeType === 1 && isKpiElement(mutation.target) && mutation.target.getAttribute(PROGRAMMATIC_ATTR) !== "true") {
                    animateElement(mutation.target);
                }
            });
        });

        observer.observe(container, {
            subtree: true,
            childList: true,
            characterData: true
        });
    }

    function reinitialize(root) {
        animateAll(root || document);
        observeChanges();
    }

    function resolvePanelUrlFromEvent(event) {
        if (event && event.detail && typeof event.detail.panelUrl === "string" && event.detail.panelUrl.trim()) {
            return event.detail.panelUrl.trim();
        }

        return window.location.pathname + window.location.search + window.location.hash;
    }

    function shouldHandleLifecycleEvent(event, eventName) {
        var key = String(eventName || "") + "|" + resolvePanelUrlFromEvent(event);

        if (lifecycleEventKeys.has(key)) {
            return false;
        }

        lifecycleEventKeys.add(key);

        if (!lifecycleCoalesceFlushQueued) {
            lifecycleCoalesceFlushQueued = true;
            scheduleMicrotask(function () {
                lifecycleEventKeys.clear();
                lifecycleCoalesceFlushQueued = false;
            });
        }

        return true;
    }

    function guardedReinitialize(root) {
        var target = root || document;
        var now = Date.now();

        if (reinitQueued) {
            return;
        }

        if (now - lastReinitAt < MIN_REINIT_GAP_MS) {
            return;
        }

        if (hasActiveAnimations(target)) {
            return;
        }

        reinitQueued = true;
        requestAnimationFrame(function () {
            reinitQueued = false;
            lastReinitAt = Date.now();
            reinitialize(target);
        });
    }

    function init() {
        configureGlobalChartAnimations();
        configureHoverLineIndicator();
        reinitialize(document);

        // Re-run after common navigation/content swap events.
        ["pageshow", "popstate", "hashchange", "htmx:afterSwap", "turbo:load", "pjax:end", "admin:panel-switched", "admin:panel-rendered"].forEach(function (evt) {
            document.addEventListener(evt, function (event) {
                if (!shouldHandleLifecycleEvent(event, evt)) {
                    return;
                }

                guardedReinitialize(document);
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.AdminPanelAnimations = {
        reinitialize: reinitialize,
        guardedReinitialize: guardedReinitialize,
        animateAll: animateAll
    };
})();

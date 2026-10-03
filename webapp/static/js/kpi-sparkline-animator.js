(function () {
    "use strict";

    var DURATION = 700;
    var FILL_DELAY = 180;
    var FILL_OPACITY = 0.06;
    var MARKER = "data-spark-animated";

    function isElementVisible(el) {
        if (!el) {
            return false;
        }

        var style = window.getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
            return false;
        }

        var rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function animateSvg(svg) {
        if (!svg || svg.getAttribute(MARKER)) {
            return;
        }

        if (!isElementVisible(svg)) {
            return;
        }

        var line = svg.querySelector("path.line");
        if (!line || typeof line.getTotalLength !== "function") {
            return;
        }

        var length = 0;
        try {
            length = line.getTotalLength();
        } catch (error) {
            return;
        }

        if (!length || !isFinite(length) || length <= 0) {
            return;
        }

        line.style.transition = "none";
        line.style.strokeDasharray = String(length);
        line.style.strokeDashoffset = String(length);
        line.getBoundingClientRect();
        line.style.transition = "stroke-dashoffset " + DURATION + "ms ease-out";
        line.style.strokeDashoffset = "0";

        var fill = svg.querySelector("path.fill");
        if (fill) {
            fill.style.opacity = "0";
            fill.style.transition = "opacity 380ms ease-out " + FILL_DELAY + "ms";
            requestAnimationFrame(function () {
                fill.style.opacity = String(FILL_OPACITY);
            });
        }

        svg.setAttribute(MARKER, "1");
    }

    function animateAll(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var svgs = scope.querySelectorAll(".kpi-sparkline svg");
        svgs.forEach(function (svg) {
            animateSvg(svg);
        });
    }

    function setupIntersectionObserver() {
        if (!("IntersectionObserver" in window)) {
            return;
        }

        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) {
                    return;
                }

                var container = entry.target;
                var svg = container.querySelector("svg");
                if (svg) {
                    animateSvg(svg);
                }
                io.unobserve(container);
            });
        }, { threshold: 0.05 });

        document.querySelectorAll(".kpi-sparkline").forEach(function (container) {
            var svg = container.querySelector("svg");
            if (!svg) {
                return;
            }

            if (isElementVisible(container)) {
                animateSvg(svg);
            } else {
                io.observe(container);
            }
        });
    }

    function setupMutationObserver() {
        if (!("MutationObserver" in window)) {
            return;
        }

        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (!(node instanceof Element)) {
                        return;
                    }

                    if (node.matches(".kpi-sparkline svg")) {
                        animateSvg(node);
                        return;
                    }

                    if (node.matches(".kpi-sparkline") || node.querySelector(".kpi-sparkline")) {
                        animateAll(node);
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    window.triggerKpiSparklineAnimations = function (contextRoot) {
        animateAll(contextRoot || document);
    };

    function init() {
        animateAll(document);
        setupIntersectionObserver();
        setupMutationObserver();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.addEventListener("load", function () {
        animateAll(document);
    });
})();
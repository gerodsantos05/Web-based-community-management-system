(function initSidebarState() {
    "use strict";

    var STORAGE_KEY = "dashboard-sidebar-state";
    var LEGACY_STORAGE_KEY = "dashboardSidebar";
    var SHELL_ID = "dashboard-shell";
    var TOGGLE_ID = "sidebar-toggle-desktop";
    var MOBILE_TOGGLE_ID = "sidebar-toggle-mobile";
    var MOBILE_OVERLAY_ID = "mobile-overlay";

    function normalizeState(value) {
        return value === "collapsed" ? "collapsed" : "expanded";
    }

    function readState() {
        try {
            var saved = localStorage.getItem(STORAGE_KEY);
            if (saved === "collapsed" || saved === "expanded") {
                return saved;
            }

            var legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
            if (legacy === "collapsed" || legacy === "expanded") {
                localStorage.setItem(STORAGE_KEY, legacy);
                return legacy;
            }

            return "expanded";
        } catch (e) {
            return "expanded";
        }
    }

    function writeState(state) {
        try {
            var normalized = normalizeState(state);
            localStorage.setItem(STORAGE_KEY, normalized);
            localStorage.setItem(LEGACY_STORAGE_KEY, normalized);
        } catch (e) {
            // Ignore storage failures (private mode / blocked storage)
        }
    }

    function getShell() {
        return document.getElementById(SHELL_ID);
    }

    function getToggle() {
        return document.getElementById(TOGGLE_ID);
    }

    function getMobileToggle() {
        return document.getElementById(MOBILE_TOGGLE_ID);
    }

    function getMobileOverlay() {
        return document.getElementById(MOBILE_OVERLAY_ID);
    }

    function syncToggleA11y(toggle, state) {
        if (!toggle) {
            return;
        }
        var expanded = state === "expanded";
        toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
        toggle.setAttribute("aria-label", expanded ? "Collapse sidebar" : "Expand sidebar");
    }

    function applyMobileOpen(isOpen) {
        var shell = getShell();
        var sidebar = document.getElementById("dashboard-sidebar");
        var mobileToggle = getMobileToggle();
        var overlay = getMobileOverlay();
        var open = !!isOpen;

        if (sidebar) {
            sidebar.setAttribute("data-mobile-open", open ? "true" : "false");
        }

        if (overlay) {
            overlay.setAttribute("data-open", open ? "true" : "false");
            overlay.classList.toggle("hidden", !open);
            overlay.setAttribute("aria-hidden", open ? "false" : "true");
        }

        if (mobileToggle) {
            mobileToggle.setAttribute("aria-expanded", open ? "true" : "false");
            mobileToggle.setAttribute("aria-label", open ? "Close sidebar navigation" : "Open sidebar navigation");
            mobileToggle.setAttribute("data-open", open ? "true" : "false");
        }

        if (shell && window.innerWidth <= 1023) {
            shell.setAttribute("data-sidebar", "expanded");
            shell.dataset.mobileMenuOpen = open ? "true" : "false";
        }
    }

    function applyState(state, persist) {
        var shell = getShell();
        if (!shell) {
            return;
        }

        var normalized = normalizeState(state);
        shell.setAttribute("data-sidebar", normalized);
        syncToggleA11y(getToggle(), normalized);

        if (persist) {
            writeState(normalized);
        }
    }

    function toggleState() {
        var shell = getShell();
        if (!shell) {
            return;
        }

        var current = normalizeState(shell.getAttribute("data-sidebar"));
        var next = current === "collapsed" ? "expanded" : "collapsed";
        applyState(next, true);
    }

    function bindToggle() {
        var toggle = getToggle();
        if (toggle && toggle.dataset.sidebarStateBound !== "true") {
            var suppressClick = false;

            toggle.addEventListener("click", function () {
                if (suppressClick) {
                    suppressClick = false;
                    return;
                }
                toggleState();
            });

            toggle.addEventListener("keydown", function (event) {
                if (event.key !== "Enter" && event.key !== " ") {
                    return;
                }
                event.preventDefault();
                suppressClick = true;
                toggleState();
            });

            toggle.dataset.sidebarStateBound = "true";
        }

        var mobileToggle = getMobileToggle();
        if (mobileToggle && mobileToggle.dataset.sidebarMobileBound !== "true") {
            mobileToggle.addEventListener("click", function () {
                var open = document.getElementById("dashboard-sidebar") && document.getElementById("dashboard-sidebar").getAttribute("data-mobile-open") === "true";
                applyMobileOpen(!open);
            });

            mobileToggle.dataset.sidebarMobileBound = "true";
        }

        var overlay = getMobileOverlay();
        if (overlay && overlay.dataset.sidebarOverlayBound !== "true") {
            overlay.addEventListener("click", function () {
                applyMobileOpen(false);
            });
            overlay.dataset.sidebarOverlayBound = "true";
        }
    }

    function clearBootingTransition() {
        var shell = getShell();
        if (!shell || !shell.classList.contains("sidebar-booting")) {
            return;
        }

        requestAnimationFrame(function () {
            shell.classList.remove("sidebar-booting");
        });
    }

    function init() {
        applyState(readState(), true);
        bindToggle();
        clearBootingTransition();

        if (window.innerWidth <= 1023) {
            applyMobileOpen(false);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.SidebarState = {
        key: STORAGE_KEY,
        readState: readState,
        applyState: applyState,
        toggleState: toggleState,
        applyMobileOpen: applyMobileOpen
    };
})();

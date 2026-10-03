(function () {
    "use strict";

    function setSection(section) {
        var links = document.querySelectorAll("[data-ud-section-link]");
        var sections = document.querySelectorAll("[data-ud-section]");
        var title = document.getElementById("ud-page-title");
        var subtitle = document.getElementById("ud-page-subtitle");

        links.forEach(function (link) {
            var active = link.getAttribute("data-ud-section-link") === section;
            link.classList.toggle("active", active);
            link.setAttribute("aria-current", active ? "page" : "false");
        });

        sections.forEach(function (panel) {
            panel.classList.toggle("active", panel.getAttribute("data-ud-section") === section);
        });

        var activeLink = document.querySelector('[data-ud-section-link="' + section + '"]');
        if (activeLink && title) {
            title.textContent = activeLink.getAttribute("data-title") || "Dashboard";
        }
        if (activeLink && subtitle) {
            subtitle.textContent = activeLink.getAttribute("data-subtitle") || "Welcome back";
        }
    }

    function bindSections() {
        var links = document.querySelectorAll("[data-ud-section-link]");
        links.forEach(function (link) {
            link.addEventListener("click", function (event) {
                event.preventDefault();
                var section = link.getAttribute("data-ud-section-link") || "dashboard";
                setSection(section);
                if (window.innerWidth < 921) {
                    toggleSidebar(false);
                }
            });
        });
    }

    function toggleSidebar(open) {
        var sidebar = document.getElementById("ud-sidebar");
        var overlay = document.getElementById("ud-overlay");
        if (!sidebar || !overlay) {
            return;
        }
        sidebar.classList.toggle("open", open);
        overlay.classList.toggle("open", open);
    }

    function bindSidebarToggle() {
        var openBtn = document.getElementById("ud-mobile-toggle");
        var overlay = document.getElementById("ud-overlay");
        if (openBtn) {
            openBtn.addEventListener("click", function () {
                toggleSidebar(true);
            });
        }
        if (overlay) {
            overlay.addEventListener("click", function () {
                toggleSidebar(false);
            });
        }
    }

    function bindProfileDropdown() {
        var trigger = document.getElementById("ud-profile-trigger");
        var drop = document.getElementById("ud-profile-dropdown");
        if (!trigger || !drop) {
            return;
        }

        trigger.addEventListener("click", function (event) {
            event.stopPropagation();
            drop.classList.toggle("open");
        });

        document.addEventListener("click", function (event) {
            if (!drop.contains(event.target) && !trigger.contains(event.target)) {
                drop.classList.remove("open");
            }
        });
    }

    function init() {
        bindSections();
        bindSidebarToggle();
        bindProfileDropdown();
        setSection("dashboard");
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

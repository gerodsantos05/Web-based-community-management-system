(function () {
    "use strict";

    function createMiniChart(canvasId, dataPoints, colorHex) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === "undefined") {
            return null;
        }

        return new Chart(canvas, {
            type: "line",
            data: {
                labels: ["W1", "W2", "W3", "W4", "W5", "W6"],
                datasets: [
                    {
                        data: dataPoints,
                        borderColor: colorHex,
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.38,
                        fill: true,
                        backgroundColor: colorHex + "22"
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });
    }

    function getActivitySeries(rangeKey) {
        // TODO: Replace this sample data with values passed from Django context or your API endpoint.
        if (rangeKey === "daily") {
            return {
                labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                donations: [420, 390, 470, 510, 495, 540, 590],
                volunteers: [18, 21, 19, 23, 25, 24, 28]
            };
        }

        if (rangeKey === "monthly") {
            return {
                labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
                donations: [1200, 1320, 1380, 1490, 1430, 1580, 1660, 1710],
                volunteers: [72, 77, 80, 84, 82, 88, 92, 95]
            };
        }

        return {
            labels: ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"],
            donations: [880, 910, 990, 1040, 1120, 1180, 1270, 1360],
            volunteers: [54, 56, 60, 63, 67, 70, 72, 76]
        };
    }

    function setSidebarCollapsedState(shell, isCollapsed) {
        shell.setAttribute("data-sidebar", isCollapsed ? "collapsed" : "expanded");
    }

    function setMobileSidebarOpen(sidebar, overlay, mobileToggle, isOpen) {
        sidebar.setAttribute("data-mobile-open", isOpen ? "true" : "false");
        overlay.setAttribute("data-open", isOpen ? "true" : "false");
        mobileToggle.setAttribute("aria-label", isOpen ? "Close sidebar navigation" : "Open sidebar navigation");
    }

    document.addEventListener("DOMContentLoaded", function () {
        var shell = document.getElementById("dashboard-shell");
        var sidebar = document.getElementById("dashboard-sidebar");
        var overlay = document.getElementById("mobile-overlay");
        var desktopToggle = document.getElementById("sidebar-toggle-desktop") || document.getElementById("header-sidebar-toggle");
        var mobileToggle = document.getElementById("sidebar-toggle-mobile");
        var rangeSelect = document.getElementById("activity-range");
        var activityCanvas = document.getElementById("community-activity-chart");

        if (desktopToggle && shell && desktopToggle.dataset.sidebarStateBound !== "true") {
            desktopToggle.addEventListener("click", function () {
                var collapsed = shell.getAttribute("data-sidebar") === "collapsed";
                setSidebarCollapsedState(shell, !collapsed);
                desktopToggle.setAttribute("aria-label", collapsed ? "Collapse sidebar" : "Expand sidebar");
            });
        }

        if (mobileToggle && sidebar && overlay) {
            mobileToggle.addEventListener("click", function () {
                var isOpen = sidebar.getAttribute("data-mobile-open") === "true";
                setMobileSidebarOpen(sidebar, overlay, mobileToggle, !isOpen);
            });

            overlay.addEventListener("click", function () {
                setMobileSidebarOpen(sidebar, overlay, mobileToggle, false);
            });
        }

        createMiniChart("kpi-members", [9, 10, 12, 11, 13, 14], "#0f766e");
        createMiniChart("kpi-volunteers", [7, 9, 8, 10, 9, 11], "#10b981");
        createMiniChart("kpi-donations", [12, 14, 13, 16, 18, 17], "#14b8a6");

        if (!activityCanvas || typeof Chart === "undefined") {
            return;
        }

        var currentData = getActivitySeries("weekly");

        var activityChart = new Chart(activityCanvas, {
            type: "line",
            data: {
                labels: currentData.labels,
                datasets: [
                    {
                        label: "Donations",
                        data: currentData.donations,
                        borderColor: "#0f766e",
                        backgroundColor: "rgba(15, 118, 110, 0.12)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 2
                    },
                    {
                        label: "Volunteers",
                        data: currentData.volunteers,
                        borderColor: "#14b8a6",
                        backgroundColor: "rgba(20, 184, 166, 0.10)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: { enabled: true },
                    legend: {
                        position: "top",
                        align: "start"
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: "rgba(35, 110, 103, 0.14)"
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: "rgba(35, 110, 103, 0.14)"
                        }
                    }
                }
            }
        });

        if (rangeSelect) {
            rangeSelect.addEventListener("change", function () {
                var next = getActivitySeries(rangeSelect.value);
                activityChart.data.labels = next.labels;
                activityChart.data.datasets[0].data = next.donations;
                activityChart.data.datasets[1].data = next.volunteers;
                activityChart.update();
            });
        }
    });
})();

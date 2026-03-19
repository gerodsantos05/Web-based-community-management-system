(function () {
    "use strict";

    var dataEl = document.getElementById("inventory-sample-data");
    if (!dataEl) {
        return;
    }

    var SAMPLE_DATA = JSON.parse(dataEl.textContent || "{}");

    var state = {
        raw: SAMPLE_DATA,
        filteredItems: (SAMPLE_DATA.items || []).slice(),
        selected: new Set(),
        page: 1,
        pageSize: 5,
        sortKey: "updated",
        sortDir: "desc",
        quickFilter: "All",
        range: "weekly",
        filters: {
            search: "",
            status: "All",
            category: "All",
            sort: "updated-desc",
            updatedFrom: "",
            updatedTo: ""
        },
        chartsReady: false,
        charts: {
            movement: null,
            status: null,
            categories: null
        }
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function parseDate(value) {
        return value ? new Date(value + "T00:00:00") : null;
    }

    function currency(value) {
        return "P " + Number(value || 0).toLocaleString();
    }

    function initials(name) {
        return String(name || "").split(" ").slice(0, 2).map(function (part) {
            return part.charAt(0).toUpperCase();
        }).join("") || "NA";
    }

    function statusClass(status) {
        if (status === "In Stock") {
            return "inventory-status inventory-status-in-stock";
        }

        if (status === "Low Stock") {
            return "inventory-status inventory-status-low-stock";
        }

        return "inventory-status inventory-status-out-of-stock";
    }

    function chartTheme() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    backgroundColor: "rgba(5, 46, 43, 0.92)",
                    titleColor: "#ecfdf5",
                    bodyColor: "#d1fae5"
                },
                legend: { labels: { color: "#0f4e48" } }
            }
        };
    }

    function initSparkline(id, points) {
        var canvas = byId(id);
        if (!canvas || typeof Chart === "undefined") {
            return;
        }

        new Chart(canvas, {
            type: "line",
            data: {
                labels: ["1", "2", "3", "4", "5", "6"],
                datasets: [{
                    data: points,
                    borderColor: "#0f766e",
                    backgroundColor: "rgba(15, 118, 110, 0.12)",
                    fill: true,
                    pointRadius: 0,
                    tension: 0.35,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false } }
            }
        });
    }

    function getMovementData() {
        var movement = state.raw.movement || {};
        return movement[state.range] || movement.weekly || { labels: [], in: [], out: [] };
    }

    function initKpis(summary) {
        byId("kpi-value").textContent = currency(summary.value);
        byId("kpi-items").textContent = Number(summary.items || 0).toLocaleString();
        byId("kpi-low-stock").textContent = Number(summary.lowStock || 0).toLocaleString();
        byId("kpi-out-stock").textContent = Number(summary.outOfStock || 0).toLocaleString();

        initSparkline("spark-value", [4200, 4380, 4550, 4720, 4870, summary.value || 5000]);
        initSparkline("spark-items", [1300, 1340, 1385, 1430, 1470, summary.items || 1500]);
        initSparkline("spark-low", [24, 22, 21, 20, 19, summary.lowStock || 18]);
        initSparkline("spark-out", [7, 6, 6, 5, 5, summary.outOfStock || 4]);
    }

    function deriveStatusCounts(items) {
        return items.reduce(function (acc, item) {
            acc[item.status] = (acc[item.status] || 0) + 1;
            return acc;
        }, { "In Stock": 0, "Low Stock": 0, "Out of Stock": 0 });
    }

    function deriveCategoryCounts(items) {
        return items.reduce(function (acc, item) {
            acc[item.category] = (acc[item.category] || 0) + item.qty;
            return acc;
        }, {});
    }

    function renderInventoryCharts(data) {
        if (typeof Chart === "undefined") {
            return;
        }

        var movement = getMovementData();
        var status = deriveStatusCounts(data.items || []);
        var categories = deriveCategoryCounts(data.items || []);

        if (!state.chartsReady) {
            state.charts.movement = new Chart(byId("inventory-movement-chart"), {
                type: "bar",
                data: {
                    labels: movement.labels,
                    datasets: [
                        {
                            label: "Stock In",
                            data: movement.in,
                            borderRadius: 8,
                            maxBarThickness: 26,
                            backgroundColor: "rgba(16, 185, 129, 0.82)"
                        },
                        {
                            label: "Stock Out",
                            data: movement.out,
                            borderRadius: 8,
                            maxBarThickness: 26,
                            backgroundColor: "rgba(20, 184, 166, 0.82)"
                        }
                    ]
                },
                options: Object.assign(chartTheme(), {
                    scales: {
                        x: { ticks: { color: "#236e67" }, grid: { display: false } },
                        y: { beginAtZero: true, ticks: { color: "#236e67" }, grid: { color: "rgba(35, 110, 103, 0.12)" } }
                    }
                })
            });

            state.charts.status = new Chart(byId("stock-status-chart"), {
                type: "doughnut",
                data: {
                    labels: ["In Stock", "Low Stock", "Out of Stock"],
                    datasets: [{
                        data: [status["In Stock"], status["Low Stock"], status["Out of Stock"]],
                        backgroundColor: ["rgba(16, 185, 129, 0.86)", "rgba(245, 158, 11, 0.82)", "rgba(239, 68, 68, 0.82)"],
                        borderColor: "#ffffff",
                        borderWidth: 2
                    }]
                },
                options: Object.assign(chartTheme(), {
                    cutout: "62%",
                    plugins: {
                        legend: { position: "bottom", labels: { color: "#0f4e48", boxWidth: 12 } },
                        tooltip: chartTheme().plugins.tooltip
                    }
                })
            });

            state.charts.categories = new Chart(byId("category-chart"), {
                type: "bar",
                data: {
                    labels: Object.keys(categories),
                    datasets: [{
                        label: "Quantity",
                        data: Object.values(categories),
                        borderRadius: 10,
                        maxBarThickness: 30,
                        backgroundColor: "rgba(15, 118, 110, 0.82)"
                    }]
                },
                options: Object.assign(chartTheme(), {
                    indexAxis: "y",
                    plugins: { legend: { display: false }, tooltip: chartTheme().plugins.tooltip },
                    scales: {
                        x: { beginAtZero: true, ticks: { color: "#236e67" }, grid: { color: "rgba(35, 110, 103, 0.12)" } },
                        y: { ticks: { color: "#236e67" }, grid: { display: false } }
                    }
                })
            });

            state.chartsReady = true;
            return;
        }

        state.charts.movement.data.labels = movement.labels;
        state.charts.movement.data.datasets[0].data = movement.in;
        state.charts.movement.data.datasets[1].data = movement.out;
        state.charts.movement.update();

        state.charts.status.data.datasets[0].data = [status["In Stock"], status["Low Stock"], status["Out of Stock"]];
        state.charts.status.update();

        state.charts.categories.data.labels = Object.keys(categories);
        state.charts.categories.data.datasets[0].data = Object.values(categories);
        state.charts.categories.update();
    }

    function updateCharts(filters) {
        var data = buildDerivedData(filters || state.filters);
        renderInventoryCharts(data);
    }

    function renderLowAlerts(data) {
        var list = byId("low-alerts-list");
        if (!list) {
            return;
        }

        list.innerHTML = "";
        data.lowAlerts.forEach(function (alert) {
            var li = document.createElement("li");
            li.className = "rounded-xl border border-brand-100 bg-white p-2.5";
            li.innerHTML = ""
                + "<div class=\"mb-1 flex items-start justify-between gap-2\">"
                    + "<div><p class=\"text-sm font-semibold text-ink-900\">" + alert.name + "</p><p class=\"text-xs text-ink-500\">" + alert.sku + " • " + alert.category + "</p></div>"
                    + "<span class=\"inventory-status inventory-status-low-stock\">" + alert.qty + " left</span>"
                + "</div>"
                + "<p class=\"text-xs text-ink-500\">Threshold: " + alert.threshold + "</p>";
            list.appendChild(li);
        });
    }

    function renderRestock(data) {
        var list = byId("restock-list");
        if (!list) {
            return;
        }

        list.innerHTML = "";
        data.lowAlerts.forEach(function (alert) {
            var suggested = Math.max(0, (alert.threshold * 2) - alert.qty);
            var li = document.createElement("li");
            li.className = "rounded-xl border border-brand-100 bg-white p-2.5";
            li.innerHTML = ""
                + "<p class=\"text-sm font-semibold text-ink-900\">" + alert.name + "</p>"
                + "<p class=\"text-xs text-ink-500\">Suggested reorder: <span class=\"font-semibold text-brand-700\">" + suggested + " " + (alert.unit || "units") + "</span></p>";
            list.appendChild(li);
        });
    }

    function renderTopConsumed(data) {
        var list = byId("top-consumed-list");
        if (!list) {
            return;
        }

        var maxIssued = (data.topConsumed || []).reduce(function (max, item) {
            return Math.max(max, item.issued);
        }, 1);

        list.innerHTML = "";
        (data.topConsumed || []).forEach(function (item, idx) {
            var ratio = Math.round((item.issued / maxIssued) * 100);
            var li = document.createElement("li");
            li.className = "rounded-xl border border-brand-100 bg-white p-2.5";
            li.innerHTML = ""
                + "<div class=\"mb-1 flex items-center justify-between gap-2\">"
                    + "<div class=\"flex items-center gap-2\"><span class=\"inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700\">" + (idx + 1) + "</span><p class=\"text-sm font-semibold text-ink-900\">" + item.name + "</p></div>"
                    + "<span class=\"text-sm font-semibold text-brand-700\">" + item.issued + " issued</span>"
                + "</div>"
                + "<div class=\"inventory-progress\"><div class=\"inventory-progress-fill\" style=\"width:" + ratio + "%\"></div></div>";
            list.appendChild(li);
        });
    }

    function renderActivity(data) {
        var list = byId("inventory-activity-list");
        if (!list) {
            return;
        }

        list.innerHTML = "";
        (data.activity || []).forEach(function (entry) {
            var li = document.createElement("li");
            li.className = "rounded-xl border border-brand-100 bg-white p-2.5";
            li.innerHTML = ""
                + "<div class=\"flex items-start gap-2\">"
                    + "<span class=\"inventory-icon-chip\" aria-hidden=\"true\">" + initials(entry.actor) + "</span>"
                    + "<div><p class=\"text-sm text-ink-900\"><span class=\"font-semibold\">" + entry.item + "</span> " + entry.action + " <span class=\"font-semibold text-brand-700\">(" + entry.qty + ")</span></p><p class=\"text-xs text-ink-500\">" + entry.actor + " • " + entry.time + "</p></div>"
                + "</div>";
            list.appendChild(li);
        });
    }

    function activeDesktopFilters() {
        return window.matchMedia("(min-width: 1280px)").matches;
    }

    function getFiltersFromUI() {
        var desktop = activeDesktopFilters();

        return {
            search: (byId("inventory-search") ? byId("inventory-search").value : "").trim().toLowerCase(),
            status: desktop ? (byId("inventory-status") ? byId("inventory-status").value : "All") : (byId("inventory-status-mobile") ? byId("inventory-status-mobile").value : "All"),
            category: desktop ? (byId("inventory-category") ? byId("inventory-category").value : "All") : (byId("inventory-category-mobile") ? byId("inventory-category-mobile").value : "All"),
            sort: byId("inventory-sort") ? byId("inventory-sort").value : "updated-desc",
            updatedFrom: desktop ? (byId("inventory-updated-from") ? byId("inventory-updated-from").value : "") : (byId("inventory-updated-from-mobile") ? byId("inventory-updated-from-mobile").value : ""),
            updatedTo: desktop ? (byId("inventory-updated-to") ? byId("inventory-updated-to").value : "") : (byId("inventory-updated-to-mobile") ? byId("inventory-updated-to-mobile").value : "")
        };
    }

    function matchesQuickFilter(item) {
        if (state.quickFilter === "All") {
            return true;
        }
        return item.status === state.quickFilter;
    }

    function buildDerivedData(filters) {
        var from = parseDate(filters.updatedFrom);
        var to = parseDate(filters.updatedTo);

        var items = (state.raw.items || []).filter(function (item) {
            var updated = parseDate(item.updated);
            var matchesSearch = !filters.search || item.name.toLowerCase().includes(filters.search) || item.sku.toLowerCase().includes(filters.search);
            var matchesStatus = filters.status === "All" || item.status === filters.status;
            var matchesCategory = filters.category === "All" || item.category === filters.category;
            var matchesFrom = !from || (updated && updated >= from);
            var matchesTo = !to || (updated && updated <= to);
            return matchesSearch && matchesStatus && matchesCategory && matchesFrom && matchesTo && matchesQuickFilter(item);
        });

        var lowAlerts = items.filter(function (item) {
            return item.status !== "In Stock";
        }).map(function (item) {
            return {
                sku: item.sku,
                name: item.name,
                qty: item.qty,
                threshold: item.reorder,
                category: item.category,
                unit: item.unit
            };
        });

        var summary = {
            value: items.reduce(function (sum, item) { return sum + (item.qty * 2); }, 0),
            items: items.reduce(function (sum, item) { return sum + item.qty; }, 0),
            lowStock: items.filter(function (item) { return item.status === "Low Stock"; }).length,
            outOfStock: items.filter(function (item) { return item.status === "Out of Stock"; }).length
        };

        return {
            summary: summary,
            movement: state.raw.movement,
            categories: state.raw.categories,
            lowAlerts: lowAlerts,
            topConsumed: state.raw.topConsumed,
            items: items,
            activity: state.raw.activity
        };
    }

    function summarizeFilters(filters) {
        var parts = [];
        if (filters.search) {
            parts.push("search: " + filters.search);
        }
        if (filters.status !== "All") {
            parts.push("status: " + filters.status);
        }
        if (filters.category !== "All") {
            parts.push("category: " + filters.category);
        }
        if (filters.updatedFrom || filters.updatedTo) {
            parts.push("updated: " + (filters.updatedFrom || "?") + " to " + (filters.updatedTo || "?"));
        }
        parts.push("quick: " + state.quickFilter);
        return parts.join(" | ");
    }

    function setQueryParams(filters) {
        var params = new URLSearchParams();
        Object.keys(filters).forEach(function (key) {
            if (filters[key]) {
                params.set(key, filters[key]);
            }
        });
        params.set("quick", state.quickFilter);
        params.set("range", state.range);
        window.history.replaceState({}, "", window.location.pathname + "?" + params.toString());
    }

    function compareItems(a, b) {
        if (state.sortKey === "qty") {
            return state.sortDir === "asc" ? a.qty - b.qty : b.qty - a.qty;
        }

        var da = parseDate(a.updated);
        var db = parseDate(b.updated);
        return state.sortDir === "asc" ? da - db : db - da;
    }

    function paginate(items) {
        var start = (state.page - 1) * state.pageSize;
        return items.slice(start, start + state.pageSize);
    }

    function setAriaSort() {
        document.querySelectorAll(".inventory-table th").forEach(function (th) {
            th.setAttribute("aria-sort", "none");
        });

        var sortButton = document.querySelector("[data-sort='" + state.sortKey + "']");
        if (sortButton) {
            var th = sortButton.closest("th");
            if (th) {
                th.setAttribute("aria-sort", state.sortDir === "asc" ? "ascending" : "descending");
            }
        }
    }

    function renderPagination(total) {
        var container = byId("inventory-pagination");
        if (!container) {
            return;
        }

        var pages = Math.max(1, Math.ceil(total / state.pageSize));
        if (state.page > pages) {
            state.page = pages;
        }

        container.innerHTML = "";

        var prev = document.createElement("button");
        prev.type = "button";
        prev.className = "inventory-focus rounded-full border border-brand-100 bg-white px-3 py-1 text-xs font-semibold text-ink-700 disabled:opacity-40";
        prev.textContent = "Prev";
        prev.disabled = state.page <= 1;
        prev.addEventListener("click", function () {
            if (state.page > 1) {
                state.page -= 1;
                renderTable();
            }
        });

        var label = document.createElement("span");
        label.className = "text-xs text-ink-500";
        label.textContent = "Page " + state.page + " of " + pages;

        var next = document.createElement("button");
        next.type = "button";
        next.className = "inventory-focus rounded-full border border-brand-100 bg-white px-3 py-1 text-xs font-semibold text-ink-700 disabled:opacity-40";
        next.textContent = "Next";
        next.disabled = state.page >= pages;
        next.addEventListener("click", function () {
            if (state.page < pages) {
                state.page += 1;
                renderTable();
            }
        });

        container.appendChild(prev);
        container.appendChild(label);
        container.appendChild(next);
    }

    function renderTable() {
        var body = byId("inventory-table-body");
        var count = byId("inventory-table-count");
        var selectAll = byId("inventory-select-all");
        if (!body || !count || !selectAll) {
            return;
        }

        var sorted = state.filteredItems.slice().sort(compareItems);
        var pageItems = paginate(sorted);

        body.innerHTML = "";

        pageItems.forEach(function (item) {
            var tr = document.createElement("tr");
            tr.innerHTML = ""
                + "<td><input type=\"checkbox\" class=\"inventory-focus inventory-row-check\" data-sku=\"" + item.sku + "\" aria-label=\"Select inventory item " + item.sku + "\" " + (state.selected.has(item.sku) ? "checked" : "") + " /></td>"
                + "<td>" + item.sku + "</td>"
                + "<td><div class=\"flex items-center gap-2\"><span class=\"inventory-icon-chip\" aria-hidden=\"true\">" + initials(item.name) + "</span><div><p class=\"text-sm font-semibold text-ink-900\">" + item.name + "</p><p class=\"text-xs text-ink-500\">ID: " + item.sku + "</p></div></div></td>"
                + "<td><span class=\"rounded-full bg-brand-50 px-2 py-1 text-xs font-semibold text-brand-700\">" + item.category + "</span></td>"
                + "<td class=\"font-semibold text-ink-900\">" + item.qty + "</td>"
                + "<td>" + item.unit + "</td>"
                + "<td><span class=\"" + statusClass(item.status) + "\">" + item.status + "</span></td>"
                + "<td>" + item.reorder + "</td>"
                + "<td>" + item.updated + "</td>"
                + "<td><span class=\"inventory-row-actions\">"
                    + "<button type=\"button\" class=\"inventory-focus rounded-lg p-1.5 text-brand-700 hover:bg-brand-50\" aria-label=\"View item " + item.sku + "\"><i data-lucide=\"eye\" class=\"h-4 w-4\"></i></button>"
                    + "<button type=\"button\" class=\"inventory-focus rounded-lg p-1.5 text-brand-700 hover:bg-brand-50\" aria-label=\"Edit item " + item.sku + "\"><i data-lucide=\"square-pen\" class=\"h-4 w-4\"></i></button>"
                    + "<button type=\"button\" class=\"inventory-focus rounded-lg p-1.5 text-brand-700 hover:bg-brand-50\" aria-label=\"Stock in item " + item.sku + "\"><i data-lucide=\"plus\" class=\"h-4 w-4\"></i></button>"
                    + "<button type=\"button\" class=\"inventory-focus rounded-lg p-1.5 text-brand-700 hover:bg-brand-50\" aria-label=\"Stock out item " + item.sku + "\"><i data-lucide=\"minus\" class=\"h-4 w-4\"></i></button>"
                    + "<button type=\"button\" class=\"inventory-focus rounded-lg p-1.5 text-red-600 hover:bg-red-50\" aria-label=\"Delete item " + item.sku + "\"><i data-lucide=\"trash-2\" class=\"h-4 w-4\"></i></button>"
                + "</span></td>";

            body.appendChild(tr);
        });

        count.textContent = state.filteredItems.length + " items";
        selectAll.checked = pageItems.length > 0 && pageItems.every(function (item) { return state.selected.has(item.sku); });

        renderPagination(sorted.length);

        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function syncDesktopMobileFilters() {
        var desktop = activeDesktopFilters();
        var pairs = [
            ["inventory-status", "inventory-status-mobile"],
            ["inventory-category", "inventory-category-mobile"],
            ["inventory-updated-from", "inventory-updated-from-mobile"],
            ["inventory-updated-to", "inventory-updated-to-mobile"]
        ];

        pairs.forEach(function (pair) {
            var d = byId(pair[0]);
            var m = byId(pair[1]);
            if (!d || !m) {
                return;
            }
            if (desktop) {
                m.value = d.value;
            } else {
                d.value = m.value;
            }
        });
    }

    function applyFilters() {
        syncDesktopMobileFilters();
        state.filters = getFiltersFromUI();

        if (state.filters.sort === "updated-desc") { state.sortKey = "updated"; state.sortDir = "desc"; }
        if (state.filters.sort === "updated-asc") { state.sortKey = "updated"; state.sortDir = "asc"; }
        if (state.filters.sort === "qty-desc") { state.sortKey = "qty"; state.sortDir = "desc"; }
        if (state.filters.sort === "qty-asc") { state.sortKey = "qty"; state.sortDir = "asc"; }

        var data = buildDerivedData(state.filters);
        state.filteredItems = data.items.slice();
        state.page = 1;

        initKpis(data.summary);
        renderLowAlerts(data);
        renderRestock(data);
        renderTopConsumed(data);
        renderActivity(data);
        updateCharts(state.filters);
        renderTable();
        setAriaSort();

        var summary = byId("inventory-filter-summary");
        if (summary) {
            summary.textContent = summarizeFilters(state.filters);
        }
        setQueryParams(state.filters);
    }

    function summarizeFilters(filters) {
        var parts = [];
        if (filters.search) { parts.push("search: " + filters.search); }
        if (filters.status !== "All") { parts.push("status: " + filters.status); }
        if (filters.category !== "All") { parts.push("category: " + filters.category); }
        if (filters.updatedFrom || filters.updatedTo) { parts.push("updated: " + (filters.updatedFrom || "?") + " to " + (filters.updatedTo || "?")); }
        parts.push("quick: " + state.quickFilter);
        return parts.join(" | ");
    }

    function setQueryParams(filters) {
        var params = new URLSearchParams();
        Object.keys(filters).forEach(function (key) {
            if (filters[key]) {
                params.set(key, filters[key]);
            }
        });
        params.set("quick", state.quickFilter);
        params.set("range", state.range);
        window.history.replaceState({}, "", window.location.pathname + "?" + params.toString());
    }

    function debounce(fn, wait) {
        var timer;
        return function () {
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(null, args);
            }, wait);
        };
    }

    function fetchInventorySummary(params) {
        return Promise.resolve({ params: params || {}, summary: state.raw.summary });
    }

    function fetchInventoryList(params) {
        return Promise.resolve({ params: params || {}, items: (state.raw.items || []).slice() });
    }

    function exportInventoryCSV(filters) {
        var rows = [
            ["SKU", "Item Name", "Category", "Quantity", "Unit", "Status", "Reorder Level", "Last Updated"]
        ];

        state.filteredItems.forEach(function (item) {
            rows.push([item.sku, item.name, item.category, String(item.qty), item.unit, item.status, String(item.reorder), item.updated]);
        });

        var csv = rows.map(function (row) {
            return row.map(function (value) {
                return '"' + String(value).replace(/"/g, '""') + '"';
            }).join(",");
        }).join("\n");

        var blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = url;
        link.download = "inventory-export.csv";
        link.click();
        URL.revokeObjectURL(url);

        return Promise.resolve({ endpoint: "/api/inventory/export", filters: filters || state.filters, exported: state.filteredItems.length });
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function placePopover(anchor, panel) {
        panel.style.visibility = "hidden";
        panel.style.display = "block";

        var a = anchor.getBoundingClientRect();
        var p = panel.getBoundingClientRect();
        var gap = 8;
        var vw = window.innerWidth;
        var vh = window.innerHeight;

        var candidates = [
            { top: a.bottom + gap, left: a.right - p.width },
            { top: a.top - p.height - gap, left: a.right - p.width },
            { top: a.bottom + gap, left: a.left },
            { top: a.top - p.height - gap, left: a.left }
        ];

        var best = { top: gap, left: gap, score: -1 };

        candidates.forEach(function (candidate) {
            var top = clamp(candidate.top, gap, vh - p.height - gap);
            var left = clamp(candidate.left, gap, vw - p.width - gap);
            var visibleW = Math.max(0, Math.min(left + p.width, vw) - Math.max(left, 0));
            var visibleH = Math.max(0, Math.min(top + p.height, vh) - Math.max(top, 0));
            var score = visibleW * visibleH;
            if (score > best.score) {
                best = { top: top, left: left, score: score };
            }
        });

        panel.style.top = best.top + "px";
        panel.style.left = best.left + "px";
        panel.style.visibility = "visible";
    }

    var activePopover = { anchor: null, panel: null };

    function closePopover() {
        if (!activePopover.panel) {
            return;
        }

        activePopover.panel.setAttribute("data-open", "false");
        activePopover.panel.style.display = "none";
        if (activePopover.anchor) {
            activePopover.anchor.setAttribute("aria-expanded", "false");
        }
        activePopover = { anchor: null, panel: null };
    }

    function togglePopover(anchor, panel) {
        var isSame = activePopover.panel === panel && panel.getAttribute("data-open") === "true";
        closePopover();
        if (isSame) {
            return;
        }

        panel.setAttribute("data-open", "true");
        panel.style.display = "block";
        anchor.setAttribute("aria-expanded", "true");
        placePopover(anchor, panel);
        activePopover = { anchor: anchor, panel: panel };
    }

    function wirePopoverClose() {
        document.addEventListener("click", function (event) {
            var target = event.target;
            if (activePopover.panel && activePopover.panel.contains(target)) {
                return;
            }
            if (activePopover.anchor && activePopover.anchor.contains(target)) {
                return;
            }
            closePopover();
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closePopover();
            }
        });

        window.addEventListener("resize", function () {
            if (activePopover.anchor && activePopover.panel) {
                placePopover(activePopover.anchor, activePopover.panel);
            }
        });

        window.addEventListener("scroll", function () {
            if (activePopover.anchor && activePopover.panel) {
                placePopover(activePopover.anchor, activePopover.panel);
            }
        }, { passive: true });
    }

    function wireControls() {
        var apply = byId("inventory-apply-filters");
        if (apply) {
            apply.addEventListener("click", applyFilters);
        }

        var applyMobile = byId("inventory-apply-mobile");
        if (applyMobile) {
            applyMobile.addEventListener("click", function () {
                applyFilters();
                closePopover();
            });
        }

        var openMobileFilters = byId("open-mobile-inventory-filters");
        var mobileFiltersPanel = byId("inventory-mobile-filters");
        if (openMobileFilters && mobileFiltersPanel) {
            openMobileFilters.addEventListener("click", function () {
                togglePopover(openMobileFilters, mobileFiltersPanel);
            });
        }

        var search = byId("inventory-search");
        if (search) {
            search.addEventListener("input", debounce(applyFilters, 280));
        }

        [
            "inventory-status", "inventory-category", "inventory-sort", "inventory-updated-from", "inventory-updated-to",
            "inventory-status-mobile", "inventory-category-mobile", "inventory-updated-from-mobile", "inventory-updated-to-mobile"
        ].forEach(function (id) {
            var el = byId(id);
            if (el) {
                el.addEventListener("change", syncDesktopMobileFilters);
            }
        });

        document.querySelectorAll("[data-range]").forEach(function (tab) {
            tab.addEventListener("click", function () {
                state.range = tab.getAttribute("data-range") || "weekly";
                document.querySelectorAll("[data-range]").forEach(function (btn) {
                    btn.setAttribute("aria-selected", btn === tab ? "true" : "false");
                });
                updateCharts(state.filters);
            });
        });

        document.querySelectorAll("[data-quick]").forEach(function (tab) {
            tab.addEventListener("click", function () {
                state.quickFilter = tab.getAttribute("data-quick") || "All";
                document.querySelectorAll("[data-quick]").forEach(function (btn) {
                    btn.setAttribute("aria-selected", btn === tab ? "true" : "false");
                });
                applyFilters();
            });
        });

        document.querySelectorAll("[data-sort]").forEach(function (sortButton) {
            sortButton.addEventListener("click", function () {
                var key = sortButton.getAttribute("data-sort");
                if (!key) {
                    return;
                }
                if (state.sortKey === key) {
                    state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
                } else {
                    state.sortKey = key;
                    state.sortDir = "asc";
                }
                setAriaSort();
                renderTable();
            });
        });

        var pageSize = byId("inventory-page-size");
        if (pageSize) {
            pageSize.addEventListener("change", function () {
                state.pageSize = Number(pageSize.value) || 5;
                state.page = 1;
                renderTable();
            });
        }

        var selectAll = byId("inventory-select-all");
        if (selectAll) {
            selectAll.addEventListener("change", function () {
                var pageItems = paginate(state.filteredItems.slice().sort(compareItems));
                pageItems.forEach(function (item) {
                    if (selectAll.checked) {
                        state.selected.add(item.sku);
                    } else {
                        state.selected.delete(item.sku);
                    }
                });
                renderTable();
            });
        }

        var tableBody = byId("inventory-table-body");
        if (tableBody) {
            tableBody.addEventListener("change", function (event) {
                var check = event.target.closest(".inventory-row-check");
                if (!check) {
                    return;
                }
                var sku = check.getAttribute("data-sku");
                if (!sku) {
                    return;
                }
                if (check.checked) {
                    state.selected.add(sku);
                } else {
                    state.selected.delete(sku);
                }
            });
        }

        var bulkIn = byId("inventory-bulk-stock-in");
        if (bulkIn) {
            bulkIn.addEventListener("click", function () {
                if (!state.selected.size) {
                    return;
                }
                state.raw.items = state.raw.items.map(function (item) {
                    if (state.selected.has(item.sku)) {
                        var nextQty = item.qty + 10;
                        return {
                            sku: item.sku,
                            name: item.name,
                            category: item.category,
                            qty: nextQty,
                            unit: item.unit,
                            status: nextQty <= 0 ? "Out of Stock" : (nextQty <= item.reorder ? "Low Stock" : "In Stock"),
                            reorder: item.reorder,
                            updated: new Date().toISOString().slice(0, 10)
                        };
                    }
                    return item;
                });
                state.selected.clear();
                applyFilters();
            });
        }

        var bulkOut = byId("inventory-bulk-stock-out");
        if (bulkOut) {
            bulkOut.addEventListener("click", function () {
                if (!state.selected.size) {
                    return;
                }
                state.raw.items = state.raw.items.map(function (item) {
                    if (state.selected.has(item.sku)) {
                        var nextQty = Math.max(0, item.qty - 10);
                        return {
                            sku: item.sku,
                            name: item.name,
                            category: item.category,
                            qty: nextQty,
                            unit: item.unit,
                            status: nextQty <= 0 ? "Out of Stock" : (nextQty <= item.reorder ? "Low Stock" : "In Stock"),
                            reorder: item.reorder,
                            updated: new Date().toISOString().slice(0, 10)
                        };
                    }
                    return item;
                });
                state.selected.clear();
                applyFilters();
            });
        }

        var exportCsv = byId("inventory-export-csv");
        if (exportCsv) {
            exportCsv.addEventListener("click", function () {
                exportInventoryCSV(state.filters);
            });
        }
    }

    function lazyInitCharts() {
        var target = byId("inventory-movement-chart");
        if (!target || !("IntersectionObserver" in window)) {
            renderInventoryCharts(state.raw);
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    renderInventoryCharts(state.raw);
                    observer.disconnect();
                }
            });
        }, { rootMargin: "180px 0px" });

        observer.observe(target);
    }

    function initialize() {
        fetchInventorySummary({}).then(function () {
            initKpis(state.raw.summary || {});
            renderLowAlerts(state.raw);
            renderRestock(state.raw);
            renderTopConsumed(state.raw);
            renderActivity(state.raw);
            lazyInitCharts();
            wireControls();
            wirePopoverClose();
            applyFilters();

            if (window.lucide && typeof window.lucide.createIcons === "function") {
                window.lucide.createIcons();
            }
        });

        fetchInventoryList({});
    }

    window.fetchInventorySummary = fetchInventorySummary;
    window.fetchInventoryList = fetchInventoryList;
    window.renderInventoryCharts = renderInventoryCharts;
    window.updateCharts = updateCharts;
    window.applyFilters = applyFilters;
    window.exportInventoryCSV = exportInventoryCSV;

    document.addEventListener("DOMContentLoaded", initialize);
})();

(function () {
    "use strict";

    var sampleNode = document.getElementById("payops-sample-data");
    if (!sampleNode) {
        return;
    }

    var SAMPLE_DATA = JSON.parse(sampleNode.textContent || "{}");

    var state = {
        raw: SAMPLE_DATA,
        filtered: (SAMPLE_DATA.transactions || []).slice(),
        selected: new Set(),
        page: 1,
        pageSize: 5,
        sortKey: "date",
        sortDir: "desc",
        quickFilter: "All",
        range: "daily",
        loading: true,
        filters: {
            search: "",
            status: "All",
            method: "All",
            dateFrom: "",
            dateTo: "",
            sort: "date-desc"
        },
        chartsReady: false,
        charts: {
            trend: null,
            status: null,
            methods: null
        }
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function buildTableActionControl(rowId) {
        var template = byId("table-actions-template");
        if (!template) {
            return "";
        }

        return template.innerHTML.split("__ROW_ID__").join(String(rowId || ""));
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
        if (status === "Completed") {
            return "payops-status payops-status-completed";
        }

        if (status === "Pending") {
            return "payops-status payops-status-pending";
        }

        if (status === "Refunded") {
            return "payops-status payops-status-refunded";
        }

        if (status === "Canceled") {
            return "payops-status payops-status-canceled";
        }

        return "payops-status payops-status-failed";
    }

    function chartTheme() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1900,
                easing: "easeInOutCubic"
            },
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

    function getRangeData() {
        var trend = state.raw.trend || {};
        return trend[state.range] || trend.daily || { labels: [], revenue: [], orders: [] };
    }

    function renderKpis(summary) {
        byId("kpi-revenue").textContent = currency(summary.revenue);
        byId("kpi-completed").textContent = Number(summary.completedOrders || 0).toLocaleString();
        byId("kpi-pending").textContent = Number(summary.pendingPayments || 0).toLocaleString();
        byId("kpi-canceled").textContent = Number(summary.canceledRefunded || 0).toLocaleString();

        if (window.AdminPanelAnimations && typeof window.AdminPanelAnimations.animateAll === "function") {
            window.AdminPanelAnimations.animateAll(document);
        }

        document.dispatchEvent(new CustomEvent("admin:panel-rendered", {
            detail: {
                panelUrl: window.location.pathname + window.location.search + window.location.hash
            }
        }));
    }

    function deriveSummary(transactions) {
        var revenue = transactions.reduce(function (sum, tx) {
            return sum + tx.amount;
        }, 0);

        var completedOrders = transactions.filter(function (tx) {
            return tx.status === "Completed";
        }).length;

        var pendingPayments = transactions.filter(function (tx) {
            return tx.status === "Pending";
        }).length;

        var canceledRefunded = transactions.filter(function (tx) {
            return tx.status === "Canceled" || tx.status === "Refunded";
        }).length;

        return {
            revenue: revenue,
            completedOrders: completedOrders,
            pendingPayments: pendingPayments,
            canceledRefunded: canceledRefunded,
            revenueChange: state.raw.summary ? state.raw.summary.revenueChange : 0,
            aov: transactions.length ? Math.round(revenue / transactions.length) : 0,
            dailyVolume: state.raw.summary ? state.raw.summary.dailyVolume : 0
        };
    }

    function deriveStatusOverview(transactions) {
        return transactions.reduce(function (acc, tx) {
            acc[tx.status] = (acc[tx.status] || 0) + 1;
            return acc;
        }, { Completed: 0, Pending: 0, Canceled: 0, Refunded: 0, Failed: 0 });
    }

    function derivePaymentMethods(transactions) {
        return transactions.reduce(function (acc, tx) {
            acc[tx.method] = (acc[tx.method] || 0) + tx.amount;
            return acc;
        }, { "Credit Card": 0, "Bank Transfer": 0, Cash: 0, "E-wallet": 0, COD: 0 });
    }

    function buildDerivedData(filters) {
        var from = parseDate(filters.dateFrom);
        var to = parseDate(filters.dateTo);
        var search = (filters.search || "").toLowerCase();

        var transactions = (state.raw.transactions || []).filter(function (tx) {
            var txDate = parseDate(tx.date);
            var matchesSearch = !search || tx.customer.toLowerCase().includes(search) || tx.orderId.toLowerCase().includes(search) || tx.email.toLowerCase().includes(search);
            var matchesStatus = filters.status === "All" || tx.status === filters.status;
            var matchesMethod = filters.method === "All" || tx.method === filters.method;
            var matchesFrom = !from || (txDate && txDate >= from);
            var matchesTo = !to || (txDate && txDate <= to);
            var matchesQuick = state.quickFilter === "All" || tx.status === state.quickFilter;
            return matchesSearch && matchesStatus && matchesMethod && matchesFrom && matchesTo && matchesQuick;
        });

        return {
            summary: deriveSummary(transactions),
            statusOverview: deriveStatusOverview(transactions),
            paymentMethods: derivePaymentMethods(transactions),
            trend: state.raw.trend,
            topCustomers: state.raw.topCustomers || [],
            topProducts: state.raw.topProducts || [],
            transactions: transactions
        };
    }

    function renderCharts(data) {
        if (typeof Chart === "undefined") {
            return;
        }

        var rangeData = getRangeData();

        if (!state.chartsReady) {
            state.charts.trend = new Chart(byId("payops-sales-trend-chart"), {
                type: "line",
                data: {
                    labels: rangeData.labels,
                    datasets: [
                        {
                            label: "Revenue",
                            data: rangeData.revenue,
                            borderColor: "#0f766e",
                            backgroundColor: "rgba(15, 118, 110, 0.12)",
                            fill: true,
                            pointRadius: 2,
                            tension: 0.35
                        },
                        {
                            label: "Orders",
                            data: rangeData.orders,
                            borderColor: "#14b8a6",
                            backgroundColor: "rgba(20, 184, 166, 0.10)",
                            fill: true,
                            pointRadius: 2,
                            tension: 0.3,
                            yAxisID: "y1"
                        }
                    ]
                },
                options: Object.assign(chartTheme(), {
                    scales: {
                        x: { ticks: { color: "#236e67" }, grid: { color: "rgba(35, 110, 103, 0.12)" } },
                        y: { beginAtZero: true, ticks: { color: "#236e67" }, grid: { color: "rgba(35, 110, 103, 0.12)" } },
                        y1: { beginAtZero: true, position: "right", ticks: { color: "#236e67" }, grid: { drawOnChartArea: false } }
                    }
                })
            });

            state.charts.status = new Chart(byId("payops-order-status-chart"), {
                type: "doughnut",
                data: {
                    labels: Object.keys(data.statusOverview),
                    datasets: [{
                        data: Object.values(data.statusOverview),
                        backgroundColor: ["rgba(16, 185, 129, 0.86)", "rgba(245, 158, 11, 0.82)", "rgba(239, 68, 68, 0.82)", "rgba(148, 163, 184, 0.8)", "rgba(239, 68, 68, 0.65)"],
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

            state.charts.methods = new Chart(byId("payops-method-chart"), {
                type: "bar",
                data: {
                    labels: Object.keys(data.paymentMethods),
                    datasets: [{
                        label: "Revenue",
                        data: Object.values(data.paymentMethods),
                        borderRadius: 10,
                        maxBarThickness: 30,
                        backgroundColor: ["rgba(15, 118, 110, 0.86)", "rgba(16, 185, 129, 0.82)", "rgba(110, 231, 183, 0.82)", "rgba(20, 184, 166, 0.78)", "rgba(45, 212, 191, 0.7)"]
                    }]
                },
                options: Object.assign(chartTheme(), {
                    plugins: { legend: { display: false }, tooltip: chartTheme().plugins.tooltip },
                    scales: {
                        x: { ticks: { color: "#236e67" }, grid: { display: false } },
                        y: { beginAtZero: true, ticks: { color: "#236e67" }, grid: { color: "rgba(35, 110, 103, 0.12)" } }
                    }
                })
            });

            state.chartsReady = true;
            return;
        }

        state.charts.trend.data.labels = rangeData.labels;
        state.charts.trend.data.datasets[0].data = rangeData.revenue;
        state.charts.trend.data.datasets[1].data = rangeData.orders;
        state.charts.trend.update();

        state.charts.status.data.labels = Object.keys(data.statusOverview);
        state.charts.status.data.datasets[0].data = Object.values(data.statusOverview);
        state.charts.status.update();

        state.charts.methods.data.labels = Object.keys(data.paymentMethods);
        state.charts.methods.data.datasets[0].data = Object.values(data.paymentMethods);
        state.charts.methods.update();
    }

    function updateCharts(filters) {
        renderCharts(buildDerivedData(filters || state.filters));
    }

    function renderSuccessRate(statusOverview) {
        var total = Object.values(statusOverview).reduce(function (sum, value) { return sum + value; }, 0) || 1;
        var successPct = Math.round(((statusOverview.Completed || 0) / total) * 100);
        var pendingPct = Math.round(((statusOverview.Pending || 0) / total) * 100);
        var failedPct = Math.round((((statusOverview.Failed || 0) + (statusOverview.Canceled || 0)) / total) * 100);

        byId("payops-success-headline").textContent = successPct + "%";
        byId("payops-success-share").textContent = successPct + "%";
        byId("payops-pending-share").textContent = pendingPct + "%";
        byId("payops-failed-share").textContent = failedPct + "%";
        byId("payops-success-bar").style.width = successPct + "%";
        byId("payops-pending-bar").style.width = pendingPct + "%";
        byId("payops-failed-bar").style.width = failedPct + "%";
    }

    function renderTopCustomers(data) {
        var list = byId("payops-top-customers");
        if (!list) {
            return;
        }

        var maxSpend = (data.topCustomers || []).reduce(function (max, customer) {
            return Math.max(max, customer.spent);
        }, 1);

        list.innerHTML = "";
        (data.topCustomers || []).forEach(function (customer, index) {
            var ratio = Math.round((customer.spent / maxSpend) * 100);
            var item = document.createElement("li");
            item.className = "rounded-xl border border-brand-100 bg-white p-2.5";
            item.innerHTML = ""
                + "<div class=\"mb-1 flex items-center justify-between gap-2\">"
                    + "<div class=\"flex items-center gap-2\"><span class=\"inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700\">" + (index + 1) + "</span><div><p class=\"text-sm font-semibold text-ink-900\">" + customer.name + "</p><p class=\"text-xs text-ink-500\">" + customer.orders + " orders</p></div></div>"
                    + "<span class=\"text-sm font-semibold text-brand-700\">" + currency(customer.spent) + "</span>"
                + "</div>"
                + "<div class=\"payops-progress\"><div class=\"payops-progress-fill\" style=\"width:" + ratio + "%\"></div></div>";
            list.appendChild(item);
        });
    }

    function renderTopProducts(data) {
        var list = byId("payops-best-products");
        if (!list) {
            return;
        }

        var maxUnits = (data.topProducts || []).reduce(function (max, product) {
            return Math.max(max, product.units);
        }, 1);

        list.innerHTML = "";
        (data.topProducts || []).forEach(function (product, index) {
            var ratio = Math.round((product.units / maxUnits) * 100);
            var item = document.createElement("li");
            item.className = "rounded-xl border border-brand-100 bg-white p-2.5";
            item.innerHTML = ""
                + "<div class=\"mb-1 flex items-center justify-between gap-2\">"
                    + "<div class=\"flex items-center gap-2\"><span class=\"inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700\">" + (index + 1) + "</span><div><p class=\"text-sm font-semibold text-ink-900\">" + product.name + "</p><p class=\"text-xs text-ink-500\">" + product.units + " sold</p></div></div>"
                    + "<span class=\"text-sm font-semibold text-brand-700\">" + currency(product.revenue) + "</span>"
                + "</div>"
                + "<div class=\"payops-progress\"><div class=\"payops-progress-fill\" style=\"width:" + ratio + "%\"></div></div>";
            list.appendChild(item);
        });
    }

    function activeDesktopFilters() {
        return window.matchMedia("(min-width: 1280px)").matches;
    }

    function getFiltersFromUI() {
        var desktop = activeDesktopFilters();

        return {
            search: (byId("payops-search") ? byId("payops-search").value : "").trim().toLowerCase(),
            status: desktop ? (byId("payops-status") ? byId("payops-status").value : "All") : (byId("payops-status-mobile") ? byId("payops-status-mobile").value : "All"),
            method: desktop ? (byId("payops-method") ? byId("payops-method").value : "All") : (byId("payops-method-mobile") ? byId("payops-method-mobile").value : "All"),
            dateFrom: desktop ? (byId("payops-date-from") ? byId("payops-date-from").value : "") : (byId("payops-date-from-mobile") ? byId("payops-date-from-mobile").value : ""),
            dateTo: desktop ? (byId("payops-date-to") ? byId("payops-date-to").value : "") : (byId("payops-date-to-mobile") ? byId("payops-date-to-mobile").value : ""),
            sort: byId("payops-sort") ? byId("payops-sort").value : "date-desc"
        };
    }

    function syncDesktopMobileFilters() {
        var desktop = activeDesktopFilters();
        var pairs = [
            ["payops-status", "payops-status-mobile"],
            ["payops-method", "payops-method-mobile"],
            ["payops-date-from", "payops-date-from-mobile"],
            ["payops-date-to", "payops-date-to-mobile"]
        ];

        pairs.forEach(function (pair) {
            var desktopControl = byId(pair[0]);
            var mobileControl = byId(pair[1]);
            if (!desktopControl || !mobileControl) {
                return;
            }

            if (desktop) {
                mobileControl.value = desktopControl.value;
            } else {
                desktopControl.value = mobileControl.value;
            }
        });
    }

    function compareTransactions(a, b) {
        if (state.sortKey === "amount") {
            return state.sortDir === "asc" ? a.amount - b.amount : b.amount - a.amount;
        }

        var da = parseDate(a.date);
        var db = parseDate(b.date);
        return state.sortDir === "asc" ? da - db : db - da;
    }

    function paginate(items) {
        return items;
    }

    function setAriaSort() {
        document.querySelectorAll(".payops-table th").forEach(function (th) {
            th.setAttribute("aria-sort", "none");
        });

        var activeSort = document.querySelector("[data-sort='" + state.sortKey + "']");
        if (activeSort) {
            var th = activeSort.closest("th");
            if (th) {
                th.setAttribute("aria-sort", state.sortDir === "asc" ? "ascending" : "descending");
            }
        }
    }

    function renderPagination(total) {
        return;
    }

    function requestRowAction(action, orderId) {
        var endpointMap = {
            "view": "/orders/" + orderId + "/",
            "invoice": "/orders/" + orderId + "/invoice/",
            "mark-paid": "/api/orders/" + orderId + "/mark-paid",
            "refund": "/api/orders/" + orderId + "/refund",
            "cancel": "/api/orders/" + orderId + "/cancel"
        };

        var endpoint = endpointMap[action];
        if (!endpoint) {
            return Promise.resolve();
        }

        if (action === "view" || action === "invoice") {
            window.location.href = endpoint;
            return Promise.resolve();
        }

        return fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ orderId: orderId })
        }).catch(function () {
            return Promise.resolve();
        });
    }

    function renderTable() {
        var tableBody = byId("payops-table-body");
        var tableCount = byId("payops-table-count");
        var selectAll = byId("payops-select-all");
        var tableShell = byId("payops-table-shell");
        var empty = byId("payops-empty-state");
        var skeleton = byId("payops-table-skeleton");

        if (!tableBody || !tableCount || !selectAll || !tableShell || !empty || !skeleton) {
            return;
        }

        var sorted = state.filtered.slice().sort(compareTransactions);
        var visibleItems = paginate(sorted);

        tableBody.innerHTML = "";

        visibleItems.forEach(function (tx) {
            var row = document.createElement("tr");
            var rowActionControl = buildTableActionControl(tx.orderId);
            row.innerHTML = ""
                + "<td><input type=\"checkbox\" class=\"payops-focus payops-row-check\" data-order=\"" + tx.orderId + "\" aria-label=\"Select order " + tx.orderId + "\" " + (state.selected.has(tx.orderId) ? "checked" : "") + " /></td>"
                + "<td><a href=\"/orders/" + tx.orderId + "/\" class=\"font-semibold text-brand-700 hover:underline\">" + tx.orderId + "</a></td>"
                + "<td><div class=\"flex items-center gap-2\"><span class=\"payops-avatar\" aria-hidden=\"true\">" + initials(tx.customer) + "</span><p class=\"text-sm font-semibold text-ink-900\">" + tx.customer + "</p></div></td>"
                + "<td><a href=\"mailto:" + tx.email + "\" class=\"text-sm text-ink-700 hover:text-brand-700\">" + tx.email + "</a></td>"
                + "<td class=\"font-semibold text-brand-700\">" + currency(tx.amount) + "</td>"
                + "<td>" + tx.method + "</td>"
                + "<td><span class=\"" + statusClass(tx.status) + "\">" + tx.status + "</span></td>"
                + "<td>" + tx.date + "</td>"
                + "<td class=\"text-right\" data-id=\"" + tx.orderId + "\">" + rowActionControl + "</td>";

            tableBody.appendChild(row);
        });

        tableCount.textContent = state.filtered.length + " records";
        selectAll.checked = visibleItems.length > 0 && visibleItems.every(function (tx) { return state.selected.has(tx.orderId); });

        skeleton.classList.add("hidden");
        tableShell.classList.remove("hidden");
        empty.classList.toggle("hidden", state.filtered.length !== 0);

        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function summarizeFilters(filters) {
        var parts = [];
        if (filters.search) { parts.push("search: " + filters.search); }
        if (filters.status !== "All") { parts.push("status: " + filters.status); }
        if (filters.method !== "All") { parts.push("method: " + filters.method); }
        if (filters.dateFrom || filters.dateTo) { parts.push("date: " + (filters.dateFrom || "?") + " to " + (filters.dateTo || "?")); }
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

    function applyFilters() {
        syncDesktopMobileFilters();
        state.filters = getFiltersFromUI();

        if (state.filters.sort === "date-desc") { state.sortKey = "date"; state.sortDir = "desc"; }
        if (state.filters.sort === "date-asc") { state.sortKey = "date"; state.sortDir = "asc"; }
        if (state.filters.sort === "amount-desc") { state.sortKey = "amount"; state.sortDir = "desc"; }
        if (state.filters.sort === "amount-asc") { state.sortKey = "amount"; state.sortDir = "asc"; }

        var data = buildDerivedData(state.filters);
        state.filtered = data.transactions.slice();
        state.page = 1;

        renderKpis(data.summary);
        renderSuccessRate(data.statusOverview);
        renderTopCustomers(data);
        renderTopProducts(data);
        updateCharts(state.filters);
        renderTable();
        setAriaSort();

        byId("payops-aov").textContent = currency(data.summary.aov);
        byId("payops-refund-summary").textContent = (data.statusOverview.Refunded || 0) + " refunded, " + (data.statusOverview.Canceled || 0) + " canceled";
        byId("payops-daily-volume").textContent = (data.summary.dailyVolume || 0) + " orders / day";
        var filterSummary = byId("payops-filter-summary");
        if (filterSummary) {
            filterSummary.textContent = summarizeFilters(state.filters);
        }
        setQueryParams(state.filters);
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

    function fetchPaymentsSummary(params) {
        return Promise.resolve({ params: params || {}, summary: state.raw.summary });
    }

    function fetchPaymentsList(params) {
        return Promise.resolve({ params: params || {}, transactions: (state.raw.transactions || []).slice() });
    }

    function exportPayments(format, filters) {
        var endpoint = format === "pdf" ? "/api/payments/export/pdf" : "/api/payments/export/csv";

        return fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ filters: filters || state.filters, rows: state.filtered })
        }).catch(function () {
            if (format === "csv") {
                var rows = [["Order ID", "Customer", "Email", "Amount", "Method", "Status", "Date"]];
                state.filtered.forEach(function (tx) {
                    rows.push([tx.orderId, tx.customer, tx.email, String(tx.amount), tx.method, tx.status, tx.date]);
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
                link.download = "payments-export.csv";
                link.click();
                URL.revokeObjectURL(url);
            }
            return Promise.resolve({ endpoint: endpoint, filters: filters || state.filters });
        });
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
        var same = activePopover.panel === panel && panel.getAttribute("data-open") === "true";
        closePopover();
        if (same) {
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

    function handleBulkAction(action) {
        if (!state.selected.size) {
            closePopover();
            return;
        }

        if (action === "export") {
            exportPayments("csv", state.filters);
        }

        if (action === "mark-paid") {
            state.raw.transactions = state.raw.transactions.map(function (tx) {
                if (state.selected.has(tx.orderId)) {
                    return {
                        orderId: tx.orderId,
                        customer: tx.customer,
                        email: tx.email,
                        amount: tx.amount,
                        method: tx.method,
                        status: "Completed",
                        date: tx.date
                    };
                }
                return tx;
            });
        }

        if (action === "refund") {
            state.raw.transactions = state.raw.transactions.map(function (tx) {
                if (state.selected.has(tx.orderId)) {
                    return {
                        orderId: tx.orderId,
                        customer: tx.customer,
                        email: tx.email,
                        amount: tx.amount,
                        method: tx.method,
                        status: "Refunded",
                        date: tx.date
                    };
                }
                return tx;
            });
        }

        state.selected.clear();
        applyFilters();
        closePopover();
    }

    function wireControls() {
        var apply = byId("payops-apply");
        if (apply) {
            apply.addEventListener("click", applyFilters);
        }

        var applyMobile = byId("payops-apply-mobile");
        if (applyMobile) {
            applyMobile.addEventListener("click", function () {
                applyFilters();
                closePopover();
            });
        }

        var search = byId("payops-search");
        if (search) {
            search.addEventListener("input", debounce(applyFilters, 280));
        }

        [
            "payops-status", "payops-method", "payops-date-from", "payops-date-to", "payops-sort",
            "payops-status-mobile", "payops-method-mobile", "payops-date-from-mobile", "payops-date-to-mobile"
        ].forEach(function (id) {
            var el = byId(id);
            if (el) {
                el.addEventListener("change", syncDesktopMobileFilters);
            }
        });

        document.querySelectorAll("[data-range]").forEach(function (tab) {
            tab.addEventListener("click", function () {
                state.range = tab.getAttribute("data-range") || "daily";
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

        document.querySelectorAll("[data-sort]").forEach(function (button) {
            button.addEventListener("click", function () {
                var key = button.getAttribute("data-sort");
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

        var selectAll = byId("payops-select-all");
        if (selectAll) {
            selectAll.addEventListener("change", function () {
                var visibleItems = paginate(state.filtered.slice().sort(compareTransactions));
                visibleItems.forEach(function (tx) {
                    if (selectAll.checked) {
                        state.selected.add(tx.orderId);
                    } else {
                        state.selected.delete(tx.orderId);
                    }
                });
                renderTable();
            });
        }

        var tableBody = byId("payops-table-body");
        if (tableBody) {
            tableBody.addEventListener("change", function (event) {
                var check = event.target.closest(".payops-row-check");
                if (!check) {
                    return;
                }
                var orderId = check.getAttribute("data-order");
                if (!orderId) {
                    return;
                }
                if (check.checked) {
                    state.selected.add(orderId);
                } else {
                    state.selected.delete(orderId);
                }
            });

            tableBody.addEventListener("click", function (event) {
                var actionButton = event.target.closest("[data-row-action]");
                if (!actionButton) {
                    return;
                }
                var action = actionButton.getAttribute("data-row-action");
                var orderId = actionButton.getAttribute("data-order");
                if (!action || !orderId) {
                    return;
                }
                requestRowAction(action, orderId).then(function () {
                    if (action === "mark-paid") {
                        state.raw.transactions = state.raw.transactions.map(function (tx) {
                            if (tx.orderId === orderId) {
                                return {
                                    orderId: tx.orderId,
                                    customer: tx.customer,
                                    email: tx.email,
                                    amount: tx.amount,
                                    method: tx.method,
                                    status: "Completed",
                                    date: tx.date
                                };
                            }
                            return tx;
                        });
                        applyFilters();
                    }
                    if (action === "refund") {
                        state.raw.transactions = state.raw.transactions.map(function (tx) {
                            if (tx.orderId === orderId) {
                                return {
                                    orderId: tx.orderId,
                                    customer: tx.customer,
                                    email: tx.email,
                                    amount: tx.amount,
                                    method: tx.method,
                                    status: "Refunded",
                                    date: tx.date
                                };
                            }
                            return tx;
                        });
                        applyFilters();
                    }
                    if (action === "cancel") {
                        state.raw.transactions = state.raw.transactions.map(function (tx) {
                            if (tx.orderId === orderId) {
                                return {
                                    orderId: tx.orderId,
                                    customer: tx.customer,
                                    email: tx.email,
                                    amount: tx.amount,
                                    method: tx.method,
                                    status: "Canceled",
                                    date: tx.date
                                };
                            }
                            return tx;
                        });
                        applyFilters();
                    }
                });
            });
        }

        var exportCsv = byId("payops-export-csv");
        if (exportCsv) {
            exportCsv.addEventListener("click", function () {
                exportPayments("csv", state.filters);
            });
        }

        var exportPdf = byId("payops-export-pdf");
        if (exportPdf) {
            exportPdf.addEventListener("click", function () {
                exportPayments("pdf", state.filters);
            });
        }

        var salesReport = byId("payops-sales-report");
        if (salesReport) {
            salesReport.addEventListener("click", function () {
                exportPayments("pdf", state.filters);
            });
        }

        var refunds = byId("payops-view-refunds");
        if (refunds) {
            refunds.addEventListener("click", function () {
                state.quickFilter = "Refunded";
                document.querySelectorAll("[data-quick]").forEach(function (btn) {
                    btn.setAttribute("aria-selected", btn.getAttribute("data-quick") === "Refunded" ? "true" : "false");
                });
                applyFilters();
            });
        }

        var openMobile = byId("payops-open-mobile-filters");
        var mobilePanel = byId("payops-mobile-filters");
        if (openMobile && mobilePanel) {
            openMobile.addEventListener("click", function () {
                togglePopover(openMobile, mobilePanel);
            });
        }

        var bulkButton = byId("payops-bulk-actions");
        var bulkPopover = byId("payops-bulk-popover");
        if (bulkButton && bulkPopover) {
            bulkButton.addEventListener("click", function () {
                togglePopover(bulkButton, bulkPopover);
            });

            bulkPopover.addEventListener("click", function (event) {
                var actionButton = event.target.closest("[data-bulk-action]");
                if (!actionButton) {
                    return;
                }
                var action = actionButton.getAttribute("data-bulk-action");
                if (!action) {
                    return;
                }
                handleBulkAction(action);
            });
        }
    }

    function lazyInitCharts() {
        var target = byId("payops-sales-trend-chart");
        if (!target || !("IntersectionObserver" in window)) {
            renderCharts(state.raw);
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    renderCharts(state.raw);
                    observer.disconnect();
                }
            });
        }, { rootMargin: "180px 0px" });

        observer.observe(target);
    }

    function setCollapsibleState(card, isOpen) {
        if (!card) {
            return;
        }

        card.setAttribute("data-open", isOpen ? "true" : "false");
        var trigger = card.querySelector(".payops-collapse-trigger");
        if (trigger) {
            trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }
    }

    function initCollapsibleCards() {
        var groups = document.querySelectorAll("[data-accordion]");
        groups.forEach(function (group) {
            var accordionMode = group.getAttribute("data-accordion") === "true";
            group.querySelectorAll(".payops-collapsible").forEach(function (card) {
                var trigger = card.querySelector(".payops-collapse-trigger");
                if (!trigger) {
                    return;
                }

                trigger.addEventListener("click", function () {
                    var isOpen = card.getAttribute("data-open") === "true";

                    if (accordionMode) {
                        group.querySelectorAll(".payops-collapsible").forEach(function (otherCard) {
                            setCollapsibleState(otherCard, false);
                        });
                        if (!isOpen) {
                            setCollapsibleState(card, true);
                        }
                    } else {
                        setCollapsibleState(card, !isOpen);
                    }
                });
            });
        });
    }

    function finishLoading() {
        state.loading = false;
        byId("payops-table-skeleton").classList.add("hidden");
        byId("payops-table-shell").classList.remove("hidden");
    }

    function initialize() {
        fetchPaymentsSummary({}).then(function () {
            renderKpis(state.raw.summary || {});
            renderSuccessRate(state.raw.statusOverview || {});
            renderTopCustomers(state.raw);
            renderTopProducts(state.raw);
            lazyInitCharts();
            wireControls();
            wirePopoverClose();
            initCollapsibleCards();

            setTimeout(function () {
                finishLoading();
                applyFilters();
            }, 240);

            if (window.lucide && typeof window.lucide.createIcons === "function") {
                window.lucide.createIcons();
            }
        });

        fetchPaymentsList({});
    }

    window.fetchPaymentsSummary = fetchPaymentsSummary;
    window.fetchPaymentsList = fetchPaymentsList;
    window.renderCharts = renderCharts;
    window.updateCharts = updateCharts;
    window.applyFilters = applyFilters;
    window.exportPayments = exportPayments;

    document.addEventListener("DOMContentLoaded", initialize);
})();

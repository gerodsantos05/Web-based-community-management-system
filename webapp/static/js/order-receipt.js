(function () {
    "use strict";

    const overlay = document.getElementById("orderReceiptModal");
    const closeButton = document.getElementById("closeOrderReceipt");
    const printButton = document.getElementById("printOrderReceipt");
    const items = document.getElementById("receiptItems");
    const receiptPaper = document.getElementById("orderReceiptPaper");

    if (!overlay || !closeButton || !printButton || !items || !receiptPaper) return;

    let activeOrder = null;

    function formatCurrency(amount) {
        return "₱" + Number(amount || 0).toLocaleString("en-PH", { maximumFractionDigits: 0 });
    }

    function formatDate(value) {
        if (!value) return "—";
        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? String(value)
            : date.toLocaleDateString("en-PH", { year: "numeric", month: "short", day: "numeric" });
    }

    function closeReceipt() {
        overlay.hidden = true;
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open", "receipt-printing");
    }

    function normalizeItems(order) {
        return (order.items || order.orderItems || []).map(function (item) {
            if (typeof item === "string") {
                return { name: item, quantity: 1, line_total: 0 };
            }
            const quantity = Number(item.quantity || item.qty || 1);
            return {
                name: item.name || item.product_name || item.productName || item.title || "Product",
                variation: item.variation || item.selectedVariation || item.selected_variation || "",
                quantity: quantity,
                line_total: Number(item.line_total ?? item.lineTotal ?? (Number(item.unit_price || item.unitPrice || 0) * quantity)),
            };
        });
    }

    function populateReceipt(order) {
        activeOrder = order;
        const receiptItems = normalizeItems(order);
        const total = Number(order.total ?? order.amount ?? 0);
        const calculatedSubtotal = receiptItems.reduce(function (sum, item) { return sum + item.line_total; }, 0);
        const subtotal = Math.min(Number(order.subtotal ?? calculatedSubtotal), total);
        const shipping = Math.min(Number(order.shipping_fee ?? 50), Math.max(total - subtotal, 0));
        const vat = Math.max(total - subtotal - shipping, 0);
        const paymentStatus = order.payment_status || order.paymentStatus || "Pending";
        const orderStatus = order.status_label || order.orderStatus || "Pending";
        const outcome = document.getElementById("receiptOutcome");

        document.getElementById("receiptOrderNumber").textContent = order.order_number || order.orderId || "—";
        document.getElementById("receiptOrderDate").textContent = formatDate(order.date || order.paymentDate);
        document.getElementById("receiptCustomerName").textContent = order.customer_name || order.customer || "Guest";
        document.getElementById("receiptPaymentMethod").textContent = order.payment_method || order.method || "—";
        document.getElementById("receiptOrderStatus").textContent = orderStatus;
        document.getElementById("receiptPaymentStatus").textContent = paymentStatus;
        document.getElementById("receiptSubtotal").textContent = formatCurrency(subtotal);
        document.getElementById("receiptDeliveryFee").textContent = formatCurrency(shipping);
        document.getElementById("receiptVat").textContent = formatCurrency(vat);
        document.getElementById("receiptTotal").textContent = formatCurrency(total);

        outcome.hidden = true;
        outcome.removeAttribute("data-kind");
        if (paymentStatus === "Refunded") {
            const refundDate = order.refund_processed_at || order.refundProcessedAt;
            outcome.textContent = "REFUNDED" + (refundDate ? " · Processed " + formatDate(refundDate) : "");
            outcome.dataset.kind = "refunded";
            outcome.hidden = false;
        } else if (orderStatus === "Cancelled" && paymentStatus === "Paid") {
            outcome.textContent = "ORDER CANCELLED · PAYMENT NOT REFUNDED";
            outcome.dataset.kind = "cancelled";
            outcome.hidden = false;
        }

        items.replaceChildren();
        receiptItems.forEach(function (item) {
            const row = document.createElement("div");
            row.className = "receipt-item";
            const detail = document.createElement("div");
            const name = document.createElement("strong");
            name.textContent = item.name;
            detail.appendChild(name);
            if (item.variation) {
                const variation = document.createElement("span");
                variation.textContent = item.variation;
                detail.appendChild(variation);
            }
            const quantity = document.createElement("span");
            quantity.textContent = "Qty " + item.quantity;
            const lineTotal = document.createElement("strong");
            lineTotal.textContent = formatCurrency(item.line_total);
            row.append(detail, quantity, lineTotal);
            items.appendChild(row);
        });
    }

    function openReceipt(order) {
        if (!order) return;
        populateReceipt(order);
        overlay.hidden = false;
        overlay.style.position = "";
        overlay.style.left = "";
        overlay.style.top = "";
        overlay.style.zIndex = "";
        overlay.style.visibility = "";
        overlay.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        closeButton.focus();
    }

    function downloadReceipt() {
        if (typeof window.html2pdf !== "function") {
            return Promise.reject(new Error("Receipt download is temporarily unavailable. Please try again."));
        }

        const paperWidth = Math.ceil(receiptPaper.getBoundingClientRect().width);
        const paperHeight = Math.ceil(receiptPaper.getBoundingClientRect().height);
        const orderNumber = activeOrder.order_number || activeOrder.orderId || "receipt";
        const safeOrderNumber = String(orderNumber).replace(/[^a-z0-9_-]/gi, "-");
        const options = {
            margin: 0,
            filename: "Receipt-" + safeOrderNumber + ".pdf",
            image: { type: "jpeg", quality: 0.98 },
            html2canvas: {
                scale: 2,
                useCORS: true,
                backgroundColor: "#ffffff",
                width: paperWidth,
                height: paperHeight,
                scrollX: 0,
                scrollY: 0,
            },
            jsPDF: {
                unit: "px",
                format: [paperWidth, paperHeight],
                orientation: "portrait",
                hotfixes: ["px_scaling"],
            },
            pagebreak: { mode: ["avoid-all"] },
        };
        const originalMarkup = printButton.innerHTML;
        printButton.disabled = true;
        printButton.textContent = "Downloading...";

        return window.html2pdf()
            .set(options)
            .from(receiptPaper)
            .save()
            .finally(function () {
                printButton.disabled = false;
                printButton.innerHTML = originalMarkup;
            });
    }

    window.openOrderReceipt = openReceipt;
    window.downloadOrderReceipt = function (order) {
        if (!order) return Promise.reject(new Error("Order details are unavailable."));
        populateReceipt(order);
        document.body.classList.remove("modal-open");
        overlay.hidden = false;
        overlay.setAttribute("aria-hidden", "true");
        overlay.style.position = "fixed";
        overlay.style.left = "-10000px";
        overlay.style.top = "0";
        overlay.style.zIndex = "1700";
        overlay.style.visibility = "visible";
        return downloadReceipt().finally(function () {
            overlay.hidden = true;
            overlay.style.position = "";
            overlay.style.left = "";
            overlay.style.top = "";
            overlay.style.zIndex = "";
            overlay.style.visibility = "";
            overlay.setAttribute("aria-hidden", "true");
        });
    };

    closeButton.addEventListener("click", closeReceipt);
    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) closeReceipt();
    });
    printButton.addEventListener("click", function () {
        downloadReceipt().catch(function (error) {
            window.alert(error.message);
        });
    });
})();

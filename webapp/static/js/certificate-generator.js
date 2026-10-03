(function () {
    "use strict";
    var DEFAULT_REASON = "In recognition of your exceptional dedication, heartfelt compassion, and outstanding service rendered as an On-the-Job Trainee volunteer of the HappYness Project. Your unwavering commitment to uplifting the community reflects the true spirit of excellence and selfless giving.";
    function byId(id) { return document.getElementById(id); }
    function update() {
        var name = byId("vol-cert-name"), reason = byId("vol-cert-reason"), volunteer = byId("vol-cert-volunteer");
        if (byId("vol-cert-preview-name")) {
            byId("vol-cert-preview-name").textContent = name ? name.value.trim() : "";
            fitNameToPreview();
        }
        if (byId("vol-cert-preview-reason")) byId("vol-cert-preview-reason").textContent = reason ? reason.value.trim() : "";
        var button = byId("vol-cert-download-btn");
        if (button) button.disabled = !(volunteer && volunteer.value && name && name.value.trim() && reason && reason.value.trim());
    }
    function fitNameToPreview() {
        var preview = byId("vol-cert-preview");
        var nameElement = byId("vol-cert-preview-name");
        if (!preview || !nameElement) return;
        var previewWidth = preview.querySelector(".vol-cert-preview-content");
        if (!previewWidth) return;
        var maxWidth = previewWidth.clientWidth * 0.78;
        nameElement.style.removeProperty("font-size");
        var computed = window.getComputedStyle(nameElement);
        var fontSize = parseFloat(computed.fontSize) || 36;
        var minFontSize = 10;
        var canvas = document.createElement("canvas");
        var context = canvas.getContext("2d");
        if (!context) return;
        context.font = computed.fontStyle + " " + computed.fontWeight + " " + fontSize + "px " + computed.fontFamily;
        var measuredWidth = context.measureText(nameElement.textContent || "").width;
        if (measuredWidth > maxWidth) {
            fontSize = Math.max(minFontSize, fontSize * maxWidth / measuredWidth);
        }
        nameElement.style.setProperty("font-size", fontSize + "px", "important");
    }
    function open() {
        var modal = byId("vol-cert-modal"), backdrop = byId("vol-modal-backdrop");
        if (!modal) return;
        var image = byId("vol-cert-bg-img");
        if (image) image.src = "/static/media/certificate%20of%20appreciation.jpg";
        if (byId("vol-cert-name")) byId("vol-cert-name").value = "";
        if (byId("vol-cert-volunteer")) byId("vol-cert-volunteer").value = "";
        if (byId("vol-cert-reason")) byId("vol-cert-reason").value = DEFAULT_REASON;
        update(); modal.setAttribute("data-open", "true"); if (backdrop) backdrop.setAttribute("data-open", "true");
    }
    function close() { if (byId("vol-cert-modal")) byId("vol-cert-modal").setAttribute("data-open", "false"); if (byId("vol-modal-backdrop")) byId("vol-modal-backdrop").setAttribute("data-open", "false"); }
    function generate() {
        var name = byId("vol-cert-name"), reason = byId("vol-cert-reason"), volunteer = byId("vol-cert-volunteer"), preview = byId("vol-cert-preview") && byId("vol-cert-preview").querySelector(".vol-cert-preview-content"), button = byId("vol-cert-download-btn");
        if (!name || !reason || !volunteer || !preview || !volunteer.value || !name.value.trim() || !reason.value.trim()) { update(); return; }
        var PDFLib = window.jspdf && window.jspdf.jsPDF ? window.jspdf.jsPDF : window.jsPDF;
        if (typeof html2canvas === "undefined" || !PDFLib) { alert("PDF library is loading. Please try again."); return; }
        update();
        button.disabled = true; button.textContent = "Generating PDF...";
        var nameElement = byId("vol-cert-preview-name");
        var reasonElement = byId("vol-cert-preview-reason");
        var nameStyle = namePreviewStyle(preview, nameElement, 0.43, 0.78);
        var reasonStyle = namePreviewStyle(preview, reasonElement, 0.68, 0.86);
        var originalNameStyle = nameElement.getAttribute("style");
        var originalReasonStyle = reasonElement.getAttribute("style");
        applyExportStyle(nameElement, nameStyle);
        applyExportStyle(reasonElement, reasonStyle);
        var backgroundImage = byId("vol-cert-bg-img");
        var imageReady = backgroundImage && (!backgroundImage.complete || !backgroundImage.naturalWidth)
            ? new Promise(function (resolve) {
                backgroundImage.addEventListener("load", resolve, { once: true });
                backgroundImage.addEventListener("error", resolve, { once: true });
                if (backgroundImage.complete && !backgroundImage.naturalWidth) backgroundImage.src = backgroundImage.src;
            })
            : Promise.resolve();
        if (backgroundImage && backgroundImage.decode) {
            imageReady = imageReady.then(function () { return backgroundImage.decode().catch(function () {}); });
        }
        imageReady.then(function () { return document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve(); }).then(function () {
            return html2canvas(preview, { backgroundColor: "#fffdf7", useCORS: true, allowTaint: false, scale: 3, logging: false, imageTimeout: 30000 });
        }).then(function (canvas) {
            restoreExportElements(nameElement, reasonElement, originalNameStyle, originalReasonStyle);
            var doc = new PDFLib({ orientation: "landscape", unit: "mm", format: "a4" });
            var pageWidth = doc.internal.pageSize.getWidth(), pageHeight = doc.internal.pageSize.getHeight(), margin = 4, width = pageWidth - margin * 2, height = width / (canvas.width / canvas.height);
            if (height > pageHeight - margin * 2) { height = pageHeight - margin * 2; width = height * (canvas.width / canvas.height); }
            doc.addImage(canvas.toDataURL("image/png"), "PNG", (pageWidth - width) / 2, (pageHeight - height) / 2, width, height);
            var pdfBlob = doc.output("blob");
            return saveIssuedCertificate(volunteer.value, name.value.trim(), reason.value.trim(), pdfBlob).then(function () {
                doc.save("Certificate_of_Appreciation_" + name.value.trim().replace(/\s+/g, "_") + ".pdf");
                close();
            });
        }).catch(function () {
            restoreExportElements(nameElement, reasonElement, originalNameStyle, originalReasonStyle);
            alert("Error generating certificate. Please try again.");
        }).finally(function () { button.disabled = false; button.textContent = "Download PDF"; });
    }
    function csrfToken() {
        var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }
    function saveIssuedCertificate(volunteerId, recipientName, reason, pdfBlob) {
        var modal = byId("vol-cert-modal");
        var endpoint = modal && modal.getAttribute("data-create-url");
        var formData = new FormData();
        formData.append("volunteer_id", volunteerId);
        formData.append("recipient_name", recipientName);
        formData.append("reason", reason);
        if (pdfBlob) formData.append("pdf_file", pdfBlob, "Certificate_of_Appreciation.pdf");
        return fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken() },
            body: formData
        }).then(function (response) {
            if (!response.ok) return response.json().catch(function () { return {}; }).then(function (data) { throw new Error(data.error || "Unable to issue certificate."); });
            return response.json();
        });
    }
    function namePreviewStyle(preview, element, verticalPosition, widthRatio) {
        var height = preview.getBoundingClientRect().height;
        var elementHeight = element.getBoundingClientRect().height;
        var width = preview.getBoundingClientRect().width * widthRatio;
        return {
            top: (height * verticalPosition - elementHeight / 2) + "px",
            left: ((preview.getBoundingClientRect().width - width) / 2) + "px",
            width: width + "px"
        };
    }
    function applyExportStyle(element, position) {
        element.style.setProperty("position", "absolute", "important");
        element.style.setProperty("left", position.left, "important");
        element.style.setProperty("top", position.top, "important");
        element.style.setProperty("width", position.width, "important");
        element.style.setProperty("max-width", position.width, "important");
        element.style.setProperty("min-width", "0", "important");
        element.style.setProperty("box-sizing", "border-box", "important");
        element.style.setProperty("transform", "none", "important");
        element.style.setProperty("text-align", "center", "important");
    }
    function restoreExportElements(nameElement, reasonElement, nameStyle, reasonStyle) {
        restoreStyle(nameElement, nameStyle);
        restoreStyle(reasonElement, reasonStyle);
    }
    function restoreStyle(element, style) {
        if (style === null) element.removeAttribute("style");
        else element.setAttribute("style", style);
    }
    window.openCertificateModal = open; window.closeCertificateModal = close; window.updateCertificatePreview = update; window.generateCertificatePDF = generate; window.generateCertificatePDFShared = generate; window.fitCertificateName = fitNameToPreview;
    function bindCertificateControls() {
        var dashboardTrigger = document.querySelector('[data-open-certificate="true"]');
        if (dashboardTrigger) dashboardTrigger.addEventListener("click", open);
        document.querySelectorAll("[data-close-cert]").forEach(function (button) {
            if (button.dataset.certificateBound === "true") return;
            button.dataset.certificateBound = "true";
            button.addEventListener("click", close);
        });
        if (byId("vol-cert-name")) byId("vol-cert-name").addEventListener("input", update);
        if (byId("vol-cert-reason")) byId("vol-cert-reason").addEventListener("input", update);
        if (byId("vol-cert-volunteer")) byId("vol-cert-volunteer").addEventListener("change", function () {
            var option = this.options[this.selectedIndex];
            var name = byId("vol-cert-name");
            if (name && option && option.dataset.volunteerName) name.value = option.dataset.volunteerName;
            update();
        });
        var downloadButton = byId("vol-cert-download-btn");
        if (downloadButton && downloadButton.dataset.certificateBound !== "true") {
            downloadButton.dataset.certificateBound = "true";
            downloadButton.addEventListener("click", generate);
        }
        if (byId("vol-modal-backdrop") && byId("vol-modal-backdrop").dataset.certificateBound !== "true") {
            byId("vol-modal-backdrop").dataset.certificateBound = "true";
            byId("vol-modal-backdrop").addEventListener("click", close);
        }
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindCertificateControls, { once: true });
    else bindCertificateControls();
})();

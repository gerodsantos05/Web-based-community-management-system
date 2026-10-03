(function () {
    "use strict";

    function isImageFile(file) {
        return !!file && String(file.type || "").toLowerCase().indexOf("image/") === 0;
    }

    function signature(file) {
        return [file.name || "", Number(file.size) || 0, Number(file.lastModified) || 0, file.type || ""].join("|");
    }

    function previewUrl(file) {
        if (!isImageFile(file) || !window.URL || typeof window.URL.createObjectURL !== "function") return "";
        try { return window.URL.createObjectURL(file); } catch (error) { return ""; }
    }

    function release(url) {
        if (!url || !window.URL || typeof window.URL.revokeObjectURL !== "function") return;
        try { window.URL.revokeObjectURL(url); } catch (error) {}
    }

    window.createCommunityAttachmentManager = function (options) {
        var host = options.host;
        var pickers = options.pickers || (options.picker ? [options.picker] : []);
        var files = [];
        var nextId = 1;

        function render() {
            host.innerHTML = files.map(function (item) {
                var media = item.isImage && item.previewUrl
                    ? '<img class="ch-chat-selected-thumb" src="' + item.previewUrl.replace(/"/g, '&quot;') + '" alt="">'
                    : '<span class="ch-chat-selected-file" aria-hidden="true"><i data-lucide="paperclip" class="ch-icon"></i></span>';
                var name = item.isImage ? "" : '<span class="community-attachment-name">' + item.name.replace(/[&<>"']/g, function (character) { return ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[character]; }) + '</span>';
                return '<article class="ch-chat-selected-label" data-community-attachment-id="' + item.id + '">' + media + name + '<button type="button" class="ch-chat-selected-remove focus-ring" data-remove-community-attachment="' + item.id + '" aria-label="Remove attachment">&#10005;</button></article>';
            }).join("");
            host.hidden = !files.length;
            if (window.lucide && typeof window.lucide.createIcons === "function") window.lucide.createIcons();
        }

        function add(fileList) {
            var existing = new Set(files.map(function (item) { return item.signature; }));
            Array.prototype.forEach.call(fileList || [], function (file) {
                if (!file || existing.has(signature(file))) return;
                existing.add(signature(file));
                files.push({ id: "community-attachment-" + nextId++, name: file.name || "Attachment", file: file, isImage: isImageFile(file), previewUrl: previewUrl(file), signature: signature(file) });
            });
            render();
        }

        function remove(id) {
            files = files.filter(function (item) { if (item.id === id) { release(item.previewUrl); return false; } return true; });
            render();
        }

        host.addEventListener("click", function (event) {
            var button = event.target.closest("[data-remove-community-attachment]");
            if (button) remove(button.getAttribute("data-remove-community-attachment"));
        });
        pickers.forEach(function (picker) { picker.addEventListener("change", function () { add(picker.files); picker.value = ""; }); });

        return {
            add: add,
            clear: function () { files.forEach(function (item) { release(item.previewUrl); }); files = []; render(); },
            items: function () { return files.slice(); },
            render: render
        };
    };
})();

(function () {
    document.addEventListener("error", function (event) {
        var image = event.target;
        if (!(image instanceof HTMLImageElement) || image.getAttribute("data-avatar-image") !== "true") {
            return;
        }

        var fallbackUrl = document.body && document.body.getAttribute("data-default-avatar-url");
        if (!fallbackUrl || image.src === new URL(fallbackUrl, document.baseURI).href) {
            return;
        }

        image.src = fallbackUrl;
    }, true);
})();

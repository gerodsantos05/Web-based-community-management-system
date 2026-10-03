(function () {
    "use strict";

    function initProfilePhotoCropper(options) {
        var input = options.input;
        if (!input || typeof window.Cropper !== "function") {
            if (options.onError) options.onError("Photo cropping is unavailable. Please refresh and try again.");
            return null;
        }

        var modal = document.createElement("div");
        modal.className = "profile-photo-crop-modal";
        modal.hidden = true;
        modal.innerHTML = '<section class="profile-photo-crop-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-photo-crop-title">' +
            '<header class="profile-photo-crop-head"><div><h2 id="profile-photo-crop-title" class="profile-photo-crop-title">Adjust profile photo</h2><p class="profile-photo-crop-copy">Drag to reposition, then zoom to frame the circle.</p></div></header>' +
            '<div class="profile-photo-crop-stage"><img class="profile-photo-crop-image" alt="Selected profile photo"></div>' +
            '<div class="profile-photo-crop-controls"><label class="profile-photo-crop-zoom-label" for="profile-photo-crop-zoom"><span>Zoom</span><span aria-hidden="true">+</span></label><input class="profile-photo-crop-zoom" id="profile-photo-crop-zoom" type="range" min="0.1" max="3" step="0.01" value="1"></div>' +
            '<footer class="profile-photo-crop-actions"><button type="button" class="profile-photo-crop-button profile-photo-crop-button-ghost" data-profile-photo-crop-cancel>Cancel</button><button type="button" class="profile-photo-crop-button profile-photo-crop-button-primary" data-profile-photo-crop-save>Save photo</button></footer>' +
            '</section>';
        document.body.appendChild(modal);

        var image = modal.querySelector(".profile-photo-crop-image");
        var zoom = modal.querySelector(".profile-photo-crop-zoom");
        var cancel = modal.querySelector("[data-profile-photo-crop-cancel]");
        var save = modal.querySelector("[data-profile-photo-crop-save]");
        var cropper = null;
        var objectUrl = "";
        var selectedFile = null;

        function close(discardFile) {
            if (cropper) {
                cropper.destroy();
                cropper = null;
            }
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = "";
            }
            modal.hidden = true;
            if (discardFile && options.onCancelled) options.onCancelled();
        }

        function open(file) {
            selectedFile = file;
            objectUrl = URL.createObjectURL(file);
            image.src = objectUrl;
            modal.hidden = false;
            zoom.value = "1";
            cropper = new window.Cropper(image, {
                aspectRatio: 1,
                viewMode: 1,
                dragMode: "move",
                autoCropArea: 0.82,
                cropBoxMovable: false,
                cropBoxResizable: false,
                guides: false,
                center: true,
                background: false,
                toggleDragModeOnDblclick: false
            });
        }

        input.addEventListener("change", function () {
            var file = input.files && input.files[0];
            if (!file) return;
            if (!file.type || file.type.indexOf("image/") !== 0) {
                input.value = "";
                if (options.onError) options.onError("Please choose a valid image file.");
                return;
            }
            if (file.size > 2 * 1024 * 1024) {
                input.value = "";
                if (options.onError) options.onError("Profile photo must be 2MB or smaller.");
                return;
            }
            open(file);
        });

        zoom.addEventListener("input", function () {
            if (cropper) cropper.zoomTo(Number(zoom.value));
        });

        cancel.addEventListener("click", function () {
            input.value = "";
            selectedFile = null;
            close(true);
        });

        save.addEventListener("click", function () {
            if (!cropper || !selectedFile) return;
            save.disabled = true;
            cropper.getCroppedCanvas({ width: 512, height: 512, imageSmoothingEnabled: true, imageSmoothingQuality: "high" }).toBlob(function (blob) {
                if (!blob) {
                    save.disabled = false;
                    if (options.onError) options.onError("Unable to prepare the cropped photo.");
                    return;
                }
                var croppedFile = new File([blob], "profile-photo.jpg", { type: "image/jpeg", lastModified: Date.now() });
                var previewUrl = URL.createObjectURL(blob);
                var dataTransfer = typeof DataTransfer === "function" ? new DataTransfer() : null;
                if (dataTransfer) {
                    dataTransfer.items.add(croppedFile);
                    input.files = dataTransfer.files;
                }
                close(false);
                if (options.onCropped) options.onCropped(croppedFile, previewUrl);
            }, "image/jpeg", 0.9);
        });

        modal.addEventListener("click", function (event) {
            if (event.target === modal) cancel.click();
        });

        return {
            clear: function () {
                input.value = "";
                selectedFile = null;
                if (!modal.hidden) close(false);
            }
        };
    }

    window.initProfilePhotoCropper = initProfilePhotoCropper;
}());

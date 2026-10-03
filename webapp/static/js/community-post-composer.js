(function () {
    "use strict";

    window.communityCreatePost = function (endpoint, content, type, attachments) {
        var body = new FormData();
        body.append("content", String(content || ""));
        body.append("type", String(type || "discussions"));
        (Array.isArray(attachments) ? attachments : []).forEach(function (attachment) {
            if (attachment && attachment.file) {
                body.append("attachments", attachment.file, attachment.file.name || attachment.name || "attachment");
            }
        });

        return fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": document.cookie.split(";").reduce(function (token, cookie) {
                var part = cookie.trim();
                return part.indexOf("csrftoken=") === 0 ? decodeURIComponent(part.substring(10)) : token;
            }, "") },
            body: body
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error(data && data.error ? data.error : "Unable to publish post.");
                }
                return data;
            });
        });
    };
})();

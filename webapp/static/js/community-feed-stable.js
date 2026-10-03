(function initCommunityFeedStable() {
    "use strict";

    var root = document.getElementById("community-hub");
    if (!root || root.dataset.communityStableBound === "true") {
        return;
    }
    root.dataset.communityStableBound = "true";

    var feedHost = document.getElementById("community-feed");
    var widgetSide = root.querySelector(".ch-side");
    var widgetIndicators = document.getElementById("community-widget-indicators");
    var dashboardScrollHost = document.getElementById("dashboard-content-scroll");
    var feedCount = document.getElementById("community-feed-count");
    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));
    var chatForm = document.getElementById("community-chatbox");
    var chatInput = document.getElementById("community-chat-input");
    var chatAuthorName = document.getElementById("community-chat-author-name");
    var chatAvatarImage = document.getElementById("community-chat-avatar-image");
    var chatAvatarFallback = document.getElementById("community-chat-avatar-fallback");
    var chatPlusButton = document.getElementById("community-chat-plus");
    var attachmentCard = document.getElementById("community-chat-attachment-card");
    var attachImagesButton = document.getElementById("community-chat-attach-images");
    var attachFilesButton = document.getElementById("community-chat-attach-files");
    var attachmentImagesInput = document.getElementById("community-chat-attachment-images-input");
    var attachmentFilesInput = document.getElementById("community-chat-attachment-files-input");
    var selectedLabelsHost = document.getElementById("community-chat-selected-labels");
    var chatSendButton = document.querySelector("#community-chatbox .ch-chatbox-send");
    var chatSendIcon = chatSendButton ? chatSendButton.querySelector("[data-lucide]") : null;
    var chatSendLabel = chatSendButton ? chatSendButton.querySelector("span") : null;
    var announcementToggleButton = document.getElementById("community-chat-announcement");
    var announcementToggleIcon = announcementToggleButton ? announcementToggleButton.querySelector("[data-lucide]") : null;
    var announcementToggleLabel = announcementToggleButton ? announcementToggleButton.querySelector(".ch-chatbox-announcement-label") : null;
    var announcementToggleLabelMobile = announcementToggleButton ? announcementToggleButton.querySelector(".ch-chatbox-announcement-label-mobile") : null;
    var mediaViewer = document.getElementById("community-media-viewer");
    var mediaViewerImage = document.getElementById("community-media-viewer-image");
    var mediaViewerCount = document.getElementById("community-media-viewer-count");
    var mediaViewerPrev = document.getElementById("community-media-viewer-prev");
    var mediaViewerNext = document.getElementById("community-media-viewer-next");

    var announcementsHost = document.getElementById("community-announcements");
    var eventsHost = document.getElementById("community-events");
    var highlightsHost = document.getElementById("community-highlights");
    var announcementsBadge = document.getElementById("community-announcements-badge");
    var eventsBadge = document.getElementById("community-events-badge");
    var highlightsBadge = document.getElementById("community-highlights-badge");
    var widgetToggles = Array.prototype.slice.call(root.querySelectorAll("[data-widget-toggle]"));
    var statusNode = document.getElementById("community-create-status");
    var commentRefreshTimer = null;
    var relativeTimeRefreshTimer = null;
    var widgetsExpanded = false;
    var composerAnnouncementMode = false;
    var composerDefaultPlaceholder = "Share something with the community...";
    var composerAnnouncementPlaceholder = "Write an announcement for the community...";
    var currentUser = {
        id: String(root.getAttribute("data-current-user-id") || ""),
        isAdmin: String(root.getAttribute("data-current-user-is-admin") || "false") === "true",
        name: String(root.getAttribute("data-current-user-name") || "You"),
        initials: String(root.getAttribute("data-current-user-initials") || "YO"),
        avatarUrl: String(root.getAttribute("data-current-user-avatar-url") || "")
    };
    var postsEndpoint = String(root.getAttribute("data-posts-endpoint") || "");
    var createPostEndpoint = String(root.getAttribute("data-create-post-endpoint") || "");
    var communityEndpointBase = postsEndpoint ? postsEndpoint.replace(/\/+$/, "") + "/" : "";
    var POST_BATCH_SIZE = 8;
    var COMMENT_BATCH_SIZE = 8;

    try {
        currentUser.name = String(localStorage.getItem("dashboard_profile_name") || currentUser.name || "You");
        currentUser.initials = String(localStorage.getItem("dashboard_profile_initials") || currentUser.initials || "YO");
        currentUser.avatarUrl = String(localStorage.getItem("dashboard_profile_avatar_url") || currentUser.avatarUrl || "");
    } catch (error) {}

    if (!feedHost || !feedCount) {
        return;
    }

    function syncMobileWidgetPosition() {
        if (!widgetSide) {
            return;
        }

        var isMobile = window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
        if (isMobile) {
            feedHost.parentNode.insertBefore(widgetSide, feedHost);
            if (widgetIndicators) {
                feedHost.parentNode.insertBefore(widgetIndicators, feedHost);
            }
            return;
        }

        root.appendChild(widgetSide);
        if (widgetIndicators) {
            root.appendChild(widgetIndicators);
        }
    }

    function updateWidgetCarouselIndicator() {
        if (!widgetSide || !widgetIndicators) {
            return;
        }

        var cards = Array.prototype.slice.call(widgetSide.querySelectorAll(".ch-widget-card"));
        if (!cards.length) {
            return;
        }

        var rowCenter = widgetSide.scrollLeft + (widgetSide.clientWidth / 2);
        var activeIndex = 0;
        var closestDistance = Infinity;
        cards.forEach(function (card, index) {
            var cardCenter = card.offsetLeft + (card.offsetWidth / 2);
            var distance = Math.abs(cardCenter - rowCenter);
            if (distance < closestDistance) {
                closestDistance = distance;
                activeIndex = index;
            }
        });

        Array.prototype.forEach.call(widgetIndicators.querySelectorAll("[data-widget-indicator]"), function (indicator, index) {
            var isActive = index === activeIndex;
            indicator.classList.toggle("is-active", isActive);
            indicator.setAttribute("aria-current", isActive ? "true" : "false");
        });
    }

    var nextPostId = 4;
    var nextAttachmentId = 1;
    var nextCommentId = 0;
    var pendingAttachments = [];
    var sharedAttachmentManager = window.createCommunityAttachmentManager ? window.createCommunityAttachmentManager({
        host: selectedLabelsHost,
        pickers: [attachmentImagesInput, attachmentFilesInput]
    }) : null;
    var openPostMenuId = null;
    var mediaViewerState = {
        images: [],
        index: 0
    };
    var commentLoadObserver = null;
    var state = {
        activeTab: "all",
        posts: [],
        postsHasMore: false,
        postsOffset: 0,
        postsLoading: false,
        announcements: [
            "Workshop schedule updated",
            "Bring IDs reminder",
            "Market booth deadline: Friday"
        ],
        events: [
            "Apr 18 - Advanced Crafts Workshop",
            "Apr 25 - Monthly Community Meeting",
            "May 1 - Skills Fair and Marketplace"
        ],
        highlights: [
            "Community garden milestone reached",
            "10 members completed learning module",
            "New volunteer mentors joined"
        ]
    };

    function escapeHtml(value) {
        var safe = String(value || "");
        var map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return safe.replace(/[&<>"']/g, function (character) {
            return map[character] || character;
        });
    }

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            var cookies = document.cookie.split(";");
            for (var i = 0; i < cookies.length; i += 1) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function buildPostActionEndpoint(postId, actionPath) {
        if (!communityEndpointBase) {
            return "";
        }

        return communityEndpointBase + encodeURIComponent(String(postId || "")) + "/" + String(actionPath || "").replace(/^\/+/, "");
    }

    function buildCommentActionEndpoint(postId, commentId, actionPath) {
        if (!communityEndpointBase) {
            return "";
        }

        return communityEndpointBase + encodeURIComponent(String(postId || "")) + "/comments/" + encodeURIComponent(String(commentId || "")) + "/" + String(actionPath || "").replace(/^\/+/, "");
    }

    function requestJson(endpoint, options, fallbackMessage) {
        if (!endpoint) {
            return Promise.reject(new Error(fallbackMessage || "Endpoint is not configured."));
        }

        var config = options && typeof options === "object" ? Object.assign({}, options) : {};
        config.credentials = "same-origin";

        return fetch(endpoint, config).then(function (response) {
            return response.json().catch(function () {
                return {};
            }).then(function (data) {
                if (!response.ok) {
                    var message = data && data.error ? data.error : (fallbackMessage || "Request failed.");
                    throw new Error(message);
                }
                return data;
            });
        });
    }

    var reportModal = document.getElementById("community-report-modal");
    var currentReportPostId = "";
    var currentReportReason = "";

    function openReportModal(postId) {
        if (!reportModal) {
            return;
        }

        currentReportPostId = String(postId || "");
        currentReportReason = "";

        var detailsInput = reportModal.querySelector("#community-report-details");
        if (detailsInput) {
            detailsInput.value = "";
        }

        Array.prototype.forEach.call(reportModal.querySelectorAll("[data-report-reason]"), function (item) {
            var input = item.querySelector("input[name='report_reason']");
            if (input) {
                input.checked = false;
            }
        });

        var submitButton = reportModal.querySelector("[data-report-submit]");
        if (submitButton) {
            submitButton.disabled = true;
        }

        reportModal.removeAttribute("hidden");
        document.body.classList.add("ch-modal-open");
    }

    function closeReportModal() {
        if (!reportModal) {
            return;
        }

        reportModal.setAttribute("hidden", "");
        currentReportPostId = "";
        currentReportReason = "";
        document.body.classList.remove("ch-modal-open");
    }

    function setReportModalState() {
        if (!reportModal) {
            return;
        }

        Array.prototype.forEach.call(reportModal.querySelectorAll("[data-report-reason]"), function (item) {
            var reason = String(item.getAttribute("data-report-reason") || "");
            var input = item.querySelector("input[name='report_reason']");
            if (input) {
                input.checked = reason === currentReportReason;
            }
        });

        var submitButton = reportModal.querySelector("[data-report-submit]");
        if (submitButton) {
            submitButton.disabled = !currentReportReason;
        }
    }

    function reportPostOnServer(postId, reason, details) {
        var endpoint = buildPostActionEndpoint(postId, "report/");
        var body = new FormData();
        body.append("reason", String(reason || ""));
        body.append("details", String(details || ""));

        return fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            },
            body: body
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    var message = data && data.error ? data.error : "Unable to submit report.";
                    throw new Error(message);
                }
                return data;
            });
        });
    }

    function setStatus(message) {
        if (!statusNode) {
            return;
        }

        statusNode.textContent = String(message || "").trim();
    }

    function syncComposerIdentity() {
        if (chatAuthorName) {
            chatAuthorName.textContent = String(currentUser.name || "You");
        }

        if (chatAvatarFallback) {
            chatAvatarFallback.textContent = String(currentUser.initials || "YO");
        }

        if (!chatAvatarImage || !chatAvatarFallback) {
            return;
        }

        var avatarUrl = String(currentUser.avatarUrl || "").trim();
        if (avatarUrl) {
            chatAvatarImage.src = avatarUrl;
            chatAvatarImage.removeAttribute("hidden");
            chatAvatarFallback.setAttribute("hidden", "");
            return;
        }

        chatAvatarImage.setAttribute("hidden", "");
        chatAvatarImage.removeAttribute("src");
        chatAvatarFallback.removeAttribute("hidden");
    }

    function isAnnouncementPost(post) {
        return String(post && post.type ? post.type : "").toLowerCase() === "announcements";
    }

    function relativeTimeLabel(timestamp) {
        var createdAt = new Date(timestamp);
        if (isNaN(createdAt.getTime())) {
            return "0s ago";
        }

        var elapsedSeconds = Math.max(0, Math.floor((Date.now() - createdAt.getTime()) / 1000));
        if (elapsedSeconds < 60) {
            return elapsedSeconds + "s ago";
        }

        var minutes = Math.floor(elapsedSeconds / 60);
        if (minutes < 60) {
            return minutes + "m ago";
        }

        var hours = Math.floor(minutes / 60);
        if (hours < 24) {
            return hours + "hr ago";
        }

        var days = Math.floor(hours / 24);
        if (days < 7) {
            return days + "d ago";
        }

        var weeks = Math.floor(days / 7);
        if (weeks < 4) {
            return weeks + "w ago";
        }

        var months = Math.max(1, Math.floor(days / 30));
        if (months < 12) {
            return months + "mo ago";
        }

        var years = Math.max(1, Math.floor(days / 365));
        return years + "yr ago";
    }

    function refreshRelativeTimestamps() {
        Array.prototype.forEach.call(feedHost.querySelectorAll("[data-post-timestamp]"), function (timestampNode) {
            timestampNode.textContent = relativeTimeLabel(timestampNode.getAttribute("data-post-timestamp"));
        });
    }

    function startRelativeTimePolling() {
        if (relativeTimeRefreshTimer) {
            return;
        }

        relativeTimeRefreshTimer = window.setInterval(refreshRelativeTimestamps, 30000);
        document.addEventListener("visibilitychange", function () {
            if (!document.hidden) {
                refreshRelativeTimestamps();
            }
        });
    }

    function setComposerMode(isAnnouncement) {
        composerAnnouncementMode = !!(isAnnouncement && announcementToggleButton);

        if (announcementToggleButton) {
            announcementToggleButton.classList.toggle("is-active", composerAnnouncementMode);
            announcementToggleButton.setAttribute("aria-pressed", composerAnnouncementMode ? "true" : "false");
        }

        if (chatInput) {
            chatInput.placeholder = composerAnnouncementMode ? composerAnnouncementPlaceholder : composerDefaultPlaceholder;
        }

        if (announcementToggleIcon) {
            announcementToggleIcon.setAttribute("data-lucide", "megaphone");
        }

        if (announcementToggleLabel) {
            announcementToggleLabel.textContent = "Announcement";
        }

        if (announcementToggleLabelMobile) {
            announcementToggleLabelMobile.textContent = "Announce";
        }

        refreshIcons();
    }

    function toggleComposerAnnouncementMode() {
        setComposerMode(!composerAnnouncementMode);
    }

    function composerPostType() {
        return composerAnnouncementMode ? "announcements" : "discussions";
    }

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function attachmentSignature(file) {
        if (!file) {
            return "";
        }
        return [file.name || "", Number(file.size) || 0, Number(file.lastModified) || 0, file.type || ""].join("|");
    }

    function isImageFile(file) {
        if (!file) {
            return false;
        }
        return String(file.type || "").toLowerCase().indexOf("image/") === 0;
    }

    function attachmentTypeLabel(file) {
        if (isImageFile(file)) {
            return "Image";
        }

        var fileName = String(file && file.name ? file.name : "");
        var match = fileName.match(/\.([a-zA-Z0-9]+)$/);
        if (match && match[1]) {
            return match[1].toUpperCase();
        }

        return "File";
    }

    function createPreviewUrl(file) {
        if (!file || !window.URL || typeof window.URL.createObjectURL !== "function") {
            return "";
        }

        try {
            return window.URL.createObjectURL(file);
        } catch (e) {
            return "";
        }
    }

    function revokePreviewUrl(previewUrl) {
        if (!previewUrl || !window.URL || typeof window.URL.revokeObjectURL !== "function") {
            return;
        }

        try {
            window.URL.revokeObjectURL(previewUrl);
        } catch (e) {
            // Ignore revoke failures for URLs already released by the browser.
        }
    }

    function setAttachmentCardOpen(open) {
        if (!attachmentCard) {
            return;
        }

        if (open) {
            attachmentCard.removeAttribute("hidden");
        } else {
            attachmentCard.setAttribute("hidden", "");
        }

        if (chatPlusButton) {
            chatPlusButton.setAttribute("aria-expanded", open ? "true" : "false");
        }
    }

    function clearNativeFileInput(input) {
        if (!input) {
            return;
        }

        try {
            input.value = "";
        } catch (e) {
            // Ignore input reset restrictions.
        }
    }

    function renderSelectedAttachmentLabels() {
        if (sharedAttachmentManager) {
            pendingAttachments = sharedAttachmentManager.items();
            return;
        }
        if (!selectedLabelsHost) {
            return;
        }

        if (!pendingAttachments.length) {
            selectedLabelsHost.innerHTML = "";
            selectedLabelsHost.setAttribute("hidden", "");
            return;
        }

        selectedLabelsHost.removeAttribute("hidden");
        selectedLabelsHost.innerHTML = pendingAttachments.map(function (attachment) {
            var previewMedia = attachment.isImage && attachment.previewUrl
                ? '<img class="ch-chat-selected-thumb" src="' + escapeHtml(attachment.previewUrl) + '" alt="">'
                : '<span class="ch-chat-selected-file" aria-hidden="true"><i data-lucide="paperclip" class="ch-icon"></i></span>';

            return [
                '<article class="ch-chat-selected-label" data-chat-attachment-id="' + escapeHtml(attachment.id) + '">',
                previewMedia,
                '<button type="button" class="ch-chat-selected-remove focus-ring" data-remove-chat-attachment="' + escapeHtml(attachment.id) + '" aria-label="Remove attachment">&#10005;</button>',
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function clearPendingAttachments() {
        if (sharedAttachmentManager) {
            sharedAttachmentManager.clear();
            pendingAttachments = [];
            return;
        }
        pendingAttachments.forEach(function (attachment) {
            revokePreviewUrl(attachment.previewUrl);
        });
        pendingAttachments = [];
        renderSelectedAttachmentLabels();
    }

    function addPendingAttachments(fileList) {
        if (sharedAttachmentManager) {
            sharedAttachmentManager.add(fileList);
            pendingAttachments = sharedAttachmentManager.items();
            if (pendingAttachments.length) {
                setStatus(pendingAttachments.length + (pendingAttachments.length === 1 ? " attachment selected." : " attachments selected."));
            }
            setAttachmentCardOpen(false);
            if (chatInput) chatInput.focus();
            return;
        }
        if (!fileList || !fileList.length) {
            return;
        }

        var existing = new Set(pendingAttachments.map(function (attachment) {
            return attachment.signature;
        }));

        Array.prototype.forEach.call(fileList, function (file) {
            if (!file) {
                return;
            }

            var signature = attachmentSignature(file);
            if (existing.has(signature)) {
                return;
            }

            existing.add(signature);
            var imageAttachment = isImageFile(file);
            pendingAttachments.push({
                id: "chat-attachment-" + nextAttachmentId++,
                name: file.name || "Attachment",
                file: file,
                isImage: imageAttachment,
                typeLabel: attachmentTypeLabel(file),
                previewUrl: imageAttachment ? createPreviewUrl(file) : "",
                signature: signature
            });
        });

        renderSelectedAttachmentLabels();
        if (pendingAttachments.length) {
            setStatus(pendingAttachments.length + (pendingAttachments.length === 1 ? " attachment selected." : " attachments selected."));
        }

        setAttachmentCardOpen(false);
        if (chatInput) {
            chatInput.focus();
        }
    }

    function setWidgetBadge(node, count) {
        if (!node) {
            return;
        }

        var value = Number(count) || 0;
        node.textContent = value > 99 ? "99+" : String(value);
    }

    function updateWidgetBadges() {
        setWidgetBadge(announcementsBadge, state.announcements.length);
        setWidgetBadge(eventsBadge, state.events.length);
        setWidgetBadge(highlightsBadge, state.highlights.length);
    }

    function widgetCardByName(name) {
        return root.querySelector('[data-widget-card="' + String(name || "").trim() + '"]');
    }

    function setWidgetExpanded(name, expanded) {
        if (!widgetSide) {
            return;
        }

        var isMobile = window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
        widgetsExpanded = !!expanded;
        var cards = isMobile
            ? Array.prototype.slice.call(widgetSide.querySelectorAll(".ch-widget-card"))
            : [widgetCardByName(name)];
        cards.forEach(function (card) {
            if (!card) {
                return;
            }

            card.classList.toggle("is-expanded", !!expanded);
            card.classList.toggle("is-collapsed", !expanded);
            var toggle = card.querySelector("[data-widget-toggle]");
            if (toggle) {
                toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
            }
        });
    }

    function commentsFor(post) {
        if (!Array.isArray(post.commentsList)) {
            post.commentsList = [];
        }

        post.commentsList = post.commentsList.map(function (comment) {
            return normalizeComment(comment);
        });

        return post.commentsList;
    }

    function normalizeComment(comment) {
        var raw = comment && typeof comment === "object" ? comment : {};
        var replies = Array.isArray(raw.replies) ? raw.replies : [];
        var author = raw.author ? String(raw.author) : "User";
        var commentId = raw.id ? String(raw.id) : "comment-" + (++nextCommentId);
        var commentNumericId = Number(commentId);
        if (isFinite(commentNumericId)) {
            nextCommentId = Math.max(nextCommentId, commentNumericId);
        }

        return {
            id: commentId,
            author: author,
            avatar: raw.avatar ? String(raw.avatar) : initialsForName(author),
            avatarImage: raw.avatarImage ? String(raw.avatarImage) : "",
            canManage: !!raw.canManage,
            isEditing: !!raw.isEditing,
            isConfirmingDelete: !!raw.isConfirmingDelete,
            likes: Math.max(0, Number(raw.likes) || 0),
            liked: !!raw.liked,
            replyShowsChain: !!raw.replyShowsChain,
            replyFromAuthor: raw.replyFromAuthor ? String(raw.replyFromAuthor) : "",
            replyToAuthor: raw.replyToAuthor ? String(raw.replyToAuthor) : "",
            time: raw.time ? String(raw.time) : "Just now",
            text: raw.text ? String(raw.text) : "",
            replies: replies.map(function (reply) {
                var rawReply = reply && typeof reply === "object" ? reply : {};
                var replyAuthor = rawReply.author ? String(rawReply.author) : "User";
                var replyId = rawReply.id ? String(rawReply.id) : "comment-" + (++nextCommentId);
                var replyNumericId = Number(replyId);
                if (isFinite(replyNumericId)) {
                    nextCommentId = Math.max(nextCommentId, replyNumericId);
                }
                return {
                    id: replyId,
                    author: replyAuthor,
                    avatar: rawReply.avatar ? String(rawReply.avatar) : initialsForName(replyAuthor),
                    avatarImage: rawReply.avatarImage ? String(rawReply.avatarImage) : "",
                    canManage: !!rawReply.canManage,
                    isEditing: !!rawReply.isEditing,
                    isConfirmingDelete: !!rawReply.isConfirmingDelete,
                    likes: Math.max(0, Number(rawReply.likes) || 0),
                    liked: !!rawReply.liked,
                    replyShowsChain: !!rawReply.replyShowsChain,
                    replyFromAuthor: rawReply.replyFromAuthor ? String(rawReply.replyFromAuthor) : "",
                    replyToAuthor: rawReply.replyToAuthor ? String(rawReply.replyToAuthor) : "",
                    time: rawReply.time ? String(rawReply.time) : "Just now",
                    text: rawReply.text ? String(rawReply.text) : ""
                };
            })
        };
    }

    function initialsForName(name) {
        var value = String(name || "").trim();
        if (!value) {
            return "U";
        }

        var parts = value.split(/\s+/).filter(Boolean);
        if (!parts.length) {
            return "U";
        }

        if (parts.length === 1) {
            return parts[0].slice(0, 1).toUpperCase();
        }

        return (parts[0].slice(0, 1) + parts[1].slice(0, 1)).toUpperCase();
    }

    function renderCommentAvatar(commentLike) {
        var avatarUrl = String(commentLike && commentLike.avatarImage ? commentLike.avatarImage : "").trim();
        var initials = String(commentLike && commentLike.avatar ? commentLike.avatar : initialsForName(commentLike && commentLike.author)).trim() || "U";
        if (avatarUrl) {
            return '<span class="ch-comment-avatar" aria-hidden="true"><img src="' + escapeHtml(avatarUrl) + '" alt=""></span>';
        }

        return '<span class="ch-comment-avatar" aria-hidden="true">' + escapeHtml(initials) + '</span>';
    }

    function commentCountFor(post) {
        var persisted = Number(post && post.commentCount);
        if (isFinite(persisted) && persisted >= 0) {
            return Math.floor(persisted);
        }

        return commentsFor(post).reduce(function (count, comment) {
            var replyCount = Array.isArray(comment.replies) ? comment.replies.length : 0;
            return count + 1 + replyCount;
        }, 0);
    }

    function ensurePostCommentState(post) {
        if (!post || typeof post !== "object") {
            return;
        }

        if (!Array.isArray(post.commentsList)) {
            post.commentsList = [];
        }

        var persistedCount = Number(post.commentCount);
        if (!isFinite(persistedCount) || persistedCount < 0) {
            persistedCount = post.commentsList.reduce(function (count, comment) {
                var replyCount = Array.isArray(comment.replies) ? comment.replies.length : 0;
                return count + 1 + replyCount;
            }, 0);
        }
        post.commentCount = Math.max(0, Math.floor(persistedCount));

        var offset = Number(post.commentsOffset);
        if (!isFinite(offset) || offset < 0) {
            offset = post.commentsList.length;
        }
        post.commentsOffset = Math.max(0, Math.floor(offset));

        post.commentsHasMore = !!post.commentsHasMore;
        post.commentsLoading = !!post.commentsLoading;
        post.commentsLoaded = !!post.commentsLoaded;
    }

    function mergeCommentsBatch(post, incomingComments, options) {
        ensurePostCommentState(post);

        var reset = !!(options && options.reset);
        var currentComments = reset ? [] : commentsFor(post).slice();
        var seenIds = new Set(currentComments.map(function (comment) {
            return String(comment.id);
        }));

        (incomingComments || []).forEach(function (comment) {
            var normalized = normalizeComment(comment);
            var id = String(normalized.id);
            if (seenIds.has(id)) {
                return;
            }
            currentComments.push(normalized);
            seenIds.add(id);
        });

        post.commentsList = currentComments;

        var incomingCount = Number(options && options.commentCount);
        if (isFinite(incomingCount) && incomingCount >= 0) {
            post.commentCount = Math.floor(incomingCount);
        }

        var incomingNextOffset = Number(options && options.nextOffset);
        if (isFinite(incomingNextOffset) && incomingNextOffset >= 0) {
            post.commentsOffset = Math.floor(incomingNextOffset);
        } else {
            post.commentsOffset = currentComments.length;
        }

        post.commentsHasMore = !!(options && options.hasMore);
        post.commentsLoaded = true;
    }

    function disconnectCommentLoadObserver() {
        if (!commentLoadObserver) {
            return;
        }

        commentLoadObserver.disconnect();
        commentLoadObserver = null;
    }

    function loadMoreCommentsForPost(post, reset) {
        ensurePostCommentState(post);

        var shouldReset = !!reset;
        if (post.commentsLoading) {
            return Promise.resolve(false);
        }

        if (!shouldReset && !post.commentsHasMore) {
            return Promise.resolve(false);
        }

        var nextOffset = shouldReset ? 0 : Math.max(0, Number(post.commentsOffset) || 0);
        var endpoint = buildPostActionEndpoint(post.id, "comments/?offset=" + nextOffset + "&limit=" + COMMENT_BATCH_SIZE);

        post.commentsLoading = true;
        renderFeed();

        return requestJson(endpoint, {
            method: "GET"
        }, "Unable to load comments.").then(function (payload) {
            var incomingComments = Array.isArray(payload && payload.comments) ? payload.comments : [];

            mergeCommentsBatch(post, incomingComments, {
                reset: shouldReset,
                hasMore: !!(payload && payload.hasMore),
                nextOffset: Number(payload && payload.nextOffset),
                commentCount: Number(payload && payload.commentCount)
            });

            return true;
        }).catch(function (error) {
            setStatus(error && error.message ? error.message : "Unable to load comments.");
            return false;
        }).finally(function () {
            post.commentsLoading = false;
            renderFeed();
        });
    }

    function refreshCommentsForPost(post) {
        ensurePostCommentState(post);

        if (post.commentsLoading || post.commentsHasMore) {
            return Promise.resolve(false);
        }

        var currentOffset = Math.max(0, Number(post.commentsOffset) || commentsFor(post).length);
        var endpoint = buildPostActionEndpoint(post.id, "comments/?offset=" + currentOffset + "&limit=" + COMMENT_BATCH_SIZE);

        return requestJson(endpoint, {
            method: "GET"
        }, "Unable to refresh comments.").then(function (payload) {
            var incomingComments = Array.isArray(payload && payload.comments) ? payload.comments : [];

            if (!incomingComments.length) {
                return false;
            }

            mergeCommentsBatch(post, incomingComments, {
                reset: false,
                hasMore: !!(payload && payload.hasMore),
                nextOffset: Number(payload && payload.nextOffset),
                commentCount: Number(payload && payload.commentCount)
            });

            return true;
        }).catch(function () {
            return false;
        });
    }

    function refreshVisibleCommentThreads() {
        if (document.hidden) {
            return;
        }

        var openPosts = state.posts.filter(function (post) {
            return post.showComments && !post.commentsLoading && !post.commentsHasMore;
        });

        if (!openPosts.length) {
            return;
        }

        openPosts.forEach(function (post) {
            refreshCommentsForPost(post).then(function (updated) {
                if (updated) {
                    renderFeed();
                }
            });
        });
    }

    function startCommentPolling() {
        if (commentRefreshTimer) {
            return;
        }

        commentRefreshTimer = window.setInterval(refreshVisibleCommentThreads, 15000);
        document.addEventListener("visibilitychange", function () {
            if (!document.hidden) {
                refreshVisibleCommentThreads();
            }
        });
    }

    function bindCommentLoadObserver() {
        disconnectCommentLoadObserver();

        if (typeof window.IntersectionObserver !== "function") {
            return;
        }

        var sentinels = Array.prototype.slice.call(feedHost.querySelectorAll("[data-comment-sentinel]"));
        if (!sentinels.length) {
            return;
        }

        commentLoadObserver = new window.IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) {
                    return;
                }

                var postId = String(entry.target.getAttribute("data-comment-sentinel") || "").trim();
                if (!postId) {
                    return;
                }

                var post = state.posts.find(function (item) {
                    return String(item.id) === postId;
                });
                if (!post || !post.showComments) {
                    return;
                }

                ensurePostCommentState(post);
                if (post.commentsLoading || !post.commentsHasMore) {
                    return;
                }

                loadMoreCommentsForPost(post, false);
            });
        }, {
            root: feedHost,
            rootMargin: "180px 0px",
            threshold: 0.01
        });

        sentinels.forEach(function (sentinel) {
            commentLoadObserver.observe(sentinel);
        });
    }

    function maybeLoadNextCommentBatchesOnScroll() {
        var sentinels = Array.prototype.slice.call(feedHost.querySelectorAll("[data-comment-sentinel]"));
        if (!sentinels.length) {
            return;
        }

        var hostRect = feedHost.getBoundingClientRect();
        var thresholdPx = 140;

        sentinels.forEach(function (sentinel) {
            var postId = String(sentinel.getAttribute("data-comment-sentinel") || "").trim();
            if (!postId) {
                return;
            }

            var post = state.posts.find(function (item) {
                return String(item.id) === postId;
            });
            if (!post || !post.showComments) {
                return;
            }

            ensurePostCommentState(post);
            if (post.commentsLoading || !post.commentsHasMore) {
                return;
            }

            var sentinelRect = sentinel.getBoundingClientRect();
            var distanceToBottom = sentinelRect.bottom - hostRect.bottom;
            if (distanceToBottom > thresholdPx) {
                return;
            }

            loadMoreCommentsForPost(post, false);
        });
    }

    function findCommentById(post, commentId) {
        var targetId = String(commentId || "").trim();
        if (!targetId) {
            return null;
        }

        return commentsFor(post).find(function (comment) {
            return String(comment.id) === targetId;
        }) || null;
    }

    function findCommentOrReplyById(post, targetId) {
        var id = String(targetId || "").trim();
        if (!id) {
            return null;
        }

        var comments = commentsFor(post);
        for (var index = 0; index < comments.length; index += 1) {
            var comment = comments[index];
            if (String(comment.id) === id) {
                return {
                    item: comment,
                    type: "comment",
                    parentComment: comment,
                    author: String(comment.author || "User")
                };
            }

            var replies = Array.isArray(comment.replies) ? comment.replies : [];
            for (var replyIndex = 0; replyIndex < replies.length; replyIndex += 1) {
                var reply = replies[replyIndex];
                if (String(reply.id) === id) {
                    return {
                        item: reply,
                        type: "reply",
                        parentComment: comment,
                        author: String(reply.author || "User")
                    };
                }
            }
        }

        return null;
    }

    function normalizeIncomingImage(image) {
        var src = image && (image.src || image.previewUrl || image.url) ? String(image.src || image.previewUrl || image.url) : "";
        if (!src.trim()) {
            return null;
        }

        var name = image && image.name ? String(image.name) : "Post image";
        return {
            id: image && image.id ? String(image.id) : "",
            src: src,
            previewUrl: String(image.previewUrl || src),
            alt: image && image.alt ? String(image.alt) : name,
            name: name,
            isImage: true
        };
    }

    function normalizeIncomingAttachment(attachment) {
        var name = attachment && attachment.name ? String(attachment.name) : "Attachment";
        var url = attachment && (attachment.url || attachment.src || attachment.previewUrl) ? String(attachment.url || attachment.src || attachment.previewUrl) : "";
        var isImage = !!(attachment && attachment.isImage);

        if (!name.trim() && !url.trim()) {
            return null;
        }

        return {
            id: attachment && attachment.id ? String(attachment.id) : "",
            name: name,
            url: url,
            src: isImage ? url : "",
            previewUrl: isImage ? String(attachment.previewUrl || url) : "",
            sizeLabel: attachment && attachment.sizeLabel ? String(attachment.sizeLabel) : "",
            icon: attachment && attachment.icon ? String(attachment.icon) : "file",
            isImage: isImage
        };
    }

    function splitAttachments(attachments) {
        var images = [];
        var files = [];

        Array.isArray(attachments) && attachments.forEach(function (attachment) {
            if (!attachment) {
                return;
            }

            var fileName = String(attachment.name || "Attachment");
            if (attachment.isImage) {
                images.push({
                    src: String(attachment.previewUrl || attachment.src || ""),
                    previewUrl: String(attachment.previewUrl || attachment.src || ""),
                    alt: fileName,
                    name: fileName,
                    isImage: true
                });
                return;
            }

            files.push({
                name: fileName,
                url: String(attachment.url || attachment.previewUrl || ""),
                previewUrl: "",
                sizeLabel: String(attachment.sizeLabel || "Attachment"),
                icon: String(attachment.icon || "file"),
                isImage: false
            });
        });

        return {
            images: images,
            attachments: files
        };
    }

    function attachmentsFor(post) {
        if (!Array.isArray(post.attachments)) {
            post.attachments = [];
        }

        return post.attachments;
    }

    function imageAttachmentsFor(post) {
        var directImages = Array.isArray(post && post.images) ? post.images.filter(function (image) {
            return !!(image && (image.previewUrl || image.src));
        }).map(function (image) {
            var source = String(image.previewUrl || image.src || "");
            return {
                previewUrl: source,
                src: source,
                alt: String(image.alt || image.name || "Post image"),
                isImage: true
            };
        }) : [];

        if (directImages.length) {
            return directImages;
        }

        return attachmentsFor(post).filter(function (attachment) {
            return !!(attachment && attachment.isImage && attachment.previewUrl);
        });
    }

    function syncMediaViewer() {
        if (!mediaViewerImage || !mediaViewerState.images.length) {
            return;
        }

        var current = mediaViewerState.images[mediaViewerState.index];
        mediaViewerImage.src = String(current.previewUrl || "");
        mediaViewerImage.alt = "Post image " + (mediaViewerState.index + 1);

        if (mediaViewerCount) {
            mediaViewerCount.textContent = (mediaViewerState.index + 1) + " / " + mediaViewerState.images.length;
        }

        var hasMultiple = mediaViewerState.images.length > 1;
        if (mediaViewerPrev) {
            mediaViewerPrev.disabled = !hasMultiple;
        }
        if (mediaViewerNext) {
            mediaViewerNext.disabled = !hasMultiple;
        }
    }

    function closeMediaViewer() {
        if (!mediaViewer) {
            return;
        }

        mediaViewer.setAttribute("hidden", "");
        if (mediaViewerImage) {
            mediaViewerImage.removeAttribute("src");
            mediaViewerImage.alt = "";
        }

        mediaViewerState.images = [];
        mediaViewerState.index = 0;
        document.body.classList.remove("ch-media-viewer-open");
    }

    function openMediaViewer(images, startIndex) {
        if (!mediaViewer || !mediaViewerImage || !Array.isArray(images) || !images.length) {
            return;
        }

        var initial = Number(startIndex);
        if (!isFinite(initial)) {
            initial = 0;
        }

        mediaViewerState.images = images.slice();
        mediaViewerState.index = Math.max(0, Math.min(mediaViewerState.images.length - 1, Math.floor(initial)));

        mediaViewer.removeAttribute("hidden");
        document.body.classList.add("ch-media-viewer-open");
        syncMediaViewer();
    }

    function moveMediaViewer(step) {
        if (!mediaViewerState.images.length) {
            return;
        }

        var total = mediaViewerState.images.length;
        var delta = Number(step) || 0;
        if (!delta) {
            return;
        }

        mediaViewerState.index = (mediaViewerState.index + delta + total) % total;
        syncMediaViewer();
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }

        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function renderCommentManagementControls(item, itemLabel) {
        if (!item.canManage) return "";

        var commentId = escapeHtml(item.id);
        if (item.isEditing) {
            return [
                '<form class="ch-comment-edit-form" data-comment-edit-form data-comment-edit-id="' + commentId + '">',
                '<label class="sr-only" for="community-comment-edit-' + commentId + '">Edit ' + escapeHtml(itemLabel) + '</label>',
                '<textarea id="community-comment-edit-' + commentId + '" name="edited_comment" maxlength="280" required>' + escapeHtml(item.text) + '</textarea>',
                '<div class="ch-comment-manage-actions">',
                '<button type="submit" class="ch-comment-manage-save">Save</button>',
                '<button type="button" data-comment-edit-cancel="' + commentId + '">Cancel</button>',
                '</div>',
                '</form>'
            ].join("");
        }

        if (item.isConfirmingDelete) {
            return [
                '<div class="ch-comment-delete-confirm" role="group" aria-label="Confirm comment deletion">',
                '<span>Delete this comment?</span>',
                '<button type="button" data-comment-delete-cancel="' + commentId + '">Cancel</button>',
                '<button type="button" class="is-danger" data-comment-delete-confirm="' + commentId + '">Delete</button>',
                '</div>'
            ].join("");
        }

        return [
            '<div class="ch-comment-manage-actions">',
            '<button type="button" data-comment-edit-open="' + commentId + '" aria-label="Edit ' + escapeHtml(itemLabel) + '">Edit</button>',
            '<button type="button" class="is-danger" data-comment-delete-open="' + commentId + '" aria-label="Delete ' + escapeHtml(itemLabel) + '">Delete</button>',
            '</div>'
        ].join("");
    }

    function renderComments(post) {
        if (!post.showComments) {
            return "";
        }

        ensurePostCommentState(post);
        var comments = commentsFor(post);
        var replyTargetId = String(post.replyingToCommentId || "");
        var replyTarget = findCommentOrReplyById(post, replyTargetId);

        var commentsMarkup = comments.length ? comments.map(function (comment) {
            var replies = Array.isArray(comment.replies) ? comment.replies : [];
            var repliesMarkup = replies.length ? replies.map(function (reply) {
                var chainText = (reply.replyShowsChain && reply.replyFromAuthor && reply.replyToAuthor)
                    ? (escapeHtml(reply.replyFromAuthor) + ' &gt; ' + escapeHtml(reply.replyToAuthor))
                    : "";
                return [
                    '<article class="ch-reply">',
                    '<div class="ch-comment-row">',
                    renderCommentAvatar(reply),
                    '<div class="ch-comment-body">',
                    '<p class="ch-comment-meta">',
                    chainText ? '<span class="ch-comment-chain-inline">' + chainText + '</span>' : '',
                    chainText ? '<span class="ch-post-separator" aria-hidden="true">&bull;</span>' : '',
                    '<span class="ch-comment-time">' + escapeHtml(reply.time) + '</span>',
                    '</p>',
                    '<p class="ch-comment-text">' + escapeHtml(reply.text) + '</p>',
                    '<div class="ch-comment-actions">',
                    '<button type="button" class="ch-comment-action' + (reply.liked ? ' is-active' : '') + ' focus-ring" data-comment-like-toggle="' + escapeHtml(reply.id) + '" aria-label="Like reply">',
                    '<i data-lucide="heart" class="ch-icon" aria-hidden="true"></i>',
                    '<span class="ch-comment-action-count">' + Math.max(0, Number(reply.likes) || 0) + '</span>',
                    '</button>',
                    '<button type="button" class="ch-comment-action' + (replyTargetId === String(reply.id) ? ' is-active' : '') + ' focus-ring" data-comment-reply-toggle="' + escapeHtml(reply.id) + '" aria-label="Reply to this reply">',
                    '<i data-lucide="corner-up-left" class="ch-icon" aria-hidden="true"></i>',
                    '</button>',
                    '</div>',
                    renderCommentManagementControls(reply, "reply"),
                    '</div>',
                    '</div>',
                    '</article>'
                ].join("");
            }).join("") : "";

            return [
                '<article class="ch-comment">',
                '<div class="ch-comment-row">',
                renderCommentAvatar(comment),
                '<div class="ch-comment-body">',
                '<p class="ch-comment-meta">',
                '<span class="ch-comment-author">' + escapeHtml(comment.author) + '</span>',
                '<span class="ch-post-separator" aria-hidden="true">&bull;</span>',
                '<span class="ch-comment-time">' + escapeHtml(comment.time) + '</span>',
                '</p>',
                '<p class="ch-comment-text">' + escapeHtml(comment.text) + '</p>',
                '<div class="ch-comment-actions">',
                '<button type="button" class="ch-comment-action' + (comment.liked ? ' is-active' : '') + ' focus-ring" data-comment-like-toggle="' + escapeHtml(comment.id) + '" aria-label="Like comment">',
                '<i data-lucide="heart" class="ch-icon" aria-hidden="true"></i>',
                '<span class="ch-comment-action-count">' + Math.max(0, Number(comment.likes) || 0) + '</span>',
                '</button>',
                '<button type="button" class="ch-comment-action' + (replyTargetId === String(comment.id) ? ' is-active' : '') + ' focus-ring" data-comment-reply-toggle="' + escapeHtml(comment.id) + '" aria-label="Reply to comment">',
                '<i data-lucide="corner-up-left" class="ch-icon" aria-hidden="true"></i>',
                '</button>',
                '</div>',
                renderCommentManagementControls(comment, "comment"),
                repliesMarkup ? '<div class="ch-reply-list">' + repliesMarkup + '</div>' : '',
                '</div>',
                '</div>',
                '</article>'
            ].join("");
        }).join("") : (post.commentsLoading
            ? '<div class="ch-comment-loading" aria-live="polite"><span class="ch-comment-spinner" aria-hidden="true"></span><span>Loading comments...</span></div>'
            : '<p class="ch-comment-empty">No comments yet. Start the conversation.</p>');

        var loadingMoreMarkup = post.commentsLoading && comments.length
            ? '<div class="ch-comment-loading" aria-live="polite"><span class="ch-comment-spinner" aria-hidden="true"></span><span>Loading more comments...</span></div>'
            : "";
        var sentinelMarkup = post.commentsHasMore
            ? '<div class="ch-comment-sentinel" data-comment-sentinel="' + escapeHtml(post.id) + '" aria-hidden="true"></div>'
            : "";

        return [
            '<section class="ch-comments" aria-label="Comments">',
            '<div class="ch-comment-list">' + commentsMarkup + '</div>',
            loadingMoreMarkup,
            sentinelMarkup,
            '<form class="ch-comment-compose" data-comment-form="true">',
            replyTarget ? '<p class="ch-comment-target" aria-live="polite">Reply to ' + escapeHtml(replyTarget.author) + '</p>' : '',
            '<label class="sr-only" for="community-comment-input-' + escapeHtml(post.id) + '">' + (replyTarget ? 'Reply to ' + escapeHtml(replyTarget.author) : 'Add a comment') + '</label>',
            '<input id="community-comment-input-' + escapeHtml(post.id) + '" name="comment" class="ch-comment-input focus-ring" type="text" placeholder="' + (replyTarget ? 'Reply to ' + escapeHtml(replyTarget.author) + '...' : 'Write a comment...') + '" maxlength="280" required>',
            '<button type="submit" class="ch-comment-submit focus-ring">' + (replyTarget ? 'Reply' : 'Post') + '</button>',
            '</form>',
            '</section>'
        ].join("");
    }

    function renderPostAvatar(post) {
        var avatarUrl = String(post && post.avatarImage ? post.avatarImage : "").trim();
        if (avatarUrl) {
            return '<span class="ch-post-avatar" aria-hidden="true"><img src="' + escapeHtml(avatarUrl) + '" alt=""></span>';
        }

        return '<span class="ch-post-avatar" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>';
    }

    function renderPostAttachments(post) {
        var images = imageAttachmentsFor(post);
        if (!images.length) {
            return "";
        }

        var totalImages = images.length;
        var currentIndex = Number(post.carouselIndex);
        if (!isFinite(currentIndex) || currentIndex < 0 || currentIndex >= totalImages) {
            currentIndex = 0;
        }
        post.carouselIndex = currentIndex;

        var currentImage = images[currentIndex];
        var hasMultiple = totalImages > 1;

        return [
            '<div class="ch-post-attachments" aria-label="Attached images">',
            '<div class="ch-post-carousel">',
            hasMultiple ? '<button type="button" class="ch-post-carousel-nav is-prev focus-ring" data-post-carousel-nav="prev" aria-label="Previous image"><i data-lucide="chevron-left" class="ch-icon" aria-hidden="true"></i></button>' : '',
            '<button type="button" class="ch-post-media-item focus-ring" data-post-media-view="' + escapeHtml(post.id) + '" data-post-media-index="' + currentIndex + '" aria-label="View image ' + (currentIndex + 1) + ' of ' + totalImages + '">',
            '<img class="ch-post-media-backdrop" src="' + escapeHtml(currentImage.previewUrl) + '" alt="" aria-hidden="true" loading="lazy">',
            '<span class="ch-post-media-glass" aria-hidden="true"></span>',
            '<img class="ch-post-media-image" src="' + escapeHtml(currentImage.previewUrl) + '" alt="Attached image">',
            '</button>',
            hasMultiple ? '<button type="button" class="ch-post-carousel-nav is-next focus-ring" data-post-carousel-nav="next" aria-label="Next image"><i data-lucide="chevron-right" class="ch-icon" aria-hidden="true"></i></button>' : '',
            hasMultiple ? '<p class="ch-post-carousel-count">' + (currentIndex + 1) + ' / ' + totalImages + '</p>' : '',
            '</div>',
            '</div>'
        ].join("");
    }

    function renderActivityAnnouncement(post) {
        var activity = post && post.activity && typeof post.activity === "object" ? post.activity : null;
        if (!activity || !activity.isAnnouncement) {
            return "";
        }

        var title = String(activity.title || post.title || "").trim();
        var dateTime = String(activity.dateTime || "").trim();
        var location = String(activity.location || "").trim();
        var details = [];

        if (dateTime) {
            details.push(dateTime);
        }

        if (location) {
            details.push(location);
        }

        if (!details.length) {
            details.push("To be announced");
        }

        return [
            title ? '<h4 class="ch-post-title">' + escapeHtml(title) + '</h4>' : '',
            '<p class="ch-post-content">' + escapeHtml(details.join(" • ")) + '</p>'
        ].join("");
    }

    function renderFeed() {
        var posts = filteredPosts();

        feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");

        if (!posts.length) {
            feedHost.innerHTML = state.postsLoading
                ? '<p class="cm-empty">Loading posts...</p>'
                : '<p class="cm-empty">No posts in this filter yet.</p>';
            disconnectCommentLoadObserver();
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            var commentCount = commentCountFor(post);
            var postTitle = String(post.title || "").trim();
            var isReportedByViewer = !!post.reportedByViewer;
            var attachmentsMarkup = isReportedByViewer ? "" : renderPostAttachments(post);
            var hasMedia = !!attachmentsMarkup;
            var isMenuOpen = openPostMenuId === post.id;
            var isAnnouncement = isAnnouncementPost(post);
            var activityMarkup = renderActivityAnnouncement(post);
            var typeTagMarkup = isAnnouncement ? '<span class="ch-post-type-tag" aria-label="Announcement">Announcement</span>' : '';
            var typeTagMobileIconMarkup = isAnnouncement ? '<span class="ch-post-type-tag ch-post-type-tag--mobile-icon" aria-label="Announcement"><i data-lucide="megaphone" class="ch-icon" aria-hidden="true"></i></span>' : '';
            var isEditing = !!post.isEditing;
            var editDraft = String(post.editDraft != null ? post.editDraft : post.content || "");
            var editMarkup = [
                '<div class="ch-post-edit">',
                '<label class="sr-only" for="community-post-edit-input-' + escapeHtml(post.id) + '">Edit post</label>',
                '<textarea id="community-post-edit-input-' + escapeHtml(post.id) + '" class="ch-post-edit-input focus-ring" data-post-edit-input="' + escapeHtml(post.id) + '" rows="4">' + escapeHtml(editDraft) + '</textarea>',
                '<div class="ch-post-edit-attachments" data-post-edit-attachments="' + escapeHtml(post.id) + '">' + renderEditAttachments(post) + '</div>',
                '<div class="ch-post-edit-attachment-tools">',
                '<button type="button" class="ch-chatbox-icon focus-ring" data-edit-attachment-menu="' + escapeHtml(post.id) + '" aria-label="Add attachment"><i data-lucide="plus" class="ch-icon"></i></button>',
                '<span class="ch-post-edit-attachment-picker" data-edit-attachment-picker="' + escapeHtml(post.id) + '" hidden>',
                '<button type="button" class="ch-chat-attach-btn focus-ring" data-edit-attach-images="' + escapeHtml(post.id) + '" aria-label="Attach images"><i data-lucide="image" class="ch-icon"></i></button>',
                '<button type="button" class="ch-chat-attach-btn focus-ring" data-edit-attach-files="' + escapeHtml(post.id) + '" aria-label="Attach files"><i data-lucide="paperclip" class="ch-icon"></i></button>',
                '</span>',
                '<input type="file" accept="image/*" multiple hidden data-edit-attachment-input="' + escapeHtml(post.id) + '" data-edit-attachment-kind="image">',
                '<input type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.zip,.rar" multiple hidden data-edit-attachment-input="' + escapeHtml(post.id) + '" data-edit-attachment-kind="file">',
                '<div class="ch-post-edit-actions">',
                '<button type="button" class="ch-post-edit-cancel focus-ring" data-post-edit-cancel="' + escapeHtml(post.id) + '">Cancel</button>',
                '<button type="button" class="ch-post-edit-save focus-ring" data-post-edit-save="' + escapeHtml(post.id) + '">Save</button>',
                '</div>',
                '</div>'
            ].join("");
            var bodyMarkup = isEditing
                ? editMarkup
                : isReportedByViewer
                    ? '<p class="ch-post-content">This post is hidden.</p>'
                    : activityMarkup
                        ? activityMarkup
                        : (postTitle ? '<h4 class="ch-post-title">' + escapeHtml(postTitle) + '</h4>' : '') + '<p class="ch-post-content">' + escapeHtml(post.content) + '</p>';

            var isAuthor = Boolean(post.isAuthor || (post.authorId && String(post.authorId) === String(currentUser.id)));
            var canDelete = isAuthor || currentUser.isAdmin;
            var canEdit = isAuthor;
            var canReport = !isAuthor && !currentUser.isAdmin;
            var menuItems = [];
            if (canEdit) {
                menuItems.push('<button type="button" class="ch-post-menu-item" data-post-menu-action="edit-post" role="menuitem"><i data-lucide="edit-2" class="ch-icon" aria-hidden="true"></i><span>Edit</span></button>');
            }
            if (canDelete) {
                menuItems.push('<button type="button" class="ch-post-menu-item is-danger" data-post-menu-action="delete-post" role="menuitem"><i data-lucide="trash-2" class="ch-icon" aria-hidden="true"></i><span>Delete</span></button>');
            }
            if (canReport) {
                menuItems.push('<button type="button" class="ch-post-menu-item" data-post-menu-action="report-post" role="menuitem"><i data-lucide="flag" class="ch-icon" aria-hidden="true"></i><span>Report</span></button>');
            }
            if (!menuItems.length) {
                menuItems.push('<button type="button" class="ch-post-menu-item" disabled role="menuitem">No actions available</button>');
            }

            var postMenu = [
                '<div class="ch-post-menu' + (isMenuOpen ? ' is-open' : '') + '">',
                '<button type="button" class="ch-post-menu-toggle focus-ring" data-post-menu-toggle="' + escapeHtml(post.id) + '" aria-haspopup="menu" aria-expanded="' + (isMenuOpen ? "true" : "false") + '" aria-label="Post options">',
                '<i data-lucide="ellipsis" class="ch-icon" aria-hidden="true"></i>',
                '</button>',
                '<div class="ch-post-menu-panel" role="menu" aria-label="Post actions">',
                menuItems.join(""),
                '</div>',
                '</div>'
            ].join("");

            return [
                '<article class="ch-post' + (hasMedia ? ' has-media' : '') + '" data-post-id="' + escapeHtml(post.id) + '" data-post-type="' + escapeHtml(post.type || 'discussions') + '">',
                '<header class="ch-post-head">',
                renderPostAvatar(post),
                '<p class="ch-post-author">' + escapeHtml(post.author) + '</p>',
                typeTagMarkup,
                typeTagMobileIconMarkup,
                '<span class="ch-post-separator" aria-hidden="true">&bull;</span>',
                '<p class="ch-post-time" data-post-timestamp="' + escapeHtml(post.timestampAt || post.timestamp) + '">' + escapeHtml(relativeTimeLabel(post.timestampAt || post.timestamp)) + '</p>',
                postMenu,
                '</header>',
                bodyMarkup,
                attachmentsMarkup,
                '<div class="ch-post-actions">',
                '<button type="button" class="ch-post-action' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post">',
                '<i data-lucide="heart" aria-hidden="true"></i>',
                '<span class="ch-post-action-count">' + post.likes + '</span>',
                '</button>',
                '<button type="button" class="ch-post-action" data-post-action="comment" aria-label="Comment on post">',
                '<i data-lucide="message-circle" aria-hidden="true"></i>',
                '<span class="ch-post-action-count">' + commentCount + '</span>',
                '</button>',
                '</div>',
                renderComments(post),
                '</article>'
            ].join("");
        }).join("");

        if (state.postsLoading && state.posts.length) {
            feedHost.insertAdjacentHTML("beforeend", '<p class="cm-empty" aria-live="polite">Loading more posts...</p>');
        } else if (state.postsHasMore) {
            feedHost.insertAdjacentHTML("beforeend", '<div class="cm-post-sentinel" aria-hidden="true"></div>');
        }

        refreshIcons();
        bindCommentLoadObserver();
        maybeLoadNextCommentBatchesOnScroll();
        maybeLoadNextPostsBatch();
        refreshRelativeTimestamps();
    }

    function renderList(host, items) {
        if (!host) {
            return;
        }

        if (!items.length) {
            host.innerHTML = '<p class="ch-empty">No updates yet.</p>';
            return;
        }

        host.innerHTML = items.map(function (item) {
            return '<p class="ch-list-item">' + escapeHtml(item) + '</p>';
        }).join("");
    }

    function setActiveTab(tabName, shouldFocus) {
        state.activeTab = tabName;

        tabs.forEach(function (tab) {
            var selected = tab.getAttribute("data-community-tab") === tabName;
            tab.setAttribute("aria-selected", selected ? "true" : "false");
            tab.tabIndex = selected ? 0 : -1;

            if (selected && shouldFocus) {
                tab.focus();
            }
        });

        renderFeed();
    }

    function createPost(content, type, attachments) {
        var text = String(content || "").trim();
        if (!text) {
            setStatus("Please write a short message first.");
            return false;
        }

        var split = splitAttachments(attachments);
        var normalizedType = String(type || "discussions").trim().toLowerCase();
        if (normalizedType === "livelihood" || normalizedType === "gardening") {
            normalizedType = "tips";
        } else if (normalizedType !== "discussions" && normalizedType !== "tips" && normalizedType !== "announcements") {
            normalizedType = "discussions";
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: currentUser.name || "You",
            authorId: currentUser.id || "",
            isAuthor: true,
            avatar: currentUser.initials || "YO",
            avatarImage: currentUser.avatarUrl || "",
            timestamp: "Just now",
            timestampAt: new Date().toISOString(),
            title: "",
            content: text,
            type: normalizedType,
            likes: 0,
            liked: false,
            showComments: false,
            replyingToCommentId: null,
            commentsList: [],
            commentCount: 0,
            commentsHasMore: false,
            commentsNextOffset: null,
            commentsOffset: 0,
            commentsLoading: false,
            commentsLoaded: true,
            images: split.images,
            attachments: split.attachments
        });

        setActiveTab("all", false);
        return true;
    }

    function normalizeIncomingPost(rawPost) {
        var images = Array.isArray(rawPost && rawPost.images) ? rawPost.images.map(normalizeIncomingImage).filter(Boolean) : [];
        var attachments = Array.isArray(rawPost && rawPost.attachments) ? rawPost.attachments.map(normalizeIncomingAttachment).filter(Boolean) : [];
        var postId = rawPost && rawPost.id ? String(rawPost.id) : "post-" + (++nextPostId);
        var postNumericId = Number(postId);
        if (isFinite(postNumericId)) {
            nextPostId = Math.max(nextPostId, postNumericId);
        }

        if (!images.length && attachments.length) {
            images = attachments.filter(function (attachment) {
                return !!(attachment && attachment.isImage && attachment.previewUrl);
            }).map(function (attachment) {
                return {
                    src: attachment.previewUrl,
                    previewUrl: attachment.previewUrl,
                    alt: attachment.alt || attachment.name || "Post image",
                    name: attachment.name || "Post image",
                    isImage: true
                };
            });
        }

        var comments = Array.isArray(rawPost && rawPost.commentsList) ? rawPost.commentsList.map(normalizeComment) : [];
        var commentCount = Math.max(0, Number(rawPost && rawPost.commentCount) || 0);
        var commentsHasMore = !!(rawPost && rawPost.commentsHasMore);
        var commentsNextOffset = Number(rawPost && rawPost.commentsNextOffset);
        if (!isFinite(commentsNextOffset) || commentsNextOffset < 0) {
            commentsNextOffset = comments.length;
        }

        return {
            id: postId,
            author: rawPost && rawPost.author ? String(rawPost.author) : "User",
            authorId: rawPost && rawPost.authorId ? String(rawPost.authorId) : "",
            isAuthor: !!(rawPost && rawPost.isAuthor),
            avatar: rawPost && rawPost.avatar ? String(rawPost.avatar) : "U",
            avatarImage: rawPost && rawPost.avatarImage ? String(rawPost.avatarImage) : "",
            timestamp: rawPost && rawPost.timestamp ? String(rawPost.timestamp) : "Just now",
            timestampAt: rawPost && rawPost.timestampIso ? String(rawPost.timestampIso) : (rawPost && rawPost.timestamp ? String(rawPost.timestamp) : ""),
            title: rawPost && rawPost.title ? String(rawPost.title) : "",
            content: rawPost && rawPost.content ? String(rawPost.content) : "",
            type: rawPost && rawPost.type ? String(rawPost.type) : "discussions",
            likes: Math.max(0, Number(rawPost && rawPost.likes) || 0),
            liked: !!(rawPost && rawPost.liked),
            reportedByViewer: !!(rawPost && rawPost.reportedByViewer),
            showComments: !!(rawPost && rawPost.showComments),
            replyingToCommentId: null,
            commentsList: comments,
            commentCount: commentCount,
            commentsHasMore: commentsHasMore,
            commentsNextOffset: commentsHasMore ? commentsNextOffset : null,
            commentsOffset: commentsHasMore ? commentsNextOffset : comments.length,
            commentsLoading: false,
            commentsLoaded: comments.length > 0 || commentCount === 0,
            images: images,
            attachments: attachments,
            activity: rawPost && rawPost.activity && typeof rawPost.activity === "object"
                ? {
                    title: String(rawPost.activity.title || ""),
                    date: String(rawPost.activity.date || ""),
                    time: String(rawPost.activity.time || ""),
                    dateTime: String(rawPost.activity.dateTime || ""),
                    location: String(rawPost.activity.location || ""),
                    isAnnouncement: !!rawPost.activity.isAnnouncement
                }
                : null
        };
    }

    function loadPostsFromServer(reset) {
        var shouldReset = reset !== false;

        if (!postsEndpoint) {
            renderFeed();
            return Promise.resolve(false);
        }

        if (state.postsLoading) {
            return Promise.resolve(false);
        }

        if (!shouldReset && !state.postsHasMore) {
            return Promise.resolve(false);
        }

        var nextOffset = shouldReset ? 0 : Math.max(0, Number(state.postsOffset) || 0);
        var separator = postsEndpoint.indexOf("?") === -1 ? "?" : "&";
        var endpoint = postsEndpoint + separator + "offset=" + encodeURIComponent(String(nextOffset)) + "&limit=" + encodeURIComponent(String(POST_BATCH_SIZE));

        state.postsLoading = true;
        if (shouldReset) {
            state.posts = [];
            state.postsHasMore = false;
            state.postsOffset = 0;
        }
        renderFeed();

        return requestJson(endpoint, {
            method: "GET"
        }, "Unable to load posts.").then(function (payload) {
            var incoming = Array.isArray(payload && payload.posts) ? payload.posts.map(normalizeIncomingPost) : [];

            if (shouldReset) {
                state.posts = incoming;
            } else {
                var existingIds = new Set(state.posts.map(function (post) {
                    return String(post.id);
                }));

                incoming.forEach(function (post) {
                    var id = String(post.id);
                    if (existingIds.has(id)) {
                        return;
                    }
                    state.posts.push(post);
                    existingIds.add(id);
                });
            }

            var nextOffsetFromPayload = Number(payload && payload.nextOffset);
            if (isFinite(nextOffsetFromPayload) && nextOffsetFromPayload >= 0) {
                state.postsOffset = Math.floor(nextOffsetFromPayload);
            } else {
                state.postsOffset = state.posts.length;
            }

            state.postsHasMore = !!(payload && payload.hasMore);
            return true;
        }).catch(function (error) {
            setStatus(error && error.message ? error.message : "Unable to load posts.");
            return false;
        }).finally(function () {
            state.postsLoading = false;
            renderFeed();
        });
    }

    function maybeLoadNextPostsBatch() {
        if (state.postsLoading || !state.postsHasMore) {
            return;
        }

        var threshold = 96;
        var activeScrollHost = dashboardScrollHost && dashboardScrollHost !== feedHost ? dashboardScrollHost : feedHost;
        var distanceFromBottom = 0;

        if (activeScrollHost === feedHost) {
            distanceFromBottom = (feedHost.scrollHeight - feedHost.clientHeight) - feedHost.scrollTop;
        } else {
            var hostRect = activeScrollHost.getBoundingClientRect();
            var feedRect = feedHost.getBoundingClientRect();
            distanceFromBottom = feedRect.bottom - hostRect.bottom;
        }

        if (distanceFromBottom > threshold) {
            return;
        }

        loadPostsFromServer(false);
    }

    function createPostOnServer(content, type, attachments) {
        if (!createPostEndpoint) {
            return Promise.resolve(null);
        }
        if (typeof window.communityCreatePost === "function") {
            return window.communityCreatePost(createPostEndpoint, content, type, attachments);
        }
        return Promise.reject(new Error("Community post composer is unavailable."));
    }

    function togglePostLikeOnServer(postId) {
        var endpoint = buildPostActionEndpoint(postId, "like/");
        return requestJson(endpoint, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            }
        }, "Unable to update post like.");
    }

    function updatePostOnServer(postId, content, post) {
        var endpoint = buildPostActionEndpoint(postId, "update/");
        var body = new FormData();
        body.append("content", String(content || ""));
        if (post && post.editAttachments) {
            body.append("attachments_changed", "1");
            var currentIds = new Set(post.editAttachments.filter(function (item) { return item.id && !item.isNew; }).map(function (item) { return String(item.id); }));
            (post.editOriginalAttachments || []).forEach(function (item) {
                if (!currentIds.has(String(item.id))) {
                    body.append("remove_attachment_ids", String(item.id));
                }
            });
            (post.editNewAttachments || []).forEach(function (item) {
                if (item.file) body.append("attachments", item.file, item.name || item.file.name || "attachment");
            });
        }

        return fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            },
            body: body
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    var message = data && data.error ? data.error : "Unable to update post.";
                    throw new Error(message);
                }
                return data;
            });
        });
    }

    function editAttachmentItems(post) {
        var items = [];
        (Array.isArray(post.images) ? post.images : []).forEach(function (image) {
            items.push({ id: image.id, name: image.name || "Image", previewUrl: image.previewUrl || image.src || image.url || "", isImage: true });
        });
        (Array.isArray(post.attachments) ? post.attachments : []).forEach(function (attachment) {
            items.push({ id: attachment.id, name: attachment.name || "Attachment", previewUrl: "", isImage: false, url: attachment.url || "" });
        });
        return items;
    }

    function renderEditAttachments(post) {
        var items = Array.isArray(post.editAttachments) ? post.editAttachments : [];
        if (!items.length) return '<p class="ch-post-edit-attachments-empty">No attachments selected.</p>';
        return items.map(function (item) {
            var media = item.isImage && item.previewUrl
                ? '<img class="ch-chat-selected-thumb" src="' + escapeHtml(item.previewUrl) + '" alt="">'
                : '<span class="ch-chat-selected-file" aria-hidden="true"><i data-lucide="paperclip" class="ch-icon"></i></span>';
            return '<article class="ch-chat-selected-label">' + media + '<button type="button" class="ch-chat-selected-remove focus-ring" data-edit-remove-attachment="' + escapeHtml(item.id || item.tempId) + '" aria-label="Remove attachment">&#10005;</button></article>';
        }).join('');
    }

    function deletePostOnServer(postId) {
        var endpoint = buildPostActionEndpoint(postId, "delete/");
        return fetch(endpoint, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            }
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    var message = data && data.error ? data.error : "Unable to delete post.";
                    throw new Error(message);
                }
                return data;
            });
        });
    }

    function toggleCommentLikeOnServer(postId, commentId) {
        var endpoint = buildCommentActionEndpoint(postId, commentId, "like/");
        return requestJson(endpoint, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            }
        }, "Unable to update comment like.");
    }

    function updateCommunityCommentOnServer(postId, commentId, content) {
        var endpoint = buildCommentActionEndpoint(postId, commentId, "edit/");
        var body = new FormData();
        body.append("content", String(content || ""));
        return requestJson(endpoint, {
            method: "POST",
            headers: { "X-CSRFToken": getCookie("csrftoken") || "" },
            body: body
        }, "Unable to edit comment.");
    }

    function deleteCommunityCommentOnServer(postId, commentId) {
        var endpoint = buildCommentActionEndpoint(postId, commentId, "delete/");
        return requestJson(endpoint, {
            method: "POST",
            headers: { "X-CSRFToken": getCookie("csrftoken") || "" }
        }, "Unable to delete comment.");
    }

    function createCommentOnServer(postId, content) {
        var endpoint = buildPostActionEndpoint(postId, "comments/create/");
        var body = new FormData();
        body.append("content", String(content || ""));

        return requestJson(endpoint, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            },
            body: body
        }, "Unable to post comment.");
    }

    function createReplyOnServer(postId, targetCommentId, content) {
        var endpoint = buildCommentActionEndpoint(postId, targetCommentId, "reply/");
        var body = new FormData();
        body.append("content", String(content || ""));

        return requestJson(endpoint, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken") || ""
            },
            body: body
        }, "Unable to post reply.");
    }

    tabs.forEach(function (tab, index) {
        tab.addEventListener("click", function () {
            setActiveTab(tab.getAttribute("data-community-tab"), false);
        });

        tab.addEventListener("keydown", function (event) {
            var nextIndex = index;
            if (event.key === "ArrowRight") {
                nextIndex = (index + 1) % tabs.length;
            } else if (event.key === "ArrowLeft") {
                nextIndex = (index - 1 + tabs.length) % tabs.length;
            } else if (event.key === "Home") {
                nextIndex = 0;
            } else if (event.key === "End") {
                nextIndex = tabs.length - 1;
            } else {
                return;
            }

            event.preventDefault();
            setActiveTab(tabs[nextIndex].getAttribute("data-community-tab"), true);
        });
    });

    widgetToggles.forEach(function (toggle) {
        toggle.addEventListener("click", function () {
            var name = toggle.getAttribute("data-widget-toggle");
            var card = widgetCardByName(name);
            if (!card) {
                return;
            }

            var isMobile = window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
            var nextExpanded = isMobile ? !widgetsExpanded : !card.classList.contains("is-expanded");

            setWidgetExpanded(name, nextExpanded);
        });
    });

    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", function (event) {
            event.preventDefault();

            var attachmentsForPost = pendingAttachments.slice();
            var postType = composerPostType();

            var postText = String(chatInput.value || "").trim();
            if (!postText) {
                setStatus("Please write a short message first.");
                chatInput.focus();
                return;
            }

            createPostOnServer(postText, postType, attachmentsForPost).then(function (result) {
                var incoming = result && result.post ? normalizeIncomingPost(result.post) : null;
                if (incoming) {
                    state.posts.unshift(incoming);
                    state.postsOffset = Math.max(0, Number(state.postsOffset) || 0) + 1;
                    setActiveTab("all", false);
                } else {
                    createPost(postText, postType, attachmentsForPost);
                }

                chatInput.value = "";
                setStatus("Posted to the community feed.");
                chatInput.focus();

                clearPendingAttachments();
                setAttachmentCardOpen(false);
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to publish post.");
            });
        });
    }

    if (announcementToggleButton) {
        announcementToggleButton.addEventListener("click", function () {
            toggleComposerAnnouncementMode();
            if (chatInput) {
                chatInput.focus();
            }
        });
    }

    if (chatPlusButton) {
        chatPlusButton.addEventListener("click", function () {
            var shouldOpen = !attachmentCard || attachmentCard.hasAttribute("hidden");
            setAttachmentCardOpen(shouldOpen);

            setStatus(shouldOpen ? "Select image or file to attach." : "");
            if (shouldOpen && attachImagesButton) {
                attachImagesButton.focus();
            } else if (chatInput) {
                chatInput.focus();
            }
        });
    }

    if (attachImagesButton && attachmentImagesInput) {
        attachImagesButton.addEventListener("click", function () {
            attachmentImagesInput.click();
        });
    }

    if (attachFilesButton && attachmentFilesInput) {
        attachFilesButton.addEventListener("click", function () {
            attachmentFilesInput.click();
        });
    }

    if (attachmentImagesInput) {
        attachmentImagesInput.addEventListener("change", function () {
            addPendingAttachments(attachmentImagesInput.files);
            clearNativeFileInput(attachmentImagesInput);
        });
    }

    if (attachmentFilesInput) {
        attachmentFilesInput.addEventListener("change", function () {
            addPendingAttachments(attachmentFilesInput.files);
            clearNativeFileInput(attachmentFilesInput);
        });
    }

    if (selectedLabelsHost) {
        selectedLabelsHost.addEventListener("click", function (event) {
            var removeButton = event.target.closest("[data-remove-chat-attachment]");
            if (!removeButton) {
                return;
            }

            var attachmentId = removeButton.getAttribute("data-remove-chat-attachment");
            pendingAttachments = pendingAttachments.filter(function (attachment) {
                var keep = attachment.id !== attachmentId;
                if (!keep) {
                    revokePreviewUrl(attachment.previewUrl);
                }
                return keep;
            });

            renderSelectedAttachmentLabels();
            setStatus(pendingAttachments.length ? "Attachment removed." : "No attachments selected.");
            if (chatInput) {
                chatInput.focus();
            }
        });
    }

    if (mediaViewer) {
        mediaViewer.addEventListener("click", function (event) {
            if (event.target.closest("[data-media-viewer-close]")) {
                closeMediaViewer();
            }
        });
    }

    if (mediaViewerPrev) {
        mediaViewerPrev.addEventListener("click", function (event) {
            event.stopPropagation();
            moveMediaViewer(-1);
        });
    }

    if (mediaViewerNext) {
        mediaViewerNext.addEventListener("click", function (event) {
            event.stopPropagation();
            moveMediaViewer(1);
        });
    }

    document.addEventListener("click", function (event) {
        if (!attachmentCard || attachmentCard.hasAttribute("hidden")) {
            return;
        }

        var clickedInsideCard = attachmentCard.contains(event.target);
        var clickedPlusButton = chatPlusButton && chatPlusButton.contains(event.target);
        if (!clickedInsideCard && !clickedPlusButton) {
            setAttachmentCardOpen(false);
        }
    });

    document.addEventListener("click", function (event) {
        if (!reportModal) {
            return;
        }

        var reportReasonOption = event.target.closest("[data-report-reason]");
        if (reportReasonOption) {
            currentReportReason = String(reportReasonOption.getAttribute("data-report-reason") || "");
            setReportModalState();
            return;
        }

        if (event.target.closest("[data-report-modal-close]") || event.target.closest("[data-report-cancel]")) {
            closeReportModal();
            return;
        }

        var submitButton = event.target.closest("[data-report-submit]");
        if (submitButton) {
            var detailsInput = reportModal.querySelector("#community-report-details");
            var detailsValue = detailsInput ? String(detailsInput.value || "").trim() : "";
            if (!currentReportReason) {
                setStatus("Please select a reason before submitting your report.");
                return;
            }

            reportPostOnServer(currentReportPostId, currentReportReason, detailsValue).then(function (payload) {
                var reportedPost = state.posts.find(function (item) {
                    return String(item.id) === String(currentReportPostId);
                });
                if (reportedPost) {
                    reportedPost.reportedByViewer = true;
                }
                closeReportModal();
                setStatus(payload && payload.message ? String(payload.message) : "Report submitted.");
                renderFeed();
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to submit report.");
            });
            return;
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            if (reportModal && !reportModal.hasAttribute("hidden")) {
                closeReportModal();
                return;
            }
            setAttachmentCardOpen(false);
            closeMediaViewer();
            return;
        }

        if (mediaViewer && !mediaViewer.hasAttribute("hidden")) {
            if (event.key === "ArrowRight") {
                event.preventDefault();
                moveMediaViewer(1);
            } else if (event.key === "ArrowLeft") {
                event.preventDefault();
                moveMediaViewer(-1);
            }
        }
    });

    feedHost.addEventListener("scroll", function () {
        maybeLoadNextCommentBatchesOnScroll();
        maybeLoadNextPostsBatch();
    });

    if (dashboardScrollHost && dashboardScrollHost !== feedHost) {
        dashboardScrollHost.addEventListener("scroll", function () {
            maybeLoadNextCommentBatchesOnScroll();
            maybeLoadNextPostsBatch();
        });
    }

    window.addEventListener("resize", function () {
        maybeLoadNextCommentBatchesOnScroll();
        maybeLoadNextPostsBatch();
    });

    feedHost.addEventListener("click", function (event) {
        var manageCommentButton = event.target.closest("[data-comment-edit-open], [data-comment-edit-cancel], [data-comment-delete-open], [data-comment-delete-cancel], [data-comment-delete-confirm]");
        if (manageCommentButton) {
            var managePostCard = manageCommentButton.closest("[data-post-id]");
            var managePostId = managePostCard ? String(managePostCard.getAttribute("data-post-id") || "") : "";
            var managePost = state.posts.find(function (item) { return String(item.id) === managePostId; });
            var manageCommentId = String(
                manageCommentButton.getAttribute("data-comment-edit-open")
                || manageCommentButton.getAttribute("data-comment-edit-cancel")
                || manageCommentButton.getAttribute("data-comment-delete-open")
                || manageCommentButton.getAttribute("data-comment-delete-cancel")
                || manageCommentButton.getAttribute("data-comment-delete-confirm")
                || ""
            );
            var manageTarget = managePost && findCommentOrReplyById(managePost, manageCommentId);
            if (!manageTarget || !manageTarget.item) return;

            if (manageCommentButton.hasAttribute("data-comment-edit-open")) {
                manageTarget.item.isEditing = true;
                manageTarget.item.isConfirmingDelete = false;
                renderFeed();
                var editField = feedHost.querySelector('[data-comment-edit-id="' + manageCommentId + '"] textarea');
                if (editField) {
                    editField.focus();
                    editField.setSelectionRange(editField.value.length, editField.value.length);
                }
                return;
            }
            if (manageCommentButton.hasAttribute("data-comment-edit-cancel")) {
                manageTarget.item.isEditing = false;
                renderFeed();
                return;
            }
            if (manageCommentButton.hasAttribute("data-comment-delete-open")) {
                manageTarget.item.isConfirmingDelete = true;
                manageTarget.item.isEditing = false;
                renderFeed();
                return;
            }
            if (manageCommentButton.hasAttribute("data-comment-delete-cancel")) {
                manageTarget.item.isConfirmingDelete = false;
                renderFeed();
                return;
            }

            deleteCommunityCommentOnServer(managePostId, manageCommentId).then(function (payload) {
                var targetId = manageCommentId;
                var remainingComments = commentsFor(managePost).filter(function (rootComment) {
                    if (String(rootComment.id) === targetId) return false;
                    rootComment.replies = (Array.isArray(rootComment.replies) ? rootComment.replies : []).filter(function (reply) {
                        return String(reply.id) !== targetId;
                    });
                    return true;
                });
                managePost.commentsList = remainingComments;
                var count = Number(payload && payload.commentCount);
                managePost.commentCount = isFinite(count) && count >= 0 ? Math.floor(count) : Math.max(0, Number(managePost.commentCount) - 1);
                if (String(managePost.replyingToCommentId || "") === targetId) managePost.replyingToCommentId = null;
                renderFeed();
                setStatus(payload && payload.message ? String(payload.message) : "Comment deleted.");
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to delete comment.");
            });
            return;
        }

        var commentLikeButton = event.target.closest("[data-comment-like-toggle]");
        if (commentLikeButton) {
            var likePostCard = commentLikeButton.closest("[data-post-id]");
            if (!likePostCard) {
                return;
            }

            var likePostId = likePostCard.getAttribute("data-post-id");
            var likePost = state.posts.find(function (item) {
                return item.id === likePostId;
            });
            if (!likePost) {
                return;
            }

            var likeCommentId = String(commentLikeButton.getAttribute("data-comment-like-toggle") || "");
            var likeTarget = findCommentOrReplyById(likePost, likeCommentId);
            if (!likeTarget || !likeTarget.item) {
                return;
            }

            toggleCommentLikeOnServer(likePostId, likeCommentId).then(function (payload) {
                likeTarget.item.liked = !!(payload && payload.liked);
                likeTarget.item.likes = Math.max(0, Number(payload && payload.likes) || 0);
                openPostMenuId = null;
                renderFeed();
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to update comment like.");
            });
            return;
        }

        var replyToggleButton = event.target.closest("[data-comment-reply-toggle]");
        if (replyToggleButton) {
            var replyPostCard = replyToggleButton.closest("[data-post-id]");
            if (!replyPostCard) {
                return;
            }

            var replyPostId = replyPostCard.getAttribute("data-post-id");
            var replyPost = state.posts.find(function (item) {
                return item.id === replyPostId;
            });
            if (!replyPost) {
                return;
            }

            var targetCommentId = String(replyToggleButton.getAttribute("data-comment-reply-toggle") || "");
            replyPost.replyingToCommentId = replyPost.replyingToCommentId === targetCommentId ? null : targetCommentId;
            openPostMenuId = null;
            renderFeed();
            return;
        }

        var menuToggleButton = event.target.closest("[data-post-menu-toggle]");
        if (menuToggleButton) {
            var menuPostId = menuToggleButton.getAttribute("data-post-menu-toggle");
            openPostMenuId = openPostMenuId === menuPostId ? null : menuPostId;
            renderFeed();
            return;
        }

        var menuActionButton = event.target.closest("[data-post-menu-action]");
        if (menuActionButton) {
            var menuPostCard = menuActionButton.closest("[data-post-id]");
            if (!menuPostCard) {
                return;
            }

            var menuActionPostId = menuPostCard.getAttribute("data-post-id");
            var menuActionPost = state.posts.find(function (item) {
                return item.id === menuActionPostId;
            });
            if (!menuActionPost) {
                return;
            }

            var menuActionType = menuActionButton.getAttribute("data-post-menu-action");
            if (menuActionType === "report-post") {
                openReportModal(menuActionPostId);
            } else if (menuActionType === "delete-post") {
                function deleteSelectedPost() {
                    deletePostOnServer(menuActionPostId).then(function (payload) {
                        state.posts = state.posts.filter(function (item) {
                            return item.id !== menuActionPostId;
                        });
                        setStatus(payload && payload.message ? String(payload.message) : "Post deleted.");
                        openPostMenuId = null;
                        renderFeed();
                    }).catch(function (error) {
                        setStatus(error && error.message ? error.message : "Unable to delete post.");
                    });
                }

                var deleteConfirmEvent = new CustomEvent("community-post-delete-confirm", {
                    cancelable: true,
                    detail: {
                        post: menuActionPost,
                        trigger: menuActionButton,
                        confirm: deleteSelectedPost
                    }
                });
                document.dispatchEvent(deleteConfirmEvent);
                if (deleteConfirmEvent.defaultPrevented) {
                    return;
                }
                if (!window.confirm("Delete this post? This can't be undone.")) {
                    return;
                }

                deleteSelectedPost();
                return;
            } else if (menuActionType === "edit-post") {
                menuActionPost.isEditing = true;
                menuActionPost.editDraft = String(menuActionPost.content || "");
                menuActionPost.editOriginalAttachments = editAttachmentItems(menuActionPost);
                menuActionPost.editAttachments = menuActionPost.editOriginalAttachments.map(function (item) { return Object.assign({}, item); });
                menuActionPost.editNewAttachments = [];
                openPostMenuId = null;
                renderFeed();
                return;
            }

            openPostMenuId = null;
            renderFeed();
            return;
        }

        var postEditSaveButton = event.target.closest("[data-post-edit-save]");
        if (postEditSaveButton) {
            var editPostId = postEditSaveButton.getAttribute("data-post-edit-save");
            var editPost = state.posts.find(function (item) {
                return item.id === editPostId;
            });
            if (!editPost) {
                return;
            }

            var editInput = feedHost.querySelector('textarea[data-post-edit-input="' + editPostId + '"]');
            var updatedText = editInput ? String(editInput.value || "").trim() : "";
            if (!updatedText) {
                setStatus("Post content cannot be empty.");
                if (editInput) {
                    editInput.focus();
                }
                return;
            }

            updatePostOnServer(editPostId, updatedText, editPost).then(function (payload) {
                var incoming = payload && payload.post ? normalizeIncomingPost(payload.post) : null;
                if (incoming) {
                    Object.keys(incoming).forEach(function (key) {
                        editPost[key] = incoming[key];
                    });
                } else {
                    editPost.content = updatedText;
                }
                editPost.isEditing = false;
                editPost.editDraft = undefined;
                editPost.editOriginalAttachments = undefined;
                editPost.editAttachments = undefined;
                editPost.editNewAttachments = undefined;
                setStatus(payload && payload.message ? String(payload.message) : "Post updated.");
                renderFeed();
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to update post.");
            });
            return;
        }

        var editAttachmentMenuButton = event.target.closest("[data-edit-attachment-menu]");
        if (editAttachmentMenuButton) {
            var menuPostId = editAttachmentMenuButton.getAttribute("data-edit-attachment-menu");
            var picker = feedHost.querySelector('[data-edit-attachment-picker="' + menuPostId + '"]');
            if (picker) picker.hidden = !picker.hidden;
            return;
        }

        var editAttachmentButton = event.target.closest("[data-edit-attach-images], [data-edit-attach-files]");
        if (editAttachmentButton) {
            var attachPostId = editAttachmentButton.getAttribute("data-edit-attach-images") || editAttachmentButton.getAttribute("data-edit-attach-files");
            var kind = editAttachmentButton.hasAttribute("data-edit-attach-images") ? "image" : "file";
            var input = feedHost.querySelector('input[data-edit-attachment-input="' + attachPostId + '"][data-edit-attachment-kind="' + kind + '"]');
            if (input) input.click();
            return;
        }

        var editRemoveButton = event.target.closest("[data-edit-remove-attachment]");
        if (editRemoveButton) {
            var removePostId = editRemoveButton.closest("[data-post-edit-attachments]").getAttribute("data-post-edit-attachments");
            var removePost = state.posts.find(function (item) { return String(item.id) === String(removePostId); });
            if (removePost) {
                var removeId = editRemoveButton.getAttribute("data-edit-remove-attachment");
                (removePost.editNewAttachments || []).forEach(function (item) {
                    if (String(item.tempId) === String(removeId) && item.previewUrl && window.URL) {
                        window.URL.revokeObjectURL(item.previewUrl);
                    }
                });
                removePost.editAttachments = (removePost.editAttachments || []).filter(function (item) { return String(item.id || item.tempId) !== String(removeId); });
                removePost.editNewAttachments = (removePost.editNewAttachments || []).filter(function (item) { return String(item.tempId) !== String(removeId); });
                renderFeed();
            }
            return;
        }

        var postEditCancelButton = event.target.closest("[data-post-edit-cancel]");
        if (postEditCancelButton) {
            var cancelPostId = postEditCancelButton.getAttribute("data-post-edit-cancel");
            var cancelPost = state.posts.find(function (item) {
                return item.id === cancelPostId;
            });
            if (!cancelPost) {
                return;
            }

            cancelPost.isEditing = false;
            cancelPost.editDraft = undefined;
            (cancelPost.editNewAttachments || []).forEach(function (item) { if (item.previewUrl && window.URL) window.URL.revokeObjectURL(item.previewUrl); });
            cancelPost.editOriginalAttachments = undefined;
            cancelPost.editAttachments = undefined;
            cancelPost.editNewAttachments = undefined;
            openPostMenuId = null;
            renderFeed();
            return;
        }

        var carouselNavButton = event.target.closest("[data-post-carousel-nav]");
        if (carouselNavButton) {
            var carouselPostCard = carouselNavButton.closest("[data-post-id]");
            if (!carouselPostCard) {
                return;
            }

            var carouselPostId = carouselPostCard.getAttribute("data-post-id");
            var carouselPost = state.posts.find(function (item) {
                return item.id === carouselPostId;
            });
            if (!carouselPost) {
                return;
            }

            var postImages = imageAttachmentsFor(carouselPost);
            if (postImages.length < 2) {
                return;
            }

            var currentIndex = Number(carouselPost.carouselIndex);
            if (!isFinite(currentIndex) || currentIndex < 0 || currentIndex >= postImages.length) {
                currentIndex = 0;
            }

            var direction = carouselNavButton.getAttribute("data-post-carousel-nav") === "next" ? 1 : -1;
            carouselPost.carouselIndex = (currentIndex + direction + postImages.length) % postImages.length;
            openPostMenuId = null;
            renderFeed();
            return;
        }

        var mediaButton = event.target.closest("[data-post-media-view]");
        if (mediaButton) {
            var mediaPostId = mediaButton.getAttribute("data-post-media-view");
            var mediaPost = state.posts.find(function (item) {
                return item.id === mediaPostId;
            });

            if (mediaPost) {
                var mediaIndex = Number(mediaButton.getAttribute("data-post-media-index"));
                openMediaViewer(imageAttachmentsFor(mediaPost), isFinite(mediaIndex) ? mediaIndex : 0);
            }

            return;
        }

        var actionButton = event.target.closest("[data-post-action]");
        var postCard = event.target.closest("[data-post-id]");
        if (!actionButton || !postCard) {
            return;
        }

        var postId = postCard.getAttribute("data-post-id");
        var post = state.posts.find(function (item) {
            return item.id === postId;
        });
        if (!post) {
            return;
        }

        var actionType = actionButton.getAttribute("data-post-action");
        if (actionType === "like") {
            togglePostLikeOnServer(postId).then(function (payload) {
                post.liked = !!(payload && payload.liked);
                post.likes = Math.max(0, Number(payload && payload.likes) || 0);
                openPostMenuId = null;
                renderFeed();
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to update post like.");
            });
            return;
        }

        if (actionType === "comment") {
            post.showComments = !post.showComments;
            post.replyingToCommentId = null;
            openPostMenuId = null;

            if (!post.showComments) {
                renderFeed();
                setStatus("Comments hidden.");
                return;
            }

            ensurePostCommentState(post);
            renderFeed();
            setStatus("Comments shown.");

            if (!post.commentsLoaded && post.commentCount > 0) {
                loadMoreCommentsForPost(post, true);
            }
        }
    });

    feedHost.addEventListener("change", function (event) {
        var input = event.target.closest("input[data-edit-attachment-input]");
        if (!input || !input.files || !input.files.length) return;
        var postId = input.getAttribute("data-edit-attachment-input");
        var post = state.posts.find(function (item) { return String(item.id) === String(postId); });
        if (!post) return;
        post.editNewAttachments = post.editNewAttachments || [];
        post.editAttachments = post.editAttachments || [];
        Array.prototype.forEach.call(input.files, function (file) {
            var previewUrl = file.type && file.type.indexOf("image/") === 0 && window.URL ? window.URL.createObjectURL(file) : "";
            var item = { tempId: "edit-attachment-" + Date.now() + "-" + Math.random().toString(36).slice(2), name: file.name || "Attachment", file: file, isNew: true, isImage: !!previewUrl, previewUrl: previewUrl };
            post.editNewAttachments.push(item);
            post.editAttachments.push(item);
        });
        input.value = "";
        renderFeed();
    });

    feedHost.addEventListener("submit", function (event) {
        var editForm = event.target.closest("[data-comment-edit-form]");
        if (editForm) {
            event.preventDefault();
            var editPostCard = editForm.closest("[data-post-id]");
            var editPostId = editPostCard ? String(editPostCard.getAttribute("data-post-id") || "") : "";
            var editPost = state.posts.find(function (item) { return String(item.id) === editPostId; });
            var editCommentId = String(editForm.getAttribute("data-comment-edit-id") || "");
            var editTarget = editPost && findCommentOrReplyById(editPost, editCommentId);
            var editValue = String((editForm.querySelector('[name="edited_comment"]') || {}).value || "").trim();
            if (!editTarget || !editTarget.item) return;
            if (!editValue) {
                setStatus("Write a comment before saving.");
                editForm.querySelector("textarea").focus();
                return;
            }
            updateCommunityCommentOnServer(editPostId, editCommentId, editValue).then(function (payload) {
                editTarget.item.text = String(payload && payload.text || editValue);
                editTarget.item.isEditing = false;
                editTarget.item.isConfirmingDelete = false;
                renderFeed();
                setStatus("Comment updated.");
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to edit comment.");
            });
            return;
        }

        var commentForm = event.target.closest("[data-comment-form]");
        if (!commentForm) {
            return;
        }

        event.preventDefault();

        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        var postId = postCard.getAttribute("data-post-id");
        var post = state.posts.find(function (item) {
            return item.id === postId;
        });
        if (!post) {
            return;
        }

        var commentInput = commentForm.querySelector('input[name="comment"]');
        var commentText = String(commentInput && commentInput.value ? commentInput.value : "").trim();
        if (!commentText) {
            setStatus("Write a comment before posting.");
            if (commentInput) {
                commentInput.focus();
            }
            return;
        }

        var replyToCommentId = String(post.replyingToCommentId || "");
        if (replyToCommentId) {
            var replyTarget = findCommentOrReplyById(post, replyToCommentId);
            if (!replyTarget || !replyTarget.parentComment) {
                setStatus("Comment no longer available.");
                return;
            }

            createReplyOnServer(postId, replyToCommentId, commentText).then(function (payload) {
                var reply = payload && payload.reply ? normalizeComment(payload.reply) : null;
                if (!reply) {
                    throw new Error("Unable to post reply.");
                }

                var rootCommentId = payload && payload.rootCommentId ? String(payload.rootCommentId) : "";
                var rootComment = rootCommentId ? findCommentById(post, rootCommentId) : null;
                if (!rootComment) {
                    rootComment = replyTarget.parentComment;
                }

                if (!Array.isArray(rootComment.replies)) {
                    rootComment.replies = [];
                }

                rootComment.replies.push(reply);

                var replyCount = Number(payload && payload.commentCount);
                if (isFinite(replyCount) && replyCount >= 0) {
                    post.commentCount = Math.floor(replyCount);
                } else {
                    post.commentCount = Math.max(0, Number(post.commentCount) || 0) + 1;
                }

                post.showComments = true;
                post.replyingToCommentId = null;
                openPostMenuId = null;
                renderFeed();
                setStatus("Reply posted.");

                var refreshedReplyInput = feedHost.querySelector('[data-post-id="' + postId + '"] input[name="comment"]');
                if (refreshedReplyInput) {
                    refreshedReplyInput.focus();
                }
            }).catch(function (error) {
                setStatus(error && error.message ? error.message : "Unable to post reply.");
            });
            return;
        }

        createCommentOnServer(postId, commentText).then(function (payload) {
            var comment = payload && payload.comment ? normalizeComment(payload.comment) : null;
            if (!comment) {
                throw new Error("Unable to post comment.");
            }

            ensurePostCommentState(post);
            commentsFor(post).push(comment);

            var createdCount = Number(payload && payload.commentCount);
            if (isFinite(createdCount) && createdCount >= 0) {
                post.commentCount = Math.floor(createdCount);
            } else {
                post.commentCount = Math.max(0, Number(post.commentCount) || 0) + 1;
            }

            post.commentsLoaded = true;
            post.commentsOffset = Math.max(0, Number(post.commentsOffset) || 0) + 1;

            post.showComments = true;
            post.replyingToCommentId = null;
            openPostMenuId = null;
            renderFeed();
            setStatus("Comment posted.");

            var refreshedCommentInput = feedHost.querySelector('[data-post-id="' + postId + '"] input[name="comment"]');
            if (refreshedCommentInput) {
                refreshedCommentInput.focus();
            }
        }).catch(function (error) {
            setStatus(error && error.message ? error.message : "Unable to post comment.");
        });
    });

    document.addEventListener("click", function (event) {
        if (!openPostMenuId) {
            return;
        }

        if (event.target.closest(".ch-post-menu")) {
            return;
        }

        openPostMenuId = null;
        renderFeed();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape" || !openPostMenuId) {
            return;
        }

        openPostMenuId = null;
        renderFeed();
    });

    renderList(announcementsHost, state.announcements);
    renderList(eventsHost, state.events);
    renderList(highlightsHost, state.highlights);
    updateWidgetBadges();
    syncMobileWidgetPosition();
    window.addEventListener("resize", syncMobileWidgetPosition);
    if (widgetSide) {
        widgetSide.addEventListener("scroll", updateWidgetCarouselIndicator, { passive: true });
    }
    if (widgetIndicators) {
        widgetIndicators.addEventListener("click", function (event) {
            var indicator = event.target.closest("[data-widget-indicator]");
            if (!indicator || !widgetSide) {
                return;
            }

            var index = Number(indicator.getAttribute("data-widget-indicator"));
            var card = widgetSide.querySelectorAll(".ch-widget-card")[index];
            if (card) {
                widgetSide.scrollTo({ left: card.offsetLeft, behavior: "smooth" });
            }
        });
    }
    updateWidgetCarouselIndicator();
    syncComposerIdentity();
    setComposerMode(false);
    renderSelectedAttachmentLabels();

    setActiveTab("all", false);
    loadPostsFromServer(true);
    startCommentPolling();
    startRelativeTimePolling();
    refreshIcons();
})();

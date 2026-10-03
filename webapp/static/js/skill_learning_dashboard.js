(function initSkillLearningDashboard() {
    "use strict";

    var root = document.getElementById("skill-learning");
    var payloadNode = document.getElementById("sl-topic-data");
    if (!root || !payloadNode || root.dataset.slHubBound === "true") {
        return;
    }
    root.dataset.slHubBound = "true";

    var searchInput = document.getElementById("sl-topic-search");
    var searchWrapper = document.getElementById("sl-search");
    var searchToggle = document.getElementById("sl-search-toggle");
    var filterButtons = Array.prototype.slice.call(root.querySelectorAll("[data-sl-filter]"));
    var grid = document.getElementById("sl-topic-grid");
    var listView = document.getElementById("sl-topic-list-view");
    var detailView = document.getElementById("sl-topic-view");
    var recommendedList = document.getElementById("sl-recommended-list");
    var popularList = document.getElementById("sl-popular-list");
    var previewFrame = document.getElementById("sl-material-preview-frame");
    var topicModal = document.getElementById("sl-topic-modal");
    var topicForm = document.getElementById("sl-topic-form");
    var topicModalTitle = document.getElementById("sl-topic-modal-title");
    var topicSubmitBtn = document.getElementById("sl-topic-submit-btn");
    var topicIdInput = document.getElementById("sl-topic-id-input");
    var topicTitleInput = document.getElementById("sl-topic-title-input");
    var topicBadgeInput = document.getElementById("sl-topic-badge-input");
    var topicDescInput = document.getElementById("sl-topic-desc-input");
    var topicCoverInput = document.getElementById("sl-topic-cover-input");
    var topicCoverUrlInput = document.getElementById("sl-topic-cover-url-input");
    var materialModal = document.getElementById("sl-material-modal");
    var materialForm = document.getElementById("sl-material-form");
    var materialModalTitle = document.getElementById("sl-material-modal-title");
    var materialSubmitBtn = document.getElementById("sl-material-submit-btn");
    var materialIdInput = document.getElementById("sl-material-id-input");
    var materialTopicIdInput = document.getElementById("sl-material-topic-id-input");
    var materialTypeInput = document.getElementById("sl-material-type-input");
    var materialTitleInput = document.getElementById("sl-material-title-input");
    var materialDescInput = document.getElementById("sl-material-desc-input");
    var materialUploadInput = document.getElementById("sl-material-upload-input");
    var materialLinkInput = document.getElementById("sl-material-link-input");
    var deleteModal = document.getElementById("sl-delete-confirm-modal");
    var deleteTitle = document.getElementById("sl-delete-confirm-title");
    var deleteMessage = document.getElementById("sl-delete-confirm-message");
    var deleteConfirmBtn = document.getElementById("sl-delete-confirm-btn");
    var apiBase = (root.dataset.apiBase || "").replace(/\/$/, "");
    var userRole = root.dataset.userRole || "user";
    var payload = {};

    try {
        payload = JSON.parse(payloadNode.textContent || "{}");
    } catch (error) {
        payload = { topics: [] };
    }

    var state = {
        topicSearchQuery: "",
        topicFilter: "all",
        currentTopicId: null,
        currentMaterialId: null,
        recentlyViewed: [],
        topics: Array.isArray(payload.topics) ? payload.topics.slice() : [],
        pendingDelete: null,
        uploadPreviewUrl: ""
    };

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>\"']/g, function (char) {
            if (char === "&") return "&amp;";
            if (char === "<") return "&lt;";
            if (char === ">") return "&gt;";
            if (char === '"') return "&quot;";
            return "&#39;";
        });
    }

    function normalizeToken(value) {
        return String(value || "")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .trim();
    }

    function getCookie(name) {
        var cookieValue = null;
        if (!document.cookie) {
            return cookieValue;
        }
        document.cookie.split(";").some(function (cookie) {
            var trimmed = cookie.trim();
            if (trimmed.indexOf(name + "=") === 0) {
                cookieValue = decodeURIComponent(trimmed.substring(name.length + 1));
                return true;
            }
            return false;
        });
        return cookieValue;
    }

    function apiUrl(path) {
        return apiBase + path;
    }

    function materialTypeLabel(type) {
        if (type === "video") return "Video";
        if (type === "reference_guide") return "Reference Guide";
        return "Document";
    }

    function materialIcon(type) {
        if (type === "video") return "play-circle";
        if (type === "reference_guide") return "book-open";
        return "file-text";
    }

    function isVolunteerView() {
        return userRole === "volunteer";
    }

    function getCurrentTopic() {
        return state.topics.find(function (topic) {
            return topic.id === state.currentTopicId;
        }) || null;
    }

    function getTopicById(topicId) {
        return state.topics.find(function (topic) {
            return topic.id === topicId;
        }) || null;
    }

    function renderCompletionSummary(topic) {
        var totalMaterials = Number(topic && topic.totalMaterials ? topic.totalMaterials : 0);
        var completedMaterials = Number(topic && topic.completedMaterials ? topic.completedMaterials : 0);
        var percentComplete = Number(topic && topic.progressPercent ? topic.progressPercent : 0);
        var materialCount = Array.isArray(topic && topic.materials) ? topic.materials.length : 0;

        if (isVolunteerView()) {
            return '<span>' + escapeHtml(String(materialCount)) + ' material' + (materialCount === 1 ? '' : 's') + '</span>';
        }

        return [
            '<div class="sl-progress-track"><span class="sl-progress-value" style="width: ' + escapeHtml(String(Math.max(0, Math.min(100, percentComplete)))) + '%"></span></div>',
            '<span>' + escapeHtml(String(completedMaterials)) + ' of ' + escapeHtml(String(totalMaterials)) + ' completed</span>'
        ].join("");
    }

    function getMaterialById(topic, materialId) {
        if (!topic || !Array.isArray(topic.materials)) {
            return null;
        }
        return topic.materials.find(function (material) {
            return material.id === materialId;
        }) || null;
    }

    function clearMaterialPreview() {
        if (!previewFrame) {
            return;
        }
        previewFrame.className = "sl-preview-frame";
        previewFrame.innerHTML = "";
    }

    function renderMaterialPreview(material, topic) {
        if (!previewFrame) {
            return;
        }
        if (!material) {
            clearMaterialPreview();
            return;
        }

        var sourceUrl = material.sourceUrl || material.externalUrl || material.fileUrl || "";
        var previewKind = material.materialType === "video" ? "video" : "document";
        var frameClass = "sl-preview-frame " + (previewKind === "video" ? "is-video" : "is-document");
        var markup = "";

        if (previewKind === "video") {
            if (sourceUrl && !/drive\.google\.com/i.test(sourceUrl)) {
                markup = '<video class="sl-preview-media" controls playsinline src="' + escapeHtml(sourceUrl) + '"></video>';
            } else if (sourceUrl) {
                markup = '<iframe src="' + escapeHtml(sourceUrl) + '" title="' + escapeHtml(material.title || "Video") + ' preview" frameborder="0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
            } else {
                markup = '<div class="sl-preview-doc" aria-hidden="true"><i data-lucide="play-circle"></i></div>';
            }
        } else if (sourceUrl) {
            if (/\.pdf($|\?)/i.test(sourceUrl) || /drive\.google\.com/i.test(sourceUrl) || /preview/i.test(sourceUrl)) {
                markup = '<iframe src="' + escapeHtml(sourceUrl) + '" title="' + escapeHtml(material.title || "Document") + ' preview" frameborder="0" allowfullscreen></iframe>';
            } else {
                markup = '<div class="sl-preview-doc"><a href="' + escapeHtml(sourceUrl) + '" target="_blank" rel="noopener">Open material</a></div>';
            }
        } else if (topic && topic.coverImageUrl) {
            markup = '<img class="sl-preview-media" src="' + escapeHtml(topic.coverImageUrl) + '" alt="' + escapeHtml((material.title || "Material") + ' preview') + '" loading="lazy" />';
        } else {
            markup = '<div class="sl-preview-doc" aria-hidden="true"><i data-lucide="file-text"></i></div>';
        }

        previewFrame.className = frameClass;
        previewFrame.innerHTML = markup;

        var video = previewFrame.querySelector("video");
        if (video && userRole !== "volunteer") {
            video.addEventListener("ended", function () {
                recordEngagement("complete", material.id);
            }, { once: true });
        }

        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function getSelectedFilterTags(form) {
        var hiddenInput = form.querySelector('#sl-topic-filter-tags-hidden');
        if (hiddenInput && hiddenInput.value) {
            return hiddenInput.value.split(',').filter(function(tag) { return tag.trim(); });
        }
        return [];
    }

    function applyTopicFormValues(topic) {
        if (!topicForm) {
            return;
        }

        topicIdInput.value = topic ? topic.id : "";
        topicTitleInput.value = topic ? (topic.title || "") : "";
        topicBadgeInput.value = topic ? (topic.badgeLabel || "") : "";
        topicDescInput.value = topic ? (topic.description || "") : "";
        topicCoverUrlInput.value = topic ? (topic.coverImageUrl || "") : "";

        // Update pill buttons
        var filterTagsContainer = document.getElementById("sl-topic-filter-tags");
        if (filterTagsContainer) {
            var pills = filterTagsContainer.querySelectorAll(".sl-tag-pill");
            var selectedTags = topic && Array.isArray(topic.filterTags) ? topic.filterTags : [];
            
            pills.forEach(function (pill) {
                var tagValue = pill.getAttribute("data-tag-value");
                var isSelected = selectedTags.indexOf(tagValue) >= 0;
                pill.classList.toggle("is-active", isSelected);
                pill.setAttribute("aria-pressed", isSelected ? "true" : "false");
            });
            
            // Update hidden input
            var hiddenInput = topicForm.querySelector('#sl-topic-filter-tags-hidden');
            if (hiddenInput) {
                hiddenInput.value = selectedTags.join(',');
            }
        }
    }

    function applyMaterialFormValues(topic, material) {
        if (!materialForm) {
            return;
        }

        materialIdInput.value = material ? material.id : "";
        materialTopicIdInput.value = topic ? topic.id : "";
        materialTypeInput.value = material ? (material.materialType || "document") : "document";
        materialTitleInput.value = material ? (material.title || "") : "";
        materialDescInput.value = material ? (material.description || "") : "";
        materialLinkInput.value = material ? (material.externalUrl || material.sourceUrl || "") : "";
        materialUploadInput.value = "";
    }

    function openModal(modal) {
        if (!modal) return;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
    }

    function setDetailMode(isDetail) {
        root.classList.toggle("is-detail", !!isDetail);
        if (listView) listView.hidden = !!isDetail;
        if (detailView) detailView.hidden = !isDetail;
    }

    function filteredTopics() {
        var query = normalizeToken(state.topicSearchQuery || "");
        var filter = normalizeToken(state.topicFilter || "all");
        return state.topics.filter(function (topic) {
            var tags = Array.isArray(topic.filterTags) ? topic.filterTags : [];
            var matchesFilter = true;
            if (filter !== "all") {
                matchesFilter = tags.map(normalizeToken).indexOf(filter) >= 0;
            }
            var matchesSearch = !query || [topic.title, topic.description, topic.badgeLabel, tags.join(" ")].some(function (value) {
                return normalizeToken(value).indexOf(query) >= 0;
            });
            return matchesFilter && matchesSearch;
        });
    }

    function renderTopicCards() {
        if (!grid) {
            return;
        }

        var visibleTopics = filteredTopics();
        if (!visibleTopics.length) {
            grid.innerHTML = '<p class="sl-empty-state">No topics match your search or filter.</p>';
            return;
        }

        grid.innerHTML = visibleTopics.map(function (topic) {
            var actions = userRole === "volunteer" ? [
                '<div class="sl-topic-card-actions">',
                '<button type="button" class="sl-card-action-btn" data-sl-topic-edit="' + escapeHtml(topic.id) + '" aria-label="Edit ' + escapeHtml(topic.title) + '"><i data-lucide="pencil" aria-hidden="true"></i></button>',
                '<button type="button" class="sl-card-action-btn" data-sl-topic-delete="' + escapeHtml(topic.id) + '" aria-label="Delete ' + escapeHtml(topic.title) + '"><i data-lucide="trash-2" aria-hidden="true"></i></button>',
                '</div>'
            ].join("") : "";
            var imageUrl = topic.coverImageUrl || "";
            var title = topic.title || "Learning topic";
            var description = topic.description || "No description provided.";
            var badge = topic.badgeLabel || topic.primaryFilterTag || "Topic";
            var categoryTag = Array.isArray(topic.filterTags) ? (topic.filterTags[0] || "Community") : (topic.primaryFilterTag || "Community");
            var materialCount = Array.isArray(topic.materials) ? topic.materials.length : 0;
            var progressMarkup = renderCompletionSummary(topic);
            return [
                '<article class="sl-topic-card" data-sl-topic-card="' + escapeHtml(topic.id) + '" role="button" tabindex="0" aria-label="Open ' + escapeHtml(title) + '">',
                actions,
                '<div class="sl-topic-media">',
                '<img src="' + escapeHtml(imageUrl) + '" alt="' + escapeHtml(title) + ' cover" loading="lazy" />',
                '<span class="sl-topic-gradient" aria-hidden="true"></span>',
                '<span class="sl-topic-tag" data-sl-category="' + escapeHtml(categoryTag) + '">' + escapeHtml(badge) + '</span>',
                '</div>',
                '<div class="sl-topic-body">',
                '<h3 class="sl-topic-title">' + escapeHtml(title) + '</h3>',
                '<p class="sl-topic-desc">' + escapeHtml(description) + '</p>',
                '<div class="sl-progress" aria-label="' + escapeHtml(String(materialCount)) + (isVolunteerView() ? ' materials"' : ' topic progress"') + '>',
                progressMarkup,
                '</div>',
                '<span class="sl-topic-open">Open <i data-lucide="arrow-right" aria-hidden="true"></i></span>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function renderSidebar() {
        var recommended = state.topics.filter(function (topic) {
            return !!topic.isRecommended;
        }).slice(0, 3);
        var popular = state.topics.slice().sort(function (a, b) {
            return (b.popularityScore || 0) - (a.popularityScore || 0);
        }).slice(0, 3);

        if (recommendedList) {
            recommendedList.innerHTML = recommended.length ? recommended.map(function (topic) {
                return [
                    '<li>',
                    '<button type="button" class="sl-recommend-item" data-sl-topic-target="' + escapeHtml(topic.id) + '">',
                    '<img class="sl-recommend-thumb" src="' + escapeHtml(topic.coverImageUrl || "") + '" alt="" loading="lazy" />',
                    '<div>',
                    '<p class="sl-recommend-title">' + escapeHtml(topic.title || "Topic") + '</p>',
                    '<span class="sl-recommend-tag" data-sl-category="' + escapeHtml(topic.primaryFilterTag || "") + '">' + escapeHtml(topic.primaryFilterTag || "") + '</span>',
                    '</div>',
                    '</button>',
                    '</li>'
                ].join("");
            }).join("") : '<li class="sl-muted-text">No recommendations yet.</li>';
        }

        if (popularList) {
            popularList.innerHTML = popular.length ? popular.map(function (topic, idx) {
                return [
                    '<li>',
                    '<button type="button" class="sl-popular-item" data-sl-topic-target="' + escapeHtml(topic.id) + '">',
                    '<span class="sl-popular-thumb-wrap">',
                    '<img class="sl-recommend-thumb" src="' + escapeHtml(topic.coverImageUrl || "") + '" alt="" loading="lazy" />',
                    '</span>',
                    '<div>',
                    '<p class="sl-recommend-title">' + escapeHtml(topic.title || "Topic") + '</p>',
                    '<span class="sl-popular-rank">#' + escapeHtml(String(idx + 1)) + '</span>',
                    '</div>',
                    '</button>',
                    '</li>'
                ].join("");
            }).join("") : '<li class="sl-muted-text">No popular topics yet.</li>';
        }
    }

    function renderTopicView(topic) {
        var titleNode = document.getElementById("sl-topic-name");
        var descNode = document.getElementById("sl-topic-description");
        var host = document.getElementById("sl-materials-sections");
        var materials = Array.isArray(topic.materials) ? topic.materials : [];

        if (titleNode) {
            titleNode.textContent = topic.title || "Topic";
        }
        if (descNode) {
            descNode.textContent = topic.description || "No description provided.";
        }
        var progressNode = document.getElementById("sl-topic-progress");
        if (progressNode) {
            progressNode.innerHTML = renderCompletionSummary(topic);
        }

        if (!host) {
            return;
        }

        if (!materials.length) {
            host.innerHTML = '<p class="sl-empty-state">No materials available yet.</p>';
            clearMaterialPreview();
            return;
        }

        if (!state.currentMaterialId || !getMaterialById(topic, state.currentMaterialId)) {
            state.currentMaterialId = materials[0].id;
        }

        host.innerHTML = materials.map(function (material) {
            var isActive = material.id === state.currentMaterialId;
            var actions = userRole === "volunteer" ? [
                '<div class="sl-material-card-actions">',
                '<button type="button" class="sl-card-action-btn" data-sl-material-edit="' + escapeHtml(material.id) + '" aria-label="Edit ' + escapeHtml(material.title) + '"><i data-lucide="pencil" aria-hidden="true"></i></button>',
                '<button type="button" class="sl-card-action-btn" data-sl-material-delete="' + escapeHtml(material.id) + '" aria-label="Delete ' + escapeHtml(material.title) + '"><i data-lucide="trash-2" aria-hidden="true"></i></button>',
                '</div>'
            ].join("") : "";
            return [
                '<article class="sl-material-card' + (isActive ? ' is-active' : '') + '" data-sl-material-id="' + escapeHtml(material.id) + '" role="button" tabindex="0" aria-pressed="' + (isActive ? 'true' : 'false') + '">',
                actions,
                '<span class="sl-material-icon" aria-hidden="true"><i data-lucide="' + escapeHtml(materialIcon(material.materialType)) + '"></i></span>',
                '<div class="sl-material-content">',
                '<div class="sl-material-head">',
                '<h4 class="sl-material-title">' + escapeHtml(material.title || "Material") + '</h4>',
                '</div>',
                '<div class="sl-material-meta">',
                '<span class="sl-material-badge">' + escapeHtml(materialTypeLabel(material.materialType)) + '</span>',
                '</div>',
                material.description ? '<p class="sl-material-desc">' + escapeHtml(material.description) + '</p>' : '',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        var activeMaterial = getMaterialById(topic, state.currentMaterialId) || materials[0];
        renderMaterialPreview(activeMaterial, topic);

        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function setActiveMaterial(topic, materialId) {
        var material = getMaterialById(topic, materialId);
        if (!material) {
            return;
        }
        state.currentMaterialId = materialId;
        renderTopicView(topic);
    }

    function showTopicList() {
        state.currentTopicId = null;
        state.currentMaterialId = null;
        setDetailMode(false);
        clearMaterialPreview();
    }

    function openTopic(topicId) {
        var topic = getTopicById(topicId);
        if (!topic) {
            return;
        }
        state.currentTopicId = topicId;
        state.currentMaterialId = null;
        setDetailMode(true);
        renderTopicView(topic);
        updateRecentlyViewed(topicId);
        renderSidebar();
        recordEngagement("topic-open", topicId);
        if (userRole !== "volunteer" && topic.materials && topic.materials.length) {
            recordEngagement("view", topic.materials[0].id);
        }
    }

    function updateRecentlyViewed(topicId) {
        var index = state.recentlyViewed.indexOf(topicId);
        if (index >= 0) {
            state.recentlyViewed.splice(index, 1);
        }
        state.recentlyViewed.unshift(topicId);
        state.recentlyViewed = state.recentlyViewed.slice(0, 3);
    }

    function openDeepLink() {
        var params = new URLSearchParams(window.location.search || "");
        var topicParam = String(params.get("course") || params.get("topic") || "").trim();
        if (!topicParam) {
            return;
        }
        var normalizedParam = normalizeToken(topicParam);
        var match = state.topics.find(function (topic) {
            return normalizeToken(topic.id) === normalizedParam || normalizeToken(topic.title).indexOf(normalizedParam) >= 0;
        });
        if (match) {
            openTopic(match.id);
        }
    }

    function rerenderAfterMutation(nextTopic) {
        state.topics = state.topics.map(function (topic) {
            return topic.id === nextTopic.id ? nextTopic : topic;
        });
        if (!getTopicById(nextTopic.id)) {
            state.topics.push(nextTopic);
        }
        renderTopicCards();
        renderSidebar();
        if (state.currentTopicId === nextTopic.id) {
            renderTopicView(nextTopic);
        }
    }

    function removeTopicFromState(topicId) {
        state.topics = state.topics.filter(function (topic) {
            return topic.id !== topicId;
        });
        if (state.currentTopicId === topicId) {
            showTopicList();
        }
        renderTopicCards();
        renderSidebar();
    }

    function fetchJson(url, options) {
        var fetchOptions = options || {};
        fetchOptions.headers = fetchOptions.headers || {};
        fetchOptions.headers["X-CSRFToken"] = getCookie("csrftoken") || "";
        return fetch(url, fetchOptions).then(function (response) {
            return response.json().then(function (body) {
                if (!response.ok) {
                    var message = (body && (body.error || body.message)) || "Request failed.";
                    var error = new Error(message);
                    error.payload = body;
                    throw error;
                }
                return body;
            });
        });
    }

    function refreshActivity() {
        return fetchJson(apiUrl("/data/")).then(function (result) {
            if (!result || !Array.isArray(result.topics)) return;
            state.topics = result.topics;
            renderTopicCards();
            renderSidebar();
            var currentTopic = getCurrentTopic();
            if (currentTopic) renderTopicView(currentTopic);
        });
    }

    function recordEngagement(action, itemId) {
        var endpoint = action === "topic-open"
            ? apiUrl("/topics/" + encodeURIComponent(itemId) + "/open/")
            : apiUrl("/materials/" + encodeURIComponent(itemId) + "/engagement/");
        var body = new FormData();
        if (action !== "topic-open") body.append("action", action);
        fetchJson(endpoint, { method: "POST", body: body }).then(function () {
            return refreshActivity();
        }).catch(function () {});
    }

    function submitTopicForm(event) {
        event.preventDefault();
        var topicId = topicIdInput.value;
        
        // Collect selected filter tags from pill buttons
        var filterTagsContainer = document.getElementById("sl-topic-filter-tags");
        var selectedTags = [];
        if (filterTagsContainer) {
            var activePills = filterTagsContainer.querySelectorAll(".sl-tag-pill.is-active");
            selectedTags = Array.prototype.slice.call(activePills).map(function(pill) {
                return pill.getAttribute("data-tag-value");
            });
        }
        
        // Update hidden input with selected tags
        var hiddenInput = topicForm.querySelector('#sl-topic-filter-tags-hidden');
        if (hiddenInput) {
            hiddenInput.value = selectedTags.join(',');
        }
        
        var endpoint = topicId ? apiUrl("/topics/" + encodeURIComponent(topicId) + "/update/") : apiUrl("/topics/create/");
        var formData = new FormData(topicForm);
        fetchJson(endpoint, {
            method: "POST",
            body: formData
        }).then(function (result) {
            if (result && result.topic) {
                rerenderAfterMutation(result.topic);
            }
            closeModal(topicModal);
        }).catch(function (error) {
            alert(error.message || "Unable to save topic.");
        });
    }

    function submitMaterialForm(event) {
        event.preventDefault();
        var topicId = materialTopicIdInput.value || state.currentTopicId;
        if (!topicId) {
            alert("Open a topic before adding a material.");
            return;
        }
        var materialId = materialIdInput.value;
        var endpoint = materialId ? apiUrl("/materials/" + encodeURIComponent(materialId) + "/update/") : apiUrl("/topics/" + encodeURIComponent(topicId) + "/materials/create/");
        var formData = new FormData(materialForm);
        fetchJson(endpoint, {
            method: "POST",
            body: formData
        }).then(function (result) {
            if (result && result.topic) {
                rerenderAfterMutation(result.topic);
            }
            closeModal(materialModal);
        }).catch(function (error) {
            alert(error.message || "Unable to save material.");
        });
    }

    function requestDelete(kind, item, onConfirm) {
        if (!deleteModal) {
            return;
        }
        state.pendingDelete = onConfirm;
        if (deleteTitle) {
            deleteTitle.textContent = kind === "topic" ? "Delete topic?" : "Delete material?";
        }
        if (deleteMessage) {
            deleteMessage.textContent = kind === "topic"
                ? "Deleting this topic will remove its materials too. This cannot be undone."
                : "This cannot be undone.";
        }
        if (deleteConfirmBtn) {
            deleteConfirmBtn.textContent = "Delete";
        }
        openModal(deleteModal);
    }

    function deleteTopic(topicId) {
        requestDelete("topic", topicId, function () {
            fetchJson(apiUrl("/topics/" + encodeURIComponent(topicId) + "/delete/"), { method: "POST", body: new FormData() }).then(function () {
                removeTopicFromState(topicId);
                closeModal(deleteModal);
            }).catch(function (error) {
                alert(error.message || "Unable to delete topic.");
            });
        });
    }

    function deleteMaterial(materialId) {
        var topic = getCurrentTopic();
        if (!topic) {
            return;
        }
        requestDelete("material", materialId, function () {
            fetchJson(apiUrl("/materials/" + encodeURIComponent(materialId) + "/delete/"), { method: "POST", body: new FormData() }).then(function (result) {
                if (result && result.topic) {
                    rerenderAfterMutation(result.topic);
                }
                closeModal(deleteModal);
            }).catch(function (error) {
                alert(error.message || "Unable to delete material.");
            });
        });
    }

    function openTopicCreateModal() {
        if (!topicModal || !topicForm) {
            return;
        }
        if (topicModalTitle) topicModalTitle.textContent = "Create new topic";
        if (topicSubmitBtn) topicSubmitBtn.textContent = "Create topic";
        applyTopicFormValues(null);
        openModal(topicModal);
    }

    function openTopicEditModal(topicId) {
        if (!topicModal || !topicForm) {
            return;
        }
        var topic = getTopicById(topicId);
        if (!topic) {
            return;
        }
        if (topicModalTitle) topicModalTitle.textContent = "Edit topic";
        if (topicSubmitBtn) topicSubmitBtn.textContent = "Save changes";
        applyTopicFormValues(topic);
        openModal(topicModal);
    }

    function openMaterialCreateModal(topicId) {
        var topic = getTopicById(topicId || state.currentTopicId);
        if (!topic) {
            return;
        }
        if (materialModalTitle) materialModalTitle.textContent = "Create new material";
        if (materialSubmitBtn) materialSubmitBtn.textContent = "Create material";
        applyMaterialFormValues(topic, null);
        openModal(materialModal);
    }

    function openMaterialEditModal(materialId) {
        var topic = getCurrentTopic();
        if (!topic) {
            return;
        }
        var material = getMaterialById(topic, materialId);
        if (!material) {
            return;
        }
        if (materialModalTitle) materialModalTitle.textContent = "Edit material";
        if (materialSubmitBtn) materialSubmitBtn.textContent = "Save changes";
        applyMaterialFormValues(topic, material);
        openModal(materialModal);
    }

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            state.topicSearchQuery = searchInput.value || "";
            renderTopicCards();
        });
    }

    if (searchWrapper && searchToggle && searchInput) {
        function expandSearch() {
            searchWrapper.classList.add("expanded");
            searchToggle.setAttribute("aria-expanded", "true");
            try { searchInput.focus(); } catch (error) {}
        }
        function collapseSearch() {
            searchWrapper.classList.remove("expanded");
            searchToggle.setAttribute("aria-expanded", "false");
        }
        searchToggle.addEventListener("click", function (event) {
            event.stopPropagation();
            if (searchWrapper.classList.contains("expanded")) {
                collapseSearch();
                searchToggle.focus();
            } else {
                expandSearch();
            }
        });
        searchInput.addEventListener("focus", expandSearch);
        searchInput.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                collapseSearch();
                searchToggle.focus();
            }
        });
        document.addEventListener("click", function (event) {
            if (!searchWrapper.contains(event.target)) {
                collapseSearch();
            }
        });
    }

    filterButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            state.topicFilter = button.getAttribute("data-sl-filter") || "all";
            filterButtons.forEach(function (item) {
                var isActive = item === button;
                item.classList.toggle("is-active", isActive);
                item.setAttribute("aria-pressed", isActive ? "true" : "false");
            });
            renderTopicCards();
        });
    });

    if (topicForm) {
        topicForm.addEventListener("submit", submitTopicForm);
        
        // Add event listeners for pill buttons
        var filterTagsContainer = topicForm.querySelector("#sl-topic-filter-tags");
        if (filterTagsContainer) {
            var pills = filterTagsContainer.querySelectorAll(".sl-tag-pill");
            pills.forEach(function (pill) {
                pill.addEventListener("click", function (event) {
                    event.preventDefault();
                    pill.classList.toggle("is-active");
                    pill.setAttribute("aria-pressed", pill.classList.contains("is-active") ? "true" : "false");
                    
                    // Update preview/form display
                    applyTopicFormValues({
                        title: topicTitleInput.value,
                        description: topicDescInput.value,
                        badgeLabel: topicBadgeInput.value,
                        coverImageUrl: state.uploadPreviewUrl || topicCoverUrlInput.value,
                        filterTags: getSelectedFilterTags(topicForm)
                    });
                });
            });
        }
    }
    if (materialForm) {
        materialForm.addEventListener("submit", submitMaterialForm);
    }

    if (topicCoverInput) {
        topicCoverInput.addEventListener("change", function () {
            var file = topicCoverInput.files && topicCoverInput.files[0];
            if (!file) {
                state.uploadPreviewUrl = "";
                return;
            }
            state.uploadPreviewUrl = URL.createObjectURL(file);
        });
    }

    [topicTitleInput, topicDescInput, topicBadgeInput, topicCoverUrlInput].forEach(function (input) {
        if (!input) {
            return;
        }
        input.addEventListener("input", function () {
            // Input changes can be handled here if needed in the future
        });
    });

    if (topicForm) {
        topicForm.addEventListener("change", function () {
            // Form changes are handled by the pill button click handlers
        });
    }

    root.addEventListener("click", function (event) {
        // Check for topic edit first (before checking for card click)
        var topicEdit = event.target.closest("[data-sl-topic-edit]");
        if (topicEdit) {
            event.preventDefault();
            event.stopPropagation();
            openTopicEditModal(topicEdit.getAttribute("data-sl-topic-edit"));
            return;
        }

        // Check for topic delete (before checking for card click)
        var topicDelete = event.target.closest("[data-sl-topic-delete]");
        if (topicDelete) {
            event.preventDefault();
            event.stopPropagation();
            deleteTopic(topicDelete.getAttribute("data-sl-topic-delete"));
            return;
        }

        // Check for material edit (before checking for card click)
        var materialEdit = event.target.closest("[data-sl-material-edit]");
        if (materialEdit) {
            event.preventDefault();
            event.stopPropagation();
            openMaterialEditModal(materialEdit.getAttribute("data-sl-material-edit"));
            return;
        }

        // Check for material delete (before checking for card click)
        var materialDelete = event.target.closest("[data-sl-material-delete]");
        if (materialDelete) {
            event.preventDefault();
            event.stopPropagation();
            deleteMaterial(materialDelete.getAttribute("data-sl-material-delete"));
            return;
        }

        var materialToggle = event.target.closest("[data-sl-material-toggle], [data-sl-material-complete]");
        if (materialToggle) {
            event.preventDefault();
            event.stopPropagation();
            var materialId = materialToggle.getAttribute("data-sl-material-toggle") || materialToggle.getAttribute("data-sl-material-complete");
            var isCompleted = materialToggle.getAttribute("aria-pressed") === "true";
            recordEngagement(isCompleted ? "uncomplete" : "complete", materialId);
            return;
        }

        // Now check for card/topic click (after specific action buttons)
        var openTopicCard = event.target.closest("[data-sl-topic-card]");
        if (openTopicCard) {
            event.preventDefault();
            openTopic(openTopicCard.getAttribute("data-sl-topic-card"));
            return;
        }

        var topicTarget = event.target.closest("[data-sl-topic-target]");
        if (topicTarget) {
            event.preventDefault();
            openTopic(topicTarget.getAttribute("data-sl-topic-target"));
            return;
        }

        var materialCard = event.target.closest("[data-sl-material-id]");
        if (materialCard) {
            event.preventDefault();
            var currentTopic = getCurrentTopic();
            if (currentTopic) {
                var materialId = materialCard.getAttribute("data-sl-material-id");
                setActiveMaterial(currentTopic, materialId);
                if (userRole !== "volunteer") recordEngagement("view", materialId);
            }
            return;
        }

        var back = event.target.closest("#sl-back-to-topics");
        if (back) {
            event.preventDefault();
            showTopicList();
            return;
        }

        var createTopicBtn = event.target.closest("#sl-open-create-topic");
        if (createTopicBtn) {
            event.preventDefault();
            openTopicCreateModal();
            return;
        }

        var createMaterialBtn = event.target.closest("#sl-open-create-material");
        if (createMaterialBtn) {
            event.preventDefault();
            openMaterialCreateModal(state.currentTopicId);
            return;
        }

        var closeBtn = event.target.closest("[data-sl-close-modal]");
        if (closeBtn) {
            event.preventDefault();
            closeModal(topicModal);
            closeModal(materialModal);
            closeModal(deleteModal);
        }
    });

    if (deleteConfirmBtn) {
        deleteConfirmBtn.addEventListener("click", function () {
            if (typeof state.pendingDelete === "function") {
                state.pendingDelete();
            }
            state.pendingDelete = null;
        });
    }

    if (topicModal) {
        topicModal.addEventListener("click", function (event) {
            if (event.target === topicModal) {
                closeModal(topicModal);
            }
        });
    }
    if (materialModal) {
        materialModal.addEventListener("click", function (event) {
            if (event.target === materialModal) {
                closeModal(materialModal);
            }
        });
    }
    if (deleteModal) {
        deleteModal.addEventListener("click", function (event) {
            if (event.target === deleteModal) {
                closeModal(deleteModal);
            }
        });
    }

    renderTopicCards();
    renderSidebar();
    showTopicList();
    openDeepLink();

    if (userRole !== "volunteer") {
        var createTopicButton = document.getElementById("sl-open-create-topic");
        if (createTopicButton) {
            createTopicButton.style.display = "none";
        }
        var createMaterialButton = document.getElementById("sl-open-create-material");
        if (createMaterialButton) {
            createMaterialButton.style.display = "none";
        }
    }

    if (window.lucide && typeof window.lucide.createIcons === "function") {
        window.lucide.createIcons();
    }

    window.setInterval(function () {
        refreshActivity().catch(function () {});
    }, 30000);
})();

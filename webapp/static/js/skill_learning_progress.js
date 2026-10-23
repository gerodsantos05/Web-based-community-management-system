(function (root, factory) {
    var api = factory();
    if (typeof module === "object" && module.exports) {
        module.exports = api;
    }
    if (root && root.document) {
        api.initialize(root.document, root);
    }
}(typeof window !== "undefined" ? window : null, function () {
    "use strict";

    var STATUS_LABELS = {
        not_started: "Not started",
        in_progress: "In progress",
        completed: "Completed"
    };

    function getProgressStatus(completed, total) {
        var completedCount = Number(completed) || 0;
        var totalCount = Number(total) || 0;
        if (completedCount <= 0 || totalCount <= 0) {
            return "not_started";
        }
        if (completedCount >= totalCount) {
            return "completed";
        }
        return "in_progress";
    }

    function getTopicAction(completed, total) {
        var completedCount = Number(completed) || 0;
        var totalCount = Number(total) || 0;
        return totalCount > 0 && completedCount >= totalCount ? "reset" : "complete";
    }

    function filterProgress(items, selectedStatus, query) {
        var normalizedQuery = String(query || "").trim().toLowerCase();
        return (items || []).filter(function (item) {
            var statusMatches = selectedStatus === "all" || item.status === selectedStatus;
            var searchMatches = !normalizedQuery ||
                String(item.searchText || "").toLowerCase().indexOf(normalizedQuery) !== -1;
            return statusMatches && searchMatches;
        });
    }

    function parseProgressUpdateResponse(response, completed) {
        return response.json().then(function (payload) {
            if (!response.ok || !payload || payload.ok !== true || payload.completed !== completed) {
                throw new Error((payload && payload.error) ||
                    "The server rejected the progress update (HTTP " + response.status + ").");
            }
            return payload;
        }, function () {
            throw new Error("The server returned an invalid progress update response (HTTP " +
                response.status + ").");
        });
    }

    function buildMaterialProgressPayload(beneficiaryId, materialId, completed) {
        return {
            beneficiary_id: String(beneficiaryId),
            material_id: String(materialId),
            action: completed ? "complete" : "uncomplete"
        };
    }

    function initialize(document, window) {
        var page = document.getElementById("learning-progress");
        if (!page || page.dataset.initialized === "true") {
            return;
        }
        page.dataset.initialized = "true";
        var bulkUpdateUrl = page.dataset.bulkUpdateUrl;

        var source = document.getElementById("learning-progress-source");
        var beneficiaries = Array.prototype.map.call(
            source ? source.querySelectorAll(".lp-source-beneficiary") : [],
            function (beneficiaryElement) {
                var topics = Array.prototype.map.call(
                    beneficiaryElement.querySelectorAll(".lp-source-topic"),
                    function (topicElement) {
                        var materials = Array.prototype.map.call(
                            topicElement.querySelectorAll(".lp-source-material"),
                            function (materialElement) {
                                return {
                                    id: materialElement.dataset.materialId,
                                    title: materialElement.dataset.materialTitle || "",
                                    completed: materialElement.dataset.completed === "true",
                                    form: materialElement.querySelector("form"),
                                    pending: false
                                };
                            }
                        );
                        return {
                            id: topicElement.dataset.topicId,
                            title: topicElement.dataset.topicTitle || "",
                            materials: materials,
                            completed: materials.filter(function (material) {
                                return material.completed;
                            }).length,
                            total: materials.length
                        };
                    }
                );
                var beneficiary = {
                    id: beneficiaryElement.dataset.beneficiaryId,
                    name: beneficiaryElement.dataset.beneficiaryName || "",
                    typeLabel: beneficiaryElement.dataset.beneficiaryType || "Beneficiary type not set",
                    topics: topics
                };
                beneficiary.searchText = beneficiary.name + " " + beneficiary.typeLabel;
                return beneficiary;
            }
        );
        if (source) {
            source.remove();
        }

        var listView = document.getElementById("lp-beneficiary-view");
        var detailView = document.getElementById("lp-detail-view");
        var pageHeader = document.getElementById("lp-page-header");
        var grid = document.getElementById("lp-beneficiary-grid");
        var topicList = document.getElementById("lp-topic-list");
        var errorMessage = document.getElementById("lp-error");
        var beneficiarySearch = document.getElementById("lp-beneficiary-search");
        var beneficiaryEmpty = document.getElementById("lp-beneficiary-empty");
        var topicEmpty = document.getElementById("lp-topic-empty");
        var pagination = document.getElementById("lp-pagination");
        var pageIndicator = document.getElementById("lp-page-indicator");
        var currentPage = 1;
        var pageSize = 24;
        var dialog = document.getElementById("learning-progress-dialog");
        var dialogMessage = document.getElementById("lp-dialog-message");
        var pendingConfirmation = null;
        var currentBeneficiary = null;
        var beneficiaryFilter = "all";
        var topicFilter = "all";
        var openTopicId = null;

        function totals(items) {
            return items.reduce(function (sum, item) {
                sum.completed += item.completed;
                sum.total += item.total;
                return sum;
            }, { completed: 0, total: 0 });
        }

        function percent(completed, total) {
            return total > 0 ? Math.round(completed * 100 / total) : 0;
        }

        function statusLabel(status) {
            return STATUS_LABELS[status] || STATUS_LABELS.not_started;
        }

        function makeStatusBadge(status) {
            var badge = document.createElement("span");
            badge.className = "lp-status-badge";
            badge.dataset.status = status;
            badge.textContent = statusLabel(status);
            return badge;
        }

        function makeProgressTrack(completed, total, label) {
            var track = document.createElement("div");
            track.className = "lp-progress-track";
            track.setAttribute("role", "progressbar");
            track.setAttribute("aria-label", label);
            track.setAttribute("aria-valuemin", "0");
            track.setAttribute("aria-valuemax", "100");
            track.setAttribute("aria-valuenow", String(percent(completed, total)));
            var fill = document.createElement("div");
            fill.className = "lp-progress-fill";
            fill.dataset.status = getProgressStatus(completed, total);
            fill.style.width = percent(completed, total) + "%";
            track.appendChild(fill);
            return track;
        }

        function makeAvatar(name, className) {
            var avatar = document.createElement("span");
            avatar.className = "lp-avatar" + (className ? " " + className : "");
            avatar.setAttribute("aria-hidden", "true");
            avatar.textContent = String(name || "").trim().charAt(0).toUpperCase();
            return avatar;
        }

        function allBeneficiaryTotals() {
            var values = beneficiaries.reduce(function (sum, beneficiary) {
                var beneficiaryTotals = totals(beneficiary.topics);
                sum.completed += beneficiaryTotals.completed;
                sum.total += beneficiaryTotals.total;
                if (getProgressStatus(beneficiaryTotals.completed, beneficiaryTotals.total) === "completed") {
                    sum.finished += 1;
                }
                return sum;
            }, { completed: 0, total: 0, finished: 0 });
            return values;
        }

        function updateSummary() {
            var summary = allBeneficiaryTotals();
            var summaryPercent = percent(summary.completed, summary.total);
            document.getElementById("lp-summary-count").textContent =
                summary.completed + " of " + summary.total + " materials completed";
            document.getElementById("lp-summary-caption").textContent =
                beneficiaries.length + " beneficiaries · " + summary.finished + " finished";
            document.getElementById("lp-summary-percent").textContent = summaryPercent + "%";
            var bar = document.getElementById("lp-summary-bar");
            bar.style.width = summaryPercent + "%";
            bar.dataset.status = getProgressStatus(summary.completed, summary.total);
            var track = bar.parentElement;
            track.setAttribute("aria-valuenow", String(summaryPercent));
        }

        function updateFilterButtons(container, selected, items) {
            var counts = { all: items.length, not_started: 0, in_progress: 0, completed: 0 };
            items.forEach(function (item) {
                counts[item.status] += 1;
            });
            container.querySelectorAll("[data-status-filter]").forEach(function (button) {
                var status = button.dataset.statusFilter;
                button.setAttribute("aria-pressed", String(status === selected));
                var count = button.querySelector("[data-filter-count]");
                if (count) {
                    count.textContent = String(counts[status] || 0);
                }
            });
        }

        function resetListFilters() {
            beneficiaryFilter = "all";
            beneficiarySearch.value = "";
            currentPage = 1;
            updateFilterButtons(document.getElementById("lp-beneficiary-filters"), beneficiaryFilter, beneficiaryStatusItems());
        }

        function beneficiaryStatusItems() {
            return beneficiaries.map(function (beneficiary) {
                var summary = totals(beneficiary.topics);
                return {
                    id: beneficiary.id,
                    name: beneficiary.name,
                    searchText: beneficiary.searchText,
                    completed: summary.completed,
                    total: summary.total,
                    topicCount: beneficiary.topics.length,
                    finishedTopics: beneficiary.topics.filter(function (topic) {
                        return getProgressStatus(topic.completed, topic.total) === "completed";
                    }).length,
                    status: getProgressStatus(summary.completed, summary.total)
                };
            });
        }

        function renderBeneficiaryList() {
            var items = beneficiaryStatusItems();
            updateFilterButtons(document.getElementById("lp-beneficiary-filters"), beneficiaryFilter, items);
            var visibleItems = filterProgress(items, beneficiaryFilter, beneficiarySearch.value);
            var pageCount = Math.max(1, Math.ceil(visibleItems.length / pageSize));
            currentPage = Math.min(currentPage, pageCount);
            var pageItems = visibleItems.slice((currentPage - 1) * pageSize, currentPage * pageSize);
            grid.replaceChildren();
            beneficiaryEmpty.hidden = beneficiaries.length > 0 && visibleItems.length > 0;
            if (!beneficiaries.length) {
                beneficiaryEmpty.textContent = "There are no beneficiary learning records to display yet.";
                beneficiaryEmpty.hidden = false;
            } else {
                beneficiaryEmpty.textContent = "No beneficiaries match this search or filter.";
            }
            pagination.hidden = visibleItems.length <= pageSize;
            pageIndicator.textContent = "Page " + currentPage + " of " + pageCount;
            document.getElementById("lp-page-previous").disabled = currentPage <= 1;
            document.getElementById("lp-page-next").disabled = currentPage >= pageCount;

            pageItems.forEach(function (item) {
                var beneficiary = beneficiaries.find(function (entry) {
                    return entry.id === item.id;
                });
                var card = document.createElement("button");
                card.type = "button";
                card.className = "lp-beneficiary-card";
                card.dataset.beneficiaryId = beneficiary.id;
                card.setAttribute(
                    "aria-label",
                    "Open progress for " + beneficiary.name + ", " + item.completed + " of " + item.total + " completed"
                );

                var heading = document.createElement("span");
                heading.className = "lp-beneficiary-heading";
                heading.appendChild(makeAvatar(beneficiary.name));
                var name = document.createElement("span");
                name.className = "lp-beneficiary-name-group";
                var nameLabel = document.createElement("span");
                nameLabel.className = "lp-beneficiary-name";
                nameLabel.textContent = beneficiary.name;
                var typeLabel = document.createElement("span");
                typeLabel.className = "lp-beneficiary-type";
                typeLabel.textContent = beneficiary.typeLabel;
                name.appendChild(nameLabel);
                name.appendChild(typeLabel);
                heading.appendChild(name);
                var chevron = document.createElement("span");
                chevron.className = "lp-chevron";
                chevron.setAttribute("aria-hidden", "true");
                chevron.textContent = "›";
                heading.appendChild(chevron);
                card.appendChild(heading);

                var meta = document.createElement("span");
                meta.className = "lp-card-meta";
                meta.appendChild(makeStatusBadge(item.status));
                var topicCount = document.createElement("span");
                topicCount.className = "lp-topic-count";
                topicCount.textContent = item.topicCount + (item.topicCount === 1 ? " topic" : " topics");
                meta.appendChild(topicCount);
                card.appendChild(meta);
                card.appendChild(makeProgressTrack(
                    item.completed,
                    item.total,
                    beneficiary.name + " progress"
                ));

                var completion = document.createElement("span");
                completion.className = "lp-completion-count";
                completion.textContent = item.completed + " of " + item.total + " completed";
                card.appendChild(completion);
                grid.appendChild(card);
            });
        }

        function updatePersonSummary(beneficiary) {
            var summary = totals(beneficiary.topics);
            var topicCount = beneficiary.topics.filter(function (topic) {
                return getProgressStatus(topic.completed, topic.total) === "completed";
            }).length;
            var value = percent(summary.completed, summary.total);
            document.getElementById("lp-person-avatar").textContent =
                String(beneficiary.name || "").trim().charAt(0).toUpperCase();
            document.getElementById("lp-person-name").textContent = beneficiary.name;
            document.getElementById("lp-person-type").textContent = beneficiary.typeLabel;
            document.getElementById("lp-topic-finished").textContent =
                topicCount + " of " + beneficiary.topics.length + " topics finished";
            document.getElementById("lp-person-percent").textContent = value + "%";
            document.getElementById("lp-person-count").textContent =
                summary.completed + " of " + summary.total + " completed";
            var bar = document.getElementById("lp-person-bar");
            bar.style.width = value + "%";
            bar.dataset.status = getProgressStatus(summary.completed, summary.total);
            document.getElementById("lp-person-track").setAttribute("aria-valuenow", String(value));
        }

        function renderTopicFilters() {
            var topicItems = currentBeneficiary.topics.map(function (topic) {
                return {
                    id: topic.id,
                    searchText: topic.title,
                    completed: topic.completed,
                    total: topic.total,
                    status: getProgressStatus(topic.completed, topic.total)
                };
            });
            updateFilterButtons(document.getElementById("lp-topic-filters"), topicFilter, topicItems);
            var visibleTopics = filterProgress(topicItems, topicFilter, "");
            if (!visibleTopics.some(function (topic) { return topic.id === openTopicId; })) {
                openTopicId = visibleTopics.length ? visibleTopics[0].id : null;
            }
            renderTopics(visibleTopics);
        }

        function updateTopicCounts(topic) {
            topic.completed = topic.materials.filter(function (material) {
                return material.completed;
            }).length;
            topic.total = topic.materials.length;
        }

        function renderTopics(visibleTopics) {
            topicList.replaceChildren();
            topicEmpty.hidden = visibleTopics.length > 0;
            visibleTopics.forEach(function (topicStatus) {
                var topic = currentBeneficiary.topics.find(function (entry) {
                    return entry.id === topicStatus.id;
                });
                var open = topic.id === openTopicId;
                var status = getProgressStatus(topic.completed, topic.total);
                var item = document.createElement("section");
                item.className = "lp-topic-item" + (open ? " is-open" : "");

                var toggle = document.createElement("button");
                toggle.type = "button";
                toggle.className = "lp-topic-toggle";
                toggle.dataset.topicId = topic.id;
                toggle.setAttribute("aria-expanded", String(open));
                toggle.setAttribute("aria-controls", "lp-topic-body-" + topic.id);
                var heading = document.createElement("span");
                heading.className = "lp-topic-heading";
                var chevron = document.createElement("span");
                chevron.className = "lp-chevron";
                chevron.setAttribute("aria-hidden", "true");
                chevron.textContent = "›";
                heading.appendChild(chevron);
                var title = document.createElement("span");
                title.className = "lp-topic-name";
                title.textContent = topic.title;
                heading.appendChild(title);
                toggle.appendChild(heading);
                var progressRow = document.createElement("span");
                progressRow.className = "lp-topic-progress-row";
                progressRow.appendChild(makeProgressTrack(topic.completed, topic.total, topic.title + " progress"));
                var count = document.createElement("span");
                count.className = "lp-topic-count-label";
                count.textContent = topic.completed + "/" + topic.total;
                progressRow.appendChild(count);
                progressRow.appendChild(makeStatusBadge(status));
                toggle.appendChild(progressRow);
                item.appendChild(toggle);

                var body = document.createElement("div");
                body.className = "lp-topic-body";
                body.id = "lp-topic-body-" + topic.id;
                body.hidden = !open;
                var tools = document.createElement("div");
                tools.className = "lp-topic-tools";
                var label = document.createElement("span");
                label.className = "lp-materials-label";
                label.textContent = "Materials";
                tools.appendChild(label);
                var markAll = document.createElement("button");
                markAll.type = "button";
                markAll.className = "lp-mark-all";
                var topicAction = getTopicAction(topic.completed, topic.total);
                markAll.dataset.topicAction = topicAction;
                markAll.dataset.topicId = topic.id;
                markAll.textContent = topicAction === "reset" ? "Reset all" : "Mark all complete";
                markAll.disabled = topic.materials.length === 0 ||
                    topic.materials.some(function (material) { return material.pending; });
                markAll.setAttribute(
                    "aria-label",
                    (topicAction === "reset" ? "Reset all materials in " : "Mark all materials in ") + topic.title +
                    (topicAction === "reset" ? " to not completed" : " complete")
                );
                tools.appendChild(markAll);
                body.appendChild(tools);

                var materials = document.createElement("div");
                materials.className = "lp-material-list";
                topic.materials.forEach(function (material) {
                    var row = document.createElement("div");
                    row.className = "lp-material-row" + (material.completed ? " is-completed" : "");
                    var checkboxTarget = document.createElement("label");
                    checkboxTarget.className = "lp-material-checkbox-target";
                    var checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.className = "lp-material-checkbox";
                    checkbox.checked = material.completed;
                    checkbox.disabled = material.pending;
                    checkbox.id = "lp-material-checkbox-" + material.id;
                    checkbox.dataset.materialId = material.id;
                    checkbox.dataset.topicId = topic.id;
                    checkbox.setAttribute(
                        "aria-label",
                        material.completed ? "Mark " + material.title + " incomplete" : "Mark " + material.title + " complete"
                    );
                    checkboxTarget.appendChild(checkbox);
                    row.appendChild(checkboxTarget);
                    var materialTitle = document.createElement("span");
                    materialTitle.className = "lp-material-name";
                    materialTitle.textContent = material.title;
                    row.appendChild(materialTitle);
                    if (material.completed) {
                        var done = document.createElement("span");
                        done.className = "lp-done-label";
                        done.textContent = "Done";
                        row.appendChild(done);
                    }
                    materials.appendChild(row);
                });
                body.appendChild(materials);
                item.appendChild(body);
                topicList.appendChild(item);
            });
        }

        function setFilter(container, value, kind) {
            if (kind === "beneficiary") {
                beneficiaryFilter = value;
                currentPage = 1;
                renderBeneficiaryList();
            } else {
                topicFilter = value;
                renderTopicFilters();
            }
        }

        function clearError() {
            errorMessage.hidden = true;
            errorMessage.textContent = "";
        }

        function showError(message) {
            errorMessage.textContent = message || "Could not update progress. Please try again.";
            errorMessage.hidden = false;
        }

        function getMaterial(topicId, materialId) {
            var topic = currentBeneficiary.topics.find(function (entry) {
                return entry.id === topicId;
            });
            if (!topic) {
                return null;
            }
            return {
                topic: topic,
                material: topic.materials.find(function (entry) {
                    return entry.id === materialId;
                })
            };
        }

        function requestCompletion(material, completed) {
            if (!material || !material.form) {
                return Promise.reject(new Error("The progress update form is missing."));
            }
            var formData = new window.FormData(material.form);
            var payload = buildMaterialProgressPayload(
                formData.get("beneficiary_id"),
                material.id,
                completed
            );
            Object.keys(payload).forEach(function (key) {
                formData.set(key, payload[key]);
            });
            formData.delete("topic_id");
            return window.fetch(bulkUpdateUrl, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" }
            }).then(function (response) {
                return parseProgressUpdateResponse(response, completed);
            });
        }

        function updateMaterial(topicId, materialId, completed) {
            var match = getMaterial(topicId, materialId);
            if (!match || !match.material || match.material.pending || match.material.completed === completed) {
                return;
            }
            var selectedBeneficiaryId = currentBeneficiary.id;
            var material = match.material;
            var previous = material.completed;
            clearError();
            material.completed = completed;
            material.pending = true;
            updateTopicCounts(match.topic);
            updateSummary();
            updatePersonSummary(currentBeneficiary);
            renderTopicFilters();

            requestCompletion(material, completed).then(function () {
                material.pending = false;
                if (currentBeneficiary && currentBeneficiary.id === selectedBeneficiaryId) {
                    renderTopicFilters();
                }
            }).catch(function (error) {
                material.completed = previous;
                material.pending = false;
                updateTopicCounts(match.topic);
                updateSummary();
                if (currentBeneficiary && currentBeneficiary.id === selectedBeneficiaryId) {
                    updatePersonSummary(currentBeneficiary);
                    renderTopicFilters();
                }
                showError((error && error.message) ||
                    "Progress could not be saved. Your previous status has been restored.");
            });
        }

        function setTopicCompletion(topicId, completed) {
            var selectedBeneficiaryId = currentBeneficiary.id;
            var topic = currentBeneficiary.topics.find(function (entry) {
                return entry.id === topicId;
            });
            if (!topic || topic.materials.length === 0 ||
                topic.materials.some(function (material) { return material.pending; })) {
                return;
            }
            clearError();
            topic.materials.forEach(function (material) {
                material.pending = true;
            });
            renderTopicFilters();

            var form = topic.materials[0].form;
            var formData = new window.FormData(form);
            formData.delete("material_id");
            formData.set("action", completed ? "complete" : "uncomplete");
            formData.set("topic_id", topic.id);
            window.fetch(bulkUpdateUrl, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" }
            }).then(function (response) {
                return parseProgressUpdateResponse(response, completed);
            }).then(function () {
                topic.materials.forEach(function (material) {
                    material.completed = completed;
                    material.pending = false;
                });
                updateTopicCounts(topic);
                updateSummary();
                if (currentBeneficiary && currentBeneficiary.id === selectedBeneficiaryId) {
                    updatePersonSummary(currentBeneficiary);
                    renderTopicFilters();
                }
            }).catch(function (error) {
                topic.materials.forEach(function (material) {
                    material.pending = false;
                });
                if (currentBeneficiary && currentBeneficiary.id === selectedBeneficiaryId) {
                    renderTopicFilters();
                }
                showError(error.message || "Topic progress could not be saved.");
            });
        }

        function resetDetailFilters() {
            topicFilter = "all";
            openTopicId = currentBeneficiary && currentBeneficiary.topics.length
                ? currentBeneficiary.topics[0].id
                : null;
        }

        function requestConfirmation(message, action, destructive) {
            pendingConfirmation = action;
            dialogMessage.textContent = message;
            var confirmButton = document.getElementById("lp-confirm");
            confirmButton.hidden = false;
            confirmButton.textContent = "Save";
            confirmButton.dataset.destructive = destructive ? "true" : "false";
            dialog.showModal();
        }

        function updateUrl(beneficiaryId, mode) {
            var url = new window.URL(window.location.href);
            if (beneficiaryId) {
                url.searchParams.set("beneficiary", beneficiaryId);
            } else {
                url.searchParams.delete("beneficiary");
            }
            var nextState = {
                lpView: beneficiaryId ? "detail" : "list",
                lpCanGoBack: mode === "select"
            };
            if (mode === "select" || mode === "replace") {
                window.history.pushState(nextState, "", url.pathname + url.search + url.hash);
            } else {
                window.history.replaceState(nextState, "", url.pathname + url.search + url.hash);
            }
        }

        function showList(mode) {
            currentBeneficiary = null;
            pageHeader.hidden = false;
            detailView.hidden = true;
            listView.hidden = false;
            resetListFilters();
            clearError();
            renderBeneficiaryList();
            if (mode === "back" && window.history.state && window.history.state.lpCanGoBack) {
                window.history.back();
            } else if (mode === "push" || mode === "back") {
                updateUrl(null, "push");
            } else if (mode === "replace") {
                updateUrl(null, "replace");
            }
        }

        function showBeneficiary(id, mode) {
            var beneficiary = beneficiaries.find(function (entry) {
                return entry.id === String(id);
            });
            if (!beneficiary) {
                showList(mode === "initial" ? "replace" : "none");
                return;
            }
            currentBeneficiary = beneficiary;
            pageHeader.hidden = true;
            listView.hidden = true;
            detailView.hidden = false;
            resetDetailFilters();
            clearError();
            updatePersonSummary(beneficiary);
            renderTopicFilters();
            if (mode === "select") {
                updateUrl(beneficiary.id, "select");
            } else if (mode === "replace") {
                updateUrl(beneficiary.id, "replace");
            }
        }

        document.getElementById("lp-beneficiary-filters").addEventListener("click", function (event) {
            var button = event.target.closest("[data-status-filter]");
            if (button) {
                setFilter(this, button.dataset.statusFilter, "beneficiary");
            }
        });
        document.getElementById("lp-topic-filters").addEventListener("click", function (event) {
            var button = event.target.closest("[data-status-filter]");
            if (button) {
                setFilter(this, button.dataset.statusFilter, "topic");
            }
        });
        grid.addEventListener("click", function (event) {
            var card = event.target.closest("[data-beneficiary-id]");
            if (card) {
                showBeneficiary(card.dataset.beneficiaryId, "select");
            }
        });
        document.getElementById("lp-back-to-beneficiaries").addEventListener("click", function () {
            showList("back");
        });
        document.getElementById("lp-page-previous").addEventListener("click", function () {
            if (currentPage > 1) {
                currentPage -= 1;
                renderBeneficiaryList();
            }
        });
        document.getElementById("lp-page-next").addEventListener("click", function () {
            currentPage += 1;
            renderBeneficiaryList();
        });
        beneficiarySearch.addEventListener("input", function () {
            currentPage = 1;
            renderBeneficiaryList();
        });
        topicList.addEventListener("click", function (event) {
            var toggle = event.target.closest(".lp-topic-toggle");
            if (toggle) {
                openTopicId = openTopicId === toggle.dataset.topicId ? null : toggle.dataset.topicId;
                renderTopicFilters();
                return;
            }
            var topicActionButton = event.target.closest("[data-topic-action]");
            if (topicActionButton) {
                var topic = currentBeneficiary.topics.find(function (entry) {
                    return entry.id === topicActionButton.dataset.topicId;
                });
                if (topic) {
                    var isReset = topicActionButton.dataset.topicAction === "reset";
                    setTopicCompletion(topic.id, !isReset);
                }
            }
        });
        topicList.addEventListener("change", function (event) {
            var checkbox = event.target.closest(".lp-material-checkbox");
            if (checkbox) {
                var shouldComplete = checkbox.checked;
                updateMaterial(checkbox.dataset.topicId, checkbox.dataset.materialId, shouldComplete);
            }
        });
        document.getElementById("lp-cancel").addEventListener("click", function () {
            pendingConfirmation = null;
            dialog.close();
        });
        document.getElementById("lp-dialog-close").addEventListener("click", function () {
            pendingConfirmation = null;
            dialog.close();
        });
        document.getElementById("lp-confirm").addEventListener("click", function () {
            var action = pendingConfirmation;
            pendingConfirmation = null;
            dialog.close();
            if (action) {
                action();
            }
        });
        dialog.addEventListener("click", function (event) {
            if (event.target === dialog) {
                pendingConfirmation = null;
                dialog.close();
            }
        });
        dialog.addEventListener("cancel", function () {
            pendingConfirmation = null;
        });
        window.addEventListener("popstate", function () {
            var id = new window.URL(window.location.href).searchParams.get("beneficiary");
            if (id) {
                showBeneficiary(id, "none");
            } else {
                showList("none");
            }
        });

        updateSummary();
        var initialBeneficiary = new window.URL(window.location.href).searchParams.get("beneficiary");
        if (initialBeneficiary) {
            showBeneficiary(initialBeneficiary, "initial");
            window.history.replaceState({ lpView: "detail", lpCanGoBack: false }, "", window.location.href);
        } else {
            window.history.replaceState({ lpView: "list", lpCanGoBack: false }, "", window.location.href);
            renderBeneficiaryList();
        }
    }

    return {
        getProgressStatus: getProgressStatus,
        getTopicAction: getTopicAction,
        filterProgress: filterProgress,
        buildMaterialProgressPayload: buildMaterialProgressPayload,
        parseProgressUpdateResponse: parseProgressUpdateResponse,
        initialize: initialize
    };
}));

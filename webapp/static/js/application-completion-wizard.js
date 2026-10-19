(function () {
    "use strict";

    var dataNode = document.getElementById("application-tracker-data");
    var trigger = document.getElementById("applicationTrackerTrigger");
    var modal = document.getElementById("applicationTrackerModal");
    var closeButton = document.getElementById("applicationTrackerClose");
    var list = document.getElementById("applicationTrackerList");
    var message = document.getElementById("applicationTrackerMessage");
    if (!dataNode || !trigger || !modal || !closeButton || !list || !message) return;

    var applications = JSON.parse(dataNode.textContent || "[]");
    var filters = Array.from(document.querySelectorAll("[data-application-filter]"));
    var activeFilter = "all";
    var lastTrigger;
    var fieldLabels = {
        full_name: "Full name", email: "Email", gender: "Gender", birthdate: "Birthdate", civil_status: "Civil status",
        phone: "Phone number", barangay: "Barangay", street_address: "House number, street, or sitio", city: "City",
        availability_days: "Availability days", skills: "Skills", reason_for_volunteering: "Reason for volunteering",
        assistance_reason: "Reason for assistance", supporting_information: "Supporting information",
        emergency_contact_name: "Emergency contact name", emergency_contact_relationship: "Emergency contact relationship",
        emergency_contact_phone: "Emergency contact number", valid_id_type: "Valid ID type", valid_id_number: "Valid ID number",
        school: "School", course: "Course", year_level: "Year level", school_coordinator_name: "School coordinator",
        school_coordinator_contact: "Coordinator contact", occupation: "Occupation", past_experience: "Past experience",
        children_count: "Number of children", household_size: "Household size", income_source: "Income source",
        monthly_income_range: "Monthly income range", child_name: "Child's name", child_birthdate: "Child's birthdate",
        grade_level: "Grade level", guardian_name: "Parent or guardian", guardian_relationship: "Relationship to child",
        guardian_contact: "Guardian contact", disability_type: "Type of disability", assistance_needed: "Assistance needed",
        caregiver_name: "Caregiver name", caregiver_contact: "Caregiver contact"
    };
    var valueLabels = {
        male: "Male", female: "Female", other: "Other", prefer_not: "Prefer not to say",
        single: "Single", married: "Married", widowed: "Widowed", separated: "Separated",
        national_id: "Philippine National ID", drivers_license: "Driver's license", voters_id: "Voter's ID",
        postal_id: "Postal ID", philhealth_id: "PhilHealth ID", umid: "UMID", passport: "Passport",
        employed: "Employment", self_employed: "Self-employed / small business", informal: "Informal or seasonal work",
        remittances: "Remittances", none: "No regular income", under_5000: "Below PHP 5,000",
        "5000_9999": "PHP 5,000-9,999", "10000_14999": "PHP 10,000-14,999", "15000_24999": "PHP 15,000-24,999",
        "25000_plus": "PHP 25,000 or more", no_income: "No household income", high_school: "High school",
        college: "College", graduate: "Graduate"
    };

    function labelFor(name) {
        return fieldLabels[name] || name.replace(/_/g, " ").replace(/\b\w/g, function (character) { return character.toUpperCase(); });
    }

    function displayValue(value) {
        if (Array.isArray(value)) return value.map(displayValue).join(", ");
        return valueLabels[value] || String(value == null ? "" : value);
    }

    function categoryFor(application) {
        if (application.status === "pending") return "pending";
        if (application.status === "approved") return "approved";
        if (application.status === "rejected") return "attention";
        return "completed";
    }

    function appendSummaryDetails(container, values) {
        var entries = Object.entries(values || {}).filter(function (entry) {
            return entry[1] !== "" && entry[1] !== null && entry[1] !== undefined;
        });
        if (!entries.length) return;
        var listNode = document.createElement("dl");
        listNode.className = "application-tracker-details";
        entries.forEach(function (entry) {
            var wrapper = document.createElement("div");
            var term = document.createElement("dt");
            var value = document.createElement("dd");
            term.textContent = labelFor(entry[0]);
            value.textContent = displayValue(entry[1]);
            wrapper.append(term, value);
            listNode.appendChild(wrapper);
        });
        container.appendChild(listNode);
    }

    function appendReadOnlyDocuments(container, documents) {
        var uploaded = (documents || []).filter(function (documentData) { return Boolean(documentData.fileName); });
        if (!uploaded.length) return;
        var listNode = document.createElement("ul");
        listNode.className = "application-tracker-readonly-documents";
        uploaded.forEach(function (documentData) {
            var item = document.createElement("li");
            item.textContent = documentData.label + ": " + documentData.fileName;
            listNode.appendChild(item);
        });
        container.appendChild(listNode);
    }

    function createApplicationWizard(application, card) {
        var form = document.createElement("form");
        form.className = "application-completion-form";
        form.noValidate = true;
        var state = {
            values: Object.assign({}, application.completionValues || {}),
            documents: (application.completionDocuments || []).map(function (item) { return Object.assign({}, item); }),
            files: new Map(),
            previews: new Map(),
            removed: new Set(),
            consent: false,
            saving: false
        };

        function setVisibleError(node, text) {
            node.textContent = text || "";
            node.hidden = !text;
        }

        function setFieldValue(name, value) {
            state.values[name] = value;
        }

        function createInput(field) {
            var wrapper = document.createElement("label");
            wrapper.className = "application-completion-field";
            var labelText = document.createElement("span");
            labelText.className = "application-completion-label-text";
            labelText.appendChild(document.createTextNode(field.label));
            if (field.required) {
                var requiredMark = document.createElement("span");
                requiredMark.className = "application-completion-required-mark";
                requiredMark.textContent = " *";
                labelText.appendChild(requiredMark);
            }
            wrapper.appendChild(labelText);
            var value = state.values[field.name];
            if (field.type === "select") {
                var select = document.createElement("select");
                var placeholder = document.createElement("option");
                placeholder.value = "";
                placeholder.textContent = "Select an option";
                select.appendChild(placeholder);
                (field.options || []).forEach(function (option) {
                    var item = document.createElement("option");
                    item.value = option.value;
                    item.textContent = option.label;
                    select.appendChild(item);
                });
                select.value = value || "";
                select.required = Boolean(field.required);
                select.addEventListener("change", function () { setFieldValue(field.name, select.value); });
                wrapper.appendChild(select);
            } else if (field.type === "checkboxes") {
                var group = document.createElement("span");
                group.className = "application-completion-checkboxes";
                if (!Array.isArray(value)) setFieldValue(field.name, []);
                var selected = Array.isArray(value) ? value : [];
                (field.options || []).forEach(function (option) {
                    var itemLabel = document.createElement("label");
                    itemLabel.className = "application-completion-check-option";
                    var checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.value = option.value;
                    checkbox.checked = selected.includes(option.value);
                    checkbox.addEventListener("change", function () {
                        var nextValues = Array.from(group.querySelectorAll("input:checked")).map(function (input) { return input.value; });
                        setFieldValue(field.name, nextValues);
                    });
                    var optionText = document.createElement("span");
                    optionText.textContent = option.label;
                    itemLabel.append(checkbox, optionText);
                    group.appendChild(itemLabel);
                });
                wrapper.appendChild(group);
            } else {
                var input = field.type === "textarea" ? document.createElement("textarea") : document.createElement("input");
                if (field.type !== "textarea") input.type = field.type;
                if (field.type === "textarea") input.rows = 3;
                if (field.min != null) input.min = String(field.min);
                if (field.max != null) input.max = String(field.max);
                if (field.maxLength != null) input.maxLength = field.maxLength;
                input.required = Boolean(field.required);
                input.value = value == null ? "" : String(value);
                input.autocomplete = "off";
                input.addEventListener("input", function () { setFieldValue(field.name, input.value); });
                wrapper.appendChild(input);
            }
            return wrapper;
        }

        function hasDocument(documentData) {
            return Boolean(documentData.fileName) && !state.removed.has(documentData.key) || state.files.has(documentData.key);
        }

        function createDocumentControl(documentData) {
            var item = document.createElement("article");
            item.className = "application-completion-document";
            var heading = document.createElement("div");
            heading.className = "application-completion-document-heading";
            var title = document.createElement("strong");
            title.textContent = documentData.label;
            var requirement = document.createElement("span");
            requirement.className = documentData.required ? "is-required" : "is-optional";
            requirement.textContent = documentData.required ? "Required" : "Optional";
            heading.append(title, requirement);
            item.appendChild(heading);
            var file = state.files.get(documentData.key);
            var previewUrl = state.previews.get(documentData.key);
            if (file) {
                var fileName = document.createElement("p");
                fileName.className = "application-completion-file-name";
                fileName.textContent = file.name;
                item.appendChild(fileName);
                if (previewUrl && file.type.indexOf("image/") === 0) {
                    var image = document.createElement("img");
                    image.className = "application-completion-preview";
                    image.src = previewUrl;
                    image.alt = documentData.label + " preview";
                    item.appendChild(image);
                } else if (previewUrl && file.type === "application/pdf") {
                    var preview = document.createElement("iframe");
                    preview.className = "application-completion-pdf-preview";
                    preview.src = previewUrl;
                    preview.title = documentData.label + " preview";
                    item.appendChild(preview);
                }
            } else if (documentData.fileName && !state.removed.has(documentData.key)) {
                var saved = document.createElement("p");
                saved.className = "application-completion-file-name is-saved";
                saved.textContent = "Saved securely: " + documentData.fileName;
                item.appendChild(saved);
            }
            var input = document.createElement("input");
            input.type = "file";
            input.required = Boolean(documentData.required && !hasDocument(documentData));
            input.accept = documentData.imageOnly ? ".jpg,.jpeg,.png,image/jpeg,image/png" : ".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf";
            input.setAttribute("aria-label", "Upload " + documentData.label);
            input.addEventListener("change", function () {
                var selectedFile = input.files && input.files[0];
                if (!selectedFile) return;
                var extension = selectedFile.name.split(".").pop().toLowerCase();
                if (selectedFile.size > 5 * 1024 * 1024) {
                    message.textContent = "Files must be 5 MB or smaller.";
                    return;
                }
                if (!["jpg", "jpeg", "png", "pdf"].includes(extension) || (documentData.imageOnly && extension === "pdf")) {
                    message.textContent = documentData.imageOnly ? "Choose a JPG or PNG photo." : "Choose a JPG, PNG, or PDF file.";
                    return;
                }
                message.textContent = "";
                state.files.set(documentData.key, selectedFile);
                state.removed.delete(documentData.key);
                if (state.previews.has(documentData.key)) URL.revokeObjectURL(state.previews.get(documentData.key));
                state.previews.set(documentData.key, URL.createObjectURL(selectedFile));
                renderForm();
            });
            item.appendChild(input);
            var hint = document.createElement("p");
            hint.className = "application-completion-hint";
            hint.textContent = documentData.imageOnly ? "JPG or PNG, up to 5 MB." : "JPG, PNG, or PDF, up to 5 MB.";
            item.appendChild(hint);
            if (hasDocument(documentData)) {
                var remove = document.createElement("button");
                remove.type = "button";
                remove.className = "application-completion-remove";
                remove.textContent = "Remove";
                remove.setAttribute("aria-label", "Remove " + documentData.label);
                remove.addEventListener("click", function () {
                    if (state.previews.has(documentData.key)) URL.revokeObjectURL(state.previews.get(documentData.key));
                    state.previews.delete(documentData.key);
                    state.files.delete(documentData.key);
                    if (documentData.fileName) state.removed.add(documentData.key);
                    renderForm();
                });
                item.appendChild(remove);
            }
            return item;
        }

        function validateForm() {
            for (var field of application.completionFields) {
                var value = state.values[field.name];
                if (field.required && (value == null || value === "" || (Array.isArray(value) && value.length === 0))) {
                    return "Complete the required field: " + field.label + ".";
                }
            }
            for (var documentData of state.documents) {
                if (documentData.required && !hasDocument(documentData)) {
                    return "Upload the required " + documentData.label.toLowerCase() + ".";
                }
            }
            if (!state.consent) return "Consent is required before submitting.";
            return "";
        }

        async function submitForm() {
            if (state.saving) return;
            state.saving = true;
            var data = new FormData();
            data.append("action", "submit");
            var editableValues = {};
            application.completionFields.forEach(function (field) {
                editableValues[field.name] = state.values[field.name] == null ? "" : state.values[field.name];
            });
            data.append("details", JSON.stringify(editableValues));
            data.append("removed_documents", JSON.stringify(Array.from(state.removed)));
            state.files.forEach(function (file, documentType) {
                data.append("documents", file, file.name);
                data.append("document_types", documentType);
            });
            data.append("consent", "on");
            var csrf = document.querySelector("input[name=csrfmiddlewaretoken]");
            if (csrf) data.append("csrfmiddlewaretoken", csrf.value);
            try {
                var template = modal.dataset.completeUrlTemplate;
                var endpoint = template.replace(/\/0\/complete-profile\/$/, "/" + application.id + "/complete-profile/");
                var response = await fetch(endpoint, { method: "POST", credentials: "same-origin", body: data });
                var payload = await response.json();
                if (!response.ok) throw new Error(payload.error || "Unable to submit this application.");
                Object.assign(application, payload.application);
                state.files.forEach(function (_, documentType) {
                    if (state.previews.has(documentType)) URL.revokeObjectURL(state.previews.get(documentType));
                });
                message.textContent = payload.message;
                render();
            } catch (error) {
                var formError = form.querySelector(".application-completion-error");
                setVisibleError(formError, error.message || "Unable to submit this application.");
            } finally {
                state.saving = false;
            }
        }

        function renderForm() {
            form.replaceChildren();
            application.completionSections.forEach(function (section) {
                var sectionNode = document.createElement("section");
                sectionNode.className = "application-completion-section";
                var heading = document.createElement("h4");
                heading.className = "application-completion-section-title";
                heading.textContent = section.label;
                sectionNode.appendChild(heading);
                var fieldGroup = document.createElement("div");
                fieldGroup.className = "application-completion-fields";
                section.fields.forEach(function (field) { fieldGroup.appendChild(createInput(field)); });
                state.documents.filter(function (documentData) {
                    return documentData.section === section.key;
                }).forEach(function (documentData) {
                    fieldGroup.appendChild(createDocumentControl(documentData));
                });
                if (section.key === "personal") {
                    var location = document.createElement("p");
                    location.className = "application-completion-location";
                    location.textContent = "City: Bacoor City, Cavite";
                    fieldGroup.appendChild(location);
                }
                sectionNode.appendChild(fieldGroup);
                form.appendChild(sectionNode);
            });

            var consentLabel = document.createElement("label");
            consentLabel.className = "application-completion-consent";
            var consentBox = document.createElement("input");
            consentBox.type = "checkbox";
            consentBox.checked = state.consent;
            consentBox.required = true;
            consentBox.addEventListener("change", function () { state.consent = consentBox.checked; });
            var consentText = document.createElement("span");
            consentText.textContent = "I agree to share this information with the organization for application review.";
            consentLabel.append(consentBox, consentText);
            form.appendChild(consentLabel);

            var error = document.createElement("p");
            error.className = "application-completion-error";
            error.setAttribute("role", "alert");
            error.hidden = true;
            form.appendChild(error);
            var actions = document.createElement("div");
            actions.className = "application-completion-actions";
            var submitButton = document.createElement("button");
            submitButton.type = "submit";
            submitButton.className = "application-tracker-action application-completion-next";
            submitButton.textContent = "Submit details for review";
            actions.appendChild(submitButton);
            form.appendChild(actions);
        }

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            var validationError = validateForm();
            if (validationError) {
                setVisibleError(form.querySelector(".application-completion-error"), validationError);
                return;
            }
            submitForm();
        });
        renderForm();
        return form;
    }

    function render() {
        var filtered = activeFilter === "all" ? applications : applications.filter(function (application) {
            return categoryFor(application) === activeFilter;
        });
        list.replaceChildren();
        if (!filtered.length) {
            var empty = document.createElement("p");
            empty.className = "application-tracker-empty";
            empty.textContent = "There are no applications in this category.";
            list.appendChild(empty);
            return;
        }
        filtered.forEach(function (application, index) {
            var card = document.createElement("article");
            card.className = "application-tracker-card";
            card.style.animationDelay = Math.min(index * 45, 225) + "ms";
            var content = document.createElement("div");
            var title = document.createElement("h3");
            title.textContent = application.roleLabel + " · " + application.trackLabel;
            var date = document.createElement("time");
            date.className = "application-tracker-date";
            date.dateTime = application.submittedAt;
            date.textContent = "Submitted " + application.submittedAt;
            content.append(title, date);
            var status = document.createElement("span");
            status.className = "application-tracker-status application-tracker-status-" + application.status;
            status.textContent = application.statusLabel;
            card.append(content, status);

            if (!application.completionEditable) {
                appendSummaryDetails(card, application.completionValues || {});
                appendReadOnlyDocuments(card, application.completionDocuments || []);
            } else {
                var actions = document.createElement("div");
                actions.className = "application-tracker-card-actions";
                var complete = document.createElement("button");
                complete.type = "button";
                complete.className = "application-tracker-action";
                complete.textContent = "Complete your profile";
                complete.addEventListener("click", function () {
                    complete.disabled = true;
                    complete.textContent = "Form opened";
                    card.appendChild(createApplicationWizard(application, card));
                });
                var hint = document.createElement("p");
                hint.className = "application-tracker-hint";
                hint.textContent = "Add details to improve your chances.";
                actions.append(complete, hint);
                card.appendChild(actions);
            }
            list.appendChild(card);
        });
    }

    function updateDot() {
        var canComplete = applications.some(function (application) { return application.completionEditable; });
        var dot = trigger.querySelector(".application-tracker-dot");
        if (dot) dot.hidden = !canComplete;
    }

    function openModal() {
        lastTrigger = document.activeElement;
        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("application-tracker-open");
        render();
        requestAnimationFrame(function () {
            modal.classList.add("is-open");
            closeButton.focus();
        });
    }

    function closeModal() {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("application-tracker-open");
        window.setTimeout(function () {
            modal.hidden = true;
            if (lastTrigger) lastTrigger.focus();
        }, 180);
    }

    trigger.addEventListener("click", openModal);
    closeButton.addEventListener("click", closeModal);
    modal.addEventListener("click", function (event) {
        if (event.target === modal) closeModal();
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.hidden) closeModal();
    });
    filters.forEach(function (button) {
        button.addEventListener("click", function () {
            activeFilter = button.dataset.applicationFilter;
            filters.forEach(function (filter) {
                var selected = filter === button;
                filter.classList.toggle("active", selected);
                filter.setAttribute("aria-pressed", selected ? "true" : "false");
            });
            render();
        });
    });

    updateDot();
    if (window.lucide && typeof window.lucide.createIcons === "function") window.lucide.createIcons();
}());
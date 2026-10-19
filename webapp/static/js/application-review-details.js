(function () {
    "use strict";

    var dataNode = document.getElementById("pending-beneficiary-applications-data")
        || document.getElementById("pending-volunteer-applications-data");
    var dialog = document.getElementById("role-application-review-dialog");
    var body = document.getElementById("role-application-review-body");
    if (!dataNode || !dialog || !body) return;

    var applications = JSON.parse(dataNode.textContent || "[]");
    var labels = {
        full_name: "Full name", gender: "Gender", birthdate: "Birthdate", civil_status: "Civil status", email: "Email",
        phone: "Phone number", barangay: "Barangay", street_address: "Street address", city: "City",
        availability_days: "Availability days", skills: "Skills", skills_availability: "Skills and availability", reason_for_volunteering: "Reason for volunteering",
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
    var values = {
        male: "Male", female: "Female", other: "Other", prefer_not: "Prefer not to say",
        physical: "Physical disability", visual: "Visual disability", hearing: "Hearing disability",
        speech: "Speech disability", intellectual: "Intellectual disability", psychosocial: "Psychosocial disability",
        multiple: "Multiple disabilities",
        single: "Single", married: "Married", widowed: "Widowed", separated: "Separated",
        national_id: "Philippine National ID", drivers_license: "Driver's license", voters_id: "Voter's ID",
        postal_id: "Postal ID", philhealth_id: "PhilHealth ID", umid: "UMID", passport: "Passport",
        high_school: "High school", college: "College", graduate: "Graduate",
        under_5000: "Below PHP 5,000", "5000_9999": "PHP 5,000-9,999", "10000_14999": "PHP 10,000-14,999",
        "15000_24999": "PHP 15,000-24,999", "25000_plus": "PHP 25,000 or more", no_income: "No household income"
    };

    function fieldLabel(name) {
        return labels[name] || name.replace(/_/g, " ").replace(/\b\w/g, function (character) { return character.toUpperCase(); });
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest("[data-application-review-details]");
        if (!button) return;
        var application = applications.find(function (item) {
            return String(item.id) === button.dataset.applicationReviewDetails;
        });
        if (!application) return;
        body.replaceChildren();
        var row = button.closest("tr");
        var profileCompleteness = application.profileCompleteness || {};
        var isComplete = row
            ? row.dataset.profileCompleteness === "complete"
            : Boolean(profileCompleteness.complete);
        var missingItems = Array.isArray(profileCompleteness.missingItems) ? profileCompleteness.missingItems.slice() : [];
        if (row && row.dataset.profileMissing) {
            try {
                var rowMissingItems = JSON.parse(row.dataset.profileMissing);
                if (Array.isArray(rowMissingItems)) missingItems = rowMissingItems;
            } catch (error) {
                missingItems = [row.dataset.profileMissing];
            }
        }
        var missingSummary = missingItems.slice(0, 3).join(", ");
        if (missingItems.length > 3) missingSummary += ", and " + (missingItems.length - 3) + " more";
        var completenessList = document.createElement("dl");
        var completenessRow = document.createElement("div");
        var completenessLabel = document.createElement("dt");
        var completenessValue = document.createElement("dd");
        completenessLabel.textContent = "Profile completeness";
        completenessValue.textContent = isComplete ? "Complete" : "Missing: " + (missingSummary || "required details or documents");
        completenessRow.append(completenessLabel, completenessValue);
        completenessList.appendChild(completenessRow);
        body.appendChild(completenessList);
        var details = application.applicationDetails || {};
        var addedDetails = application.applicantAddedDetails || {};
        var addedKeys = new Set(Object.keys(addedDetails));
        var entries = Object.entries(details).filter(function (entry) { return entry[1] !== "" && entry[1] != null; });
        if (!entries.length) {
            var empty = document.createElement("p");
            empty.className = "role-application-review-empty";
            empty.textContent = "No application details are available.";
            body.appendChild(empty);
        } else {
            var list = document.createElement("dl");
            entries.forEach(function (entry) {
                var wrapper = document.createElement("div");
                var label = document.createElement("dt");
                var value = document.createElement("dd");
                label.appendChild(document.createTextNode(fieldLabel(entry[0])));
                if (addedKeys.has(entry[0])) {
                    var addedLabel = document.createElement("span");
                    addedLabel.textContent = "Added by applicant";
                    label.appendChild(addedLabel);
                }
                value.textContent = Array.isArray(entry[1])
                    ? entry[1].map(function (item) { return values[item] || String(item); }).join(", ")
                    : values[entry[1]] || String(entry[1]);
                wrapper.append(label, value);
                list.appendChild(wrapper);
            });
            body.appendChild(list);
        }
        var documents = application.applicationDocuments || [];
        if (documents.length) {
            var documentSection = document.createElement("section");
            documentSection.className = "role-application-review-documents";
            var heading = document.createElement("h3");
            heading.textContent = "Documents";
            documentSection.appendChild(heading);
            documents.forEach(function (documentData) {
                var item = document.createElement("article");
                item.className = "role-application-review-document";
                var link = document.createElement("a");
                link.href = documentData.viewUrl;
                link.target = "_blank";
                link.rel = "noopener";
                link.textContent = documentData.label + " · " + documentData.fileName;
                var addedLabel = document.createElement("span");
                addedLabel.className = "application-review-added-label";
                addedLabel.textContent = "Added by applicant";
                item.appendChild(addedLabel);
                item.appendChild(link);
                if (documentData.contentType && documentData.contentType.indexOf("image/") === 0) {
                    var image = document.createElement("img");
                    image.src = documentData.viewUrl;
                    image.alt = documentData.label;
                    image.loading = "lazy";
                    item.appendChild(image);
                } else if (documentData.contentType === "application/pdf") {
                    var preview = document.createElement("iframe");
                    preview.src = documentData.viewUrl;
                    preview.title = documentData.label + " preview";
                    item.appendChild(preview);
                }
                documentSection.appendChild(item);
            });
            body.appendChild(documentSection);
        }
        if (application.detailsConsentGiven) {
            var consent = document.createElement("p");
            consent.className = "role-application-review-consent";
            consent.textContent = "Applicant consent recorded for sharing details and documents for review.";
            body.appendChild(consent);
        }
        dialog.showModal();
    });

    dialog.addEventListener("click", function (event) {
        if (event.target.closest("[data-close-application-review]") || event.target === dialog) dialog.close();
    });
}());
if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
}

const menuBtn = document.getElementById("menuBtn");
const mobileNav = document.getElementById("mobileNav");

if (menuBtn && mobileNav) {
    menuBtn.addEventListener("click", function () {
        const isOpen = mobileNav.classList.toggle("open");
        menuBtn.setAttribute("aria-expanded", String(isOpen));
    });

    mobileNav.addEventListener("click", function (event) {
        if (event.target.classList.contains("nav-link")) {
            mobileNav.classList.remove("open");
            menuBtn.setAttribute("aria-expanded", "false");
        }
    });
}

const openSignInModalBtn = document.getElementById("openSignInModal");
const openSignUpModalBtn = document.getElementById("openSignUpModal");
const signInModal = document.getElementById("signinModal");
const signUpModal = document.getElementById("signupModal");
const closeSignInModalBtn = document.getElementById("closeSignInModal");
const closeSignUpModalBtn = document.getElementById("closeSignUpModal");
const switchToSignUpFromSignIn = document.getElementById("switchToSignUpFromSignIn");
const switchToSignInFromSignUp = document.getElementById("switchToSignInFromSignUp");
const modalEmailInput = document.getElementById("id_username_or_email");
const signupModalEmailInput = document.getElementById("id_username");

function showModal(modal, focusEl) {
    if (!modal) {
        return;
    }

    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");

    if (focusEl) {
        focusEl.focus();
    }
}

function hideModal(modal) {
    if (!modal) {
        return;
    }

    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");

    if (
        (!signInModal || !signInModal.classList.contains("open")) &&
        (!signUpModal || !signUpModal.classList.contains("open"))
    ) {
        document.body.classList.remove("modal-open");
    }
}

function openSignInModal() {
    hideModal(signUpModal);
    showModal(signInModal, modalEmailInput);
}

function closeSignInModal() {
    hideModal(signInModal);
}

function openSignUpModal() {
    hideModal(signInModal);
    showModal(signUpModal, signupModalEmailInput);
}

function closeSignUpModal() {
    hideModal(signUpModal);
}

function switchToSignUp(event) {
    event.preventDefault();
    hideModal(signInModal);
    window.setTimeout(openSignUpModal, 100);
}

function switchToSignIn(event) {
    event.preventDefault();
    hideModal(signUpModal);
    window.setTimeout(openSignInModal, 100);
}

if (openSignInModalBtn && signInModal) {
    openSignInModalBtn.addEventListener("click", openSignInModal);
}

if (openSignUpModalBtn && signUpModal) {
    openSignUpModalBtn.addEventListener("click", openSignUpModal);
}

if (closeSignInModalBtn) {
    closeSignInModalBtn.addEventListener("click", closeSignInModal);
}

if (closeSignUpModalBtn) {
    closeSignUpModalBtn.addEventListener("click", closeSignUpModal);
}

if (switchToSignUpFromSignIn) {
    switchToSignUpFromSignIn.addEventListener("click", switchToSignUp);
}

if (switchToSignInFromSignUp) {
    switchToSignInFromSignUp.addEventListener("click", switchToSignIn);
}

if (signInModal) {
    signInModal.addEventListener("click", function (event) {
        if (event.target === signInModal) {
            closeSignInModal();
        }
    });
}

if (signUpModal) {
    signUpModal.addEventListener("click", function (event) {
        if (event.target === signUpModal) {
            closeSignUpModal();
        }
    });
}

document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
        return;
    }

    if (signInModal && signInModal.classList.contains("open")) {
        closeSignInModal();
    }

    if (signUpModal && signUpModal.classList.contains("open")) {
        closeSignUpModal();
    }
});

function initProductFilters() {
    const categoryButtons = document.querySelectorAll("[data-category-btn]");
    const productCards = document.querySelectorAll(".product-card[data-category]");
    const productsToolbar = document.querySelector(".products-toolbar");
    const productsEmpty = document.getElementById("productsEmpty");

    if (!categoryButtons.length || !productCards.length) {
        return;
    }

    function applyCategoryFilter(category) {
        let visibleCount = 0;

        productCards.forEach(function (card) {
            const matches = category === "all" || card.dataset.category === category;
            card.classList.toggle("is-hidden", !matches);

            if (matches) {
                visibleCount += 1;
            }
        });

        if (productsEmpty) {
            productsEmpty.hidden = visibleCount > 0;
        }
    }

    function setActiveButton(selectedButton) {
        categoryButtons.forEach(function (btn) {
            const isActive = btn === selectedButton;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-pressed", String(isActive));
        });
    }

    function handleFilterButton(button) {
        const selectedCategory = button.dataset.categoryBtn || "all";
        setActiveButton(button);
        applyCategoryFilter(selectedCategory);
    }

    if (productsToolbar) {
        productsToolbar.addEventListener("click", function (event) {
            const button = event.target.closest("[data-category-btn]");

            if (!button) {
                return;
            }

            handleFilterButton(button);
        });
    }

    categoryButtons.forEach(function (button) {
        button.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                handleFilterButton(button);
            }
        });
    });

    const initialActive = document.querySelector("[data-category-btn].active") || categoryButtons[0];
    handleFilterButton(initialActive);
}

function initContactHub() {
    const hub = document.getElementById("contactHub");

    if (!hub) {
        return;
    }

    const pathButtons = hub.querySelectorAll("[data-contact-path]");
    const panels = hub.querySelectorAll("[data-contact-panel]");
    const backToPathButtons = hub.querySelectorAll("[data-path-home]");

    function setActivePath(path) {
        const resolvedPath = path || "";

        const isDetailMode = Boolean(resolvedPath);
        hub.classList.toggle("detail-mode", isDetailMode);
        hub.classList.toggle("matrix-mode", !isDetailMode);

        pathButtons.forEach(function (button) {
            const isActive = button.dataset.contactPath === resolvedPath;
            button.classList.toggle("active", isActive);
            button.setAttribute("aria-pressed", String(isActive));
        });

        panels.forEach(function (panel) {
            panel.classList.toggle("active", panel.dataset.contactPanel === resolvedPath);
        });

        if (resolvedPath === "form") {
            resetFormToFlowChoice();
        }
    }

    pathButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            setActivePath(button.dataset.contactPath || "chat");
        });
    });

    backToPathButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            setActivePath("");
            const firstCard = pathButtons[0];

            if (firstCard) {
                firstCard.focus();
            }
        });
    });

    const chatMessages = document.getElementById("contactChatMessages");
    const chatForm = document.getElementById("contactChatForm");
    const chatInput = document.getElementById("contactChatInput");
    const typingIndicator = document.getElementById("contactTyping");

    function appendChatMessage(sender, text, suggestedAction) {
        if (!chatMessages) {
            return;
        }

        const bubble = document.createElement("article");
        bubble.className = "chat-bubble " + sender;

        if (sender === "bot") {
            const avatar = document.createElement("div");
            avatar.className = "chat-avatar";
            avatar.innerHTML = "<i data-lucide=\"bot\"></i>";
            bubble.appendChild(avatar);
        }

        const body = document.createElement("div");
        body.className = "chat-body";
        const textNode = document.createElement("p");
        textNode.textContent = text;
        body.appendChild(textNode);

        if (suggestedAction) {
            const suggestRow = document.createElement("div");
            suggestRow.className = "chat-suggest-row";
            const suggestButton = document.createElement("button");
            suggestButton.type = "button";
            suggestButton.className = "chat-suggest-btn";
            suggestButton.dataset.chatActionPath = suggestedAction.path;
            suggestButton.textContent = suggestedAction.label;
            suggestRow.appendChild(suggestButton);
            body.appendChild(suggestRow);
        }

        bubble.appendChild(body);
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function detectIntent(message) {
        const lowerMessage = message.toLowerCase();

        if (
            lowerMessage.includes("price") ||
            lowerMessage.includes("pricing") ||
            lowerMessage.includes("cost") ||
            lowerMessage.includes("quote")
        ) {
            return "pricing";
        }

        if (
            lowerMessage.includes("demo") ||
            lowerMessage.includes("meeting") ||
            lowerMessage.includes("call") ||
            lowerMessage.includes("schedule") ||
            lowerMessage.includes("book") ||
            lowerMessage.includes("calendar")
        ) {
            return "calendar";
        }

        return null;
    }

    function getBotReply(message) {
        const intent = detectIntent(message);

        if (intent === "pricing") {
            return {
                text: "For accurate pricing, I can get you a specialist. Would you like to grab a 15-minute slot on our calendar right now?",
                suggestedAction: {
                    label: "Open Calendar",
                    path: "calendar",
                },
            };
        }

        if (intent === "calendar") {
            return {
                text: "That sounds like something we should discuss in detail. Want to hop on a quick call? I can show you available times.",
                suggestedAction: {
                    label: "Book a Call",
                    path: "calendar",
                },
            };
        }

        return {
            text: "I can help with that. If you want instant scheduling, choose the calendar path. If you prefer structured details, the 2-minute form works great.",
            suggestedAction: {
                label: "Open 2-Min Form",
                path: "form",
            },
        };
    }

    if (chatMessages) {
        chatMessages.addEventListener("click", function (event) {
            const actionButton = event.target.closest("[data-chat-action-path]");

            if (!actionButton) {
                return;
            }

            setActivePath(actionButton.dataset.chatActionPath || "chat");
        });
    }

    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", function (event) {
            event.preventDefault();

            const message = chatInput.value.trim();
            if (!message) {
                return;
            }

            appendChatMessage("user", message);
            chatInput.value = "";

            if (typingIndicator) {
                typingIndicator.hidden = false;
            }

            window.setTimeout(function () {
                if (typingIndicator) {
                    typingIndicator.hidden = true;
                }

                const reply = getBotReply(message);
                appendChatMessage("bot", reply.text, reply.suggestedAction);
            }, 800);
        });
    }

    const dateListEl = document.getElementById("contactDateList");
    const timeSlotsEl = document.getElementById("contactTimeSlots");
    const bookingForm = document.getElementById("contactBookingForm");
    const bookingError = document.getElementById("bookingError");
    const bookingName = document.getElementById("bookingName");
    const bookingEmail = document.getElementById("bookingEmail");
    const calendarBody = document.getElementById("calendarBookingBody");
    const calendarSuccess = document.getElementById("calendarSuccess");
    const calendarSuccessEmail = document.getElementById("calendarSuccessEmail");
    const calendarSuccessDetails = document.getElementById("calendarSuccessDetails");
    const confirmBookingBtn = document.getElementById("confirmBookingBtn");
    const calProgressFill = document.getElementById("calProgressFill");

    const availableDates = [
        { id: "1", date: "Mar 10", dayOfWeek: "Mon", slotsAvailable: 4 },
        { id: "2", date: "Mar 11", dayOfWeek: "Tue", slotsAvailable: 4 },
        { id: "3", date: "Mar 12", dayOfWeek: "Wed", slotsAvailable: 3 },
        { id: "4", date: "Mar 13", dayOfWeek: "Thu", slotsAvailable: 5 },
        { id: "5", date: "Mar 14", dayOfWeek: "Fri", slotsAvailable: 2 },
    ];

    const timeSlotsByDate = {
        "1": [
            { id: "t1", time: "9:00 AM", available: true },
            { id: "t2", time: "10:30 AM", available: true },
            { id: "t3", time: "1:00 PM", available: true },
            { id: "t4", time: "3:30 PM", available: true },
        ],
        "2": [
            { id: "t5", time: "9:30 AM", available: true },
            { id: "t6", time: "11:00 AM", available: true },
            { id: "t7", time: "2:00 PM", available: true },
            { id: "t8", time: "4:00 PM", available: true },
        ],
        "3": [
            { id: "t9", time: "10:00 AM", available: true },
            { id: "t10", time: "12:30 PM", available: true },
            { id: "t11", time: "3:00 PM", available: true },
        ],
        "4": [
            { id: "t12", time: "8:30 AM", available: true },
            { id: "t13", time: "10:00 AM", available: true },
            { id: "t14", time: "11:30 AM", available: true },
            { id: "t15", time: "2:30 PM", available: true },
            { id: "t16", time: "4:30 PM", available: true },
        ],
        "5": [
            { id: "t17", time: "9:00 AM", available: true },
            { id: "t18", time: "1:30 PM", available: true },
        ],
    };

    let selectedDateId = availableDates[0].id;
    let selectedSlotId = timeSlotsByDate[selectedDateId][0].id;

    function updateCalendarProgress() {
        let progress = 0;

        if (selectedDateId) {
            progress += 35;
        }

        if (selectedSlotId) {
            progress += 30;
        }

        if (
            bookingName &&
            bookingEmail &&
            bookingName.value.trim() &&
            bookingEmail.value.trim().includes("@")
        ) {
            progress += 35;
        }

        if (calProgressFill) {
            calProgressFill.style.width = String(progress) + "%";
        }
    }

    function renderDates() {
        if (!dateListEl) {
            return;
        }

        dateListEl.innerHTML = "";

        availableDates.forEach(function (dateSlot) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "cal-item-btn" + (dateSlot.id === selectedDateId ? " active" : "");
            button.innerHTML =
                "<span>" +
                dateSlot.dayOfWeek +
                " · " +
                dateSlot.date +
                "</span><small>" +
                String(dateSlot.slotsAvailable) +
                " slots</small>";

            button.addEventListener("click", function () {
                selectedDateId = dateSlot.id;
                const firstAvailable = (timeSlotsByDate[selectedDateId] || []).find(function (slot) {
                    return slot.available;
                });
                selectedSlotId = firstAvailable ? firstAvailable.id : "";
                renderDates();
                renderTimeSlots();
                updateCalendarProgress();
            });

            dateListEl.appendChild(button);
        });
    }

    function renderTimeSlots() {
        if (!timeSlotsEl) {
            return;
        }

        const slots = timeSlotsByDate[selectedDateId] || [];
        timeSlotsEl.innerHTML = "";

        slots.forEach(function (slot) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "cal-item-btn" + (slot.id === selectedSlotId ? " active" : "");
            button.textContent = slot.time + " (15 min)";
            button.disabled = !slot.available;

            if (!slot.available) {
                button.style.opacity = "0.6";
                button.style.cursor = "not-allowed";
            }

            button.addEventListener("click", function () {
                if (!slot.available) {
                    return;
                }

                selectedSlotId = slot.id;
                renderTimeSlots();
                updateCalendarProgress();
            });

            timeSlotsEl.appendChild(button);
        });
    }

    if (bookingName) {
        bookingName.addEventListener("input", updateCalendarProgress);
    }

    if (bookingEmail) {
        bookingEmail.addEventListener("input", updateCalendarProgress);
    }

    if (bookingForm) {
        bookingForm.addEventListener("submit", function (event) {
            event.preventDefault();

            const name = bookingName ? bookingName.value.trim() : "";
            const email = bookingEmail ? bookingEmail.value.trim() : "";

            if (bookingError) {
                bookingError.hidden = true;
                bookingError.textContent = "";
            }

            if (!selectedDateId || !selectedSlotId) {
                if (bookingError) {
                    bookingError.hidden = false;
                    bookingError.textContent = "Choose a date and time slot first.";
                }
                return;
            }

            if (!name) {
                if (bookingError) {
                    bookingError.hidden = false;
                    bookingError.textContent = "Name is required.";
                }
                return;
            }

            if (!email || !email.includes("@")) {
                if (bookingError) {
                    bookingError.hidden = false;
                    bookingError.textContent = "Enter a valid email address.";
                }
                return;
            }

            if (confirmBookingBtn) {
                confirmBookingBtn.disabled = true;
                confirmBookingBtn.textContent = "Booking...";
            }

            window.setTimeout(function () {
                const dateObj = availableDates.find(function (dateSlot) {
                    return dateSlot.id === selectedDateId;
                });
                const slotObj = (timeSlotsByDate[selectedDateId] || []).find(function (slot) {
                    return slot.id === selectedSlotId;
                });

                const payload = {
                    event: "booking.created",
                    data: {
                        attendee: { name: name, email: email },
                        date: {
                            date: dateObj ? dateObj.date : "",
                            dayOfWeek: dateObj ? dateObj.dayOfWeek : "",
                        },
                        timeSlot: {
                            time: slotObj ? slotObj.time : "",
                        },
                        timestamp: new Date().toISOString(),
                    },
                };

                console.log("ContactHubWebhook", payload);

                if (calendarBody) {
                    calendarBody.hidden = true;
                }

                if (calendarSuccess) {
                    calendarSuccess.hidden = false;
                }

                if (calendarSuccessEmail) {
                    calendarSuccessEmail.textContent = email;
                }

                if (calendarSuccessDetails && dateObj && slotObj) {
                    calendarSuccessDetails.textContent =
                        dateObj.dayOfWeek + ", " + dateObj.date + " at " + slotObj.time;
                }

                if (confirmBookingBtn) {
                    confirmBookingBtn.disabled = false;
                    confirmBookingBtn.textContent = "Confirm Booking";
                }

                window.setTimeout(function () {
                    if (calendarBody) {
                        calendarBody.hidden = false;
                    }

                    if (calendarSuccess) {
                        calendarSuccess.hidden = true;
                    }

                    setActivePath("");
                }, 3000);
            }, 1500);
        });
    }

    renderDates();
    renderTimeSlots();
    updateCalendarProgress();

    const flowPicker = document.getElementById("flowPicker");
    const formPanel = hub.querySelector("[data-contact-panel='form']");
    const flowOptionButtons = hub.querySelectorAll("[data-flow]");
    const conversationForm = document.getElementById("contactConversationForm");
    const formPrompt = document.getElementById("formPrompt");
    const formHint = document.getElementById("formHint");
    const formOptions = document.getElementById("formOptions");
    const formTextWrap = document.getElementById("formTextWrap");
    const formTextInput = document.getElementById("formTextInput");
    const formTextAreaWrap = document.getElementById("formTextAreaWrap");
    const formTextArea = document.getElementById("formTextArea");
    const formBackBtn = document.getElementById("formBackBtn");
    const formSkipBtn = document.getElementById("formSkipBtn");
    const formNextBtn = document.getElementById("formNextBtn");
    const conversationActions = document.getElementById("conversationActions");
    const formProgressFill = document.getElementById("formProgressFill");
    const formProgressText = document.getElementById("formProgressText");
    const formSuccess = document.getElementById("formSuccess");

    const STORAGE_DATA_KEY = "contactHub_formData";
    const STORAGE_STEP_KEY = "contactHub_formStep";
    const STORAGE_FLOW_KEY = "contactHub_formFlow";

    const projectSteps = [
        {
            key: "projectType",
            prompt: "What type of project?",
            hint: "Choose the closest match.",
            type: "options",
            options: [
                "Product Design",
                "Web Development",
                "Mobile App",
                "Brand & Strategy",
                "Consulting",
                "Other",
            ],
        },
        {
            key: "budget",
            prompt: "What budget range are you considering?",
            hint: "A rough range helps us suggest the right scope.",
            type: "options",
            options: ["Under $10K", "$10K-$50K", "$50K-$100K", "$100K+", "Not sure yet"],
        },
        {
            key: "timeline",
            prompt: "What is your preferred timeline?",
            hint: "We can tailor team setup based on urgency.",
            type: "options",
            options: ["ASAP", "1-3 months", "3-6 months", "6+ months", "Flexible"],
        },
        {
            key: "details",
            prompt: "Tell us about the project details",
            hint: "Share goals, constraints, and any must-haves.",
            type: "textarea",
        },
        {
            key: "email",
            prompt: "What email should we reply to?",
            hint: "We will send a response in about 2 hours.",
            type: "text",
            inputType: "email",
        },
    ];

    const supportSteps = [
        {
            key: "productName",
            prompt: "Which product or service is this about?",
            hint: "This helps route your request to the right team.",
            type: "text",
            inputType: "text",
        },
        {
            key: "orderId",
            prompt: "Order or project ID",
            hint: "Optional, but useful for faster lookup.",
            type: "text",
            inputType: "text",
            optional: true,
        },
        {
            key: "issue",
            prompt: "Describe the issue",
            hint: "Include context and what you expected to happen.",
            type: "textarea",
        },
        {
            key: "email",
            prompt: "What email should we reply to?",
            hint: "We will send a response in about 2 hours.",
            type: "text",
            inputType: "email",
        },
    ];

    let formState = {
        flow: null,
        step: 0,
        answers: {},
    };

    function getCurrentSteps() {
        if (formState.flow === "project") {
            return projectSteps;
        }

        if (formState.flow === "support") {
            return supportSteps;
        }

        return [];
    }

    function saveFormState() {
        localStorage.setItem(STORAGE_DATA_KEY, JSON.stringify(formState.answers));
        localStorage.setItem(STORAGE_STEP_KEY, String(formState.step));
        localStorage.setItem(STORAGE_FLOW_KEY, formState.flow || "");
    }

    function clearFormState() {
        localStorage.removeItem(STORAGE_DATA_KEY);
        localStorage.removeItem(STORAGE_STEP_KEY);
        localStorage.removeItem(STORAGE_FLOW_KEY);
    }

    function loadFormState() {
        try {
            const storedAnswers = localStorage.getItem(STORAGE_DATA_KEY);
            const storedStep = localStorage.getItem(STORAGE_STEP_KEY);
            const storedFlow = localStorage.getItem(STORAGE_FLOW_KEY);

            if (storedAnswers) {
                formState.answers = JSON.parse(storedAnswers) || {};
            }

            if (storedFlow === "project" || storedFlow === "support") {
                formState.flow = storedFlow;
            }

            if (storedStep && Number.isInteger(Number(storedStep))) {
                formState.step = Number(storedStep);
            }
        } catch (_error) {
            formState = {
                flow: null,
                step: 0,
                answers: {},
            };
        }
    }

    function updateFormProgress() {
        const steps = getCurrentSteps();
        const total = steps.length || 1;
        const current = Math.min(formState.step + 1, total);
        const percent = Math.round((current / total) * 100);

        if (formProgressFill) {
            formProgressFill.style.width = String(percent) + "%";
        }

        if (formProgressText) {
            formProgressText.textContent = "Step " + String(current) + " of " + String(total);
        }
    }

    function showFlowPicker() {
        if (formPanel) {
            formPanel.classList.add("form-awaiting-choice");
        }

        if (flowPicker) {
            flowPicker.hidden = false;
        }

        if (conversationForm) {
            conversationForm.hidden = true;
        }

        if (conversationActions) {
            conversationActions.hidden = true;
        }

        if (formSuccess) {
            formSuccess.hidden = true;
        }
    }

    function resetFormToFlowChoice() {
        formState.flow = null;
        formState.step = 0;
        clearFormState();
        showFlowPicker();
        updateFormProgress();
    }

    function showConversationForm() {
        if (formPanel) {
            formPanel.classList.remove("form-awaiting-choice");
        }

        if (flowPicker) {
            flowPicker.hidden = true;
        }

        if (conversationForm) {
            conversationForm.hidden = false;
        }

        if (conversationActions) {
            conversationActions.hidden = !(formState.flow === "project" || formState.flow === "support");
        }

        if (formSuccess) {
            formSuccess.hidden = true;
        }
    }

    function renderQuestion() {
        const steps = getCurrentSteps();
        const stepConfig = steps[formState.step];

        if (!stepConfig || !conversationForm) {
            return;
        }

        showConversationForm();
        updateFormProgress();

        if (conversationActions) {
            conversationActions.hidden = false;
        }

        if (formPrompt) {
            formPrompt.textContent = stepConfig.prompt;
        }

        if (formHint) {
            formHint.textContent = stepConfig.hint;
        }

        if (formOptions) {
            formOptions.innerHTML = "";
            formOptions.hidden = stepConfig.type !== "options";
        }

        if (formTextWrap) {
            formTextWrap.hidden = stepConfig.type !== "text";
        }

        if (formTextAreaWrap) {
            formTextAreaWrap.hidden = stepConfig.type !== "textarea";
        }

        if (formSkipBtn) {
            formSkipBtn.hidden = !stepConfig.optional;
        }

        const answer = formState.answers[stepConfig.key] || "";

        if (stepConfig.type === "options" && formOptions) {
            stepConfig.options.forEach(function (optionValue) {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "form-option-btn" + (answer === optionValue ? " active" : "");
                button.textContent = optionValue;

                button.addEventListener("click", function () {
                    formState.answers[stepConfig.key] = optionValue;
                    saveFormState();
                    renderQuestion();
                });

                formOptions.appendChild(button);
            });
        }

        if (stepConfig.type === "text" && formTextInput) {
            formTextInput.type = stepConfig.inputType || "text";
            formTextInput.value = answer;
            formTextInput.placeholder = stepConfig.inputType === "email" ? "you@example.com" : "Type your answer";
        }

        if (stepConfig.type === "textarea" && formTextArea) {
            formTextArea.value = answer;
        }

        if (formNextBtn) {
            formNextBtn.textContent = formState.step === steps.length - 1 ? "Submit" : "Next";
        }

        if (formBackBtn) {
            formBackBtn.textContent = formState.step === 0 ? "Change Flow" : "Back";
        }
    }

    function validateCurrentStep() {
        const steps = getCurrentSteps();
        const stepConfig = steps[formState.step];

        if (!stepConfig) {
            return false;
        }

        const currentValue = (formState.answers[stepConfig.key] || "").toString().trim();

        if (stepConfig.optional && currentValue.length === 0) {
            return true;
        }

        if (currentValue.length === 0) {
            return false;
        }

        if (stepConfig.inputType === "email" && !currentValue.includes("@")) {
            return false;
        }

        return true;
    }

    function completeFormFlow() {
        if (conversationForm) {
            conversationForm.hidden = true;
        }

        if (formSuccess) {
            formSuccess.hidden = false;
        }

        clearFormState();
    }

    flowOptionButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            formState.flow = button.dataset.flow;
            formState.step = 0;
            saveFormState();
            renderQuestion();
        });
    });

    if (formTextInput) {
        formTextInput.addEventListener("input", function () {
            const steps = getCurrentSteps();
            const stepConfig = steps[formState.step];

            if (!stepConfig) {
                return;
            }

            formState.answers[stepConfig.key] = formTextInput.value;
            saveFormState();
        });
    }

    if (formTextArea) {
        formTextArea.addEventListener("input", function () {
            const steps = getCurrentSteps();
            const stepConfig = steps[formState.step];

            if (!stepConfig) {
                return;
            }

            formState.answers[stepConfig.key] = formTextArea.value;
            saveFormState();
        });
    }

    if (formBackBtn) {
        formBackBtn.addEventListener("click", function () {
            if (formState.step === 0) {
                formState.flow = null;
                formState.step = 0;
                saveFormState();
                showFlowPicker();
                updateFormProgress();
                return;
            }

            formState.step -= 1;
            saveFormState();
            renderQuestion();
        });
    }

    if (formSkipBtn) {
        formSkipBtn.addEventListener("click", function () {
            const steps = getCurrentSteps();
            if (!steps.length) {
                return;
            }

            if (formState.step >= steps.length - 1) {
                completeFormFlow();
                return;
            }

            formState.step += 1;
            saveFormState();
            renderQuestion();
        });
    }

    if (conversationForm) {
        conversationForm.addEventListener("submit", function (event) {
            event.preventDefault();

            const steps = getCurrentSteps();
            const stepConfig = steps[formState.step];

            if (!stepConfig) {
                return;
            }

            if (stepConfig.type === "text" && formTextInput) {
                formState.answers[stepConfig.key] = formTextInput.value;
            }

            if (stepConfig.type === "textarea" && formTextArea) {
                formState.answers[stepConfig.key] = formTextArea.value;
            }

            if (!validateCurrentStep()) {
                if (formHint) {
                    formHint.textContent = stepConfig.inputType === "email"
                        ? "Please enter a valid email address to continue."
                        : "Please provide an answer to continue.";
                }
                return;
            }

            if (formState.step >= steps.length - 1) {
                console.log("ContactHubFormSubmission", {
                    flow: formState.flow,
                    answers: formState.answers,
                    timestamp: new Date().toISOString(),
                });
                completeFormFlow();
                return;
            }

            formState.step += 1;
            saveFormState();
            renderQuestion();
        });
    }

    // Require explicit path choice every time before showing step controls.
    resetFormToFlowChoice();

    setActivePath("");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
        initProductFilters();
        initContactHub();
    });
} else {
    initProductFilters();
    initContactHub();
}

(function () {
    function initSidebarCollapseToggles() {
        const shell = document.getElementById("dashboard-shell");
        if (!shell) {
            return;
        }

        const headerToggle = document.getElementById("header-sidebar-toggle");
        const mobileToggle = document.getElementById("sidebar-toggle-mobile");
        const inlineToggle = document.getElementById("sidebar-toggle-inline");
        const collapseToggles = [headerToggle, mobileToggle, inlineToggle].filter(Boolean);

        if (!collapseToggles.length) {
            return;
        }

        function syncToggleState(isCollapsed) {
            collapseToggles.forEach(function (toggle) {
                toggle.setAttribute("aria-expanded", String(!isCollapsed));
                toggle.setAttribute("data-collapsed", String(isCollapsed));
            });
        }

        syncToggleState(shell.getAttribute("data-sidebar") === "collapsed");

        collapseToggles.forEach(function (toggle) {
            toggle.addEventListener("click", function (event) {
                event.stopPropagation();
                const isCollapsed = shell.getAttribute("data-sidebar") === "collapsed";
                const nextCollapsed = !isCollapsed;
                shell.setAttribute("data-sidebar", nextCollapsed ? "collapsed" : "expanded");
                syncToggleState(nextCollapsed);
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSidebarCollapseToggles);
    } else {
        initSidebarCollapseToggles();
    }
})();

(function () {
    function positionPanel(btn, panel, opts = { preferred: "bottom-right", padding: 8 }) {
        if (!btn || !panel) return;
        const padding = opts.padding;
        const rect = btn.getBoundingClientRect();
        const vw = document.documentElement.clientWidth;
        const vh = document.documentElement.clientHeight;

        // ensure panel measured size (render briefly if hidden)
        panel.style.left = "0px";
        panel.style.top = "0px";
        panel.style.display = "block";
        panel.style.visibility = "hidden";
        const pw = panel.offsetWidth;
        const ph = panel.offsetHeight;
        panel.style.visibility = "";
        panel.style.display = "";

        // candidate placements (preferred bottom-right first)
        const candidates = [
            { left: rect.right - pw, top: rect.bottom + padding, origin: "top right" }, // bottom-right
            { left: rect.left, top: rect.bottom + padding, origin: "top left" }, // bottom-left
            { left: rect.right - pw, top: rect.top - ph - padding, origin: "bottom right" }, // top-right
            { left: rect.left, top: rect.top - ph - padding, origin: "bottom left" }, // top-left
        ];

        // pick first that fits fully inside viewport with padding
        let chosen = candidates.find(function (c) {
            return c.left >= padding
                && c.left + pw <= vw - padding
                && c.top >= padding
                && c.top + ph <= vh - padding;
        });

        // if none fit entirely, pick the candidate with largest visible area, then clamp
        if (!chosen) {
            let best = null;
            let bestArea = -1;
            candidates.forEach(function (c) {
                const visibleW = Math.max(0, Math.min(vw - padding, c.left + pw) - Math.max(padding, c.left));
                const visibleH = Math.max(0, Math.min(vh - padding, c.top + ph) - Math.max(padding, c.top));
                const area = visibleW * visibleH;
                if (area > bestArea) {
                    bestArea = area;
                    best = c;
                }
            });
            chosen = best || candidates[0];
            chosen.left = Math.min(Math.max(chosen.left, padding), Math.max(padding, vw - pw - padding));
            chosen.top = Math.min(Math.max(chosen.top, padding), Math.max(padding, vh - ph - padding));
        }

        // apply position and transform origin (account for page scroll)
        panel.style.left = `${Math.round(chosen.left + window.scrollX)}px`;
        panel.style.top = `${Math.round(chosen.top + window.scrollY)}px`;
        panel.style.transformOrigin = chosen.origin;
    }

    function setupDropdown(triggerId, panelId) {
        const btn = document.getElementById(triggerId);
        const panel = document.getElementById(panelId);
        if (!btn || !panel) return null;

        if (panel.parentElement !== document.body) {
            document.body.appendChild(panel);
        }

        let lastFocused = null;

        function closePanel(targetPanel) {
            if (!targetPanel) return;
            const selector = `[aria-controls="${targetPanel.id}"]`;
            const targetButton = document.querySelector(selector);
            targetPanel.setAttribute("data-open", "false");
            if (targetButton) {
                targetButton.setAttribute("aria-expanded", "false");
            }
            window.setTimeout(function () {
                targetPanel.hidden = true;
            }, 200);
        }

        function open() {
            document.querySelectorAll('.dropdown-card[data-open="true"]').forEach(function (openPanel) {
                if (openPanel !== panel) {
                    closePanel(openPanel);
                }
            });

            lastFocused = document.activeElement;
            panel.hidden = false;
            panel.setAttribute("data-open", "true");
            btn.setAttribute("aria-expanded", "true");
            positionPanel(btn, panel);

            const first = panel.querySelector("a, button, [role='menuitem']");
            if (first) {
                first.focus();
            }
        }

        function close(restoreFocus) {
            panel.setAttribute("data-open", "false");
            btn.setAttribute("aria-expanded", "false");
            window.setTimeout(function () {
                panel.hidden = true;
            }, 200);
            if (restoreFocus && lastFocused && typeof lastFocused.focus === "function") {
                lastFocused.focus();
            }
        }

        function toggle() {
            if (panel.getAttribute("data-open") === "true") {
                close(false);
            } else {
                open();
            }
        }

        btn.addEventListener("click", function (event) {
            event.stopPropagation();
            toggle();
        });

        document.addEventListener("click", function (event) {
            if (!panel.contains(event.target) && !btn.contains(event.target)) {
                close(false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                close(true);
            }
        });

        window.addEventListener("resize", function () {
            if (panel.getAttribute("data-open") === "true") {
                positionPanel(btn, panel);
            }
        });

        window.addEventListener("scroll", function () {
            if (panel.getAttribute("data-open") === "true") {
                positionPanel(btn, panel);
            }
        }, { passive: true });

        return {
            close: close,
            open: open,
        };
    }

    function syncNotificationCount() {
        const trigger = document.getElementById("header-notifications");
        const countNode = document.getElementById("notif-count");
        const list = document.getElementById("notif-list");
        if (!trigger || !countNode || !list) {
            return;
        }

        const unread = list.querySelectorAll(".notif-item.unread").length;
        const resolvedCount = Number.isFinite(unread) ? unread : 0;
        trigger.setAttribute("data-notifications", String(resolvedCount));
        countNode.textContent = String(resolvedCount);

        const badge = trigger.querySelector("span.absolute");
        if (badge) {
            badge.textContent = String(resolvedCount);
        }
    }

    function initDropdownCards() {
        const notifications = setupDropdown("header-notifications", "dropdown-notifications");
        const profile = setupDropdown("header-profile", "dropdown-profile");
        syncNotificationCount();

        const markAllRead = document.getElementById("mark-all-read");
        const notifList = document.getElementById("notif-list");

        if (markAllRead && notifList) {
            markAllRead.addEventListener("click", function () {
                notifList.querySelectorAll(".notif-item.unread").forEach(function (item) {
                    item.classList.remove("unread");
                });
                syncNotificationCount();
            });
        }

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                if (notifications) {
                    notifications.close(false);
                }
                if (profile) {
                    profile.close(false);
                }
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initDropdownCards);
    } else {
        initDropdownCards();
    }
})();

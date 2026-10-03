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
const signInModalTitle = document.getElementById("signinDialogTitle");
const signInModalDescription = document.getElementById("signinDialogDescription");
const signInNextInput = document.getElementById("signInNext");
const defaultSignInModalTitle = signInModalTitle ? signInModalTitle.textContent.trim() : "";
const defaultSignInModalDescription = signInModalDescription ? signInModalDescription.textContent.trim() : "";
const signInFirstModalTitle = "Sign in First!";
const signInFirstModalDescription = "You must sign in first before applying..";
const productSignInModalDescription = "You must sign in first before viewing product details.";
let signInModalSource = "default";

function setSignInModalContent(source) {
    if (!signInModalTitle || !signInModalDescription) {
        return;
    }

    if (source === "application") {
        signInModalTitle.textContent = signInFirstModalTitle;
        signInModalDescription.textContent = signInFirstModalDescription;
    } else if (source === "product") {
        signInModalTitle.textContent = signInFirstModalTitle;
        signInModalDescription.textContent = productSignInModalDescription;
    } else {
        signInModalTitle.textContent = defaultSignInModalTitle;
        signInModalDescription.textContent = defaultSignInModalDescription;
    }
}

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

function openSignInModal(sourceOrEvent) {
    if (sourceOrEvent === "application" || sourceOrEvent === "product") {
        signInModalSource = sourceOrEvent;
    } else {
        signInModalSource = "default";
    }
    hideModal(signUpModal);
    setSignInModalContent(signInModalSource);
    showModal(signInModal, modalEmailInput);
}

function closeSignInModal() {
    hideModal(signInModal);
    signInModalSource = "default";
    if (signInNextInput) {
        signInNextInput.value = "";
    }
    setSignInModalContent(signInModalSource);
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
    window.setTimeout(function () {
        openSignInModal(signInModalSource);
    }, 100);
}

window.openSignInModal = openSignInModal;

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

function initModalAnimations() {
    if (!window.lottie || typeof window.lottie.loadAnimation !== "function") {
        return;
    }

    const modalAnimationElements = document.querySelectorAll("[data-lottie-path]");

    modalAnimationElements.forEach(function (element) {
        if (element.dataset.lottieInitialized === "true") {
            return;
        }

        const animationPath = element.dataset.lottiePath;
        if (!animationPath) {
            return;
        }

        const isCardAnimation = element.classList.contains("apply-lottie");
        const shouldLoop = isCardAnimation;

        window.lottie.loadAnimation({
            container: element,
            renderer: "svg",
            loop: shouldLoop,
            autoplay: true,
            path: animationPath,
        });

        element.dataset.lottieInitialized = "true";
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initModalAnimations, { once: true });
} else {
    initModalAnimations();
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

function initReceiptModal() {
    const overlay = document.getElementById("orderReceiptModal");
    const closeButton = document.getElementById("closeOrderReceipt");
    const printButton = document.getElementById("printOrderReceipt");
    const items = document.getElementById("receiptItems");
    const receiptPaper = document.getElementById("orderReceiptPaper");

    if (!overlay || !closeButton || !printButton || !items || !receiptPaper) {
        return;
    }

    function closeReceipt() {
        overlay.hidden = true;
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open", "receipt-printing");
    }

    function downloadReceipt(orderNumber) {
        if (typeof window.html2pdf !== "function") {
            window.alert("Receipt download is temporarily unavailable. Please try again.");
            return;
        }

        const paperWidth = Math.ceil(receiptPaper.getBoundingClientRect().width);
        const paperHeight = Math.ceil(receiptPaper.getBoundingClientRect().height);
        const safeOrderNumber = String(orderNumber || "receipt").replace(/[^a-z0-9_-]/gi, "-");
        const options = {
            margin: 0,
            filename: `Receipt-${safeOrderNumber}.pdf`,
            image: { type: "jpeg", quality: 0.98 },
            html2canvas: {
                scale: 2,
                useCORS: true,
                backgroundColor: "#ffffff",
                width: paperWidth,
                height: paperHeight,
                scrollX: 0,
                scrollY: 0,
            },
            jsPDF: {
                unit: "px",
                format: [paperWidth, paperHeight],
                orientation: "portrait",
                hotfixes: ["px_scaling"],
            },
            pagebreak: { mode: ["avoid-all"] },
        };

        printButton.disabled = true;
        const originalLabel = printButton.lastChild;
        if (originalLabel) {
            originalLabel.textContent = " Downloading...";
        }
        window.html2pdf()
            .set(options)
            .from(receiptPaper)
            .save()
            .finally(function () {
                printButton.disabled = false;
                if (originalLabel) {
                    originalLabel.textContent = " Download Receipt";
                }
            });
    }

    window.openOrderReceipt = function (order) {
        if (!order) {
            return;
        }

        const formatCurrency = function (amount) {
            return "₱" + Number(amount || 0).toLocaleString("en-PH", { maximumFractionDigits: 0 });
        };
        document.getElementById("receiptOrderNumber").textContent = order.order_number || `ORD-${order.id}`;
        document.getElementById("receiptOrderDate").textContent = order.date || "-";
        document.getElementById("receiptCustomerName").textContent = order.customer_name || "Guest";
        document.getElementById("receiptPaymentMethod").textContent = order.payment_method || "-";
        document.getElementById("receiptPaymentStatus").textContent = order.payment_status || order.status_label || "Pending";
        const receiptSubtotal = Number(order.total || 0);
        const receiptShipping = 50;
        const receiptVat = receiptSubtotal * 0.12;
        const receiptGrandTotal = receiptSubtotal + receiptShipping + receiptVat;
        document.getElementById("receiptSubtotal").textContent = formatCurrency(receiptSubtotal);
        document.getElementById("receiptDeliveryFee").textContent = formatCurrency(receiptShipping);
        document.getElementById("receiptVat").textContent = formatCurrency(receiptVat);
        document.getElementById("receiptTotal").textContent = formatCurrency(receiptGrandTotal);
        items.replaceChildren();
        (order.items || []).forEach(function (item) {
            const row = document.createElement("div");
            row.className = "receipt-item";
            const detail = document.createElement("div");
            const name = document.createElement("strong");
            name.textContent = item.name || "Product";
            detail.appendChild(name);
            if (item.variation) {
                const variation = document.createElement("span");
                variation.textContent = item.variation;
                detail.appendChild(variation);
            }
            const quantity = document.createElement("span");
            quantity.textContent = `Qty ${item.quantity || 0}`;
            const lineTotal = document.createElement("strong");
            lineTotal.textContent = formatCurrency(item.line_total);
            row.append(detail, quantity, lineTotal);
            items.appendChild(row);
        });

        overlay.hidden = false;
        overlay.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        closeButton.focus();
    };

    window.downloadOrderReceipt = downloadReceipt;

    closeButton.addEventListener("click", closeReceipt);
    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) {
            closeReceipt();
        }
    });
    printButton.addEventListener("click", function () {
        downloadReceipt(document.getElementById("receiptOrderNumber").textContent);
    });
}

function initProductDetails() {
    const modal = document.getElementById("productDetailModal");
    const closeButton = document.getElementById("closeProductDetailModal");
    const cards = document.querySelectorAll(".product-card");
    const image = document.getElementById("productDetailImage");
    const category = document.getElementById("productDetailCategory");
    const title = document.getElementById("productDetailTitle");
    const description = document.getElementById("productDetailDescription");
    const variations = document.getElementById("productDetailVariations");
    const variationLabel = document.getElementById("productDetailVariationLabel");
    const variationOptions = document.getElementById("productDetailVariationOptions");
    const quantityValue = document.getElementById("productDetailQuantity");
    const total = document.getElementById("productDetailTotal");
    const decreaseButton = document.getElementById("productDetailDecrease");
    const increaseButton = document.getElementById("productDetailIncrease");
    const stepOne = document.getElementById("productDetailStepOne");
    const stepTwo = document.getElementById("productDetailStepTwo");
    const continueButton = document.getElementById("productDetailContinue");
    const backButton = document.getElementById("productDetailBack");
    const orderForm = document.getElementById("productDetailOrderForm");
    const orderName = document.getElementById("productOrderConfirmedName");
    const orderEmail = document.getElementById("productOrderConfirmedEmail");
    const orderPhone = document.getElementById("productOrderPhone");
    const orderAddress = document.getElementById("productOrderAddress");
    const orderCity = document.getElementById("productOrderCity");
    const orderFullName = document.getElementById("productOrderFullName");
    const orderEmailField = document.getElementById("productOrderEmail");
    const confirmedCard = document.getElementById("productOrderConfirmedCard");
    const editButton = document.getElementById("productOrderEdit");
    const confirmedName = document.getElementById("productOrderConfirmedName");
    const confirmedEmail = document.getElementById("productOrderConfirmedEmail");
    const confirmedPhone = document.getElementById("productOrderConfirmedPhone");
    const confirmedAddress = document.getElementById("productOrderConfirmedAddress");
    const paymentSection = document.getElementById("productOrderPaymentSection");
    const submitButton = document.getElementById("productOrderSubmit");
    const editModal = document.getElementById("productEditModal");
    const editCloseButton = document.getElementById("closeProductEditModal");
    const editName = document.getElementById("productEditName");
    const editEmail = document.getElementById("productEditEmail");
    const editPhone = document.getElementById("productEditPhone");
    const editCity = document.getElementById("productEditCity");
    const editStreet = document.getElementById("productEditStreet");
    const saveEditButton = document.getElementById("saveProductEdit");
    const editError = document.getElementById("productEditError");
    const orderPayment = document.getElementById("productOrderPayment");
    const paymentOptions = document.querySelectorAll("[data-payment-method]");
    const paymentPanels = document.querySelectorAll("[data-payment-panel]");
    const codTotal = document.getElementById("productCodTotal");
    const gcashReference = document.getElementById("productGcashReference");
    const cardNumber = document.getElementById("productCardNumber");
    const cardExpiry = document.getElementById("productCardExpiry");
    const cardCvv = document.getElementById("productCardCvv");
    const cardholderName = document.getElementById("productCardholderName");
    const orderItems = document.getElementById("productOrderItems");
    const orderTotal = document.getElementById("productOrderTotal");
    const orderMessage = document.getElementById("productOrderMessage");
    const orderTotalDisplay = document.getElementById("productOrderTotalDisplay");
    const submitError = document.getElementById("productDetailSubmitError");
    const submitButtonDefaultText = submitButton ? submitButton.textContent.trim() : "Place order";
    const successView = document.getElementById("productDetailSuccess");
    const successAnimation = document.getElementById("productDetailSuccessAnimation");
    const successSummary = document.getElementById("productDetailSuccessSummary");
    const successClose = document.getElementById("productDetailSuccessClose");

    if (!modal || !closeButton || !cards.length || !image || !category || !title || !description || !variations || !variationLabel || !variationOptions || !quantityValue || !total || !decreaseButton || !increaseButton || !stepOne || !stepTwo || !continueButton || !backButton || !orderForm || !orderPhone || !orderAddress || !orderCity || !orderFullName || !orderEmailField || !orderPayment || !orderItems || !orderTotal || !orderTotalDisplay || !orderMessage || !confirmedCard || !editButton || !paymentSection || !submitButton || !editModal || !editCloseButton || !editName || !editEmail || !editPhone || !editCity || !editStreet || !saveEditButton || !editError || !successView || !successAnimation || !successSummary || !successClose) {
        return;
    }

    let unitPrice = 0;
    let quantity = 1;
    let selectedCard = null;
    let selectedVariation = "";

    function openSignInForProduct(card) {
        if (!signInModal || typeof window.openSignInModal !== "function") {
            return false;
        }

        if (signInNextInput) {
            signInNextInput.value = "/products/";
        }
        window.openSignInModal("product");
        return true;
    }
    let savedDetails = {
        name: editName.value.trim(),
        email: editEmail.value.trim(),
        phone: editPhone.value.trim(),
        city: editCity.value.trim() || editCity.dataset.savedCity || "",
        street: editStreet.value.trim(),
    };
    editCity.value = savedDetails.city;

    function formatCurrency(amount) {
        return "₱" + amount.toLocaleString("en-PH", { maximumFractionDigits: 0 });
    }

    function updateTotal() {
        quantityValue.textContent = String(quantity);
        total.textContent = formatCurrency(unitPrice * quantity);
        orderTotalDisplay.textContent = formatCurrency(unitPrice * quantity);
        orderTotal.value = String(unitPrice * quantity);
        if (codTotal) {
            codTotal.textContent = formatCurrency(unitPrice * quantity);
        }
        quantityValue.classList.remove("quantity-pulse");
        void quantityValue.offsetWidth;
        quantityValue.classList.add("quantity-pulse");
    }

    function updatePaymentPanel() {
        const selectedMethod = orderPayment.value || "cod";
        paymentPanels.forEach(function (panel) {
            const isActive = panel.dataset.paymentPanel === selectedMethod;
            panel.hidden = !isActive;
            panel.querySelectorAll("input").forEach(function (input) {
                input.required = isActive;
            });
        });
    }

    function setStep(step) {
        const isStepTwo = step === 2;
        stepOne.hidden = isStepTwo;
        stepTwo.hidden = !isStepTwo;
        const activeStep = isStepTwo ? stepTwo : stepOne;
        activeStep.classList.remove("step-forward", "step-back");
        void activeStep.offsetWidth;
        activeStep.classList.add(isStepTwo ? "step-forward" : "step-back");
        if (isStepTwo) {
            orderTotalDisplay.textContent = formatCurrency(unitPrice * quantity);
        }
    }

    function updateBuyerSummary() {
        const address = [savedDetails.street, savedDetails.city].filter(Boolean).join(", ");
        confirmedPhone.textContent = savedDetails.phone;
        confirmedAddress.textContent = address;
        confirmedName.textContent = savedDetails.name;
        confirmedEmail.textContent = savedDetails.email;
        orderFullName.value = savedDetails.name;
        orderEmailField.value = savedDetails.email;
        orderPhone.value = savedDetails.phone;
        orderAddress.value = savedDetails.street;
        orderCity.value = savedDetails.city;
        submitButton.disabled = !orderPayment.value;
    }

    function resetStepTwo() {
        orderPayment.value = "cod";
        updateBuyerSummary();
        paymentOptions.forEach(function (option, index) {
            option.classList.toggle("selected", index === 0);
        });
        updatePaymentPanel();
        submitError.hidden = true;
        editError.hidden = true;
        successView.hidden = true;
        modal.classList.remove("is-success");
    }

    function closeModal() {
        if (modal.classList.contains("is-closing")) {
            return;
        }
        modal.classList.remove("is-opening");
        modal.classList.add("is-closing");
        window.setTimeout(function () {
            modal.hidden = true;
            modal.classList.remove("is-closing");
            setStep(1);
            resetStepTwo();
        }, 150);
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open");
    }

    function showOrderSuccess(receiptOrder) {
        stepOne.hidden = true;
        stepTwo.hidden = true;
        successView.hidden = false;
        modal.classList.add("is-success");
        modal.classList.remove("is-opening");
        void modal.offsetWidth;
        modal.classList.add("is-opening");
        successSummary.textContent = `${title.textContent.trim()} · ${quantity} unit${quantity === 1 ? "" : "s"} · ${formatCurrency(unitPrice * quantity)}`;
        if (receiptOrder && typeof window.openOrderReceipt === "function") {
            const printReceiptButton = document.getElementById("productOrderPrintReceipt");
            if (printReceiptButton) {
                printReceiptButton.onclick = function () {
                    window.openOrderReceipt(receiptOrder);
                    window.requestAnimationFrame(function () {
                        if (typeof window.downloadOrderReceipt === "function") {
                            window.downloadOrderReceipt(receiptOrder.order_number);
                        }
                    });
                };
            }
        }
        if (window.lottie && typeof window.lottie.loadAnimation === "function") {
            successAnimation.replaceChildren();
            const animation = window.lottie.loadAnimation({
                container: successAnimation,
                renderer: "svg",
                loop: false,
                autoplay: false,
                path: successAnimation.dataset.lottiePath,
            });
            animation.addEventListener("DOMLoaded", function () {
                animation.goToAndStop(0, true);
                window.requestAnimationFrame(function () {
                    animation.play();
                });
            });
        }
    }

    function renderVariations(card) {
        const values = (card.dataset.variations || "").split("|").filter(Boolean);
        if (values.length < 2) {
            variations.hidden = true;
            variationOptions.replaceChildren();
            selectedVariation = "";
            return;
        }

        variationLabel.textContent = values[0];
        selectedVariation = values[1];
        variationOptions.replaceChildren();
        values.slice(1).forEach(function (value, index) {
            const option = document.createElement("button");
            option.type = "button";
            option.className = "product-detail-option";
            option.textContent = value;
            option.classList.toggle("selected", index === 0);
            option.addEventListener("click", function () {
                selectedVariation = value;
                variationOptions.querySelectorAll(".product-detail-option").forEach(function (item) {
                    item.classList.toggle("selected", item === option);
                });
            });
            variationOptions.appendChild(option);
        });
        variations.hidden = false;
    }

    function openModal(card) {
        const cardImage = card.querySelector(".product-media img");
        const cardCategory = card.querySelector(".product-category-badge");
        const cardTitle = card.querySelector("h3");
        const cardDescription = card.dataset.description || "";
        const cardPrice = card.querySelector(".product-price");

        if (!cardImage || !cardCategory || !cardTitle || !cardDescription || !cardPrice) {
            return;
        }

        image.src = cardImage.src;
        image.alt = cardImage.alt;
        category.textContent = cardCategory.textContent.trim();
        title.textContent = cardTitle.textContent.trim();
        description.textContent = cardDescription.trim();
        unitPrice = Number.parseFloat(cardPrice.textContent.replace(/[^0-9.]/g, "")) || 0;
        quantity = 1;
        selectedCard = card;
        renderVariations(card);
        resetStepTwo();
        setStep(1);
        updateTotal();
        modal.classList.remove("is-closing");
        modal.hidden = false;
        void modal.offsetWidth;
        modal.classList.add("is-opening");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        closeButton.focus();
    }

    cards.forEach(function (card) {
        card.setAttribute("tabindex", "0");
        card.setAttribute("role", "button");
        card.addEventListener("click", function () {
            if (window.isAuthenticated !== true) {
                openSignInForProduct(card);
                return;
            }
            openModal(card);
        });
        card.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (window.isAuthenticated !== true) {
                    openSignInForProduct(card);
                    return;
                }
                openModal(card);
            }
        });
    });

    decreaseButton.addEventListener("click", function () {
        quantity = Math.max(1, quantity - 1);
        updateTotal();
    });

    increaseButton.addEventListener("click", function () {
        quantity += 1;
        updateTotal();
    });

    continueButton.addEventListener("click", function () {
        setStep(2);
        updateBuyerSummary();
    });

    backButton.addEventListener("click", function () {
        setStep(1);
    });

    paymentOptions.forEach(function (option) {
        option.addEventListener("click", function () {
            orderPayment.value = option.dataset.paymentMethod || "cod";
            paymentOptions.forEach(function (item) {
                item.classList.toggle("selected", item === option);
            });
            updatePaymentPanel();
            submitButton.disabled = !orderPayment.value;
        });
    });

    function openEditModal() {
        editPhone.value = savedDetails.phone;
        editCity.value = savedDetails.city;
        editStreet.value = savedDetails.street;
        editModal.classList.remove("is-closing");
        editModal.hidden = false;
        void editModal.offsetWidth;
        editModal.classList.add("is-opening");
        editModal.setAttribute("aria-hidden", "false");
        editPhone.focus();
    }

    function closeEditModal() {
        if (editModal.classList.contains("is-closing")) {
            return;
        }
        editModal.classList.remove("is-opening");
        editModal.classList.add("is-closing");
        window.setTimeout(function () {
            editModal.hidden = true;
            editModal.classList.remove("is-closing");
        }, 150);
        editModal.setAttribute("aria-hidden", "true");
        editError.hidden = true;
    }

    editButton.addEventListener("click", openEditModal);
    editCloseButton.addEventListener("click", closeEditModal);
    editModal.addEventListener("click", function (event) {
        if (event.target === editModal) {
            closeEditModal();
        }
    });
    saveEditButton.addEventListener("click", function () {
        if (!editName.value.trim() || !editEmail.value.trim() || !editPhone.value.trim() || !editCity.value.trim() || !editStreet.value.trim()) {
            editError.hidden = false;
            return;
        }
        saveEditButton.disabled = true;
        const csrfToken = orderForm.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        const payload = new FormData();
        payload.append("phone", editPhone.value.trim());
        payload.append("city", editCity.value.trim());
        payload.append("street", editStreet.value.trim());
        payload.append("csrfmiddlewaretoken", csrfToken);

        fetch(saveEditButton.dataset.saveUrl, {
            method: "POST",
            body: payload,
            headers: { "X-Requested-With": "XMLHttpRequest" },
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) {
                        throw new Error(data.error || "Unable to save your details.");
                    }
                    return data;
                });
            })
            .then(function (data) {
                savedDetails = {
                    name: editName.value.trim(),
                    email: editEmail.value.trim(),
                    phone: data.phone,
                    city: data.city,
                    street: data.street,
                };
                updateBuyerSummary();
                closeEditModal();
            })
            .catch(function (error) {
                editError.textContent = error.message;
                editError.hidden = false;
            })
            .finally(function () {
                saveEditButton.disabled = false;
            });
    });

    orderForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const hasDetails = Boolean(savedDetails.name && savedDetails.email && savedDetails.phone && savedDetails.city && savedDetails.street);
        const activePaymentFieldsValid = orderPayment.value === "gcash"
            ? Boolean(gcashReference.value.trim())
            : orderPayment.value === "card"
                ? Boolean(cardNumber.value.trim() && cardExpiry.value.trim() && cardCvv.value.trim() && cardholderName.value.trim())
                : true;
        if (!hasDetails || !orderPayment.value || !selectedCard || !activePaymentFieldsValid) {
            submitError.classList.remove("validation-shake");
            void submitError.offsetWidth;
            submitError.classList.add("validation-shake");
            submitError.hidden = false;
            return;
        }

        const selectedCategory = selectedCard.querySelector(".product-category-badge").textContent.trim();
        orderItems.value = JSON.stringify([{
            name: title.textContent.trim(),
            category: selectedCategory,
            variation: selectedVariation,
            quantity: quantity,
            unit_price: unitPrice,
        }]);
        const paymentDetails = orderPayment.value === "gcash"
            ? `GCash reference number: ${gcashReference.value.trim()}`
            : orderPayment.value === "card"
                ? `Card number: ${cardNumber.value.trim()}\nExpiry: ${cardExpiry.value.trim()}\nCVV: ${cardCvv.value.trim()}\nCardholder name: ${cardholderName.value.trim()}`
                : `COD amount due: ${formatCurrency(unitPrice * quantity)}`;
        orderMessage.value = `Payment details (${orderPayment.value}):\n${paymentDetails}`;
        orderPhone.value = savedDetails.phone;
        orderAddress.value = savedDetails.street;
        orderCity.value = savedDetails.city;
        submitError.hidden = true;
        submitButton.disabled = true;
        submitButton.classList.add("is-loading");
        submitButton.textContent = "Placing order";

        try {
            const response = await fetch(orderForm.action, {
                method: "POST",
                body: new FormData(orderForm),
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Unable to place your order.");
            }
            submitButton.classList.remove("is-loading");
            showOrderSuccess(data.order);
        } catch (error) {
            submitButton.disabled = false;
            submitButton.classList.remove("is-loading");
            submitButton.textContent = submitButtonDefaultText;
            submitError.textContent = error.message;
            submitError.hidden = false;
        }
    });

    closeButton.addEventListener("click", closeModal);
    successClose.addEventListener("click", function () {
        if (typeof window.notifyOrderTrackerOrderPlaced === "function") {
            window.notifyOrderTrackerOrderPlaced();
        }
        closeModal();
    });
    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !editModal.hidden) {
            closeEditModal();
            return;
        }
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

}

function initOrderTracker() {
    const button = document.getElementById("orderTrackerButton");
    const overlay = document.getElementById("orderTrackerModal");
    const closeButton = document.getElementById("orderTrackerClose");
    const selectButton = document.getElementById("orderTrackerSelect");
    const deleteButton = document.getElementById("orderTrackerDelete");
    const searchInput = document.getElementById("orderTrackerSearch");
    const badge = document.getElementById("orderTrackerBadge");
    const list = document.getElementById("orderTrackerList");
    const cancelOverlay = document.getElementById("orderCancelModal");
    const cancelKeep = document.getElementById("orderCancelKeep");
    const cancelConfirm = document.getElementById("orderCancelConfirm");
    const bulkBar = document.getElementById("orderTrackerBulkBar");
    const selectedCount = document.getElementById("orderTrackerSelectedCount");
    const bulkCancel = document.getElementById("orderTrackerBulkCancel");
    const clearSelection = document.getElementById("orderTrackerClear");
    const cancelMessage = document.getElementById("orderCancelMessage");

    if (!button || !overlay || !closeButton || !selectButton || !deleteButton || !searchInput || !badge || !list || !cancelOverlay || !cancelKeep || !cancelConfirm || !bulkBar || !selectedCount || !bulkCancel || !clearSelection || !cancelMessage) {
        return;
    }

    let previousActiveCount = Number.parseInt(badge.textContent || "0", 10) || 0;
    let pendingCancelId = null;
    let pendingCancelCard = null;
    let selectedOrderIds = new Set();
    let pendingCancelIds = [];
    let selectMode = false;
    let currentOrders = [];

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function renderOrders(orders, activeCount) {
        currentOrders = orders;
        const eligibleIds = new Set(orders.filter(function (order) { return order.status === "pending" || order.status === "verified"; }).map(function (order) { return order.id; }));
        selectedOrderIds = new Set([...selectedOrderIds].filter(function (id) { return eligibleIds.has(id); }));
        previousActiveCount = activeCount;
        overlay.classList.toggle("is-selecting", selectMode);
        badge.textContent = String(activeCount);
        badge.hidden = activeCount === 0;
        button.hidden = orders.length === 0;
        if (!orders.length) {
            list.innerHTML = '<p class="order-tracker-empty">You haven\'t placed any orders yet.</p>';
            updateBulkBar();
            return;
        }
        list.innerHTML = orders.map(function (order) {
            const variation = order.variation ? `<span>${escapeHtml(order.variation)}</span>` : "";
            const unitLabel = Number(order.quantity) === 1 ? "unit" : "units";
            const cancel = order.status === "pending" || order.status === "verified"
                ? `<button class="order-tracker-cancel" type="button" data-cancel-order-id="${escapeHtml(order.id)}">Cancel</button>`
                : "";
            const checkbox = order.status === "pending" || order.status === "verified"
                ? `<input class="order-tracker-checkbox" type="checkbox" data-order-id="${escapeHtml(order.id)}" aria-label="Select ${escapeHtml(order.name)} for cancellation"${selectedOrderIds.has(order.id) ? " checked" : ""}>`
                : '<span class="order-tracker-checkbox-spacer" aria-hidden="true"></span>';
            const receipt = `<button class="order-tracker-receipt" type="button" data-receipt-order-id="${escapeHtml(order.id)}" aria-label="Print receipt for ${escapeHtml(order.name)}"><i data-lucide="receipt-text"></i><span>Receipt</span></button>`;
            const actionMarkup = `<div class="order-tracker-card-actions"><span class="order-tracker-status status-${escapeHtml(order.status)}">${escapeHtml(order.status_label)}</span>${receipt}${cancel}</div>`;
            return `<article class="order-tracker-card" data-order-card-id="${escapeHtml(order.id)}">
                ${checkbox}
                <img src="${escapeHtml(order.image)}" alt="${escapeHtml(order.name)}">
                <div class="order-tracker-card-body">
                    <strong>${escapeHtml(order.name)}</strong>
                    ${variation}
                    <span>${escapeHtml(order.quantity)} ${unitLabel} · ₱${escapeHtml(order.total)}</span>
                    <time>${escapeHtml(order.date)}</time>
                </div>
                ${actionMarkup}
            </article>`;
        }).join("");
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
        updateBulkBar();
        applySearch();
    }

    function updateBulkBar() {
        selectedCount.textContent = String(selectedOrderIds.size);
        bulkBar.hidden = selectedOrderIds.size === 0;
        deleteButton.hidden = selectedOrderIds.size === 0;
    }

    function applySearch() {
        const query = searchInput.value.trim().toLowerCase();
        list.querySelectorAll(".order-tracker-card").forEach(function (card) {
            const order = currentOrders.find(function (item) { return item.id === card.dataset.orderCardId; });
            const matches = !query || (order && order.name.toLowerCase().includes(query));
            card.classList.toggle("is-search-hidden", !matches);
        });
    }

    function openCancelPrompt(ids, card) {
        pendingCancelIds = ids;
        pendingCancelId = ids.length === 1 ? ids[0] : null;
        pendingCancelCard = card || null;
        cancelMessage.textContent = ids.length === 1
            ? "This can't be undone."
            : `Cancel these ${ids.length} orders? This can't be undone.`;
        cancelConfirm.textContent = ids.length === 1 ? "Cancel order" : "Cancel orders";
        cancelOverlay.classList.remove("is-closing");
        cancelOverlay.hidden = false;
        void cancelOverlay.offsetWidth;
        cancelOverlay.classList.add("is-opening");
        cancelOverlay.setAttribute("aria-hidden", "false");
    }

    function parseJsonResponse(response) {
        return response.text().then(function (text) {
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (error) {
                throw new Error("Something went wrong. Please try again.");
            }
            if (!response.ok) {
                throw new Error(data.error || "Something went wrong. Please try again.");
            }
            return data;
        });
    }

    function setSelectMode(enabled) {
        selectMode = enabled;
        overlay.classList.toggle("is-selecting", enabled);
        selectButton.textContent = enabled ? "Done" : "Select";
        selectButton.setAttribute("aria-pressed", String(enabled));
        if (!enabled) {
            selectedOrderIds.clear();
            list.querySelectorAll(".order-tracker-checkbox").forEach(function (checkbox) { checkbox.checked = false; });
        }
        updateBulkBar();
    }

    function animateNewOrderBadge() {
        const nextCount = previousActiveCount + 1;
        const increment = document.createElement("span");
        increment.className = "order-tracker-plus-one";
        increment.textContent = "+1";
        button.appendChild(increment);
        window.setTimeout(function () { increment.remove(); }, 1550);
        button.hidden = false;
        button.classList.remove("is-pressed");
        void button.offsetWidth;
        button.classList.add("is-pressed");
        badge.textContent = String(nextCount);
        badge.hidden = false;
        badge.classList.remove("is-pulsing");
        void badge.offsetWidth;
        badge.classList.add("is-pulsing");
        previousActiveCount = nextCount;
        refreshOrders();
    }

    window.notifyOrderTrackerOrderPlaced = animateNewOrderBadge;

    function refreshOrders() {
        fetch("/products/orders/tracker/", { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (response) { return response.ok ? response.json() : null; })
            .then(function (data) {
                if (data) {
                    renderOrders(data.orders || [], Number(data.active_count) || 0);
                }
            })
            .catch(function () { /* Keep the last known order state visible. */ });
    }

    function openTracker() {
        button.classList.remove("is-pressed");
        void button.offsetWidth;
        button.classList.add("is-pressed");
        overlay.hidden = false;
        overlay.classList.remove("is-closing");
        void overlay.offsetWidth;
        overlay.classList.add("is-opening");
        overlay.setAttribute("aria-hidden", "false");
        button.setAttribute("aria-expanded", "true");
        document.body.classList.add("modal-open");
    }

    function closeTracker() {
        setSelectMode(false);
        overlay.classList.remove("is-opening");
        overlay.classList.add("is-closing");
        window.setTimeout(function () {
            overlay.hidden = true;
            overlay.classList.remove("is-closing");
        }, 150);
        overlay.setAttribute("aria-hidden", "true");
        button.setAttribute("aria-expanded", "false");
        document.body.classList.remove("modal-open");
    }

    button.addEventListener("click", openTracker);
    closeButton.addEventListener("click", closeTracker);
    selectButton.addEventListener("click", function () {
        setSelectMode(!selectMode);
    });
    deleteButton.addEventListener("click", function () {
        if (selectedOrderIds.size) openCancelPrompt([...selectedOrderIds], null);
    });
    searchInput.addEventListener("input", applySearch);
    list.addEventListener("change", function (event) {
        if (!event.target.classList.contains("order-tracker-checkbox")) return;
        if (event.target.checked) selectedOrderIds.add(event.target.dataset.orderId);
        else selectedOrderIds.delete(event.target.dataset.orderId);
        updateBulkBar();
    });
    overlay.addEventListener("click", function (event) {
        if (event.target.classList.contains("order-tracker-checkbox")) {
            return;
        }
        const cancelButton = event.target.closest("[data-cancel-order-id]");
        if (cancelButton) {
            openCancelPrompt([cancelButton.dataset.cancelOrderId], cancelButton.closest(".order-tracker-card"));
            return;
        }
        const receiptButton = event.target.closest("[data-receipt-order-id]");
        if (receiptButton) {
            const order = currentOrders.find(function (item) { return item.id === receiptButton.dataset.receiptOrderId; });
            if (order && typeof window.openOrderReceipt === "function") {
                window.openOrderReceipt(order);
            }
            return;
        }
        if (event.target === overlay) {
            closeTracker();
        }
    });
    bulkCancel.addEventListener("click", function () {
        if (!selectedOrderIds.size) return;
        pendingCancelIds = [...selectedOrderIds];
        pendingCancelId = null;
        pendingCancelCard = null;
        openCancelPrompt([...selectedOrderIds], null);
    });
    clearSelection.addEventListener("click", function () {
        selectedOrderIds.clear();
        list.querySelectorAll(".order-tracker-checkbox").forEach(function (checkbox) { checkbox.checked = false; });
        updateBulkBar();
    });
    cancelKeep.addEventListener("click", function () {
        cancelOverlay.hidden = true;
        cancelOverlay.classList.remove("is-opening");
        cancelOverlay.setAttribute("aria-hidden", "true");
        pendingCancelId = null;
        pendingCancelCard = null;
        pendingCancelIds = [];
        cancelConfirm.textContent = "Cancel order";
    });
    cancelConfirm.addEventListener("click", function () {
        if (!pendingCancelIds.length) return;
        cancelConfirm.disabled = true;
        const csrfField = document.querySelector("[name=csrfmiddlewaretoken]");
        const csrfCookie = document.cookie.split(";").map(function (part) { return part.trim(); }).find(function (part) { return part.startsWith("csrftoken="); });
        const csrfToken = csrfField?.value || (csrfCookie ? decodeURIComponent(csrfCookie.split("=").slice(1).join("=")) : "");
        const idsToCancel = [...pendingCancelIds];
        const cancelRequests = idsToCancel.map(function (id) {
            return fetch(`/products/orders/${id}/cancel/`, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" },
            }).then(parseJsonResponse);
        });
        Promise.all(cancelRequests)
            .then(function () {
                const cards = idsToCancel.map(function (id) { return list.querySelector(`[data-order-card-id="${id}"]`); }).filter(Boolean);
                cancelKeep.click();
                cards.forEach(function (card) { card.classList.add("is-removing"); });
                selectedOrderIds = new Set();
                window.setTimeout(function () {
                    refreshOrders();
                }, 220);
                pendingCancelId = null;
                pendingCancelCard = null;
            })
            .catch(function (error) {
                cancelConfirm.disabled = false;
                cancelMessage.textContent = error.message || "Unable to cancel this order. Please try again.";
            })
            .finally(function () { cancelConfirm.disabled = false; });
    });
    cancelOverlay.addEventListener("click", function (event) {
        if (event.target === cancelOverlay) cancelKeep.click();
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !cancelOverlay.hidden) {
            cancelKeep.click();
            return;
        }
        if (event.key === "Escape" && !overlay.hidden) {
            closeTracker();
        }
    });

    window.setInterval(refreshOrders, 15000);
    refreshOrders();
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

function initAboutCorePrograms() {
    var grid = document.querySelector("[data-program-grid]");
    var modalOverlay = document.getElementById("programModal");
    var modalCloseBtn = document.getElementById("programModalClose");
    var modalLogo = document.getElementById("programModalLogo");
    var modalTitle = document.getElementById("programModalTitle");
    var modalDescription = document.getElementById("programModalDescription");

    if (!grid || !modalOverlay || !modalCloseBtn || !modalLogo || !modalTitle || !modalDescription) {
        return;
    }

    var cards = grid.querySelectorAll(".program-card[data-program]");
    if (!cards.length) {
        return;
    }

    function clearActive() {
        cards.forEach(function (card) {
            card.classList.remove("is-active");
            card.setAttribute("aria-pressed", "false");
        });
    }

    function closeDetails() {
        clearActive();
        modalOverlay.hidden = true;
        document.body.classList.remove("modal-open");
        modalLogo.removeAttribute("src");
        modalTitle.textContent = "";
        modalDescription.textContent = "";
    }

    function openProgramModal(card) {
        var programTitle = card.dataset.title || card.dataset.program || "Program";
        var programDescription = card.dataset.description || "";
        var programLogo = card.dataset.logo || "";

        clearActive();
        card.classList.add("is-active");
        card.setAttribute("aria-pressed", "true");

        if (programLogo) {
            modalLogo.src = programLogo;
            modalLogo.alt = programTitle + " logo";
        } else {
            var logo = card.querySelector(".program-logo-image");
            var logoSrc = logo ? logo.getAttribute("src") : "";
            if (logoSrc) {
                modalLogo.src = logoSrc;
                modalLogo.alt = programTitle + " logo";
            }
        }

        modalTitle.textContent = programTitle;
        modalDescription.textContent = programDescription;
        modalOverlay.hidden = false;
        document.body.classList.add("modal-open");
    }

    cards.forEach(function (card) {
        card.addEventListener("click", function () {
            if (card.classList.contains("is-active")) {
                closeDetails();
                return;
            }
            openProgramModal(card);
        });

        card.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (card.classList.contains("is-active")) {
                    closeDetails();
                    return;
                }
                openProgramModal(card);
            }
        });
    });

    modalCloseBtn.addEventListener("click", closeDetails);

    modalOverlay.addEventListener("click", function (event) {
        if (event.target === modalOverlay) {
            closeDetails();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modalOverlay.hidden) {
            closeDetails();
        }
    });
}

function initFooterFaqModal() {
    var openFaqBtn = document.getElementById("openFaqModal");
    var faqModal = document.getElementById("faqModal");
    var closeFaqBtn = document.getElementById("closeFaqModal");

    if (!openFaqBtn || !faqModal || !closeFaqBtn) {
        return;
    }

    var programModal = document.getElementById("programModal");
    var questionButtons = faqModal.querySelectorAll("[data-faq-question]");

    function syncBodyModalState() {
        var authModalOpen =
            (signInModal && signInModal.classList.contains("open")) ||
            (signUpModal && signUpModal.classList.contains("open"));
        var programModalOpen = programModal && !programModal.hidden;
        var faqModalOpen = !faqModal.hidden;

        if (authModalOpen || programModalOpen || faqModalOpen) {
            document.body.classList.add("modal-open");
            return;
        }

        document.body.classList.remove("modal-open");
    }

    function closeFaqModal() {
        faqModal.hidden = true;
        faqModal.setAttribute("aria-hidden", "true");
        syncBodyModalState();
    }

    function openFaqModal() {
        faqModal.hidden = false;
        faqModal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
    }

    openFaqBtn.addEventListener("click", openFaqModal);
    closeFaqBtn.addEventListener("click", closeFaqModal);

    faqModal.addEventListener("click", function (event) {
        if (event.target === faqModal) {
            closeFaqModal();
        }
    });

    questionButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            var item = button.closest(".faq-item");
            var answer = item ? item.querySelector(".faq-answer") : null;

            if (!item || !answer) {
                return;
            }

            var isOpen = item.classList.contains("is-open");
            item.classList.toggle("is-open", !isOpen);
            button.setAttribute("aria-expanded", String(!isOpen));
            answer.hidden = isOpen;
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !faqModal.hidden) {
            closeFaqModal();
        }
    });
}

function initContactPhoneInput() {
    const contactPhoneInput = document.getElementById("contactPhone");

    if (!contactPhoneInput) {
        return;
    }

    function sanitizePhoneValue() {
        contactPhoneInput.value = contactPhoneInput.value.replace(/\D+/g, "");
    }

    contactPhoneInput.addEventListener("input", sanitizePhoneValue);
    contactPhoneInput.addEventListener("paste", function () {
        window.setTimeout(sanitizePhoneValue, 0);
    });
}

function initContactCountryPicker() {
    const picker = document.querySelector("[data-contact-country-picker]");

    if (!picker) {
        return;
    }

    const trigger = picker.querySelector("[data-contact-country-trigger]");
    const menu = picker.querySelector("[data-contact-country-menu]");
    const options = picker.querySelectorAll("[data-contact-country-option]");
    const label = picker.querySelector("[data-contact-country-label]");
    const hiddenInput = document.getElementById("contactCountry");

    if (!trigger || !menu || !options.length || !label || !hiddenInput) {
        return;
    }

    function closeMenu() {
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
    }

    trigger.addEventListener("click", function () {
        if (menu.hidden) {
            openMenu();
            return;
        }

        closeMenu();
    });

    options.forEach(function (option) {
        option.addEventListener("click", function () {
            const value = option.dataset.value || "+63";
            hiddenInput.value = value;
            label.textContent = value;
            closeMenu();
        });
    });

    document.addEventListener("click", function (event) {
        if (!picker.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });
}

function initProductPhoneInput() {
    const productPhoneInput = document.getElementById("productPhone");

    if (!productPhoneInput) {
        return;
    }

    function sanitizePhoneValue() {
        productPhoneInput.value = productPhoneInput.value.replace(/\D+/g, "");
    }

    productPhoneInput.addEventListener("input", sanitizePhoneValue);
    productPhoneInput.addEventListener("paste", function () {
        window.setTimeout(sanitizePhoneValue, 0);
    });
}

function initProductCountryPicker() {
    const picker = document.querySelector("[data-product-country-picker]");

    if (!picker) {
        return;
    }

    const trigger = picker.querySelector("[data-country-trigger]");
    const menu = picker.querySelector("[data-country-menu]");
    const options = picker.querySelectorAll("[data-country-option]");
    const label = picker.querySelector("[data-country-label]");
    const hiddenInput = document.getElementById("productCountry");

    if (!trigger || !menu || !options.length || !label || !hiddenInput) {
        return;
    }

    function closeMenu() {
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
    }

    trigger.addEventListener("click", function () {
        if (menu.hidden) {
            openMenu();
            return;
        }

        closeMenu();
    });

    options.forEach(function (option) {
        option.addEventListener("click", function () {
            const value = option.dataset.value || "+63";
            hiddenInput.value = value;
            label.textContent = value;
            closeMenu();
        });
    });

    document.addEventListener("click", function (event) {
        if (!picker.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });
}

function initProductInquiryModal() {
    const openButton = document.getElementById("openProductInquiryModal");
    const modal = document.getElementById("productInquiryModal");
    const closeButton = document.getElementById("closeProductInquiryModal");
    const form = document.getElementById("productInquiryForm");
    const formStateWrapper = document.getElementById("productFormStateWrapper");
    const summary = document.getElementById("productOrderSummary");
    const summaryList = document.getElementById("productOrderSummaryList");
    const summaryTotal = document.getElementById("productOrderSummaryTotal");
    const paymentSummaryList = document.getElementById("productPaymentSummaryList");
    const paymentSummaryTotal = document.getElementById("productPaymentSummaryTotal");
    const inquirySubmit = document.getElementById("productInquirySubmit");
    
    // Payment Modal elements
    const paymentModal = document.getElementById("paymentModal");
    const paymentModalCloseButton = document.getElementById("closePaymentModal");
    const paymentModalHeader = document.getElementById("paymentModalHeader");
    const paymentModalCODContent = document.getElementById("paymentModalCODContent");
    const paymentModalGCashBankContent = document.getElementById("paymentModalGCashBankContent");
    const paymentModalThankYouContent = document.getElementById("paymentModalThankYouContent");
    const paymentModalQr = document.getElementById("paymentModalQr");
    const productInquiryThankYouContent = document.getElementById("productInquiryThankYouContent");
    const productInquiryHeader = modal ? modal.querySelector(".product-inquiry-header") : null;
    const paymentModalSummaryList = document.getElementById("paymentModalSummaryList");
    const paymentModalSummaryTotal = document.getElementById("paymentModalSummaryTotal");
    const paymentModalForm = document.getElementById("paymentModalForm");
    const paymentScreenshotInput = document.getElementById("paymentScreenshotInput");
    const paymentUploadArea = document.getElementById("paymentUploadArea");
    const paymentFilePreview = document.getElementById("paymentFilePreview");
    const paymentFileName = document.getElementById("paymentFileName");
    const paymentFileSize = document.getElementById("paymentFileSize");
    const removePaymentFile = document.getElementById("removePaymentFile");
    const productPreviewOverlay = document.getElementById("productPreviewOverlay");
    const closeProductPreview = document.getElementById("closeProductPreview");
    const productPreviewImg = document.getElementById("productPreviewImg");
    const productPreviewName = document.getElementById("productPreviewName");
    const productPreviewCat = document.getElementById("productPreviewCat");
    const productPreviewButtons = document.querySelectorAll(".product-preview-btn");
    let storedInquiryData = null;
    
    const orderItemsPayload = document.getElementById("productOrderItemsPayload");
    const orderTotalPayload = document.getElementById("productOrderTotal");
    const paymentMethodInput = document.getElementById("paymentMethodInput");
    const paymentOptions = modal ? modal.querySelectorAll(".payment-option") : [];
    const rows = modal ? modal.querySelectorAll("[data-product-row]") : [];
    const qrPlaceholder = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent([
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320" fill="none">',
        '<rect width="320" height="320" rx="28" fill="#ffffff"/>',
        '<rect x="28" y="28" width="264" height="264" rx="20" fill="#f8fafc" stroke="#d1d5db"/>',
        '<rect x="56" y="56" width="68" height="68" rx="8" fill="#111827"/>',
        '<rect x="196" y="56" width="68" height="68" rx="8" fill="#111827"/>',
        '<rect x="56" y="196" width="68" height="68" rx="8" fill="#111827"/>',
        '<rect x="142" y="56" width="18" height="18" fill="#111827"/>',
        '<rect x="142" y="82" width="18" height="18" fill="#111827"/>',
        '<rect x="168" y="82" width="18" height="18" fill="#111827"/>',
        '<rect x="142" y="108" width="18" height="18" fill="#111827"/>',
        '<rect x="168" y="108" width="18" height="18" fill="#111827"/>',
        '<rect x="142" y="142" width="18" height="18" fill="#111827"/>',
        '<rect x="168" y="142" width="18" height="18" fill="#111827"/>',
        '<rect x="194" y="142" width="18" height="18" fill="#111827"/>',
        '<rect x="220" y="142" width="18" height="18" fill="#111827"/>',
        '<rect x="142" y="168" width="18" height="18" fill="#111827"/>',
        '<rect x="168" y="168" width="18" height="18" fill="#111827"/>',
        '<rect x="194" y="168" width="18" height="18" fill="#111827"/>',
        '<rect x="220" y="168" width="18" height="18" fill="#111827"/>',
        '<text x="160" y="296" fill="#64748b" font-family="Arial, sans-serif" font-size="18" font-weight="700" text-anchor="middle">QR code placeholder</text>',
        '</svg>'
    ].join(""));

    if (!openButton || !modal || !closeButton || !form || !summary || !summaryList || !summaryTotal || !inquirySubmit || !orderItemsPayload || !orderTotalPayload || !rows.length || !paymentOptions.length || !paymentMethodInput || !paymentModal || !paymentModalHeader || !paymentModalCloseButton || !paymentModalCODContent || !paymentModalGCashBankContent || !paymentModalThankYouContent || !paymentModalQr || !paymentModalSummaryList || !paymentModalSummaryTotal || !paymentModalForm || !paymentScreenshotInput || !paymentModalSubmit || !paymentModalNote || !formStateWrapper || !productInquiryThankYouContent || !productInquiryHeader) {
        return;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function syncBodyModalState() {
        const isAnyModalOpen = Boolean(
            document.querySelector(".modal-overlay.open") ||
            document.querySelector(".faq-modal-overlay:not([hidden])") ||
            document.querySelector(".product-inquiry-overlay:not([hidden])")
        );

        document.body.classList.toggle("modal-open", isAnyModalOpen);
    }

    function formatCurrency(amount) {
        const value = Number(amount) || 0;
        return "₱" + value.toLocaleString("en-PH", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    }

    function getQuantity(row) {
        return Number.parseInt(row.dataset.qty || "0", 10) || 0;
    }

    function getUnitPrice(row) {
        return Number.parseInt(row.dataset.price || "0", 10) || 0;
    }

    function setQuantity(row, quantity) {
        const nextQuantity = Math.max(0, quantity);
        row.dataset.qty = String(nextQuantity);

        const valueEl = row.querySelector("[data-qty-value]");
        if (valueEl) {
            valueEl.textContent = String(nextQuantity);
        }
    }

    function getSelectedPaymentMethod() {
        return paymentMethodInput.value || "gcash";
    }

    function syncPaymentOptionState() {
        const selectedValue = getSelectedPaymentMethod();
        paymentOptions.forEach(function (label) {
            label.classList.toggle("selected", label.dataset.payment === selectedValue);
        });
    }

    function buildOrderItems() {
        const selectedItems = [];
        let orderTotal = 0;

        rows.forEach(function (row) {
            const quantity = getQuantity(row);
            const unitPrice = getUnitPrice(row);

            if (quantity > 0) {
                const lineTotal = quantity * unitPrice;
                orderTotal += lineTotal;
                selectedItems.push({
                    name: row.dataset.productName || "",
                    category: row.dataset.productCategory || "",
                    quantity: quantity,
                    unit_price: unitPrice,
                    line_total: lineTotal,
                });
            }
        });

        return { selectedItems, orderTotal };
    }

    function renderSummary(listElement, totalElement, selectedItems, orderTotal) {
        if (!listElement || !totalElement) {
            return;
        }

        if (!selectedItems.length) {
            listElement.innerHTML = "";
            totalElement.innerHTML = "";
            return;
        }

        listElement.innerHTML = selectedItems.map(function (item) {
            return (
                '<div class="product-order-summary-item">' +
                    '<div><strong>' + escapeHtml(item.name) + '</strong><span>' + escapeHtml(item.category) + ' • ' + escapeHtml(formatCurrency(item.unit_price)) + ' x ' + item.quantity + '</span></div>' +
                    '<strong>' + escapeHtml(formatCurrency(item.line_total)) + '</strong>' +
                '</div>'
            );
        }).join("");

        totalElement.innerHTML = '<span>Total</span><strong>' + escapeHtml(formatCurrency(orderTotal)) + '</strong>';
    }

    function syncOrderPayload() {
        const { selectedItems, orderTotal } = buildOrderItems();
        orderItemsPayload.value = JSON.stringify(selectedItems);
        orderTotalPayload.value = String(orderTotal);
        renderSummary(summaryList, summaryTotal, selectedItems, orderTotal);
        summary.hidden = !selectedItems.length;
        inquirySubmit.disabled = !selectedItems.length;
        return { selectedItems, orderTotal };
    }

    function resetModalState() {
        form.reset();
        rows.forEach(function (row) {
            setQuantity(row, 0);
        });
        orderItemsPayload.value = "";
        orderTotalPayload.value = "";
        renderSummary(summaryList, summaryTotal, [], 0);
        renderSummary(paymentModalSummaryList, paymentModalSummaryTotal, [], 0);
        syncPaymentOptionState();
        syncOrderPayload();
    }


    function openModal() {
        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
        resetModalState();
        syncBodyModalState();
    }

    function resetInquiryModal() {
        if (!form || !inquirySubmit) {
            return;
        }

        inquirySubmit.disabled = false;
        inquirySubmit.textContent = "Send Inquiry";
        form.reset();
        storedInquiryData = null;
        if (productInquiryHeader) {
            productInquiryHeader.style.display = "";
        }
        if (productInquiryThankYouContent) {
            productInquiryThankYouContent.hidden = true;
            productInquiryThankYouContent.innerHTML = "";
        }
        if (formStateWrapper) {
            formStateWrapper.hidden = false;
        }
    }

    function hideInquiryModal() {
        modal.setAttribute("hidden", "");
        modal.setAttribute("aria-hidden", "true");
        syncBodyModalState();
    }

    function closeInquiryModal() {
        resetInquiryModal();
        hideInquiryModal();
    }

    function resetPaymentModal() {
        if (paymentModalHeader) {
            paymentModalHeader.style.display = "";
        }
        if (paymentModalThankYouContent) {
            paymentModalThankYouContent.hidden = true;
        }
        if (paymentModalGCashBankContent) {
            paymentModalGCashBankContent.hidden = true;
        }
        if (paymentModalCODContent) {
            paymentModalCODContent.hidden = true;
        }
        if (paymentModalQr) {
            paymentModalQr.src = "";
        }
        if (paymentUploadArea) {
            paymentUploadArea.style.display = "grid";
        }
        if (paymentFilePreview) {
            paymentFilePreview.style.display = "none";
        }
        if (paymentFileName) {
            paymentFileName.textContent = "";
        }
        if (paymentFileSize) {
            paymentFileSize.textContent = "";
        }
        if (paymentScreenshotInput) {
            paymentScreenshotInput.value = "";
        }
        if (paymentModalSubmit) {
            paymentModalSubmit.disabled = true;
            paymentModalSubmit.style.background = "#ccc";
            paymentModalSubmit.style.cursor = "default";
            paymentModalSubmit.textContent = "Submit Payment";
        }
        if (paymentModalNote) {
            paymentModalNote.textContent = "Upload a screenshot to enable the submit button.";
        }
    }

    function openPaymentModal(paymentMethod, inquiryData) {
        // Hide all content sections
        paymentModalCODContent.hidden = true;
        paymentModalGCashBankContent.hidden = true;
        paymentModalThankYouContent.hidden = true;
        
        if (paymentMethod === "cod") {
            paymentModalCODContent.hidden = false;
        } else {
            // GCash or Bank Transfer
            paymentModalGCashBankContent.hidden = false;
            paymentModalQr.src = qrPlaceholder;
            
            // Populate order summary
            renderSummary(paymentModalSummaryList, paymentModalSummaryTotal, inquiryData.selectedItems, inquiryData.orderTotal);
            
            // Reset file input, preview state, and submit button style
            paymentScreenshotInput.value = "";
            paymentModalSubmit.disabled = true;
            paymentModalSubmit.style.background = "#ccc";
            paymentModalSubmit.style.cursor = "default";
            if (paymentUploadArea) {
                paymentUploadArea.style.display = "grid";
            }
            if (paymentFilePreview) {
                paymentFilePreview.style.display = "none";
            }
            if (paymentFileName) {
                paymentFileName.textContent = "";
            }
            if (paymentFileSize) {
                paymentFileSize.textContent = "";
            }
            paymentModalNote.textContent = "Upload a screenshot to enable the submit button.";
        }
        
        // Open payment modal using setAttribute/removeAttribute
        paymentModal.removeAttribute("hidden");
        paymentModal.setAttribute("aria-hidden", "false");
        syncBodyModalState();
    }

    function closePaymentModal() {
        resetInquiryModal();
        resetPaymentModal();
        paymentModal.setAttribute("hidden", "");
        paymentModal.setAttribute("aria-hidden", "true");
        syncBodyModalState();
    }

    window.closePaymentModal = closePaymentModal;

    function buildThankYouScreenHtml(thankYouMessage, customerName, paymentMethodLabel, orderTotal, closeFunctionName) {
        return `
            <div style="text-align:center; padding:32px 24px; position:relative;">
              <button onclick="${closeFunctionName}()" style="position:absolute;top:0;right:0;width:32px;height:32px;border-radius:50%;border:1.5px solid #e0e0e0;background:#fff;cursor:pointer;font-size:16px;color:#666;">×</button>
              <div style="width:64px;height:64px;border-radius:50%;background:#f0f7f4;border:2px solid #2d6e4e;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M5 12l4 4L19 7" stroke="#2d6e4e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </div>
              <p style="font-size:11px;font-weight:600;color:#2d6e4e;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Thank you!</p>
              <h2 style="font-size:20px;font-weight:700;color:#111;margin-bottom:10px;">Order Received</h2>
              <p style="font-size:13px;color:#888;line-height:1.7;margin-bottom:24px;">${thankYouMessage}</p>
              <div style="background:#f8faf9;border:1.5px solid #e0ece6;border-radius:10px;padding:14px 16px;margin-bottom:24px;text-align:left;">
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;"><span style="color:#888;">Customer</span><span style="font-weight:600;color:#111;">${customerName}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;"><span style="color:#888;">Payment</span><span style="font-weight:600;color:#111;">${paymentMethodLabel}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;"><span style="color:#888;">Total</span><span style="font-weight:600;color:#111;">₱${orderTotal}</span></div>
                <div style="display:flex;justify-content:space-between;font-size:12px;"><span style="color:#888;">Status</span><span style="color:#f59e0b;font-weight:600;">⏳ Pending confirmation</span></div>
              </div>
              <button onclick="${closeFunctionName}()" style="width:100%;padding:13px;background:#2d6e4e;color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">Close</button>
            </div>`;
    }

    function showPaymentModalThankYou() {
        if (paymentModalHeader) {
            paymentModalHeader.style.display = "none";
        }
        if (paymentModalCODContent) {
            paymentModalCODContent.hidden = true;
        }
        if (paymentModalGCashBankContent) {
            paymentModalGCashBankContent.hidden = true;
        }
        if (!paymentModalThankYouContent) {
            return;
        }

        const paymentMethod = storedInquiryData?.payment_method || "GCash";
        const orderTotal = storedInquiryData?.order_total || "0";
        const customerName = storedInquiryData?.full_name || "Customer";
        const thankYouMessage = paymentMethod === "cod"
            ? "We'll contact you soon to arrange your delivery.<br>Thank you for supporting Happy Nanays! 💚"
            : "We'll confirm your payment within 24 hours.<br>Thank you for supporting Happy Nanays! 💚";

        const displayPaymentMethod = paymentMethod === "cod" ? "Cash on Delivery" : paymentMethod === "bank" ? "Bank Transfer" : "GCash";

        paymentModalThankYouContent.innerHTML = buildThankYouScreenHtml(thankYouMessage, customerName, displayPaymentMethod, orderTotal, "closePaymentModal");
        paymentModalThankYouContent.hidden = false;
    }

    rows.forEach(function (row) {
        setQuantity(row, 0);

        row.querySelectorAll("[data-qty-step]").forEach(function (button) {
            button.addEventListener("click", function () {
                const step = Number.parseInt(button.dataset.qtyStep || "0", 10) || 0;
                setQuantity(row, getQuantity(row) + step);
                syncOrderPayload();
            });
        });
    });

    paymentOptions.forEach(function (option) {
        option.addEventListener("click", function () {
            const paymentValue = option.dataset.payment;
            paymentMethodInput.value = paymentValue;
            syncPaymentOptionState();
        });
    });

    openButton.addEventListener("click", function () {
        if (!window.isRegularUser) {
            if (typeof window.openSignInModal === "function") {
                window.openSignInModal("product-inquiry");
            } else {
                const openSignInModalBtn = document.getElementById("openSignInModal");
                if (openSignInModalBtn) {
                    openSignInModalBtn.click();
                }
            }
            return;
        }

        openModal();
    });
    closeButton.addEventListener("click", closeInquiryModal);

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeInquiryModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            if (!modal.hidden) {
                closeInquiryModal();
            } else if (!paymentModal.hidden) {
                closePaymentModal();
            }
        }
    });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        // Validate form fields
        const fullName = document.getElementById("productFullName").value.trim();
        const email = document.getElementById("productEmail").value.trim();
        const phone = document.getElementById("productPhone").value.trim();
        const { selectedItems, orderTotal } = syncOrderPayload();

        if (!fullName || !email || !phone) {
            window.alert("Please fill in all required fields: Full Name, Email, and Phone Number.");
            return;
        }

        const deliveryStreet = document.getElementById("productStreet")?.value?.trim() || '';
        const deliveryCity = document.getElementById("productCity")?.value?.trim() || '';
        const deliveryProvince = document.getElementById("productProvince")?.value?.trim() || '';
        const deliveryZip = document.getElementById("productZip")?.value?.trim() || '';
        const deliveryCountry = document.getElementById("productDeliveryCountry")?.value?.trim() || 'Philippines';

        if (!deliveryStreet || !deliveryCity || !deliveryProvince || !deliveryZip) {
            window.alert("Please fill in your complete delivery address: Street, City, Province, and ZIP Code.");
            return;
        }

        if (!selectedItems.length) {
            window.alert("Please select at least one product.");
            return;
        }

        const paymentMethod = getSelectedPaymentMethod();

        // For COD: Submit directly to Django without screenshot
        if (paymentMethod === "cod") {
            inquirySubmit.disabled = true;
            inquirySubmit.textContent = "Sending...";

            try {
                const formData = new FormData(form);
                // Ensure payment_screenshot is not included for COD
                formData.delete("payment_screenshot");

                const response = await fetch(form.action, {
                    method: "POST",
                    body: formData,
                    credentials: "same-origin",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                const data = await response.json().catch(function () {
                    return {};
                });

                if (!response.ok) {
                    throw new Error(data.error || "Unable to submit product inquiry.");
                }

                // For COD: Close inquiry modal, open payment modal, and show thank you
                hideInquiryModal();
                
                // Store inquiry data for thank you screen
                storedInquiryData = {
                    full_name: fullName,
                    order_total: orderTotal,
                    payment_method: "cod"
                };
                
                // Open payment modal with COD
                setTimeout(function() {
                    openPaymentModal("cod", {});
                    // Show thank you screen instead of COD form
                    showPaymentModalThankYou();
                }, 300);
            } catch (error) {
                inquirySubmit.textContent = "Send Inquiry";
                syncOrderPayload();
                window.alert(error.message);
            }
            return;
        }

        // For GCash/Bank Transfer: store inquiry data, hide inquiry modal, and open payment modal
        inquirySubmit.disabled = true;
        inquirySubmit.textContent = "Sending...";
        const message = document.getElementById("productMessage").value.trim();
        storedInquiryData = {
            full_name: fullName,
            email: email,
            phone: phone,
            country_code: document.querySelector('[name="country_code"]')?.value || '+63',
            message: message,
            payment_method: paymentMethod,
            order_items: JSON.stringify(selectedItems),
            order_total: String(orderTotal),
            delivery_street: deliveryStreet,
            delivery_city: deliveryCity,
            delivery_province: deliveryProvince,
            delivery_zip: deliveryZip,
            delivery_country: deliveryCountry,
        };

        try {
            hideInquiryModal();
            
            // Prepare data for payment modal (no server submission yet)
            const paymentModalData = {
                selectedItems: selectedItems,
                orderTotal: orderTotal,
            };
            
            // Open payment modal
            openPaymentModal(paymentMethod, paymentModalData);
        } catch (error) {
            inquirySubmit.textContent = "Send Inquiry";
            window.alert(error.message);
        }
    });

    // Payment Modal Listeners
    paymentModalCloseButton.addEventListener("click", closePaymentModal);
    
    paymentModal.addEventListener("click", function (event) {
        if (event.target === paymentModal) {
            closePaymentModal();
        }
    });

    if (productPreviewButtons && productPreviewButtons.length) {
        productPreviewButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                if (!productPreviewOverlay || !productPreviewImg || !productPreviewName || !productPreviewCat) {
                    return;
                }
                productPreviewImg.src = button.dataset.productImg || "";
                productPreviewImg.alt = button.dataset.productName || "Product preview";
                productPreviewName.textContent = button.dataset.productName || "";
                productPreviewCat.textContent = button.dataset.productCat || "";
                productPreviewOverlay.style.display = "flex";
            });
        });
    }

    if (closeProductPreview) {
        closeProductPreview.addEventListener("click", function () {
            if (productPreviewOverlay) {
                productPreviewOverlay.style.display = "none";
            }
        });
    }

    if (productPreviewOverlay) {
        productPreviewOverlay.addEventListener("click", function (event) {
            if (event.target === productPreviewOverlay) {
                productPreviewOverlay.style.display = "none";
            }
        });
    }

    paymentScreenshotInput.addEventListener("change", function () {
        if (paymentScreenshotInput.files.length) {
            const file = paymentScreenshotInput.files[0];
            if (paymentFileName) {
                paymentFileName.textContent = file.name;
            }
            if (paymentFileSize) {
                paymentFileSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
            }
            if (paymentUploadArea) {
                paymentUploadArea.style.display = "none";
            }
            if (paymentFilePreview) {
                paymentFilePreview.style.display = "flex";
            }
            paymentModalSubmit.disabled = false;
            paymentModalSubmit.style.background = "#2d6e4e";
            paymentModalSubmit.style.cursor = "pointer";
            paymentModalNote.textContent = "Click 'Submit Payment' to complete your order.";
        } else {
            if (paymentUploadArea) {
                paymentUploadArea.style.display = "grid";
            }
            if (paymentFilePreview) {
                paymentFilePreview.style.display = "none";
            }
            paymentModalSubmit.disabled = true;
            paymentModalSubmit.style.background = "#ccc";
            paymentModalSubmit.style.cursor = "default";
            paymentModalNote.textContent = "Upload a screenshot to enable the submit button.";
        }
    });

    if (removePaymentFile) {
        removePaymentFile.addEventListener("click", function () {
            paymentScreenshotInput.value = "";
            if (paymentFilePreview) {
                paymentFilePreview.style.display = "none";
            }
            if (paymentUploadArea) {
                paymentUploadArea.style.display = "grid";
            }
            paymentModalSubmit.disabled = true;
            paymentModalSubmit.style.background = "#ccc";
            paymentModalSubmit.style.cursor = "default";
            paymentModalNote.textContent = "Upload a screenshot to enable the submit button.";
        });
    }

    paymentModalForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        // Validate payment screenshot file
        if (!paymentScreenshotInput.files.length) {
            window.alert("Please select a payment screenshot.");
            return;
        }

        const file = paymentScreenshotInput.files[0];
        const allowedExtensions = ['.jpg', '.jpeg', '.png'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        const maxFileSize = 5 * 1024 * 1024; // 5MB in bytes

        // Validate file extension
        if (!allowedExtensions.includes(fileExt)) {
            window.alert("Please upload a JPEG or PNG image only.");
            return;
        }

        // Validate file size
        if (file.size > maxFileSize) {
            window.alert("File size must not exceed 5MB.");
            return;
        }

        // Gather inquiry form data and payment screenshot
        const formData = new FormData();
        if (storedInquiryData) {
            Object.keys(storedInquiryData).forEach(function (key) {
                formData.append(key, storedInquiryData[key]);
            });
        } else {
            const fallbackFormData = new FormData(form);
            fallbackFormData.forEach(function (value, key) {
                formData.append(key, value);
            });
        }
        formData.append("payment_screenshot", file);
        if (storedInquiryData) {
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (csrfToken) {
                formData.append("csrfmiddlewaretoken", csrfToken);
            }
        }

        paymentModalSubmit.disabled = true;
        paymentModalSubmit.textContent = "Submitting...";

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            const data = await response.json().catch(function () {
                return {};
            });

            if (!response.ok) {
                throw new Error(data.error || "Unable to submit payment screenshot.");
            }

            showPaymentModalThankYou();
        } catch (error) {
            paymentModalSubmit.disabled = false;
            paymentModalSubmit.textContent = "Submit Payment";
            window.alert(error.message);
        }
    });

    syncOrderPayload();
    syncPaymentOptionState();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
        initProductFilters();
        initReceiptModal();
        initProductDetails();
        initOrderTracker();
        initContactHub();
        initAboutCorePrograms();
        initFooterFaqModal();
        initContactPhoneInput();
        initContactCountryPicker();
        initProductPhoneInput();
        initProductCountryPicker();
    });
} else {
    initProductFilters();
    initReceiptModal();
    initProductDetails();
    initOrderTracker();
    initContactHub();
    initAboutCorePrograms();
    initFooterFaqModal();
    initContactPhoneInput();
    initContactCountryPicker();
    initProductPhoneInput();
    initProductCountryPicker();
}


(function () {
    // Compatibility sidebar handler: keep non-desktop toggles in sync without
    // overriding the dedicated desktop persistence controller.
    var KEY = 'dashboard-sidebar-state'; // stored values: "expanded" or "collapsed"
    var LEGACY_KEY = 'dashboardSidebar';

  function applyState(state) {
    var shell = document.getElementById('dashboard-shell');
    if (!shell) return;
    var next = state === 'collapsed' ? 'collapsed' : 'expanded';
    shell.setAttribute('data-sidebar', next);

    var collapsed = next === 'collapsed';
        var toggles = document.querySelectorAll('#sidebar-toggle-inline, [data-toggle-sidebar], .sidebar-toggle, #sidebar-toggle');
    toggles.forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!collapsed));
      btn.setAttribute('data-collapsed', String(collapsed));
    });
  }

  function readState() {
        try {
            var current = localStorage.getItem(KEY);
            if (current === 'collapsed' || current === 'expanded') {
                return current;
            }

            var legacy = localStorage.getItem(LEGACY_KEY);
            if (legacy === 'collapsed' || legacy === 'expanded') {
                localStorage.setItem(KEY, legacy);
                return legacy;
            }

            return null;
        } catch (e) {
            return null;
        }
  }

  function writeState(state) {
        try {
            localStorage.setItem(KEY, state);
            // Keep legacy key mirrored for older scripts still reading it.
            localStorage.setItem(LEGACY_KEY, state);
        } catch (e) {}
  }

  function toggleState() {
    var shell = document.getElementById('dashboard-shell');
    if (!shell) return;
    var current = shell.dataset.sidebar === 'collapsed' ? 'collapsed' : 'expanded';
    var next = current === 'collapsed' ? 'expanded' : 'collapsed';
    applyState(next);
    writeState(next);
  }

  document.addEventListener('DOMContentLoaded', function () {
        var shell = document.getElementById('dashboard-shell');
        if (!shell) return;

    // 1) Apply persisted state (if inline script missed it)
    var persisted = readState();
    if (persisted) applyState(persisted);
        if (!persisted) applyState(shell.dataset.sidebar);

        // Remove boot class after state sync so page-to-page navigation does not flicker.
        requestAnimationFrame(function () {
            shell.classList.remove('sidebar-booting');
        });

    // 2) Attach toggles: adapt selectors if project uses a different toggler
        var toggles = document.querySelectorAll('#sidebar-toggle-inline, [data-toggle-sidebar], .sidebar-toggle, #sidebar-toggle');
    toggles.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        toggleState();
      });
    });
  });
})();

(function () {
    "use strict";

    // Delegated row-action dispatcher for shared table action buttons.
    function dispatchRowAction(action, button) {
        if (!action || !button) {
            return;
        }

        var td = button.closest("td");
        var row = button.closest("tr") || document;
        var id = button.getAttribute("data-id") || (td ? td.getAttribute("data-id") : null);
        var detail = { id: id, source: button };

        row.dispatchEvent(new CustomEvent("row:" + action, {
            bubbles: true,
            detail: detail
        }));

        if (action === "delete") {
            row.dispatchEvent(new CustomEvent("row:delete:confirm-requested", {
                bubbles: true,
                detail: detail
            }));
        }
    }

    function setActionMenuOpen(container, open) {
        if (!container) {
            return;
        }

        container.setAttribute("data-open", open ? "true" : "false");
        var trigger = container.querySelector(".table-actions-menu-trigger");
        if (trigger) {
            trigger.setAttribute("aria-expanded", open ? "true" : "false");
        }
    }

    function closeAllActionMenus(exceptContainer) {
        document.querySelectorAll(".table-actions[data-open='true']").forEach(function (container) {
            if (exceptContainer && container === exceptContainer) {
                return;
            }
            setActionMenuOpen(container, false);
        });
    }

    function initTableActionDispatch() {
        // Capture phase ensures dispatch still occurs even if page code stops propagation later.
        document.addEventListener("click", function (event) {
            var menuTrigger = event.target.closest(".table-actions-menu-trigger");
            if (menuTrigger) {
                event.preventDefault();
                event.stopPropagation();

                var actionGroup = menuTrigger.closest(".table-actions");
                var isOpen = actionGroup && actionGroup.getAttribute("data-open") === "true";
                closeAllActionMenus(actionGroup);
                setActionMenuOpen(actionGroup, !isOpen);
                return;
            }

            var button = event.target.closest(".table-action-btn");
            if (!button) {
                if (!event.target.closest(".table-actions")) {
                    closeAllActionMenus();
                }
                return;
            }

            closeAllActionMenus();
            dispatchRowAction(button.getAttribute("data-action"), button);
        }, true);

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeAllActionMenus();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initTableActionDispatch);
    } else {
        initTableActionDispatch();
    }
})();

(function () {
    "use strict";

    var EXIT_DURATION_MS = 120;
    var isNavigating = false;
    var prefetchedPanelUrls = new Set();
    var panelPayloadCache = new Map();
    var inflightPanelFetches = new Map();
    var activeTransitionToken = 0;
    var loadedPanelScriptSrc = new Set(Array.from(document.querySelectorAll("script[src]")).map(function (script) {
        try {
            return new URL(script.getAttribute("src"), window.location.href).href;
        } catch (_error) {
            return script.src || "";
        }
    }).filter(Boolean));

    function getPanelCacheKey(targetUrl) {
        return targetUrl.pathname + targetUrl.search;
    }

    function isSameDocumentTarget(targetUrl) {
        return targetUrl.pathname === window.location.pathname && targetUrl.search === window.location.search && targetUrl.hash === window.location.hash;
    }

    function isPanelNavigationTarget(targetUrl) {
        if (!targetUrl || targetUrl.origin !== window.location.origin) {
            return false;
        }

        if (targetUrl.pathname.indexOf("/logout") !== -1) {
            return false;
        }

        return !isSameDocumentTarget(targetUrl);
    }

    function extractPanelStyles(doc) {
        if (!doc || !doc.querySelectorAll) {
            return [];
        }

        var taggedStyles = Array.from(doc.querySelectorAll("head style[data-admin-panel-style]")).map(function (styleEl) {
            return {
                marker: styleEl.getAttribute("data-admin-panel-style") || "panel-style",
                css: styleEl.textContent || ""
            };
        }).filter(function (style) {
            return style.css && style.css.trim().length > 0;
        });

        if (taggedStyles.length) {
            return taggedStyles;
        }

        // Fallback for templates that were not tagged yet.
        return Array.from(doc.querySelectorAll("head style")).map(function (styleEl, index) {
            return {
                marker: "fallback-panel-style-" + index,
                css: styleEl.textContent || ""
            };
        }).filter(function (style) {
            return style.css && style.css.trim().length > 0;
        });
    }

    function syncPanelStyles(styles) {
        document.head.querySelectorAll("style[data-admin-panel-style]").forEach(function (styleEl) {
            styleEl.remove();
        });

        (styles || []).forEach(function (style, index) {
            var styleEl = document.createElement("style");
            styleEl.setAttribute("data-admin-panel-style", style.marker || ("panel-style-" + index));
            styleEl.textContent = style.css;
            document.head.appendChild(styleEl);
        });
    }

    function seedCurrentPanelStyles() {
        document.head.querySelectorAll("style").forEach(function (styleEl, index) {
            if (styleEl.hasAttribute("data-admin-panel-style")) {
                return;
            }

            var css = styleEl.textContent || "";
            if (!css.trim()) {
                return;
            }

            // Tailwind runtime style tags should not be managed by panel sync.
            if (css.indexOf("--tw-") >= 0 || css.indexOf("tailwindcss") >= 0) {
                return;
            }

            styleEl.setAttribute("data-admin-panel-style", "seeded-panel-style-" + index);
        });
    }

    function parsePanelPayload(html, targetUrl) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(html, "text/html");
        var nextContent = doc.querySelector("#dashboard-shell main > section[aria-label='Page content']");

        if (!nextContent) {
            return null;
        }

        return {
            key: getPanelCacheKey(targetUrl),
            title: doc.title || document.title,
            sectionClassName: nextContent.className || "",
            sectionHtml: nextContent.innerHTML,
            panelStyles: extractPanelStyles(doc)
        };
    }

    function fetchPanelPayload(targetUrl) {
        if (!isPanelNavigationTarget(targetUrl)) {
            return Promise.reject(new Error("Invalid panel target"));
        }

        var key = getPanelCacheKey(targetUrl);
        if (panelPayloadCache.has(key)) {
            return Promise.resolve(panelPayloadCache.get(key));
        }

        if (inflightPanelFetches.has(key)) {
            return inflightPanelFetches.get(key);
        }

        var request = fetch(targetUrl.href, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "admin-panel-prefetch"
            }
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("Panel fetch failed");
            }

            return response.text();
        }).then(function (html) {
            var payload = parsePanelPayload(html, targetUrl);
            if (!payload) {
                throw new Error("Panel payload missing");
            }

            panelPayloadCache.set(key, payload);
            return payload;
        }).finally(function () {
            inflightPanelFetches.delete(key);
        });

        inflightPanelFetches.set(key, request);
        return request;
    }

    function prefetchPanelUrl(targetUrl) {
        if (!isPanelNavigationTarget(targetUrl)) {
            return;
        }

        var key = getPanelCacheKey(targetUrl);
        if (prefetchedPanelUrls.has(key)) {
            return;
        }

        prefetchedPanelUrls.add(key);

        var link = document.createElement("link");
        link.rel = "prefetch";
        link.href = targetUrl.href;
        link.as = "document";
        document.head.appendChild(link);

        fetchPanelPayload(targetUrl).catch(function () {
            // Keep navigation resilient even when prefetch fails.
        });
    }

    function runEmbeddedScripts(container) {
        if (!container) {
            return;
        }

        container.querySelectorAll("script").forEach(function (oldScript) {
            var newScript = document.createElement("script");
            Array.from(oldScript.attributes).forEach(function (attr) {
                newScript.setAttribute(attr.name, attr.value);
            });

            if (newScript.src) {
                var resolvedSrc;
                try {
                    resolvedSrc = new URL(newScript.getAttribute("src"), window.location.href).href;
                } catch (_error) {
                    resolvedSrc = newScript.src;
                }

                if (loadedPanelScriptSrc.has(resolvedSrc)) {
                    oldScript.remove();
                    return;
                }

                loadedPanelScriptSrc.add(resolvedSrc);
            } else {
                newScript.textContent = oldScript.textContent;
            }

            oldScript.parentNode.replaceChild(newScript, oldScript);
        });
    }

    function setActiveSidebarLink(sidebar, targetUrl) {
        if (!sidebar || !targetUrl) {
            return;
        }

        var allLinks = Array.from(sidebar.querySelectorAll("a.sidebar-link[href]"));
        var targetSection = (targetUrl.hash || "").replace("#", "").trim();
        if (targetSection === "distribution-events-all") {
            targetSection = "distribution-outreach";
        }

        var hasSectionLinks = allLinks.some(function (anchor) {
            return !!anchor.getAttribute("data-section");
        });

        allLinks.forEach(function (anchor) {
            var url;
            try {
                url = new URL(anchor.href, window.location.href);
            } catch (_error) {
                return;
            }

            var linkSection = String(anchor.getAttribute("data-section") || "").trim();
            var samePath = url.pathname === targetUrl.pathname;
            var isSectionLink = !!linkSection;
            var isActive = false;

            if (hasSectionLinks && isSectionLink && samePath) {
                var expected = targetSection || "dashboard-overview";
                isActive = linkSection === expected;
            } else if (!hasSectionLinks || !isSectionLink) {
                isActive = samePath;
            }

            if (isActive) {
                anchor.setAttribute("aria-current", "page");
                anchor.classList.add("font-semibold", "bg-brand-100/70", "text-ink-900");
                anchor.classList.remove("font-medium", "text-ink-700");
                anchor.classList.add("active");
                anchor.classList.add("is-active");
                return;
            }

            anchor.removeAttribute("aria-current");
            anchor.classList.remove("font-semibold", "bg-brand-100/70", "text-ink-900");
            anchor.classList.add("font-medium", "text-ink-700");
            anchor.classList.remove("active");
            anchor.classList.remove("is-active");
        });
    }

    function dispatchPanelLifecycle(targetUrl) {
        var detail = {
            panelUrl: targetUrl.pathname + targetUrl.search + targetUrl.hash
        };

        document.dispatchEvent(new CustomEvent("admin:panel-switched", { detail: detail }));
        document.dispatchEvent(new CustomEvent("admin:panel-rendered", { detail: detail }));
    }

    function waitForExitAnimation(content) {
        return Promise.resolve();
    }

    function syncOpsPanelSurfaceClass(section) {
        if (!section || !section.classList) {
            return;
        }

        var hasOpsPanel = !!section.querySelector("#donations-page, #inventory-page, #payments-page");
        section.classList.toggle("admin-ops-surface", hasOpsPanel);
    }

    function applyPanelPayload(shell, sidebar, currentContent, payload, targetUrl, shouldPushHistory) {
        var nextSection = document.createElement("section");
        nextSection.setAttribute("aria-label", "Page content");
        if (payload.sectionClassName) {
            nextSection.className = payload.sectionClassName;
        }

        syncPanelStyles(payload.panelStyles);
        nextSection.innerHTML = payload.sectionHtml;
        syncOpsPanelSurfaceClass(nextSection);

        currentContent.replaceWith(nextSection);
        runEmbeddedScripts(nextSection);

        if (payload.title) {
            document.title = payload.title;
        }

        if (shouldPushHistory) {
            window.history.pushState({ panelUrl: targetUrl.href }, "", targetUrl.href);
        }

        setActiveSidebarLink(sidebar, targetUrl);
        dispatchPanelLifecycle(targetUrl);
        window.scrollTo(0, 0);
    }

    function bindSidebarPrefetch(sidebar) {
        if (!sidebar || sidebar.dataset.panelPrefetchBound === "true") {
            return;
        }

        sidebar.dataset.panelPrefetchBound = "true";

        function prefetchFromAnchor(anchor) {
            if (!anchor) {
                return;
            }

            try {
                prefetchPanelUrl(new URL(anchor.href, window.location.href));
            } catch (_error) {
                // Ignore malformed hrefs.
            }
        }

        sidebar.addEventListener("pointerenter", function (event) {
            prefetchFromAnchor(event.target.closest("a[href]"));
        }, true);

        sidebar.addEventListener("focusin", function (event) {
            prefetchFromAnchor(event.target.closest("a[href]"));
        });

        var idlePrefetch = function () {
            sidebar.querySelectorAll("a[href]").forEach(function (anchor) {
                try {
                    prefetchPanelUrl(new URL(anchor.href, window.location.href));
                } catch (_error) {
                    // Ignore malformed hrefs.
                }
            });
        };

        if (typeof window.requestIdleCallback === "function") {
            window.requestIdleCallback(idlePrefetch, { timeout: 1200 });
            return;
        }

        window.setTimeout(idlePrefetch, 320);
    }

    function initAdminPanelTransitions() {
        var shell = document.getElementById("dashboard-shell");
        if (!shell || !shell.classList.contains("admin-page")) {
            return;
        }

        var content = shell.querySelector("main > section[aria-label='Page content']");
        if (!content) {
            return;
        }

        syncOpsPanelSurfaceClass(content);

        var sidebar = document.getElementById("dashboard-sidebar");
        if (!sidebar) {
            return;
        }

        seedCurrentPanelStyles();

        bindSidebarPrefetch(sidebar);

        if (sidebar.dataset.panelTransitionBound === "true") {
            return;
        }
        sidebar.dataset.panelTransitionBound = "true";

        window.addEventListener("popstate", function () {
            var targetUrl;
            try {
                targetUrl = new URL(window.location.href);
            } catch (_error) {
                window.location.reload();
                return;
            }

            var activeToken = ++activeTransitionToken;

            fetchPanelPayload(targetUrl).then(function (payload) {
                if (activeToken !== activeTransitionToken) {
                    return;
                }

                var current = shell.querySelector("main > section[aria-label='Page content']");
                if (!current) {
                    window.location.reload();
                    return;
                }

                applyPanelPayload(shell, sidebar, current, payload, targetUrl, false);
            }).catch(function () {
                window.location.reload();
            });
        });

        sidebar.addEventListener("click", function (event) {
            var link = event.target.closest("a[href]");
            if (!link) {
                return;
            }

            if (isNavigating) {
                event.preventDefault();
                return;
            }

            if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                return;
            }

            if (link.target && link.target !== "_self") {
                return;
            }

            var href = link.getAttribute("href");
            if (!href || href.indexOf("javascript:") === 0 || href.indexOf("#") === 0) {
                return;
            }

            var targetUrl;
            try {
                targetUrl = new URL(link.href, window.location.href);
            } catch (_error) {
                return;
            }

            if (!isPanelNavigationTarget(targetUrl)) {
                return;
            }

            event.preventDefault();
            isNavigating = true;
            setActiveSidebarLink(sidebar, targetUrl);
            window.location.assign(targetUrl.href);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAdminPanelTransitions);
    } else {
        initAdminPanelTransitions();
    }
})();

(function () {
    "use strict";

    function initSettingsPage() {
        var shell = document.getElementById("settings-shell");
        var form = document.getElementById("settings-form");
        var saveBtn = document.getElementById("save-btn");
        var discardBtn = document.getElementById("discard-btn");
        var saveStateIndicator = document.getElementById("settings-save-state");
        var inlineStatus = document.getElementById("settings-inline-status");
        var toast = document.getElementById("settings-toast");
        var pageTitle = document.getElementById("settings-page-title");
        var pageDescription = document.getElementById("settings-page-description");
        var floatingBar = document.getElementById("settings-floating-bar");
        var floatingSaveBtn = document.querySelector("[data-floating-save]");
        var floatingDiscardBtn = document.querySelector("[data-floating-discard]");
        var panelSections = shell ? shell.querySelectorAll("[data-settings-panel]") : [];

        if (!shell || !form || !saveBtn || !discardBtn) {
            return;
        }

        function captureState() {
            var state = {};
            var inputs = form.querySelectorAll("[name]");

            inputs.forEach(function (el) {
                var name = el.name;
                if (!name) {
                    return;
                }

                if (!Object.prototype.hasOwnProperty.call(state, name)) {
                    state[name] = [];
                }

                if (el.type === "checkbox" || el.type === "radio") {
                    if (el.checked) {
                        state[name].push(el.value || "on");
                    }
                    return;
                }

                if (el instanceof HTMLSelectElement && el.multiple) {
                    Array.from(el.options).forEach(function (option) {
                        if (option.selected) {
                            state[name].push(option.value);
                        }
                    });
                    return;
                }

                state[name] = [el.value];
            });

            return state;
        }

        function hashState(state) {
            return Object.keys(state)
                .sort()
                .map(function (key) {
                    var values = (state[key] || []).slice().sort();
                    return key + "=" + values.join("||");
                })
                .join("&");
        }

        function applyState(state) {
            var inputs = form.querySelectorAll("[name]");

            inputs.forEach(function (el) {
                var values = state[el.name] || [];

                if (el.type === "checkbox" || el.type === "radio") {
                    var candidate = el.value || "on";
                    el.checked = values.indexOf(candidate) > -1;
                    return;
                }

                if (el instanceof HTMLSelectElement && el.multiple) {
                    Array.from(el.options).forEach(function (option) {
                        option.selected = values.indexOf(option.value) > -1;
                    });
                    return;
                }

                el.value = values.length ? values[0] : "";
            });
        }

        function showToast(message) {
            if (!toast) {
                return;
            }

            toast.textContent = message;
            toast.classList.add("is-visible");
            window.clearTimeout(showToast._timer);
            showToast._timer = window.setTimeout(function () {
                toast.classList.remove("is-visible");
            }, 2100);
        }

        function setStatus(message) {
            if (inlineStatus) {
                inlineStatus.textContent = message || "";
            }
        }

        function setSaveStateLabel(message) {
            if (saveStateIndicator) {
                saveStateIndicator.textContent = message;
            }
        }

        var snapshotState = captureState();
        var snapshotHash = hashState(snapshotState);
        var isSaving = false;
        var isDirty = false;

        function refreshDirtyState() {
            isDirty = hashState(captureState()) !== snapshotHash;
            saveBtn.disabled = !isDirty || isSaving;
            discardBtn.disabled = !isDirty || isSaving;

            if (floatingSaveBtn) {
                floatingSaveBtn.disabled = !isDirty || isSaving;
            }

            if (floatingDiscardBtn) {
                floatingDiscardBtn.disabled = !isDirty || isSaving;
            }

            if (floatingBar) {
                var showFloating = isDirty && !isSaving;
                floatingBar.classList.toggle("is-visible", showFloating);
                floatingBar.setAttribute("aria-hidden", showFloating ? "false" : "true");
            }

            if (!isDirty && !isSaving) {
                setSaveStateLabel("No unsaved changes");
                setStatus("All changes saved.");
            }

            if (isDirty && !isSaving) {
                setSaveStateLabel("Unsaved changes");
                setStatus("Unsaved changes are ready to save.");
            }
        }

        function markSaved() {
            snapshotState = captureState();
            snapshotHash = hashState(snapshotState);
            isSaving = false;
            setSaveStateLabel("Saved recently");
            setStatus("Changes saved.");
            refreshDirtyState();
            showToast("Settings saved successfully.");
            window.setTimeout(function () {
                if (!isDirty) {
                    setSaveStateLabel("No unsaved changes");
                }
            }, 1800);
        }

        function handleSave(event) {
            event.preventDefault();

            if (!isDirty || isSaving) {
                return;
            }

            isSaving = true;
            saveBtn.disabled = true;
            discardBtn.disabled = true;
            setSaveStateLabel("Saving...");
            setStatus("Saving changes...");

            window.setTimeout(markSaved, 520);
        }

        function handleDiscard(event) {
            event.preventDefault();

            if (!isDirty || isSaving) {
                return;
            }

            applyState(snapshotState);
            setSaveStateLabel("No unsaved changes");
            setStatus("Changes discarded.");
            refreshDirtyState();
            showToast("Changes discarded.");
        }

        form.addEventListener("input", refreshDirtyState);
        form.addEventListener("change", refreshDirtyState);
        form.addEventListener("submit", handleSave);
        saveBtn.addEventListener("click", handleSave);
        discardBtn.addEventListener("click", handleDiscard);

        if (floatingSaveBtn) {
            floatingSaveBtn.addEventListener("click", handleSave);
        }

        if (floatingDiscardBtn) {
            floatingDiscardBtn.addEventListener("click", handleDiscard);
        }

        window.addEventListener("beforeunload", function (event) {
            if (!isDirty) {
                return;
            }
            event.preventDefault();
            event.returnValue = "";
        });

        var navLinks = shell.querySelectorAll("[data-settings-nav]");
        var currentSection = shell.getAttribute("data-settings-section") || "general";

        function setActiveSection(sectionName) {
            currentSection = sectionName || "general";
            shell.setAttribute("data-settings-section", currentSection);

            navLinks.forEach(function (link) {
                var isActive = link.getAttribute("data-settings-nav") === currentSection;
                link.classList.toggle("active", isActive);
                link.setAttribute("aria-current", isActive ? "page" : "false");

                if (isActive) {
                    if (pageTitle && link.dataset.settingsTitle) {
                        pageTitle.textContent = link.dataset.settingsTitle;
                    }

                    if (pageDescription && link.dataset.settingsDescription) {
                        pageDescription.textContent = link.dataset.settingsDescription;
                    }
                }
            });

            panelSections.forEach(function (panel) {
                var isTarget = panel.getAttribute("data-settings-panel") === currentSection;
                panel.hidden = !isTarget;
            });
        }

        navLinks.forEach(function (link) {
            link.addEventListener("click", function (event) {
                event.preventDefault();
                setActiveSection(link.getAttribute("data-settings-nav") || "general");
            });
        });

        setActiveSection(currentSection);

        refreshDirtyState();
        setSaveStateLabel("No unsaved changes");
        setStatus("All changes saved.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSettingsPage);
    } else {
        initSettingsPage();
    }
})();

(function () {
    "use strict";

    var SELECTORS = ".page-bg, .background-spacer, .decorative-gradient, .bottom-hero, .page-gradient";

    function removeDecorative(root) {
        var scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll(SELECTORS).forEach(function (el) {
            if (el.closest(".admin-page")) {
                el.remove();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            removeDecorative(document);
        });
    } else {
        removeDecorative(document);
    }

    window.addEventListener("load", function () {
        removeDecorative(document);
    });

    if ("MutationObserver" in window) {
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (!(node instanceof Element)) {
                        return;
                    }

                    if (node.matches && node.matches(SELECTORS)) {
                        if (node.closest(".admin-page")) {
                            node.remove();
                        }
                    } else if (node.querySelectorAll) {
                        removeDecorative(node);
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        var tries = 0;
        var int = setInterval(function () {
            removeDecorative(document);
            tries += 1;
            if (tries > 8) {
                clearInterval(int);
            }
        }, 300);
    }
})();

(function () {
  "use strict";

  function initHeaderDropdowns() {
    var toggles = document.querySelectorAll("[data-toggle]");
    if (!toggles.length) return;
    var openDropdown = null;

    function closeDropdown(drop) {
      try {
        if (!drop) return;
        drop.setAttribute("aria-hidden", "true");
        drop.removeAttribute("data-open");
        drop.hidden = true;
        var toggle = document.querySelector('[data-toggle="' + drop.dataset.dropdown + '"]');
        if (toggle) toggle.setAttribute("aria-expanded", "false");
        if (openDropdown === drop) openDropdown = null;
      } catch (e) { console.warn("closeDropdown", e); }
    }

    function openDropdownFor(drop) {
      try {
        if (!drop) return;
        if (openDropdown && openDropdown !== drop) closeDropdown(openDropdown);
        drop.hidden = false;
        drop.setAttribute("aria-hidden", "false");
        drop.setAttribute("data-open", "true");
        var toggle = document.querySelector('[data-toggle="' + drop.dataset.dropdown + '"]');
        if (toggle) toggle.setAttribute("aria-expanded", "true");
        openDropdown = drop;
      } catch (e) { console.warn("openDropdown", e); }
    }

    toggles.forEach(function (toggle) {
      var key = toggle.dataset.toggle;
      if (!key) return;
      var drop = document.querySelector('[data-dropdown="' + key + '"]');
      // ensure dropdown sits inside header for absolute anchoring
      if (drop && !drop.closest("#app-header")) {
        var header = document.getElementById("app-header");
        if (header) header.appendChild(drop);
      }
      toggle.addEventListener("click", function (ev) {
        ev.stopPropagation();
        try {
          if (!drop) return;
          var isOpen = drop.getAttribute("data-open") === "true" || drop.getAttribute("aria-hidden") === "false";
          if (isOpen) closeDropdown(drop);
                    else {
                        openDropdownFor(drop);
                        if (key === "notifications") {
                            refreshNotificationsFromServer();
                        }
                    }
        } catch (err) { console.error("toggle error", err); }
      });
    });

    // close on outside click
    document.addEventListener("click", function (ev) {
      if (!openDropdown) return;
      var node = ev.target;
      var toggle = document.querySelector('[data-toggle="' + (openDropdown && openDropdown.dataset.dropdown) + '"]');
      if (!openDropdown.contains(node) && !(toggle && toggle.contains(node))) closeDropdown(openDropdown);
    });

    // close on Escape
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && openDropdown) closeDropdown(openDropdown);
    });

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

        function escapeHtml(value) {
            return String(value == null ? "" : value)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }

        function notificationIconMarkup(type) {
            if (type === "post_like") {
                return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21s-6.5-4.4-6.5-10A3.5 3.5 0 0 1 9 7.5c1.2 0 2.3.6 3 1.6.7-1 1.8-1.6 3-1.6a3.5 3.5 0 0 1 3.5 3.5c0 5.6-6.5 10-6.5 10Z"/></svg>';
            }

            if (type === "post_comment") {
                return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z"/></svg>';
            }

            return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M8 8h8M8 12h6M4 4h16v12H7l-3 4V4Z"/></svg>';
        }

        function notificationItemMarkup(notification) {
            var isUnread = !notification.is_read;
            return [
                '<button type="button" class="notif-item' + (isUnread ? ' unread' : ' read') + '" role="listitem" tabindex="0" data-id="' + escapeHtml(notification.id) + '" data-unread="' + (isUnread ? 'true' : 'false') + '" data-href="' + escapeHtml(notification.url || '') + '">',
                '<span class="notif-dot' + (isUnread ? ' unread' : ' read') + '" aria-hidden="true"></span>',
                '<span class="notif-type-icon" aria-hidden="true">' + notificationIconMarkup(notification.type) + '</span>',
                '<span class="notif-text">',
                '<span class="notif-title">' + escapeHtml(notification.title || '') + '</span>',
                '<span class="notif-meta">' + escapeHtml(notification.time_ago || '') + '</span>',
                '</span>',
                '</button>'
            ].join("");
        }

        function renderNotificationsList(notifications) {
            var list = document.getElementById("notif-list");
            if (!list) {
                return;
            }

            var items = Array.isArray(notifications) ? notifications : [];
            if (!items.length) {
                list.innerHTML = '<p class="notif-group-title" role="listitem">No notifications yet.</p>';
                return;
            }

            var unreadItems = items.filter(function (notification) {
                return !notification.is_read;
            });
            var readItems = items.filter(function (notification) {
                return !!notification.is_read;
            });
            var sections = [];

            if (unreadItems.length) {
                sections.push([
                    '<section class="notif-group" role="group" aria-labelledby="notif-group-unread">',
                    '<h4 class="notif-group-title" id="notif-group-unread">Unread</h4>',
                    unreadItems.map(notificationItemMarkup).join(""),
                    '</section>'
                ].join(""));
            }

            if (readItems.length) {
                sections.push([
                    '<section class="notif-group" role="group" aria-labelledby="notif-group-earlier">',
                    '<h4 class="notif-group-title" id="notif-group-earlier">Earlier</h4>',
                    readItems.map(notificationItemMarkup).join(""),
                    '</section>'
                ].join(""));
            }

            list.innerHTML = sections.join("");
        }

        function refreshNotificationsFromServer() {
            var dropdown = document.getElementById("dropdown-notifications");
            var endpoint = dropdown ? dropdown.getAttribute("data-notifications-feed-endpoint") : "";
            if (!endpoint) {
                return;
            }

            fetch(endpoint, {
                method: "GET",
                credentials: "same-origin"
            }).then(function (response) {
                return response.json().catch(function () {
                    return {};
                }).then(function (payload) {
                    if (!response.ok) {
                        return;
                    }

                    updateNotificationBadges(payload && payload.unreadCount);
                    renderNotificationsList(payload && payload.notifications);
                });
            }).catch(function () {
            });
        }

        var notificationsRefreshTimer = null;

        function startNotificationsPolling() {
            if (notificationsRefreshTimer) {
                return;
            }

            refreshNotificationsFromServer();
            notificationsRefreshTimer = window.setInterval(function () {
                if (document.hidden) {
                    return;
                }

                refreshNotificationsFromServer();
            }, 15000);

            document.addEventListener("visibilitychange", function () {
                if (!document.hidden) {
                    refreshNotificationsFromServer();
                }
            });
        }

        function updateNotificationBadges(unreadCount) {
            var count = Math.max(0, Number(unreadCount) || 0);
            var toggle = document.getElementById("header-notifications");
            var badge = document.getElementById("header-notifications-badge");
            var countBadge = document.getElementById("notif-count");
            var markAllButton = document.getElementById("mark-all-read");

            if (toggle) {
                toggle.setAttribute("data-notifications", String(count));
            }
            if (badge) {
                badge.textContent = String(count);
                if (count > 0) badge.removeAttribute("hidden");
                else badge.setAttribute("hidden", "");
            }
            if (countBadge) {
                countBadge.textContent = String(count);
            }
            if (markAllButton) {
                markAllButton.disabled = count <= 0;
            }
        }

        function markNotificationRead(item, callback) {
            var dropdown = document.getElementById("dropdown-notifications");
            var endpoint = dropdown ? dropdown.getAttribute("data-mark-read-endpoint") : "";
            var notificationId = item ? String(item.getAttribute("data-id") || "").trim() : "";
            var onDone = typeof callback === "function" ? callback : function () {};

            if (!endpoint || !notificationId) {
                onDone();
                return;
            }

            if (item.getAttribute("data-unread") !== "true") {
                onDone();
                return;
            }

            var body = new URLSearchParams();
            body.append("notification_id", notificationId);

            fetch(endpoint, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-CSRFToken": getCookie("csrftoken") || ""
                },
                body: body.toString(),
            }).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (payload) {
                    if (!response.ok) {
                        return;
                    }
                    item.setAttribute("data-unread", "false");
                    item.classList.remove("unread");
                    item.classList.add("read");
                    var dot = item.querySelector(".notif-dot");
                    if (dot) {
                        dot.classList.remove("unread");
                        dot.classList.add("read");
                    }
                    updateNotificationBadges(payload && payload.unreadCount);
                });
            }).catch(function () {
            }).finally(function () {
                onDone();
            });
        }

        function markAllNotificationsRead() {
            var dropdown = document.getElementById("dropdown-notifications");
            var endpoint = dropdown ? dropdown.getAttribute("data-mark-all-read-endpoint") : "";
            if (!endpoint) return;

            fetch(endpoint, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") || ""
                },
            }).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (payload) {
                    if (!response.ok) {
                        return;
                    }
                    document.querySelectorAll(".notif-item.unread").forEach(function (item) {
                        item.classList.remove("unread");
                        item.classList.add("read");
                        item.setAttribute("data-unread", "false");
                        var dot = item.querySelector(".notif-dot");
                        if (dot) {
                            dot.classList.remove("unread");
                            dot.classList.add("read");
                        }
                    });
                    updateNotificationBadges(payload && payload.unreadCount);
                });
            }).catch(function () {
            });
        }

        var markAllButton = document.getElementById("mark-all-read");
        if (markAllButton) {
            markAllButton.addEventListener("click", function (ev) {
                ev.preventDefault();
                markAllNotificationsRead();
            });
        }

        startNotificationsPolling();

        // safe item handler: navigation or form submit (no exceptions)
    document.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".notif-item, .user-item, .user-signout");
      if (!btn) return;
      try {
        var href = btn.dataset.href || btn.getAttribute("href");
        if (href && btn.classList.contains("notif-item")) {
                    ev.preventDefault();
                    markNotificationRead(btn, function () {
                        window.location.href = href;
                    });
        }
        // signout form can submit naturally; do not preventDefault
      } catch (err) { console.error("dropdown item handler error", err); }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initHeaderDropdowns);
  else initHeaderDropdowns();
})();

(function () {
    "use strict";

    var scrollFxObserver = null;

    function revealElement(el) {
        el.setAttribute("data-scrollfx-state", "visible");
    }

    function initSafeScrollFx() {
        if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }

        if (scrollFxObserver) {
            scrollFxObserver.disconnect();
            scrollFxObserver = null;
        }

        var items = [];

        function register(selector, options) {
            var nodes = document.querySelectorAll(selector);
            nodes.forEach(function (el, index) {
                items.push({
                    el: el,
                    hiddenTransform: options.hiddenTransform,
                    duration: options.duration,
                    delayMs: (options.staggerMs || 0) * index,
                });
            });
        }

        var onHome = Boolean(document.querySelector(".hero-grid") && document.querySelector(".feature-grid"));
        var onAbout = Boolean(document.querySelector(".about-page"));
        var onProducts = Boolean(document.querySelector(".products-page"));
        var onContact = Boolean(document.querySelector(".contact-page"));

        if (onHome) {
            register(".hero-grid > :first-child", {
                hiddenTransform: "translateX(-50px)",
                duration: 800,
                staggerMs: 0,
            });
            register(".hero-image-wrap", {
                hiddenTransform: "translateX(50px)",
                duration: 800,
                staggerMs: 0,
            });
            register(".section-title", {
                hiddenTransform: "translateY(24px)",
                duration: 700,
                staggerMs: 0,
            });
            register(".feature-grid .feature-card", {
                hiddenTransform: "translateY(28px)",
                duration: 700,
                staggerMs: 100,
            });
        }

        if (onAbout) {
            register(".about-grid:not(.about-grid-reverse) > :first-child", {
                hiddenTransform: "translateX(-50px)",
                duration: 800,
                staggerMs: 0,
            });
            register(".about-grid:not(.about-grid-reverse) > :last-child", {
                hiddenTransform: "translateX(50px)",
                duration: 800,
                staggerMs: 0,
            });
            register(".about-grid.about-grid-reverse > :first-child", {
                hiddenTransform: "translateX(50px)",
                duration: 800,
                staggerMs: 0,
            });
            register(".about-grid.about-grid-reverse > :last-child", {
                hiddenTransform: "translateX(-50px)",
                duration: 800,
                staggerMs: 0,
            });
            register(".program-grid .program-card", {
                hiddenTransform: "translateY(28px)",
                duration: 700,
                staggerMs: 100,
            });
        }

        if (onProducts) {
            register(".products-hero", {
                hiddenTransform: "translateY(24px)",
                duration: 700,
                staggerMs: 0,
            });
            register(".products-toolbar", {
                hiddenTransform: "translateY(24px)",
                duration: 700,
                staggerMs: 0,
            });
            register(".products-grid .product-card", {
                hiddenTransform: "translateY(24px)",
                duration: 700,
                staggerMs: 120,
            });
        }

        if (onContact) {
            register(".contact-hero", {
                hiddenTransform: "none",
                duration: 650,
                staggerMs: 0,
            });
            register(".contact-path-grid .contact-path-card", {
                hiddenTransform: "none",
                duration: 650,
                staggerMs: 100,
            });
            register(".contact-workspace", {
                hiddenTransform: "none",
                duration: 650,
                staggerMs: 0,
            });
        }

        if (!items.length) {
            return;
        }

        document.documentElement.classList.add("js-scrollfx");

        items.forEach(function (item) {
            item.el.classList.add("scrollfx");
            item.el.style.setProperty("--scrollfx-duration", String(item.duration || 700) + "ms");
            item.el.style.setProperty("--scrollfx-delay", String(item.delayMs || 0) + "ms");
            item.el.style.setProperty("--scrollfx-hidden-transform", item.hiddenTransform || "translateY(24px)");
            item.el.setAttribute("data-scrollfx-state", "hidden");
        });

        function revealInViewport() {
            var vh = window.innerHeight || document.documentElement.clientHeight;
            items.forEach(function (item) {
                if (item.el.getAttribute("data-scrollfx-state") === "visible") {
                    return;
                }

                var rect = item.el.getBoundingClientRect();
                if (rect.top < vh - 100 && rect.bottom > 0) {
                    revealElement(item.el);
                }
            });
        }

        if (!("IntersectionObserver" in window)) {
            items.forEach(function (item) {
                revealElement(item.el);
            });
            return;
        }

        scrollFxObserver = new IntersectionObserver(function (entries, observer) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) {
                    return;
                }

                revealElement(entry.target);
                observer.unobserve(entry.target);
            });
        }, {
            threshold: 0.15,
            rootMargin: "0px 0px -100px 0px",
        });

        items.forEach(function (item) {
            scrollFxObserver.observe(item.el);
        });

        window.setTimeout(revealInViewport, 90);
        window.setTimeout(revealInViewport, 420);

        // Final fail-safe: never leave content hidden if observer misses an element.
        window.setTimeout(function () {
            items.forEach(function (item) {
                if (item.el.getAttribute("data-scrollfx-state") !== "visible") {
                    revealElement(item.el);
                }
            });
        }, 1800);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSafeScrollFx);
    } else {
        initSafeScrollFx();
    }

    window.addEventListener("pageshow", initSafeScrollFx);
})();

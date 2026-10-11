(function () {
    const cashForm = document.getElementById('donationFunnel');
    const itemForm = document.getElementById('itemPledgeFunnel');
    const modeSwitch = document.getElementById('donateModeSwitch');
    const formCard = document.querySelector('.donate-form-card');
    const progress = document.querySelector('.donate-progress');
    const progressItems = Array.from(document.querySelectorAll('.donate-progress-item'));
    const error = document.getElementById('donateFormError');
    const status = document.getElementById('donateStepStatus');
    const configElement = document.getElementById('donation-config');
    if (!cashForm || !itemForm || !modeSwitch || !formCard || !progress || !configElement) return;

    const config = JSON.parse(configElement.textContent || '{}');
    const itemNameInput = itemForm.querySelector('[name="item_name"]');
    const categoryInput = itemForm.querySelector('[name="category"]');
    const quantityInput = itemForm.querySelector('[name="quantity"]');
    const conditionInput = itemForm.querySelector('[name="condition"]');
    const descriptionInput = itemForm.querySelector('[name="description"]');
    const photoInput = itemForm.querySelector('[name="photo"]');
    const donorNameInput = itemForm.querySelector('[name="donor_name"]');
    const anonymousInput = itemForm.querySelector('[name="is_anonymous"]');
    const deliveryOptions = Array.from(itemForm.querySelectorAll('[name="delivery_method"]'));
    const deliveryGroups = {
        drop_off: document.getElementById('pledgeDropoffDetails'),
        pickup: document.getElementById('pledgePickupDetails'),
        courier: document.getElementById('pledgeCourierDetails')
    };
    const cashLabels = ['Amount', 'Send', 'Confirm', 'Thank you'];
    const itemLabels = ['Item details', 'Delivery', 'Confirm', 'Thank you'];
    const cashCopy = {
        kicker: document.querySelector('.donate-give-grid > div:first-child .donate-kicker').textContent,
        heading: document.querySelector('.donate-give-grid > div:first-child .donate-section-heading').textContent,
        copy: document.querySelector('.donate-give-grid > div:first-child .donate-section-copy').textContent,
        helper: cashForm.querySelector('[data-step="1"] .donate-section-copy').textContent,
        note: document.getElementById('donateImpact').textContent,
        photoImpact: document.getElementById('givePhotoImpact').textContent
    };
    const leftKicker = document.querySelector('.donate-give-grid > div:first-child .donate-kicker');
    const leftHeading = document.querySelector('.donate-give-grid > div:first-child .donate-section-heading');
    const leftCopy = document.querySelector('.donate-give-grid > div:first-child .donate-section-copy');
    const cashHelper = cashForm.querySelector('[data-step="1"] .donate-section-copy');
    const cashImpact = document.getElementById('donateImpact');
    const photoImpact = document.getElementById('givePhotoImpact');
    let mode = 'cash';
    let locked = false;
    let itemStep = 1;

    formCard.insertBefore(modeSwitch, progress);
    cashForm.after(itemForm);
    modeSwitch.hidden = false;

    function showError(message) {
        error.textContent = message || '';
        error.hidden = !message;
    }

    function updateSwitch() {
        modeSwitch.querySelectorAll('[data-donation-mode]').forEach(button => {
            const selected = button.dataset.donationMode === mode;
            button.classList.toggle('active', selected);
            button.disabled = locked;
            button.setAttribute('aria-pressed', selected ? 'true' : 'false');
        });
    }

    function setMode(nextMode) {
        if (locked || (nextMode !== 'cash' && nextMode !== 'item')) return;
        mode = nextMode;
        const isItem = mode === 'item';
        cashForm.hidden = isItem;
        itemForm.hidden = !isItem;
        progress.setAttribute('aria-label', isItem ? 'Item donation progress' : 'Donation progress');
        progressItems.forEach((item, index) => {
            item.textContent = (isItem ? itemLabels : cashLabels)[index];
        });
        leftKicker.textContent = isItem ? 'Give in-kind' : cashCopy.kicker;
        leftHeading.textContent = isItem ? 'Your generosity, made practical.' : cashCopy.heading;
        leftCopy.textContent = isItem
            ? "Tell us what you'd like to give so our team can arrange it."
            : cashCopy.copy;
        cashHelper.textContent = isItem
            ? "Tell us what you'd like to give so our team can arrange it."
            : cashCopy.helper;
        cashImpact.textContent = isItem
            ? 'Your item pledge helps provide practical support for our community.'
            : cashCopy.note;
        photoImpact.textContent = isItem
            ? 'Tell us what you would like to give so our team can arrange it.'
            : cashCopy.photoImpact;
        if (isItem) {
            setItemStep(1, false);
        } else {
            document.querySelector('[data-step="1"]').hidden = false;
            progressItems.forEach(item => item.classList.toggle('active', item.dataset.progress === '1'));
            status.textContent = 'Step 1 of 4';
        }
        updateSwitch();
        showError('');
    }

    function setLocked() {
        locked = true;
        updateSwitch();
    }

    function setItemStep(nextStep, shouldLock = true) {
        itemStep = nextStep;
        if (shouldLock && nextStep > 1) setLocked();
        let activePanel;
        itemForm.querySelectorAll('[data-item-step]').forEach(panel => {
            const isActive = Number(panel.dataset.itemStep) === itemStep;
            panel.hidden = !isActive;
            panel.classList.remove('is-entering');
            if (isActive) activePanel = panel;
        });
        if (activePanel) {
            void activePanel.offsetWidth;
            activePanel.classList.add('is-entering');
            activePanel.addEventListener('animationend', () => activePanel.classList.remove('is-entering'), { once: true });
        }
        progressItems.forEach(item => item.classList.toggle('active', Number(item.dataset.progress) <= itemStep));
        status.textContent = 'Step ' + itemStep + ' of 4';
        showError('');
        document.getElementById('give').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function checkedDeliveryMethod() {
        const selected = deliveryOptions.find(option => option.checked);
        return selected ? selected.value : '';
    }

    function updateDeliveryFields() {
        const selectedMethod = checkedDeliveryMethod();
        Object.entries(deliveryGroups).forEach(([method, group]) => {
            const isActive = method === selectedMethod;
            group.hidden = !isActive;
            group.querySelectorAll('input, textarea').forEach(input => {
                input.disabled = !isActive;
                input.required = isActive;
            });
        });
    }

    function updateAnonymousField() {
        donorNameInput.disabled = anonymousInput.checked;
        donorNameInput.required = false;
        if (anonymousInput.checked) donorNameInput.value = '';
        updateSummary();
    }

    function fieldValue(name) {
        const field = itemForm.elements.namedItem(name);
        return field && 'value' in field ? field.value.trim() : '';
    }

    function summaryEntries() {
        const deliveryMethod = checkedDeliveryMethod();
        const entries = [
            ['Item', fieldValue('item_name')],
            ['Category', categoryInput.selectedOptions[0] && categoryInput.value ? categoryInput.selectedOptions[0].text : ''],
            ['Quantity', fieldValue('quantity')],
            ['Condition', conditionInput.selectedOptions[0] && conditionInput.value ? conditionInput.selectedOptions[0].text : ''],
            ['Description', fieldValue('description') || 'Not provided'],
            ['Photo', photoInput.files[0] ? photoInput.files[0].name : 'Not provided']
        ];
        if (deliveryMethod === 'drop_off') {
            entries.push(['Delivery', 'Drop off']);
            entries.push(['Drop-off details', (deliveryGroups.drop_off.textContent || '').replace(/\s+/g, ' ').trim()]);
        } else if (deliveryMethod === 'pickup') {
            entries.push(['Delivery', 'Pick up']);
            entries.push(['Pickup address', fieldValue('delivery_address')]);
            entries.push(['Preferred date', fieldValue('preferred_date')]);
            entries.push(['Preferred time', fieldValue('preferred_time')]);
        } else if (deliveryMethod === 'courier') {
            entries.push(['Delivery', 'Send by courier']);
            entries.push(['Courier', fieldValue('courier_name')]);
            entries.push(['Tracking number', fieldValue('tracking_number')]);
        }
        entries.push(['Name', anonymousInput.checked ? 'Anonymous' : fieldValue('donor_name')]);
        entries.push(['Phone', fieldValue('donor_phone')]);
        entries.push(['Email', fieldValue('donor_email')]);
        entries.push(['Status', 'Pending - awaiting confirmation']);
        return entries;
    }

    function updateSummary() {
        const summary = document.getElementById('pledgeSummary');
        if (!summary) return;
        summary.replaceChildren();
        summaryEntries().forEach(([label, value]) => {
            const row = document.createElement('div');
            row.className = 'donate-summary-row';
            const title = document.createElement('span');
            title.textContent = label;
            const content = document.createElement('strong');
            content.textContent = value || 'Not provided';
            row.append(title, content);
            summary.appendChild(row);
        });
    }

    function validatePanel(step) {
        const panel = itemForm.querySelector('[data-item-step="' + step + '"]');
        const invalidInput = Array.from(panel.querySelectorAll('input, select, textarea')).find(input => !input.disabled && !input.checkValidity());
        if (invalidInput) {
            invalidInput.reportValidity();
            return false;
        }
        return true;
    }

    modeSwitch.querySelectorAll('[data-donation-mode]').forEach(button => {
        button.addEventListener('click', () => setMode(button.dataset.donationMode));
    });
    cashForm.querySelectorAll('[data-next]').forEach(button => {
        button.addEventListener('click', () => {
            if (Number(button.dataset.next) > 1) setLocked();
        });
    });
    itemForm.querySelectorAll('[data-item-next]').forEach(button => {
        button.addEventListener('click', () => {
            const nextStep = Number(button.dataset.itemNext);
            if (nextStep === 2 && !validatePanel(1)) return;
            if (nextStep === 3) {
                updateDeliveryFields();
                if (!checkedDeliveryMethod()) {
                    showError('Choose how you would like to deliver the item.');
                    return;
                }
                if (!validatePanel(2)) return;
                updateSummary();
            }
            setItemStep(nextStep);
        });
    });
    itemForm.querySelectorAll('[data-item-back]').forEach(button => {
        button.addEventListener('click', () => setItemStep(Number(button.dataset.itemBack), false));
    });
    deliveryOptions.forEach(option => option.addEventListener('change', updateDeliveryFields));
    anonymousInput.addEventListener('change', updateAnonymousField);
    itemForm.addEventListener('input', updateSummary);
    itemForm.addEventListener('change', updateSummary);
    photoInput.addEventListener('change', () => {
        const photo = photoInput.files[0];
        const maxSize = 5 * 1024 * 1024;
        const acceptedTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (photo && (photo.size > maxSize || (photo.type && !acceptedTypes.includes(photo.type)))) {
            photoInput.value = '';
            document.getElementById('pledgePhotoStatus').textContent = '';
            showError('Choose a JPG, PNG, or WebP item photo no larger than 5 MB.');
            return;
        }
        document.getElementById('pledgePhotoStatus').textContent = photo ? photo.name + ' selected' : '';
        showError('');
        updateSummary();
    });
    itemForm.addEventListener('submit', async event => {
        event.preventDefault();
        if (!validatePanel(3)) return;
        updateSummary();
        const submit = itemForm.querySelector('[type="submit"]');
        submit.disabled = true;
        submit.textContent = 'Submitting...';
        try {
            const response = await fetch(itemForm.action, {
                method: 'POST',
                body: new FormData(itemForm),
                credentials: 'same-origin'
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || 'Unable to submit item pledge.');
            document.getElementById('pledgeThankYouItem').textContent =
                quantityInput.value + ' × ' + itemNameInput.value.trim();
            setItemStep(4);
        } catch (submissionError) {
            showError(submissionError.message || 'Unable to submit item pledge. Please try again.');
        } finally {
            submit.disabled = false;
            submit.textContent = 'Submit pledge';
        }
    });

    updateDeliveryFields();
    updateAnonymousField();
    setMode('cash');
    updateSwitch();
}());

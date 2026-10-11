(function () {
    const trigger = document.getElementById('donationTrackerTrigger');
    const modal = document.getElementById('donationTrackerModal');
    const closeButton = document.getElementById('donationTrackerClose');
    const list = document.getElementById('donationTrackerList');
    const message = document.getElementById('donationTrackerMessage');
    const filters = Array.from(document.querySelectorAll('[data-donation-filter]'));
    const csrfInput = document.querySelector('#donationFunnel [name="csrfmiddlewaretoken"]');
    if (!trigger || !modal || !closeButton || !list || !message || !csrfInput) return;

    let donations = [];
    let activeFilter = 'pending';
    let lastTrigger;
    let renderTimer;
    let renderVersion = 0;

    function categoryFor(record) {
        if (record.kind === 'cash') {
            if (record.status === 'pending') return 'pending';
            if (record.status === 'completed') return 'completed';
            return 'attention';
        }
        if (record.status === 'pledged') return 'pending';
        if (record.status === 'approved' || record.status === 'scheduled') return 'progress';
        if (record.status === 'received') return 'completed';
        return 'attention';
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        })[character]);
    }

    function renderDonationsNow() {
        const filtered = activeFilter === 'all'
            ? donations
            : donations.filter(record => categoryFor(record) === activeFilter);
        list.replaceChildren();
        if (!filtered.length) {
            const empty = document.createElement('p');
            empty.className = 'donation-tracker-empty';
            empty.textContent = donations.length
                ? 'There are no donations in this category yet.'
                : 'Your donations and in-kind pledges will appear here after you submit them.';
            list.appendChild(empty);
            return;
        }
        filtered.forEach((record, index) => {
            const card = document.createElement('article');
            card.className = 'donation-tracker-card is-entering';
            card.style.animationDelay = Math.min(index * 45, 225) + 'ms';
            if (record.kind === 'item') {
                const thumbnail = document.createElement('img');
                thumbnail.className = 'donation-tracker-thumbnail';
                thumbnail.src = record.image || '/static/media/default-donation-receipt.svg';
                thumbnail.alt = record.imageAlt || 'No item photo provided';
                thumbnail.loading = 'lazy';
                card.appendChild(thumbnail);
            } else {
                const kind = document.createElement('span');
                kind.className = 'donation-tracker-kind';
                kind.textContent = 'Cash';
                card.appendChild(kind);
            }
            const content = document.createElement('div');
            content.className = 'donation-tracker-card-content';
            const title = document.createElement('strong');
            title.textContent = record.title;
            const detail = document.createElement('span');
            detail.textContent = record.detail;
            const date = document.createElement('time');
            date.textContent = record.date;
            content.append(title, detail, date);
            card.appendChild(content);
            const status = document.createElement('span');
            status.className = 'donation-tracker-status donation-tracker-status-' + escapeHtml(record.status);
            status.textContent = record.statusLabel;
            card.appendChild(status);
            list.appendChild(card);
        });
    }

    function renderDonations() {
        const version = ++renderVersion;
        window.clearTimeout(renderTimer);
        list.classList.add('is-changing');
        renderTimer = window.setTimeout(() => {
            if (version !== renderVersion) return;
            renderDonationsNow();
            list.classList.remove('is-changing');
        }, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 120);
    }

    async function loadDonations() {
        message.textContent = 'Loading your donations…';
        list.replaceChildren();
        try {
            const response = await fetch('/donations/tracker/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    'X-CSRFToken': csrfInput.value
                },
                body: new URLSearchParams({ csrfmiddlewaretoken: csrfInput.value })
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || 'Unable to load your donations.');
            donations = Array.isArray(payload.donations) ? payload.donations : [];
            message.textContent = '';
            renderDonations();
        } catch (error) {
            message.textContent = error.message || 'Unable to load your donations. Please try again.';
        }
    }

    function openModal() {
        lastTrigger = document.activeElement;
        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('donation-tracker-open');
        requestAnimationFrame(() => {
            modal.classList.add('is-open');
            closeButton.focus();
        });
        loadDonations();
    }

    function closeModal() {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('donation-tracker-open');
        window.setTimeout(() => {
            modal.hidden = true;
            if (lastTrigger) lastTrigger.focus();
        }, 180);
    }

    trigger.addEventListener('click', openModal);
    closeButton.addEventListener('click', closeModal);
    modal.addEventListener('click', event => {
        if (event.target === modal) closeModal();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !modal.hidden) closeModal();
    });
    filters.forEach(button => {
        button.addEventListener('click', () => {
            activeFilter = button.dataset.donationFilter;
            filters.forEach(filter => {
                const selected = filter === button;
                filter.classList.toggle('active', selected);
                filter.setAttribute('aria-pressed', selected ? 'true' : 'false');
            });
            renderDonations();
        });
    });
}());

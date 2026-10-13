(function () {
    "use strict";

    var selectSelector = "select[data-status-filter-custom]";
    var componentClass = "status-filter-select";

    function initializeStatusFilter(select) {
        if (select.dataset.customSelectInitialized === "true") return;

        var wrapper = select.parentElement;
        if (!wrapper.classList.contains(componentClass)) {
            wrapper = document.createElement("div");
            select.parentNode.insertBefore(wrapper, select);
            wrapper.appendChild(select);
        }
        wrapper.classList.add(componentClass, componentClass + "--" + select.id);
        var trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = componentClass + "__trigger";
        trigger.setAttribute("role", "combobox");
        trigger.setAttribute("aria-haspopup", "listbox");
        trigger.setAttribute("aria-expanded", "false");
        trigger.setAttribute("aria-label", select.getAttribute("aria-label") || "Filter by status");

        var label = document.createElement("span");
        label.className = componentClass + "__label";
        var arrow = document.createElement("span");
        arrow.className = componentClass + "__arrow";
        arrow.setAttribute("aria-hidden", "true");
        trigger.append(label, arrow);

        var menu = document.createElement("div");
        menu.className = componentClass + "__menu";
        menu.id = select.id + "-options";
        menu.setAttribute("role", "listbox");
        menu.hidden = true;
        trigger.setAttribute("aria-controls", menu.id);

        wrapper.appendChild(trigger);
        select.classList.add(componentClass + "__native");
        select.tabIndex = -1;
        select.setAttribute("aria-hidden", "true");
        select.dataset.customSelectInitialized = "true";
        document.body.appendChild(menu);

        var optionButtons = [];
        var activeIndex = -1;

        function updatePosition() {
            if (menu.hidden) return;
            var rect = trigger.getBoundingClientRect();
            var gap = 4;
            var availableBelow = window.innerHeight - rect.bottom - gap;
            var availableAbove = rect.top - gap;
            var placeAbove = availableBelow < 160 && availableAbove > availableBelow;
            var available = Math.max(120, placeAbove ? availableAbove : availableBelow);
            var height = Math.min(menu.scrollHeight, window.innerHeight * 0.45, available);

            menu.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8)) + "px";
            menu.style.width = Math.max(0, Math.min(rect.width, window.innerWidth - 16)) + "px";
            menu.style.maxHeight = Math.min(window.innerHeight * 0.45, available) + "px";
            menu.style.top = placeAbove
                ? Math.max(8, rect.top - height - gap) + "px"
                : Math.min(window.innerHeight - height - 8, rect.bottom + gap) + "px";
        }

        function setActive(index, focusOption) {
            if (!optionButtons.length) return;
            var nextIndex = (index + optionButtons.length) % optionButtons.length;
            var attempts = 0;
            while (select.options[nextIndex] && select.options[nextIndex].disabled && attempts < optionButtons.length) {
                nextIndex = (nextIndex + (index >= activeIndex ? 1 : -1) + optionButtons.length) % optionButtons.length;
                attempts += 1;
            }
            activeIndex = nextIndex;
            optionButtons.forEach(function (option, optionIndex) {
                option.classList.toggle("is-active", optionIndex === activeIndex);
            });
            if (focusOption) optionButtons[activeIndex].focus();
        }

        function close(restoreFocus) {
            menu.hidden = true;
            trigger.setAttribute("aria-expanded", "false");
            if (restoreFocus) trigger.focus();
        }

        function choose(optionIndex) {
            var option = select.options[optionIndex];
            if (!option || option.disabled) return;
            select.value = option.value;
            label.textContent = option.textContent;
            close(false);
            select.dispatchEvent(new Event("change", { bubbles: true }));
            trigger.focus();
        }

        function renderOptions() {
            menu.replaceChildren();
            optionButtons = [];
            activeIndex = -1;

            Array.prototype.forEach.call(select.options, function (option) {
                var item = document.createElement("div");
                item.className = componentClass + "__option";
                item.setAttribute("role", "option");
                item.setAttribute("aria-selected", option.value === select.value ? "true" : "false");
                item.setAttribute("aria-disabled", option.disabled ? "true" : "false");
                item.tabIndex = -1;
                item.textContent = option.textContent;
                item.dataset.value = option.value;
                item.addEventListener("click", function () {
                    choose(optionButtons.indexOf(item));
                });
                menu.appendChild(item);
                optionButtons.push(item);
            });

            updateLabel();
            if (!menu.hidden) updatePosition();
        }

        function updateLabel() {
            var selectedOption = select.options[select.selectedIndex];
            label.textContent = selectedOption ? selectedOption.textContent : "";
            trigger.setAttribute("aria-label", select.getAttribute("aria-label") || "Filter by status");
            optionButtons.forEach(function (item) {
                item.setAttribute("aria-selected", item.dataset.value === select.value ? "true" : "false");
            });
        }

        function open() {
            if (!select.options.length) return;
            menu.hidden = false;
            trigger.setAttribute("aria-expanded", "true");
            updatePosition();
            var selectedIndex = Array.prototype.findIndex.call(select.options, function (option) {
                return option.value === select.value && !option.disabled;
            });
            setActive(selectedIndex >= 0 ? selectedIndex : 0, false);
        }

        trigger.addEventListener("click", function () {
            if (menu.hidden) open();
            else close(false);
        });

        trigger.addEventListener("keydown", function (event) {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                if (menu.hidden) open();
                setActive(activeIndex + (event.key === "ArrowDown" ? 1 : -1), true);
            } else if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (menu.hidden) open();
                else if (optionButtons[activeIndex]) choose(activeIndex);
            } else if (event.key === "Escape" && !menu.hidden) {
                event.preventDefault();
                close(true);
            }
        });

        menu.addEventListener("keydown", function (event) {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                setActive(activeIndex + (event.key === "ArrowDown" ? 1 : -1), true);
            } else if (event.key === "Home" || event.key === "End") {
                event.preventDefault();
                setActive(event.key === "Home" ? 0 : optionButtons.length - 1, true);
            } else if (event.key === "Escape") {
                event.preventDefault();
                close(true);
            } else if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (select.options[activeIndex]) choose(activeIndex);
            }
        });

        select.addEventListener("change", updateLabel);
        new MutationObserver(renderOptions).observe(select, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["disabled", "label", "value"]
        });

        document.addEventListener("click", function (event) {
            if (!wrapper.contains(event.target) && !menu.contains(event.target)) close(false);
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Tab" && !menu.hidden) close(false);
        });
        window.addEventListener("resize", updatePosition);
        window.addEventListener("scroll", updatePosition, true);

        renderOptions();
    }

    function initializeAll() {
        document.querySelectorAll(selectSelector).forEach(initializeStatusFilter);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeAll);
    } else {
        initializeAll();
    }
})();

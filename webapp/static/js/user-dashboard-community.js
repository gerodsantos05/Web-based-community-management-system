(function initCommunityDashboard() {
    "use strict";

    var root = document.getElementById("community-hub");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var createForm = document.getElementById("community-create-post-form");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var statusNode = document.getElementById("community-create-status");
    var chatForm = document.getElementById("community-chatbox");
    var chatInput = document.getElementById("community-chat-input");
    var chatPlusButton = document.getElementById("community-chat-plus");
    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-community-tab]"));
    var announcementsHost = document.getElementById("community-announcements");
    var eventsHost = document.getElementById("community-events");
    var highlightsHost = document.getElementById("community-highlights");

    if (!feedHost || !feedCount) {
        return;
    }

    var nextPostId = 4;
    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "Posting simple before-and-after product photos helped me increase trust and sales this month.",
                type: "tips",
                likes: 18,
                comments: 2,
                commentsList: [
                    {
                        author: "Rica T.",
                        time: "1h ago",
                        text: "This is helpful. I will try the photo approach this week."
                    },
                    {
                        author: "Pao L.",
                        time: "44m ago",
                        text: "Same here. Price labels in photos really make a difference."
                    }
                ],
                liked: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "Pechay and kangkong worked best for us in small recycled containers.",
                type: "discussions",
                likes: 23,
                comments: 1,
                commentsList: [
                    {
                        author: "Mina R.",
                        time: "3h ago",
                        text: "Thanks for sharing. I only have small pots so this is perfect."
                    }
                ],
                liked: true
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open. Submit your request by Friday.",
                type: "announcements",
                likes: 12,
                comments: 2,
                commentsList: [
                    {
                        author: "Lito V.",
                        time: "20h ago",
                        text: "Is there still a slot for food products?"
                    },
                    {
                        author: "Community Admin",
                        time: "18h ago",
                        text: "Yes, there are still open slots. Please submit your form today."
                    }
                ],
                liked: false
            }
        ],
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
        var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return safe.replace(/[&<>"']/g, function (character) {
            return map[character] || character;
        });
    }

    function setStatus(message) {
        if (statusNode) {
            statusNode.textContent = String(message || "").trim();
        }
    }

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }
        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function normalizedComments(post) {
        if (!Array.isArray(post.commentsList)) {
            post.commentsList = [];
        }

        if (post.comments !== post.commentsList.length) {
            post.comments = post.commentsList.length;
        }

        return post.commentsList;
    }

    function renderComments(post) {
        var comments = normalizedComments(post);

        var commentsMarkup = comments.length ? comments.map(function (comment) {
            return [
                '<article class="ch-comment">',
                '<p class="ch-comment-meta">',
                '<span class="ch-comment-author">' + escapeHtml(comment.author) + '</span>',
                '<span class="ch-post-separator" aria-hidden="true">&bull;</span>',
                '<span class="ch-comment-time">' + escapeHtml(comment.time) + '</span>',
                '</p>',
                '<p class="ch-comment-text">' + escapeHtml(comment.text) + '</p>',
                '</article>'
            ].join("");
        }).join("") : '<p class="ch-comment-empty">No comments yet. Start the conversation.</p>';

        return [
            '<section class="ch-comments" aria-label="Comments">',
            '<div class="ch-comment-list">' + commentsMarkup + '</div>',
            '<form class="ch-comment-form" data-comment-form="' + escapeHtml(post.id) + '">',
            '<label class="sr-only" for="comment-input-' + escapeHtml(post.id) + '">Add a comment</label>',
            '<input id="comment-input-' + escapeHtml(post.id) + '" class="ch-comment-input focus-ring" data-comment-input="' + escapeHtml(post.id) + '" type="text" placeholder="Write a comment...">',
            '<button type="submit" class="ch-comment-submit focus-ring">Comment</button>',
            '</form>',
            '</section>'
        ].join("");
    }

    function renderFeed() {
        var posts = filteredPosts();

        feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");

        if (!posts.length) {
            feedHost.innerHTML = '<p class="cm-empty">No posts in this filter yet.</p>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            return [
                '<article class="ch-post" data-post-id="' + escapeHtml(post.id) + '">',
                '<header class="ch-post-head">',
                '<span class="ch-post-avatar" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>',
                '<p class="ch-post-author">' + escapeHtml(post.author) + '</p>',
                '<span class="ch-post-separator" aria-hidden="true">&bull;</span>',
                '<p class="ch-post-time">' + escapeHtml(post.timestamp) + '</p>',
                '</header>',
                '<h4 class="ch-post-title">' + escapeHtml(post.title) + '</h4>',
                '<p class="ch-post-content">' + escapeHtml(post.content) + '</p>',
                '<div class="ch-post-actions">',
                '<button type="button" class="ch-post-action' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post">',
                '<i data-lucide="heart" aria-hidden="true"></i>',
                '<span class="ch-post-action-count">' + post.likes + '</span>',
                '</button>',
                '<button type="button" class="ch-post-action" data-post-action="comment" aria-label="Comment on post">',
                '<i data-lucide="message-circle" aria-hidden="true"></i>',
                '<span class="ch-post-action-count">' + post.comments + '</span>',
                '</button>',
                '</div>',
                renderComments(post),
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function renderList(host, items) {
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

    function createPost(content, type) {
        var text = String(content || "").trim();
        if (!text) {
            setStatus("Please write a short message first.");
            return false;
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: "You",
            avatar: "YO",
            timestamp: "Just now",
            title: "New post",
            content: text,
            type: type === "livelihood" || type === "gardening" ? "tips" : "discussions",
            likes: 0,
            comments: 0,
            commentsList: [],
            liked: false
        });

        setActiveTab("all", false);
        return true;
    }

    if (createForm) {
        createForm.addEventListener("submit", function (event) {
            event.preventDefault();

            var content = postInput ? postInput.value.trim() : "";
            var type = postCategory ? postCategory.value.toLowerCase() : "discussions";

            if (!createPost(content, type)) {
                if (postInput) {
                    postInput.focus();
                }
                return;
            }

            if (postInput) {
                postInput.value = "";
            }
            if (postCategory) {
                postCategory.value = "Livelihood";
            }

            setStatus("Posted to the community feed.");
        });
    }

    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", function (event) {
            event.preventDefault();

            if (!createPost(chatInput.value, "discussions")) {
                chatInput.focus();
                return;
            }

            chatInput.value = "";
            setStatus("Posted to the community feed.");
            chatInput.focus();
        });
    }

    if (chatPlusButton) {
        chatPlusButton.addEventListener("click", function () {
            setStatus("Attachments will be available soon.");
            if (chatInput) {
                chatInput.focus();
            }
        });
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

    feedHost.addEventListener("click", function (event) {
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
            post.liked = !post.liked;
            post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
            renderFeed();
            return;
        }

        if (actionType === "comment") {
            var commentInput = feedHost.querySelector('[data-comment-input="' + post.id + '"]');
            if (commentInput) {
                commentInput.focus();
                commentInput.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
            setStatus("Add your comment below.");
        }
    });

    feedHost.addEventListener("submit", function (event) {
        var commentForm = event.target.closest("[data-comment-form]");
        if (!commentForm) {
            return;
        }

        event.preventDefault();

        var postId = commentForm.getAttribute("data-comment-form");
        var input = commentForm.querySelector("[data-comment-input]");
        var content = input ? String(input.value || "").trim() : "";

        if (!content) {
            if (input) {
                input.focus();
            }
            return;
        }

        var post = state.posts.find(function (item) {
            return item.id === postId;
        });
        if (!post) {
            return;
        }

        normalizedComments(post).push({
            author: "You",
            time: "Just now",
            text: content
        });
        post.comments = post.commentsList.length;

        renderFeed();
        setStatus("Comment added.");

        var refreshedInput = feedHost.querySelector('[data-comment-input="' + postId + '"]');
        if (refreshedInput) {
            refreshedInput.focus();
        }
    });

    if (announcementsHost) {
        renderList(announcementsHost, state.announcements);
    }
    if (eventsHost) {
        renderList(eventsHost, state.events);
    }
    if (highlightsHost) {
        renderList(highlightsHost, state.highlights);
    }
    setActiveTab("all", false);
    refreshIcons();
})();
(function initCommunityPremium() {
    "use strict";

    var root = document.getElementById("community-premium");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var tabs = Array.prototype.slice.call(root.querySelectorAll(".cm-tab"));
    var navLinks = Array.prototype.slice.call(root.querySelectorAll("[data-scroll-target]"));
    var feedList = document.getElementById("community-feed-list");
    var countNode = document.getElementById("community-feed-count");
    var searchInput = document.getElementById("community-search");
    var createShortcut = document.getElementById("community-create-shortcut");
    var chatForm = document.getElementById("community-chatbox");
    var chatInput = document.getElementById("community-chat-input");
    var centerColumn = root.querySelector(".cm-center");

    if (!feedList || !countNode || !chatForm || !chatInput || !centerColumn) {
        return;
    }

    var activeFilter = "all";
    var nextPostId = 5;

    function escapeHtml(value) {
        var safe = String(value || "");
        var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return safe.replace(/[&<>"']/g, function (char) {
            return map[char] || char;
        });
    }

    function allPosts() {
        return Array.prototype.slice.call(feedList.querySelectorAll(".cm-post"));
    }

    function updateCount(count) {
        countNode.textContent = count + (count === 1 ? " post" : " posts");
    }

    function postMatches(post, term) {
        var type = String(post.getAttribute("data-type") || "").toLowerCase();
        var haystack = String(post.getAttribute("data-search") || post.textContent || "").toLowerCase();

        var matchesFilter = activeFilter === "all" || type.indexOf(activeFilter) !== -1;
        var matchesSearch = !term || haystack.indexOf(term) !== -1;

        return matchesFilter && matchesSearch;
    }

    function renderFeed() {
        var term = searchInput ? String(searchInput.value || "").trim().toLowerCase() : "";
        var visible = 0;

        allPosts().forEach(function (post) {
            var show = postMatches(post, term);
            post.hidden = !show;
            if (show) {
                visible += 1;
            }
        });

        var empty = feedList.querySelector(".cm-empty");
        if (!visible) {
            if (!empty) {
                empty = document.createElement("p");
                empty.className = "cm-empty";
                empty.textContent = "No posts match this filter yet.";
                feedList.appendChild(empty);
            }
        } else if (empty) {
            empty.remove();
        }

        updateCount(visible);
    }

    function setActiveFilter(filterName, shouldFocus) {
        activeFilter = filterName;

        tabs.forEach(function (tab) {
            var selected = tab.getAttribute("data-filter") === filterName;
            tab.setAttribute("aria-selected", selected ? "true" : "false");
            tab.tabIndex = selected ? 0 : -1;
            if (selected && shouldFocus) {
                tab.focus();
            }
        });

        renderFeed();
    }

    function autosizeInput() {
        chatInput.style.height = "auto";
        var nextHeight = Math.min(chatInput.scrollHeight, 170);
        chatInput.style.height = Math.max(42, nextHeight) + "px";
        chatForm.classList.toggle("is-expanded", nextHeight > 48 || chatInput.value.trim().length > 48);
    }

    function syncChatboxPlacement() {
        var rect = centerColumn.getBoundingClientRect();
        if (!rect.width) {
            return;
        }

        var width = Math.min(rect.width, 760);
        var left = rect.left + (rect.width - width) / 2;
        var minLeft = 12;
        var maxLeft = Math.max(minLeft, window.innerWidth - width - 12);

        if (left < minLeft) {
            left = minLeft;
        }
        if (left > maxLeft) {
            left = maxLeft;
        }

        chatForm.style.width = width + "px";
        chatForm.style.left = left + "px";
        chatForm.style.transform = "none";
    }

    tabs.forEach(function (tab, index) {
        tab.addEventListener("click", function () {
            setActiveFilter(tab.getAttribute("data-filter"), false);
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
            setActiveFilter(tabs[nextIndex].getAttribute("data-filter"), true);
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", renderFeed);
    }

    if (createShortcut) {
        createShortcut.addEventListener("click", function () {
            chatInput.focus();
            chatInput.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
    }

    navLinks.forEach(function (link) {
        link.addEventListener("click", function (event) {
            event.preventDefault();

            navLinks.forEach(function (item) {
                item.classList.remove("is-active");
            });
            link.classList.add("is-active");

            var targetId = link.getAttribute("data-scroll-target");
            var target = targetId ? document.getElementById(targetId) : null;
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    chatInput.addEventListener("input", autosizeInput);
    chatInput.addEventListener("focus", autosizeInput);

    chatForm.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = String(chatInput.value || "").trim();
        if (!content) {
            chatInput.focus();
            return;
        }

        nextPostId += 1;

        var post = document.createElement("article");
        post.className = "cm-post";
        post.setAttribute("role", "listitem");
        post.setAttribute("data-type", "discussions");
        post.setAttribute("data-search", content.toLowerCase());
        post.id = "post-" + nextPostId;
        post.tabIndex = 0;

        post.innerHTML = [
            '<header class="cm-post-head">',
            '<span class="cm-avatar" aria-hidden="true">YO</span>',
            '<div><p class="cm-post-name">You</p><p class="cm-post-time">Just now</p></div>',
            '</header>',
            '<p class="cm-post-content">' + escapeHtml(content) + '</p>',
            '<footer class="cm-post-actions">',
            '<button type="button" class="cm-post-action" data-action="like" data-count="0">Like 0</button>',
            '<button type="button" class="cm-post-action" data-action="reply" data-count="0">Reply 0</button>',
            '<button type="button" class="cm-post-action" data-action="save">Save</button>',
            '</footer>'
        ].join("");

        feedList.insertBefore(post, feedList.firstChild);

        if (searchInput) {
            searchInput.value = "";
        }
        chatInput.value = "";
        autosizeInput();
        setActiveFilter("all", false);
    });

    feedList.addEventListener("click", function (event) {
        var actionButton = event.target.closest(".cm-post-action");
        if (!actionButton) {
            return;
        }

        var action = actionButton.getAttribute("data-action");
        if (action === "reply") {
            chatInput.focus();
            return;
        }

        if (action === "save") {
            actionButton.classList.toggle("is-active");
            actionButton.textContent = actionButton.classList.contains("is-active") ? "Saved" : "Save";
            return;
        }

        if (action === "like") {
            var current = Number(actionButton.getAttribute("data-count") || "0");
            var isActive = actionButton.classList.toggle("is-active");
            var next = Math.max(0, current + (isActive ? 1 : -1));
            actionButton.setAttribute("data-count", String(next));
            actionButton.textContent = "Like " + next;
        }
    });

    window.addEventListener("resize", syncChatboxPlacement);

    if (typeof window.ResizeObserver === "function") {
        var observer = new ResizeObserver(syncChatboxPlacement);
        observer.observe(centerColumn);

        var shell = document.getElementById("dashboard-shell");
        if (shell) {
            observer.observe(shell);
        }
    }

    autosizeInput();
    setActiveFilter("all", false);
    window.requestAnimationFrame(syncChatboxPlacement);
})();
(function () {
    "use strict";

    var root = document.getElementById("community-redesign");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var createForm = document.getElementById("community-create-post-form");
    var composerTrigger = document.getElementById("community-composer-trigger");
    var composerExpanded = document.getElementById("community-composer-expanded");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var statusNode = document.getElementById("community-create-status");

    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));
    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var eventsHost = document.getElementById("community-events");
    var updatesHost = document.getElementById("community-updates");

    if (!createForm || !composerTrigger || !composerExpanded || !feedHost || !eventsHost || !updatesHost) {
        return;
    }

    var nextPostId = 5;
    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "Posting simple before-and-after product photos helped me increase trust and sales this month. I also keep one clear price card in every image so buyers can decide faster.",
                type: "tips",
                tags: ["Livelihood"],
                likes: 18,
                comments: 4,
                liked: false,
                expanded: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "For small spaces, pechay and kangkong worked best for us. If anyone wants, I can share the watering routine we used for recycled containers.",
                type: "discussions",
                tags: ["Gardening"],
                likes: 23,
                comments: 7,
                liked: true,
                expanded: false
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open for beneficiary products. Please submit your booth request by Friday so the team can finalize layout and logistics early.",
                type: "announcements",
                tags: ["Schedule"],
                likes: 12,
                comments: 2,
                liked: false,
                expanded: false
            },
            {
                id: "post-4",
                author: "Rosa M.",
                avatar: "RM",
                timestamp: "2 days ago",
                title: "Share your latest rag-making creations",
                content: "Let us collect photos from this week so we can feature practical ideas in the next livelihood workshop and inspire new members.",
                type: "discussions",
                tags: ["Community"],
                likes: 9,
                comments: 5,
                liked: false,
                expanded: false
            }
        ],
        events: [
            { id: "ev-1", title: "Advanced Crafts Workshop", dateTime: "Apr 18, 2026 - 2:00 PM", location: "Covered Court Hall", joined: false },
            { id: "ev-2", title: "Monthly Community Meeting", dateTime: "Apr 25, 2026 - 10:00 AM", location: "Barangay Session Room", joined: true },
            { id: "ev-3", title: "Skills Fair and Marketplace", dateTime: "May 1, 2026 - 9:00 AM", location: "Community Center A", joined: false }
        ],
        updates: [
            "Workshop schedule updated",
            "Bring IDs reminder",
            "Community garden milestone reached",
            "Market booth request deadline is Friday"
        ]
    };

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(value) {
        var safe = String(value || "");
        var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return safe.replace(/[&<>"']/g, function (char) {
            return map[char] || char;
        });
    }

    function setStatus(message) {
        if (statusNode) {
            statusNode.textContent = String(message || "").trim();
        }
    }

    function labelForType(type) {
        if (type === "discussions") {
            return "Discussion";
        }
        if (type === "tips") {
            return "Tip";
        }
        return "Announcement";
    }

    function findPost(id) {
        return state.posts.find(function (post) {
            return post.id === id;
        }) || null;
    }

    function findEvent(id) {
        return state.events.find(function (eventItem) {
            return eventItem.id === id;
        }) || null;
    }

    function setComposerOpen(open) {
        composerExpanded.hidden = !open;
        if (open && postInput) {
            window.requestAnimationFrame(function () {
                postInput.focus();
            });
        }
    }

    function canCloseComposer() {
        return !(postInput && postInput.value && postInput.value.trim());
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }
        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function renderFeed() {
        var posts = filteredPosts();

        if (feedCount) {
            feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");
        }

        if (!posts.length) {
            feedHost.innerHTML = '<p class="cd-empty">No posts in this filter yet. Try another tab or create the first one.</p>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            var tag = (post.tags && post.tags.length) ? post.tags[0] : labelForType(post.type);
            var cls = "cd-post" + (post.expanded ? " is-expanded" : "");
            return [
                '<article class="' + cls + '" data-post-id="' + escapeHtml(post.id) + '" role="button" tabindex="0" aria-expanded="' + (post.expanded ? "true" : "false") + '">',
                '<header class="cd-post-top">',
                '<span class="cd-avatar cd-avatar--small" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>',
                '<div class="cd-post-meta">',
                '<p class="cd-post-author">' + escapeHtml(post.author) + '</p>',
                '<p class="cd-post-time">' + escapeHtml(post.timestamp) + '</p>',
                '</div>',
                '<span class="cd-post-tag">' + escapeHtml(tag) + '</span>',
                '</header>',
                '<h4 class="cd-post-title">' + escapeHtml(post.title) + '</h4>',
                '<p class="cd-post-content">' + escapeHtml(post.content) + '</p>',
                '<div class="cd-post-actions">',
                '<button type="button" class="cd-post-action focus-ring' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post"><i data-lucide="heart" aria-hidden="true"></i><span>' + post.likes + '</span></button>',
                '<button type="button" class="cd-post-action focus-ring" data-post-action="comment" aria-label="Comment on post"><i data-lucide="message-circle" aria-hidden="true"></i><span>' + post.comments + '</span></button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function renderEvents() {
        if (!state.events.length) {
            eventsHost.innerHTML = '<p class="cd-empty">No upcoming events yet.</p>';
            return;
        }

        eventsHost.innerHTML = state.events.map(function (eventItem) {
            var joined = !!eventItem.joined;
            var btnClass = "cd-event-btn focus-ring" + (joined ? " is-joined" : "");
            return [
                '<article class="cd-event">',
                '<p class="cd-event-title">' + escapeHtml(eventItem.title) + '</p>',
                '<p class="cd-event-meta">' + escapeHtml(eventItem.dateTime) + '</p>',
                '<p class="cd-event-location">' + escapeHtml(eventItem.location) + '</p>',
                '<div class="cd-event-footer">',
                '<button type="button" class="' + btnClass + '" data-event-id="' + escapeHtml(eventItem.id) + '">' + (joined ? "Joined" : "Join") + '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderUpdates() {
        if (!state.updates.length) {
            updatesHost.innerHTML = '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>No updates yet.</span></li>';
            return;
        }

        updatesHost.innerHTML = state.updates.map(function (item) {
            return '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>' + escapeHtml(item) + '</span></li>';
        }).join("");
    }

    function setActiveTab(tabName, focusTab) {
        var valid = tabs.some(function (tab) {
            return tab.getAttribute("data-community-tab") === tabName;
        });
        if (!valid) {
            return;
        }

        state.activeTab = tabName;

        tabs.forEach(function (tab) {
            var selected = tab.getAttribute("data-community-tab") === tabName;
            tab.setAttribute("aria-selected", selected ? "true" : "false");
            tab.tabIndex = selected ? 0 : -1;
            if (selected && focusTab) {
                tab.focus();
            }
        });

        renderFeed();
    }

    function deriveTitle(content, type) {
        var message = String(content || "").trim();
        if (!message) {
            return labelForType(type);
        }

        var words = message.split(/\s+/).slice(0, 7);
        var title = words.join(" ");
        if (message.length > title.length) {
            title += "...";
        }
        return title;
    }

    composerTrigger.addEventListener("click", function () {
        setComposerOpen(true);
    });

    if (postInput) {
        postInput.addEventListener("focus", function () {
            setComposerOpen(true);
        });
    }

    document.addEventListener("click", function (event) {
        if (!createForm.contains(event.target) && !composerExpanded.hidden && canCloseComposer()) {
            setComposerOpen(false);
        }
    });

    createForm.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = postInput ? postInput.value.trim() : "";
        var type = postCategory ? postCategory.value : "discussions";

        if (!content) {
            setStatus("Please write a short message first.");
            if (postInput) {
                postInput.focus();
            }
            return;
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: "You",
            avatar: "YO",
            timestamp: "Just now",
            title: deriveTitle(content, type),
            content: content,
            type: type,
            tags: [labelForType(type)],
            likes: 0,
            comments: 0,
            liked: false,
            expanded: true
        });

        if (postInput) {
            postInput.value = "";
        }
        if (postCategory) {
            postCategory.value = "discussions";
        }

        setStatus("Posted to the community feed.");
        setComposerOpen(false);
        setActiveTab("all", false);
    });

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

    feedHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-post-action]");
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        if (actionButton) {
            var action = actionButton.getAttribute("data-post-action");
            if (action === "like") {
                post.liked = !post.liked;
                post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
                renderFeed();
                return;
            }
            if (action === "comment") {
                post.expanded = true;
                renderFeed();
                return;
            }
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    feedHost.addEventListener("keydown", function (event) {
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        event.preventDefault();
        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    eventsHost.addEventListener("click", function (event) {
        var joinButton = event.target.closest("[data-event-id]");
        if (!joinButton) {
            return;
        }

        var eventItem = findEvent(joinButton.getAttribute("data-event-id"));
        if (!eventItem) {
            return;
        }

        eventItem.joined = !eventItem.joined;
        renderEvents();
        setStatus(eventItem.joined ? "Joined event: " + eventItem.title : "Left event: " + eventItem.title);
    });

    renderUpdates();
    renderEvents();
    setActiveTab("all", false);
    refreshIcons();
})();
(function () {
    "use strict";

    var root = document.getElementById("community-redesign");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var createForm = document.getElementById("community-create-post-form");
    var composerTrigger = document.getElementById("community-composer-trigger");
    var composerExpanded = document.getElementById("community-composer-expanded");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var statusNode = document.getElementById("community-create-status");

    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));
    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var eventsHost = document.getElementById("community-events");
    var updatesHost = document.getElementById("community-updates");

    if (!createForm || !composerTrigger || !composerExpanded || !feedHost || !eventsHost || !updatesHost) {
        return;
    }

    var nextPostId = 5;
    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "Posting simple before-and-after product photos helped me increase trust and sales this month. I also keep one clear price card in every image so buyers can decide faster.",
                type: "tips",
                tags: ["Livelihood"],
                likes: 18,
                comments: 4,
                liked: false,
                expanded: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "For small spaces, pechay and kangkong worked best for us. If anyone wants, I can share the watering routine we used for recycled containers.",
                type: "discussions",
                tags: ["Gardening"],
                likes: 23,
                comments: 7,
                liked: true,
                expanded: false
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open for beneficiary products. Please submit your booth request by Friday so the team can finalize layout and logistics early.",
                type: "announcements",
                tags: ["Schedule"],
                likes: 12,
                comments: 2,
                liked: false,
                expanded: false
            },
            {
                id: "post-4",
                author: "Rosa M.",
                avatar: "RM",
                timestamp: "2 days ago",
                title: "Share your latest rag-making creations",
                content: "Let us collect photos from this week so we can feature practical ideas in the next livelihood workshop and inspire new members.",
                type: "discussions",
                tags: ["Community"],
                likes: 9,
                comments: 5,
                liked: false,
                expanded: false
            }
        ],
        events: [
            { id: "ev-1", title: "Advanced Crafts Workshop", dateTime: "Apr 18, 2026 - 2:00 PM", location: "Covered Court Hall", joined: false },
            { id: "ev-2", title: "Monthly Community Meeting", dateTime: "Apr 25, 2026 - 10:00 AM", location: "Barangay Session Room", joined: true },
            { id: "ev-3", title: "Skills Fair and Marketplace", dateTime: "May 1, 2026 - 9:00 AM", location: "Community Center A", joined: false }
        ],
        updates: [
            "Workshop schedule updated",
            "Bring IDs reminder",
            "Community garden milestone reached",
            "Market booth request deadline is Friday"
        ]
    };

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(value) {
        var safe = String(value || "");
        var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return safe.replace(/[&<>"']/g, function (char) {
            return map[char] || char;
        });
    }

    function setStatus(message) {
        if (statusNode) {
            statusNode.textContent = String(message || "").trim();
        }
    }

    function labelForType(type) {
        if (type === "discussions") {
            return "Discussion";
        }
        if (type === "tips") {
            return "Tip";
        }
        return "Announcement";
    }

    function findPost(id) {
        return state.posts.find(function (post) {
            return post.id === id;
        }) || null;
    }

    function findEvent(id) {
        return state.events.find(function (eventItem) {
            return eventItem.id === id;
        }) || null;
    }

    function setComposerOpen(open) {
        composerExpanded.hidden = !open;
        if (open && postInput) {
            window.requestAnimationFrame(function () {
                postInput.focus();
            });
        }
    }

    function canCloseComposer() {
        return !(postInput && postInput.value && postInput.value.trim());
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }
        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function renderFeed() {
        var posts = filteredPosts();

        if (feedCount) {
            feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");
        }

        if (!posts.length) {
            feedHost.innerHTML = '<p class="cd-empty">No posts in this filter yet. Try another tab or create the first one.</p>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            var tag = (post.tags && post.tags.length) ? post.tags[0] : labelForType(post.type);
            var cls = "cd-post" + (post.expanded ? " is-expanded" : "");
            return [
                '<article class="' + cls + '" data-post-id="' + escapeHtml(post.id) + '" role="button" tabindex="0" aria-expanded="' + (post.expanded ? "true" : "false") + '">',
                '<header class="cd-post-top">',
                '<span class="cd-avatar cd-avatar--small" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>',
                '<div class="cd-post-meta">',
                '<p class="cd-post-author">' + escapeHtml(post.author) + '</p>',
                '<p class="cd-post-time">' + escapeHtml(post.timestamp) + '</p>',
                '</div>',
                '<span class="cd-post-tag">' + escapeHtml(tag) + '</span>',
                '</header>',
                '<h4 class="cd-post-title">' + escapeHtml(post.title) + '</h4>',
                '<p class="cd-post-content">' + escapeHtml(post.content) + '</p>',
                '<div class="cd-post-actions">',
                '<button type="button" class="cd-post-action focus-ring' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post"><i data-lucide="heart" aria-hidden="true"></i><span>' + post.likes + '</span></button>',
                '<button type="button" class="cd-post-action focus-ring" data-post-action="comment" aria-label="Comment on post"><i data-lucide="message-circle" aria-hidden="true"></i><span>' + post.comments + '</span></button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function renderEvents() {
        if (!state.events.length) {
            eventsHost.innerHTML = '<p class="cd-empty">No upcoming events yet.</p>';
            return;
        }

        eventsHost.innerHTML = state.events.map(function (eventItem) {
            var joined = !!eventItem.joined;
            var btnClass = "cd-event-btn focus-ring" + (joined ? " is-joined" : "");
            return [
                '<article class="cd-event">',
                '<p class="cd-event-title">' + escapeHtml(eventItem.title) + '</p>',
                '<p class="cd-event-meta">' + escapeHtml(eventItem.dateTime) + '</p>',
                '<p class="cd-event-location">' + escapeHtml(eventItem.location) + '</p>',
                '<div class="cd-event-footer">',
                '<button type="button" class="' + btnClass + '" data-event-id="' + escapeHtml(eventItem.id) + '">' + (joined ? "Joined" : "Join") + '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderUpdates() {
        if (!state.updates.length) {
            updatesHost.innerHTML = '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>No updates yet.</span></li>';
            return;
        }

        updatesHost.innerHTML = state.updates.map(function (item) {
            return '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>' + escapeHtml(item) + '</span></li>';
        }).join("");
    }

    function setActiveTab(tabName, focusTab) {
        var valid = tabs.some(function (tab) {
            return tab.getAttribute("data-community-tab") === tabName;
        });
        if (!valid) {
            return;
        }

        state.activeTab = tabName;

        tabs.forEach(function (tab) {
            var selected = tab.getAttribute("data-community-tab") === tabName;
            tab.setAttribute("aria-selected", selected ? "true" : "false");
            tab.tabIndex = selected ? 0 : -1;
            if (selected && focusTab) {
                tab.focus();
            }
        });

        renderFeed();
    }

    function deriveTitle(content, type) {
        var message = String(content || "").trim();
        if (!message) {
            return labelForType(type);
        }

        var words = message.split(/\s+/).slice(0, 7);
        var title = words.join(" ");
        if (message.length > title.length) {
            title += "...";
        }
        return title;
    }

    composerTrigger.addEventListener("click", function () {
        setComposerOpen(true);
    });

    if (postInput) {
        postInput.addEventListener("focus", function () {
            setComposerOpen(true);
        });
    }

    document.addEventListener("click", function (event) {
        if (!createForm.contains(event.target) && !composerExpanded.hidden && canCloseComposer()) {
            setComposerOpen(false);
        }
    });

    createForm.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = postInput ? postInput.value.trim() : "";
        var type = postCategory ? postCategory.value : "discussions";

        if (!content) {
            setStatus("Please write a short message first.");
            if (postInput) {
                postInput.focus();
            }
            return;
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: "You",
            avatar: "YO",
            timestamp: "Just now",
            title: deriveTitle(content, type),
            content: content,
            type: type,
            tags: [labelForType(type)],
            likes: 0,
            comments: 0,
            liked: false,
            expanded: true
        });

        if (postInput) {
            postInput.value = "";
        }
        if (postCategory) {
            postCategory.value = "discussions";
        }

        setStatus("Posted to the community feed.");
        setComposerOpen(false);
        setActiveTab("all", false);
    });

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

    feedHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-post-action]");
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        if (actionButton) {
            var action = actionButton.getAttribute("data-post-action");
            if (action === "like") {
                post.liked = !post.liked;
                post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
                renderFeed();
                return;
            }
            if (action === "comment") {
                post.expanded = true;
                renderFeed();
                return;
            }
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    feedHost.addEventListener("keydown", function (event) {
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        event.preventDefault();
        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    eventsHost.addEventListener("click", function (event) {
        var joinButton = event.target.closest("[data-event-id]");
        if (!joinButton) {
            return;
        }

        var eventItem = findEvent(joinButton.getAttribute("data-event-id"));
        if (!eventItem) {
            return;
        }

        eventItem.joined = !eventItem.joined;
        renderEvents();
        setStatus(eventItem.joined ? "Joined event: " + eventItem.title : "Left event: " + eventItem.title);
    });

    renderUpdates();
    renderEvents();
    setActiveTab("all", false);
    refreshIcons();
})();(function () {
    "use strict";

    var root = document.getElementById("community-redesign");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var createForm = document.getElementById("community-create-post-form");
    var composerTrigger = document.getElementById("community-composer-trigger");
    var composerExpanded = document.getElementById("community-composer-expanded");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var statusNode = document.getElementById("community-create-status");

    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));
    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var eventsHost = document.getElementById("community-events");
    var updatesHost = document.getElementById("community-updates");

    if (!createForm || !composerTrigger || !composerExpanded || !feedHost || !eventsHost || !updatesHost) {
        return;
    }

    var nextPostId = 5;

    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "Posting simple before-and-after product photos helped me increase trust and sales this month. I also keep one clear price card in every image so buyers can decide faster.",
                type: "tips",
                tags: ["Livelihood"],
                likes: 18,
                comments: 4,
                liked: false,
                expanded: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "For small spaces, pechay and kangkong worked best for us. If anyone wants, I can share the watering routine we used for recycled containers.",
                type: "discussions",
                tags: ["Gardening"],
                likes: 23,
                comments: 7,
                liked: true,
                expanded: false
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open for beneficiary products. Please submit your booth request by Friday so the team can finalize layout and logistics early.",
                type: "announcements",
                tags: ["Schedule"],
                likes: 12,
                comments: 2,
                liked: false,
                expanded: false
            },
            {
                id: "post-4",
                author: "Rosa M.",
                avatar: "RM",
                timestamp: "2 days ago",
                title: "Share your latest rag-making creations",
                content: "Let us collect photos from this week so we can feature practical ideas in the next livelihood workshop and inspire new members.",
                type: "discussions",
                tags: ["Community"],
                likes: 9,
                comments: 5,
                liked: false,
                expanded: false
            }
        ],
        events: [
            { id: "ev-1", title: "Advanced Crafts Workshop", dateTime: "Apr 18, 2026 - 2:00 PM", location: "Covered Court Hall", joined: false },
            { id: "ev-2", title: "Monthly Community Meeting", dateTime: "Apr 25, 2026 - 10:00 AM", location: "Barangay Session Room", joined: true },
            { id: "ev-3", title: "Skills Fair and Marketplace", dateTime: "May 1, 2026 - 9:00 AM", location: "Community Center A", joined: false }
        ],
        updates: [
            "Workshop schedule updated",
            "Bring IDs reminder",
            "Community garden milestone reached",
            "Market booth request deadline is Friday"
        ]
    };

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(value) {
        var safe = String(value || "");
        var map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return safe.replace(/[&<>"']/g, function (char) { return map[char] || char; });
    }

    function setStatus(message) {
        if (statusNode) {
            statusNode.textContent = String(message || "").trim();
        }
    }

    function labelForType(type) {
        if (type === "discussions") { return "Discussion"; }
        if (type === "tips") { return "Tip"; }
        return "Announcement";
    }

    function findPost(id) {
        return state.posts.find(function (post) { return post.id === id; }) || null;
    }

    function findEvent(id) {
        return state.events.find(function (eventItem) { return eventItem.id === id; }) || null;
    }

    function setComposerOpen(open) {
        composerExpanded.hidden = !open;
        if (open && postInput) {
            window.requestAnimationFrame(function () { postInput.focus(); });
        }
    }

    function canCloseComposer() {
        return !(postInput && postInput.value && postInput.value.trim());
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }
        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function renderFeed() {
        var posts = filteredPosts();

        if (feedCount) {
            feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");
        }

        if (!posts.length) {
            feedHost.innerHTML = '<p class="cd-empty">No posts in this filter yet. Try another tab or create the first one.</p>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            var tag = (post.tags && post.tags.length) ? post.tags[0] : labelForType(post.type);
            var cls = "cd-post" + (post.expanded ? " is-expanded" : "");
            return [
                '<article class="' + cls + '" data-post-id="' + escapeHtml(post.id) + '" role="button" tabindex="0" aria-expanded="' + (post.expanded ? "true" : "false") + '">',
                '<header class="cd-post-top">',
                '<span class="cd-avatar cd-avatar--small" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>',
                '<div class="cd-post-meta">',
                '<p class="cd-post-author">' + escapeHtml(post.author) + '</p>',
                '<p class="cd-post-time">' + escapeHtml(post.timestamp) + '</p>',
                '</div>',
                '<span class="cd-post-tag">' + escapeHtml(tag) + '</span>',
                '</header>',
                '<h4 class="cd-post-title">' + escapeHtml(post.title) + '</h4>',
                '<p class="cd-post-content">' + escapeHtml(post.content) + '</p>',
                '<div class="cd-post-actions">',
                '<button type="button" class="cd-post-action focus-ring' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post"><i data-lucide="heart" aria-hidden="true"></i><span>' + post.likes + '</span></button>',
                '<button type="button" class="cd-post-action focus-ring" data-post-action="comment" aria-label="Comment on post"><i data-lucide="message-circle" aria-hidden="true"></i><span>' + post.comments + '</span></button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function renderEvents() {
        if (!state.events.length) {
            eventsHost.innerHTML = '<p class="cd-empty">No upcoming events yet.</p>';
            return;
        }

        eventsHost.innerHTML = state.events.map(function (eventItem) {
            var joined = !!eventItem.joined;
            var btnClass = "cd-event-btn focus-ring" + (joined ? " is-joined" : "");
            return [
                '<article class="cd-event">',
                '<p class="cd-event-title">' + escapeHtml(eventItem.title) + '</p>',
                '<p class="cd-event-meta">' + escapeHtml(eventItem.dateTime) + '</p>',
                '<p class="cd-event-location">' + escapeHtml(eventItem.location) + '</p>',
                '<div class="cd-event-footer">',
                '<button type="button" class="' + btnClass + '" data-event-id="' + escapeHtml(eventItem.id) + '">' + (joined ? "Joined" : "Join") + '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderUpdates() {
        if (!state.updates.length) {
            updatesHost.innerHTML = '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>No updates yet.</span></li>';
            return;
        }

        updatesHost.innerHTML = state.updates.map(function (item) {
            return '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>' + escapeHtml(item) + '</span></li>';
        }).join("");
    }

    function setActiveTab(tabName, focusTab) {
        var valid = tabs.some(function (tab) {
            return tab.getAttribute("data-community-tab") === tabName;
        });
        if (!valid) {
            return;
        }

        state.activeTab = tabName;

        tabs.forEach(function (tab) {
            var selected = tab.getAttribute("data-community-tab") === tabName;
            tab.setAttribute("aria-selected", selected ? "true" : "false");
            tab.tabIndex = selected ? 0 : -1;
            if (selected && focusTab) {
                tab.focus();
            }
        });

        renderFeed();
    }

    function deriveTitle(content, type) {
        var message = String(content || "").trim();
        if (!message) {
            return labelForType(type);
        }

        var words = message.split(/\s+/).slice(0, 7);
        var title = words.join(" ");
        if (message.length > title.length) {
            title += "...";
        }
        return title;
    }

    composerTrigger.addEventListener("click", function () {
        setComposerOpen(true);
    });

    if (postInput) {
        postInput.addEventListener("focus", function () {
            setComposerOpen(true);
        });
    }

    document.addEventListener("click", function (event) {
        if (!createForm.contains(event.target) && !composerExpanded.hidden && canCloseComposer()) {
            setComposerOpen(false);
        }
    });

    createForm.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = postInput ? postInput.value.trim() : "";
        var type = postCategory ? postCategory.value : "discussions";

        if (!content) {
            setStatus("Please write a short message first.");
            if (postInput) {
                postInput.focus();
            }
            return;
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: "You",
            avatar: "YO",
            timestamp: "Just now",
            title: deriveTitle(content, type),
            content: content,
            type: type,
            tags: [labelForType(type)],
            likes: 0,
            comments: 0,
            liked: false,
            expanded: true
        });

        if (postInput) {
            postInput.value = "";
        }
        if (postCategory) {
            postCategory.value = "discussions";
        }

        setStatus("Posted to the community feed.");
        setComposerOpen(false);
        setActiveTab("all", false);
    });

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

    feedHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-post-action]");
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        if (actionButton) {
            var action = actionButton.getAttribute("data-post-action");
            if (action === "like") {
                post.liked = !post.liked;
                post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
                renderFeed();
                return;
            }
            if (action === "comment") {
                post.expanded = true;
                renderFeed();
                return;
            }
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    feedHost.addEventListener("keydown", function (event) {
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        event.preventDefault();
        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    eventsHost.addEventListener("click", function (event) {
        var joinButton = event.target.closest("[data-event-id]");
        if (!joinButton) {
            return;
        }

        var eventItem = findEvent(joinButton.getAttribute("data-event-id"));
        if (!eventItem) {
            return;
        }

        eventItem.joined = !eventItem.joined;
        renderEvents();
        setStatus(eventItem.joined ? "Joined event: " + eventItem.title : "Left event: " + eventItem.title);
    });

    renderUpdates();
    renderEvents();
    setActiveTab("all", false);
    refreshIcons();
})();
(function initCommunityDashboard() {
    "use strict";

    var root = document.getElementById("community-redesign");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var createForm = document.getElementById("community-create-post-form");
    var composerTrigger = document.getElementById("community-composer-trigger");
    var composerExpanded = document.getElementById("community-composer-expanded");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var statusNode = document.getElementById("community-create-status");

    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));
    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var eventsHost = document.getElementById("community-events");
    var updatesHost = document.getElementById("community-updates");

    if (!createForm || !composerExpanded || !feedHost || !eventsHost || !updatesHost || !composerTrigger) {
        return;
    }

    var nextPostId = 5;

    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "Posting simple before-and-after product photos helped me increase trust and sales this month. I also keep one clear price card in every image so buyers can decide faster.",
                type: "tips",
                tags: ["Livelihood"],
                likes: 18,
                comments: 4,
                liked: false,
                expanded: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "For small spaces, pechay and kangkong worked best for us. If anyone wants, I can share the watering routine we used for recycled containers.",
                type: "discussions",
                tags: ["Gardening"],
                likes: 23,
                comments: 7,
                liked: true,
                expanded: false
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open for beneficiary products. Please submit your booth request by Friday so the team can finalize layout and logistics early.",
                type: "announcements",
                tags: ["Schedule"],
                likes: 12,
                comments: 2,
                liked: false,
                expanded: false
            },
            {
                id: "post-4",
                author: "Rosa M.",
                avatar: "RM",
                timestamp: "2 days ago",
                title: "Share your latest rag-making creations",
                content: "Let us collect photos from this week so we can feature practical ideas in the next livelihood workshop and inspire new members.",
                type: "discussions",
                tags: ["Community"],
                likes: 9,
                comments: 5,
                liked: false,
                expanded: false
            }
        ],
        events: [
            {
                id: "ev-1",
                title: "Advanced Crafts Workshop",
                dateTime: "Apr 18, 2026 - 2:00 PM",
                location: "Covered Court Hall",
                joined: false
            },
            {
                id: "ev-2",
                title: "Monthly Community Meeting",
                dateTime: "Apr 25, 2026 - 10:00 AM",
                location: "Barangay Session Room",
                joined: true
            },
            {
                id: "ev-3",
                title: "Skills Fair and Marketplace",
                dateTime: "May 1, 2026 - 9:00 AM",
                location: "Community Center A",
                joined: false
            }
        ],
        updates: [
            "Workshop schedule updated",
            "Bring IDs reminder",
            "Community garden milestone reached",
            "Market booth request deadline is Friday"
        ]
    };

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(value) {
        var safe = String(value || "");
        var lookup = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return safe.replace(/[&<>"']/g, function (character) {
            return lookup[character] || character;
        });
    }

    function setStatus(message) {
        if (!statusNode) {
            return;
        }
        statusNode.textContent = String(message || "").trim();
    }

    function typeLabel(type) {
        if (type === "discussions") {
            return "Discussion";
        }
        if (type === "tips") {
            return "Tip";
        }
        return "Announcement";
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }
        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function findPost(postId) {
        return state.posts.find(function (post) {
            return post.id === postId;
        }) || null;
    }

    function findEvent(eventId) {
        return state.events.find(function (eventItem) {
            return eventItem.id === eventId;
        }) || null;
    }

    function setComposerOpen(isOpen) {
        composerExpanded.hidden = !isOpen;
        if (isOpen && postInput) {
            window.requestAnimationFrame(function () {
                postInput.focus();
            });
        }
    }

    function canCloseComposer() {
        var hasText = postInput && postInput.value && postInput.value.trim().length > 0;
        return !hasText;
    }

    function renderFeed() {
        var posts = filteredPosts();

        if (feedCount) {
            feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");
        }

        if (!posts.length) {
            feedHost.innerHTML = '<p class="cd-empty">No posts in this filter yet. Try another tab or create the first one.</p>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            var firstTag = (post.tags && post.tags.length) ? post.tags[0] : typeLabel(post.type);
            var cardClass = "cd-post" + (post.expanded ? " is-expanded" : "");
            return [
                '<article class="' + cardClass + '" data-post-id="' + escapeHtml(post.id) + '" role="button" tabindex="0" aria-expanded="' + (post.expanded ? "true" : "false") + '">',
                '<header class="cd-post-top">',
                '<span class="cd-avatar cd-avatar--small" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>',
                '<div class="cd-post-meta">',
                '<p class="cd-post-author">' + escapeHtml(post.author) + '</p>',
                '<p class="cd-post-time">' + escapeHtml(post.timestamp) + '</p>',
                '</div>',
                '<span class="cd-post-tag">' + escapeHtml(firstTag) + '</span>',
                '</header>',
                '<h4 class="cd-post-title">' + escapeHtml(post.title) + '</h4>',
                '<p class="cd-post-content">' + escapeHtml(post.content) + '</p>',
                '<div class="cd-post-actions">',
                '<button type="button" class="cd-post-action focus-ring' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post">',
                '<i data-lucide="heart" aria-hidden="true"></i>',
                '<span>' + post.likes + '</span>',
                '</button>',
                '<button type="button" class="cd-post-action focus-ring" data-post-action="comment" aria-label="Comment on post">',
                '<i data-lucide="message-circle" aria-hidden="true"></i>',
                '<span>' + post.comments + '</span>',
                '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function renderEvents() {
        if (!state.events.length) {
            eventsHost.innerHTML = '<p class="cd-empty">No upcoming events yet.</p>';
            return;
        }

        eventsHost.innerHTML = state.events.map(function (eventItem) {
            var joined = !!eventItem.joined;
            var buttonClass = "cd-event-btn focus-ring" + (joined ? " is-joined" : "");
            return [
                '<article class="cd-event">',
                '<p class="cd-event-title">' + escapeHtml(eventItem.title) + '</p>',
                '<p class="cd-event-meta">' + escapeHtml(eventItem.dateTime) + '</p>',
                '<p class="cd-event-location">' + escapeHtml(eventItem.location) + '</p>',
                '<div class="cd-event-footer">',
                '<button type="button" class="' + buttonClass + '" data-event-id="' + escapeHtml(eventItem.id) + '">' + (joined ? "Joined" : "Join") + '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderUpdates() {
        if (!state.updates.length) {
            updatesHost.innerHTML = '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>No updates yet.</span></li>';
            return;
        }

        updatesHost.innerHTML = state.updates.map(function (line) {
            return '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>' + escapeHtml(line) + '</span></li>';
        }).join("");
    }

    function setActiveTab(tabName, moveFocus) {
        var valid = tabs.some(function (tabButton) {
            return tabButton.getAttribute("data-community-tab") === tabName;
        });
        if (!valid) {
            return;
        }

        state.activeTab = tabName;

        tabs.forEach(function (tabButton) {
            var selected = tabButton.getAttribute("data-community-tab") === tabName;
            tabButton.setAttribute("aria-selected", selected ? "true" : "false");
            tabButton.tabIndex = selected ? 0 : -1;
            if (selected && moveFocus) {
                tabButton.focus();
            }
        });

        renderFeed();
    }

    function derivePostTitle(message, category) {
        var source = String(message || "").trim();
        if (!source) {
            return typeLabel(category);
        }

        var words = source.split(/\s+/).slice(0, 7);
        var draft = words.join(" ");
        if (source.length > draft.length) {
            draft += "...";
        }
        return draft;
    }

    composerTrigger.addEventListener("click", function () {
        setComposerOpen(true);
    });

    if (postInput) {
        postInput.addEventListener("focus", function () {
            setComposerOpen(true);
        });
    }

    document.addEventListener("click", function (event) {
        if (!createForm.contains(event.target) && !composerExpanded.hidden && canCloseComposer()) {
            setComposerOpen(false);
        }
    });

    createForm.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = postInput ? postInput.value.trim() : "";
        var category = postCategory ? postCategory.value : "discussions";
        if (!content) {
            setStatus("Please write a short message first.");
            if (postInput) {
                postInput.focus();
            }
            return;
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: "You",
            avatar: "YO",
            timestamp: "Just now",
            title: derivePostTitle(content, category),
            content: content,
            type: category,
            tags: [typeLabel(category)],
            likes: 0,
            comments: 0,
            liked: false,
            expanded: true
        });

        if (postInput) {
            postInput.value = "";
        }
        if (postCategory) {
            postCategory.value = "discussions";
        }

        setStatus("Posted to the community feed.");
        setComposerOpen(false);
        setActiveTab("all", false);
    });

    tabs.forEach(function (tabButton, index) {
        tabButton.addEventListener("click", function () {
            setActiveTab(tabButton.getAttribute("data-community-tab"), false);
        });

        tabButton.addEventListener("keydown", function (event) {
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

    feedHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-post-action]");
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        if (actionButton) {
            var action = actionButton.getAttribute("data-post-action");
            if (action === "like") {
                post.liked = !post.liked;
                post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
                renderFeed();
                return;
            }

            if (action === "comment") {
                post.expanded = true;
                renderFeed();
                return;
            }
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    feedHost.addEventListener("keydown", function (event) {
        var card = event.target.closest("[data-post-id]");
        if (!card) {
            return;
        }

        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        event.preventDefault();
        var post = findPost(card.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        post.expanded = !post.expanded;
        renderFeed();
    });

    eventsHost.addEventListener("click", function (event) {
        var joinButton = event.target.closest("[data-event-id]");
        if (!joinButton) {
            return;
        }

        var eventItem = findEvent(joinButton.getAttribute("data-event-id"));
        if (!eventItem) {
            return;
        }

        eventItem.joined = !eventItem.joined;
        renderEvents();
        setStatus(eventItem.joined ? "Joined event: " + eventItem.title : "Left event: " + eventItem.title);
    });

    renderUpdates();
    renderEvents();
    setActiveTab("all", false);
    refreshIcons();
})();
(function initCommunityDashboard() {
    "use strict";

    var root = document.getElementById("community-redesign");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var createForm = document.getElementById("community-create-post-form");
    var composerTrigger = document.getElementById("community-composer-trigger");
    var composerExpanded = document.getElementById("community-composer-expanded");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var statusNode = document.getElementById("community-create-status");

    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));
    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var eventsHost = document.getElementById("community-events");
    var updatesHost = document.getElementById("community-updates");

    if (!createForm || !composerExpanded || !feedHost || !eventsHost || !updatesHost) {
        return;
    }

    var nextPostId = 5;

    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "Posting simple before-and-after product photos helped me increase trust and sales this month. I also keep one clear price card in every image so buyers can decide faster.",
                type: "tips",
                tags: ["Livelihood"],
                likes: 18,
                comments: 4,
                liked: false,
                expanded: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "For small spaces, pechay and kangkong worked best for us. If anyone wants, I can share the watering routine we used for recycled containers.",
                type: "discussions",
                tags: ["Gardening"],
                likes: 23,
                comments: 7,
                liked: true,
                expanded: false
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open for beneficiary products. Please submit your booth request by Friday so the team can finalize layout and logistics early.",
                type: "announcements",
                tags: ["Schedule"],
                likes: 12,
                comments: 2,
                liked: false,
                expanded: false
            },
            {
                id: "post-4",
                author: "Rosa M.",
                avatar: "RM",
                timestamp: "2 days ago",
                title: "Share your latest rag-making creations",
                content: "Let us collect photos from this week so we can feature practical ideas in the next livelihood workshop and inspire new members.",
                type: "discussions",
                tags: ["Community"],
                likes: 9,
                comments: 5,
                liked: false,
                expanded: false
            }
        ],
        events: [
            {
                id: "ev-1",
                title: "Advanced Crafts Workshop",
                dateTime: "Apr 18, 2026 - 2:00 PM",
                location: "Covered Court Hall",
                joined: false
            },
            {
                id: "ev-2",
                title: "Monthly Community Meeting",
                dateTime: "Apr 25, 2026 - 10:00 AM",
                location: "Barangay Session Room",
                joined: true
            },
            {
                id: "ev-3",
                title: "Skills Fair and Marketplace",
                dateTime: "May 1, 2026 - 9:00 AM",
                location: "Community Center A",
                joined: false
            }
        ],
        updates: [
            "Workshop schedule updated",
            "Bring IDs reminder",
            "Community garden milestone reached",
            "Market booth request deadline is Friday"
        ]
    };

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(value) {
        var safe = String(value || "");
        var lookup = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return safe.replace(/[&<>"']/g, function (character) {
            return lookup[character] || character;
        });
    }

    function setStatus(message) {
        if (!statusNode) {
            return;
        }
        statusNode.textContent = String(message || "").trim();
    }

    function typeLabel(type) {
        if (type === "discussions") {
            return "Discussion";
        }
        if (type === "tips") {
            return "Tip";
        }
        return "Announcement";
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }
        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function findPost(postId) {
        return state.posts.find(function (post) {
            return post.id === postId;
        }) || null;
    }

    function findEvent(eventId) {
        return state.events.find(function (eventItem) {
            return eventItem.id === eventId;
        }) || null;
    }

    function setComposerOpen(isOpen) {
        composerExpanded.hidden = !isOpen;
        if (isOpen && postInput) {
            window.requestAnimationFrame(function () {
                postInput.focus();
            });
        }
    }

    function canCloseComposer() {
        var hasText = postInput && postInput.value && postInput.value.trim().length > 0;
        return !hasText;
    }

    function renderFeed() {
        var posts = filteredPosts();

        if (feedCount) {
            feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");
        }

        if (!posts.length) {
            feedHost.innerHTML = '<p class="cd-empty">No posts in this filter yet. Try another tab or create the first one.</p>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            var firstTag = (post.tags && post.tags.length) ? post.tags[0] : typeLabel(post.type);
            var cardClass = "cd-post" + (post.expanded ? " is-expanded" : "");
            return [
                '<article class="' + cardClass + '" data-post-id="' + escapeHtml(post.id) + '" role="button" tabindex="0" aria-expanded="' + (post.expanded ? "true" : "false") + '">',
                '<header class="cd-post-top">',
                '<span class="cd-avatar cd-avatar--small" aria-hidden="true">' + escapeHtml(post.avatar) + '</span>',
                '<div class="cd-post-meta">',
                '<p class="cd-post-author">' + escapeHtml(post.author) + '</p>',
                '<p class="cd-post-time">' + escapeHtml(post.timestamp) + '</p>',
                '</div>',
                '<span class="cd-post-tag">' + escapeHtml(firstTag) + '</span>',
                '</header>',
                '<h4 class="cd-post-title">' + escapeHtml(post.title) + '</h4>',
                '<p class="cd-post-content">' + escapeHtml(post.content) + '</p>',
                '<div class="cd-post-actions">',
                '<button type="button" class="cd-post-action focus-ring' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post">',
                '<i data-lucide="heart" aria-hidden="true"></i>',
                '<span>' + post.likes + '</span>',
                '</button>',
                '<button type="button" class="cd-post-action focus-ring" data-post-action="comment" aria-label="Comment on post">',
                '<i data-lucide="message-circle" aria-hidden="true"></i>',
                '<span>' + post.comments + '</span>',
                '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");

        refreshIcons();
    }

    function renderEvents() {
        if (!state.events.length) {
            eventsHost.innerHTML = '<p class="cd-empty">No upcoming events yet.</p>';
            return;
        }

        eventsHost.innerHTML = state.events.map(function (eventItem) {
            var joined = !!eventItem.joined;
            var buttonClass = "cd-event-btn focus-ring" + (joined ? " is-joined" : "");
            return [
                '<article class="cd-event">',
                '<p class="cd-event-title">' + escapeHtml(eventItem.title) + '</p>',
                '<p class="cd-event-meta">' + escapeHtml(eventItem.dateTime) + '</p>',
                '<p class="cd-event-location">' + escapeHtml(eventItem.location) + '</p>',
                '<div class="cd-event-footer">',
                '<button type="button" class="' + buttonClass + '" data-event-id="' + escapeHtml(eventItem.id) + '">' + (joined ? "Joined" : "Join") + '</button>',
                '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderUpdates() {
        if (!state.updates.length) {
            updatesHost.innerHTML = '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>No updates yet.</span></li>';
            return;
        }

        updatesHost.innerHTML = state.updates.map(function (line) {
            return '<li class="cd-update-item"><span class="cd-update-dot" aria-hidden="true"></span><span>' + escapeHtml(line) + '</span></li>';
        }).join("");
    }

    function setActiveTab(tabName, moveFocus) {
        var valid = tabs.some(function (tabButton) {
            return tabButton.getAttribute("data-community-tab") === tabName;
        });
        if (!valid) {
            return;
        }

        state.activeTab = tabName;

        tabs.forEach(function (tabButton) {
            var selected = tabButton.getAttribute("data-community-tab") === tabName;
            tabButton.setAttribute("aria-selected", selected ? "true" : "false");
            tabButton.tabIndex = selected ? 0 : -1;
            if (selected && moveFocus) {
                tabButton.focus();
            }
        });

        renderFeed();
    }

    function derivePostTitle(message, category) {
        var source = String(message || "").trim();
        if (!source) {
            return typeLabel(category);
        }

        var words = source.split(/\s+/).slice(0, 7);
        var draft = words.join(" ");
        if (source.length > draft.length) {
            draft += "...";
        }
        return draft;
    }

    composerTrigger.addEventListener("click", function () {
        setComposerOpen(true);
    });

    if (postInput) {
        postInput.addEventListener("focus", function () {
            setComposerOpen(true);
        });
    }

    document.addEventListener("click", function (event) {
        if (!createForm.contains(event.target) && !composerExpanded.hidden && canCloseComposer()) {
            setComposerOpen(false);
        }
    });

    createForm.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = postInput ? postInput.value.trim() : "";
        var category = postCategory ? postCategory.value : "discussions";
        if (!content) {
            setStatus("Please write a short message first.");
            if (postInput) {
                postInput.focus();
            }
            return;
        }

        nextPostId += 1;
        state.posts.unshift({
            id: "post-" + nextPostId,
            author: "You",
            avatar: "YO",
            timestamp: "Just now",
            title: derivePostTitle(content, category),
            content: content,
            type: category,
            tags: [typeLabel(category)],
            likes: 0,
            comments: 0,
            liked: false,
            expanded: true
        });

        if (postInput) {
            postInput.value = "";
        }
        if (postCategory) {
            postCategory.value = "discussions";
        }

        setStatus("Posted to the community feed.");
        setComposerOpen(false);
        setActiveTab("all", false);
    });

    tabs.forEach(function (tabButton, index) {
        tabButton.addEventListener("click", function () {
            setActiveTab(tabButton.getAttribute("data-community-tab"), false);
        });

        tabButton.addEventListener("keydown", function (event) {
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

    feedHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-post-action]");
        var postCard = event.target.closest("[data-post-id]");
        if (!postCard) {
            return;
        }

        var post = findPost(postCard.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        if (actionButton) {
            var action = actionButton.getAttribute("data-post-action");
            if (action === "like") {
                post.liked = !post.liked;
                post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
+                renderFeed();
+                return;
            }
            if (action === "comment") {
                post.expanded = true;
+                renderFeed();
+                return;
            }
-            renderFeed();
-            return;
         }
 
         post.expanded = !post.expanded;
         renderFeed();
     });
@@
         if (!post) {
             return;
         }
 
         post.expanded = !post.expanded;
         renderFeed();
     });
 
     eventsHost.addEventListener("click", function (event) {
         var joinButton = event.target.closest("[data-event-id]");
         if (!joinButton) {
             return;
         }
 
         var eventItem = findEvent(joinButton.getAttribute("data-event-id"));
         if (!eventItem) {
             return;
         }
 
         eventItem.joined = !eventItem.joined;
         renderEvents();
         setStatus(eventItem.joined ? "Joined event: " + eventItem.title : "Left event: " + eventItem.title);
     });
 
     renderUpdates();
     renderEvents();
     setActiveTab("all", false);
     refreshIcons();
 })();
(function initCommunityHub() {
    "use strict";

    var root = document.getElementById("community-hub");
    if (!root || root.dataset.bound === "true") {
        return;
    }
    root.dataset.bound = "true";

    var feedHost = document.getElementById("community-feed");
    var feedCount = document.getElementById("community-feed-count");
    var announcementsHost = document.getElementById("community-announcements");
    var eventsHost = document.getElementById("community-events");
    var highlightsHost = document.getElementById("community-highlights");
    var highlightsMore = document.getElementById("community-highlights-more");

    var createForm = document.getElementById("community-create-post-form");
    var postInput = document.getElementById("community-post-input");
    var postCategory = document.getElementById("community-post-category");
    var attachmentTrigger = document.getElementById("community-post-attachment-trigger");
    var attachmentInput = document.getElementById("community-post-attachment");
    var attachmentTray = document.getElementById("community-attachment-tray");
    var createStatus = document.getElementById("community-create-status");
    var tabButtons = Array.prototype.slice.call(root.querySelectorAll("[data-community-tab]"));

    if (!feedHost || !announcementsHost || !eventsHost || !highlightsHost || !createForm) {
        return;
    }

    var nextPostId = 7;
    var nextAttachmentId = 0;

    var state = {
        activeTab: "all",
        posts: [
            {
                id: "post-1",
                author: "Maria S.",
                avatar: "MS",
                timestamp: "2 hours ago",
                title: "Tips for selling handmade products",
                content: "I found that posting before-and-after photos of products helps buyers trust quality faster. What pricing strategy works for your local market?",
                type: "tips",
                tags: ["Livelihood", "Handmade"],
                likes: 18,
                comments: [
                    { author: "Rosa M.", text: "Bundling products helped me increase weekly sales." },
                    { author: "Jules P.", text: "Try short demo videos during market day." }
                ],
                liked: false,
                saved: false,
                expanded: false,
                showComposer: false
            },
            {
                id: "post-2",
                author: "Juan D.",
                avatar: "JD",
                timestamp: "5 hours ago",
                title: "Best vegetables for small gardens",
                content: "For low-space setups, pechay and kangkong have been the easiest to maintain. I can share my small-pot watering routine if anyone needs it.",
                type: "discussions",
                tags: ["Gardening", "Food Security"],
                likes: 23,
                comments: [
                    { author: "Aira T.", text: "Please share your watering schedule." }
                ],
                liked: true,
                saved: true,
                expanded: false,
                showComposer: false
            },
            {
                id: "post-3",
                author: "Community Admin",
                avatar: "CA",
                timestamp: "1 day ago",
                title: "Upcoming community market on April 20",
                content: "Booth slots are now open for beneficiary products. Submit your booth request by Friday so we can finalize layout and logistics.",
                type: "announcements",
                tags: ["Marketplace", "Schedule"],
                likes: 12,
                comments: [
                    { author: "Mika R.", text: "Can we still join if we only have 3 products?" }
                ],
                liked: false,
                saved: false,
                expanded: false,
                showComposer: false
            },
            {
                id: "post-4",
                author: "Rosa M.",
                avatar: "RM",
                timestamp: "2 days ago",
                title: "Share your latest rag-making creations",
                content: "Let's collect photos from this week so we can feature local product ideas in the next livelihood workshop.",
                type: "discussions",
                tags: ["Rag-Making", "Community Support"],
                likes: 9,
                comments: [],
                liked: false,
                saved: false,
                expanded: false,
                showComposer: false
            }
        ],
        announcements: [
            {
                id: "ann-1",
                title: "Updated workshop schedule",
                body: "Skills and livelihood sessions now begin at 1:30 PM this week.",
                priority: "New"
            },
            {
                id: "ann-2",
                title: "Distribution guideline reminder",
                body: "Please bring beneficiary IDs to avoid queue delays on Saturday.",
                priority: "Important"
            },
            {
                id: "ann-3",
                title: "Community garden opening",
                body: "Seedling handout starts after the short orientation at 9:00 AM.",
                priority: "New"
            }
        ],
        events: [
            {
                id: "ev-1",
                title: "Community Workshop: Advanced Crafts",
                dateTime: "Apr 18, 2026 at 2:00 PM",
                location: "Covered Court Hall",
                joined: false,
                interestedByUser: true,
                interestedCount: 34
            },
            {
                id: "ev-2",
                title: "Monthly Community Meeting",
                dateTime: "Apr 25, 2026 at 10:00 AM",
                location: "Barangay Session Room",
                joined: true,
                interestedByUser: true,
                interestedCount: 52
            },
            {
                id: "ev-3",
                title: "Skills Fair and Marketplace",
                dateTime: "May 1, 2026 at 9:00 AM",
                location: "Community Center A",
                joined: false,
                interestedByUser: false,
                interestedCount: 61
            }
        ],
        highlights: [
            {
                id: "hl-1",
                label: "Most Active Member",
                value: "Maria S. - 14 helpful replies this month",
                note: "Recognized for consistently supporting new members."
            },
            {
                id: "hl-2",
                label: "Recent Success Story",
                value: "Household income improved through weekend craft sales",
                note: "Four beneficiary families started a shared stall initiative."
            },
            {
                id: "hl-3",
                label: "Featured Achievement",
                value: "Community garden reached 120 harvest bags",
                note: "Produce was shared across three nearby barangays this quarter."
            }
        ]
    };

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function escapeHtml(value) {
        var safe = String(value || "");
        var lookup = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return safe.replace(/[&<>"']/g, function (character) {
            return lookup[character] || character;
        });
    }

    function setCreateStatus(message) {
        if (createStatus) {
            var value = (message || "").trim();
            createStatus.textContent = value;
            createStatus.classList.toggle("has-message", value.length > 0);
        }
    }

    function fileExtension(fileName) {
        var name = String(fileName || "");
        var dotIndex = name.lastIndexOf(".");
        if (dotIndex < 0 || dotIndex === name.length - 1) {
            return "";
        }

        return name.slice(dotIndex + 1).toLowerCase();
    }

    function isImageFile(file) {
        if (!file) {
            return false;
        }

        var mimeType = String(file.type || "").toLowerCase();
        if (mimeType.indexOf("image/") === 0) {
            return true;
        }

        var extension = fileExtension(file.name);
        return ["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"].indexOf(extension) >= 0;
    }

    function attachmentIconName(fileName, mimeType) {
        var extension = fileExtension(fileName);
        var mime = String(mimeType || "").toLowerCase();

        if (extension === "pdf" || mime === "application/pdf") {
            return "file-text";
        }
        if (["doc", "docx", "txt", "rtf", "md"].indexOf(extension) >= 0) {
            return "file-text";
        }
        if (["xls", "xlsx", "csv"].indexOf(extension) >= 0) {
            return "file-spreadsheet";
        }
        if (["ppt", "pptx", "key"].indexOf(extension) >= 0) {
            return "presentation";
        }
        if (["zip", "rar", "7z"].indexOf(extension) >= 0) {
            return "archive";
        }

        return "file";
    }

    function formatFileSize(sizeInBytes) {
        var size = Number(sizeInBytes);
        if (!isFinite(size) || size < 0) {
            return "Unknown size";
        }

        var units = ["B", "KB", "MB", "GB"];
        var unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex += 1;
        }

        var rounded = size >= 10 || unitIndex === 0
            ? Math.round(size)
            : Math.round(size * 10) / 10;

        return rounded + " " + units[unitIndex];
    }

    function filteredPosts() {
        if (state.activeTab === "all") {
            return state.posts;
        }

        return state.posts.filter(function (post) {
            return post.type === state.activeTab;
        });
    }

    function findPostById(postId) {
        return state.posts.find(function (post) {
            return post.id === postId;
        }) || null;
    }

    function postImageItems(post) {
        var images = post && Array.isArray(post.images) ? post.images : [];
        return images.filter(function (imageItem) {
            return imageItem && typeof imageItem.src === "string" && imageItem.src.trim().length > 0;
        });
    }

    function postFileItems(post) {
        var attachments = post && Array.isArray(post.attachments) ? post.attachments : [];
        return attachments.filter(function (fileItem) {
            return fileItem && typeof fileItem.name === "string" && fileItem.name.trim().length > 0;
        });
    }

    function setActiveTab(tabKey, shouldFocus) {
        var tabToFocus = null;

        if (!tabButtons.some(function (tabButton) {
            return tabButton.getAttribute("data-community-tab") === tabKey;
        })) {
            return;
        }

        state.activeTab = tabKey;

        tabButtons.forEach(function (button) {
            var selected = button.getAttribute("data-community-tab") === tabKey;
            button.setAttribute("aria-selected", selected ? "true" : "false");
            button.tabIndex = selected ? 0 : -1;
            if (selected) {
                tabToFocus = button;
            }
        });

        renderFeed();

        if (shouldFocus && tabToFocus) {
            tabToFocus.focus();
        }
    }

    function createGalleryModal() {
        var modal = document.getElementById("community-gallery-modal");
        if (!modal) {
            modal = document.createElement("div");
            modal.id = "community-gallery-modal";
            modal.className = "ch-gallery-modal";
            modal.setAttribute("aria-hidden", "true");
            modal.innerHTML = ''
                + '<div class="ch-gallery-backdrop" data-gallery-action="close"></div>'
                + '<div class="ch-gallery-dialog" role="dialog" aria-modal="true" aria-label="Post image gallery">'
                    + '<button type="button" class="ch-gallery-close focus-ring" data-gallery-action="close" aria-label="Close gallery">'
                        + '<i data-lucide="x" class="ch-icon" aria-hidden="true"></i>'
                    + '</button>'
                    + '<div class="ch-gallery-stage">'
                        + '<button type="button" class="ch-gallery-nav prev focus-ring" data-gallery-action="prev" aria-label="Previous image">'
                            + '<i data-lucide="chevron-left" class="ch-icon" aria-hidden="true"></i>'
                        + '</button>'
                        + '<figure class="ch-gallery-figure">'
                            + '<img id="community-gallery-image" class="ch-gallery-image" alt="" loading="lazy">'
                            + '<figcaption id="community-gallery-caption" class="ch-gallery-caption"></figcaption>'
                        + '</figure>'
                        + '<button type="button" class="ch-gallery-nav next focus-ring" data-gallery-action="next" aria-label="Next image">'
                            + '<i data-lucide="chevron-right" class="ch-icon" aria-hidden="true"></i>'
                        + '</button>'
                    + '</div>'
                    + '<p id="community-gallery-counter" class="ch-gallery-counter" aria-live="polite"></p>'
                + '</div>';
            document.body.appendChild(modal);
            refreshIcons();
        }

        var imageEl = modal.querySelector("#community-gallery-image");
        var captionEl = modal.querySelector("#community-gallery-caption");
        var counterEl = modal.querySelector("#community-gallery-counter");
        var closeButton = modal.querySelector(".ch-gallery-close");
        var prevButton = modal.querySelector("[data-gallery-action='prev']");
        var nextButton = modal.querySelector("[data-gallery-action='next']");
        var galleryState = {
            images: [],
            index: 0
        };

        function isOpen() {
            return modal.classList.contains("is-open");
        }

        function normalizeIndex(index) {
            var total = galleryState.images.length;
            if (!total) {
                return 0;
            }

            if (index < 0) {
                return total - 1;
            }
            if (index >= total) {
                return 0;
            }

            return index;
        }

        function renderGallery() {
            var total = galleryState.images.length;
            if (!total || !imageEl) {
                return;
            }

            galleryState.index = normalizeIndex(galleryState.index);
            var current = galleryState.images[galleryState.index] || {};
            var caption = (current.alt || "").trim();

            imageEl.src = current.src || "";
            imageEl.alt = caption || ("Post image " + (galleryState.index + 1));

            if (captionEl) {
                captionEl.textContent = caption;
                captionEl.hidden = caption.length === 0;
            }

            if (counterEl) {
                counterEl.textContent = (galleryState.index + 1) + " / " + total;
            }

            var hasMultiple = total > 1;
            if (prevButton) {
                prevButton.disabled = !hasMultiple;
            }
            if (nextButton) {
                nextButton.disabled = !hasMultiple;
            }
        }

        function stepGallery(delta) {
            if (galleryState.images.length <= 1) {
                return;
            }

            galleryState.index = normalizeIndex(galleryState.index + delta);
            renderGallery();
        }

        function closeGallery() {
            if (!isOpen()) {
                return;
            }

            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
            document.body.classList.remove("ch-gallery-open");
            if (imageEl) {
                imageEl.removeAttribute("src");
            }
            galleryState.images = [];
            galleryState.index = 0;
        }

        function openGallery(images, startIndex) {
            if (!images || !images.length) {
                return;
            }

            galleryState.images = images.slice();
            galleryState.index = normalizeIndex(Number(startIndex) || 0);
            renderGallery();

            modal.classList.add("is-open");
            modal.setAttribute("aria-hidden", "false");
            document.body.classList.add("ch-gallery-open");

            if (closeButton) {
                closeButton.focus();
            }
        }

        modal.addEventListener("click", function (event) {
            var actionButton = event.target.closest("[data-gallery-action]");
            if (!actionButton) {
                return;
            }

            var action = actionButton.getAttribute("data-gallery-action");
            if (action === "close") {
                closeGallery();
            } else if (action === "prev") {
                stepGallery(-1);
            } else if (action === "next") {
                stepGallery(1);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (!isOpen()) {
                return;
            }

            if (event.key === "Escape") {
                event.preventDefault();
                closeGallery();
                return;
            }

            if (event.key === "ArrowLeft") {
                event.preventDefault();
                stepGallery(-1);
                return;
            }

            if (event.key === "ArrowRight") {
                event.preventDefault();
                stepGallery(1);
            }
        });

        return {
            open: openGallery,
            close: closeGallery
        };
    }

    var galleryModal = createGalleryModal();

    function PostCard(post) {
        var content = post.content || "";
        var shouldTrim = content.length > 120;
        var textClass = post.expanded ? "ch-post-text" : "ch-post-text is-clamped";
        var imageItems = postImageItems(post);
        var fileItems = postFileItems(post);
        var hasAttachments = imageItems.length > 0 || fileItems.length > 0;
        var postClass = "ch-post"
            + (hasAttachments ? " has-attachments is-media-split" : "");

        var visibleTags = (post.tags || []).slice(0, 2).map(function (tag) {
            return '<span class="ch-tag">' + escapeHtml(tag) + '</span>';
        }).join("");

        var hiddenTagCount = Math.max((post.tags || []).length - 2, 0);
        var moreTag = hiddenTagCount > 0
            ? '<span class="ch-tag">+' + hiddenTagCount + ' more</span>'
            : "";

        var firstComment = (post.comments || [])[0];
        var commentsBlock = (firstComment && post.showComposer)
            ? '<div class="ch-comment-preview"><p class="ch-comment-item"><strong>' + escapeHtml(firstComment.author) + ':</strong> ' + escapeHtml(firstComment.text) + '</p></div>'
            : "";

        var viewMore = shouldTrim
            ? '<button type="button" class="ch-link-btn focus-ring" data-post-action="toggle-content">' + (post.expanded ? "See less" : "See more") + '</button>'
            : "";
        var textToggle = viewMore
            ? '<div class="ch-post-expand">' + viewMore + '</div>'
            : "";

        var sideMediaBlock = "";
        if (hasAttachments) {
            var imageSection = "";
            var fileSection = "";

            if (imageItems.length > 0) {
                var primaryImage = imageItems[0];
                var imageAlt = primaryImage.alt || post.title || "Post image";
                var hiddenImageCount = Math.max(imageItems.length - 1, 0);
                var overlay = hiddenImageCount > 0
                    ? '<span class="ch-post-media-more">+' + hiddenImageCount + '</span>'
                    : "";

                imageSection = ''
                    + '<div class="ch-post-side-section ch-post-side-images">'
                        + '<button type="button" class="ch-post-media-single focus-ring" data-post-action="open-gallery" aria-label="Open image gallery">'
                            + '<img src="' + escapeHtml(primaryImage.src) + '" alt="' + escapeHtml(imageAlt) + '" loading="lazy">'
                            + overlay
                        + '</button>'
                    + '</div>';
            }

            if (fileItems.length > 0) {
                fileSection = ''
                    + '<div class="ch-post-side-section ch-post-side-files">'
                        + '<div class="ch-post-file-stack">'
                            + fileItems.map(function (attachment) {
                                var fileName = attachment.name || "Attachment";
                                var sizeLabel = attachment.sizeLabel || "";
                                var iconName = attachment.icon || attachmentIconName(fileName, "");
                                var href = attachment.url ? String(attachment.url).trim() : "";
                                var sizeMarkup = sizeLabel && sizeLabel !== "Attachment"
                                    ? '<p class="ch-post-file-size">' + escapeHtml(sizeLabel) + '</p>'
                                    : "";
                                var downloadLink = href
                                    ? '<a class="ch-post-file-link focus-ring" href="' + escapeHtml(href) + '" download="' + escapeHtml(fileName) + '" aria-label="Download ' + escapeHtml(fileName) + '"><i data-lucide="download" class="ch-icon" aria-hidden="true"></i></a>'
                                    : "";

                                return ''
                                    + '<article class="ch-post-file-card">'
                                        + '<div class="ch-post-file-main">'
                                            + '<i data-lucide="' + escapeHtml(iconName) + '" class="ch-icon" aria-hidden="true"></i>'
                                            + '<div class="ch-post-file-copy">'
                                                + '<p class="ch-post-file-name" title="' + escapeHtml(fileName) + '">' + escapeHtml(fileName) + '</p>'
                                                + sizeMarkup
                                            + '</div>'
                                        + '</div>'
                                        + downloadLink
                                    + '</article>';
                            }).join("")
                        + '</div>'
                    + '</div>';
            }

            sideMediaBlock = ''
                + '<aside class="ch-post-side" aria-label="Post attachments">'
                    + imageSection
                    + fileSection
                + '</aside>';
        }

        var commentComposer = post.showComposer
            ? '<form class="ch-comment-form" data-comment-form="true">'
                + '<label class="sr-only" for="comment-input-' + escapeHtml(post.id) + '">Write comment</label>'
                + '<input id="comment-input-' + escapeHtml(post.id) + '" name="comment" class="ch-comment-input focus-ring" type="text" maxlength="160" placeholder="Write a comment...">'
                + '<button type="submit" class="ch-comment-submit focus-ring">Post</button>'
                + '</form>'
            : "";

        return ''
            + '<article class="' + postClass + '" data-post-id="' + escapeHtml(post.id) + '">'
                + '<div class="ch-post-body">'
                    + '<div class="ch-post-main">'
                        + '<div class="ch-post-top">'
                            + '<div class="ch-author">'
                                + '<div class="ch-avatar" aria-hidden="true">' + escapeHtml(post.avatar) + '</div>'
                                + '<p class="ch-author-meta">'
                                    + '<span class="ch-author-name">' + escapeHtml(post.author) + '</span>'
                                    + '<span class="ch-author-meta-dot" aria-hidden="true"></span>'
                                    + '<span class="ch-post-time">' + escapeHtml(post.timestamp) + '</span>'
                                + '</p>'
                            + '</div>'
                        + '</div>'
                        + '<h4 class="ch-post-title">' + escapeHtml(post.title) + '</h4>'
                        + '<p class="' + textClass + '">' + escapeHtml(content) + '</p>'
                        + textToggle
                        + '<div class="ch-tags">' + visibleTags + moreTag + '</div>'
                        + '<div class="ch-actions">'
                            + '<button type="button" class="ch-action-btn focus-ring' + (post.liked ? ' is-active' : '') + '" data-post-action="like" aria-label="Like post">'
                                + '<i data-lucide="thumbs-up" class="ch-icon" aria-hidden="true"></i>'
                                + '<span class="ch-action-count">' + post.likes + '</span>'
                                + '<span class="sr-only">likes</span>'
                            + '</button>'
                            + '<button type="button" class="ch-action-btn focus-ring" data-post-action="comment" aria-label="Comment on post">'
                                + '<i data-lucide="message-circle" class="ch-icon" aria-hidden="true"></i>'
                                + '<span class="ch-action-count">' + (post.comments || []).length + '</span>'
                                + '<span class="sr-only">comments</span>'
                            + '</button>'
                            + '<button type="button" class="ch-action-btn focus-ring' + (post.saved ? ' is-active' : '') + '" data-post-action="save" aria-label="Save post">'
                                + '<i data-lucide="bookmark" class="ch-icon" aria-hidden="true"></i>'
                                + '<span class="sr-only">' + (post.saved ? 'Saved' : 'Save') + '</span>'
                            + '</button>'
                        + '</div>'
                        + commentsBlock
                        + commentComposer
                    + '</div>'
                    + sideMediaBlock
                + '</div>'
            + '</article>';
    }

    function renderFeed() {
        var posts = filteredPosts();

        if (feedCount) {
            feedCount.textContent = posts.length + (posts.length === 1 ? " post" : " posts");
        }

        if (!posts.length) {
            feedHost.innerHTML = '<div class="ch-empty">No posts found in this filter yet. Try another tab or share the first post.</div>';
            refreshIcons();
            return;
        }

        feedHost.innerHTML = posts.map(function (post) {
            return PostCard(post);
        }).join("");

        refreshIcons();
    }

    function AnnouncementsPanel() {
        announcementsHost.innerHTML = state.announcements.map(function (announcement) {
            var priorityText = String(announcement.priority || "").trim();
            var isImportant = priorityText.toLowerCase() === "important";
            var priorityClass = isImportant ? "important" : "new";
            var rowClass = "ch-announcement" + (isImportant ? " is-important" : " is-new");
            var titleText = String(announcement.title || "Community update").trim();
            var bodyText = String(announcement.body || "No details provided.").trim();

            if (bodyText.length > 120) {
                bodyText = bodyText.slice(0, 117) + "...";
            }

            return ''
                + '<article class="' + rowClass + '">'
                    + '<div class="ch-announcement-row">'
                        + '<p class="ch-announcement-title"><i data-lucide="megaphone" class="ch-announcement-icon" aria-hidden="true"></i><span>' + escapeHtml(titleText) + '</span></p>'
                        + '<span class="ch-priority ' + priorityClass + '">' + escapeHtml(priorityText || "New") + '</span>'
                    + '</div>'
                    + '<p class="ch-announcement-body">' + escapeHtml(bodyText) + '</p>'
                + '</article>';
        }).join("");

        refreshIcons();
    }

    function EventsPanel() {
        eventsHost.innerHTML = state.events.map(function (eventItem) {
            var joinLabel = eventItem.joined ? "Joined" : "Join";
            var interestLabel = eventItem.interestedCount + " interested";

            return ''
                + '<article class="ch-event">'
                    + '<div class="ch-event-main">'
                        + '<p class="ch-event-title">' + escapeHtml(eventItem.title) + '</p>'
                        + '<div class="ch-event-meta-row">'
                            + '<p class="ch-event-meta">' + escapeHtml(eventItem.dateTime) + '</p>'
                            + '<p class="ch-event-location" title="' + escapeHtml(eventItem.location) + '">' + escapeHtml(eventItem.location) + '</p>'
                        + '</div>'
                    + '</div>'
                    + '<div class="ch-event-footer">'
                        + '<p class="ch-event-interest">' + escapeHtml(interestLabel) + '</p>'
                        + '<button type="button" class="ch-event-action focus-ring' + (eventItem.joined ? ' is-active' : '') + '" data-event-id="' + escapeHtml(eventItem.id) + '" data-event-action="join">' + joinLabel + '</button>'
                    + '</div>'
                + '</article>';
        }).join("");
    }

    function HighlightsPanel() {
        highlightsHost.innerHTML = state.highlights.map(function (highlight) {
            var summary = (highlight.label ? highlight.label + ": " : "") + (highlight.value || "");

            return ''
                + '<article class="ch-highlight">'
                    + '<p class="ch-highlight-line" title="' + escapeHtml(summary) + '">'
                        + '<span class="ch-highlight-marker" aria-hidden="true"></span>'
                        + '<span class="ch-highlight-text">' + escapeHtml(summary) + '</span>'
                    + '</p>'
                + '</article>';
        }).join("");
    }

    function CreatePostBox() {
        var composerAttachments = [];
        var trayVisibleLimit = 4;

        function hasComposerContent() {
            var hasText = postInput && postInput.value && postInput.value.trim().length > 0;
            var hasFile = composerAttachments.length > 0;
            return !!(hasText || hasFile);
        }

        function setComposerExpanded(expanded) {
            createForm.classList.toggle("is-active", !!expanded);
        }

        function clearNativeFileInput() {
            if (!attachmentInput) {
                return;
            }

            try {
                attachmentInput.value = "";
            } catch (e) {
                // Ignore assignment restrictions in older browsers.
            }
        }

        function attachmentSignature(file) {
            if (!file) {
                return "";
            }

            var name = file.name || "";
            var size = Number(file.size) || 0;
            var modified = Number(file.lastModified) || 0;
            var type = file.type || "";
            return [name, size, modified, type].join("|");
        }

        function createComposerAttachment(file) {
            var fileName = (file && file.name) ? file.name : "Attachment";
            var imageFile = isImageFile(file);
            var previewUrl = "";

            if (imageFile && window.URL && typeof window.URL.createObjectURL === "function") {
                previewUrl = window.URL.createObjectURL(file);
            }

            nextAttachmentId += 1;

            return {
                id: "composer-attachment-" + nextAttachmentId,
                file: file,
                name: fileName,
                sizeLabel: formatFileSize(file ? file.size : 0),
                icon: attachmentIconName(fileName, file ? file.type : ""),
                isImage: imageFile,
                previewUrl: previewUrl,
                signature: attachmentSignature(file)
            };
        }

        function releaseComposerAttachment(attachment) {
            if (!attachment || !attachment.previewUrl) {
                return;
            }

            if (window.URL && typeof window.URL.revokeObjectURL === "function") {
                window.URL.revokeObjectURL(attachment.previewUrl);
            }

            attachment.previewUrl = "";
        }

        function renderComposerAttachmentTray() {
            if (!attachmentTray) {
                return;
            }

            if (!composerAttachments.length) {
                attachmentTray.classList.remove("has-items");
                attachmentTray.innerHTML = "";
                return;
            }

            var visibleAttachments = composerAttachments.slice(0, trayVisibleLimit);
            var hiddenCount = Math.max(composerAttachments.length - visibleAttachments.length, 0);

            attachmentTray.innerHTML = visibleAttachments.map(function (attachment) {
                var safeId = escapeHtml(attachment.id);
                var safeName = escapeHtml(attachment.name || "Attachment");

                if (attachment.isImage && attachment.previewUrl) {
                    return ''
                        + '<article class="ch-tray-item image" data-composer-attachment-id="' + safeId + '">'
                            + '<img class="ch-tray-thumb" src="' + escapeHtml(attachment.previewUrl) + '" alt="' + safeName + '" loading="lazy">'
                            + '<button type="button" class="ch-tray-remove focus-ring" data-remove-composer-attachment="' + safeId + '" aria-label="Remove ' + safeName + '">'
                                + '<i data-lucide="x" class="ch-icon" aria-hidden="true"></i>'
                            + '</button>'
                        + '</article>';
                }

                return ''
                    + '<article class="ch-tray-item file" data-composer-attachment-id="' + safeId + '">'
                        + '<div class="ch-tray-file-main">'
                            + '<i data-lucide="' + escapeHtml(attachment.icon || "file") + '" class="ch-icon" aria-hidden="true"></i>'
                            + '<div class="ch-tray-file-copy">'
                                + '<p class="ch-tray-file-name" title="' + safeName + '">' + safeName + '</p>'
                                + '<p class="ch-tray-file-size">' + escapeHtml(attachment.sizeLabel || "Attachment") + '</p>'
                            + '</div>'
                        + '</div>'
                        + '<button type="button" class="ch-tray-remove focus-ring" data-remove-composer-attachment="' + safeId + '" aria-label="Remove ' + safeName + '">'
                            + '<i data-lucide="x" class="ch-icon" aria-hidden="true"></i>'
                        + '</button>'
                    + '</article>';
            }).join("") + (hiddenCount > 0
                ? '<span class="ch-tray-more" aria-label="' + hiddenCount + ' more attachments">+' + hiddenCount + ' more</span>'
                : "");

            attachmentTray.classList.add("has-items");
            refreshIcons();
        }

        function clearComposerAttachments() {
            composerAttachments.forEach(function (attachment) {
                releaseComposerAttachment(attachment);
            });

            composerAttachments = [];
            clearNativeFileInput();
            renderComposerAttachmentTray();
        }

        function removeComposerAttachment(attachmentId) {
            var attachmentIndex = composerAttachments.findIndex(function (attachment) {
                return attachment.id === attachmentId;
            });

            if (attachmentIndex < 0) {
                return;
            }

            var removedAttachment = composerAttachments.splice(attachmentIndex, 1)[0];
            releaseComposerAttachment(removedAttachment);
            renderComposerAttachmentTray();
        }

        function addFilesToComposer(fileList) {
            if (!fileList || !fileList.length) {
                return;
            }

            var existingSignatures = new Set(composerAttachments.map(function (attachment) {
                return attachment.signature;
            }));

            fileList.forEach(function (file) {
                if (!file) {
                    return;
                }

                var signature = attachmentSignature(file);
                if (existingSignatures.has(signature)) {
                    return;
                }

                existingSignatures.add(signature);
                composerAttachments.push(createComposerAttachment(file));
            });

            renderComposerAttachmentTray();
        }

        function openAttachmentPicker() {
            if (!attachmentInput) {
                return;
            }

            setComposerExpanded(true);
            setCreateStatus("");

            clearNativeFileInput();

            if (typeof attachmentInput.showPicker === "function") {
                try {
                    attachmentInput.showPicker();
                    return;
                } catch (e) {
                    // Fall back to click when showPicker is unavailable.
                }
            }

            attachmentInput.click();
        }

        createForm.addEventListener("focusin", function () {
            setComposerExpanded(true);
        });

        createForm.addEventListener("focusout", function () {
            window.setTimeout(function () {
                var focusInside = createForm.contains(document.activeElement);
                if (!focusInside && !hasComposerContent()) {
                    setComposerExpanded(false);
                }
            }, 0);
        });

        if (attachmentTrigger && attachmentInput) {
            attachmentTrigger.addEventListener("pointerdown", function (event) {
                event.preventDefault();
                setComposerExpanded(true);
            });

            attachmentTrigger.addEventListener("mousedown", function (event) {
                event.preventDefault();
                setComposerExpanded(true);
            });

            attachmentTrigger.addEventListener("click", function (event) {
                event.preventDefault();
                openAttachmentPicker();
            });
        }

        if (attachmentTray) {
            attachmentTray.addEventListener("click", function (event) {
                var removeButton = event.target.closest("[data-remove-composer-attachment]");
                if (!removeButton) {
                    return;
                }

                event.preventDefault();
                removeComposerAttachment(removeButton.getAttribute("data-remove-composer-attachment"));
                setCreateStatus("");

                if (!hasComposerContent()) {
                    setComposerExpanded(false);
                }
            });
        }

        if (attachmentInput) {
            attachmentInput.addEventListener("change", function () {
                var files = attachmentInput.files
                    ? Array.prototype.slice.call(attachmentInput.files)
                    : [];

                if (!files.length) {
                    return;
                }

                addFilesToComposer(files);
                setComposerExpanded(true);
                setCreateStatus("");
                clearNativeFileInput();
            });
        }

        if (postInput) {
            postInput.addEventListener("input", function () {
                setComposerExpanded(true);
                setCreateStatus("");
            });
        }

        createForm.addEventListener("submit", function (event) {
            event.preventDefault();

            var content = postInput ? postInput.value.trim() : "";
            if (!content && !composerAttachments.length) {
                setCreateStatus("Please add a message or attach at least one file before posting.");
                if (postInput) {
                    postInput.focus();
                }
                return;
            }

            nextPostId += 1;

            var selectedCategory = postCategory && postCategory.value ? postCategory.value : "Community Support";
            var postType = /\?$/.test(content)
                ? "discussions"
                : (selectedCategory === "Community Support" ? "discussions" : "tips");
            var titleMap = {
                discussions: "Community question",
                tips: "Community tip"
            };
            var mediaImages = [];
            var mediaFiles = [];

            composerAttachments.forEach(function (selectedAttachment) {
                var file = selectedAttachment.file;
                if (!file) {
                    return;
                }

                var fileName = selectedAttachment.name || "Attachment";
                var objectUrl = "";
                if (window.URL && typeof window.URL.createObjectURL === "function") {
                    objectUrl = window.URL.createObjectURL(file);
                }

                if (selectedAttachment.isImage && objectUrl) {
                    mediaImages.push({
                        src: objectUrl,
                        alt: fileName
                    });
                    return;
                }

                mediaFiles.push({
                    name: fileName,
                    sizeLabel: selectedAttachment.sizeLabel || formatFileSize(file.size),
                    url: objectUrl,
                    icon: selectedAttachment.icon || attachmentIconName(fileName, file.type)
                });
            });

            var fallbackContent = "";
            if (!content) {
                if (mediaImages.length > 0 && mediaFiles.length > 0) {
                    fallbackContent = "Shared images and files with the community.";
                } else if (mediaImages.length > 0) {
                    fallbackContent = "Shared images with the community.";
                } else {
                    fallbackContent = "Shared files with the community.";
                }
            }

            var postTitle = titleMap[postType] || "Community post";
            if (!content) {
                postTitle = composerAttachments.length === 1 ? "Shared an attachment" : "Shared attachments";
            }

            var newTags = [selectedCategory, "Beneficiary"];
            if (mediaImages.length > 0) {
                newTags.push(mediaImages.length === 1 ? "Photo" : "Photos");
            }
            if (mediaFiles.length > 0) {
                newTags.push(mediaFiles.length === 1 ? "File" : "Files");
            }

            state.posts.unshift({
                id: "post-" + nextPostId,
                author: "You",
                avatar: "YO",
                timestamp: "Just now",
                title: postTitle,
                content: content || fallbackContent,
                type: postType,
                tags: newTags,
                likes: 0,
                comments: [],
                liked: false,
                saved: false,
                expanded: true,
                showComposer: false,
                images: mediaImages,
                attachments: mediaFiles
            });

            createForm.reset();
            clearComposerAttachments();
            setComposerExpanded(false);

            setActiveTab("all", false);
            setCreateStatus("Your post is now visible in the community feed.");
        });

        renderComposerAttachmentTray();
    }

    function CommunityTabs() {
        tabButtons.forEach(function (button, index) {
            button.addEventListener("click", function () {
                setActiveTab(button.getAttribute("data-community-tab"), false);
            });

            button.addEventListener("keydown", function (event) {
                var nextIndex = index;

                if (event.key === "ArrowRight") {
                    nextIndex = (index + 1) % tabButtons.length;
                } else if (event.key === "ArrowLeft") {
                    nextIndex = (index - 1 + tabButtons.length) % tabButtons.length;
                } else if (event.key === "Home") {
                    nextIndex = 0;
                } else if (event.key === "End") {
                    nextIndex = tabButtons.length - 1;
                } else {
                    return;
                }

                event.preventDefault();
                setActiveTab(tabButtons[nextIndex].getAttribute("data-community-tab"), true);
            });
        });
    }

    feedHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-post-action]");
        if (!actionButton) {
            return;
        }

        var postNode = actionButton.closest("[data-post-id]");
        if (!postNode) {
            return;
        }

        var post = findPostById(postNode.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        var action = actionButton.getAttribute("data-post-action");
        if (action === "open-gallery") {
            galleryModal.open(postImageItems(post), 0);
            return;
        }

        if (action === "like") {
            post.liked = !post.liked;
            post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
        } else if (action === "save") {
            post.saved = !post.saved;
        } else if (action === "toggle-content") {
            post.expanded = !post.expanded;
        } else if (action === "comment") {
            post.showComposer = !post.showComposer;
        }

        renderFeed();
    });

    feedHost.addEventListener("submit", function (event) {
        var commentForm = event.target.closest("[data-comment-form]");
        if (!commentForm) {
            return;
        }

        event.preventDefault();

        var postNode = commentForm.closest("[data-post-id]");
        if (!postNode) {
            return;
        }

        var post = findPostById(postNode.getAttribute("data-post-id"));
        if (!post) {
            return;
        }

        var input = commentForm.querySelector("input[name='comment']");
        var commentText = input ? input.value.trim() : "";
        if (!commentText) {
            if (input) {
                input.focus();
            }
            return;
        }

        post.comments.unshift({
            author: "You",
            text: commentText
        });
        post.showComposer = false;
        post.expanded = true;

        renderFeed();
    });

    eventsHost.addEventListener("click", function (event) {
        var actionButton = event.target.closest("[data-event-action]");
        if (!actionButton) {
            return;
        }

        var eventId = actionButton.getAttribute("data-event-id");
        var action = actionButton.getAttribute("data-event-action");
        var selectedEvent = state.events.find(function (item) {
            return item.id === eventId;
        });

        if (!selectedEvent) {
            return;
        }

        if (action === "join") {
            var wasInterested = !!selectedEvent.interestedByUser;
            selectedEvent.joined = !selectedEvent.joined;
            selectedEvent.interestedByUser = selectedEvent.joined;

            if (selectedEvent.joined && !wasInterested) {
                selectedEvent.interestedCount += 1;
            } else if (!selectedEvent.joined && wasInterested) {
                selectedEvent.interestedCount = Math.max(0, selectedEvent.interestedCount - 1);
            }

            setCreateStatus(selectedEvent.joined ? "You joined: " + selectedEvent.title : "You left: " + selectedEvent.title);
        }

        EventsPanel();
    });

    if (highlightsMore) {
        highlightsMore.addEventListener("click", function () {
            setCreateStatus("More community highlights will be available soon.");
        });
    }

    CommunityTabs();
    CreatePostBox();
    AnnouncementsPanel();
    EventsPanel();
    HighlightsPanel();
    setActiveTab("all", false);
    refreshIcons();
})();

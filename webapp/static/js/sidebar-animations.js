/**
 * Sidebar Click Animations & Transitions
 * 
 * Enhances user interactions with smooth click animations,
 * highlight effects, and visual feedback on navigation items.
 */

(function initSidebarAnimations() {
    const SIDEBAR_ID = 'dashboard-sidebar';
    const LINK_SELECTOR = '.sidebar-link';
    const ACTIVE_CLASS = 'active';
    const ANIMATION_DURATION = 180; // milliseconds
    
    /**
     * Get the sidebar element
     */
    function getSidebar() {
        return document.getElementById(SIDEBAR_ID);
    }
    
    /**
     * Enhance a link with click animation
     */
    function enhanceLinkWithAnimation(link) {
        // Skip logout links and already enhanced links
        if (link.dataset.animationEnhanced || link.getAttribute('href')?.includes('logout') || link.dataset.noClickAnimation === 'true') {
            return;
        }
        
        link.dataset.animationEnhanced = 'true';
        
        /**
         * Handle click animation
         */
        link.addEventListener('click', function(e) {
            performClickAnimation(this);
        });
        
        /**
         * Handle keyboard activation (Enter/Space)
         */
        link.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                performClickAnimation(this);
                // Trigger the click after animation completes
                setTimeout(() => this.click(), ANIMATION_DURATION / 2);
            }
        });
    }
    
    /**
     * Perform the click animation effect
     */
    function performClickAnimation(linkElement) {
        // Add short click state for subtle visual feedback
        linkElement.classList.add('is-clicked');
        
        // Remove the animation class after duration
        setTimeout(() => {
            linkElement.classList.remove('is-clicked');
        }, ANIMATION_DURATION);
        
        // Animate the icon
        const iconWrap = linkElement.querySelector('.sidebar-icon-wrap');
        if (iconWrap) {
            iconWrap.style.animation = 'none';
            // Force reflow to restart animation
            void iconWrap.offsetWidth;
            iconWrap.style.animation = 'sidebar-icon-scale 180ms ease-out';
        }
    }
    
    /**
     * Update active state styling
     */
    function updateActiveState() {
        const sidebar = getSidebar();
        if (!sidebar) return;
        
        const links = sidebar.querySelectorAll(LINK_SELECTOR);
        
        links.forEach(link => {
            // Check if this link is the current page
            const isCurrent = link.hasAttribute('aria-current') && 
                            link.getAttribute('aria-current') === 'page';

            if (link.dataset.noClickAnimation === 'true') {
                link.classList.remove(ACTIVE_CLASS);
                link.style.animation = '';
                return;
            }
            
            if (isCurrent) {
                link.classList.add(ACTIVE_CLASS);
                // Keep active class only; visuals are handled by CSS transitions
                link.style.animation = '';
            } else {
                link.classList.remove(ACTIVE_CLASS);
            }
        });
    }
    
    /**
     * Initialize all sidebar animations
     */
    function init() {
        const sidebar = getSidebar();
        if (!sidebar) {
            console.warn('Sidebar element not found. Animations not initialized.');
            return;
        }
        
        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initAnimations);
        } else {
            initAnimations();
        }
    }
    
    /**
     * Initialize animations on all sidebar links
     */
    function initAnimations() {
        const sidebar = getSidebar();
        if (!sidebar) return;
        
        const links = sidebar.querySelectorAll(LINK_SELECTOR);
        links.forEach(link => {
            enhanceLinkWithAnimation(link);
        });
        
        // Update active states
        updateActiveState();
        
        // Watch for mutations to handle dynamically added links
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        const newLinks = node.querySelectorAll?.(LINK_SELECTOR);
                        newLinks?.forEach(link => {
                            enhanceLinkWithAnimation(link);
                        });
                    }
                });
            });
        });
        
        observer.observe(sidebar, {
            childList: true,
            subtree: true,
            attributes: false,
            characterData: false
        });
    }
    
    // Initialize when this script is loaded
    init();
    
    // Expose public API for testing
    window.SidebarAnimations = {
        performClickAnimation,
        updateActiveState,
        getSidebar
    };
})();

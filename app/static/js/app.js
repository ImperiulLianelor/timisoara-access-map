/**
 * Timisoara Accessibility Map
 * Main application JavaScript
 */

/**
 * Main application class
 */
class AccessibilityApp {
    constructor() {
        // App state
        this.state = {
            highContrast: false,
            textSize: 'normal', // normal, large, xl
            userPreferences: null
        };
        
        // Initialize the application
        this.init();
    }
    
    /**
     * Initialize the application
     */
    init() {
        // Load saved preferences
        this.loadPreferences();
        
        // Initialize UI components
        this.initMobileMenu();
        this.initAccessibilityTools();
        this.initFlashMessages();
        this.initLanguageToggle();
        
        // Apply saved preferences
        this.applyPreferences();
    }
    
    /**
     * Initialize mobile menu
     */
    initMobileMenu() {
        const menuToggle = document.querySelector('.menu-toggle');
        const navMenu = document.querySelector('.nav-menu');
        
        if (menuToggle && navMenu) {
            menuToggle.addEventListener('click', () => {
                const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
                
                // Toggle menu visibility
                navMenu.classList.toggle('open');
                
                // Update ARIA state
                menuToggle.setAttribute('aria-expanded', !expanded);
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', (event) => {
                if (!menuToggle.contains(event.target) && !navMenu.contains(event.target) && navMenu.classList.contains('open')) {
                    navMenu.classList.remove('open');
                    menuToggle.setAttribute('aria-expanded', 'false');
                }
            });
        }
        
        // Add controls sidebar toggle for mobile
        const mapContainer = document.querySelector('.map-container');
        const controlsSidebar = document.querySelector('.controls-sidebar');
        
        if (mapContainer && controlsSidebar && window.innerWidth < 768) {
            mapContainer.addEventListener('click', (event) => {
                // Check if click was on the toggle button (::before pseudo-element)
                const rect = mapContainer.getBoundingClientRect();
                const isToggleClick = (
                    event.clientX - rect.left < 50 && 
                    event.clientY - rect.top < 50
                );
                
                if (isToggleClick) {
                    controlsSidebar.classList.toggle('open');
                }
            });
            
            // Add a close button to the sidebar
            const closeButton = document.createElement('button');
            closeButton.className = 'close-sidebar';
            closeButton.innerHTML = '&times;';
            closeButton.setAttribute('aria-label', 'Close filters sidebar');
            
            controlsSidebar.appendChild(closeButton);
            
            closeButton.addEventListener('click', () => {
                controlsSidebar.classList.remove('open');
            });
        }
    }
    
    /**
     * Initialize accessibility tools
     */
    initAccessibilityTools() {
        // High contrast toggle
        const highContrastBtn = document.querySelector('.toggle-high-contrast');
        if (highContrastBtn) {
            highContrastBtn.addEventListener('click', () => {
                this.toggleHighContrast();
            });
        }
        
        // Text size controls
        const increaseTextBtn = document.querySelector('.increase-text-size');
        const decreaseTextBtn = document.querySelector('.decrease-text-size');
        
        if (increaseTextBtn) {
            increaseTextBtn.addEventListener('click', () => {
                this.increaseTextSize();
            });
        }
        
        if (decreaseTextBtn) {
            decreaseTextBtn.addEventListener('click', () => {
                this.decreaseTextSize();
            });
        }
        
        // Keyboard accessibility
        this.setupKeyboardAccessibility();
    }
    
    /**
     * Initialize flash messages
     */
    initFlashMessages() {
        const closeButtons = document.querySelectorAll('.close-alert');
        
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const alert = button.closest('.alert');
                
                if (alert) {
                    alert.style.opacity = '0';
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 300);
                }
            });
        });
        
        // Auto-hide flash messages after 5 seconds
        setTimeout(() => {
            document.querySelectorAll('.alert').forEach(alert => {
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 300);
            });
        }, 5000);
    }
    
    /**
     * Initialize language toggle
     */
    initLanguageToggle() {
        const languageLinks = document.querySelectorAll('.language-toggle a');
        
        languageLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Language switch is handled by the server
                // We just show a loading indicator
                document.body.classList.add('loading');
            });
        });
    }
    
    /**
     * Setup keyboard accessibility
     */
    setupKeyboardAccessibility() {
        // Add focus visible utility
        document.body.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });
        
        document.body.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
        
        // ESC key to close modals and sidebars
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close any open sidebars
                const openSidebars = document.querySelectorAll('.sidebar.open');
                if (openSidebars.length > 0) {
                    openSidebars.forEach(sidebar => {
                        sidebar.classList.remove('open');
                    });
                    e.preventDefault();
                }
                
                // Close mobile menu if open
                const navMenu = document.querySelector('.nav-menu.open');
                if (navMenu) {
                    navMenu.classList.remove('open');
                    document.querySelector('.menu-toggle').setAttribute('aria-expanded', 'false');
                    e.preventDefault();
                }
            }
        });
    }
    
    /**
     * Toggle high contrast mode
     */
    toggleHighContrast() {
        this.state.highContrast = !this.state.highContrast;
        
        // Apply high contrast class to body
        document.body.classList.toggle('high-contrast', this.state.highContrast);
        
        // Add override class to prevent system preferences from conflicting
        document.body.classList.add('high-contrast-override');
        
        // Save preference
        this.savePreferences();
        
        // Announce change for screen readers
        this.announceAccessibilityChange(
            `High contrast mode ${this.state.highContrast ? 'enabled' : 'disabled'}`
        );
    }
    
    /**
     * Increase text size
     */
    increaseTextSize() {
        if (this.state.textSize === 'normal') {
            this.state.textSize = 'large';
            document.body.classList.add('large-text');
            document.body.classList.remove('xl-text');
        } else if (this.state.textSize === 'large') {
            this.state.textSize = 'xl';
            document.body.classList.remove('large-text');
            document.body.classList.add('xl-text');
        }
        
        // Save preference
        this.savePreferences();
        
        // Announce change for screen readers
        this.announceAccessibilityChange(
            `Text size increased to ${this.state.textSize}`
        );
    }
    
    /**
     * Decrease text size
     */
    decreaseTextSize() {
        if (this.state.textSize === 'xl') {
            this.state.textSize = 'large';
            document.body.classList.add('large-text');
            document.body.classList.remove('xl-text');
        } else if (this.state.textSize === 'large') {
            this.state.textSize = 'normal';
            document.body.classList.remove('large-text');
            document.body.classList.remove('xl-text');
        }
        
        // Save preference
        this.savePreferences();
        
        // Announce change for screen readers
        this.announceAccessibilityChange(
            `Text size decreased to ${this.state.textSize}`
        );
    }
    
    /**
     * Apply saved preferences
     */
    applyPreferences() {
        // Apply high contrast if enabled
        if (this.state.highContrast) {
            document.body.classList.add('high-contrast');
            document.body.classList.add('high-contrast-override');
        }
        
        // Apply text size
        if (this.state.textSize === 'large') {
            document.body.classList.add('large-text');
        } else if (this.state.textSize === 'xl') {
            document.body.classList.add('xl-text');
        }
        
        // Apply user accessibility preferences to filters
        if (this.state.userPreferences && window.accessibilityFilters) {
            window.accessibilityFilters.setFromUserPreferences(this.state.userPreferences);
        }
    }
    
    /**
     * Save preferences to localStorage
     */
    savePreferences() {
        try {
            localStorage.setItem('accessibility_preferences', JSON.stringify({
                highContrast: this.state.highContrast,
                textSize: this.state.textSize
            }));
        } catch (e) {
            console.warn('Could not save preferences to localStorage:', e);
        }
    }
    
    /**
     * Load preferences from localStorage
     */
    loadPreferences() {
        try {
            const saved = localStorage.getItem('accessibility_preferences');
            if (saved) {
                const preferences = JSON.parse(saved);
                this.state.highContrast = preferences.highContrast || false;
                this.state.textSize = preferences.textSize || 'normal';
            }
            
            // Check for user preferences in data attribute (set by server)
            const userPrefsElement = document.getElementById('user-preferences');
            if (userPrefsElement && userPrefsElement.dataset.preferences) {
                this.state.userPreferences = JSON.parse(userPrefsElement.dataset.preferences);
            }
        } catch (e) {
            console.warn('Could not load preferences from localStorage:', e);
        }
    }
    
    /**
     * Show notification message
     * @param {string} message The message to display
     * @param {string} type The notification type (info, success, warning, error)
     * @param {number} duration Duration in milliseconds (0 for no auto-hide)
     */
    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="message">${message}</span>
            <button class="close-notification" aria-label="Close notification">&times;</button>
        `;
        
        // Make it accessible
        notification.setAttribute('role', 'alert');
        
        // Add to container
        container.appendChild(notification);
        
        // Add close functionality
        const closeBtn = notification.querySelector('.close-notification');
        closeBtn.addEventListener('click', () => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        
        // Auto-hide after duration if specified
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.add('fade-out');
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.remove();
                        }
                    }, 300);
                }
            }, duration);
        }
    }
    
    /**
     * Announce changes for screen readers
     * @param {string} message The message to announce
     */
    announceAccessibilityChange(message) {
        let announcer = document.getElementById('accessibility-announcer');
        
        if (!announcer) {
            announcer = document.createElement('div');
            announcer.id = 'accessibility-announcer';
            announcer.setAttribute('role', 'status');
            announcer.setAttribute('aria-live', 'polite');
            announcer.className = 'sr-only';
            document.body.appendChild(announcer);
        }
        
        announcer.textContent = message;
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AccessibilityApp();
    
    // Handle close buttons for sidebars
    document.querySelectorAll('.close-sidebar, .close-btn').forEach(button => {
        button.addEventListener('click', () => {
            const sidebar = button.closest('.sidebar');
            if (sidebar) {
                sidebar.classList.remove('open');
            }
        });
    });
    
    // Initialize any standalone close buttons
    document.querySelectorAll('[data-dismiss]').forEach(element => {
        element.addEventListener('click', () => {
            const target = document.getElementById(element.dataset.dismiss);
            if (target) {
                target.style.display = 'none';
            }
        });
    });
});

// Add utility functions to the global scope
window.utils = {
    /**
     * Format a date in the user's locale
     * @param {string} dateString ISO date string
     * @param {object} options Intl.DateTimeFormat options
     * @returns {string} Formatted date string
     */
    formatDate(dateString, options = {}) {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat(document.documentElement.lang || 'ro', options).format(date);
    },
    
    /**
     * Format a number as a percentage
     * @param {number} value The value to format
     * @param {number} decimals Number of decimal places
     * @returns {string} Formatted percentage
     */
    formatPercent(value, decimals = 0) {
        return `${value.toFixed(decimals)}%`;
    },
    
    /**
     * Show loading indicator
     * @param {HTMLElement} element Element to show loading on
     * @param {string} text Optional loading text
     */
    showLoading(element, text = 'Loading...') {
        // Save original content
        element.dataset.originalContent = element.innerHTML;
        
        // Show loading
        element.innerHTML = `<span class="loading-spinner"></span> ${text}`;
        element.classList.add('is-loading');
    },
    
    /**
     * Hide loading indicator
     * @param {HTMLElement} element Element to hide loading from
     */
    hideLoading(element) {
        // Restore original content
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
            delete element.dataset.originalContent;
        }
        
        element.classList.remove('is-loading');
    }
};

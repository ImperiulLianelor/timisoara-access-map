/**
 * Timisoara Accessibility Map
 * Accessibility filters functionality
 */

class AccessibilityFilters {
    constructor(options = {}) {
        // Default options
        this.options = {
            filterButtonSelector: '.filter-btn',
            typeFilterSelector: '.type-filter',
            locationTypesContainer: '.type-filters',
            storageKey: 'accessibility_filters',
            ...options
        };
        
        // Initialize filters state
        this.filters = {
            wheelchair: false,
            visual: false,
            hearing: false,
            cognitive: false,
            locationTypes: []
        };
        
        // Map instance reference
        this.map = window.map;
        
        // Initialize filters
        this.initFilters();
    }
    
    /**
     * Initialize the accessibility filters
     */
    initFilters() {
        // Load saved filters from localStorage
        this.loadSavedFilters();
        
        // Initialize filter buttons
        const filterButtons = document.querySelectorAll(this.options.filterButtonSelector);
        filterButtons.forEach(button => {
            // Set initial state
            const filterType = button.dataset.filter;
            if (this.filters[filterType]) {
                button.classList.add('active');
                button.setAttribute('aria-pressed', 'true');
            }
            
            // Add click event handler
            button.addEventListener('click', () => {
                this.toggleFilterButton(button);
            });
            
            // Add keyboard handler for accessibility
            button.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleFilterButton(button);
                }
            });
        });
        
        // Initialize location type filters
        const typeFilters = document.querySelectorAll(this.options.typeFilterSelector);
        typeFilters.forEach(checkbox => {
            // Set initial state
            const locationType = checkbox.dataset.type;
            if (this.filters.locationTypes.includes(locationType)) {
                checkbox.checked = true;
                checkbox.closest('.checkbox-label').classList.add('active');
            }
            
            // Add change event handler
            checkbox.addEventListener('change', () => {
                this.toggleTypeFilter(checkbox);
            });
        });
        
        // Apply initial filters if any
        if (this.hasActiveFilters()) {
            this.applyFilters();
        }
    }
    
    /**
     * Toggle an accessibility filter button
     * @param {HTMLElement} button The filter button
     */
    toggleFilterButton(button) {
        const filterType = button.dataset.filter;
        
        // Toggle state
        button.classList.toggle('active');
        const isActive = button.classList.contains('active');
        
        // Update accessibility attributes
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        
        // Update filter state
        this.filters[filterType] = isActive;
        
        // Apply filters
        this.applyFilters();
        
        // Save to localStorage
        this.saveFilters();
        
        // Announce filter change for screen readers
        this.announceFilterChange(filterType, isActive);
    }
    
    /**
     * Toggle a location type filter
     * @param {HTMLElement} checkbox The type filter checkbox
     */
    toggleTypeFilter(checkbox) {
        const locationType = checkbox.dataset.type;
        const isChecked = checkbox.checked;
        
        // Update checkbox label
        const label = checkbox.closest('.checkbox-label');
        if (label) {
            if (isChecked) {
                label.classList.add('active');
            } else {
                label.classList.remove('active');
            }
        }
        
        // Update filters state
        if (isChecked) {
            if (!this.filters.locationTypes.includes(locationType)) {
                this.filters.locationTypes.push(locationType);
            }
        } else {
            this.filters.locationTypes = this.filters.locationTypes.filter(
                type => type !== locationType
            );
        }
        
        // Apply filters
        this.applyFilters();
        
        // Save to localStorage
        this.saveFilters();
        
        // Announce filter change for screen readers
        this.announceTypeFilterChange(locationType, isChecked);
    }
    
    /**
     * Apply current filters to the map
     */
    applyFilters() {
        if (this.map && typeof this.map.applyFilters === 'function') {
            this.map.applyFilters(this.filters);
        } else {
            console.error('Map instance not found or applyFilters method not available');
        }
    }
    
    /**
     * Check if any filters are active
     * @returns {boolean} True if at least one filter is active
     */
    hasActiveFilters() {
        return (
            this.filters.wheelchair || 
            this.filters.visual || 
            this.filters.hearing || 
            this.filters.cognitive || 
            this.filters.locationTypes.length > 0
        );
    }
    
    /**
     * Reset all filters to their default state
     */
    resetFilters() {
        // Reset filters state
        this.filters = {
            wheelchair: false,
            visual: false,
            hearing: false,
            cognitive: false,
            locationTypes: []
        };
        
        // Update UI
        const filterButtons = document.querySelectorAll(this.options.filterButtonSelector);
        filterButtons.forEach(button => {
            button.classList.remove('active');
            button.setAttribute('aria-pressed', 'false');
        });
        
        const typeFilters = document.querySelectorAll(this.options.typeFilterSelector);
        typeFilters.forEach(checkbox => {
            checkbox.checked = false;
            const label = checkbox.closest('.checkbox-label');
            if (label) {
                label.classList.remove('active');
            }
        });
        
        // Apply updated filters
        this.applyFilters();
        
        // Save changes
        this.saveFilters();
        
        // Announce reset for screen readers
        this.announceReset();
    }
    
    /**
     * Save current filters to localStorage
     */
    saveFilters() {
        try {
            localStorage.setItem(this.options.storageKey, JSON.stringify(this.filters));
        } catch (e) {
            console.warn('Could not save filters to localStorage:', e);
        }
    }
    
    /**
     * Load saved filters from localStorage
     */
    loadSavedFilters() {
        try {
            const savedFilters = localStorage.getItem(this.options.storageKey);
            if (savedFilters) {
                this.filters = JSON.parse(savedFilters);
            }
        } catch (e) {
            console.warn('Could not load filters from localStorage:', e);
        }
    }
    
    /**
     * Set filters based on user preferences
     * @param {Object} preferences User accessibility preferences
     */
    setFromUserPreferences(preferences) {
        if (!preferences) return;
        
        // Update filters based on preferences
        if (preferences.needs_wheelchair) {
            this.filters.wheelchair = true;
        }
        
        if (preferences.needs_visual_assistance) {
            this.filters.visual = true;
        }
        
        if (preferences.needs_hearing_assistance) {
            this.filters.hearing = true;
        }
        
        if (preferences.needs_cognitive_assistance) {
            this.filters.cognitive = true;
        }
        
        // Update UI
        const filterButtons = document.querySelectorAll(this.options.filterButtonSelector);
        filterButtons.forEach(button => {
            const filterType = button.dataset.filter;
            if (this.filters[filterType]) {
                button.classList.add('active');
                button.setAttribute('aria-pressed', 'true');
            }
        });
        
        // Apply updated filters
        this.applyFilters();
        
        // Save changes
        this.saveFilters();
    }
    
    /**
     * Announce filter change for screen readers
     * @param {string} filterType Type of filter changed
     * @param {boolean} isActive Whether the filter is active
     */
    announceFilterChange(filterType, isActive) {
        const statusElement = this.getAnnouncementElement();
        const filterNames = {
            wheelchair: 'Wheelchair accessibility',
            visual: 'Visual accessibility',
            hearing: 'Hearing accessibility',
            cognitive: 'Cognitive accessibility'
        };
        
        const message = `${filterNames[filterType]} filter ${isActive ? 'enabled' : 'disabled'}`;
        statusElement.textContent = message;
    }
    
    /**
     * Announce type filter change for screen readers
     * @param {string} locationType Type of location filter changed
     * @param {boolean} isChecked Whether the filter is checked
     */
    announceTypeFilterChange(locationType, isChecked) {
        const statusElement = this.getAnnouncementElement();
        const message = `${locationType} filter ${isChecked ? 'enabled' : 'disabled'}`;
        statusElement.textContent = message;
    }
    
    /**
     * Announce filter reset for screen readers
     */
    announceReset() {
        const statusElement = this.getAnnouncementElement();
        statusElement.textContent = 'All filters have been reset';
    }
    
    /**
     * Get or create the announcement element for screen readers
     * @returns {HTMLElement} The announcement element
     */
    getAnnouncementElement() {
        let statusElement = document.getElementById('filter-status-announcer');
        
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = 'filter-status-announcer';
            statusElement.setAttribute('role', 'status');
            statusElement.setAttribute('aria-live', 'polite');
            statusElement.className = 'sr-only';
            document.body.appendChild(statusElement);
        }
        
        return statusElement;
    }
}

// Initialize filters on page load
document.addEventListener('DOMContentLoaded', () => {
    // We need to wait for the map to be initialized first
    const checkMapInterval = setInterval(() => {
        if (window.map) {
            clearInterval(checkMapInterval);
            window.accessibilityFilters = new AccessibilityFilters();
            
            // Add reset button if needed
            const filterSection = document.querySelector('.filter-section');
            if (filterSection && !document.querySelector('.reset-filters-btn')) {
                const resetButton = document.createElement('button');
                resetButton.className = 'btn secondary reset-filters-btn';
                resetButton.textContent = 'Reset Filters';
                resetButton.addEventListener('click', () => {
                    window.accessibilityFilters.resetFilters();
                });
                
                filterSection.appendChild(resetButton);
            }
        }
    }, 100);
    
    // Stop checking after 5 seconds to prevent infinite loop
    setTimeout(() => {
        clearInterval(checkMapInterval);
    }, 5000);
});

// Export the class for direct usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AccessibilityFilters;
}
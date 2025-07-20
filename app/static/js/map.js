/**
 * Timisoara Accessibility Map
 * Main map functionality for the accessibility web app
 */

 class AccessibilityMap {
    constructor(mapElementId, options = {}) {
        // Default options
        this.options = {
            center: [45.7557, 21.2300],
            zoom: 13,
            minZoom: 12,
            maxZoom: 18,
            bounds: [[45.70, 21.10], [45.80, 21.35]],
            ...options
        };

        this.markers = [];
        this.currentFilters = {
            wheelchair: false,
            visual: false,
            hearing: false,
            cognitive: false,
            locationTypes: []
        };

        // Initialize map
        this.initMap(mapElementId);
        
        // Initialize search functionality
        this.initSearch();
        
        // Get user's location if available
        this.getUserLocation();
    }

    /**
     * Initialize the map with OpenStreetMap tiles
     */
    initMap(elementId) {
        // Create map instance
        this.map = L.map(elementId, {
            center: this.options.center,
            zoom: this.options.zoom,
            minZoom: this.options.minZoom,
            maxZoom: this.options.maxZoom,
            maxBounds: this.options.bounds,
            zoomControl: false
        });

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Add zoom control to top right
        L.control.zoom({
            position: 'topright'
        }).addTo(this.map);

        // Add scale
        L.control.scale({
            imperial: false,
            position: 'bottomright'
        }).addTo(this.map);

        // Create layers for different marker categories
        this.layers = {
            approved: L.layerGroup().addTo(this.map),
            pending: L.layerGroup().addTo(this.map),
            selected: L.layerGroup().addTo(this.map)
        };

        // Add central selection marker
        this.selectionMarker = L.marker(this.options.center, {
            icon: L.divIcon({
                className: 'selection-marker',
                html: '<div class="pin-dot"></div><div class="pin-pulse"></div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            zIndexOffset: 1000,
            interactive: false
        }).addTo(this.layers.selected);

        // Update marker position when the map is moved
        this.map.on('move', () => {
            this.selectionMarker.setLatLng(this.map.getCenter());
        });

        // This click handler is now ONLY for adding new locations
        this.map.on('click', (e) => {
            if (document.getElementById('add-location-btn')) {
                this.map.setView(e.latlng);
                this.showAddLocationForm(e.latlng);
            }
        });
    }
    
    /**
     * Initialize search functionality
     */
    initSearch() {
        const searchInput = document.getElementById('location-search');
        if (!searchInput) return;
        
        searchInput.addEventListener('input', this.debounce(() => {
            const query = searchInput.value.trim();
            if (query.length < 3) return;
            
            this.searchLocations(query);
        }, 300));
    }
    
    /**
     * Search for locations using the API
     */
    searchLocations(query) {
        const searchResults = document.getElementById('search-results');
        if (!searchResults) return;
        
        fetch(`/api/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                searchResults.innerHTML = '';
                
                if (data.results.length === 0) {
                    searchResults.innerHTML = '<div class="no-results">No results found</div>';
                    return;
                }
                
                data.results.forEach(result => {
                    const item = document.createElement('div');
                    item.className = 'search-result-item';
                    item.innerHTML = `
                        <strong>${result.name}</strong>
                        <span>${result.address || ''}</span>
                    `;
                    
                    item.addEventListener('click', () => {
                        this.map.setView([result.lat, result.lng], 17);
                        this.showLocationDetails(result.id);
                        searchResults.innerHTML = '';
                    });
                    
                    searchResults.appendChild(item);
                });
                
                searchResults.style.display = 'block';
            })
            .catch(error => {
                console.error('Search error:', error);
                searchResults.innerHTML = '<div class="error">Search error. Please try again.</div>';
            });
    }

    /**
     * Load location markers from the API
     */
    loadLocations() {
        // Clear existing markers
        this.layers.approved.clearLayers();
        this.layers.pending.clearLayers();

        // Build filter query string
        const filterParams = new URLSearchParams();
        
        if (this.currentFilters.wheelchair) filterParams.append('wheelchair', 'true');
        if (this.currentFilters.visual) filterParams.append('visual', 'true');
        if (this.currentFilters.hearing) filterParams.append('hearing', 'true');
        if (this.currentFilters.cognitive) filterParams.append('cognitive', 'true');
        
        this.currentFilters.locationTypes.forEach(type => {
            filterParams.append('type', type);
        });

        // Fetch locations from API
        fetch(`/api/locations?${filterParams.toString()}`)
            .then(response => response.json())
            .then(data => {
                this.addMarkersToMap(data.locations);
            })
            .catch(error => {
                console.error('Error loading locations:', error);
                this.showNotification('Error loading locations. Please try again.', 'error');
            });
    }

    /**
     * Add markers to the map
     */
    addMarkersToMap(locations) {
        locations.forEach(location => {
            const marker = this.createLocationMarker(location);
            
            if (location.is_approved) {
                marker.addTo(this.layers.approved);
            } else {
                marker.addTo(this.layers.pending);
            }
            
            this.markers.push(marker);
        });
    }

    /**
     * Create a marker for a location
     */
    createLocationMarker(location) {
        const iconClass = this.getMarkerIconClass(location);
        
        const marker = L.marker([location.lat, location.lng], {
            icon: L.divIcon({
                className: `location-marker ${iconClass}`,
                html: `<div class="marker-icon" aria-label="${location.name}"></div>`,
                iconSize: [32, 32],
                iconAnchor: [16, 32],
                popupAnchor: [0, -32]
            })
        });
        
        // Bind the popup content
        marker.bindPopup(this.createPopupContent(location));

        // **THE FIX:** Add a listener for when this popup opens
        marker.on('popupopen', (e) => {
            const popupElement = e.popup.getElement();
            const btn = popupElement.querySelector('.details-btn');
            if (btn) {
                // This is crucial to prevent the map from handling the click and closing the popup
                L.DomEvent.on(btn, 'click', L.DomEvent.stop);
                
                // Now, add our own click listener to the button
                L.DomEvent.on(btn, 'click', () => {
                    const locationId = btn.dataset.locationId;
                    if (locationId) {
                        this.showLocationDetails(parseInt(locationId, 10));
                    }
                });
            }
        });
        
        return marker;
    }

    /**
     * Get the appropriate marker icon class based on accessibility features
     */
    
     getMarkerIconClass(location) {
        const classes = ['marker'];
        
        const isWheelchair = location.has_ramp || location.has_accessible_entrance || location.has_accessible_parking;
        const isVisual = location.has_braille || location.has_audio_guidance;
        const isCognitive = location.has_staff_assistance;
        const isHearing = location.has_audio_guidance; // Note: You might want a different flag for this
        
        // Check for the special "fully accessible" case first
        if (isWheelchair && isVisual && isCognitive && isHearing) {
            classes.push('fully-accessible');
        } else {
            // Otherwise, add individual classes
            if (isWheelchair) classes.push('wheelchair');
            if (isVisual) classes.push('visual');
            if (isCognitive) classes.push('cognitive');
            if (isHearing) classes.push('hearing');
        }
        
        if (!location.is_approved) {
            classes.push('pending');
        }
        
        return classes.join(' ');
    }

    /**
     * Create popup content for a location marker
     */
    createPopupContent(location) {
        const content = `
            <div class="marker-popup">
                <h3>${location.name}</h3>
                <p>${location.address || ''}</p>
                <div class="accessibility-icons">
                    ${location.has_ramp ? '<span class="icon wheelchair" title="Wheelchair accessible"></span>' : ''}
                    ${location.has_accessible_wc ? '<span class="icon wc" title="Accessible toilet"></span>' : ''}
                    ${location.has_braille ? '<span class="icon braille" title="Braille available"></span>' : ''}
                </div>
                <button class="details-btn" data-location-id="${location.id}">View Details</button>
            </div>
        `;
        return content;
    }

    /**
     * Show location details in the sidebar
     */
    showLocationDetails(locationId) {
        fetch(`/api/locations/${locationId}`)
            .then(response => response.json())
            .then(data => {
                const sidebar = document.getElementById('location-details');
                if (!sidebar) return;
                
                sidebar.innerHTML = this.createLocationDetailsHTML(data.location);
                sidebar.classList.add('open');
                
                // Add event listener to close button
                const closeBtn = document.getElementById('close-details');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        sidebar.classList.remove('open');
                    });
                }
            })
            .catch(error => {
                console.error('Error loading location details:', error);
                this.showNotification('Error loading location details. Please try again.', 'error');
            });
    }

    /**
     * Create HTML for location details sidebar
     */
    createLocationDetailsHTML(location) {
        const accessibilityFeatures = [
            { name: 'Wheelchair ramp', value: location.has_ramp, icon: 'ramp' },
            { name: 'Accessible toilet', value: location.has_accessible_wc, icon: 'wc' },
            { name: 'Accessible parking', value: location.has_accessible_parking, icon: 'parking' },
            { name: 'Accessible entrance', value: location.has_accessible_entrance, icon: 'entrance' },
            { name: 'Braille', value: location.has_braille, icon: 'braille' },
            { name: 'Audio guidance', value: location.has_audio_guidance, icon: 'audio' },
            { name: 'Staff assistance', value: location.has_staff_assistance, icon: 'staff' }
        ];

        const featuresList = accessibilityFeatures
            .map(feature => `
                <li class="${feature.value ? 'available' : 'unavailable'}">
                    <span class="icon ${feature.icon}"></span>
                    ${feature.name}: ${feature.value ? 'Yes' : 'No'}
                </li>
            `)
            .join('');

        // Get photos if available
        const photosHTML = location.photos && location.photos.length > 0 
            ? `
                <div class="location-photos">
                    ${location.photos.map(photo => `
                        <img src="/static/uploads/${photo.filename}" alt="${photo.description || location.name}" />
                    `).join('')}
                </div>
            `
            : '<p>No photos available</p>';

        return `
            <div class="location-details-container">
                <button id="close-details" class="close-btn" aria-label="Close details">×</button>
                <h2>${location.name}</h2>
                <p class="address">${location.address || 'No address provided'}</p>
                
                <div class="details-section">
                    <h3>Accessibility Features</h3>
                    <ul class="features-list">
                        ${featuresList}
                    </ul>
                </div>
                
                <div class="details-section">
                    <h3>Description</h3>
                    <p>${location.description || 'No description provided'}</p>
                </div>
                
                <div class="details-section">
                    <h3>Photos</h3>
                    ${photosHTML}
                </div>
                
                <div class="details-section">
                    <h3>Reviews</h3>
                    <div id="reviews-container">
                        ${this.renderReviews(location.reviews || [])}
                    </div>
                    <button id="add-review-btn" class="btn secondary">Add Review</button>
                </div>
                
                <div class="actions">
                    <button id="directions-btn" class="btn primary">Get Directions</button>
                </div>
            </div>
        `;
    }

    /**
     * Render location reviews
     */
    renderReviews(reviews) {
        if (reviews.length === 0) {
            return '<p>No reviews yet. Be the first to review this location!</p>';
        }

        return reviews.map(review => `
            <div class="review">
                <div class="review-header">
                    <span class="review-author">${review.author_name}</span>
                    <span class="review-rating">
                        ${this.generateStarRating(review.rating)}
                    </span>
                    <span class="review-date">${new Date(review.created_at).toLocaleDateString()}</span>
                </div>
                <div class="review-content">
                    ${review.content}
                </div>
            </div>
        `).join('');
    }

    /**
     * Generate HTML for star rating
     */
    generateStarRating(rating) {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= rating) {
                stars += '<span class="star filled">★</span>';
            } else {
                stars += '<span class="star">☆</span>';
            }
        }
        return stars;
    }

    /**
     * Show the add location form
     */
    showAddLocationForm(latlng) {
        const sidebar = document.getElementById('add-location-form');
        if (!sidebar) return;
        
        // Set the lat/lng values in the form
        const latInput = document.getElementById('lat');
        const lngInput = document.getElementById('lng');
        
        if (latInput && lngInput) {
            latInput.value = latlng.lat.toFixed(6);
            lngInput.value = latlng.lng.toFixed(6);
        }
        
        sidebar.classList.add('open');
    }

    /**
     * Apply accessibility filters
     */
    applyFilters(filters) {
        this.currentFilters = {...filters};
        this.loadLocations();
    }

    /**
     * Try to get user's current location
     */
    getUserLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                // Success callback
                (position) => {
                    const userLat = position.coords.latitude;
                    const userLng = position.coords.longitude;
                    
                    // Check if user is within Timisoara bounds
                    if (userLat >= 45.70 && userLat <= 45.80 && 
                        userLng >= 21.10 && userLng <= 21.35) {
                        this.map.setView([userLat, userLng], 16);
                    }
                },
                // Error callback
                (error) => {
                    console.log('Geolocation error:', error);
                },
                // Options
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        }
    }

    /**
     * Show notification message
     */
    showNotification(message, type = 'info') {
        const notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="message">${message}</span>
            <button class="close-notification">×</button>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Add close button functionality
        const closeBtn = notification.querySelector('.close-notification');
        closeBtn.addEventListener('click', () => {
            notification.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 500);
        }, 5000);
    }

    /**
     * Debounce function for search input
     */
    debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func.apply(context, args);
            }, wait);
        };
    }
}

// Initialize map when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if map container exists
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;
    
    // Create global map instance
    window.map = new AccessibilityMap('map');
    
    // Load initial locations
    window.map.loadLocations();
    
    // Initialize filter buttons
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            button.classList.toggle('active');
            
            // Get active filters
            const activeFilters = {
                wheelchair: document.querySelector('.filter-btn[data-filter="wheelchair"]').classList.contains('active'),
                visual: document.querySelector('.filter-btn[data-filter="visual"]').classList.contains('active'),
                hearing: document.querySelector('.filter-btn[data-filter="hearing"]').classList.contains('active'),
                cognitive: document.querySelector('.filter-btn[data-filter="cognitive"]').classList.contains('active'),
                locationTypes: Array.from(document.querySelectorAll('.type-filter.active')).map(el => el.dataset.type)
            };
            
            // Apply filters
            window.map.applyFilters(activeFilters);
        });
    });
});
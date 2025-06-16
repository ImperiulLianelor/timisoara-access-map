/**
 * Timisoara Accessibility Map
 * Form validation functionality
 */

class FormValidator {
    constructor(formElement, options = {}) {
        // Store the form element
        this.form = formElement;
        
        // Default options
        this.options = {
            errorClass: 'error-message',
            errorContainer: 'div',
            highlightClass: 'has-error',
            successClass: 'is-valid',
            validateOnInput: true,
            validateOnBlur: true,
            ...options
        };
        
        // Initialize validation rules - add more as needed
        this.validationRules = {
            required: {
                validator: (value) => value.trim() !== '',
                message: 'This field is required.'
            },
            email: {
                validator: (value) => {
                    const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
                    return value === '' || regex.test(value);
                },
                message: 'Please enter a valid email address.'
            },
            minLength: {
                validator: (value, param) => value === '' || value.length >= param,
                message: (param) => `This field must be at least ${param} characters long.`
            },
            maxLength: {
                validator: (value, param) => value === '' || value.length <= param,
                message: (param) => `This field cannot exceed ${param} characters.`
            },
            password: {
                validator: (value) => {
                    // At least 8 chars, one uppercase, one lowercase, one digit
                    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
                    return value === '' || regex.test(value);
                },
                message: 'Password must be at least 8 characters with at least one uppercase letter, one lowercase letter, and one digit.'
            },
            numeric: {
                validator: (value) => value === '' || !isNaN(parseFloat(value)) && isFinite(value),
                message: 'Please enter a valid number.'
            },
            match: {
                validator: (value, param) => {
                    const matchField = this.form.querySelector(`[name="${param}"]`);
                    return matchField && value === matchField.value;
                },
                message: (param) => `This field must match ${param}.`
            },
            coordinates: {
                validator: (value, param) => {
                    if (value === '') return true;
                    const num = parseFloat(value);
                    if (isNaN(num)) return false;
                    
                    // Check if within Timisoara bounds
                    if (param === 'lat') {
                        return num >= 45.70 && num <= 45.80;
                    } else if (param === 'lng') {
                        return num >= 21.10 && num <= 21.35;
                    }
                    return true;
                },
                message: (param) => `Please enter valid ${param === 'lat' ? 'latitude' : 'longitude'} within Timisoara.`
            }
        };
        
        // Initialize the validator
        this.initValidator();
    }
    
    /**
     * Initialize the form validator
     */
    initValidator() {
        // Add submit event listener
        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                // Focus on the first invalid field
                const firstInvalid = this.form.querySelector(`.${this.options.highlightClass} input, .${this.options.highlightClass} textarea, .${this.options.highlightClass} select`);
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });
        
        // Add input and blur event listeners if needed
        if (this.options.validateOnInput || this.options.validateOnBlur) {
            const inputs = this.form.querySelectorAll('input, textarea, select');
            
            inputs.forEach(input => {
                if (this.options.validateOnInput) {
                    input.addEventListener('input', () => {
                        this.validateField(input);
                    });
                }
                
                if (this.options.validateOnBlur) {
                    input.addEventListener('blur', () => {
                        this.validateField(input);
                    });
                }
            });
        }
    }
    
    /**
     * Validate the entire form
     * @returns {boolean} True if the form is valid, false otherwise
     */
    validateForm() {
        let isValid = true;
        const inputs = this.form.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            // Skip submit buttons and elements with no-validate class
            if (input.type === 'submit' || input.classList.contains('no-validate')) {
                return;
            }
            
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    /**
     * Validate a single field
     * @param {HTMLElement} field The input field to validate
     * @returns {boolean} True if the field is valid, false otherwise
     */
    validateField(field) {
        // Clear previous validation
        this.clearFieldValidation(field);
        
        // Get field value
        const value = field.type === 'checkbox' ? field.checked.toString() : field.value;
        
        // Get validation rules from data attributes
        const validations = this.getFieldValidations(field);
        
        // Check each validation rule
        for (const validation of validations) {
            const rule = this.validationRules[validation.rule];
            if (!rule) continue;
            
            const isValid = rule.validator(value, validation.param);
            
            if (!isValid) {
                // Field is invalid, show error
                let message = typeof rule.message === 'function' 
                    ? rule.message(validation.param)
                    : rule.message;
                
                // Check for custom error message in data attribute
                const customMessage = field.dataset[`${validation.rule}Message`];
                if (customMessage) {
                    message = customMessage;
                }
                
                this.showFieldError(field, message);
                return false;
            }
        }
        
        // If we get here, field is valid
        this.showFieldSuccess(field);
        return true;
    }
    
    /**
     * Get validation rules from field data attributes
     * @param {HTMLElement} field The input field
     * @returns {Array} Array of validation rule objects
     */
    getFieldValidations(field) {
        const validations = [];
        
        // Check if required
        if (field.hasAttribute('required') || field.dataset.required === 'true') {
            validations.push({ rule: 'required' });
        }
        
        // Check type-specific validations
        if (field.type === 'email') {
            validations.push({ rule: 'email' });
        }
        
        if (field.dataset.type === 'password' || field.type === 'password') {
            validations.push({ rule: 'password' });
        }
        
        if (field.dataset.type === 'numeric' || field.type === 'number') {
            validations.push({ rule: 'numeric' });
        }
        
        // Check min length
        if (field.minLength > 0) {
            validations.push({ rule: 'minLength', param: field.minLength });
        }
        
        // Check max length
        if (field.maxLength > 0 && field.maxLength < 1000) { // Ignore unrealistic maxlength
            validations.push({ rule: 'maxLength', param: field.maxLength });
        }
        
        // Check for match validation (e.g., password confirmation)
        if (field.dataset.match) {
            validations.push({ rule: 'match', param: field.dataset.match });
        }
        
        // Check for coordinate validation
        if (field.name === 'lat' || field.dataset.type === 'lat') {
            validations.push({ rule: 'coordinates', param: 'lat' });
        }
        
        if (field.name === 'lng' || field.dataset.type === 'lng') {
            validations.push({ rule: 'coordinates', param: 'lng' });
        }
        
        return validations;
    }
    
    /**
     * Show error message for a field
     * @param {HTMLElement} field The field with an error
     * @param {string} message The error message to display
     */
    showFieldError(field, message) {
        // Find or create the container for the field
        const container = this.getFieldContainer(field);
        
        // Add error class to the container
        container.classList.add(this.options.highlightClass);
        container.classList.remove(this.options.successClass);
        
        // Create error message element
        const errorElement = document.createElement(this.options.errorContainer);
        errorElement.className = this.options.errorClass;
        errorElement.textContent = message;
        
        // Make it accessible
        errorElement.setAttribute('aria-live', 'polite');
        
        // Add error ID and connect it to the input with aria-describedby
        const errorId = `error-${field.name || Math.random().toString(36).substring(2, 9)}`;
        errorElement.id = errorId;
        
        // Update input's aria attributes
        field.setAttribute('aria-invalid', 'true');
        
        // Append aria-describedby if it doesn't exist
        if (!field.getAttribute('aria-describedby')) {
            field.setAttribute('aria-describedby', errorId);
        } else {
            const describedBy = field.getAttribute('aria-describedby');
            if (!describedBy.includes(errorId)) {
                field.setAttribute('aria-describedby', `${describedBy} ${errorId}`);
            }
        }
        
        // Append error element to container
        container.appendChild(errorElement);
    }
    
    /**
     * Show success state for a field
     * @param {HTMLElement} field The valid field
     */
    showFieldSuccess(field) {
        // Find the container for the field
        const container = this.getFieldContainer(field);
        
        // Add success class to the container
        container.classList.add(this.options.successClass);
        container.classList.remove(this.options.highlightClass);
        
        // Update input's aria attribute
        field.setAttribute('aria-invalid', 'false');
    }
    
    /**
     * Clear validation state for a field
     * @param {HTMLElement} field The field to clear validation for
     */
    clearFieldValidation(field) {
        // Find the container for the field
        const container = this.getFieldContainer(field);
        
        // Remove validation classes
        container.classList.remove(this.options.highlightClass, this.options.successClass);
        
        // Remove error messages
        const errorElements = container.querySelectorAll(`.${this.options.errorClass}`);
        errorElements.forEach(element => {
            element.remove();
        });
        
        // Reset aria attributes
        field.removeAttribute('aria-invalid');
    }
    
    /**
     * Get the container element for a field
     * @param {HTMLElement} field The input field
     * @returns {HTMLElement} The container element
     */
    getFieldContainer(field) {
        // Look for the closest parent form-group
        let container = field.closest('.form-group');
        
        // If not found, look for parent div, label, or create a wrapper
        if (!container) {
            container = field.parentElement;
            
            // If still not a proper container, create a wrapper
            if (container === this.form) {
                const wrapper = document.createElement('div');
                wrapper.className = 'form-group';
                
                // Replace the field with the wrapper
                field.parentElement.replaceChild(wrapper, field);
                wrapper.appendChild(field);
                
                container = wrapper;
            }
        }
        
        return container;
    }
}

// Initialize all forms with validation on page load
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        // Get custom options if available
        let options = {};
        if (form.dataset.validationOptions) {
            try {
                options = JSON.parse(form.dataset.validationOptions);
            } catch (e) {
                console.error('Invalid validation options:', e);
            }
        }
        
        // Create validator for the form
        new FormValidator(form, options);
    });
    
    // Special handling for the add location form
    const addLocationForm = document.getElementById('add-location-form');
    if (addLocationForm) {
        const form = addLocationForm.querySelector('form');
        if (form) {
            form.setAttribute('data-validate', 'true');
            new FormValidator(form);
        }
    }
});

// Export the FormValidator class for direct usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormValidator;
}
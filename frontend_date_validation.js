// Frontend Date Validation and Display Functions
// Add this to your templates to handle invalid dates gracefully

/**
 * Format event date with fallback for invalid dates
 * @param {string} dateString - The date string to format
 * @returns {string} - Formatted date or "Date TBD" for invalid dates
 */
function formatEventDate(dateString) {
    if (!dateString || dateString === 'Invalid Date' || dateString === '' || dateString === null) {
        return '<span class="text-orange-600 font-medium">Date TBD</span>';
    }
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return '<span class="text-orange-600 font-medium">Date TBD</span>';
        }
        
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (error) {
        console.warn('Error formatting date:', dateString, error);
        return '<span class="text-orange-600 font-medium">Date TBD</span>';
    }
}

/**
 * Format event time with fallback for invalid dates
 * @param {string} dateString - The date string to format
 * @returns {string} - Formatted time or empty string for invalid dates
 */
function formatEventTime(dateString) {
    if (!dateString || dateString === 'Invalid Date' || dateString === '' || dateString === null) {
        return '';
    }
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return '';
        }
        
        const time = date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        
        // Only show time if it's not midnight
        if (time === '12:00 AM') {
            return '';
        }
        
        return time;
    } catch (error) {
        console.warn('Error formatting time:', dateString, error);
        return '';
    }
}

/**
 * Format event date and time together
 * @param {string} dateString - The date string to format
 * @returns {string} - Formatted date and time
 */
function formatEventDateTime(dateString) {
    const date = formatEventDate(dateString);
    const time = formatEventTime(dateString);
    
    if (time) {
        return `${date} at ${time}`;
    }
    
    return date;
}

/**
 * Check if a date string is valid
 * @param {string} dateString - The date string to check
 * @returns {boolean} - True if valid, false otherwise
 */
function isValidDate(dateString) {
    if (!dateString || dateString === 'Invalid Date' || dateString === '' || dateString === null) {
        return false;
    }
    
    try {
        const date = new Date(dateString);
        return !isNaN(date.getTime());
    } catch (error) {
        return false;
    }
}

/**
 * Get relative time (e.g., "2 days ago", "in 3 hours")
 * @param {string} dateString - The date string
 * @returns {string} - Relative time string
 */
function getRelativeTime(dateString) {
    if (!isValidDate(dateString)) {
        return 'Date TBD';
    }
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = date.getTime() - now.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        
        if (diffMs < 0) {
            // Past date
            if (diffDays < -1) {
                return `${Math.abs(diffDays)} days ago`;
            } else if (diffHours < -1) {
                return `${Math.abs(diffHours)} hours ago`;
            } else {
                return 'Just now';
            }
        } else {
            // Future date
            if (diffDays > 1) {
                return `in ${diffDays} days`;
            } else if (diffHours > 1) {
                return `in ${diffHours} hours`;
            } else if (diffMinutes > 1) {
                return `in ${diffMinutes} minutes`;
            } else {
                return 'Soon';
            }
        }
    } catch (error) {
        console.warn('Error calculating relative time:', dateString, error);
        return 'Date TBD';
    }
}

/**
 * Format date for display in event cards
 * @param {string} dateString - The date string to format
 * @returns {object} - Object with date, time, and relative time
 */
function formatEventCardDate(dateString) {
    return {
        date: formatEventDate(dateString),
        time: formatEventTime(dateString),
        relative: getRelativeTime(dateString),
        isValid: isValidDate(dateString)
    };
}

// Alpine.js compatible functions
function alpineFormatDate(dateString) {
    return formatEventDate(dateString);
}

function alpineFormatTime(dateString) {
    return formatEventTime(dateString);
}

function alpineFormatDateTime(dateString) {
    return formatEventDateTime(dateString);
}

function alpineIsValidDate(dateString) {
    return isValidDate(dateString);
}

function alpineGetRelativeTime(dateString) {
    return getRelativeTime(dateString);
}

// Make functions available globally
window.formatEventDate = formatEventDate;
window.formatEventTime = formatEventTime;
window.formatEventDateTime = formatEventDateTime;
window.isValidDate = isValidDate;
window.getRelativeTime = getRelativeTime;
window.formatEventCardDate = formatEventCardDate;
window.alpineFormatDate = alpineFormatDate;
window.alpineFormatTime = alpineFormatTime;
window.alpineFormatDateTime = alpineFormatDateTime;
window.alpineIsValidDate = alpineIsValidDate;
window.alpineGetRelativeTime = alpineGetRelativeTime;

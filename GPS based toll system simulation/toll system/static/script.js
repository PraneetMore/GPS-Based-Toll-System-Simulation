/**
 * GPS Based Toll Collection System - Frontend Script
 * Handles all client-side interactions and API calls
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components when DOM is loaded
    initSimulationControls();
    initMapView();
    initPaymentHandlers();
    initFormValidations();
    initAdminDashboard();
    setupEventListeners();
    
    // Check for authentication status
    checkAuthStatus();
});

/**
 * Global Configuration
 */
const config = {
    apiBaseUrl: window.location.origin,
    map: null,
    mapMarkers: [],
    simulationInterval: null,
    currentVehicleId: null
};

/**
 * Initialize Simulation Controls
 */
function initSimulationControls() {
    const startBtn = document.getElementById('start-simulation');
    const cancelBtn = document.getElementById('cancel-simulation');
    const statusDisplay = document.getElementById('simulation-status');
    
    if (startBtn) {
        startBtn.addEventListener('click', startVehicleSimulation);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelSimulation);
    }
}

/**
 * Initialize Map View
 */
function initMapView() {
    const mapElement = document.getElementById('map');
    
    if (mapElement) {
        // Initialize Leaflet map
        config.map = L.map('map').setView([18.5204, 73.8567], 12); // Default to Pune coordinates
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(config.map);
        
        // Fit bounds button functionality
        const fitBoundsBtn = document.getElementById('fit-bounds');
        if (fitBoundsBtn) {
            fitBoundsBtn.addEventListener('click', fitMapToRoute);
        }
    }
}

// Set up CSRF token for AJAX requests
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    
    // Set up AJAX to include CSRF token
    if (csrfToken) {
        $.ajaxSetup({
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
    }
    
    // Or for fetch API
    if (csrfToken) {
        fetchCsrfToken = csrfToken;
    }
});

// For fetch requests
function fetchWithCsrf(url, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    options.headers = options.headers || {};
    options.headers['X-CSRFToken'] = csrfToken;
    return fetch(url, options);
}

/**
 * Initialize Payment Handlers
 */
function initPaymentHandlers() {
    const paymentForm = document.getElementById('payment-form');
    const paymentMethods = document.querySelectorAll('.payment-method');
    
    if (paymentForm) {
        paymentForm.addEventListener('submit', processPayment);
    }
    
    if (paymentMethods) {
        paymentMethods.forEach(method => {
            method.addEventListener('click', selectPaymentMethod);
        });
    }
}

/**
 * Initialize Form Validations
 */
function initFormValidations() {
    // Login form validation
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', validateLoginForm);
    }
    
    // Signup form validation
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', validateSignupForm);
    }
    
    // Feedback form validation
    const feedbackForm = document.getElementById('feedback-form');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', validateFeedbackForm);
    }
}

/**
 * Initialize Admin Dashboard
 */
function initAdminDashboard() {
    if (document.getElementById('admin-dashboard')) {
        loadAdminStats();
        setupChartJS();
    }
}

/**
 * Setup Event Listeners
 */
function setupEventListeners() {
    // Toggle password visibility
    document.querySelectorAll('.toggle-password').forEach(button => {
        button.addEventListener('click', togglePasswordVisibility);
    });
    
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logoutUser);
    }
    
    // Handle flash message dismissal
    document.querySelectorAll('.flash-close').forEach(button => {
        button.addEventListener('click', dismissFlashMessage);
    });
}

/**
 * Authentication Functions
 */
function checkAuthStatus() {
    // Check if user is logged in by trying to access a protected endpoint
    fetch(`${config.apiBaseUrl}/api/check-auth`, {
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            redirectToLogin();
        }
    })
    .catch(error => {
        console.error('Auth check failed:', error);
    });
}

function redirectToLogin() {
    window.location.href = '/login';
}

function logoutUser() {
    fetch(`${config.apiBaseUrl}/logout`, {
        method: 'POST',
        credentials: 'include'
    })
    .then(response => {
        if (response.ok) {
            window.location.href = '/login';
        }
    })
    .catch(error => {
        console.error('Logout failed:', error);
        showFlashMessage('Logout failed. Please try again.', 'error');
    });
}

/**
 * Simulation Functions
 */
function startVehicleSimulation() {
    const vehicleId = document.getElementById('vehicle-id').value;
    
    if (!vehicleId) {
        showFlashMessage('Please select a vehicle', 'error');
        return;
    }
    
    config.currentVehicleId = vehicleId;
    
    fetch(`${config.apiBaseUrl}/start_simulation`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `vehicle_id=${vehicleId}`,
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showFlashMessage(data.error, 'error');
            return;
        }
        
        showFlashMessage('Simulation started successfully', 'success');
        updateSimulationStatus();
    })
    .catch(error => {
        console.error('Error starting simulation:', error);
        showFlashMessage('Failed to start simulation', 'error');
    });
}

function updateSimulationStatus() {
    if (!config.currentVehicleId) return;
    
    config.simulationInterval = setInterval(() => {
        fetch(`${config.apiBaseUrl}/simulation_status/${config.currentVehicleId}`, {
            credentials: 'include'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'in_progress') {
                updateSimulationUI(data);
            } else if (data.status === 'completed') {
                clearInterval(config.simulationInterval);
                showFlashMessage('Simulation completed', 'success');
                updateSimulationUI(data);
            } else if (data.status === 'error') {
                clearInterval(config.simulationInterval);
                showFlashMessage(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error checking simulation status:', error);
            clearInterval(config.simulationInterval);
        });
    }, 2000);
}

function updateSimulationUI(data) {
    // Update progress bar
    const progressBar = document.getElementById('simulation-progress');
    if (progressBar) {
        progressBar.style.width = `${data.progress}%`;
        progressBar.textContent = `${data.progress}%`;
    }
    
    // Update map position
    if (config.map && data.current_position) {
        updateMapPosition(
            data.current_position.latitude, 
            data.current_position.longitude,
            data.end_plaza.latitude,
            data.end_plaza.longitude
        );
    }
    
    // Update stats display
    const statsDisplay = document.getElementById('simulation-stats');
    if (statsDisplay) {
        statsDisplay.innerHTML = `
            <div>Distance: ${data.distance} km</div>
            <div>Toll: ₹${data.toll}</div>
            <div>Fine: ₹${data.fine}</div>
        `;
    }
}

function cancelSimulation() {
    if (!config.currentVehicleId) return;
    
    fetch(`${config.apiBaseUrl}/cancel_simulation/${config.currentVehicleId}`, {
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'canceled') {
            clearInterval(config.simulationInterval);
            showFlashMessage('Simulation canceled', 'success');
        }
    })
    .catch(error => {
        console.error('Error canceling simulation:', error);
        showFlashMessage('Failed to cancel simulation', 'error');
    });
}

/**
 * Map Functions
 */
function updateMapPosition(startLat, startLng, endLat, endLng) {
    // Clear existing markers
    config.mapMarkers.forEach(marker => config.map.removeLayer(marker));
    config.mapMarkers = [];
    
    // Add start marker
    const startMarker = L.marker([startLat, startLng], {
        icon: L.divIcon({
            className: 'start-marker',
            html: '<i class="fas fa-flag fa-2x"></i>',
            iconSize: [30, 30]
        })
    }).addTo(config.map);
    startMarker.bindPopup('Start Location').openPopup();
    config.mapMarkers.push(startMarker);
    
    // Add end marker
    const endMarker = L.marker([endLat, endLng], {
        icon: L.divIcon({
            className: 'end-marker',
            html: '<i class="fas fa-flag-checkered fa-2x"></i>',
            iconSize: [30, 30]
        })
    }).addTo(config.map);
    endMarker.bindPopup('Destination').openPopup();
    config.mapMarkers.push(endMarker);
    
    // Add route line
    const routeLine = L.polyline(
        [[startLat, startLng], [endLat, endLng]],
        {color: '#3B82F6', weight: 4}
    ).addTo(config.map);
    config.mapMarkers.push(routeLine);
    
    // Fit bounds to show both points
    fitMapToRoute();
}

function fitMapToRoute() {
    if (config.mapMarkers.length >= 2) {
        const startMarker = config.mapMarkers[0];
        const endMarker = config.mapMarkers[1];
        
        if (startMarker && endMarker) {
            const bounds = L.latLngBounds(
                [startMarker.getLatLng().lat, startMarker.getLatLng().lng],
                [endMarker.getLatLng().lat, endMarker.getLatLng().lng]
            );
            config.map.fitBounds(bounds, {padding: [50, 50]});
        }
    }
}

/**
 * Payment Functions
 */
function selectPaymentMethod(event) {
    const method = event.currentTarget;
    const methodName = method.dataset.method;
    
    // Remove active class from all methods
    document.querySelectorAll('.payment-method').forEach(m => {
        m.classList.remove('active');
    });
    
    // Add active class to selected method
    method.classList.add('active');
    
    // Show corresponding form
    document.querySelectorAll('.payment-form-section').forEach(section => {
        section.style.display = 'none';
    });
    
    const formSection = document.getElementById(`${methodName}-form`);
    if (formSection) {
        formSection.style.display = 'block';
    }
}

function processPayment(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const paymentData = {};
    
    formData.forEach((value, key) => {
        paymentData[key] = value;
    });
    
    showLoading(true);
    
    fetch(`${config.apiBaseUrl}/process_payment`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(paymentData),
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        
        if (data.success) {
            showFlashMessage('Payment processed successfully', 'success');
            form.reset();
            // Redirect or update UI as needed
        } else {
            showFlashMessage(data.error || 'Payment failed', 'error');
        }
    })
    .catch(error => {
        showLoading(false);
        console.error('Payment error:', error);
        showFlashMessage('Payment processing failed', 'error');
    });
}

/**
 * Form Validation Functions
 */
function validateLoginForm(event) {
    event.preventDefault();
    const form = event.target;
    const username = form.username.value.trim();
    const password = form.password.value.trim();
    
    if (!username || !password) {
        showFlashMessage('Please fill in all fields', 'error');
        return;
    }
    
    // Additional validation if needed
    
    form.submit();
}

function validateSignupForm(event) {
    event.preventDefault();
    const form = event.target;
    const password = form.password.value;
    
    if (password.length < 8) {
        showFlashMessage('Password must be at least 8 characters', 'error');
        return;
    }
    
    // Additional validation if needed
    
    form.submit();
}

function validateFeedbackForm(event) {
    event.preventDefault();
    const form = event.target;
    const feedback = form.feedback.value.trim();
    
    if (feedback.length < 10) {
        showFlashMessage('Please provide more detailed feedback', 'error');
        return;
    }
    
    form.submit();
}

/**
 * Admin Dashboard Functions
 */
function loadAdminStats() {
    fetch(`${config.apiBaseUrl}/api/admin/stats`, {
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        updateStatsCards(data);
        updateCharts(data);
    })
    .catch(error => {
        console.error('Error loading admin stats:', error);
    });
}

function setupChartJS() {
    // Initialize charts if needed
    // This would be more specific to your charting library
}

/**
 * UI Utility Functions
 */
function showFlashMessage(message, type) {
    const flashContainer = document.getElementById('flash-messages');
    if (!flashContainer) return;
    
    const flash = document.createElement('div');
    flash.className = `flash flash-${type}`;
    flash.innerHTML = `
        <span>${message}</span>
        <button class="flash-close">&times;</button>
    `;
    
    flashContainer.appendChild(flash);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        flash.remove();
    }, 5000);
}

function dismissFlashMessage(event) {
    event.currentTarget.parentElement.remove();
}

function togglePasswordVisibility(event) {
    const button = event.currentTarget;
    const input = button.previousElementSibling;
    
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

function showLoading(show) {
    const loader = document.getElementById('loading-overlay');
    if (loader) {
        loader.style.display = show ? 'flex' : 'none';
    }
}

/**
 * Initialize the application
 */
function initializeApp() {
    // Check if we're on a specific page and initialize accordingly
    if (document.getElementById('dashboard-page')) {
        initDashboard();
    } else if (document.getElementById('map-page')) {
        initMapPage();
    } else if (document.getElementById('payment-page')) {
        initPaymentPage();
    }
    
    // Common initializations
    setupEventListeners();
}

// Start the application
initializeApp();
// TripBot Chat Interface JavaScript

class TripBotChat {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.progressSteps = document.getElementById('progressSteps');
        this.collectedInfo = document.getElementById('collectedInfo');
        this.costBreakdownCard = document.getElementById('costBreakdownCard');
        this.costBreakdown = document.getElementById('costBreakdown');
        
        this.currentStep = 'greeting';
        this.collectedData = {};
        this.isTyping = false;
        
        this.initializeEventListeners();
        this.updateProgressSteps();
    }
    
    initializeEventListeners() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Enter key handling
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea and focus
        this.messageInput.addEventListener('input', () => {
            this.adjustInputHeight();
        });
        
        // Focus input on load
        this.messageInput.focus();
    }
    
    adjustInputHeight() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
    }
    
    async sendMessage(message) {
        if(message ==null){
            const user_message = this.messageInput.value.trim();
            if (!user_message || this.isTyping) return;
            message = user_message;
        }
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable form
        this.messageInput.value = '';
        this.adjustInputHeight();
        this.setInputDisabled(true);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Send message to backend
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-session-id': sessionStorage.getItem('sessionId') || '',
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            // After getting the response, check for and store the session ID
            const sessionId = response.headers.get('x-session-id');
            if (sessionId) {
                sessionStorage.setItem('sessionId', sessionId);
            }
            const data = await response.json();
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add bot response
            this.addMessage(data.response, 'bot');

            // If there's a follow-up question, display it
            if (data.question) {
                this.addMessage(`Question: ${data.question}`, 'bot');
            }
                      
            // Update conversation state
            this.currentStep = data.current_step;
            this.collectedData = data.collected_data || {};
            
            // Update UI
            this.updateProgressSteps();
            this.updateCollectedInfo();
            
            // Handle additional data (cost breakdown, booking confirmation)
            if (data.additional_data) {
                this.handleAdditionalData(data.additional_data);
            }
            if(data.tool_call && data.tool_call === "search_flight"){
                this.addFlightSearchWidget(data.collected_data);
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot', true);
        } finally {
            this.setInputDisabled(false);
            this.messageInput.focus();
        }
    }
    
    addMessage(content, type, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const avatarIcon = type === 'user' ? 'fa-user' : 'fa-robot';
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas ${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble ${isError ? 'alert alert-danger' : ''}">
                    ${this.formatMessage(content)}
                </div>
                <small class="message-time text-muted">${timestamp}</small>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(content) {
        // Convert URLs to links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        content = content.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        
        // Convert line breaks to HTML
        content = content.replace(/\n/g, '<br>');
        
        // Basic markdown-like formatting
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return content;
    }
    
    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.style.display = 'none';
    }
    
    setInputDisabled(disabled) {
        this.messageInput.disabled = disabled;
        this.sendButton.disabled = disabled;
        
        if (disabled) {
            this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    updateProgressSteps() {
        const steps = this.progressSteps.querySelectorAll('.step');
        const stepNames = [
            'greeting', 'name_collection', 'email_collection', 
            'destination_collection', 'date_collection', 'confirmation', 'final_confirmation'
        ];
        
        const currentIndex = stepNames.indexOf(this.currentStep);
        
        steps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            
            if (index < currentIndex) {
                step.classList.add('completed');
            } else if (index === currentIndex) {
                step.classList.add('active');
            }
        });
    }
    
    updateCollectedInfo() {
        if (Object.keys(this.collectedData).length === 0) {
            this.collectedInfo.innerHTML = '<p class="text-muted mb-0">Information will appear here as we chat...</p>';
            return;
        }
        
        const infoHtml = Object.entries(this.collectedData)
            .filter(([key, value]) => value && value.trim && value.trim() !== '')
            .map(([key, value]) => {
                const label = this.formatFieldLabel(key);
                const formattedValue = this.formatFieldValue(key, value);
                return `
                    <div class="info-item mb-2">
                        <strong>${label}:</strong>
                        <span class="ms-2">${formattedValue}</span>
                    </div>
                `;
            })
            .join('');
        
        this.collectedInfo.innerHTML = infoHtml || '<p class="text-muted mb-0">Information will appear here as we chat...</p>';
    }
    
    formatFieldLabel(key) {
        const labels = {
            'traveler_name': 'UserName',
            'email': 'Email',
            'destination': 'Destination',
            'departure_location': 'Departure',
            'departure_date': 'Departure Date',
            'return_date': 'Return Date',
            'travelers_count': 'Travelers',
            'trip_type': 'Trip Type',
            'budget': 'Budget',
            'preferences': 'Preferences'
        };
        
        return labels[key] || key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    formatFieldValue(key, value) {
        if (key === 'budget' && value) {
            return `$${value}`;
        }
        if (key === 'trip_type') {
            return value.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        if (key === 'preferences' && typeof value === 'object') {
            return value.user_input || JSON.stringify(value);
        }
        
        return value;
    }
    
    handleAdditionalData(data) {
        if (data.cost_breakdown) {
            this.displayCostBreakdown(data.cost_breakdown);
        }
        
        if (data.booking) {
            this.displayBookingConfirmation(data.booking, data.payment);
        }
    }
    
    displayCostBreakdown(costData) {
        if (costData.error) {
            this.costBreakdown.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${costData.error}
                </div>
            `;
        } else {
            this.costBreakdown.innerHTML = `
                <div class="cost-item">
                    <span><i class="fas fa-plane me-2"></i>Flights</span>
                    <span>$${costData.flight_cost?.toFixed(2) || '0.00'}</span>
                </div>
                <div class="cost-item">
                    <span><i class="fas fa-bed me-2"></i>Hotels (${costData.nights || 0} nights)</span>
                    <span>$${costData.hotel_cost?.toFixed(2) || '0.00'}</span>
                </div>
                <div class="cost-item">
                    <span><i class="fas fa-receipt me-2"></i>Taxes & Fees</span>
                    <span>$${costData.taxes_and_fees?.toFixed(2) || '0.00'}</span>
                </div>
                <div class="cost-item">
                    <span><strong>Total</strong></span>
                    <span><strong>$${costData.total_cost?.toFixed(2) || '0.00'}</strong></span>
                </div>
                <small class="text-muted mt-2 d-block">
                    <i class="fas fa-info-circle me-1"></i>
                    Prices are estimates and may vary based on availability
                </small>
            `;
        }
        
        this.costBreakdownCard.style.display = 'block';
    }
    
    displayBookingConfirmation(booking, payment) {
        if (payment && payment.success) {
            const confirmationMessage = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle me-2"></i>Booking Confirmed!</h6>
                    <p class="mb-1"><strong>Confirmation Number:</strong> ${payment.confirmation_number}</p>
                    <p class="mb-1"><strong>Total Amount:</strong> $${payment.amount_charged?.toFixed(2)}</p>
                    <p class="mb-0">A confirmation email has been sent to your email address.</p>
                </div>
            `;
            
            // Add confirmation to chat
            this.addMessage(confirmationMessage, 'bot');
        } else if (payment && !payment.success) {
            const errorMessage = `
                <div class="alert alert-danger">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Payment Failed</h6>
                    <p class="mb-0">${payment.error || 'Payment processing failed. Please try again.'}</p>
                </div>
            `;
            
            this.addMessage(errorMessage, 'bot');
        }
    }
    //TODO: Move to a separate file. 
    addFlightSearchWidget(collectedData) {
        // Create a message container for the widget
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        // Set a unique ID for this widget instance
        const widgetId = 'flight-widget-' + Date.now();
        messageDiv.id = widgetId;
        
        // Add the widget HTML structure
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <div id="${widgetId}-content">
                        <div class="text-center py-3">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading flight search...</p>
                        </div>
                    </div>
                </div>
                <small class="message-time text-muted">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small>
            </div>
        `;
        
        // Add the message to the chat
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Load the flight search widget template
        fetch('/templates/flight_search_widget.html')
            .then(response => response.text())
            .then(html => {
                // Inject the widget HTML
                const widgetContent = document.getElementById(`${widgetId}-content`);
                widgetContent.innerHTML = html;
                
                // Set default values from collectedData if available
                if (collectedData) {
                    if (collectedData.departure_location) document.getElementById('flightFrom').value = collectedData.departure_location;
                    if (collectedData.destination) document.getElementById('flightTo').value = collectedData.destination;
                    if (collectedData.departure_date) document.getElementById('departureDate').value = collectedData.departure_date;
                    if (collectedData.return_date) document.getElementById('returnDate').value = collectedData.return_date;
                }
                
                // Set minimum date to today
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('departureDate').min = today;
                document.getElementById('returnDate').min = today;
                
                // Add event listeners
                this.setupFlightSearchWidget(widgetId, collectedData);
            })
            .catch(error => {
                console.error('Error loading flight search widget:', error);
                const widgetContent = document.getElementById(`${widgetId}-content`);
                widgetContent.innerHTML = '<div class="alert alert-danger">Failed to load flight search. Please try again later.</div>';
            });
    }
    
    setupFlightSearchWidget(widgetId, collectedData) {
        const widget = document.getElementById(widgetId);
        const searchForm = widget.querySelector('.flight-search-form');
        const resultsDiv = widget.querySelector('.flight-results');
        const flightsList = widget.querySelector('#flightsList');
        const searchBtn = widget.querySelector('#searchFlightsBtn');
        const backBtn = widget.querySelector('#backToSearch');
        const selectBtn = widget.querySelector('#selectFlightBtn');
        
        let selectedFlight = null;
        
        // Toggle between search form and results
        const showResults = (show) => {
            searchForm.style.display = show ? 'none' : 'block';
            resultsDiv.style.display = show ? 'block' : 'none';
        };
        
        // Handle flight search
        searchBtn.addEventListener('click', async () => {
            const from = widget.querySelector('#flightFrom').value.trim();
            const to = widget.querySelector('#flightTo').value.trim();
            const departureDate = widget.querySelector('#departureDate').value;
            const returnDate = widget.querySelector('#returnDate').value;
            const passengers = widget.querySelector('#passengers').value;
            const cabinClass = widget.querySelector('#cabinClass').value;
            
            if (!from || !to || !departureDate) {
                alert('Please fill in all required fields');
                return;
            }
            
            try {
                // Show loading state
                flightsList.innerHTML = `
                    <div class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Searching flights...</span>
                        </div>
                        <p class="mt-2 mb-0">Searching for flights...</p>
                    </div>
                `;
                
                showResults(true);
                
                // Call the flight search API
                const response = await fetch('/api/travel/search_flights', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        origin: from,
                        destination: to,
                        departure_date: departureDate,
                        return_date: returnDate || null,
                        passengers: parseInt(passengers),
                        travel_class: cabinClass


                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to search for flights');
                }
                
                const data = await response.json();
                
                if (!data.flights_results || data.flights_results.length === 0) {
                    flightsList.innerHTML = `
                        <div class="alert alert-warning mb-0">
                            No flights found for the selected criteria. Please try different search parameters.
                        </div>
                    `;
                    return;
                }
                
                // Display flight results
                flightsList.innerHTML = data.flights_results.map((flight, index) => {
                    const departureTime = new Date(flight.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const arrivalTime = new Date(flight.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const duration = `${Math.floor(flight.duration / 60)}h ${flight.duration % 60}m`;
                    
                    return `
                        <div class="card mb-2 flight-option ${selectedFlight === index ? 'border-primary' : ''}" 
                             data-index="${index}" 
                             style="cursor: pointer;">
                             <input type="hidden" id="flight-raw-data-${index}" class="flight-raw-data" value='${JSON.stringify(flight.raw).replace(/'/g, "&apos;")}'>
                            <div class="card-body p-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <div class="fw-bold">${flight.airline} ${flight.flight_number}</div>
                                        <div class="small text-muted">${flight.aircraft || 'Aircraft not specified'}</div>
                                    </div>
                                    <div class="text-end">
                                        <div class="fw-bold">₹${flight.price.toFixed(2)}</div>
                                        <div class="small text-muted">${flight.stops} ${flight.stops === 1 ? 'stop' : 'stops'}</div>
                                    </div>
                                </div>
                                <div class="d-flex justify-content-between align-items-center mt-2">
                                    <div>
                                        <div class="fw-bold">${departureTime}</div>
                                        <div class="small">${flight.arrival_airport}</div>
                                    </div>
                                    <div class="text-center px-2" style="flex-grow: 1;">
                                        <div class="flight-route">
                                            <div class="flight-route-line"></div>
                                            <div class="flight-route-duration small">${duration}</div>
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <div class="fw-bold">${arrivalTime}</div>
                                        <div class="small">${flight.departure_airport}</div>
                                    </div>
                                </div>
                            </div>

                        </div>
                    `;
                }).join('');
                
                // Add click handlers for flight selection
                document.querySelectorAll('.flight-option').forEach((card, index) => {
                    card.addEventListener('click', () => {
                        // Remove selection from all cards
                        document.querySelectorAll('.flight-option').forEach(c => {
                            c.classList.remove('border-primary');
                            c.style.border = '1px solid #dee2e6'; // Reset to default border
                        });
                        
                        // Add red border to selected card
                        card.style.border = '2px solid #dc3545';
                        selectedFlight = index;
                        selectBtn.disabled = false;
                    });
                });
                
            } catch (error) {
                console.error('Error searching flights:', error);
                flightsList.innerHTML = `
                    <div class="alert alert-danger mb-0">
                        An error occurred while searching for flights. Please try again later.
                    </div>
                `;
            }
        });
        
        // Back button handler
        backBtn.addEventListener('click', () => {
            showResults(false);
            selectedFlight = null;
            selectBtn.disabled = true;
        });
        
        // Select flight handler
        selectBtn.addEventListener('click', () => {
            if (selectedFlight === null) return;
            
            // Get the selected flight data (in a real app, this would be the actual flight data)
            const flightData = {
                selected: true,
                flightIndex: selectedFlight,
                raw_search_data: encodeURIComponent(JSON.stringify(JSON.parse(document.getElementById(`flight-raw-data-${selectedFlight}`).value)))
                // Add any other relevant flight data here
            };
            
            // Send the selected flight as a message
            this.sendFlightSelection(flightData, widgetId);
            
            // Disable the widget
            widget.querySelectorAll('input, button, select').forEach(el => el.disabled = true);
            selectBtn.innerHTML = '<i class="fas fa-check me-1"></i> Flight Selected';
            selectBtn.classList.remove('btn-primary');
            selectBtn.classList.add('btn-success');
            selectBtn.disabled = true;
        });
    }
    
    sendFlightSelection(flightData, widgetId) {
        // Hide the flight selection widget
        const widget = document.getElementById(widgetId);
        widget.style.display = 'none';
    
        // Create booking form
        const bookingForm = document.createElement('div');
        bookingForm.className = 'booking-form p-3 bg-light rounded mb-3';
        bookingForm.innerHTML = `
            <h5 class="mb-3 text-dark">Complete Your Booking</h5>
            <form id="bookingForm">
                <input type="hidden" name="flight_raw_data" value='${flightData.raw_search_data}'/>
                
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">Full Name</label>
                    <input type="text" class="form-control" name="user_name" required>
                </div>
                
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">Email</label>
                    <input type="email" class="form-control" name="user_email" required>
                </div>
                
                <div id="passengerContainer" class="mb-3">
                    <!-- Passengers will be added here -->
                </div>
                
                <button type="button" class="btn btn-outline-secondary btn-sm mb-3" id="addPassenger">
                    <i class="fas fa-plus me-1"></i> Add Passenger
                </button>
                
                <div class="d-grid gap-2">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-check me-1"></i> Confirm Booking
                    </button>
                </div>
            </form>
        `;
    
        // Insert after the widget
        widget.parentNode.insertBefore(bookingForm, widget.nextSibling);
    
        // Add first passenger field
        this.addPassengerField();
    
        // Add passenger button handler
        document.getElementById('addPassenger').addEventListener('click', () => {
            this.addPassengerField();
        });
    
        // Form submission handler
        document.getElementById('bookingForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const passengers = [];
            
            // Collect passenger data
            document.querySelectorAll('.passenger-row').forEach((row, index) => {
                passengers.push({
                    type: row.querySelector('.passenger-type').value,
                    firstName: row.querySelector('.first-name').value,
                    lastName: row.querySelector('.last-name').value,
                    dob: row.querySelector('.dob').value,
                    gender: row.querySelector('.gender').value,
                    passport: row.querySelector('.passport').value
                });
            });
    
            const bookingData = {
                user_name: formData.get('user_name'),
                user_email: formData.get('user_email'),
                flight_raw_data: formData.get('flight_raw_data'),
                passengers: passengers
            };
    
            try {
                const response = await fetch('/api/travel/book_flight', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(bookingData)
                });
    
                const result = await response.json();
                
                if (response.ok) {
                    this.addMessage(`Your flight has been booked! PNR: ${result.pnr}`, 'assistant',false);
                    // You might want to show booking details here
                } else {
                    throw new Error(result.message || 'Failed to book flight');
                }
            } catch (error) {
                console.error('Booking error:', error);
                this.addMessage(`Sorry, we couldn't process your booking. Please try again.`,'assistant',true);
            }
        });
    }
    
    addPassengerField() {
        const container = document.getElementById('passengerContainer');
        const passengerCount = container.querySelectorAll('.passenger-row').length + 1;
        
        const passengerDiv = document.createElement('div');
        passengerDiv.className = 'passenger-row border p-3 mb-3 rounded';
        passengerDiv.innerHTML = `
            <h6>Passenger ${passengerCount}</h6>
            <div class="row g-2">
                <div class="col-md-2">
                    <select class="form-select passenger-type" required>
                        <option value="ADT">Adult</option>
                        <option value="CHD">Child</option>
                        <option value="INF">Infant</option>
                    </select>
                </div>
                <div class="col-md-5">
                    <input type="text" class="form-control first-name" placeholder="First Name" required>
                </div>
                <div class="col-md-5">
                    <input type="text" class="form-control last-name" placeholder="Last Name" required>
                </div>
                <div class="col-md-4">
                    <input type="date" class="form-control dob" required>
                </div>
                <div class="col-md-3">
                    <select class="form-select gender" required>
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                        <option value="O">Other</option>
                    </select>
                </div>
                <div class="col-md-5">
                    <input type="text" class="form-control passport" placeholder="Passport Number" required>
                </div>
            </div>
        `;
        
        container.appendChild(passengerDiv);
    }
}

// Global functions
function resetChat() {
    if (confirm('Are you sure you want to start a new conversation? All current progress will be lost.')) {
        fetch('/api/reset', { method: 'POST' })
            .then(() => {
                location.reload();
            })
            .catch(error => {
                console.error('Error resetting chat:', error);
                location.reload();
            });
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.tripBot = new TripBotChat();
});

// Handle page visibility change to refocus input
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.tripBot) {
        setTimeout(() => {
            window.tripBot.messageInput.focus();
        }, 100);
    }
});

// Error handling for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    event.preventDefault();
});

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
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
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
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
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
            'traveler_email': 'Email',
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


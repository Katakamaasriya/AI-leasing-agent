/**
 * AI Leasing Agent Chat Widget
 * A modern, responsive chat widget for property inquiries
 */

class LeasingChatWidget {
    constructor(config = {}) {
        this.apiEndpoint = config.apiEndpoint || 'http://127.0.0.1:8000';
        this.propertyId = config.propertyId || null;
        this.leadId = config.leadId || null;
        this.primaryColor = config.primaryColor || '#0f766e';
        this.position = config.position || 'bottom-right';
        this.welcomeMessage = config.welcomeMessage || 'Hello! I\'m your AI leasing assistant. How can I help you find your perfect home today?';
        
        this.isOpen = false;
        this.messages = [];
        this.isTyping = false;
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.addEventListeners();
        this.loadSession();
    }
    
    createWidget() {
        // Create chat button
        this.chatButton = document.createElement('div');
        this.chatButton.className = 'leasing-chat-button';
        this.chatButton.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        `;
        this.chatButton.style.cssText = `
            position: fixed;
            ${this.position === 'bottom-right' ? 'right: 20px;' : 'left: 20px;'}
            bottom: 20px;
            width: 60px;
            height: 60px;
            background-color: ${this.primaryColor};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            transition: transform 0.3s ease;
        `;
        
        // Create chat window
        this.chatWindow = document.createElement('div');
        this.chatWindow.className = 'leasing-chat-window';
        this.chatWindow.innerHTML = `
            <div class="chat-header">
                <div class="chat-title">
                    <span class="status-indicator"></span>
                    AI Leasing Assistant
                </div>
                <button class="close-button">&times;</button>
            </div>
            <div class="chat-messages"></div>
            <div class="chat-input-area">
                <input type="text" class="chat-input" placeholder="Type your message...">
                <button class="send-button">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        `;
        
        this.chatWindow.style.cssText = `
            position: fixed;
            ${this.position === 'bottom-right' ? 'right: 20px;' : 'left: 20px;'}
            bottom: 90px;
            width: 380px;
            height: 500px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            display: none;
            flex-direction: column;
            z-index: 9998;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        // Add styles
        this.addStyles();
        
        document.body.appendChild(this.chatButton);
        document.body.appendChild(this.chatWindow);
        
        // Get references to elements
        this.messagesContainer = this.chatWindow.querySelector('.chat-messages');
        this.inputField = this.chatWindow.querySelector('.chat-input');
        this.sendButton = this.chatWindow.querySelector('.send-button');
        this.closeButton = this.chatWindow.querySelector('.close-button');
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .leasing-chat-button:hover {
                transform: scale(1.1);
            }
            
            .leasing-chat-window .chat-header {
                background: ${this.primaryColor};
                color: white;
                padding: 16px;
                border-radius: 12px 12px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .leasing-chat-window .chat-title {
                font-weight: 600;
                font-size: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .leasing-chat-window .status-indicator {
                width: 8px;
                height: 8px;
                background: #22c55e;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .leasing-chat-window .close-button {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
            }
            
            .leasing-chat-window .close-button:hover {
                background: rgba(255,255,255,0.1);
            }
            
            .leasing-chat-window .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .leasing-chat-window .message {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 12px;
                font-size: 14px;
                line-height: 1.5;
            }
            
            .leasing-chat-window .message.user {
                background: ${this.primaryColor};
                color: white;
                align-self: flex-end;
                border-bottom-right-radius: 4px;
            }
            
            .leasing-chat-window .message.assistant {
                background: #f3f4f6;
                color: #1f2937;
                align-self: flex-start;
                border-bottom-left-radius: 4px;
            }
            
            .leasing-chat-window .typing-indicator {
                display: flex;
                gap: 4px;
                padding: 12px 16px;
                background: #f3f4f6;
                border-radius: 12px;
                width: fit-content;
            }
            
            .leasing-chat-window .typing-indicator span {
                width: 8px;
                height: 8px;
                background: #9ca3af;
                border-radius: 50%;
                animation: typing 1.4s infinite;
            }
            
            .leasing-chat-window .typing-indicator span:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .leasing-chat-window .typing-indicator span:nth-child(3) {
                animation-delay: 0.4s;
            }
            
            @keyframes typing {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-4px); }
            }
            
            .leasing-chat-window .chat-input-area {
                padding: 16px;
                border-top: 1px solid #e5e7eb;
                display: flex;
                gap: 8px;
            }
            
            .leasing-chat-window .chat-input {
                flex: 1;
                padding: 12px 16px;
                border: 1px solid #e5e7eb;
                border-radius: 24px;
                font-size: 14px;
                outline: none;
            }
            
            .leasing-chat-window .chat-input:focus {
                border-color: ${this.primaryColor};
            }
            
            .leasing-chat-window .send-button {
                width: 44px;
                height: 44px;
                background: ${this.primaryColor};
                border: none;
                border-radius: 50%;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            
            .leasing-chat-window .send-button:hover {
                background: ${this.darkenColor(this.primaryColor, 10)};
            }
            
            .leasing-chat-window .send-button:disabled {
                background: #9ca3af;
                cursor: not-allowed;
            }
        `;
        document.head.appendChild(style);
    }
    
    darkenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) - amt;
        const G = (num >> 8 & 0x00FF) - amt;
        const B = (num & 0x0000FF) - amt;
        return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
    }
    
    addEventListeners() {
        this.chatButton.addEventListener('click', () => this.toggleChat());
        this.closeButton.addEventListener('click', () => this.toggleChat());
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }
    
    toggleChat() {
        this.isOpen = !this.isOpen;
        this.chatWindow.style.display = this.isOpen ? 'flex' : 'none';
        
        if (this.isOpen && this.messages.length === 0) {
            this.addMessage('assistant', this.welcomeMessage);
        }
    }
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.textContent = content;
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        
        this.messages.push({ role, content });
        this.saveSession();
    }
    
    showTypingIndicator() {
        if (this.isTyping) return;
        
        this.isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        typingDiv.id = 'typing-indicator';
        this.messagesContainer.appendChild(typingDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        const typingDiv = this.messagesContainer.querySelector('#typing-indicator');
        if (typingDiv) {
            typingDiv.remove();
        }
    }
    
    async sendMessage() {
        const message = this.inputField.value.trim();
        if (!message) return;
        
        this.inputField.value = '';
        this.addMessage('user', message);
        this.showTypingIndicator();
        
        try {
            // Create lead if not exists
            if (!this.leadId) {
                const leadResponse = await fetch(`${this.apiEndpoint}/inquiries`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: 'Web Visitor',
                        contact: 'web@example.com',
                        channel: 'web_chat',
                        message: message,
                        property_id: this.propertyId
                    })
                });
                
                if (leadResponse.ok) {
                    const leadData = await leadResponse.json();
                    this.leadId = leadData.lead_id;
                }
            }
            
            // Send message to AI
            if (this.leadId) {
                const response = await fetch(`${this.apiEndpoint}/agent/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        lead_id: this.leadId,
                        prompt: message
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.hideTypingIndicator();
                    this.addMessage('assistant', data.reply);
                } else {
                    throw new Error('Failed to get AI response');
                }
            } else {
                // Fallback response
                this.hideTypingIndicator();
                this.addMessage('assistant', 'Thank you for your message! A leasing specialist will follow up with you shortly.');
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('assistant', 'Sorry, I encountered an error. Please try again or contact us directly.');
            console.error('Chat error:', error);
        }
    }
    
    saveSession() {
        sessionStorage.setItem('leasing_chat_messages', JSON.stringify(this.messages));
        sessionStorage.setItem('leasing_chat_lead_id', this.leadId || '');
    }
    
    loadSession() {
        const savedMessages = sessionStorage.getItem('leasing_chat_messages');
        const savedLeadId = sessionStorage.getItem('leasing_chat_lead_id');
        
        if (savedMessages) {
            this.messages = JSON.parse(savedMessages);
            this.messages.forEach(msg => this.addMessage(msg.role, msg.content));
        }
        
        if (savedLeadId) {
            this.leadId = savedLeadId || null;
        }
    }
    
    destroy() {
        this.chatButton.remove();
        this.chatWindow.remove();
    }
}

// Initialize widget when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.LeasingChatWidget = LeasingChatWidget;
    });
} else {
    window.LeasingChatWidget = LeasingChatWidget;
}
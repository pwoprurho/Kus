document.addEventListener('DOMContentLoaded', () => {
    
    // =================================================================
    // --- 1. CHAT WIDGET LOGIC ---
    // =================================================================
    const chatToggle = document.getElementById('chat-toggle-btn'); 
    const chatWindow = document.getElementById('chat-window');
    const chatInput = document.getElementById('chat-input-text'); 
    const chatSend = document.getElementById('chat-send-btn'); 
    const chatMessages = document.getElementById('chat-body'); 

    // Helper: Reset Chat Session
    async function resetChat() {
        try {
            // 1. Clear Backend Session
            await fetch('/chat/reset', { method: 'POST' });
            
            // 2. Clear Frontend UI
            if (chatMessages) {
                chatMessages.innerHTML = '';
                // Restore Default Greeting
                const div = document.createElement('div');
                div.className = 'msg bot';
                div.innerText = 'Hello. I am the Kusmus AI Assistant. Ask me about enterprise solutions or engineering certainty.';
                chatMessages.appendChild(div);
            }
        } catch (err) {
            console.error("Failed to reset chat:", err);
        }
    }

    // 1. Toggle Window
    if (chatToggle && chatWindow) {
        chatToggle.addEventListener('click', () => {
            const isOpen = chatWindow.classList.contains('open');
            
            if (isOpen) {
                // CLOSING: Hide window and Reset Chat
                chatWindow.classList.remove('open');
                // Optional: Change icon back
                chatToggle.innerHTML = '<i class="fas fa-comment-dots"></i>';
                
                // Reset the conversation for privacy/fresh context
                setTimeout(resetChat, 300); // Small delay to wait for close animation
                
            } else {
                // OPENING
                chatWindow.classList.add('open');
                chatToggle.innerHTML = '<i class="fas fa-times"></i>';
                
                if (chatInput) {
                    setTimeout(() => chatInput.focus(), 100);
                }
            }
        });
    }

    // 2. Append Message to UI
    function appendMessage(sender, text) {
        if (!chatMessages) return;
        
        const div = document.createElement('div');
        div.className = `msg ${sender}`;
        div.innerText = text;
        
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return div; 
    }

    // 3. Send Message to API
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';

        // Add temporary loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'msg bot';
        loadingDiv.innerText = 'Analyzing...';
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/chat', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            
            // Remove loading message
            loadingDiv.remove();
            
            if (data.response) {
                appendMessage('bot', data.response);
            } else {
                appendMessage('bot', "Connection stable, but no response data.");
            }

        } catch (err) {
            console.error("AI Assistant API Error:", err);
            loadingDiv.remove();
            appendMessage("bot", "Connection interrupted. Please try again.");
        }
    }

    // 4. Event Listeners for Chat Interaction
    if (chatSend && chatInput) {
        chatSend.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
    
    // =================================================================
    // --- 2. MOBILE NAVIGATION TOGGLE ---
    // =================================================================
    const navToggle = document.querySelector('.nav-toggle'); 
    const navList = document.getElementById('primary-navigation'); 

    if (navToggle && navList) {
        navToggle.addEventListener('click', () => {
            const isVisible = navList.getAttribute('data-visible') === "true";
            const newState = (!isVisible).toString();

            // Toggle the data-visible attribute (Triggers CSS sliding)
            navList.setAttribute('data-visible', newState);
            
            // Toggle aria-expanded for accessibility
            navToggle.setAttribute('aria-expanded', newState);
        });
    }
});
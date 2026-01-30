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
            const isOpen = chatWindow.classList.contains('active');
            if (isOpen) {
                chatWindow.classList.remove('active');
                chatWindow.style.height = "0";
                chatWindow.style.opacity = "0";
                chatWindow.style.visibility = "hidden";
            } else {
                chatWindow.classList.add('active');
                chatWindow.style.height = "480px";
                chatWindow.style.opacity = "1";
                chatWindow.style.visibility = "visible";
            }
        });
    }

    // 2. Append Message to UI
    function appendMessage(role, text) {
        if (!chatMessages) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = `msg ${role}`;
        msgDiv.innerText = text;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 3. Send Message to API
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';

        // Show Loading
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'msg bot loading';
        loadingDiv.id = 'ai-loading';
        loadingDiv.innerText = '...';
        chatMessages.appendChild(loadingDiv);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
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
    const navToggles = document.querySelectorAll('.nav-toggle');
    const navList = document.getElementById('primary-navigation');

    if (navToggles.length > 0 && navList) {
        navToggles.forEach(toggle => {
            toggle.addEventListener('click', () => {
                const isVisible = navList.getAttribute('data-visible') === "true";
                const newState = (!isVisible).toString();

                // Toggle the data-visible attribute (Triggers CSS sliding)
                navList.setAttribute('data-visible', newState);

                // Toggle aria-expanded for accessibility on all toggles
                navToggles.forEach(t => {
                    t.setAttribute('aria-expanded', newState);
                    // Dynamic Icon Switching
                    const icon = t.querySelector('i');
                    if (icon) {
                        if (newState === "true") {
                            icon.classList.remove('fa-bars');
                            icon.classList.add('fa-times');
                        } else {
                            icon.classList.remove('fa-times');
                            icon.classList.add('fa-bars');
                        }
                    }
                });
            });
        });
    }
});
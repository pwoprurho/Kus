// static/js/tax_agent.js

document.addEventListener('DOMContentLoaded', function() {
  // Handle file uploads
  const uploadForm = document.getElementById('upload-form');
  const uploadStatus = document.getElementById('upload-status');
  const miniTableContainer = document.getElementById('mini-table-container');

  uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(uploadForm);
    uploadStatus.textContent = 'Uploading...';
    try {
      const res = await fetch('/api/tax/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        uploadStatus.textContent = 'Files uploaded successfully!';
        renderFileList(data.files);
      } else {
        uploadStatus.textContent = data.error || 'Upload failed.';
      }
    } catch (err) {
      uploadStatus.textContent = 'Error uploading files.';
    }
  });

  function renderFileList(files) {
    if (!files || files.length === 0) {
      miniTableContainer.innerHTML = '<em class="text-muted">No documents uploaded yet.</em>';
      return;
    }
    let html = '<div class="list-group">';
    files.forEach(f => {
      let icon = 'fa-file';
      if (f.name.endsWith('.pdf')) icon = 'fa-file-pdf';
      else if (f.name.match(/\.(jpg|jpeg|png)$/i)) icon = 'fa-file-image';
      
      html += `
        <div class="list-group-item bg-transparent border-secondary text-light d-flex align-items-center">
            <i class="fas ${icon} fa-lg me-3 text-primary"></i>
            <div>
                <div class="fw-bold">${f.type}</div>
                <small class="text-muted">${f.name}</small>
            </div>
            <i class="fas fa-check-circle text-success ms-auto"></i>
        </div>
      `;
    });
    html += '</div>';
    miniTableContainer.innerHTML = html;
  }

  // Chat logic
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const chatBox = document.getElementById('chat-box');
  const cognitiveTrace = document.getElementById('cognitive-trace');

  chatForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;
    
    // Updated UI for User Message
    chatBox.innerHTML += `<div class="message user"><strong>You:</strong><br>${msg}</div>`;
    chatInput.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    // Add processing bubble
    const processingId = 'proc-' + Date.now();
    const processingHTML = `
        <div id="${processingId}" class="message processing">
            <div class="processing-spinner"></div>
            <span>Agent is thinking...</span>
        </div>
    `;
    chatBox.insertAdjacentHTML('beforeend', processingHTML);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
      const res = await fetch('/api/tax/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      
      // Remove processing bubble
      const processingEl = document.getElementById(processingId);
      if (processingEl) processingEl.remove();

      const data = await res.json();
      
      if (res.ok) {
          // Construct Thought Trace HTML if available
          let thoughtsHTML = '';
          if (data.thought_trace && data.thought_trace.length > 0) {
              const thoughtsText = data.thought_trace.join('\n\n');
              thoughtsHTML = `
                  <details class="thought-bubble">
                      <summary class="thought-summary">
                          <i class="fas fa-brain"></i>
                          <span>Thinking Process</span>
                      </summary>
                      <div class="thought-content">${thoughtsText}</div>
                  </details>
              `;
          }

          // Updated UI for Agent Message with Thoughts
          chatBox.innerHTML += `
              <div class="message agent">
                  ${thoughtsHTML}
                  <strong>Agent:</strong><br>${data.response}
              </div>
          `;
          
          // Clear the old global trace if it exists
          if (cognitiveTrace) cognitiveTrace.textContent = '';

      } else {
          // Handle server errors (like 503 Overloaded)
          chatBox.innerHTML += `<div class="message agent text-danger"><strong>System:</strong> ${data.error || 'An error occurred.'}</div>`;
      }
      
      chatBox.scrollTop = chatBox.scrollHeight;
    } catch (err) {
      // Remove processing bubble
      const processingEl = document.getElementById(processingId);
      if (processingEl) processingEl.remove();

      chatBox.innerHTML += '<div class="message agent text-danger">Error contacting agent. Please check your connection.</div>';
    }
  });
});

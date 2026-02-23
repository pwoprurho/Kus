// static/js/tax_agent.js

document.addEventListener('DOMContentLoaded', function () {
    // Handle file uploads
    const uploadForm = document.getElementById('upload-form');
    const uploadStatus = document.getElementById('upload-status');

    uploadForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        if (typeof fileQueue === 'undefined' || fileQueue.length === 0) {
            uploadStatus.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-circle me-2"></i>No files to upload.</span>';
            return;
        }

        const formData = new FormData();
        const descInput = uploadForm.querySelector('input[name="file_description"]');
        if (descInput && descInput.value) {
            formData.append('file_description', descInput.value);
        }

        // Append all files in the queue
        fileQueue.forEach(f => {
            formData.append('documents', f);
        });

        uploadStatus.innerHTML = '<span class="text-info"><i class="fas fa-spinner fa-spin me-2"></i>Uploading & analyzing ' + fileQueue.length + ' document(s)...</span>';
        try {
            const res = await fetch('/api/tax/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                uploadStatus.innerHTML = '<span class="text-success"><i class="fas fa-check-circle me-2"></i>' + data.count + ' document(s) uploaded and analyzed successfully!</span>';

                // Clear the queue after successful upload
                fileQueue = [];
                if (typeof renderFileQueue === 'function') renderFileQueue();
                if (typeof clearIndexedDB === 'function') clearIndexedDB();
                if (descInput) descInput.value = '';

            } else {
                uploadStatus.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle me-2"></i>' + (data.error || 'Upload failed.') + '</span>';
            }
        } catch (err) {
            uploadStatus.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle me-2"></i>Error uploading files.</span>';
        }
    });

    // Chat logic
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatBox = document.getElementById('chat-box');
    const cognitiveTrace = document.getElementById('cognitive-trace');

    chatForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (!msg) return;

        // Updated UI for User Message
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        chatBox.innerHTML += `
        <div class="message user" style="margin-bottom: 2rem;">
            <div class="d-flex justify-content-between align-items-center mb-1">
                 <div style="display:flex; align-items:center; gap:8px;">
                      <div class="user-avatar" style="width:24px; height:24px; background: #6c757d; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                         <i class="fas fa-user text-white" style="font-size: 12px;"></i>
                      </div>
                      <strong>You</strong>
                  </div>
                <span class="text-white-50 small" style="font-size: 0.75rem;">${timeStr}</span>
            </div>
            <div style="margin-left: 32px; font-size: 0.95rem;">
                ${msg}
            </div>
        </div>`;
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
            // Collect visible history for context
            const history = [];
            document.querySelectorAll('.message').forEach(el => {
                // rudimentary reconstruction of history
                if (el.classList.contains('user')) {
                    // Logic to get text content without the You/Time header?
                    // Since we changed structure, el.innerText might include time.
                    // Let's rely on finding the last text node or clean it.
                    // Simplest: Just grab the whole text and strip "You:" and time pattern if needed,
                    // OR store raw content in a data attribute.
                    // For now, let's just use a simpler parsing or just the text that isn't the header.
                    let clone = el.cloneNode(true);
                    let header = clone.querySelector('.d-flex');
                    if (header) header.remove();
                    history.push({ role: 'user', content: clone.innerText.trim() });
                } else if (el.classList.contains('agent')) {
                    let clone = el.cloneNode(true);
                    let header = clone.querySelector('.d-flex');
                    if (header) header.remove();
                    // remove thoughts
                    let details = clone.querySelector('details');
                    if (details) details.remove();
                    let loader = clone.querySelector('.agent-loader');
                    if (loader) loader.remove();

                    history.push({ role: 'model', content: clone.innerText.trim() });
                }
            });

            // Prepare UI for Streaming Response
            const msgId = 'msg-' + Date.now();

            // Removed: generic processing bubble removal here to keep it until we init stream or replace it.
            // Better: Replace the "processing" bubble with the Agent message logic directly.
            const processingEl = document.getElementById(processingId);
            if (processingEl) processingEl.remove();

            // NEW: Added back the spinner INSIDE the agent message initially
            const agentTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const agentMsgHTML = `
          <div id="${msgId}" class="message agent" style="display:flex; flex-direction:column;">
              <div class="d-flex justify-content-between align-items-center mb-1">
                  <div style="display:flex; align-items:center; gap:8px;">
                      <div class="agent-avatar" style="width:24px; height:24px; background: linear-gradient(135deg, #FFB75E, #ED8F03); border-radius:50%; display:flex; align-items:center; justify-content:center;">
                         <i class="fas fa-robot text-white" style="font-size: 12px;"></i>
                      </div>
                      <strong>Kusmus Tax Agent</strong>
                  </div>
                  <span class="text-white-50 small" style="font-size: 0.75rem;">${agentTimeStr}</span>
              </div>
              <div class="agent-loader" style="display:flex; align-items:center; gap:10px; margin-bottom:10px; margin-left: 32px;">
                  <div class="processing-spinner" style="width:16px; height:16px;"></div>
                  <span class="text-muted fst-italic small">Initiating Tax Protocol...</span>
              </div>
              
              <details class="thought-bubble" open style="display:none; margin-top:5px; margin-bottom:15px; margin-left: 32px; border-left: 2px solid #58a6ff; padding-left: 12px;">
                  <summary class="thought-summary text-primary" style="cursor:pointer; font-size:0.85rem; list-style:none; display:flex; align-items:center; gap:8px; outline:none; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                      <i class="fas fa-chevron-down toggle-icon" style="font-size:0.8em; transition: transform 0.2s;"></i>
                      <i class="fas fa-brain fa-pulse status-icon"></i> 
                      <span class="status-text">Thinking...</span>
                  </summary>
                  <div class="thought-content text-white-50 small" style="white-space: pre-wrap; margin-top:8px; font-family: 'Consolas', monospace; max-height:250px; overflow-y:auto; background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; font-size: 0.8em; line-height: 1.4;"></div>
              </details>

              <div class="agent-content" style="margin-left: 32px; font-family: 'Segoe UI', sans-serif; font-size: 0.95rem; line-height: 1.6; color: #e6edf3;"></div>
          </div>
      `;

            chatBox.insertAdjacentHTML('beforeend', agentMsgHTML);

            const msgContainer = document.getElementById(msgId);
            const loaderDiv = msgContainer.querySelector('.agent-loader');
            const contentDiv = msgContainer.querySelector('.agent-content');
            const thoughtBubble = msgContainer.querySelector('.thought-bubble');
            const thoughtContent = msgContainer.querySelector('.thought-content');
            const thoughtSummaryText = msgContainer.querySelector('.thought-summary .status-text');
            const thoughtStatusIcon = msgContainer.querySelector('.thought-summary .status-icon');
            const toggleIcon = msgContainer.querySelector('.thought-summary .toggle-icon');

            // Add click listener to toggle icon rotation
            msgContainer.querySelector('summary').addEventListener('click', function () {
                if (thoughtBubble.open) {
                    toggleIcon.style.transform = 'rotate(-90deg)';
                } else {
                    toggleIcon.style.transform = 'rotate(0deg)';
                }
            });

            // Initiate Stream
            try {
                const response = await fetch('/api/tax/chat_stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg, history: history })
                });

                if (!response.ok) {
                    throw new Error(`Server Error: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let accumulatedMarkdown = '';
                let hasReceivedData = false;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    hasReceivedData = true;
                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;

                    // Process SSE lines (data: {...})
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop(); // Keep partial line in buffer

                    for (const line of lines) {
                        if (line.trim().startsWith('data: ')) {
                            const dataStr = line.replace('data: ', '').trim();
                            if (dataStr === '[DONE]') {
                                break;
                            }

                            try {
                                const event = JSON.parse(dataStr);

                                // Hide loader on first data packet
                                if (loaderDiv.style.display !== 'none') {
                                    loaderDiv.style.display = 'none';
                                }

                                if (event.type === 'thought') {
                                    // Reveal thought bubble
                                    if (thoughtBubble.style.display === 'none') {
                                        thoughtBubble.style.display = 'block';
                                    }
                                    // Update text
                                    thoughtContent.innerText += event.content + '\n';
                                    thoughtSummaryText.innerText = "Thinking Process...";
                                    // Auto-scroll thought box
                                    thoughtContent.scrollTop = thoughtContent.scrollHeight;

                                } else if (event.type === 'content') {
                                    // Once we get content, maybe collapse thoughts or change icon?
                                    if (thoughtStatusIcon.classList.contains('fa-pulse')) {
                                        thoughtStatusIcon.classList.remove('fa-pulse');
                                        thoughtSummaryText.innerText = "Reasoning Complete";
                                        // Optional: Auto-collapse when done?
                                        // thoughtBubble.removeAttribute('open'); 
                                        // toggleIcon.style.transform = 'rotate(-90deg)';
                                    }

                                    accumulatedMarkdown += event.content;

                                    // Safe render
                                    if (typeof marked !== 'undefined' && marked.parse) {
                                        contentDiv.innerHTML = marked.parse(accumulatedMarkdown);
                                    } else {
                                        // Fallback if library missing
                                        contentDiv.innerText = accumulatedMarkdown;
                                    }

                                } else if (event.type === 'error') {
                                    if (loaderDiv.style.display !== 'none') loaderDiv.style.display = 'none';
                                    contentDiv.innerHTML += `<div class="alert alert-danger mt-2"><strong>Error:</strong> ${event.content}</div>`;
                                }
                            } catch (e) {
                                console.error('JSON Parse Error', e);
                                contentDiv.innerHTML += `<div class="text-danger small">Parsing error: ${e.message}</div>`;
                            }
                        }
                    } // end for
                    chatBox.scrollTop = chatBox.scrollHeight;
                } // end while

                // --- STREAM COMPLETE: FINAL TAG CHECKS ---
                const personalTrigger = /\[?\[?TRIGGER_FORM_PERSONAL\]?\]?/i;
                const corporateTrigger = /\[?\[?TRIGGER_FORM_CORPORATE\]?\]?/i;
                const legacyTrigger = /\[?\[?TRIGGER_FORM\]?\]?/i;
                const generateFilingTrigger = /\[?\[?GENERATE_FILING\]?\]?/i;

                let detectedForm = null;

                if (generateFilingTrigger.test(accumulatedMarkdown)) {
                    const cleanText = accumulatedMarkdown.replace(generateFilingTrigger, '').trim();
                    if (typeof marked !== 'undefined' && marked.parse) {
                        contentDiv.innerHTML = marked.parse(cleanText) +
                            '<div id="pdf-gen-status" class="mt-3"><span class="text-info"><i class="fas fa-spinner fa-spin me-2"></i>Generating Official Tax Document...</span></div>';
                    } else {
                        contentDiv.innerText = cleanText;
                    }

                    fetch('/api/tax/generate_filing', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    })
                        .then(res => res.json())
                        .then(data => {
                            const statusDiv = contentDiv.querySelector('#pdf-gen-status');
                            if (data.success && statusDiv) {
                                statusDiv.innerHTML = `<a href="${data.pdf_url}" class="btn btn-success mt-2" download target="_blank"><i class="fas fa-file-pdf me-2"></i> Download Official Tax Filing Document</a>`;
                            } else if (statusDiv) {
                                statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Failed to generate document.</span>`;
                            }
                        })
                        .catch(err => {
                            const statusDiv = contentDiv.querySelector('#pdf-gen-status');
                            if (statusDiv) statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-2"></i>Server error during generation.</span>`;
                        });
                } else if (personalTrigger.test(accumulatedMarkdown)) {
                    detectedForm = 'personal';
                } else if (corporateTrigger.test(accumulatedMarkdown)) {
                    detectedForm = 'corporate';
                } else if (legacyTrigger.test(accumulatedMarkdown)) {
                    detectedForm = 'personal';
                }

                if (detectedForm) {
                    const cleanText = accumulatedMarkdown.replace(/\[?\[?TRIGGER_FORM(_PERSONAL|_CORPORATE)?\]?\]?/i, '').trim();
                    if (typeof marked !== 'undefined' && marked.parse) contentDiv.innerHTML = marked.parse(cleanText);
                    setTimeout(() => { showTaxForm(detectedForm); }, 800);
                }

                if (!hasReceivedData && !accumulatedMarkdown) {
                    if (loaderDiv.style.display !== 'none') loaderDiv.style.display = 'none';
                    contentDiv.innerHTML = '<span class="text-warning">Server sent no data. Please try again.</span>';
                }

            } catch (fetchErr) {
                if (loaderDiv) loaderDiv.style.display = 'none';
                contentDiv.innerHTML = `<span class="text-danger">Network Connection Error: ${fetchErr.message}</span>`;
            }

        } catch (err) {
            console.error(err);
            // Remove processing bubble if still there
            const processingEl = document.getElementById(processingId);
            if (processingEl) processingEl.remove();
            chatBox.innerHTML += '<div class="message agent text-danger">Connection Failed (Client Logic).</div>';
        }
    });
});

// Tax Filing Generation Function
async function generateTaxFiling() {
    const btn = document.getElementById('generate-filing-btn');
    const originalHTML = btn.innerHTML;

    try {
        // Show loading state
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Generating...';

        // Get taxpayer info (you can add a form for this or use session data)
        const taxpayerInfo = {
            taxpayer_name: prompt('Enter your full name:') || 'N/A',
            taxpayer_tin: prompt('Enter your TIN (Tax Identification Number):') || 'N/A',
            taxpayer_address: prompt('Enter your address:') || 'N/A',
            taxpayer_email: prompt('Enter your email:') || 'N/A',
            taxpayer_phone: prompt('Enter your phone:') || 'N/A',
            tax_year: 2025,
            wht_paid: parseFloat(prompt('Enter WHT (Withholding Tax) already paid (₦):') || '0')
        };

        // Call API
        const response = await fetch('/api/tax/generate_filing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taxpayerInfo)
        });

        const data = await response.json();

        if (data.success) {
            // Show success message with summary
            const summary = data.summary;
            const summaryHTML = `
        <div class="alert alert-success mt-3">
          <h6><i class="fas fa-check-circle me-2"></i>Tax Filing Generated Successfully!</h6>
          <hr>
          <div class="row">
            <div class="col-6"><strong>Gross Income:</strong></div>
            <div class="col-6 text-end">₦ ${summary.gross_income.toLocaleString()}</div>
          </div>
          <div class="row">
            <div class="col-6"><strong>Total Reliefs:</strong></div>
            <div class="col-6 text-end">₦ ${summary.total_reliefs.toLocaleString()}</div>
          </div>
          <div class="row">
            <div class="col-6"><strong>Taxable Income:</strong></div>
            <div class="col-6 text-end">₦ ${summary.taxable_income.toLocaleString()}</div>
          </div>
          <div class="row">
            <div class="col-6"><strong>Tax Due:</strong></div>
            <div class="col-6 text-end">₦ ${summary.tax_due.toLocaleString()}</div>
          </div>
          <div class="row mt-2 pt-2 border-top">
            <div class="col-6"><strong>Balance Due:</strong></div>
            <div class="col-6 text-end"><strong>₦ ${summary.balance_due.toLocaleString()}</strong></div>
          </div>
          <div class="mt-3">
            <a href="${data.pdf_url}" class="btn btn-primary btn-sm" download>
              <i class="fas fa-download me-2"></i>Download PDF
            </a>
          </div>
        </div>
      `;

            document.getElementById('upload-status').innerHTML = summaryHTML;

            // Optionally auto-download
            if (confirm('Would you like to download the PDF now?')) {
                window.location.href = data.pdf_url;
            }

        } else {
            document.getElementById('upload-status').innerHTML = `
        <div class="alert alert-danger mt-3">
          <i class="fas fa-exclamation-triangle me-2"></i>${data.error || 'Failed to generate tax filing'}
        </div>
      `;
        }

    } catch (error) {
        console.error('Tax Filing Error:', error);
        document.getElementById('upload-status').innerHTML = `
      <div class="alert alert-danger mt-3">
        <i class="fas fa-exclamation-triangle me-2"></i>Error: ${error.message}
      </div>
    `;
    } finally {
        // Restore button
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}



// --- COMPREHENSIVE FORM UTILITIES ---

function showTaxForm(type) {
    type = type || 'personal';
    hideTaxForm(); // close any open modal first
    if (type === 'corporate') {
        const modal = document.getElementById('corporate-form-modal');
        if (modal) modal.style.display = 'flex';
    } else {
        const modal = document.getElementById('tax-form-modal');
        if (modal) modal.style.display = 'flex';
    }
}

function hideTaxForm() {
    const personal = document.getElementById('tax-form-modal');
    const corporate = document.getElementById('corporate-form-modal');
    if (personal) personal.style.display = 'none';
    if (corporate) corporate.style.display = 'none';
}

// Generic form submission handler
async function handleTaxFormSubmit(formElement, formType) {
    const submitBtn = formElement.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerText;
    const formData = new FormData(formElement);
    const data = Object.fromEntries(formData.entries());

    // Convert all number inputs
    formElement.querySelectorAll('input[type="number"]').forEach(inp => {
        data[inp.name] = parseFloat(data[inp.name] || 0);
    });

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Syncing...';

        const res = await fetch('/api/tax/submit_comprehensive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await res.json();
        if (result.success) {
            hideTaxForm();
            const chatBox = document.getElementById('chat-box');
            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const label = formType === 'corporate' ? 'Corporate Tax Form' : 'Personal Tax Form';
            chatBox.innerHTML += `
                <div class="message user" style="margin-bottom: 2rem;">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                         <div style="display:flex; align-items:center; gap:8px;">
                              <div class="user-avatar" style="width:24px; height:24px; background: #6c757d; border-radius:50%; display:flex; align-items:center; justify-content:center;">
                                 <i class="fas fa-user text-white" style="font-size: 12px;"></i>
                              </div>
                              <strong>You</strong>
                          </div>
                        <span class="text-white-50 small" style="font-size: 0.75rem;">${timeStr}</span>
                    </div>
                    <div style="margin-left: 32px; font-size: 0.95rem; font-style: italic; color: #58a6ff;">
                        [${label} Submitted Successfully]
                    </div>
                </div>`;
            chatBox.scrollTop = chatBox.scrollHeight;

            const chatInput = document.getElementById('chat-input');
            if (formType === 'corporate') {
                chatInput.value = "I have submitted the corporate tax form. Please analyze the data and provide the Company Income Tax breakdown.";
            } else {
                chatInput.value = "I have submitted the personal tax form. Please analyze the data and provide the Personal Income Tax breakdown.";
            }
            document.getElementById('chat-form').dispatchEvent(new Event('submit'));
        } else {
            alert("Submission error: " + (result.error || "Unknown error"));
        }
    } catch (err) {
        console.error(err);
        alert("Failed to connect to secure server.");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// Personal Form Submission
document.getElementById('comprehensive-tax-form').addEventListener('submit', function (e) {
    e.preventDefault();
    handleTaxFormSubmit(e.target, 'personal');
});

// Corporate Form Submission
document.getElementById('corporate-tax-form').addEventListener('submit', function (e) {
    e.preventDefault();
    handleTaxFormSubmit(e.target, 'corporate');
});

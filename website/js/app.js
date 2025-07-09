// Data Compose - Unified Application Framework
// Extensible single-page application with preserved functionality

class DataComposeApp {
    constructor() {
        this.currentSection = 'home';
        this.webhookUrl = CONFIG.WEBHOOK_URL;
        this.sections = new Map();
        
        // Chat history management
        this.currentChatId = null;
        this.chatHistory = new Map();
        
        this.init();
    }

    init() {
        this.setupNavigation();
        this.registerSections();
        this.showSection(this.currentSection);
        console.log('Aletheia App initialized with webhook:', this.webhookUrl);
    }

    // Navigation System
    setupNavigation() {
        const navTabs = document.querySelectorAll('.nav-tab');
        navTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const sectionId = tab.getAttribute('data-section');
                this.showSection(sectionId);
            });
        });
    }

    showSection(sectionId) {
        // Call onHide for current section if it exists
        if (this.currentSection && this.sections.has(this.currentSection)) {
            const currentHandler = this.sections.get(this.currentSection);
            if (currentHandler.onHide) {
                currentHandler.onHide();
            }
        }
        
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        // Remove active state from all nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // Show target section
        const targetSection = document.getElementById(sectionId);
        const targetTab = document.querySelector(`[data-section="${sectionId}"]`);
        
        if (targetSection && targetTab) {
            targetSection.classList.add('active');
            targetTab.classList.add('active');
            this.currentSection = sectionId;
            
            // Call section-specific initialization if it exists
            if (this.sections.has(sectionId)) {
                const handler = this.sections.get(sectionId);
                if (handler.onShow) {
                    handler.onShow();
                }
            }
        }
    }

    // Section Registration System - allows easy addition of new sections
    registerSection(id, sectionHandler) {
        this.sections.set(id, sectionHandler);
    }

    registerSections() {
        // Home Section
        this.registerSection('home', {
            onShow: () => {
                // Home section is static, no special handling needed
            }
        });

        // Chat Section
        this.registerSection('chat', {
            onShow: () => {
                this.initializeChatIfNeeded();
                this.loadChatHistory();
                document.getElementById('chat-history-toggle').style.display = 'flex';
                document.querySelector('.new-chat-btn').style.display = 'flex';
            },
            onHide: () => {
                document.getElementById('chat-history-drawer').classList.remove('open');
                document.getElementById('chat-history-toggle').style.display = 'none';
                document.querySelector('.new-chat-btn').style.display = 'none';
            }
        });

        // Workflows Section
        this.registerSection('workflows', {
            onShow: () => {
                this.loadWorkflows();
            }
        });

        // Hierarchical Summarization Section
        this.registerSection('hierarchical-summarization', {
            onShow: () => {
                this.loadSummarizationHistory();
                // Show history toggle button and new summarization button
                document.getElementById('history-toggle').style.display = 'flex';
                document.querySelector('.new-summarization-main-btn').style.display = 'flex';
            },
            onHide: () => {
                // Hide history drawer when leaving section
                document.getElementById('history-drawer').classList.remove('open');
                document.getElementById('history-toggle').style.display = 'none';
                document.querySelector('.new-summarization-main-btn').style.display = 'none';
            }
        });

        // RAG Testing Section
        this.registerSection('rag-testing', {
            onShow: () => {
                if (window.ragTesting) {
                    window.ragTesting.initialize();
                }
            }
        });
    }

    // Extensibility: Easy method to add new sections
    addSection(id, title, icon, contentHtml, handler = {}) {
        // Add navigation tab
        const navTabs = document.querySelector('.nav-tabs');
        const newTab = document.createElement('button');
        newTab.className = 'nav-tab';
        newTab.setAttribute('data-section', id);
        newTab.innerHTML = `<i class="${icon}"></i> ${title}`;
        navTabs.appendChild(newTab);

        // Add content section
        const appMain = document.querySelector('.app-main');
        const newSection = document.createElement('div');
        newSection.id = id;
        newSection.className = 'content-section';
        newSection.innerHTML = contentHtml;
        appMain.appendChild(newSection);

        // Register handler
        this.registerSection(id, handler);
        
        // Re-setup navigation to include new tab
        this.setupNavigation();
    }

    // Chat Functionality (Preserved from original)
    initializeChatIfNeeded() {
        const messageInput = document.getElementById('chat-input');
        if (messageInput && !messageInput.hasAttribute('data-initialized')) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
            messageInput.setAttribute('data-initialized', 'true');
        }
    }

    addMessage(text, isUser = false) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user' : 'bot');
        messageDiv.textContent = text;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async sendMessage() {
        const messageInput = document.getElementById('chat-input');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        // Initialize new chat if needed
        if (!this.currentChatId) {
            this.currentChatId = this.generateChatId();
        }
        
        this.addMessage(message, true);
        messageInput.value = '';
        
        try {
            this.updateChatStatus('Sending...');
            
            // Get the selected chat mode
            const chatMode = document.querySelector('input[name="chat-mode"]:checked').value;
            const action = chatMode === 'local' ? 'local_chat' : 'public_chat';
            
            const response = await fetch(this.webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: action,
                    sessionKey: this.currentChatId,  // Using chatId as sessionKey for n8n PostgreSQL storage
                    message: message,
                    timestamp: new Date().toISOString()
                })
            });
            
            // Check if response is JSON or plain text
            const contentType = response.headers.get('content-type');
            let responseText;
            
            if (contentType && contentType.includes('application/json')) {
                // Handle JSON response
                const jsonData = await response.json();
                // Extract text from JSON - adjust based on your n8n output structure
                responseText = jsonData.response || jsonData.output || jsonData.message || JSON.stringify(jsonData);
            } else {
                // Handle plain text response
                responseText = await response.text();
            }
            
            this.updateChatStatus('');
            this.addMessage(responseText);
            
            // Save conversation after successful response
            this.saveCurrentConversation();
            
        } catch (error) {
            this.updateChatStatus('Error: ' + error.message);
            console.error('Chat error:', error);
        }
    }

    updateChatStatus(message) {
        const statusElement = document.getElementById('chat-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    // Chat History Management Methods
    generateChatId() {
        return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getChatHistory() {
        const stored = localStorage.getItem('ai_chat_history');
        return stored ? JSON.parse(stored) : [];
    }

    saveChatHistory(history) {
        localStorage.setItem('ai_chat_history', JSON.stringify(history));
    }

    saveCurrentConversation() {
        const messages = document.querySelectorAll('#chat-messages .message');
        if (messages.length <= 1) return; // Don't save if only welcome message
        
        const conversation = {
            id: this.currentChatId,
            timestamp: new Date().toISOString(),
            messageCount: messages.length,
            preview: messages[1]?.textContent.substring(0, 100) || 'New conversation',
            messages: Array.from(messages).map(msg => ({
                content: msg.textContent,
                isUser: msg.classList.contains('user'),
                timestamp: new Date().toISOString()
            }))
        };
        
        const history = this.getChatHistory();
        
        // Update existing conversation or add new one
        const existingIndex = history.findIndex(item => item.id === this.currentChatId);
        if (existingIndex !== -1) {
            history[existingIndex] = conversation;
        } else {
            history.unshift(conversation);
        }
        
        // Keep only last 50 conversations
        if (history.length > 50) {
            history.splice(50);
        }
        
        this.saveChatHistory(history);
        this.loadChatHistory();
    }

    loadChatHistory() {
        const history = this.getChatHistory();
        const historyList = document.getElementById('chat-history-list');
        
        if (!historyList) return;
        
        if (history.length === 0) {
            historyList.innerHTML = '<div class="history-empty">No conversations yet</div>';
        } else {
            historyList.innerHTML = history.map(item => `
                <div class="history-item" 
                     onclick="window.app.loadChatConversation('${item.id}')"
                     oncontextmenu="window.app.showChatHistoryContextMenu(event, '${item.id}'); return false;">
                    <div class="history-item-title">${item.preview}</div>
                    <div class="history-item-meta">
                        ${new Date(item.timestamp).toLocaleDateString()} • 
                        ${item.messageCount} messages
                    </div>
                </div>
            `).join('');
        }
    }

    loadChatConversation(chatId) {
        const history = this.getChatHistory();
        const conversation = history.find(item => item.id === chatId);
        
        if (!conversation) return;
        
        // Clear current chat
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = '';
        
        // Load messages
        conversation.messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message');
            messageDiv.classList.add(msg.isUser ? 'user' : 'bot');
            messageDiv.textContent = msg.content;
            chatMessages.appendChild(messageDiv);
        });
        
        // Update current chat ID
        this.currentChatId = chatId;
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Close drawer
        document.getElementById('chat-history-drawer').classList.remove('open');
    }

    showChatHistoryContextMenu(event, chatId) {
        event.preventDefault();
        
        // Remove any existing context menu
        const existingMenu = document.querySelector('.context-menu');
        if (existingMenu) existingMenu.remove();
        
        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';
        menu.innerHTML = `
            <div class="context-menu-item" onclick="window.app.deleteChatConversation('${chatId}')">
                <i class="fas fa-trash"></i> Delete
            </div>
        `;
        
        document.body.appendChild(menu);
        
        // Remove menu when clicking elsewhere
        setTimeout(() => {
            document.addEventListener('click', function removeMenu() {
                menu.remove();
                document.removeEventListener('click', removeMenu);
            }, { once: true });
        }, 100);
    }

    deleteChatConversation(chatId) {
        if (confirm('Delete this conversation?')) {
            const history = this.getChatHistory();
            const filtered = history.filter(item => item.id !== chatId);
            this.saveChatHistory(filtered);
            this.loadChatHistory();
            
            // If deleted current chat, start new one
            if (chatId === this.currentChatId) {
                this.startNewChat();
            }
        }
    }

    startNewChat() {
        this.currentChatId = this.generateChatId();
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div class="message bot">
                Welcome! I'm your AI assistant powered by DeepSeek R1. How can I help you today?
            </div>
        `;
    }

    // n8n Connection Test (Preserved from original)
    async testN8nConnection() {
        const resultBox = document.getElementById('connection-result');
        resultBox.innerHTML = '<p class="loading">Testing connection...</p>';
        resultBox.className = 'info-box';
        
        try {
            const response = await fetch('/n8n/healthz');
            const data = await response.json();
            
            resultBox.innerHTML = 
                '<p><strong>✅ Connection Successful!</strong></p>' +
                '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            resultBox.className = 'info-box success';
            
        } catch (error) {
            resultBox.innerHTML = 
                '<p><strong>❌ Connection Failed:</strong> ' + error.message + '</p>';
            resultBox.className = 'info-box error';
        }
    }

    // Workflows Functionality (Preserved from original)
    async loadWorkflows() {
        const workflowsList = document.getElementById('workflows-list');
        workflowsList.innerHTML = '<p class="loading">Loading workflows...</p>';
        
        try {
            const response = await fetch('/n8n/rest/workflows', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data && data.data && data.data.length > 0) {
                    let html = '<h3>Current Workflows:</h3>';
                    
                    data.data.forEach(workflow => {
                        const statusClass = workflow.active ? 'active' : 'inactive';
                        const statusText = workflow.active ? '✅ Active' : '⏸️ Inactive';
                        
                        html += `
                            <div class="workflow-item">
                                <span class="workflow-name">${workflow.name}</span>
                                <span class="workflow-status ${statusClass}">${statusText}</span>
                            </div>
                        `;
                    });
                    
                    workflowsList.innerHTML = html;
                } else {
                    workflowsList.innerHTML = 
                        '<p>No workflows found. <a href="/n8n/" target="_blank" class="btn btn-primary">Create your first workflow</a></p>';
                }
            } else {
                workflowsList.innerHTML = 
                    '<p class="text-center">Error fetching workflows. You may need to authenticate first.</p>';
            }
        } catch (error) {
            workflowsList.innerHTML = 
                '<p class="text-center">Error: ' + error.message + '</p>';
        }
    }

    // Hierarchical Summarization Methods
    loadSummarizationHistory() {
        const history = this.getSummarizationHistory();
        const historyList = document.getElementById('history-list');
        
        if (history.length === 0) {
            historyList.innerHTML = '<div class="history-empty">No summarizations yet</div>';
        } else {
            historyList.innerHTML = history.map(item => `
                <div class="history-item" 
                     onclick="selectHistoryItem('${item.batchId}')"
                     oncontextmenu="showHistoryContextMenu(event, '${item.batchId}', '${item.directoryName}'); return false;">
                    <div class="history-item-title">${item.directoryName}</div>
                    <div class="history-item-meta">
                        ${new Date(item.timestamp).toLocaleDateString()} • 
                        ${item.totalDocuments} docs • 
                        ${item.hierarchyDepth} levels
                    </div>
                </div>
            `).join('');
        }
    }

    getSummarizationHistory() {
        const stored = localStorage.getItem('hierarchical_summaries_history');
        return stored ? JSON.parse(stored) : [];
    }

    saveSummarizationToHistory(item) {
        const history = this.getSummarizationHistory();
        
        // Add to beginning of array (most recent first)
        history.unshift(item);
        
        // Keep only last 20 items
        if (history.length > 20) {
            history.pop();
        }
        
        localStorage.setItem('hierarchical_summaries_history', JSON.stringify(history));
        this.loadSummarizationHistory();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new DataComposeApp();
});

// App Menu Cabinet Functions
function toggleAppMenu() {
    const cabinet = document.getElementById('app-menu-cabinet');
    const overlay = document.getElementById('app-menu-overlay');
    
    cabinet.classList.toggle('show');
    overlay.classList.toggle('show');
}

function closeAppMenu() {
    const cabinet = document.getElementById('app-menu-cabinet');
    const overlay = document.getElementById('app-menu-overlay');
    
    cabinet.classList.remove('show');
    overlay.classList.remove('show');
}

// Close menu with escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAppMenu();
    }
});

// Global functions for backwards compatibility and inline handlers
function testConnection() {
    window.app.testN8nConnection();
}

// Removed handleRecursiveSummary - not needed for visualization-only mode

function sendMessage() {
    window.app.sendMessage();
}

// Removed processSimpleDirectory - not needed for visualization-only mode

// History Drawer Functions
window.toggleHistoryDrawer = function() {
    const drawer = document.getElementById('history-drawer');
    if (drawer) {
        drawer.classList.toggle('open');
    }
}

window.toggleChatHistoryDrawer = function() {
    const drawer = document.getElementById('chat-history-drawer');
    if (drawer) {
        drawer.classList.toggle('open');
    }
}

window.startNewChat = function() {
    if (window.app) {
        window.app.startNewChat();
    }
}

// Close drawer when clicking outside (optional enhancement)
document.addEventListener('click', function(event) {
    const drawer = document.getElementById('history-drawer');
    const toggleBtn = document.getElementById('history-toggle');
    const chatDrawer = document.getElementById('chat-history-drawer');
    const chatToggleBtn = document.getElementById('chat-history-toggle');
    
    // Check if click is outside history drawer and toggle button
    if (drawer && drawer.classList.contains('open') && 
        !drawer.contains(event.target) && 
        toggleBtn && !toggleBtn.contains(event.target)) {
        drawer.classList.remove('open');
    }
    
    // Check if click is outside chat history drawer and toggle button
    if (chatDrawer && chatDrawer.classList.contains('open') && 
        !chatDrawer.contains(event.target) && 
        chatToggleBtn && !chatToggleBtn.contains(event.target)) {
        chatDrawer.classList.remove('open');
    }
});

// Hierarchical Summarization Functions
async function startHierarchicalSummarization() {
    const directoryInput = document.getElementById('directory-name');
    const directoryName = directoryInput.value.trim();
    
    if (!directoryName) {
        alert('Please enter a directory name');
        return;
    }
    
    // Show processing status
    const statusDiv = document.getElementById('processing-status');
    const statusMessage = document.getElementById('status-message');
    statusDiv.classList.remove('hidden');
    statusMessage.textContent = 'Processing documents...';
    
    try {
        // Build the full path as expected by the container
        const directoryPath = `/files/uploads/${directoryName}`;
        
        // Get the selected hierarchical summarization mode
        const hsMode = document.querySelector('input[name="hs-mode"]:checked').value;
        const action = hsMode === 'local' ? 'hs_local' : 'hs_public';
        
        const response = await fetch(CONFIG.WEBHOOK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                directoryPath: directoryPath,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to process: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Summarization complete:', data);
        
        // Save to history
        const historyItem = {
            batchId: data.batchId,
            directoryPath: directoryPath,
            directoryName: directoryName,
            timestamp: new Date().toISOString(),
            totalDocuments: data.totalDocuments || 0,
            hierarchyDepth: data.hierarchyDepth || 0,
            finalSummary: data.finalSummary ? data.finalSummary.substring(0, 100) + '...' : ''
        };
        
        window.app.saveSummarizationToHistory(historyItem);
        
        // Show success message
        statusMessage.textContent = `✅ Processing complete! ${data.totalDocuments} documents processed.`;
        
        // Clear form
        directoryInput.value = '';
        
        // Automatically select the new item after a delay
        setTimeout(() => {
            selectHistoryItem(data.batchId);
        }, 1500);
        
    } catch (error) {
        console.error('Error processing:', error);
        statusMessage.textContent = `❌ Error: ${error.message}`;
    }
}

function selectHistoryItem(batchId) {
    // Update active state in sidebar
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Find and activate the selected item
    const selectedItem = document.querySelector(`.history-item[onclick*="${batchId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    // Hide form, show visualization
    document.getElementById('summarization-form').classList.add('hidden');
    document.getElementById('hierarchy-visualization').classList.remove('hidden');
    
    // Load the visualization
    showHierarchyVisualization(batchId);
}

function startNewSummarization() {
    // Clear any active history items
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Show form, hide visualization
    document.getElementById('summarization-form').classList.remove('hidden');
    document.getElementById('hierarchy-visualization').classList.add('hidden');
    
    // Clear the directory input
    document.getElementById('directory-name').value = '';
    
    // Close the history drawer if it's open
    document.getElementById('history-drawer').classList.remove('open');
}

// Context menu for history items
function showHistoryContextMenu(event, batchId, directoryName) {
    event.preventDefault();
    
    // Remove any existing context menu
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Create context menu
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.innerHTML = `
        <div class="context-menu-item" onclick="deleteHistoryItem('${batchId}', '${directoryName}')">
            <i class="fas fa-trash"></i> Delete
        </div>
    `;
    
    // Position the menu
    menu.style.left = event.pageX + 'px';
    menu.style.top = event.pageY + 'px';
    
    document.body.appendChild(menu);
    
    // Close menu when clicking elsewhere
    const closeMenu = () => {
        menu.remove();
        document.removeEventListener('click', closeMenu);
    };
    
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 100);
}

async function deleteHistoryItem(batchId, directoryName) {
    // Close any context menu
    const menu = document.querySelector('.context-menu');
    if (menu) menu.remove();
    
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the summarization for "${directoryName}"?`)) {
        return;
    }
    
    try {
        // Send delete action to n8n
        const response = await fetch(CONFIG.WEBHOOK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'delete_summarization',
                batchId: batchId,
                directoryName: directoryName,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to delete: ${response.status}`);
        }
        
        // Remove from local storage
        const history = window.app.getSummarizationHistory();
        const updatedHistory = history.filter(item => item.batchId !== batchId);
        localStorage.setItem('hierarchical_summaries_history', JSON.stringify(updatedHistory));
        
        // Reload history display
        window.app.loadSummarizationHistory();
        
        // If the deleted item was currently being viewed, show the form
        const currentVisualization = document.getElementById('hierarchy-visualization');
        if (!currentVisualization.classList.contains('hidden')) {
            // Check if we're viewing the deleted item
            const vizContainer = currentVisualization.querySelector('[data-batch-id]');
            if (vizContainer && vizContainer.dataset.batchId === batchId) {
                startNewSummarization();
            }
        }
        
    } catch (error) {
        console.error('Error deleting summarization:', error);
        alert('Failed to delete summarization: ' + error.message);
    }
}

// Hierarchy Visualization Functions
let currentDetailLevel = 'simple';

async function showHierarchyVisualization(batchId) {
    if (!batchId || batchId.trim() === '') {
        alert('Please enter a batch ID');
        return;
    }
    
    const vizContainer = document.getElementById('hierarchy-visualization');
    
    // Show the visualization container
    vizContainer.classList.remove('hidden');
    
    console.log('Starting hierarchy visualization for batch:', batchId);
    
    // Show loading state
    showLoadingState();
    
    try {
        // Fetch hierarchy data from n8n
        const response = await fetch(CONFIG.WEBHOOK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'get_summaries',
                batchId: batchId,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch hierarchy data: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Received data from webhook:', data);
        
        // Use actual data or mock for testing
        const hierarchyData = data.hierarchy || createMockHierarchy(batchId);
        
        // Validate hierarchy data structure
        if (hierarchyData && hierarchyData.levels && hierarchyData.documents) {
            console.log('Valid hierarchy data received:', hierarchyData);
            window.lastHierarchyData = hierarchyData;
            
            // Check if processing is complete
            if (data.processingStatus && data.processingStatus !== 'complete') {
                // Start polling for updates
                startProgressiveLoading(batchId, hierarchyData);
            } else {
                hideLoadingState();
                displayHierarchyTree(hierarchyData);
            }
        } else {
            console.warn('Invalid hierarchy data structure, using mock data');
            const mockData = createMockHierarchy(batchId);
            window.lastHierarchyData = mockData;
            hideLoadingState();
            displayHierarchyTree(mockData);
        }
        
    } catch (error) {
        console.error('Error fetching hierarchy:', error);
        hideLoadingState();
        // Display mock data for demonstration
        const mockData = createMockHierarchy(batchId);
        window.lastHierarchyData = mockData;
        displayHierarchyTree(mockData);
    }
}

// Progressive loading functionality
let pollingInterval = null;

function startProgressiveLoading(batchId, initialData) {
    // Display initial partial data
    displayHierarchyTree(initialData);
    
    // Show processing indicator
    showProcessingIndicator();
    
    // Poll for updates every 2 seconds
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(CONFIG.WEBHOOK_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'get_summaries',
                    batchId: batchId,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.hierarchy) {
                    window.lastHierarchyData = data.hierarchy;
                    updateVisualizationData(data.hierarchy);
                    
                    // Check if processing is complete
                    if (data.processingStatus === 'complete') {
                        stopProgressiveLoading();
                    }
                }
            }
        } catch (error) {
            console.error('Error polling for updates:', error);
        }
    }, 2000);
}

function stopProgressiveLoading() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    hideProcessingIndicator();
}

function showLoadingState() {
    const canvas = document.getElementById('tree-canvas');
    if (!document.getElementById('loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading hierarchy data...</p>
            </div>
        `;
        canvas.appendChild(overlay);
    }
}

function hideLoadingState() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showProcessingIndicator() {
    const canvas = document.getElementById('tree-canvas');
    if (!document.getElementById('processing-indicator')) {
        const indicator = document.createElement('div');
        indicator.id = 'processing-indicator';
        indicator.className = 'processing-indicator';
        indicator.innerHTML = `
            <i class="fas fa-sync fa-spin"></i>
            <span>Processing documents...</span>
        `;
        canvas.appendChild(indicator);
    }
}

function hideProcessingIndicator() {
    const indicator = document.getElementById('processing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Update visualization with new data without full redraw
function updateVisualizationData(newData) {
    // This would intelligently update only changed nodes
    // For now, we'll do a full redraw
    displayHierarchyTree(newData);
}

function createMockHierarchy(batchId) {
    // Comprehensive mock hierarchy for testing visualization
    return {
        batchId: batchId,
        levels: [
            { level: 0, count: 8, label: "Source Documents" },
            { level: 1, count: 4, label: "Initial Summaries" },
            { level: 2, count: 2, label: "Intermediate Summaries" },
            { level: 3, count: 1, label: "Final Summary" }
        ],
        documents: {
            0: [
                { id: 1, source: "chapter_1.txt", content: "Introduction to machine learning concepts and fundamental principles that guide artificial intelligence development...", child_ids: [9] },
                { id: 2, source: "chapter_2.txt", content: "Deep learning architectures including convolutional neural networks and their applications in computer vision...", child_ids: [9] },
                { id: 3, source: "chapter_3.txt", content: "Natural language processing techniques using transformer models and attention mechanisms for text understanding...", child_ids: [10] },
                { id: 4, source: "chapter_4.txt", content: "Reinforcement learning algorithms and their implementation in autonomous systems and game playing agents...", child_ids: [10] },
                { id: 5, source: "chapter_5.txt", content: "Ethics in AI development focusing on bias mitigation, fairness, and responsible deployment of AI systems...", child_ids: [11] },
                { id: 6, source: "chapter_6.txt", content: "Future directions in AI research including AGI, quantum computing applications, and neuromorphic computing...", child_ids: [11] },
                { id: 7, source: "chapter_7.txt", content: "Practical applications of AI in healthcare, finance, transportation, and industrial automation sectors...", child_ids: [12] },
                { id: 8, source: "chapter_8.txt", content: "Case studies of successful AI implementations and lessons learned from large-scale deployments...", child_ids: [12] }
            ],
            1: [
                { id: 9, parent_ids: [1, 2], summary: "Machine learning and deep learning form the foundation of modern AI, with CNNs revolutionizing computer vision tasks.", child_ids: [13] },
                { id: 10, parent_ids: [3, 4], summary: "NLP and reinforcement learning represent two major branches of AI, enabling language understanding and autonomous decision-making.", child_ids: [13] },
                { id: 11, parent_ids: [5, 6], summary: "Ethical AI development and future research directions are crucial for responsible advancement of artificial intelligence.", child_ids: [14] },
                { id: 12, parent_ids: [7, 8], summary: "Real-world AI applications demonstrate significant impact across industries with valuable implementation insights.", child_ids: [14] }
            ],
            2: [
                { id: 13, parent_ids: [9, 10], summary: "Core AI technologies encompass learning algorithms, language processing, and autonomous systems, forming the technical foundation of artificial intelligence.", child_ids: [15] },
                { id: 14, parent_ids: [11, 12], summary: "Responsible AI development requires ethical considerations while practical applications showcase transformative potential across sectors.", child_ids: [15] }
            ],
            3: [
                { id: 15, parent_ids: [13, 14], summary: "Artificial Intelligence represents a transformative technology combining advanced algorithms, ethical frameworks, and practical applications to solve complex problems across diverse domains, with ongoing research pushing boundaries toward more capable and responsible AI systems.", child_ids: [] }
            ]
        }
    };
}

// Global variables for visualization
let currentLevel = null;
let hierarchyData = null;
let currentTreeData = null;
let currentFocusedNode = null;
let navigationState = {
    currentLevel: null,
    visibleNodes: new Set()
};
let useStraightLines = false; // Toggle for line style

function displayHierarchyTree(hierarchy) {
    console.log('displayHierarchyTree called with:', hierarchy);
    hierarchyData = hierarchy;
    currentTreeData = hierarchy;
    
    // Initialize the new visualization
    initializeNewVisualization(hierarchy);
}

function getMaxLevel(hierarchy) {
    if (!hierarchy.levels) return 0;
    return Math.max(...hierarchy.levels.map(l => l.level));
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Store the last hierarchy data
window.lastHierarchyData = null;

// Initialize new visualization
function initializeNewVisualization(hierarchyData) {
    console.log('Initializing new visualization with data:', hierarchyData);
    navigationState.currentLevel = getMaxLevel(hierarchyData);
    
    // Load D3 if needed
    if (!window.d3) {
        console.log('Loading D3.js...');
        window.loadD3().then(() => {
            console.log('D3.js loaded, creating visualization');
            createBubbleVisualization(hierarchyData);
        }).catch(err => {
            console.error('Error loading D3:', err);
        });
    } else {
        console.log('D3 already loaded, creating visualization');
        createBubbleVisualization(hierarchyData);
    }
}

// Global zoom behavior
let globalZoom = null;

// Create the new bubble-style visualization
function createBubbleVisualization(hierarchyData) {
    console.log('Creating bubble visualization');
    const container = document.getElementById('tree-canvas');
    if (!container) {
        console.error('tree-canvas container not found!');
        return;
    }
    
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;
    console.log('Container dimensions:', width, height);
    
    if (width === 0 || height === 0) {
        console.error('Container has zero dimensions, using defaults');
    }
    
    const svg = d3.select('#hierarchy-svg');
    
    // Clear existing content
    svg.selectAll('*').remove();
    
    // Define arrow marker for link directionality
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 0 10 10')
        .attr('refX', 0)
        .attr('refY', 5)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M 0 0 L 10 5 L 0 10 z')
        .attr('fill', 'var(--border-color)');
    
    // Recreate the zoom group structure
    const zoomGroup = svg.append('g').attr('id', 'zoom-group');
    const linksGroup = zoomGroup.append('g').attr('id', 'links-group');
    const nodesGroup = zoomGroup.append('g').attr('id', 'nodes-group');
    
    // Create zoom behavior with debounced minimap update
    const debouncedMinimapUpdate = debounce(updateMinimapViewport, 100);
    
    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .on('zoom', (event) => {
            zoomGroup.attr('transform', event.transform);
            // Update minimap viewport when zooming/panning (debounced)
            debouncedMinimapUpdate();
        });
    
    svg.call(zoom);
    globalZoom = zoom; // Store for later use
    
    // Add touch gesture support
    let touches = [];
    let lastDistance = 0;
    let lastCenter = null;
    
    svg.on('touchstart', function(event) {
        event.preventDefault();
        touches = event.touches;
        
        if (touches.length === 2) {
            // Calculate initial distance for pinch
            const touch1 = touches[0];
            const touch2 = touches[1];
            lastDistance = Math.hypot(
                touch2.clientX - touch1.clientX,
                touch2.clientY - touch1.clientY
            );
            
            // Calculate center point for pan
            lastCenter = {
                x: (touch1.clientX + touch2.clientX) / 2,
                y: (touch1.clientY + touch2.clientY) / 2
            };
        }
    });
    
    svg.on('touchmove', function(event) {
        event.preventDefault();
        touches = event.touches;
        
        if (touches.length === 2) {
            const touch1 = touches[0];
            const touch2 = touches[1];
            
            // Calculate current distance
            const currentDistance = Math.hypot(
                touch2.clientX - touch1.clientX,
                touch2.clientY - touch1.clientY
            );
            
            // Calculate current center
            const currentCenter = {
                x: (touch1.clientX + touch2.clientX) / 2,
                y: (touch1.clientY + touch2.clientY) / 2
            };
            
            // Get current transform
            const transform = d3.zoomTransform(svg.node());
            
            // Calculate scale change (pinch)
            if (lastDistance > 0) {
                const scaleFactor = currentDistance / lastDistance;
                const newScale = Math.max(0.5, Math.min(3, transform.k * scaleFactor));
                
                // Calculate pan (two-finger swipe)
                const dx = currentCenter.x - lastCenter.x;
                const dy = currentCenter.y - lastCenter.y;
                
                // Apply new transform
                const newTransform = d3.zoomIdentity
                    .translate(transform.x + dx, transform.y + dy)
                    .scale(newScale);
                
                svg.call(zoom.transform, newTransform);
            }
            
            lastDistance = currentDistance;
            lastCenter = currentCenter;
        }
    });
    
    svg.on('touchend', function(event) {
        touches = event.touches;
        if (touches.length < 2) {
            lastDistance = 0;
            lastCenter = null;
        }
    });
    
    // Build flat node array from hierarchy
    const nodes = [];
    const nodeById = new Map();
    
    console.log('Processing hierarchy documents:', hierarchyData.documents);
    
    // Process each level
    Object.entries(hierarchyData.documents).forEach(([level, docs]) => {
        console.log(`Processing level ${level} with ${docs.length} documents`);
        docs.forEach(doc => {
            const node = {
                id: doc.id,
                level: parseInt(level),
                content: doc.summary || doc.content || 'No content',
                source: doc.source,
                parentIds: doc.parent_ids || [],
                childIds: doc.child_ids || [],
                x: 0,
                y: 0
            };
            nodes.push(node);
            nodeById.set(node.id, node);
        });
    });
    
    console.log(`Created ${nodes.length} nodes`);
    
    // Position nodes horizontally by level
    const levelWidth = 400;
    const nodeHeight = 200;
    const nodeSpacing = 50;
    
    // Group nodes by level
    const nodesByLevel = {};
    nodes.forEach(node => {
        if (!nodesByLevel[node.level]) {
            nodesByLevel[node.level] = [];
        }
        nodesByLevel[node.level].push(node);
    });
    
    // Position nodes (final summary on left, source docs on right)
    const maxLevel = getMaxLevel(hierarchyData);
    Object.entries(nodesByLevel).forEach(([level, levelNodes]) => {
        // Reverse the level positioning
        const levelX = (maxLevel - parseInt(level)) * levelWidth + 100;
        const totalHeight = levelNodes.length * (nodeHeight + nodeSpacing);
        const startY = (height - totalHeight) / 2;
        
        levelNodes.forEach((node, index) => {
            node.x = levelX;
            node.y = startY + index * (nodeHeight + nodeSpacing);
        });
    });
    
    // Store nodes globally for navigation
    window.visualizationNodes = nodes;
    
    // Create links
    const links = [];
    nodes.forEach(node => {
        node.childIds.forEach(childId => {
            const childNode = nodeById.get(childId);
            if (childNode) {
                links.push({ source: node, target: childNode });
            }
        });
    });
    
    // Draw links
    const linkGroup = d3.select('#links-group');
    linkGroup.selectAll('path')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'bubble-link')
        .attr('marker-end', 'url(#arrowhead)')
        .attr('d', d => {
            // Calculate node sizes for proper connection points
            const sourceWidth = 300 + (getMaxLevel(hierarchyData) - d.source.level) * 20;
            const sourceHeight = nodeHeight + (getMaxLevel(hierarchyData) - d.source.level) * 10;
            const targetWidth = 300 + (getMaxLevel(hierarchyData) - d.target.level) * 20;
            const targetHeight = nodeHeight + (getMaxLevel(hierarchyData) - d.target.level) * 10;
            
            // Start from right edge of source, end at left edge of target
            const startX = d.source.x + sourceWidth;
            const startY = d.source.y + sourceHeight / 2;
            const endX = d.target.x;
            const endY = d.target.y + targetHeight / 2;
            
            if (useStraightLines) {
                // Simple straight line
                return `M ${startX},${startY} L ${endX},${endY}`;
            } else {
                // Create a subtle S-curve for better readability
                const midX = (startX + endX) / 2;
                
                // Use a cubic bezier curve for smooth, readable connections
                return `M ${startX},${startY} 
                        C ${midX},${startY} 
                          ${midX},${endY} 
                          ${endX},${endY}`;
            }
        });
    
    // Draw nodes as bubbles
    const nodeGroup = d3.select('#nodes-group');
    console.log('Drawing nodes, nodeGroup:', nodeGroup.node());
    
    const nodeElements = nodeGroup.selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', d => `bubble-node level-${d.level}`)
        .attr('transform', d => `translate(${d.x},${d.y})`);
    
    console.log('Created node elements:', nodeElements.size());
    
    // Add bubble backgrounds with size based on level
    nodeElements.append('rect')
        .attr('class', 'bubble-bg')
        .attr('width', d => {
            // Make higher-level nodes slightly wider
            const baseWidth = 300;
            const levelBonus = (getMaxLevel(hierarchyData) - d.level) * 20;
            return baseWidth + levelBonus;
        })
        .attr('height', d => {
            // Make higher-level nodes slightly taller
            const baseHeight = nodeHeight;
            const levelBonus = (getMaxLevel(hierarchyData) - d.level) * 10;
            return baseHeight + levelBonus;
        })
        .attr('rx', 20)
        .attr('ry', 20);
    
    // Add scrollable content containers
    nodeElements.append('foreignObject')
        .attr('width', d => {
            const baseWidth = 300;
            const levelBonus = (getMaxLevel(hierarchyData) - d.level) * 20;
            return (baseWidth + levelBonus) - 20; // Subtract padding
        })
        .attr('height', d => {
            const baseHeight = nodeHeight;
            const levelBonus = (getMaxLevel(hierarchyData) - d.level) * 10;
            return (baseHeight + levelBonus) - 20; // Subtract padding
        })
        .attr('x', 10)
        .attr('y', 10)
        .append('xhtml:div')
        .attr('class', 'bubble-content')
        .style('width', '100%')
        .style('height', '100%')
        .style('overflow-y', 'auto')
        .style('padding', '10px')
        .html(d => {
            const levelInfo = hierarchyData.levels.find(l => l.level === d.level);
            const levelLabel = levelInfo ? levelInfo.label : `Level ${d.level}`;
            return `
                <div class="bubble-header">${levelLabel}</div>
                <div class="bubble-text">${escapeHtml(d.content)}</div>
            `;
        });
    
    // Add click handlers for focus
    nodeElements.on('click', function(event, d) {
        focusOnNode(d, svg, zoom, width, height, nodeHeight);
    });
    
    // Initial focus on final summary
    const finalSummary = nodes.find(n => n.level === maxLevel);
    if (finalSummary) {
        console.log('Focusing on final summary:', finalSummary);
        setTimeout(() => {
            focusOnNode(finalSummary, svg, zoom, width, height, nodeHeight);
        }, 100);
    } else {
        console.error('No final summary found!');
    }
    
    // Update navigation arrows and level indicator
    updateNavigationState(hierarchyData);
    
    // Create minimap
    createMinimap(nodes, links, width, height);
    
    console.log('Visualization creation complete');
}

// Create minimap for spatial navigation
function createMinimap(nodes, links, mainWidth, mainHeight) {
    const minimapContainer = document.getElementById('minimap-container');
    
    // Create minimap container if it doesn't exist
    if (!minimapContainer) {
        const container = document.createElement('div');
        container.id = 'minimap-container';
        container.className = 'minimap-container';
        container.innerHTML = `
            <div class="minimap-header">
                <span>Overview</span>
                <button class="minimap-toggle" onclick="toggleMinimap()">−</button>
            </div>
            <svg id="minimap-svg" width="200" height="150"></svg>
        `;
        document.getElementById('tree-canvas').appendChild(container);
    }
    
    const minimapSvg = d3.select('#minimap-svg');
    const minimapWidth = 200;
    const minimapHeight = 150;
    
    // Calculate bounding box of all nodes to show complete tree
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    nodes.forEach(node => {
        minX = Math.min(minX, node.x);
        minY = Math.min(minY, node.y);
        maxX = Math.max(maxX, node.x + 300); // Add node width
        maxY = Math.max(maxY, node.y + 200); // Add node height
    });
    
    // Calculate actual tree dimensions
    const treeWidth = maxX - minX;
    const treeHeight = maxY - minY;
    const treeCenterX = (minX + maxX) / 2;
    const treeCenterY = (minY + maxY) / 2;
    
    // Calculate scale to fit entire tree with padding
    const padding = 20;
    const scaleX = (minimapWidth - padding * 2) / treeWidth;
    const scaleY = (minimapHeight - padding * 2) / treeHeight;
    const scale = Math.min(scaleX, scaleY);
    
    // Store minimap scale globally for viewport updates
    window.minimapScale = scale;
    window.minimapTreeCenter = { x: treeCenterX, y: treeCenterY };
    
    // Clear existing content
    minimapSvg.selectAll('*').remove();
    
    // Create minimap group centered on tree
    const minimapGroup = minimapSvg.append('g')
        .attr('transform', `translate(${minimapWidth/2}, ${minimapHeight/2})`);
    
    // Draw minimap links
    minimapGroup.selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('x1', d => (d.source.x - treeCenterX) * scale)
        .attr('y1', d => (d.source.y - treeCenterY) * scale)
        .attr('x2', d => (d.target.x - treeCenterX) * scale)
        .attr('y2', d => (d.target.y - treeCenterY) * scale)
        .attr('stroke', '#ccc')
        .attr('stroke-width', 1);
    
    // Draw minimap nodes with level-based colors
    minimapGroup.selectAll('circle')
        .data(nodes)
        .enter()
        .append('circle')
        .attr('cx', d => (d.x - treeCenterX) * scale)
        .attr('cy', d => (d.y - treeCenterY) * scale)
        .attr('r', d => {
            // Larger dots for better visibility
            if (d.id === currentFocusedNode?.id) return 5;
            return d.level === getMaxLevel(hierarchyData) ? 4 : 3;
        })
        .attr('fill', d => {
            if (d.id === currentFocusedNode?.id) return '#ff6b6b';
            // Use level-based colors
            return `var(--level-${d.level}-border)`;
        })
        .attr('class', 'minimap-node')
        .style('cursor', 'pointer')
        .on('click', function(event, d) {
            // Navigate to clicked node
            const node = window.visualizationNodes.find(n => n.id === d.id);
            if (node) {
                focusOnNode(node, d3.select('#hierarchy-svg'), globalZoom,
                           mainWidth, mainHeight, 200);
            }
        });
    
    // Add viewport indicator
    const viewportIndicator = minimapGroup.append('rect')
        .attr('class', 'minimap-viewport')
        .attr('fill', 'rgba(52, 152, 219, 0.2)')
        .attr('stroke', '#3498db')
        .attr('stroke-width', 2);
    
    // Update viewport indicator on zoom/pan
    updateMinimapViewport();
}

// Update minimap viewport indicator
function updateMinimapViewport() {
    const transform = d3.zoomTransform(d3.select('#hierarchy-svg').node());
    const mainWidth = document.getElementById('tree-canvas').clientWidth;
    const mainHeight = document.getElementById('tree-canvas').clientHeight;
    
    // Use stored minimap scale and tree center
    const scale = window.minimapScale || 0.1;
    const treeCenter = window.minimapTreeCenter || { x: 0, y: 0 };
    
    const viewport = d3.select('.minimap-viewport');
    if (viewport.node()) {
        // Calculate visible area in tree coordinates
        const visibleWidth = mainWidth / transform.k;
        const visibleHeight = mainHeight / transform.k;
        
        // Calculate the center of the visible area in tree coordinates
        const visibleCenterX = -transform.x / transform.k + visibleWidth / 2;
        const visibleCenterY = -transform.y / transform.k + visibleHeight / 2;
        
        // Convert to minimap coordinates
        const viewportWidth = visibleWidth * scale;
        const viewportHeight = visibleHeight * scale;
        const viewportX = (visibleCenterX - treeCenter.x) * scale - viewportWidth / 2;
        const viewportY = (visibleCenterY - treeCenter.y) * scale - viewportHeight / 2;
        
        viewport
            .attr('x', viewportX)
            .attr('y', viewportY)
            .attr('width', viewportWidth)
            .attr('height', viewportHeight);
    }
}

// Toggle minimap visibility
function toggleMinimap() {
    const minimap = document.getElementById('minimap-container');
    minimap.classList.toggle('minimized');
    const toggleBtn = minimap.querySelector('.minimap-toggle');
    toggleBtn.textContent = minimap.classList.contains('minimized') ? '+' : '−';
}

// Focus on a specific node with smooth animation
function focusOnNode(node, svg, zoom, containerWidth, containerHeight, nodeHeight) {
    currentFocusedNode = node;
    
    // Calculate dynamic node height based on level
    const baseHeight = nodeHeight;
    const levelBonus = (getMaxLevel(currentTreeData) - node.level) * 10;
    const actualNodeHeight = baseHeight + levelBonus;
    
    // Calculate transform to center the node - increased zoom for better readability
    const scale = 2.0; // Increased from 1.2 to 2.0 for better visibility
    const nodeWidth = 300 + (getMaxLevel(currentTreeData) - node.level) * 20;
    
    // Calculate the center point of the node
    const nodeCenterX = node.x + nodeWidth / 2;
    const nodeCenterY = node.y + actualNodeHeight / 2;
    
    // Calculate translation to center the node in the viewport
    const x = containerWidth / 2 - nodeCenterX * scale;
    const y = containerHeight / 2 - nodeCenterY * scale;
    
    // Apply zoom transform with easing
    svg.transition()
        .duration(750)
        .ease(d3.easeCubicInOut)
        .call(
            zoom.transform,
            d3.zoomIdentity
                .translate(x, y)
                .scale(scale)
        );
    
    // Highlight focused node and show active path
    highlightActivePath(node);
    
    // Update level indicator with animation
    updateLevelIndicator(node.level);
    
    // Update breadcrumb navigation
    updateBreadcrumbNavigation(node);
    
    // Update navigation arrows
    updateNavigationArrows(node);
    
    // Update URL hash for bookmarking
    window.location.hash = `node-${node.id}`;
    
    // Update minimap to show current focus
    updateMinimapFocus(node);
}

// Update level indicator with smooth animation
function updateLevelIndicator(level) {
    document.querySelectorAll('.level-dot').forEach(dot => {
        const dotLevel = parseInt(dot.dataset.level);
        if (dotLevel === level) {
            dot.classList.add('active');
            // Pulse animation for active level
            dot.style.transform = 'scale(1.3)';
            setTimeout(() => {
                dot.style.transform = 'scale(1)';
            }, 300);
        } else {
            dot.classList.remove('active');
        }
    });
}

// Update navigation arrows based on current node
function updateNavigationArrows(node) {
    if (!currentTreeData || !currentTreeData.documents) return;
    
    const currentLevelDocs = currentTreeData.documents[node.level] || [];
    const currentIndex = currentLevelDocs.findIndex(doc => doc.id === node.id);
    
    // Check for navigation possibilities and get target nodes
    const hasLeft = node.level < getMaxLevel(currentTreeData);
    const hasRight = node.level > 0;
    const hasUp = currentIndex > 0;
    const hasDown = currentIndex < currentLevelDocs.length - 1;
    
    // Get target nodes for each direction
    let leftTarget = null, rightTarget = null, upTarget = null, downTarget = null;
    
    if (hasLeft) {
        const higherLevelDocs = currentTreeData.documents[node.level + 1] || [];
        // Find child nodes
        leftTarget = higherLevelDocs.find(doc => 
            doc.parent_ids && doc.parent_ids.includes(node.id)
        );
        
        // If no direct child found, try to find via childIds
        if (!leftTarget && node.childIds && node.childIds.length > 0) {
            leftTarget = higherLevelDocs.find(doc => 
                node.childIds.includes(doc.id)
            );
        }
        
        // Only fall back if no connection
        if (!leftTarget) {
            leftTarget = higherLevelDocs[0];
        }
    }
    
    if (hasRight) {
        const lowerLevelDocs = currentTreeData.documents[node.level - 1] || [];
        
        // First try to find nodes that list current node as their child
        rightTarget = lowerLevelDocs.find(doc => 
            doc.child_ids && doc.child_ids.includes(node.id)
        );
        
        // If not found, try using parentIds
        if (!rightTarget && node.parentIds && node.parentIds.length > 0) {
            rightTarget = lowerLevelDocs.find(doc => 
                node.parentIds.includes(doc.id)
            );
        }
        
        // Only fall back if no connection
        if (!rightTarget && lowerLevelDocs.length > 0) {
            rightTarget = lowerLevelDocs[0];
        }
    }
    
    if (hasUp) {
        upTarget = currentLevelDocs[currentIndex - 1];
    }
    
    if (hasDown) {
        downTarget = currentLevelDocs[currentIndex + 1];
    }
    
    // Update arrows with tooltips
    updateArrowWithTooltip('.nav-arrow-left', hasLeft, leftTarget, 'left');
    updateArrowWithTooltip('.nav-arrow-right', hasRight, rightTarget, 'right');
    updateArrowWithTooltip('.nav-arrow-up', hasUp, upTarget, 'up');
    updateArrowWithTooltip('.nav-arrow-down', hasDown, downTarget, 'down');
}

// Update individual arrow with tooltip
function updateArrowWithTooltip(selector, visible, targetNode, direction) {
    const arrow = document.querySelector(selector);
    const tooltip = arrow.querySelector('.nav-arrow-tooltip');
    
    arrow.style.display = visible ? 'flex' : 'none';
    
    if (visible && targetNode) {
        // Set tooltip content
        const levelInfo = currentTreeData.levels.find(l => l.level === targetNode.level);
        const label = levelInfo ? levelInfo.label : `Level ${targetNode.level}`;
        const preview = (targetNode.summary || targetNode.content || '').substring(0, 50);
        tooltip.textContent = `${label}: ${preview}${preview.length >= 50 ? '...' : ''}`;
        
        // Add hover listeners
        arrow.onmouseenter = () => tooltip.classList.add('visible');
        arrow.onmouseleave = () => tooltip.classList.remove('visible');
    }
}

// Update general navigation state
function updateNavigationState(hierarchyData) {
    // Set up click handlers for navigation arrows
    setupNavigationHandlers();
}

// Setup navigation handlers including keyboard support
function setupNavigationHandlers() {
    // Remove existing handlers
    document.querySelectorAll('.nav-arrow').forEach(arrow => {
        arrow.replaceWith(arrow.cloneNode(true));
    });
    
    // Add arrow click handlers
    document.querySelector('.nav-arrow-left')?.addEventListener('click', () => navigateDirection('left'));
    document.querySelector('.nav-arrow-right')?.addEventListener('click', () => navigateDirection('right'));
    document.querySelector('.nav-arrow-up')?.addEventListener('click', () => navigateDirection('up'));
    document.querySelector('.nav-arrow-down')?.addEventListener('click', () => navigateDirection('down'));
    
    // Add keyboard navigation
    document.removeEventListener('keydown', handleKeyboardNavigation);
    document.addEventListener('keydown', handleKeyboardNavigation);
}

// Handle keyboard navigation
function handleKeyboardNavigation(event) {
    // Only handle if visualization is active
    if (!document.getElementById('hierarchy-visualization').classList.contains('hidden')) {
        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                navigateDirection('left');
                break;
            case 'ArrowRight':
                event.preventDefault();
                navigateDirection('right');
                break;
            case 'ArrowUp':
                event.preventDefault();
                navigateDirection('up');
                break;
            case 'ArrowDown':
                event.preventDefault();
                navigateDirection('down');
                break;
            case 'Home':
                event.preventDefault();
                navigateToFinalSummary();
                break;
            case 'End':
                event.preventDefault();
                navigateToSourceDocs();
                break;
            case '/':
                if (event.ctrlKey || event.metaKey) {
                    event.preventDefault();
                    showSearchDialog();
                }
                break;
        }
    }
}

// Navigate in a specific direction
function navigateDirection(direction) {
    if (!currentFocusedNode || !currentTreeData) return;
    
    const currentLevelDocs = currentTreeData.documents[currentFocusedNode.level] || [];
    const currentIndex = currentLevelDocs.findIndex(doc => doc.id === currentFocusedNode.id);
    let targetNode = null;
    
    switch(direction) {
        case 'left': // Go to higher level (toward final summary)
            if (currentFocusedNode.level < getMaxLevel(currentTreeData)) {
                const higherLevelDocs = currentTreeData.documents[currentFocusedNode.level + 1] || [];
                if (higherLevelDocs.length > 0) {
                    // Find child nodes that have this node as a parent
                    targetNode = higherLevelDocs.find(doc => 
                        doc.parent_ids && doc.parent_ids.includes(currentFocusedNode.id)
                    );
                    
                    // If no direct child found, try to find via childIds
                    if (!targetNode && currentFocusedNode.childIds && currentFocusedNode.childIds.length > 0) {
                        targetNode = higherLevelDocs.find(doc => 
                            currentFocusedNode.childIds.includes(doc.id)
                        );
                    }
                    
                    // Only fall back to first node if no connection exists
                    if (!targetNode) {
                        targetNode = higherLevelDocs[0];
                    }
                }
            }
            break;
            
        case 'right': // Go to lower level (toward source documents)
            if (currentFocusedNode.level > 0) {
                const lowerLevelDocs = currentTreeData.documents[currentFocusedNode.level - 1] || [];
                
                // First try to find nodes that list current node as their child
                targetNode = lowerLevelDocs.find(doc => 
                    doc.child_ids && doc.child_ids.includes(currentFocusedNode.id)
                );
                
                // If not found, try using parentIds
                if (!targetNode && currentFocusedNode.parentIds && currentFocusedNode.parentIds.length > 0) {
                    targetNode = lowerLevelDocs.find(doc => 
                        currentFocusedNode.parentIds.includes(doc.id)
                    );
                }
                
                // Only fall back to first node if no connection exists
                if (!targetNode && lowerLevelDocs.length > 0) {
                    targetNode = lowerLevelDocs[0];
                }
            }
            break;
            
        case 'up': // Go to previous document at same level
            if (currentIndex > 0) {
                targetNode = currentLevelDocs[currentIndex - 1];
            }
            break;
            
        case 'down': // Go to next document at same level
            if (currentIndex < currentLevelDocs.length - 1) {
                targetNode = currentLevelDocs[currentIndex + 1];
            }
            break;
    }
    
    if (targetNode && window.visualizationNodes) {
        // Find the node in our stored nodes array
        const nodeToFocus = window.visualizationNodes.find(n => n.id === targetNode.id);
        if (nodeToFocus) {
            const svg = d3.select('#hierarchy-svg');
            const container = document.getElementById('tree-canvas');
            focusOnNode(nodeToFocus, svg, globalZoom, container.clientWidth, container.clientHeight, 200);
        }
    }
}

// Navigate to final summary (highest level)
function navigateToFinalSummary() {
    if (!currentTreeData || !window.visualizationNodes) return;
    
    const maxLevel = getMaxLevel(currentTreeData);
    const finalNode = window.visualizationNodes.find(n => n.level === maxLevel);
    
    if (finalNode) {
        focusOnNode(finalNode, d3.select('#hierarchy-svg'), globalZoom,
                   document.getElementById('tree-canvas').clientWidth,
                   document.getElementById('tree-canvas').clientHeight,
                   200);
    }
}

// Navigate to source documents (level 0)
function navigateToSourceDocs() {
    if (!window.visualizationNodes) return;
    
    const sourceNodes = window.visualizationNodes.filter(n => n.level === 0);
    if (sourceNodes.length > 0) {
        focusOnNode(sourceNodes[0], d3.select('#hierarchy-svg'), globalZoom,
                   document.getElementById('tree-canvas').clientWidth,
                   document.getElementById('tree-canvas').clientHeight,
                   200);
    }
}

// Get all nodes from hierarchy data
function getAllNodesFromHierarchy(hierarchyData) {
    const nodes = [];
    Object.entries(hierarchyData.documents).forEach(([level, docs]) => {
        docs.forEach(doc => {
            nodes.push({
                id: doc.id,
                level: parseInt(level),
                content: doc.summary || doc.content || 'No content',
                source: doc.source,
                parentIds: doc.parent_ids || [],
                childIds: doc.child_ids || [],
                x: doc.x || 0,
                y: doc.y || 0
            });
        });
    });
    return nodes;
}

// Search functionality for hierarchy visualization
function showSearchDialog() {
    // Check if search dialog already exists
    let searchDialog = document.getElementById('hierarchy-search-dialog');
    
    if (!searchDialog) {
        // Create search dialog
        searchDialog = document.createElement('div');
        searchDialog.id = 'hierarchy-search-dialog';
        searchDialog.className = 'search-dialog';
        searchDialog.innerHTML = `
            <div class="search-dialog-content">
                <h3>Search Hierarchy</h3>
                <input type="text" id="hierarchy-search-input" 
                       placeholder="Search for text in documents..." 
                       class="search-input">
                <div id="search-results" class="search-results"></div>
                <button class="btn btn-secondary" onclick="closeSearchDialog()">Close</button>
            </div>
        `;
        document.body.appendChild(searchDialog);
        
        // Add search event listener
        const searchInput = document.getElementById('hierarchy-search-input');
        searchInput.addEventListener('input', debounce(performSearch, 300));
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeSearchDialog();
        });
    }
    
    // Show dialog and focus input
    searchDialog.style.display = 'flex';
    document.getElementById('hierarchy-search-input').focus();
}

function closeSearchDialog() {
    const dialog = document.getElementById('hierarchy-search-dialog');
    if (dialog) {
        dialog.style.display = 'none';
        // Clear search highlights
        d3.selectAll('.bubble-node').classed('search-match', false);
    }
}

function performSearch() {
    const searchTerm = document.getElementById('hierarchy-search-input').value.toLowerCase();
    const resultsContainer = document.getElementById('search-results');
    
    if (!searchTerm || !window.visualizationNodes) {
        resultsContainer.innerHTML = '';
        return;
    }
    
    // Search through all nodes
    const matches = window.visualizationNodes.filter(node => 
        node.content.toLowerCase().includes(searchTerm) ||
        (node.source && node.source.toLowerCase().includes(searchTerm))
    );
    
    // Update visualization to highlight matches
    d3.selectAll('.bubble-node')
        .classed('search-match', d => matches.some(m => m.id === d.id));
    
    // Display results
    if (matches.length === 0) {
        resultsContainer.innerHTML = '<p>No matches found</p>';
    } else {
        resultsContainer.innerHTML = `
            <p>${matches.length} match${matches.length > 1 ? 'es' : ''} found</p>
            ${matches.map(node => `
                <div class="search-result-item" onclick="focusOnSearchResult(${node.id})">
                    <span class="result-level">Level ${node.level}</span>
                    <span class="result-text">${highlightSearchTerm(node.content, searchTerm)}</span>
                </div>
            `).join('')}
        `;
    }
}

function focusOnSearchResult(nodeId) {
    const node = window.visualizationNodes.find(n => n.id === nodeId);
    if (node) {
        const svg = d3.select('#hierarchy-svg');
        const container = document.getElementById('tree-canvas');
        focusOnNode(node, svg, globalZoom, container.clientWidth, container.clientHeight, 200);
        closeSearchDialog();
    }
}

function highlightSearchTerm(text, searchTerm) {
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const lowerText = text.toLowerCase();
    const lowerSearch = searchTerm.toLowerCase();
    
    // Find the position of the search term
    const matchIndex = lowerText.indexOf(lowerSearch);
    
    if (matchIndex === -1) {
        // No match found, return excerpt from beginning
        const excerpt = text.substring(0, 150);
        return excerpt + (text.length > 150 ? '...' : '');
    }
    
    // Calculate context window around the match
    const contextBefore = 50;
    const contextAfter = 100;
    const startIndex = Math.max(0, matchIndex - contextBefore);
    const endIndex = Math.min(text.length, matchIndex + searchTerm.length + contextAfter);
    
    // Extract context with ellipsis if needed
    let excerpt = '';
    if (startIndex > 0) excerpt += '...';
    excerpt += text.substring(startIndex, endIndex);
    if (endIndex < text.length) excerpt += '...';
    
    // Highlight the search term
    return excerpt.replace(regex, '<mark>$1</mark>');
}

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Toggle keyboard help visibility
function toggleKeyboardHelp() {
    const helpContent = document.querySelector('.help-content');
    if (helpContent) {
        helpContent.classList.toggle('hidden');
    }
}

// Highlight the active path from current node to final summary
function highlightActivePath(focusedNode) {
    // Clear previous highlighting
    d3.selectAll('.bubble-node').classed('in-active-path', false);
    d3.selectAll('.bubble-link').classed('in-active-path', false);
    
    // Highlight focused node with animation
    d3.selectAll('.bubble-node')
        .transition()
        .duration(300)
        .style('opacity', d => d.id === focusedNode.id ? 1 : 0.6);
    
    // Build path from current node to final summary
    const pathNodes = new Set([focusedNode.id]);
    let currentNode = focusedNode;
    
    // Traverse up to final summary
    while (currentNode && currentNode.childIds && currentNode.childIds.length > 0) {
        const childId = currentNode.childIds[0]; // Follow first child
        const childNode = window.visualizationNodes.find(n => n.id === childId);
        if (childNode) {
            pathNodes.add(childNode.id);
            currentNode = childNode;
        } else {
            break;
        }
    }
    
    // Traverse down to source if applicable
    currentNode = focusedNode;
    while (currentNode && currentNode.parentIds && currentNode.parentIds.length > 0) {
        const parentId = currentNode.parentIds[0]; // Follow first parent
        const parentNode = window.visualizationNodes.find(n => n.id === parentId);
        if (parentNode) {
            pathNodes.add(parentNode.id);
            currentNode = parentNode;
        } else {
            break;
        }
    }
    
    // Apply highlighting to nodes in path
    d3.selectAll('.bubble-node')
        .classed('in-active-path', d => pathNodes.has(d.id));
    
    // Highlight links in path
    d3.selectAll('.bubble-link')
        .classed('in-active-path', d => 
            pathNodes.has(d.source.id) && pathNodes.has(d.target.id)
        );
}

// Update minimap to show current focus
function updateMinimapFocus(node) {
    // Update minimap nodes to show focus
    d3.select('#minimap-svg').selectAll('circle')
        .transition()
        .duration(300)
        .attr('r', d => d.id === node.id ? 6 : 2)
        .attr('fill', d => {
            if (d.id === node.id) return '#ff6b6b';
            if (d.level === getMaxLevel(currentTreeData)) return '#4ecdc4';
            return `var(--level-${d.level}-border)`;
        });
}

// Update breadcrumb navigation
function updateBreadcrumbNavigation(currentNode) {
    const breadcrumbTrail = document.querySelector('.breadcrumb-trail');
    if (!breadcrumbTrail) return;
    
    // Build path from final summary to current node
    const path = [];
    let node = currentNode;
    
    // Add current node
    path.unshift(node);
    
    // Traverse up to final summary
    while (node && node.childIds && node.childIds.length > 0) {
        const childId = node.childIds[0];
        const childNode = window.visualizationNodes.find(n => n.id === childId);
        if (childNode) {
            path.push(childNode);
            node = childNode;
        } else {
            break;
        }
    }
    
    // Create breadcrumb HTML
    const breadcrumbHTML = path.map((n, index) => {
        const isActive = n.id === currentNode.id;
        const levelInfo = currentTreeData.levels.find(l => l.level === n.level);
        const label = levelInfo ? levelInfo.label : `Level ${n.level}`;
        const preview = n.content.substring(0, 50) + (n.content.length > 50 ? '...' : '');
        
        return `
            <span class="breadcrumb-item level-${n.level} ${isActive ? 'active' : ''}" 
                  onclick="navigateToBreadcrumbNode(${n.id})"
                  title="${escapeHtml(preview)}">
                ${label}
            </span>
            ${index < path.length - 1 ? '<span class="breadcrumb-separator">→</span>' : ''}
        `;
    }).join('');
    
    breadcrumbTrail.innerHTML = breadcrumbHTML;
}

// Navigate to a node from breadcrumb
function navigateToBreadcrumbNode(nodeId) {
    const node = window.visualizationNodes.find(n => n.id === nodeId);
    if (node) {
        const svg = d3.select('#hierarchy-svg');
        const container = document.getElementById('tree-canvas');
        focusOnNode(node, svg, globalZoom, container.clientWidth, container.clientHeight, 200);
    }
}

// Toggle quick jump menu
function toggleQuickJump() {
    const menu = document.querySelector('.quick-jump-menu');
    menu.classList.toggle('hidden');
    
    // Populate the dropdown if it's being shown
    if (!menu.classList.contains('hidden')) {
        populateQuickJumpSelect();
    }
}

// Populate quick jump select with all nodes
function populateQuickJumpSelect() {
    const select = document.getElementById('quick-jump-select');
    if (!window.visualizationNodes || !currentTreeData) return;
    
    // Clear existing options
    select.innerHTML = '<option value="">Select a node...</option>';
    
    // Group nodes by level
    const nodesByLevel = {};
    window.visualizationNodes.forEach(node => {
        if (!nodesByLevel[node.level]) {
            nodesByLevel[node.level] = [];
        }
        nodesByLevel[node.level].push(node);
    });
    
    // Add options grouped by level
    Object.keys(nodesByLevel).sort((a, b) => b - a).forEach(level => {
        const levelInfo = currentTreeData.levels.find(l => l.level === parseInt(level));
        const levelLabel = levelInfo ? levelInfo.label : `Level ${level}`;
        
        // Add optgroup for this level
        const optgroup = document.createElement('optgroup');
        optgroup.label = levelLabel;
        
        nodesByLevel[level].forEach(node => {
            const option = document.createElement('option');
            option.value = node.id;
            const preview = (node.content || '').substring(0, 60);
            option.textContent = `${node.source || 'Node ' + node.id}: ${preview}${preview.length >= 60 ? '...' : ''}`;
            optgroup.appendChild(option);
        });
        
        select.appendChild(optgroup);
    });
}

// Quick jump to selected node
function quickJumpToNode(nodeId) {
    if (!nodeId) return;
    
    const node = window.visualizationNodes.find(n => n.id === parseInt(nodeId));
    if (node) {
        const svg = d3.select('#hierarchy-svg');
        const container = document.getElementById('tree-canvas');
        focusOnNode(node, svg, globalZoom, container.clientWidth, container.clientHeight, 200);
        
        // Close the menu
        document.querySelector('.quick-jump-menu').classList.add('hidden');
    }
}

// Toggle between straight and curved lines
function toggleLineStyle() {
    useStraightLines = !useStraightLines;
    
    // Update all existing links
    d3.selectAll('.bubble-link')
        .transition()
        .duration(300)
        .attr('d', d => {
            // Recalculate the path with new style
            const sourceWidth = 300 + (getMaxLevel(hierarchyData) - d.source.level) * 20;
            const sourceHeight = 200 + (getMaxLevel(hierarchyData) - d.source.level) * 10;
            const targetHeight = 200 + (getMaxLevel(hierarchyData) - d.target.level) * 10;
            
            const startX = d.source.x + sourceWidth;
            const startY = d.source.y + sourceHeight / 2;
            const endX = d.target.x;
            const endY = d.target.y + targetHeight / 2;
            
            if (useStraightLines) {
                return `M ${startX},${startY} L ${endX},${endY}`;
            } else {
                const midX = (startX + endX) / 2;
                return `M ${startX},${startY} 
                        C ${midX},${startY} 
                          ${midX},${endY} 
                          ${endX},${endY}`;
            }
        });
    
    // Update button appearance
    const btn = document.querySelector('.line-style-btn');
    if (btn) {
        btn.style.background = useStraightLines ? 'var(--primary-color)' : 'var(--white)';
        btn.style.color = useStraightLines ? 'var(--white)' : 'var(--primary-color)';
    }
}

// Example of how to add new sections dynamically:
// window.app.addSection('settings', 'Settings', 'fas fa-cog', 
//     '<h2>Settings</h2><p>Configuration options...</p>',
//     { onShow: () => console.log('Settings shown') }
// );

// Developer Dashboard Functions
async function checkAllServices() {
    // Update last checked time
    document.getElementById('last-updated').textContent = new Date().toLocaleString();
    
    // Check n8n
    checkService('/n8n/healthz', 'n8n-status', 'n8n Workflow Engine');
    
    // Check PostgreSQL (through n8n's database connection)
    checkService('/n8n/rest/workflows', 'db-status', 'PostgreSQL Database');
    
    // Check Haystack/Elasticsearch
    checkService('http://localhost:8000/health', 'haystack-status', 'Haystack/Elasticsearch', true);
    
    // Check Lawyer Chat
    checkService('/chat', 'lawyer-chat-status', 'Lawyer Chat');
}

async function checkService(url, statusId, serviceName, isExternal = false) {
    const statusElement = document.getElementById(statusId);
    if (!statusElement) return;
    
    // Show checking status
    statusElement.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Checking...';
    statusElement.className = 'service-status checking';
    
    try {
        const response = await fetch(url, {
            method: 'GET',
            mode: isExternal ? 'no-cors' : 'same-origin',
            cache: 'no-cache'
        });
        
        // For no-cors requests, we can't read the response but no error means it's likely up
        if (isExternal || response.ok) {
            statusElement.innerHTML = '<i class="fas fa-check-circle"></i> Online';
            statusElement.className = 'service-status online';
        } else {
            statusElement.innerHTML = '<i class="fas fa-times-circle"></i> Offline';
            statusElement.className = 'service-status offline';
        }
    } catch (error) {
        statusElement.innerHTML = '<i class="fas fa-times-circle"></i> Offline';
        statusElement.className = 'service-status offline';
    }
}

function viewLogs() {
    const service = document.getElementById('log-service').value;
    const logViewer = document.getElementById('log-viewer');
    const logContent = document.getElementById('log-content');
    
    if (!service) {
        alert('Please select a service to view logs');
        return;
    }
    
    // Show log viewer
    logViewer.classList.remove('hidden');
    logContent.textContent = `Fetching ${service} logs...\n\nNote: In production, this would connect to your logging infrastructure.\nFor now, you can view logs using:\n\ndocker-compose logs ${service}`;
}

function showDoc(docType) {
    const docs = {
        setup: 'Setup documentation would be displayed here.\nSee README.md for setup instructions.',
        api: 'API documentation would be displayed here.\nVisit http://localhost:8000/docs for Haystack API.',
        troubleshooting: 'Troubleshooting guide would be displayed here.\nCheck CLAUDE.md for common issues.'
    };
    
    alert(docs[docType] || 'Documentation not found');
}

function clearCache() {
    if (confirm('Are you sure you want to clear the application cache?')) {
        // Clear localStorage
        localStorage.clear();
        // Clear sessionStorage
        sessionStorage.clear();
        // Clear cookies (limited to same domain)
        document.cookie.split(";").forEach(function(c) { 
            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
        });
        alert('Cache cleared successfully!');
    }
}

function exportConfig() {
    const config = {
        webhookId: CONFIG.WEBHOOK_ID,
        services: {
            n8n: 'http://localhost:5678',
            haystack: 'http://localhost:8000',
            elasticsearch: 'http://localhost:9200',
            aiPortal: 'http://localhost:8085'
        },
        environment: 'development',
        exportDate: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aletheia-config-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function restartServices() {
    if (confirm('Are you sure you want to restart all services? This will temporarily interrupt service availability.')) {
        alert('Service restart command would be executed here.\n\nTo manually restart services, run:\ndocker-compose restart');
    }
}

// Run service check when dashboard is shown
document.addEventListener('DOMContentLoaded', () => {
    // Add event listener for developer dashboard section
    const originalShowSection = window.app.showSection;
    window.app.showSection = function(sectionName) {
        originalShowSection.call(this, sectionName);
        if (sectionName === 'developer-dashboard') {
            checkAllServices();
        }
    };
});
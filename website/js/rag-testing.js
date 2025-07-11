/**
 * RAG Testing Module for Haystack Service
 * Provides comprehensive testing interface for the RAG-only Haystack service
 */

class RAGTestingManager {
    constructor() {
        this.baseUrl = 'http://localhost:8000';
        this.documentIds = [];
        this.searchResults = [];
        this.serviceStatus = null;
        this.dashboardMode = false; // Flag to indicate if running in dashboard
    }

    /**
     * Get element ID based on dashboard mode
     */
    getElementId(baseId) {
        return this.dashboardMode ? `dashboard-${baseId}` : baseId;
    }

    /**
     * Initialize the RAG testing interface
     */
    async initialize() {
        console.log('Initializing RAG Testing Manager...', this.dashboardMode ? '(Dashboard Mode)' : '(Standalone Mode)');
        
        // Check service health on load
        await this.checkServiceHealth();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load any stored document IDs
        this.loadStoredDocumentIds();
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Document ingestion form
        const ingestForm = document.getElementById(this.getElementId('rag-ingest-form'));
        if (ingestForm) {
            ingestForm.addEventListener('submit', (e) => this.handleIngestSubmit(e));
        }

        // Add metadata field button
        const addMetadataBtn = document.getElementById(this.getElementId('add-metadata-field'));
        if (addMetadataBtn) {
            addMetadataBtn.addEventListener('click', () => this.addMetadataField());
        }

        // Search form
        const searchForm = document.getElementById(this.getElementId('rag-search-form'));
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => this.handleSearchSubmit(e));
        }

        // Document lookup
        const lookupBtn = document.getElementById(this.getElementId('lookup-document'));
        if (lookupBtn) {
            lookupBtn.addEventListener('click', () => this.lookupDocument());
        }

        // Clear results button
        const clearBtn = document.getElementById(this.getElementId('clear-results'));
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearResults());
        }
    }

    /**
     * Check service health and update UI
     */
    async checkServiceHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            this.serviceStatus = await response.json();
            this.updateHealthDisplay();
        } catch (error) {
            console.error('Health check failed:', error);
            this.updateHealthDisplay(error);
        }
    }

    /**
     * Update health status display
     */
    updateHealthDisplay(error = null) {
        const statusEl = document.getElementById(this.getElementId('rag-service-status'));
        if (!statusEl) return;

        if (error) {
            statusEl.innerHTML = `
                <div class="status-indicator status-error">
                    <i class="fas fa-exclamation-circle"></i>
                    Service Unavailable
                </div>
                <div class="error-message">${error.message}</div>
            `;
            return;
        }

        const status = this.serviceStatus;
        const isHealthy = status.status === 'healthy';
        
        statusEl.innerHTML = `
            <div class="status-indicator ${isHealthy ? 'status-healthy' : 'status-unhealthy'}">
                <i class="fas fa-${isHealthy ? 'check-circle' : 'times-circle'}"></i>
                ${status.status.toUpperCase()}
            </div>
            <div class="status-details">
                <div><strong>Mode:</strong> ${status.features.mode}</div>
                <div><strong>Elasticsearch:</strong> ${status.elasticsearch}</div>
                <div><strong>Model:</strong> ${status.embedding_model}</div>
                <div><strong>Index:</strong> ${status.index}</div>
            </div>
            <div class="feature-grid">
                ${Object.entries(status.features)
                    .filter(([key]) => key !== 'mode')
                    .map(([feature, enabled]) => `
                        <div class="feature-item ${enabled ? 'enabled' : 'disabled'}">
                            <i class="fas fa-${enabled ? 'check' : 'times'}"></i>
                            ${this.formatFeatureName(feature)}
                        </div>
                    `).join('')}
            </div>
        `;
    }

    /**
     * Format feature name for display
     */
    formatFeatureName(feature) {
        return feature.replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Handle document ingestion form submission
     */
    async handleIngestSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Ingesting...';
            
            // Collect form data
            const content = form.querySelector('#' + this.getElementId('doc-content')).value;
            const metadata = this.collectMetadata();
            
            // Prepare documents array
            const documents = [{
                content: content,
                metadata: metadata
            }];
            
            // Send ingestion request
            const response = await fetch(`${this.baseUrl}/ingest`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(documents)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            // Store document IDs
            this.documentIds.push(...result.document_ids);
            this.saveDocumentIds();
            
            // Show success message
            this.showIngestSuccess(result);
            
            // Reset form
            form.reset();
            this.resetMetadataFields();
            
        } catch (error) {
            console.error('Ingestion failed:', error);
            this.showError('ingest-results', `Ingestion failed: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    /**
     * Collect metadata from dynamic fields
     */
    collectMetadata() {
        const metadata = {};
        const fields = document.querySelectorAll('.metadata-field');
        
        fields.forEach(field => {
            const key = field.querySelector('.metadata-key').value.trim();
            const value = field.querySelector('.metadata-value').value.trim();
            if (key && value) {
                metadata[key] = value;
            }
        });
        
        return metadata;
    }

    /**
     * Add a new metadata field
     */
    addMetadataField() {
        const container = document.getElementById(this.getElementId('metadata-fields'));
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'metadata-field';
        fieldDiv.innerHTML = `
            <input type="text" class="metadata-key" placeholder="Key (e.g., source)">
            <input type="text" class="metadata-value" placeholder="Value (e.g., legal_doc)">
            <button type="button" class="remove-metadata" onclick="ragTesting.removeMetadataField(this)">
                <i class="fas fa-times"></i>
            </button>
        `;
        container.appendChild(fieldDiv);
    }

    /**
     * Remove a metadata field
     */
    removeMetadataField(button) {
        button.closest('.metadata-field').remove();
    }

    /**
     * Reset metadata fields to default
     */
    resetMetadataFields() {
        const container = document.getElementById(this.getElementId('metadata-fields'));
        container.innerHTML = `
            <div class="metadata-field">
                <input type="text" class="metadata-key" placeholder="Key (e.g., source)">
                <input type="text" class="metadata-value" placeholder="Value (e.g., legal_doc)">
                <button type="button" class="remove-metadata" onclick="ragTesting.removeMetadataField(this)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }

    /**
     * Show ingestion success message
     */
    showIngestSuccess(result) {
        const resultsEl = document.getElementById(this.getElementId('ingest-results'));
        resultsEl.innerHTML = `
            <div class="success-message">
                <i class="fas fa-check-circle"></i>
                Successfully ingested ${result.documents_processed} document(s)
            </div>
            <div class="document-ids">
                <strong>Document IDs:</strong>
                <ul>
                    ${result.document_ids.map(id => `
                        <li>
                            <code>${id}</code>
                            <button class="copy-btn" onclick="ragTesting.copyToClipboard('${id}')">
                                <i class="fas fa-copy"></i>
                            </button>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    /**
     * Handle search form submission
     */
    async handleSearchSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
            
            // Collect search parameters
            const searchParams = {
                query: form.querySelector('#' + this.getElementId('search-query')).value,
                top_k: parseInt(form.querySelector('#' + this.getElementId('top-k')).value),
                search_type: form.querySelector('#' + this.getElementId('search-type')).value
            };
            
            // Add filters if any
            const filterKey = form.querySelector('#' + this.getElementId('filter-key')).value.trim();
            const filterValue = form.querySelector('#' + this.getElementId('filter-value')).value.trim();
            if (filterKey && filterValue) {
                searchParams.filters = {
                    [filterKey]: filterValue
                };
            }
            
            // Send search request
            const response = await fetch(`${this.baseUrl}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(searchParams)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            this.searchResults = result.results;
            
            // Display results
            this.displaySearchResults(result);
            
        } catch (error) {
            console.error('Search failed:', error);
            this.showError('search-results', `Search failed: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    /**
     * Display search results
     */
    displaySearchResults(result) {
        const resultsEl = document.getElementById(this.getElementId('search-results'));
        
        if (result.results.length === 0) {
            resultsEl.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    No results found for "${result.query}"
                </div>
            `;
            return;
        }
        
        resultsEl.innerHTML = `
            <div class="results-header">
                <h4>Search Results (${result.total_results} found)</h4>
                <div class="search-info">
                    <span>Query: "${result.query}"</span>
                    <span>Type: ${result.search_type}</span>
                </div>
            </div>
            <div class="results-list">
                ${result.results.map((doc, index) => `
                    <div class="result-item">
                        <div class="result-header">
                            <span class="result-number">#${index + 1}</span>
                            <span class="result-score">Score: ${doc.score.toFixed(4)}</span>
                        </div>
                        <div class="result-content">
                            ${this.highlightContent(doc.content, result.query)}
                        </div>
                        <div class="result-metadata">
                            ${Object.entries(doc.metadata).map(([key, value]) => `
                                <span class="metadata-tag">
                                    <strong>${key}:</strong> ${value}
                                </span>
                            `).join('')}
                        </div>
                        <div class="result-actions">
                            <button onclick="ragTesting.viewDocument('${doc.document_id}')">
                                <i class="fas fa-eye"></i> View Full Document
                            </button>
                            <button onclick="ragTesting.copyToClipboard('${doc.document_id}')">
                                <i class="fas fa-copy"></i> Copy ID
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Highlight search terms in content
     */
    highlightContent(content, query) {
        const terms = query.split(/\s+/);
        let highlighted = content;
        
        terms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            highlighted = highlighted.replace(regex, '<mark>$1</mark>');
        });
        
        return highlighted;
    }

    /**
     * Lookup a specific document
     */
    async lookupDocument() {
        const input = document.getElementById(this.getElementId('document-id-input'));
        const documentId = input.value.trim();
        
        if (!documentId) {
            this.showError('document-viewer', 'Please enter a document ID');
            return;
        }
        
        await this.viewDocument(documentId);
    }

    /**
     * View a specific document
     */
    async viewDocument(documentId) {
        const viewerEl = document.getElementById(this.getElementId('document-viewer'));
        
        try {
            viewerEl.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading document...</div>';
            
            const response = await fetch(`${this.baseUrl}/get_document_with_context/${documentId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Document not found');
                }
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const document = await response.json();
            
            viewerEl.innerHTML = `
                <div class="document-view">
                    <div class="document-header">
                        <h4>Document Details</h4>
                        <span class="document-id">ID: ${document.document_id}</span>
                    </div>
                    <div class="document-content">
                        <h5>Content:</h5>
                        <pre>${document.content}</pre>
                    </div>
                    <div class="document-metadata">
                        <h5>Metadata:</h5>
                        ${Object.keys(document.metadata).length > 0 ? `
                            <table class="metadata-table">
                                ${Object.entries(document.metadata).map(([key, value]) => `
                                    <tr>
                                        <td><strong>${key}</strong></td>
                                        <td>${value}</td>
                                    </tr>
                                `).join('')}
                            </table>
                        ` : '<p>No metadata</p>'}
                    </div>
                    <div class="document-info">
                        <p><strong>Ingestion Time:</strong> ${new Date(document.ingestion_timestamp).toLocaleString()}</p>
                        <p><strong>Service Mode:</strong> ${document.mode}</p>
                    </div>
                </div>
            `;
            
            // Update the input field
            document.getElementById(this.getElementId('document-id-input')).value = documentId;
            
        } catch (error) {
            console.error('Document lookup failed:', error);
            viewerEl.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    ${error.message}
                </div>
            `;
        }
    }

    /**
     * Clear all results
     */
    clearResults() {
        document.getElementById(this.getElementId('ingest-results')).innerHTML = '';
        document.getElementById(this.getElementId('search-results')).innerHTML = '';
        document.getElementById(this.getElementId('document-viewer')).innerHTML = '';
    }

    /**
     * Copy text to clipboard
     */
    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            // Show brief success message
            const btn = event.target.closest('button');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            setTimeout(() => {
                btn.innerHTML = originalHTML;
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    /**
     * Show error message
     */
    showError(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    ${message}
                </div>
            `;
        }
    }

    /**
     * Load stored document IDs from localStorage
     */
    loadStoredDocumentIds() {
        const stored = localStorage.getItem('rag_document_ids');
        if (stored) {
            try {
                this.documentIds = JSON.parse(stored);
            } catch (e) {
                console.error('Failed to load document IDs:', e);
            }
        }
    }

    /**
     * Save document IDs to localStorage
     */
    saveDocumentIds() {
        localStorage.setItem('rag_document_ids', JSON.stringify(this.documentIds));
    }
}

// Create global instance
window.ragTesting = new RAGTestingManager();
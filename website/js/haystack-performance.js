/**
 * Haystack Performance Dashboard Integration
 * 
 * Integrates Haystack performance monitoring into the Data Compose developer dashboard
 */

class HaystackPerformanceMonitor {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8001'; // Dashboard integration API
        this.updateInterval = 30000; // 30 seconds
        this.isInitialized = false;
        this.updateTimer = null;
        
        // Performance data cache
        this.cachedData = {
            overview: null,
            metrics: null,
            jobs: null,
            lastUpdate: null
        };
        
        console.log('Haystack Performance Monitor initialized');
    }
    
    /**
     * Initialize the performance monitor
     */
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            console.log('Starting Haystack Performance Monitor initialization...');
            
            // Add performance card to dashboard if not exists
            this.ensurePerformanceCard();
            
            // Initial data load
            await this.updatePerformanceData();
            
            // Start periodic updates
            this.startPeriodicUpdates();
            
            // Add service check to existing system
            this.addToServiceChecking();
            
            this.isInitialized = true;
            console.log('Haystack Performance Monitor started successfully');
            
        } catch (error) {
            console.error('Failed to initialize Haystack Performance Monitor:', error);
            this.showError('Failed to initialize performance monitoring');
        }
    }
    
    /**
     * Add Haystack service to existing service checking system
     */
    addToServiceChecking() {
        // Hook into existing checkAllServices function if it exists
        if (typeof checkAllServices === 'function') {
            console.log('Integrating with existing service checking system');
            
            // Store original function
            const originalCheckAllServices = checkAllServices;
            
            // Override with enhanced version
            window.checkAllServices = () => {
                // Call original function
                originalCheckAllServices();
                
                // Add our Haystack performance check
                this.checkHaystackPerformance();
            };
        }
    }
    
    /**
     * Check Haystack performance service status
     */
    async checkHaystackPerformance() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            
            // Update status display if the service item exists
            const statusElement = document.getElementById('haystack-performance-status');
            if (statusElement) {
                if (response.ok && data.status === 'healthy') {
                    statusElement.innerHTML = '<i class="fas fa-check-circle" style="color: green;"></i> Online';
                } else {
                    statusElement.innerHTML = '<i class="fas fa-exclamation-triangle" style="color: orange;"></i> Degraded';
                }
            }
            
        } catch (error) {
            console.warn('Haystack performance service check failed:', error);
            const statusElement = document.getElementById('haystack-performance-status');
            if (statusElement) {
                statusElement.innerHTML = '<i class="fas fa-times-circle" style="color: red;"></i> Offline';
            }
        }
    }
    
    /**
     * Ensure the performance card exists in the dashboard
     */
    ensurePerformanceCard() {
        console.log('Ensuring Haystack performance card exists...');
        
        // First, add service item to existing service status
        this.addServiceStatusItem();
        
        // Then add the performance monitoring card
        const dashboardGrid = document.querySelector('#developer-dashboard .dashboard-grid');
        if (!dashboardGrid) {
            console.error('Dashboard grid not found at selector: #developer-dashboard .dashboard-grid');
            // Try alternative selector
            const dashboard = document.getElementById('developer-dashboard');
            if (dashboard) {
                console.log('Found dashboard section, looking for grid...');
                const grid = dashboard.querySelector('.dashboard-grid');
                if (grid) {
                    console.log('Found dashboard grid via alternative method');
                } else {
                    console.error('No dashboard grid found in dashboard section');
                    return;
                }
            } else {
                console.error('No developer dashboard section found');
                return;
            }
        }
        
        // Check if performance card already exists
        if (document.getElementById('haystack-performance-card')) {
            console.log('Haystack performance card already exists');
            return;
        }
        
        console.log('Creating new Haystack performance card...');
        
        // Create performance card
        const performanceCard = this.createPerformanceCard();
        
        // Find dashboard grid again in case it wasn't found above
        const grid = dashboardGrid || document.querySelector('#developer-dashboard .dashboard-grid');
        
        if (grid) {
            // Insert before the RAG Testing card (which is full-width)
            const ragCard = grid.querySelector('.dashboard-card-wide');
            if (ragCard) {
                console.log('Inserting performance card before RAG testing card');
                grid.insertBefore(performanceCard, ragCard);
            } else {
                console.log('RAG card not found, appending performance card to grid');
                grid.appendChild(performanceCard);
            }
            
            console.log('Haystack performance card added successfully');
        } else {
            console.error('Could not find dashboard grid to insert performance card');
        }
    }
    
    /**
     * Add Haystack service item to existing service status section
     */
    addServiceStatusItem() {
        const serviceList = document.querySelector('#developer-dashboard .service-list');
        if (!serviceList) {
            console.warn('Service list not found, skipping service status item');
            return;
        }
        
        // Check if already added
        if (document.querySelector('[data-service="haystack-performance"]')) {
            console.log('Haystack performance service item already exists');
            return;
        }
        
        console.log('Adding Haystack performance service item...');
        
        // Create service item
        const serviceItem = document.createElement('div');
        serviceItem.className = 'service-item';
        serviceItem.setAttribute('data-service', 'haystack-performance');
        serviceItem.innerHTML = `
            <div>
                <span class="service-name">Haystack Performance</span>
                <div class="service-last-check" id="haystack-performance-last-check"></div>
            </div>
            <span class="service-status" id="haystack-performance-status">
                <i class="fas fa-circle-notch fa-spin"></i> Checking...
            </span>
        `;
        
        // Add to service list
        serviceList.appendChild(serviceItem);
        
        console.log('Haystack performance service item added');
    }
    
    /**
     * Create the performance monitoring card HTML
     */
    createPerformanceCard() {
        const card = document.createElement('div');
        card.className = 'dashboard-card';
        card.id = 'haystack-performance-card';
        
        card.innerHTML = `
            <h3><i class="fas fa-chart-bar"></i> Haystack Performance</h3>
            <div class="card-description">
                Real-time performance monitoring for bulk document processing
            </div>
            
            <!-- Performance Overview -->
            <div id="performance-overview" class="performance-section">
                <div class="loading">
                    <i class="fas fa-spinner fa-spin"></i> Loading performance data...
                </div>
            </div>
            
            <!-- Quick Actions -->
            <div class="performance-actions">
                <button class="btn btn-primary btn-sm" onclick="haystackPerformance.showDetailedMetrics()">
                    <i class="fas fa-chart-line"></i> Detailed Metrics
                </button>
                <button class="btn btn-secondary btn-sm" onclick="haystackPerformance.refreshData()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
            
            <!-- Job Management (collapsible) -->
            <div class="performance-jobs-section">
                <button class="btn btn-outline btn-sm" onclick="haystackPerformance.toggleJobsSection()">
                    <i class="fas fa-tasks" id="jobs-toggle-icon"></i> 
                    <span id="jobs-toggle-text">Show Jobs</span>
                </button>
                <div id="jobs-container" class="jobs-container collapsed">
                    <div class="loading">
                        <i class="fas fa-spinner fa-spin"></i> Loading jobs...
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    /**
     * Update all performance data
     */
    async updatePerformanceData() {
        try {
            // Update overview data
            await this.updateOverview();
            
            // Update jobs data if jobs section is expanded
            if (!document.getElementById('jobs-container')?.classList.contains('collapsed')) {
                await this.updateJobs();
            }
            
            this.cachedData.lastUpdate = new Date();
            
        } catch (error) {
            console.error('Failed to update performance data:', error);
            this.showError('Failed to fetch performance data');
        }
    }
    
    /**
     * Update performance overview
     */
    async updateOverview() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/performance/overview`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.cachedData.overview = data;
            this.renderOverview(data);
            
        } catch (error) {
            console.error('Failed to fetch overview:', error);
            this.showError('Service unavailable');
        }
    }
    
    /**
     * Render performance overview
     */
    renderOverview(data) {
        const container = document.getElementById('performance-overview');
        if (!container) return;
        
        const statusIcon = this.getStatusIcon(data.status_indicator);
        const errorRate = data.processing.error_rate;
        const errorClass = errorRate > 10 ? 'error' : errorRate > 5 ? 'warning' : 'success';
        
        container.innerHTML = `
            <div class="performance-grid">
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">System Status</span>
                        ${statusIcon}
                    </div>
                    <div class="metric-details">
                        CPU: ${data.system.cpu_percent}% | Memory: ${data.system.memory_percent}%
                    </div>
                </div>
                
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">Documents Processed</span>
                        <span class="metric-value">${data.processing.total_documents.toLocaleString()}</span>
                    </div>
                    <div class="metric-details">
                        Success: ${data.processing.successful_documents.toLocaleString()} | 
                        <span class="error-rate ${errorClass}">Errors: ${data.processing.error_count}</span>
                    </div>
                </div>
                
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">Performance</span>
                        <span class="metric-value">${data.performance.throughput_last_hour} docs/hr</span>
                    </div>
                    <div class="metric-details">
                        Avg time: ${data.performance.avg_processing_time}s per doc
                    </div>
                </div>
                
                ${data.alerts.count > 0 ? `
                <div class="performance-metric performance-alerts">
                    <div class="metric-header">
                        <span class="metric-label">Alerts</span>
                        <span class="metric-value alert-count">${data.alerts.count}</span>
                    </div>
                    <div class="metric-details">
                        ${data.alerts.recent.map(alert => `
                            <div class="alert-item">${alert.message}</div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
            
            <div class="performance-summary">
                <small>
                    <i class="fas fa-clock"></i> Updated: ${new Date().toLocaleTimeString()} | 
                    Uptime: ${Math.round(data.uptime_hours * 10) / 10}h
                </small>
            </div>
        `;
    }
    
    /**
     * Update jobs data
     */
    async updateJobs() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/jobs`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.cachedData.jobs = data;
            this.renderJobs(data);
            
        } catch (error) {
            console.error('Failed to fetch jobs:', error);
            document.getElementById('jobs-container').innerHTML = `
                <div class="error">Failed to load jobs data</div>
            `;
        }
    }
    
    /**
     * Render jobs section
     */
    renderJobs(data) {
        const container = document.getElementById('jobs-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="jobs-summary">
                <div class="job-stat">
                    <span class="job-stat-label">Active:</span>
                    <span class="job-stat-value">${data.active_jobs}</span>
                </div>
                <div class="job-stat">
                    <span class="job-stat-label">Total:</span>
                    <span class="job-stat-value">${data.total_jobs}</span>
                </div>
                <div class="job-stat">
                    <span class="job-stat-label">Completed:</span>
                    <span class="job-stat-value success">${data.summary.completed}</span>
                </div>
                <div class="job-stat">
                    <span class="job-stat-label">Failed:</span>
                    <span class="job-stat-value ${data.summary.failed > 0 ? 'error' : ''}">${data.summary.failed}</span>
                </div>
            </div>
            
            ${data.active_details.length > 0 ? `
                <div class="active-jobs">
                    <h4>Active Jobs</h4>
                    ${data.active_details.map(job => `
                        <div class="job-item">
                            <div class="job-header">
                                <span class="job-id">${job.job_id}</span>
                                <span class="job-type">${job.job_type}</span>
                            </div>
                            <div class="job-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
                                </div>
                                <span class="progress-text">${Math.round(job.progress || 0)}%</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            
            ${data.recent_jobs.length > 0 ? `
                <div class="recent-jobs">
                    <h4>Recent Jobs</h4>
                    ${data.recent_jobs.slice(-3).map(job => `
                        <div class="job-item ${job.status}">
                            <div class="job-header">
                                <span class="job-id">${job.job_id}</span>
                                <span class="job-status">${job.status}</span>
                            </div>
                            ${job.stats ? `
                                <div class="job-stats">
                                    ${job.stats.successful_documents}/${job.stats.total_documents} docs 
                                    (${job.stats.success_rate}% success)
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            
            <div class="job-actions">
                <button class="btn btn-primary btn-sm" onclick="haystackPerformance.startQuickJob('ingest_new')">
                    <i class="fas fa-play"></i> Ingest New Documents
                </button>
                <button class="btn btn-secondary btn-sm" onclick="haystackPerformance.showJobDialog()">
                    <i class="fas fa-plus"></i> Start Custom Job
                </button>
            </div>
        `;
    }
    
    /**
     * Get status icon based on status indicator
     */
    getStatusIcon(status) {
        switch (status) {
            case 'healthy':
                return '<i class="fas fa-check-circle text-success"></i>';
            case 'degraded':
                return '<i class="fas fa-exclamation-triangle text-warning"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-circle text-error"></i>';
            default:
                return '<i class="fas fa-question-circle"></i>';
        }
    }
    
    /**
     * Show error message
     */
    showError(message) {
        const container = document.getElementById('performance-overview');
        if (container) {
            container.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i> ${message}
                </div>
            `;
        }
    }
    
    /**
     * Start periodic updates
     */
    startPeriodicUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        this.updateTimer = setInterval(() => {
            this.updatePerformanceData();
        }, this.updateInterval);
    }
    
    /**
     * Stop periodic updates
     */
    stopPeriodicUpdates() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    /**
     * Toggle jobs section
     */
    toggleJobsSection() {
        const container = document.getElementById('jobs-container');
        const icon = document.getElementById('jobs-toggle-icon');
        const text = document.getElementById('jobs-toggle-text');
        
        if (container.classList.contains('collapsed')) {
            container.classList.remove('collapsed');
            icon.className = 'fas fa-chevron-up';
            text.textContent = 'Hide Jobs';
            this.updateJobs(); // Load jobs data when expanded
        } else {
            container.classList.add('collapsed');
            icon.className = 'fas fa-tasks';
            text.textContent = 'Show Jobs';
        }
    }
    
    /**
     * Refresh performance data manually
     */
    async refreshData() {
        const button = event.target.closest('button');
        const originalHtml = button.innerHTML;
        
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        button.disabled = true;
        
        try {
            await this.updatePerformanceData();
        } finally {
            button.innerHTML = originalHtml;
            button.disabled = false;
        }
    }
    
    /**
     * Show detailed metrics in modal/drawer
     */
    async showDetailedMetrics() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/performance/metrics`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.showMetricsModal(data);
            
        } catch (error) {
            console.error('Failed to fetch detailed metrics:', error);
            alert('Failed to load detailed metrics');
        }
    }
    
    /**
     * Show metrics in a modal
     */
    showMetricsModal(data) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('performance-metrics-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'performance-metrics-modal';
            modal.className = 'modal';
            document.body.appendChild(modal);
        }
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Detailed Performance Metrics</h3>
                    <button class="modal-close" onclick="haystackPerformance.closeMetricsModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="metrics-tabs">
                        <button class="tab-button active" onclick="haystackPerformance.showMetricsTab('system')">System</button>
                        <button class="tab-button" onclick="haystackPerformance.showMetricsTab('performance')">Performance</button>
                        <button class="tab-button" onclick="haystackPerformance.showMetricsTab('connections')">Connections</button>
                        <button class="tab-button" onclick="haystackPerformance.showMetricsTab('recommendations')">Recommendations</button>
                    </div>
                    
                    <div id="metrics-tab-system" class="metrics-tab active">
                        ${this.renderSystemMetrics(data)}
                    </div>
                    
                    <div id="metrics-tab-performance" class="metrics-tab">
                        ${this.renderPerformanceMetrics(data)}
                    </div>
                    
                    <div id="metrics-tab-connections" class="metrics-tab">
                        ${this.renderConnectionMetrics(data)}
                    </div>
                    
                    <div id="metrics-tab-recommendations" class="metrics-tab">
                        ${this.renderRecommendations(data)}
                    </div>
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    }
    
    /**
     * Render system metrics tab
     */
    renderSystemMetrics(data) {
        return `
            <div class="metrics-section">
                <h4>System Resources</h4>
                <div class="metrics-grid">
                    ${data.system_trends.cpu_percent ? `
                        <div class="metric-chart">
                            <h5>CPU Usage</h5>
                            <div class="chart-placeholder">
                                Current: ${data.system_trends.cpu_percent[data.system_trends.cpu_percent.length - 1]}%
                            </div>
                        </div>
                    ` : ''}
                    ${data.system_trends.memory_percent ? `
                        <div class="metric-chart">
                            <h5>Memory Usage</h5>
                            <div class="chart-placeholder">
                                Current: ${data.system_trends.memory_percent[data.system_trends.memory_percent.length - 1]}%
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Render performance metrics tab
     */
    renderPerformanceMetrics(data) {
        return `
            <div class="metrics-section">
                <h4>Processing Performance</h4>
                <div class="timing-stats">
                    ${Object.entries(data.timing_stats).map(([key, stats]) => `
                        <div class="timing-stat">
                            <h5>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h5>
                            <div class="stat-grid">
                                <div>Mean: ${stats.mean || 0}s</div>
                                <div>Min: ${stats.min || 0}s</div>
                                <div>Max: ${stats.max || 0}s</div>
                                <div>Count: ${stats.count || 0}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    /**
     * Render connection metrics tab
     */
    renderConnectionMetrics(data) {
        return `
            <div class="metrics-section">
                <h4>Connection Pools</h4>
                <div class="connection-stats">
                    ${Object.entries(data.connection_pools).map(([service, info]) => `
                        <div class="connection-stat">
                            <h5>${service.charAt(0).toUpperCase() + service.slice(1)}</h5>
                            <div class="stat-details">
                                ${typeof info === 'object' && info.connected !== undefined ? `
                                    <div>Status: ${info.connected ? 'Connected' : 'Disconnected'}</div>
                                    ${info.size ? `<div>Pool Size: ${info.idle_connections}/${info.size}</div>` : ''}
                                ` : `
                                    <div>Status: ${JSON.stringify(info)}</div>
                                `}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    /**
     * Render recommendations tab
     */
    renderRecommendations(data) {
        return `
            <div class="metrics-section">
                <h4>Performance Recommendations</h4>
                <div class="recommendations">
                    ${data.recommendations.map(rec => `
                        <div class="recommendation-item">
                            <i class="fas fa-lightbulb"></i> ${rec}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    /**
     * Show specific metrics tab
     */
    showMetricsTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.metrics-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected tab
        document.getElementById(`metrics-tab-${tabName}`).classList.add('active');
        event.target.classList.add('active');
    }
    
    /**
     * Close metrics modal
     */
    closeMetricsModal() {
        const modal = document.getElementById('performance-metrics-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    /**
     * Start a quick ingestion job
     */
    async startQuickJob(jobType) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/jobs/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ type: jobType })
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const result = await response.json();
            
            // Show success message
            this.showNotification(`Job started: ${result.job_id}`, 'success');
            
            // Refresh jobs data
            if (!document.getElementById('jobs-container').classList.contains('collapsed')) {
                await this.updateJobs();
            }
            
        } catch (error) {
            console.error('Failed to start job:', error);
            this.showNotification('Failed to start job', 'error');
        }
    }
    
    /**
     * Show job creation dialog
     */
    showJobDialog() {
        // Simple prompt for now - could be enhanced with a proper modal
        const jobType = prompt('Job type (ingest_new, ingest_judge, ingest_recent):');
        if (!jobType) return;
        
        let jobConfig = { type: jobType };
        
        if (jobType === 'ingest_judge') {
            const judgeName = prompt('Judge name:');
            if (!judgeName) return;
            jobConfig.judge_name = judgeName;
            
            const courtId = prompt('Court ID (optional):');
            if (courtId) jobConfig.court_id = courtId;
        } else if (jobType === 'ingest_recent') {
            const days = prompt('Number of days (default 30):');
            if (days) jobConfig.days = parseInt(days);
        }
        
        this.startCustomJob(jobConfig);
    }
    
    /**
     * Start custom job
     */
    async startCustomJob(jobConfig) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/jobs/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(jobConfig)
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const result = await response.json();
            this.showNotification(`Job started: ${result.job_id}`, 'success');
            
            // Refresh jobs data
            if (!document.getElementById('jobs-container').classList.contains('collapsed')) {
                await this.updateJobs();
            }
            
        } catch (error) {
            console.error('Failed to start custom job:', error);
            this.showNotification('Failed to start job', 'error');
        }
    }
    
    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : 'info'}-circle"></i>
            ${message}
        `;
        
        // Add to document
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    /**
     * Cleanup when dashboard is hidden
     */
    cleanup() {
        this.stopPeriodicUpdates();
        this.isInitialized = false;
    }
}

// Global instance
const haystackPerformance = new HaystackPerformanceMonitor();

// Enhanced integration with Data Compose app
function integrateHaystackWithDashboard() {
    console.log('Integrating Haystack Performance with Data Compose dashboard...');
    
    // Wait for the app to be fully loaded
    const integrationInterval = setInterval(() => {
        // Check if the main app is available and dashboard exists
        if (typeof checkAllServices === 'function' && document.getElementById('developer-dashboard')) {
            console.log('Data Compose app detected, proceeding with integration...');
            clearInterval(integrationInterval);
            
            // Store reference to original onShow handler
            const dashboardSection = document.getElementById('developer-dashboard');
            
            // Extend the existing dashboard initialization
            const originalCheckAllServices = window.checkAllServices;
            
            // Override checkAllServices to include our integration
            window.checkAllServices = function() {
                // Call original function
                if (originalCheckAllServices) {
                    originalCheckAllServices();
                }
                
                // Initialize Haystack monitoring if dashboard is active
                if (dashboardSection && dashboardSection.classList.contains('active')) {
                    setTimeout(() => {
                        haystackPerformance.initialize();
                    }, 500); // Give time for dashboard to fully load
                }
            };
            
            // If dashboard is currently active, initialize immediately
            if (dashboardSection.classList.contains('active')) {
                setTimeout(() => {
                    haystackPerformance.initialize();
                }, 1000);
            }
            
            console.log('Haystack Performance integration completed');
        }
    }, 100);
    
    // Timeout after 10 seconds if app doesn't load
    setTimeout(() => {
        clearInterval(integrationInterval);
        console.warn('Timeout waiting for Data Compose app to load');
    }, 10000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', integrateHaystackWithDashboard);
} else {
    // DOM already loaded
    integrateHaystackWithDashboard();
}
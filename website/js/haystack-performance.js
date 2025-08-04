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
        this.startTime = Date.now(); // Track when monitoring started
        
        // Performance data cache
        this.cachedData = {
            overview: null,
            metrics: null,
            jobs: null,
            lastUpdate: null
        };
        
        // Hook into console.error to track errors
        this.setupErrorTracking();
        
        console.log('🔧 Haystack Performance Monitor initialized - Real metrics mode');
    }
    
    /**
     * Setup error tracking for real debugging info
     */
    setupErrorTracking() {
        if (!window.consoleErrorCount) {
            window.consoleErrorCount = 0;
        }
        
        // Hook into console.error
        const originalError = console.error;
        console.error = function(...args) {
            window.consoleErrorCount++;
            originalError.apply(console, args);
        };
        
        // Hook into window.onerror
        const originalOnError = window.onerror;
        window.onerror = function(message, source, lineno, colno, error) {
            window.consoleErrorCount++;
            if (originalOnError) {
                return originalOnError.apply(window, arguments);
            }
        };
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
            console.log('🔄 Fetching performance overview...');
            const response = await fetch(`${this.apiBaseUrl}/performance/overview`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('✅ Performance data received:', data);
            this.cachedData.overview = data;
            this.renderOverview(data);
            
        } catch (error) {
            console.warn('⚠️ Haystack API not available, using fallback data:', error.message);
            
            // Use real system data where available, fallback data elsewhere
            const fallbackData = await this.getFallbackPerformanceData();
            this.cachedData.overview = fallbackData;
            this.renderOverview(fallbackData);
        }
    }
    
    /**
     * Get fallback performance data with real system info where possible
     */
    async getFallbackPerformanceData() {
        const data = {
            timestamp: new Date().toISOString(),
            uptime_hours: (Date.now() - this.startTime) / (1000 * 60 * 60),
            system: await this.getRealSystemMetrics(),
            processing: await this.getRealProcessingMetrics(),
            performance: await this.getRealPerformanceMetrics(),
            alerts: await this.getRealAlerts(),
            status_indicator: 'degraded' // API not available
        };
        
        console.log('📊 Using fallback data:', data);
        return data;
    }
    
    /**
     * Get real system metrics from browser APIs
     */
    async getRealSystemMetrics() {
        try {
            const nav = navigator;
            const perf = performance;
            
            // Real browser memory metrics
            let memoryInfo = { usedJSHeapSize: 0, totalJSHeapSize: 0, jsHeapSizeLimit: 0 };
            if (nav.memory) {
                memoryInfo = nav.memory;
            }
            
            // Connection info
            let connectionInfo = { effectiveType: 'unknown', downlink: 0, rtt: 0 };
            if (nav.connection) {
                connectionInfo = nav.connection;
            }
            
            // Calculate memory usage
            const memoryMB = Math.round(memoryInfo.usedJSHeapSize / 1024 / 1024);
            const memoryPercent = memoryInfo.totalJSHeapSize ? 
                Math.round((memoryInfo.usedJSHeapSize / memoryInfo.totalJSHeapSize) * 100) : 0;
            
            // Get browser timing for performance assessment
            const timing = perf.timing;
            const navigation = perf.getEntriesByType('navigation')[0];
            
            // Real resource loading count
            const resourceCount = perf.getEntriesByType('resource').length;
            
            // Browser-based CPU approximation using performance metrics
            let cpuApprox = 10; // baseline
            if (navigation) {
                const loadTime = navigation.loadEventEnd - navigation.loadEventStart;
                cpuApprox += Math.min(Math.round(loadTime / 50), 30);
            }
            if (resourceCount > 50) cpuApprox += 5;
            if (memoryPercent > 70) cpuApprox += 10;
            
            return {
                cpu_percent: Math.min(cpuApprox, 95),
                memory_mb: memoryMB,
                memory_percent: memoryPercent,
                memory_limit_mb: Math.round(memoryInfo.jsHeapSizeLimit / 1024 / 1024),
                connection_type: connectionInfo.effectiveType,
                connection_rtt: connectionInfo.rtt || 0,
                connection_downlink: connectionInfo.downlink || 0,
                resource_count: resourceCount,
                timing_info: {
                    load_time: timing ? timing.loadEventEnd - timing.navigationStart : 0,
                    dom_ready: timing ? timing.domContentLoadedEventEnd - timing.navigationStart : 0,
                    page_load: navigation ? navigation.loadEventEnd : 0
                }
            };
        } catch (error) {
            console.warn('Could not get real system metrics:', error);
            return {
                cpu_percent: 0,
                memory_mb: 0,
                memory_percent: 0,
                memory_limit_mb: 0,
                connection_type: 'unknown',
                resource_count: 0
            };
        }
    }
    
    /**
     * Get real processing metrics from existing services
     */
    async getRealProcessingMetrics() {
        try {
            // Check if we can get data from existing Haystack service
            const haystackResponse = await this.checkExistingHaystackService();
            
            if (haystackResponse.available) {
                return {
                    total_documents: haystackResponse.document_count || 0,
                    successful_documents: haystackResponse.successful_count || 0,
                    error_count: haystackResponse.error_count || 0,
                    error_rate: haystackResponse.error_rate || 0,
                    last_update: haystackResponse.last_update || new Date().toISOString()
                };
            }
            
            // Fallback to localStorage cache if available
            const cached = localStorage.getItem('haystack_processing_stats');
            if (cached) {
                return JSON.parse(cached);
            }
            
            return {
                total_documents: 0,
                successful_documents: 0,
                error_count: 0,
                error_rate: 0,
                last_update: new Date().toISOString()
            };
            
        } catch (error) {
            console.warn('Could not get processing metrics:', error);
            return {
                total_documents: 0,
                successful_documents: 0,
                error_count: 0,
                error_rate: 0
            };
        }
    }
    
    /**
     * Check existing Haystack service endpoints
     */
    async checkExistingHaystackService() {
        const endpoints = [
            { url: 'http://localhost:8000/health', name: 'haystack-health', timeout: 3000 },
            { url: 'http://localhost:8000/docs', name: 'haystack-docs', timeout: 3000 },
            { url: 'http://localhost:8001/health', name: 'dashboard-api', timeout: 2000 },
            { url: 'http://localhost:9200/_cluster/health', name: 'elasticsearch', timeout: 3000 },
            { url: 'http://localhost:5678/rest/active-workflows', name: 'n8n-workflows', timeout: 3000 },
            { url: 'http://localhost:5678/rest/executions', name: 'n8n-executions', timeout: 3000 }
        ];
        
        const results = { 
            available: false, 
            services: {},
            connectivity_score: 0,
            total_checked: endpoints.length,
            online_count: 0
        };
        
        // Check all endpoints concurrently
        const checks = endpoints.map(async (endpoint) => {
            const startTime = performance.now();
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), endpoint.timeout);
                
                const response = await fetch(endpoint.url, { 
                    method: 'GET',
                    signal: controller.signal,
                    mode: 'no-cors', // Allow checking services without CORS
                    cache: 'no-cache'
                });
                
                clearTimeout(timeoutId);
                const responseTime = Math.round(performance.now() - startTime);
                
                const serviceResult = {
                    status: 'online',
                    status_code: response.status || 200,
                    response_time_ms: responseTime,
                    last_checked: new Date().toISOString()
                };
                
                // Try to get JSON data for health endpoints
                if (endpoint.name.includes('health') && response.ok) {
                    try {
                        const data = await response.json();
                        serviceResult.health_data = data;
                        if (data.document_count) results.document_count = data.document_count;
                        if (data.timestamp) results.last_update = data.timestamp;
                    } catch (jsonError) {
                        // JSON parsing failed, but service is still online
                        serviceResult.json_error = jsonError.message;
                    }
                }
                
                results.services[endpoint.name] = serviceResult;
                results.online_count++;
                
                if (endpoint.name.startsWith('haystack')) {
                    results.available = true;
                }
                
            } catch (error) {
                const responseTime = Math.round(performance.now() - startTime);
                results.services[endpoint.name] = {
                    status: 'offline',
                    error: error.name === 'AbortError' ? 'timeout' : error.message,
                    response_time_ms: responseTime,
                    last_checked: new Date().toISOString()
                };
            }
        });
        
        // Wait for all checks to complete
        await Promise.allSettled(checks);
        
        // Calculate connectivity score
        results.connectivity_score = Math.round((results.online_count / results.total_checked) * 100);
        
        console.log('🔍 Enhanced service check results:', results);
        return results;
    }
    
    getServiceNameFromEndpoint(endpoint) {
        if (endpoint.includes(':8000')) return 'haystack';
        if (endpoint.includes(':9200')) return 'elasticsearch';
        if (endpoint.includes(':5678')) return 'n8n';
        return 'unknown';
    }
    
    /**
     * Get real performance metrics
     */
    async getRealPerformanceMetrics() {
        try {
            // Check browser performance metrics
            const perf = performance;
            const navigation = perf.getEntriesByType('navigation')[0];
            
            return {
                avg_processing_time: navigation ? (navigation.loadEventEnd - navigation.loadEventStart) / 1000 : 0,
                throughput_last_hour: this.calculateBrowserThroughput(),
                page_load_time: navigation ? navigation.loadEventEnd / 1000 : 0,
                resource_count: perf.getEntriesByType('resource').length
            };
        } catch (error) {
            return {
                avg_processing_time: 0,
                throughput_last_hour: 0,
                page_load_time: 0,
                resource_count: 0
            };
        }
    }
    
    calculateBrowserThroughput() {
        // Calculate based on resource loading performance
        const resources = performance.getEntriesByType('resource');
        const lastHour = Date.now() - (60 * 60 * 1000);
        const recentResources = resources.filter(r => r.startTime > lastHour);
        return recentResources.length;
    }
    
    /**
     * Get real alerts from system state
     */
    async getRealAlerts() {
        const alerts = [];
        
        try {
            // Check browser memory usage
            if (navigator.memory && navigator.memory.usedJSHeapSize) {
                const memUsage = (navigator.memory.usedJSHeapSize / navigator.memory.totalJSHeapSize) * 100;
                if (memUsage > 80) {
                    alerts.push({
                        type: 'memory_warning',
                        message: `Browser memory usage high: ${memUsage.toFixed(1)}%`,
                        timestamp: new Date().toISOString(),
                        level: 'warning'
                    });
                }
            }
            
            // Check connection quality
            if (navigator.connection && navigator.connection.effectiveType) {
                const connType = navigator.connection.effectiveType;
                if (connType === 'slow-2g' || connType === '2g') {
                    alerts.push({
                        type: 'connection_warning',
                        message: `Slow network connection detected: ${connType}`,
                        timestamp: new Date().toISOString(),
                        level: 'warning'
                    });
                }
            }
            
            // Check for console errors
            const errorCount = this.getConsoleErrorCount();
            if (errorCount > 0) {
                alerts.push({
                    type: 'javascript_errors',
                    message: `${errorCount} JavaScript errors detected`,
                    timestamp: new Date().toISOString(),
                    level: 'error'
                });
            }
            
        } catch (error) {
            console.warn('Could not generate real alerts:', error);
        }
        
        return alerts;
    }
    
    getConsoleErrorCount() {
        // This is a simplified approach - in reality you'd need to hook into console.error
        return window.consoleErrorCount || 0;
    }
    
    /**
     * Render performance overview
     */
    renderOverview(data) {
        const container = document.getElementById('performance-overview');
        if (!container) return;
        
        console.log('🎨 Rendering performance overview with data:', data);
        
        const statusIcon = this.getStatusIcon(data.status_indicator);
        const errorRate = data.processing.error_rate || 0;
        const errorClass = errorRate > 10 ? 'error' : errorRate > 5 ? 'warning' : 'success';
        
        // Enhanced debugging info
        const connectivity = await this.checkExistingHaystackService();
        const debugInfo = data.status_indicator === 'degraded' ? 
            `<span style="color: orange;">📡 API Offline - Browser Mode (${connectivity.connectivity_score}% services)</span>` : 
            `<span style="color: green;">📡 API Connected (${connectivity.connectivity_score}% services online)</span>`;
        
        const memoryDetails = data.system.memory_limit_mb ? 
            `${data.system.memory_mb}MB/${data.system.memory_limit_mb}MB (${data.system.memory_percent}%)` :
            `${data.system.memory_mb}MB (${data.system.memory_percent}%)`;
        
        container.innerHTML = `
            <div class="performance-grid">
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">System Status</span>
                        ${statusIcon}
                    </div>
                    <div class="metric-details">
                        CPU: ${data.system.cpu_percent}% | Memory: ${memoryDetails}
                        ${data.system.connection_type && data.system.connection_type !== 'unknown' ? 
                            `<br>Network: ${data.system.connection_type} (${data.system.connection_rtt}ms RTT)` : ''}
                        <br>Resources: ${data.system.resource_count || 0} loaded
                    </div>
                </div>
                
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">Documents Processed</span>
                        <span class="metric-value">${(data.processing.total_documents || 0).toLocaleString()}</span>
                    </div>
                    <div class="metric-details">
                        Success: ${(data.processing.successful_documents || 0).toLocaleString()} | 
                        <span class="error-rate ${errorClass}">Errors: ${data.processing.error_count || 0}</span>
                        <br>Error Rate: ${errorRate.toFixed(1)}%
                        ${data.processing.last_update ? `<br>Last: ${new Date(data.processing.last_update).toLocaleTimeString()}` : ''}
                    </div>
                </div>
                
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">Performance</span>
                        <span class="metric-value">${(data.performance.throughput_last_hour || 0)} resources/hr</span>
                    </div>
                    <div class="metric-details">
                        Page Load: ${(data.performance.page_load_time || 0).toFixed(2)}s
                        <br>DOM Ready: ${data.system.timing_info ? (data.system.timing_info.dom_ready / 1000).toFixed(2) : 0}s
                    </div>
                </div>
                
                <div class="performance-metric">
                    <div class="metric-header">
                        <span class="metric-label">Service Connectivity</span>
                        <span class="metric-value">${connectivity.connectivity_score}%</span>
                    </div>
                    <div class="metric-details">
                        Online: ${connectivity.online_count}/${connectivity.total_checked} services
                        <br>Haystack: ${connectivity.services['haystack-health']?.status || 'offline'}
                        <br>Elasticsearch: ${connectivity.services['elasticsearch']?.status || 'offline'}
                    </div>
                </div>
                
                ${data.alerts && data.alerts.length > 0 ? `
                <div class="performance-metric performance-alerts">
                    <div class="metric-header">
                        <span class="metric-label">Alerts</span>
                        <span class="metric-value alert-count">${data.alerts.length}</span>
                    </div>
                    <div class="metric-details">
                        ${data.alerts.slice(0, 2).map(alert => `
                            <div class="alert-item">${alert.message}</div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
            
            <div class="performance-summary">
                <small>
                    <i class="fas fa-clock"></i> Updated: ${new Date().toLocaleTimeString()} | 
                    Uptime: ${Math.round((data.uptime_hours || 0) * 10) / 10}h | 
                    ${debugInfo}
                    <br>JS Errors: ${window.consoleErrorCount || 0} | 
                    Console: ${connectivity.services ? Object.keys(connectivity.services).length : 0} endpoints checked |
                    Mode: ${data.status_indicator === 'degraded' ? 'Fallback' : 'Connected'}
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
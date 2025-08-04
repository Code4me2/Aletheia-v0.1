/**
 * Haystack Performance Dashboard Integration - Debug Version
 * 
 * Simplified version for testing frontend integration without backend dependencies
 */

class HaystackPerformanceDebug {
    constructor() {
        this.isInitialized = false;
        console.log('🔧 Haystack Performance Debug Monitor initialized');
    }
    
    async initialize() {
        if (this.isInitialized) return;
        
        console.log('🚀 Starting Haystack Performance Debug initialization...');
        
        try {
            // Add service status item first
            this.addServiceStatusItem();
            
            // Add performance card
            this.ensurePerformanceCard();
            
            // Mock data update
            this.updateWithMockData();
            
            this.isInitialized = true;
            console.log('✅ Haystack Performance Debug initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize Haystack Performance Debug:', error);
        }
    }
    
    addServiceStatusItem() {
        const serviceList = document.querySelector('#developer-dashboard .service-list');
        if (!serviceList) {
            console.warn('⚠️ Service list not found');
            return;
        }
        
        // Check if already added
        if (document.querySelector('[data-service="haystack-performance"]')) {
            console.log('ℹ️ Haystack performance service item already exists');
            return;
        }
        
        console.log('➕ Adding Haystack performance service item...');
        
        const serviceItem = document.createElement('div');
        serviceItem.className = 'service-item';
        serviceItem.setAttribute('data-service', 'haystack-performance');
        serviceItem.innerHTML = `
            <div>
                <span class="service-name">Haystack Performance</span>
                <div class="service-last-check" id="haystack-performance-last-check">Debug Mode</div>
            </div>
            <span class="service-status" id="haystack-performance-status">
                <i class="fas fa-cog fa-spin" style="color: orange;"></i> Debug
            </span>
        `;
        
        serviceList.appendChild(serviceItem);
        console.log('✅ Haystack performance service item added');
    }
    
    ensurePerformanceCard() {
        console.log('🎨 Creating Haystack performance card...');
        
        const dashboardGrid = document.querySelector('#developer-dashboard .dashboard-grid');
        if (!dashboardGrid) {
            console.error('❌ Dashboard grid not found');
            return;
        }
        
        // Check if already exists
        if (document.getElementById('haystack-performance-card')) {
            console.log('ℹ️ Performance card already exists');
            return;
        }
        
        const performanceCard = this.createPerformanceCard();
        
        // Insert before RAG Testing card
        const ragCard = dashboardGrid.querySelector('.dashboard-card-wide');
        if (ragCard) {
            console.log('📍 Inserting before RAG testing card');
            dashboardGrid.insertBefore(performanceCard, ragCard);
        } else {
            console.log('📍 Appending to dashboard grid');
            dashboardGrid.appendChild(performanceCard);
        }
        
        console.log('✅ Haystack performance card created successfully');
    }
    
    createPerformanceCard() {
        const card = document.createElement('div');
        card.className = 'dashboard-card';
        card.id = 'haystack-performance-card';
        
        card.innerHTML = `
            <h3><i class="fas fa-chart-bar"></i> Haystack Performance (Debug)</h3>
            <div class="card-description">
                Debug mode - Real-time performance monitoring for bulk document processing
            </div>
            
            <div id="performance-overview" class="performance-section">
                <div class="performance-grid">
                    <div class="performance-metric">
                        <div class="metric-header">
                            <span class="metric-label">System Status</span>
                            <i class="fas fa-check-circle text-success"></i>
                        </div>
                        <div class="metric-details">
                            CPU: 25.3% | Memory: 42.1%
                        </div>
                    </div>
                    
                    <div class="performance-metric">
                        <div class="metric-header">
                            <span class="metric-label">Documents Processed</span>
                            <span class="metric-value">12,543</span>
                        </div>
                        <div class="metric-details">
                            Success: 12,234 | <span class="error-rate success">Errors: 309</span>
                        </div>
                    </div>
                    
                    <div class="performance-metric">
                        <div class="metric-header">
                            <span class="metric-label">Performance</span>
                            <span class="metric-value">450 docs/hr</span>
                        </div>
                        <div class="metric-details">
                            Avg time: 2.3s per doc
                        </div>
                    </div>
                </div>
                
                <div class="performance-summary">
                    <small>
                        <i class="fas fa-clock"></i> Updated: ${new Date().toLocaleTimeString()} | 
                        Uptime: 2.5h | 
                        <span style="color: orange;">🔧 DEBUG MODE</span>
                    </small>
                </div>
            </div>
            
            <div class="performance-actions">
                <button class="btn btn-primary btn-sm" onclick="haystackDebug.showDetailedMetrics()">
                    <i class="fas fa-chart-line"></i> Detailed Metrics
                </button>
                <button class="btn btn-secondary btn-sm" onclick="haystackDebug.refreshData()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
            
            <div class="performance-jobs-section">
                <button class="btn btn-outline btn-sm" onclick="haystackDebug.toggleJobsSection()">
                    <i class="fas fa-tasks" id="jobs-toggle-icon"></i> 
                    <span id="jobs-toggle-text">Show Jobs</span>
                </button>
                <div id="jobs-container" class="jobs-container collapsed">
                    <div class="jobs-summary">
                        <div class="job-stat">
                            <span class="job-stat-label">Active:</span>
                            <span class="job-stat-value">2</span>
                        </div>
                        <div class="job-stat">
                            <span class="job-stat-label">Total:</span>
                            <span class="job-stat-value">15</span>
                        </div>
                        <div class="job-stat">
                            <span class="job-stat-label">Completed:</span>
                            <span class="job-stat-value success">12</span>
                        </div>
                        <div class="job-stat">
                            <span class="job-stat-label">Failed:</span>
                            <span class="job-stat-value">1</span>
                        </div>
                    </div>
                    
                    <div class="job-actions">
                        <button class="btn btn-primary btn-sm" onclick="haystackDebug.startMockJob()">
                            <i class="fas fa-play"></i> Start Mock Job
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="alert('Debug mode - custom jobs not available')">
                            <i class="fas fa-plus"></i> Custom Job (Debug)
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    updateWithMockData() {
        console.log('📊 Updating with mock performance data...');
        // Mock data is already in the HTML
    }
    
    toggleJobsSection() {
        const container = document.getElementById('jobs-container');
        const icon = document.getElementById('jobs-toggle-icon');
        const text = document.getElementById('jobs-toggle-text');
        
        if (!container) return;
        
        if (container.classList.contains('collapsed')) {
            container.classList.remove('collapsed');
            icon.className = 'fas fa-chevron-up';
            text.textContent = 'Hide Jobs';
            console.log('📂 Jobs section expanded');
        } else {
            container.classList.add('collapsed');
            icon.className = 'fas fa-tasks';
            text.textContent = 'Show Jobs';
            console.log('📁 Jobs section collapsed');
        }
    }
    
    refreshData() {
        console.log('🔄 Refreshing mock data...');
        const button = event.target.closest('button');
        const originalHtml = button.innerHTML;
        
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        button.disabled = true;
        
        setTimeout(() => {
            button.innerHTML = originalHtml;
            button.disabled = false;
            console.log('✅ Mock data refresh completed');
        }, 1000);
    }
    
    showDetailedMetrics() {
        console.log('📈 Showing detailed metrics modal...');
        alert('Debug Mode: Detailed metrics modal would appear here.\n\nThis will show:\n- System resource trends\n- Performance statistics\n- Connection health\n- Recommendations');
    }
    
    startMockJob() {
        console.log('🚀 Starting mock job...');
        alert('Debug Mode: Mock job started!\n\nJob ID: debug_job_001\nType: ingest_new\nStatus: running');
    }
}

// Global debug instance
const haystackDebug = new HaystackPerformanceDebug();

// Debug integration function
function integrateHaystackDebug() {
    console.log('🔧 Starting Haystack Performance DEBUG integration...');
    
    const integrationInterval = setInterval(() => {
        const dashboard = document.getElementById('developer-dashboard');
        const grid = document.querySelector('#developer-dashboard .dashboard-grid');
        
        if (dashboard && grid) {
            console.log('✅ Dashboard found, initializing debug integration...');
            clearInterval(integrationInterval);
            
            // Initialize immediately if dashboard is active
            if (dashboard.classList.contains('active')) {
                console.log('📍 Dashboard is active, initializing now...');
                setTimeout(() => {
                    haystackDebug.initialize();
                }, 500);
            }
            
            // Also hook into service checking if available
            if (typeof checkAllServices === 'function') {
                console.log('🔗 Hooking into existing service checking...');
                const originalCheck = window.checkAllServices;
                window.checkAllServices = function() {
                    originalCheck();
                    
                    // Initialize debug monitor if dashboard is active
                    const dashboardSection = document.getElementById('developer-dashboard');
                    if (dashboardSection && dashboardSection.classList.contains('active') && !haystackDebug.isInitialized) {
                        console.log('🎯 Initializing debug monitor from service check...');
                        haystackDebug.initialize();
                    }
                };
            }
            
            console.log('🎉 Haystack Performance DEBUG integration completed!');
            console.log('📍 Navigate to Developer Dashboard to see the Haystack Performance card');
        }
    }, 100);
    
    // Timeout after 10 seconds
    setTimeout(() => {
        clearInterval(integrationInterval);
        console.warn('⏰ Timeout waiting for dashboard - debug integration may have failed');
    }, 10000);
}

// Initialize debug integration
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', integrateHaystackDebug);
} else {
    integrateHaystackDebug();
}

console.log('🔧 Haystack Performance Debug script loaded');
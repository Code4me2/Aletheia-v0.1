# Haystack Performance Dashboard Integration

Complete integration of Haystack performance monitoring into the Data Compose developer dashboard, providing real-time monitoring, job management, and performance optimization for bulk document processing.

## Overview

This integration refits the standalone Haystack performance monitoring system into the existing Data Compose UI, maintaining the familiar interface while adding powerful bulk processing capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Compose Frontend                        │
│                     (localhost:8080)                           │
├─────────────────────────────────────────────────────────────────┤
│  Developer Dashboard                                            │
│  ├── Service Status Card (existing)                            │
│  ├── Quick Actions Card (existing)                             │
│  ├── System Info Card (existing)                               │
│  ├── Haystack Performance Card (NEW) ←──────────────────┐      │
│  ├── Logs & Monitoring Card (existing)                  │      │
│  └── RAG Testing Card (existing)                        │      │
└──────────────────────────────────────────────────────────┘      │
                                                           │      │
┌─────────────────────────────────────────────────────────────────┐      │
│              Dashboard Integration API                  │      │
│                  (localhost:8001)                       │      │
├─────────────────────────────────────────────────────────────────┤      │
│  FastAPI Service with CORS                              │ ←────┘
│  ├── /health - Service health check                     │
│  ├── /performance/overview - Dashboard metrics          │
│  ├── /performance/metrics - Detailed metrics            │
│  ├── /jobs - Job status and management                  │
│  └── /jobs/start - Start ingestion jobs                 │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│              Enhanced Haystack Backend                  │
│  ├── Bulk Ingestion Service                             │
│  ├── Performance Monitor                                │
│  ├── Metadata Processor                                 │
│  └── Integration Manager                                │
└─────────────────────────────────────────────────────────────────┘
```

## Features Added to Developer Dashboard

### 🎯 **Haystack Performance Card**

**Location**: New card in the dashboard grid (inserted before RAG Testing card)

**Key Metrics Display**:
- **System Status**: Real-time CPU, memory usage with color-coded indicators
- **Document Processing**: Total processed, success rate, error count  
- **Performance**: Throughput (docs/hour), average processing time
- **Alerts**: Recent performance alerts and warnings

**Quick Actions**:
- **Detailed Metrics**: Opens modal with comprehensive performance data
- **Refresh**: Manual data refresh
- **Job Management**: Collapsible section for managing ingestion jobs

### 📊 **Job Management Interface**

**Jobs Summary**:
- Active, total, completed, and failed job counts
- Real-time progress tracking for active jobs
- Recent job history with status indicators

**Job Actions**:
- **Quick Start**: One-click "Ingest New Documents" 
- **Custom Jobs**: Dialog for judge-specific or date-filtered ingestion
- **Job Monitoring**: Real-time progress bars and status updates

### 🔍 **Detailed Metrics Modal**

**Tabbed Interface**:
- **System Tab**: CPU/memory trends, resource utilization
- **Performance Tab**: Processing time statistics, throughput analysis
- **Connections Tab**: Database pool status, service connectivity
- **Recommendations Tab**: Automated performance optimization suggestions

## Installation & Setup

### 1. **File Structure**

The integration adds these key files:

```
court-processor/
├── enhanced/web/
│   ├── dashboard_integration.py    # FastAPI backend service
│   ├── Dockerfile                  # Container configuration
│   └── requirements.txt           # Python dependencies
├── docker-compose.dashboard.yml   # Service configuration
└── README_DASHBOARD_INTEGRATION.md

website/
├── js/haystack-performance.js     # Frontend JavaScript
├── css/haystack-performance.css   # Styling
└── index.html                     # Updated with new includes
```

### 2. **Environment Configuration**

Add to your `.env` file:

```bash
# Haystack Dashboard Integration
HAYSTACK_DASHBOARD_PORT=8001
```

### 3. **Start the Integration Service**

**Option A: Docker Compose (Recommended)**
```bash
# Start alongside existing services
docker-compose -f docker-compose.yml -f court-processor/docker-compose.dashboard.yml up -d

# Or start just the dashboard service
docker-compose -f court-processor/docker-compose.dashboard.yml up -d
```

**Option B: Direct Python**
```bash
cd court-processor
pip install -r enhanced/web/requirements.txt
python -m uvicorn enhanced.web.dashboard_integration:DashboardIntegrationAPI.app --host 0.0.0.0 --port 8001
```

### 4. **Verify Integration**

1. **Access Data Compose**: http://localhost:8080
2. **Navigate to Developer Dashboard**
3. **Check for Haystack Performance Card**: Should appear automatically
4. **Test API**: http://localhost:8001/health should return service status

## Usage Guide

### **Real-Time Monitoring**

The dashboard automatically:
- **Updates every 30 seconds** with fresh performance data
- **Shows system health** with color-coded status indicators  
- **Displays active jobs** with real-time progress tracking
- **Monitors alerts** and performance degradation

### **Starting Ingestion Jobs**

**Quick Ingestion**:
```javascript
// From the dashboard UI
1. Expand "Show Jobs" section
2. Click "Ingest New Documents" 
3. Monitor progress in real-time
```

**Custom Jobs**:
```javascript
// Judge-specific ingestion
1. Click "Start Custom Job"
2. Select "ingest_judge"
3. Enter judge name (e.g., "Gilstrap")
4. Optionally specify court ID (e.g., "txed")
```

**Programmatic API**:
```bash
# Start new documents ingestion
curl -X POST http://localhost:8001/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"type": "ingest_new"}'

# Start judge-specific ingestion  
curl -X POST http://localhost:8001/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"type": "ingest_judge", "judge_name": "Gilstrap", "court_id": "txed"}'

# Start recent documents (last 7 days)
curl -X POST http://localhost:8001/jobs/start \
  -H "Content-Type: application/json" \
  -d '{"type": "ingest_recent", "days": 7}'
```

### **Performance Analysis**

**Dashboard Metrics**:
- **Green Status**: System healthy, low error rate
- **Yellow Status**: Performance degraded, elevated resource usage
- **Red Status**: High error rate or system overload

**Detailed Metrics Modal**:
- **System Trends**: 30-minute CPU/memory history
- **Timing Analysis**: Mean, min, max processing times by operation
- **Connection Health**: Database pool utilization and status
- **Recommendations**: Automated suggestions for optimization

## Integration with Existing Services

### **Service Status Integration**

The Haystack performance monitoring integrates with the existing service status system:

```javascript
// Existing service check pattern maintained
checkService('http://localhost:8001/health', 'haystack-performance-status', 'Haystack Performance', false);

// Enhanced with performance metrics
{
  "status": "healthy",
  "service": "haystack_performance", 
  "details": {
    "active_jobs": 2,
    "total_jobs": 15,
    "services": {
      "elasticsearch": {"connected": true},
      "postgresql": {"connected": true}
    }
  }
}
```

### **Data Flow Integration**

The dashboard connects existing Data Compose workflows:

1. **Court Document Processing** → Enhanced Unified Document Processor
2. **Bulk Ingestion** → Haystack Integration Manager  
3. **Search & Retrieval** → Elasticsearch via RAG Testing interface
4. **Monitoring** → Performance Dashboard in Developer UI

## API Reference

### **Health Check**
```http
GET /health
```
Returns service health status compatible with existing Data Compose service monitoring.

### **Performance Overview**
```http
GET /performance/overview
```
Returns dashboard metrics:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_hours": 12.5,
  "system": {
    "cpu_percent": 45.2,
    "memory_mb": 1024.5,
    "memory_percent": 62.1
  },
  "processing": {
    "total_documents": 15432,
    "successful_documents": 15200,
    "error_count": 232,
    "error_rate": 1.5
  },
  "performance": {
    "avg_processing_time": 2.3,
    "throughput_last_hour": 450.2
  },
  "status_indicator": "healthy"
}
```

### **Job Management**
```http
GET /jobs                    # List all jobs
POST /jobs/start            # Start new job
GET /jobs/{job_id}          # Get job details
```

### **Detailed Metrics**
```http
GET /performance/metrics    # Comprehensive performance data
```

## Styling & UI Integration

### **CSS Integration**

The performance monitoring uses existing Data Compose design tokens:

```css
/* Maintains consistent styling */
.dashboard-card { /* Uses existing card pattern */ }
.performance-metric { /* Follows dashboard metric styling */ }
.job-item { /* Consistent with service items */ }

/* Color-coded status indicators */
.text-success { color: var(--success); }
.text-warning { color: var(--warning); }  
.text-error { color: var(--error); }
```

### **Responsive Design**

- **Desktop**: 2-column grid layout in dashboard
- **Tablet**: Responsive grid, collapsible sections
- **Mobile**: Single-column layout, touch-friendly controls

### **Dark Mode Support**

Full compatibility with existing dark mode toggle:
- Uses CSS custom properties from main theme
- Automatic color scheme adaptation
- High contrast mode support

## Performance & Optimization

### **Frontend Optimization**

- **Lazy Loading**: Performance card loads only when dashboard is active
- **Caching**: 30-second client-side cache for API responses
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Resource Cleanup**: Stops timers when switching away from dashboard

### **Backend Optimization**

- **Connection Pooling**: Shared database connections across requests
- **Response Caching**: Metrics cached for 30 seconds to reduce load
- **Async Operations**: Non-blocking I/O for all database operations
- **Error Resilience**: Graceful degradation when services unavailable

### **Network Efficiency**

- **CORS Optimization**: Minimal preflight requests
- **JSON Compression**: Gzip compression for large responses
- **Request Batching**: Multiple metrics in single API call
- **WebSocket Ready**: Future real-time updates via WebSocket

## Monitoring & Alerting

### **Built-in Alerts**

The dashboard automatically alerts on:
- **High CPU Usage**: >90% sustained
- **Memory Pressure**: >85% memory utilization  
- **Error Rate**: >5% processing errors
- **Low Throughput**: <1 document/second sustained

### **Alert Display**

Alerts appear in multiple places:
- **Performance Card**: Recent alerts section
- **Detailed Modal**: Full alert history
- **Browser Notifications**: Optional toast notifications
- **Status Indicators**: Color-coded visual feedback

### **External Integration**

Ready for external monitoring:
```bash
# Prometheus metrics endpoint (planned)
curl http://localhost:8001/metrics

# Health check for monitoring systems
curl http://localhost:8001/health
```

## Troubleshooting

### **Common Issues**

**1. Performance Card Not Appearing**
```bash
# Check if CSS/JS files are loaded
curl http://localhost:8080/css/haystack-performance.css
curl http://localhost:8080/js/haystack-performance.js

# Verify API service is running
curl http://localhost:8001/health
```

**2. CORS Errors**
```bash
# Ensure API allows Data Compose origin
# Check browser console for CORS policy errors
# Verify API is running on localhost:8001
```

**3. Performance Data Not Loading**
```bash
# Check API connectivity
curl http://localhost:8001/performance/overview

# Verify backend services are running
docker-compose ps
```

**4. Jobs Not Starting**
```bash
# Check PostgreSQL connection
curl http://localhost:8001/health

# Verify Enhanced Unified Document Processor is available
# Check court-processor services are running
```

### **Debug Mode**

Enable detailed logging:
```javascript
// In browser console
localStorage.setItem('haystack-debug', 'true');
// Reload page to see detailed logs
```

```python
# In API service
import logging
logging.getLogger("dashboard_integration").setLevel(logging.DEBUG)
```

## Future Enhancements

### **Planned Features**

- **Real-time WebSocket Updates**: Live job progress without polling
- **Advanced Visualizations**: Interactive charts for performance trends  
- **Bulk Job Scheduling**: Cron-like scheduling for regular ingestion
- **Performance Profiling**: Detailed breakdown of processing bottlenecks
- **Alert Configuration**: User-configurable alert thresholds

### **Integration Roadmap**

- **Grafana Dashboard**: Export metrics to Grafana for advanced visualization
- **Prometheus Metrics**: Native Prometheus metrics endpoint
- **Slack Notifications**: Alert integration with Slack/Teams
- **Mobile App**: React Native companion app for monitoring

### **API Extensions**

- **GraphQL Support**: Flexible query interface for custom dashboards
- **Webhook Integration**: Event-driven notifications to external systems
- **Bulk API Operations**: Batch job management for enterprise workflows
- **Custom Metrics**: User-defined performance indicators

## Support & Maintenance

### **Logging**

All components use structured logging:
```python
logger.info("Performance data updated", 
           cpu_percent=45.2, 
           memory_mb=1024.5, 
           active_jobs=2)
```

### **Health Monitoring**

Built-in health checks for all components:
- **API Service**: `/health` endpoint with dependency checks
- **Database Connections**: Connection pool health monitoring  
- **Background Tasks**: Job queue health verification
- **Resource Usage**: System resource monitoring with alerts

### **Version Compatibility**

- **Data Compose**: Compatible with current Data Compose UI architecture
- **Python**: Requires Python 3.9+ for async features
- **Docker**: Compatible with Docker Compose v2
- **Browsers**: Modern browsers with ES6+ support

This integration provides a seamless, production-ready performance monitoring solution that enhances the existing Data Compose developer dashboard while maintaining the familiar interface and design patterns.
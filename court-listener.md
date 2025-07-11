# Advanced Court Data Retrieval Manual for Aletheia v0.1
## CourtListener/RECAP Archive Integration Guide

### Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [CourtListener API Authentication](#authentication)
4. [Court Identifiers](#court-identifiers)
5. [Implementation Architecture](#architecture)
6. [Phase 1: Initial Bulk Retrieval](#bulk-retrieval)
7. [Phase 2: Scheduled Retrieval Mechanism](#scheduled-retrieval)
8. [Webhook Integration for Real-Time Updates](#webhooks)
9. [Rate Limiting Strategy](#rate-limiting)
10. [Data Storage and Processing](#data-storage)
11. [Testing and Monitoring](#testing)
12. [Deployment](#deployment)

---

## 1. Overview {#overview}

This manual provides comprehensive instructions for implementing advanced court data retrieval capabilities in the Aletheia v0.1 project using the CourtListener/RECAP Archive API. The implementation will support:

- Initial bulk data retrieval for targeted IP courts
- Scheduled retrieval mechanism with intelligent rate limiting
- Comprehensive court coverage across federal district and appellate courts

### Key Features
- **API Rate Limit Compliance**: Stays within 5,000 requests/hour limit
- **Automated Scheduling**: Continuous data collection across jurisdictions
- **Scalable Architecture**: Microservices-based design for easy expansion
- **Error Handling**: Robust retry mechanisms and failure recovery

---

## 2. Prerequisites {#prerequisites}

### Required Components
1. **CourtListener Account**: Register at https://www.courtlistener.com/
2. **API Token**: Obtain from your CourtListener profile
3. **Python 3.10+**: For court processor implementation
4. **PostgreSQL**: Database with court_data schema (already configured)
5. **Docker**: For containerized deployment

### System Requirements
- 4GB+ RAM for processing
- 50GB+ storage for PDF documents and metadata
- Stable internet connection for API calls

---

## 3. CourtListener API Authentication {#authentication}

### Setting Up Authentication

1. **Obtain API Token**:
   ```bash
   # Add to .env file
   COURTLISTENER_API_TOKEN=your-token-here
   ```

2. **Configure Headers**:
   ```python
   headers = {
       'Authorization': f'Token {COURTLISTENER_API_TOKEN}',
       'User-Agent': 'Aletheia-v0.1/1.0 (https://github.com/Code4me2/Aletheia-v0.1)'
   }
   ```

### API Endpoints
- **Base URL**: `https://www.courtlistener.com/api/rest/v4/`
- **Case Law**: `/clusters/`, `/opinions/`, `/dockets/`
- **Search**: `/search/`
- **Courts**: `/courts/`

---

## 4. Court Identifiers {#court-identifiers}

### Target Courts and Their CourtListener IDs

| Court Name | CourtListener ID | Jurisdiction Type |
|------------|-----------------|-------------------|
| District of Delaware | `deld` | Federal District |
| Eastern District of Texas | `txed` | Federal District |
| Northern District of California | `cand` | Federal District |
| Court of Appeals for the Federal Circuit | `cafc` | Federal Appellate |

### Additional IP-Heavy Courts to Consider
- Central District of California: `cacd`
- Southern District of New York: `nysd`
- District of New Jersey: `njd`

---

## 5. Implementation Architecture {#architecture}

### Component Structure

```
court-processor/
├── courtlistener_integration/
│   ├── __init__.py
│   ├── api_client.py          # CourtListener API wrapper
│   ├── bulk_retriever.py      # Initial bulk data retrieval
│   ├── scheduled_retriever.py # Scheduled incremental updates
│   ├── rate_limiter.py        # Rate limiting implementation
│   └── data_processor.py      # Process and store retrieved data
├── config/
│   ├── courts.yaml            # Court configurations
│   └── schedule.yaml          # Retrieval schedule
└── scripts/
    ├── init_bulk_retrieval.py
    └── start_scheduler.py
```

---

## 6. Phase 1: Initial Bulk Retrieval {#bulk-retrieval}

### Implementation Steps

#### 6.1 Create API Client (`api_client.py`)

```python
import requests
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin
import logging

class CourtListenerClient:
    """CourtListener API client with built-in rate limiting"""
    
    BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
    
    def __init__(self, api_token: str, requests_per_hour: int = 4500):
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0'
        })
        self.requests_per_hour = requests_per_hour
        self.request_times = []
        self.logger = logging.getLogger(__name__)
    
    def _rate_limit(self):
        """Implement token bucket rate limiting"""
        current_time = time.time()
        # Remove requests older than 1 hour
        self.request_times = [t for t in self.request_times 
                            if current_time - t < 3600]
        
        if len(self.request_times) >= self.requests_per_hour:
            sleep_time = 3600 - (current_time - self.request_times[0]) + 1
            self.logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
            self.request_times = []
        
        self.request_times.append(current_time)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request with rate limiting"""
        self._rate_limit()
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise
    
    def paginate(self, endpoint: str, params: Optional[Dict] = None, 
                 max_pages: Optional[int] = None) -> List[Dict]:
        """Paginate through all results"""
        results = []
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
                
            page_params = {**(params or {}), 'page': page}
            data = self.get(endpoint, page_params)
            
            if 'results' in data:
                results.extend(data['results'])
                
                if not data.get('next'):
                    break
                    
                page += 1
            else:
                # Single object response
                results.append(data)
                break
                
        return results
```

#### 6.2 Bulk Retrieval Implementation (`bulk_retriever.py`)

```python
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from courtlistener_integration.api_client import CourtListenerClient
from courtlistener_integration.data_processor import DataProcessor

class BulkRetriever:
    """Handle initial bulk retrieval of court data"""
    
    def __init__(self, api_client: CourtListenerClient, data_processor: DataProcessor):
        self.api = api_client
        self.processor = data_processor
        self.logger = logging.getLogger(__name__)
        
    def retrieve_court_dockets(self, court_id: str, 
                             date_from: datetime = None,
                             date_to: datetime = None) -> List[Dict]:
        """Retrieve all dockets for a specific court"""
        params = {
            'court': court_id,
            'order_by': '-date_modified'
        }
        
        if date_from:
            params['date_filed__gte'] = date_from.isoformat()
        if date_to:
            params['date_filed__lte'] = date_to.isoformat()
            
        self.logger.info(f"Retrieving dockets for court {court_id}")
        dockets = self.api.paginate('dockets/', params=params)
        
        return dockets
    
    def retrieve_docket_details(self, docket_id: int) -> Dict:
        """Retrieve detailed information for a specific docket"""
        # Get docket entries
        entries = self.api.paginate(f'docket-entries/', 
                                  params={'docket': docket_id})
        
        # Get parties
        parties = self.api.paginate(f'parties/', 
                                  params={'docket': docket_id})
        
        # Get documents if available
        documents = []
        for entry in entries:
            if entry.get('recap_documents'):
                for doc_url in entry['recap_documents']:
                    doc_data = self.api.get(doc_url)
                    documents.append(doc_data)
        
        return {
            'entries': entries,
            'parties': parties,
            'documents': documents
        }
    
    def retrieve_opinions_for_court(self, court_id: str,
                                  date_from: datetime = None) -> List[Dict]:
        """Retrieve opinions (case law) for a specific court"""
        params = {
            'cluster__docket__court': court_id,
            'order_by': '-date_created'
        }
        
        if date_from:
            params['date_created__gte'] = date_from.isoformat()
            
        opinions = self.api.paginate('opinions/', params=params)
        return opinions
    
    async def bulk_retrieve_all_courts(self, court_ids: List[str],
                                     lookback_days: int = 365):
        """Perform bulk retrieval for all specified courts"""
        date_from = datetime.now() - timedelta(days=lookback_days)
        
        for court_id in court_ids:
            self.logger.info(f"Starting bulk retrieval for {court_id}")
            
            # Retrieve dockets
            dockets = self.retrieve_court_dockets(court_id, date_from=date_from)
            self.logger.info(f"Retrieved {len(dockets)} dockets for {court_id}")
            
            # Process and store dockets
            for docket in dockets:
                self.processor.process_docket(docket)
                
                # Optionally retrieve detailed information for important cases
                if self._is_patent_case(docket):
                    details = self.retrieve_docket_details(docket['id'])
                    self.processor.process_docket_details(docket['id'], details)
            
            # Retrieve opinions
            opinions = self.retrieve_opinions_for_court(court_id, date_from=date_from)
            self.logger.info(f"Retrieved {len(opinions)} opinions for {court_id}")
            
            for opinion in opinions:
                self.processor.process_opinion(opinion)
    
    def _is_patent_case(self, docket: Dict) -> bool:
        """Determine if a docket is a patent case"""
        # Check nature of suit codes for patent cases
        nos = docket.get('nature_of_suit', '')
        patent_nos_codes = ['830', '835', '840']  # Patent case codes
        
        case_name = docket.get('case_name', '').lower()
        patent_keywords = ['patent', 'infringement', '35 u.s.c.']
        
        return (nos in patent_nos_codes or 
                any(keyword in case_name for keyword in patent_keywords))
```

#### 6.3 Configure Courts (`config/courts.yaml`)

```yaml
courts:
  - id: deld
    name: "District of Delaware"
    type: district
    priority: high
    bulk_retrieval:
      enabled: true
      lookback_days: 730  # 2 years
      filter_patent_cases: true
    
  - id: txed
    name: "Eastern District of Texas"
    type: district
    priority: high
    bulk_retrieval:
      enabled: true
      lookback_days: 730
      filter_patent_cases: true
    
  - id: cand
    name: "Northern District of California"
    type: district
    priority: high
    bulk_retrieval:
      enabled: true
      lookback_days: 730
      filter_patent_cases: true
    
  - id: cafc
    name: "Court of Appeals for the Federal Circuit"
    type: appellate
    priority: high
    bulk_retrieval:
      enabled: true
      lookback_days: 1095  # 3 years for appellate
      filter_patent_cases: false  # All cases are relevant

# Additional courts for future expansion
additional_courts:
  - id: cacd
    name: "Central District of California"
    priority: medium
    
  - id: nysd
    name: "Southern District of New York"
    priority: medium
```

---

## 7. Phase 2: Scheduled Retrieval Mechanism {#scheduled-retrieval}

### 7.1 Scheduler Implementation (`scheduled_retriever.py`)

```python
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List
import yaml
import logging
from courtlistener_integration.api_client import CourtListenerClient
from courtlistener_integration.data_processor import DataProcessor

class ScheduledRetriever:
    """Implement scheduled retrieval with intelligent distribution"""
    
    def __init__(self, api_client: CourtListenerClient, 
                 data_processor: DataProcessor,
                 config_path: str = 'config/schedule.yaml'):
        self.api = api_client
        self.processor = data_processor
        self.logger = logging.getLogger(__name__)
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.court_schedule = self._create_court_schedule()
        
    def _create_court_schedule(self) -> Dict[str, Dict]:
        """Create an optimized schedule for court data retrieval"""
        courts = self.config['courts']
        schedule_config = self.config['schedule']
        
        # Distribute courts across time slots to maximize API usage
        # while staying under rate limits
        court_schedule = {}
        
        # High priority courts - check multiple times per day
        high_priority = [c for c in courts if c['priority'] == 'high']
        medium_priority = [c for c in courts if c['priority'] == 'medium']
        low_priority = [c for c in courts if c['priority'] == 'low']
        
        # Assign time slots
        for idx, court in enumerate(high_priority):
            court_schedule[court['id']] = {
                'times': ['06:00', '12:00', '18:00', '22:00'],
                'lookback_hours': 6,
                'max_requests': 200
            }
            
        for idx, court in enumerate(medium_priority):
            court_schedule[court['id']] = {
                'times': ['08:00', '20:00'],
                'lookback_hours': 12,
                'max_requests': 150
            }
            
        for idx, court in enumerate(low_priority):
            court_schedule[court['id']] = {
                'times': ['10:00'],
                'lookback_hours': 24,
                'max_requests': 100
            }
            
        return court_schedule
    
    def check_court_updates(self, court_id: str):
        """Check for updates in a specific court"""
        schedule_info = self.court_schedule[court_id]
        lookback = datetime.now() - timedelta(hours=schedule_info['lookback_hours'])
        
        self.logger.info(f"Checking updates for {court_id} since {lookback}")
        
        # Check for new/modified dockets
        params = {
            'court': court_id,
            'date_modified__gte': lookback.isoformat(),
            'order_by': '-date_modified'
        }
        
        dockets = self.api.paginate('dockets/', params=params, 
                                  max_pages=schedule_info['max_requests']//20)
        
        for docket in dockets:
            self.processor.process_docket(docket)
            
        # Check for new opinions
        opinion_params = {
            'cluster__docket__court': court_id,
            'date_created__gte': lookback.isoformat(),
            'order_by': '-date_created'
        }
        
        opinions = self.api.paginate('opinions/', params=opinion_params,
                                   max_pages=schedule_info['max_requests']//20)
        
        for opinion in opinions:
            self.processor.process_opinion(opinion)
            
        self.logger.info(f"Processed {len(dockets)} dockets and {len(opinions)} opinions for {court_id}")
    
    def setup_schedule(self):
        """Set up the scheduled tasks"""
        for court_id, schedule_info in self.court_schedule.items():
            for check_time in schedule_info['times']:
                schedule.every().day.at(check_time).do(
                    self.check_court_updates, court_id=court_id
                )
        
        # Add a daily comprehensive check
        schedule.every().day.at("03:00").do(self.daily_comprehensive_check)
        
        # Add webhook listener check
        schedule.every(5).minutes.do(self.check_webhook_updates)
        
    def daily_comprehensive_check(self):
        """Perform a comprehensive daily check across all courts"""
        self.logger.info("Starting daily comprehensive check")
        
        for court_id in self.court_schedule.keys():
            self.check_court_updates(court_id)
            
        # Clean up old data
        self.processor.cleanup_old_data(days=90)
        
        # Generate statistics
        self.processor.generate_daily_stats()
    
    def check_webhook_updates(self):
        """Check for any webhook notifications (if configured)"""
        # CourtListener supports webhooks for real-time updates
        # This would integrate with their webhook system
        # Webhooks are sent immediately for RECAP data
        # Case law webhooks are sent with the alert emails
        pass
    
    def run(self):
        """Run the scheduler"""
        self.setup_schedule()
        self.logger.info("Scheduler started")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
```

### 7.2 Schedule Configuration (`config/schedule.yaml`)

```yaml
schedule:
  # Global settings
  rate_limit_buffer: 0.9  # Use 90% of rate limit
  requests_per_hour: 4500  # Leave buffer from 5000 limit
  
  # Court priority levels
  priorities:
    high:
      check_frequency: 4  # times per day
      max_requests_per_check: 200
      lookback_hours: 6
      
    medium:
      check_frequency: 2
      max_requests_per_check: 150
      lookback_hours: 12
      
    low:
      check_frequency: 1
      max_requests_per_check: 100
      lookback_hours: 24

courts:
  - id: deld
    priority: high
    
  - id: txed
    priority: high
    
  - id: cand
    priority: high
    
  - id: cafc
    priority: high
    
  - id: cacd
    priority: medium
    
  - id: nysd
    priority: medium

# Webhook configuration (if available)
webhooks:
  enabled: true
  endpoint: "https://your-domain.com/webhook/courtlistener"
  secret: "generate-long-random-string-here"
  allowed_ips:
    - "34.210.230.218"
    - "54.189.59.91"
```

---

## 8. Webhook Integration for Real-Time Updates {#webhooks}

CourtListener's webhook system enables real-time notifications without polling, significantly improving efficiency and reducing API usage.

### 8.1 Webhook Types

CourtListener supports several webhook event types:

1. **Docket Alerts**: Immediate notifications when cases are updated
2. **Search Alerts**: Notifications for new search results
3. **RECAP Fetch**: Completion notifications for PACER downloads
4. **Expired Alerts**: Notifications when alerts on old cases expire

### 8.2 Webhook Endpoint Implementation

Create `webhook_handler.py`:

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import logging
from datetime import datetime
from courtlistener_integration.data_processor import DataProcessor

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Allowed IPs from CourtListener
ALLOWED_IPS = ['34.210.230.218', '54.189.59.91']

class WebhookHandler:
    """Handle incoming webhooks from CourtListener"""
    
    def __init__(self, data_processor: DataProcessor):
        self.processor = data_processor
        self.logger = logging.getLogger(__name__)
    
    def verify_webhook(self, request_data):
        """Verify webhook is from CourtListener"""
        # Check IP address
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip not in ALLOWED_IPS:
            self.logger.warning(f"Webhook from unauthorized IP: {client_ip}")
            return False
        
        # Check headers
        event_type = request.headers.get('X-Courtlistener-Webhook-Event-Type')
        idempotency_key = request.headers.get('Idempotency-Key')
        
        if not event_type or not idempotency_key:
            self.logger.warning("Missing required webhook headers")
            return False
            
        return True
    
    def process_webhook(self, event_type: str, payload: dict, 
                       idempotency_key: str) -> bool:
        """Process webhook event"""
        # Check if already processed
        if self._is_duplicate(idempotency_key):
            self.logger.info(f"Duplicate webhook: {idempotency_key}")
            return True
        
        try:
            if event_type == 'docket_alert':
                self._process_docket_alert(payload)
            elif event_type == 'search_alert':
                self._process_search_alert(payload)
            elif event_type == 'recap_fetch':
                self._process_recap_fetch(payload)
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                
            # Mark as processed
            self._mark_processed(idempotency_key)
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}")
            return False
    
    def _process_docket_alert(self, payload: dict):
        """Process docket alert webhook"""
        docket_data = payload.get('docket', {})
        docket_entries = payload.get('docket_entries', [])
        
        self.logger.info(f"Processing docket alert for {docket_data.get('id')}")
        
        # Process the docket
        self.processor.process_docket(docket_data)
        
        # Process new entries
        for entry in docket_entries:
            self.processor._process_docket_entry(
                None, docket_data['id'], entry
            )
    
    def _process_search_alert(self, payload: dict):
        """Process search alert webhook"""
        alert_info = payload.get('alert', {})
        results = payload.get('results', {}).get('results', [])
        
        self.logger.info(f"Processing search alert: {alert_info.get('name')}")
        
        for result in results:
            if result.get('type') == 'r':  # RECAP document
                # Process RECAP results
                docket_id = result.get('docket_id')
                if docket_id:
                    # Fetch and process full docket information
                    self.processor.fetch_and_process_docket(docket_id)
            elif result.get('type') == 'o':  # Opinion
                # Process opinion
                self.processor.process_opinion(result)
    
    def _process_recap_fetch(self, payload: dict):
        """Process RECAP fetch completion webhook"""
        fetch_info = payload.get('recap_fetch', {})
        status = fetch_info.get('status')
        
        if status == 'success':
            document_url = fetch_info.get('filepath_local')
            if document_url:
                # Process the downloaded document
                self.processor.process_recap_document(document_url)
    
    def _is_duplicate(self, idempotency_key: str) -> bool:
        """Check if webhook has already been processed"""
        # Query database or cache
        with self.processor.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM court_data.webhook_events 
                    WHERE idempotency_key = :key
                """),
                {'key': idempotency_key}
            ).scalar()
            return result > 0
    
    def _mark_processed(self, idempotency_key: str):
        """Mark webhook as processed"""
        with self.processor.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO court_data.webhook_events 
                    (idempotency_key, processed_at)
                    VALUES (:key, NOW())
                    ON CONFLICT (idempotency_key) DO NOTHING
                """),
                {'key': idempotency_key}
            )
            conn.commit()

# Flask routes
webhook_handler = WebhookHandler(DataProcessor(DATABASE_URL))

@app.route('/webhook/courtlistener', methods=['POST'])
def courtlistener_webhook():
    """Endpoint for CourtListener webhooks"""
    
    # Verify webhook
    if not webhook_handler.verify_webhook(request):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get webhook data
    event_type = request.headers.get('X-Courtlistener-Webhook-Event-Type')
    idempotency_key = request.headers.get('Idempotency-Key')
    payload = request.get_json()
    
    # Process asynchronously to avoid timeouts
    # In production, use a task queue like Celery
    success = webhook_handler.process_webhook(
        event_type, payload, idempotency_key
    )
    
    if success:
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'error': 'Processing failed'}), 500

@app.before_request
def limit_remote_addr():
    """Restrict access to allowed IPs"""
    if request.endpoint == 'courtlistener_webhook':
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip not in ALLOWED_IPS:
            abort(403)
```

### 8.3 Setting Up Webhooks in CourtListener

1. **Create Search Alerts via API**:
```python
def create_search_alert_with_webhook(self, query: str, name: str):
    """Create a search alert that triggers webhooks"""
    
    alert_data = {
        'name': name,
        'query': query,
        'rate': 'rt',  # Real-time
        'alert_type': 'r'  # RECAP documents and dockets
    }
    
    response = self.api.session.post(
        'https://www.courtlistener.com/api/rest/v4/alerts/',
        json=alert_data
    )
    
    alert_id = response.json()['id']
    return alert_id
```

2. **Create Docket Alerts**:
```python
def create_docket_alert(self, docket_id: int):
    """Create a docket alert for real-time updates"""
    
    alert_data = {
        'docket': docket_id
    }
    
    response = self.api.session.post(
        'https://www.courtlistener.com/api/rest/v4/docket-alerts/',
        json=alert_data
    )
    
    return response.json()
```

3. **Configure Webhook Endpoints**:
   - Log into CourtListener
   - Navigate to Profile → Webhooks
   - Add webhook endpoint with your URL
   - Select event types (Docket Alert, Search Alert, etc.)
   - Enable the webhook

### 8.4 Database Schema for Webhooks

```sql
-- Webhook events tracking
CREATE TABLE IF NOT EXISTS court_data.webhook_events (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(50),
    payload JSONB,
    processed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_webhook_events_created ON court_data.webhook_events(created_at);

-- Search alerts configuration
CREATE TABLE IF NOT EXISTS court_data.search_alerts (
    alert_id INTEGER PRIMARY KEY,
    court_id VARCHAR(50),
    query TEXT,
    name VARCHAR(255),
    alert_type VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Docket alerts configuration  
CREATE TABLE IF NOT EXISTS court_data.docket_alerts (
    alert_id INTEGER PRIMARY KEY,
    docket_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 8.5 Integrating Webhooks with Scheduled Retrieval

Update the `scheduled_retriever.py` to coordinate with webhooks:

```python
def check_webhook_updates(self):
    """Process any pending webhook notifications"""
    with self.processor.engine.connect() as conn:
        # Get recent webhook events
        recent_events = conn.execute(
            text("""
                SELECT * FROM court_data.webhook_events
                WHERE processed_at > NOW() - INTERVAL '5 minutes'
                AND event_type IN ('docket_alert', 'search_alert')
                ORDER BY processed_at DESC
            """)
        ).fetchall()
        
        # Update last check times for courts with webhook activity
        courts_updated = set()
        for event in recent_events:
            payload = json.loads(event['payload'])
            if 'court_id' in payload:
                courts_updated.add(payload['court_id'])
        
        # Skip regular checks for courts that just had webhook updates
        for court_id in courts_updated:
            self.last_webhook_update[court_id] = datetime.now()
            self.logger.info(f"Skipping scheduled check for {court_id} due to recent webhook")
```

---

## 9. Rate Limiting Strategy {#rate-limiting}

### 8.1 Advanced Rate Limiter (`rate_limiter.py`)

```python
import time
import threading
from collections import deque
from typing import Optional
import logging

class RateLimiter:
    """Thread-safe rate limiter with multiple strategies"""
    
    def __init__(self, requests_per_hour: int = 4500,
                 burst_size: int = 100,
                 min_interval: float = 0.5):
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self.min_interval = min_interval
        
        # Token bucket implementation
        self.tokens = burst_size
        self.max_tokens = burst_size
        self.refill_rate = requests_per_hour / 3600.0
        self.last_refill = time.time()
        
        # Sliding window for request tracking
        self.request_times = deque()
        
        # Thread safety
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, blocking if necessary. Returns wait time."""
        with self.lock:
            wait_time = 0
            
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, 
                            self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Clean old requests from sliding window
            cutoff = now - 3600
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()
            
            # Check sliding window
            if len(self.request_times) >= self.requests_per_hour:
                wait_time = max(wait_time, 
                              3600 - (now - self.request_times[0]) + 0.1)
            
            # Check token bucket
            if self.tokens < tokens:
                tokens_needed = tokens - self.tokens
                wait_time = max(wait_time, tokens_needed / self.refill_rate)
            
            # Check minimum interval
            if self.request_times:
                time_since_last = now - self.request_times[-1]
                if time_since_last < self.min_interval:
                    wait_time = max(wait_time, self.min_interval - time_since_last)
            
            if wait_time > 0:
                self.logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                now = time.time()
                
                # Refill after wait
                elapsed = wait_time
                self.tokens = min(self.max_tokens,
                                self.tokens + elapsed * self.refill_rate)
            
            # Consume tokens
            self.tokens -= tokens
            self.request_times.append(now)
            
            return wait_time
    
    def get_current_rate(self) -> Dict[str, float]:
        """Get current rate limiting statistics"""
        with self.lock:
            now = time.time()
            cutoff = now - 3600
            recent_requests = sum(1 for t in self.request_times if t > cutoff)
            
            return {
                'requests_last_hour': recent_requests,
                'tokens_available': self.tokens,
                'current_rate': recent_requests / 3600.0 if recent_requests > 0 else 0,
                'rate_limit_percentage': (recent_requests / self.requests_per_hour) * 100
            }
```

---

## 10. Data Storage and Processing {#data-storage}

### 9.1 Data Processor (`data_processor.py`)

```python
import json
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
from sqlalchemy import create_engine, text
import logging

class DataProcessor:
    """Process and store court data in PostgreSQL"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.logger = logging.getLogger(__name__)
        
    def process_docket(self, docket_data: Dict) -> int:
        """Process and store docket information"""
        # Extract key fields
        docket_id = docket_data['id']
        court_id = docket_data.get('court_id') or docket_data['court'].split('/')[-2]
        
        processed_data = {
            'docket_id': docket_id,
            'court_id': court_id,
            'case_name': docket_data.get('case_name', ''),
            'case_number': docket_data.get('docket_number', ''),
            'date_filed': docket_data.get('date_filed'),
            'date_terminated': docket_data.get('date_terminated'),
            'nature_of_suit': docket_data.get('nature_of_suit', ''),
            'cause': docket_data.get('cause', ''),
            'jury_demand': docket_data.get('jury_demand', ''),
            'jurisdiction_type': docket_data.get('jurisdiction_type', ''),
            'assigned_to': self._extract_judge_info(docket_data.get('assigned_to_str')),
            'referred_to': self._extract_judge_info(docket_data.get('referred_to_str')),
            'pacer_case_id': docket_data.get('pacer_case_id'),
            'source': docket_data.get('source'),
            'date_created': docket_data.get('date_created'),
            'date_modified': docket_data.get('date_modified'),
            'raw_data': json.dumps(docket_data),
            'hash': self._generate_hash(docket_data)
        }
        
        # Check if docket already exists
        with self.engine.connect() as conn:
            existing = conn.execute(
                text("SELECT docket_id FROM court_data.dockets WHERE docket_id = :id"),
                {'id': docket_id}
            ).fetchone()
            
            if existing:
                # Update if modified
                if self._has_changed(conn, 'dockets', docket_id, processed_data['hash']):
                    conn.execute(
                        text("""
                            UPDATE court_data.dockets 
                            SET case_name = :case_name,
                                date_modified = :date_modified,
                                raw_data = :raw_data,
                                hash = :hash,
                                updated_at = NOW()
                            WHERE docket_id = :docket_id
                        """),
                        processed_data
                    )
                    conn.commit()
                    self.logger.info(f"Updated docket {docket_id}")
            else:
                # Insert new docket
                conn.execute(
                    text("""
                        INSERT INTO court_data.dockets 
                        (docket_id, court_id, case_name, case_number, date_filed,
                         date_terminated, nature_of_suit, cause, jury_demand,
                         jurisdiction_type, assigned_to, referred_to, pacer_case_id,
                         source, date_created, date_modified, raw_data, hash)
                        VALUES 
                        (:docket_id, :court_id, :case_name, :case_number, :date_filed,
                         :date_terminated, :nature_of_suit, :cause, :jury_demand,
                         :jurisdiction_type, :assigned_to, :referred_to, :pacer_case_id,
                         :source, :date_created, :date_modified, :raw_data, :hash)
                    """),
                    processed_data
                )
                conn.commit()
                self.logger.info(f"Inserted new docket {docket_id}")
        
        return docket_id
    
    def process_opinion(self, opinion_data: Dict) -> int:
        """Process and store opinion (case law) information"""
        opinion_id = opinion_data['id']
        
        # Extract cluster information
        cluster_url = opinion_data.get('cluster')
        cluster_id = cluster_url.split('/')[-2] if cluster_url else None
        
        processed_data = {
            'opinion_id': opinion_id,
            'cluster_id': cluster_id,
            'author_str': opinion_data.get('author_str', ''),
            'per_curiam': opinion_data.get('per_curiam', False),
            'type': opinion_data.get('type', ''),
            'sha1': opinion_data.get('sha1', ''),
            'download_url': opinion_data.get('download_url', ''),
            'local_path': opinion_data.get('local_path', ''),
            'plain_text': opinion_data.get('plain_text', ''),
            'html': opinion_data.get('html', ''),
            'html_lawbox': opinion_data.get('html_lawbox', ''),
            'html_columbia': opinion_data.get('html_columbia', ''),
            'xml_harvard': opinion_data.get('xml_harvard', ''),
            'date_created': opinion_data.get('date_created'),
            'date_modified': opinion_data.get('date_modified'),
            'raw_data': json.dumps(opinion_data),
            'hash': self._generate_hash(opinion_data)
        }
        
        with self.engine.connect() as conn:
            # Store opinion
            conn.execute(
                text("""
                    INSERT INTO court_data.opinions 
                    (opinion_id, cluster_id, author_str, per_curiam, type,
                     sha1, download_url, local_path, plain_text, html,
                     html_lawbox, html_columbia, xml_harvard,
                     date_created, date_modified, raw_data, hash)
                    VALUES 
                    (:opinion_id, :cluster_id, :author_str, :per_curiam, :type,
                     :sha1, :download_url, :local_path, :plain_text, :html,
                     :html_lawbox, :html_columbia, :xml_harvard,
                     :date_created, :date_modified, :raw_data, :hash)
                    ON CONFLICT (opinion_id) DO UPDATE SET
                        date_modified = EXCLUDED.date_modified,
                        raw_data = EXCLUDED.raw_data,
                        hash = EXCLUDED.hash,
                        updated_at = NOW()
                """),
                processed_data
            )
            conn.commit()
            
        return opinion_id
    
    def process_docket_details(self, docket_id: int, details: Dict):
        """Process detailed docket information (entries, parties, documents)"""
        with self.engine.connect() as conn:
            # Process docket entries
            for entry in details.get('entries', []):
                self._process_docket_entry(conn, docket_id, entry)
            
            # Process parties
            for party in details.get('parties', []):
                self._process_party(conn, docket_id, party)
            
            # Process documents
            for doc in details.get('documents', []):
                self._process_document(conn, doc)
            
            conn.commit()
    
    def _process_docket_entry(self, conn, docket_id: int, entry: Dict):
        """Process individual docket entry"""
        entry_data = {
            'entry_id': entry['id'],
            'docket_id': docket_id,
            'date_filed': entry.get('date_filed'),
            'entry_number': entry.get('entry_number'),
            'recap_sequence_number': entry.get('recap_sequence_number'),
            'pacer_sequence_number': entry.get('pacer_sequence_number'),
            'description': entry.get('description', ''),
            'short_description': entry.get('short_description', ''),
            'document_count': len(entry.get('recap_documents', [])),
            'raw_data': json.dumps(entry)
        }
        
        conn.execute(
            text("""
                INSERT INTO court_data.docket_entries
                (entry_id, docket_id, date_filed, entry_number,
                 recap_sequence_number, pacer_sequence_number,
                 description, short_description, document_count, raw_data)
                VALUES
                (:entry_id, :docket_id, :date_filed, :entry_number,
                 :recap_sequence_number, :pacer_sequence_number,
                 :description, :short_description, :document_count, :raw_data)
                ON CONFLICT (entry_id) DO UPDATE SET
                    description = EXCLUDED.description,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = NOW()
            """),
            entry_data
        )
    
    def _extract_judge_info(self, judge_str: Optional[str]) -> Optional[str]:
        """Extract judge name from string"""
        if not judge_str:
            return None
        
        # Remove common prefixes
        prefixes = ['Judge', 'Magistrate Judge', 'Hon.', 'Honorable']
        for prefix in prefixes:
            if judge_str.startswith(prefix):
                judge_str = judge_str[len(prefix):].strip()
                
        return judge_str
    
    def _generate_hash(self, data: Dict) -> str:
        """Generate hash of data for change detection"""
        # Remove volatile fields
        stable_data = {k: v for k, v in data.items() 
                      if k not in ['date_modified', 'date_created', 'id']}
        
        data_str = json.dumps(stable_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _has_changed(self, conn, table: str, record_id: int, new_hash: str) -> bool:
        """Check if record has changed based on hash"""
        result = conn.execute(
            text(f"SELECT hash FROM court_data.{table} WHERE {table[:-1]}_id = :id"),
            {'id': record_id}
        ).fetchone()
        
        return not result or result[0] != new_hash
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data based on retention policy"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    DELETE FROM court_data.api_logs 
                    WHERE created_at < NOW() - INTERVAL ':days days'
                """),
                {'days': days}
            )
            conn.commit()
    
    def generate_daily_stats(self):
        """Generate daily statistics"""
        with self.engine.connect() as conn:
            stats = {}
            
            # Count by court
            result = conn.execute(
                text("""
                    SELECT court_id, COUNT(*) as count
                    FROM court_data.dockets
                    WHERE date_created >= CURRENT_DATE - INTERVAL '1 day'
                    GROUP BY court_id
                """)
            ).fetchall()
            
            stats['new_dockets_by_court'] = {row[0]: row[1] for row in result}
            
            # Total counts
            stats['total_dockets'] = conn.execute(
                text("SELECT COUNT(*) FROM court_data.dockets")
            ).scalar()
            
            stats['total_opinions'] = conn.execute(
                text("SELECT COUNT(*) FROM court_data.opinions")
            ).scalar()
            
            # Store stats
            conn.execute(
                text("""
                    INSERT INTO court_data.daily_stats (date, stats)
                    VALUES (CURRENT_DATE, :stats)
                    ON CONFLICT (date) DO UPDATE SET
                        stats = EXCLUDED.stats,
                        updated_at = NOW()
                """),
                {'stats': json.dumps(stats)}
            )
            conn.commit()
            
            self.logger.info(f"Daily stats: {stats}")
```

### 9.2 Database Schema Updates

```sql
-- Add to existing court_data schema

-- Dockets table
CREATE TABLE IF NOT EXISTS court_data.dockets (
    docket_id BIGINT PRIMARY KEY,
    court_id VARCHAR(50) NOT NULL,
    case_name TEXT,
    case_number VARCHAR(255),
    date_filed DATE,
    date_terminated DATE,
    nature_of_suit VARCHAR(10),
    cause TEXT,
    jury_demand VARCHAR(50),
    jurisdiction_type VARCHAR(50),
    assigned_to VARCHAR(255),
    referred_to VARCHAR(255),
    pacer_case_id VARCHAR(100),
    source INTEGER,
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    raw_data JSONB,
    hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dockets_court_id ON court_data.dockets(court_id);
CREATE INDEX idx_dockets_date_filed ON court_data.dockets(date_filed);
CREATE INDEX idx_dockets_date_modified ON court_data.dockets(date_modified);
CREATE INDEX idx_dockets_case_name_gin ON court_data.dockets USING gin(to_tsvector('english', case_name));

-- Opinions table
CREATE TABLE IF NOT EXISTS court_data.opinions (
    opinion_id BIGINT PRIMARY KEY,
    cluster_id BIGINT,
    author_str VARCHAR(255),
    per_curiam BOOLEAN DEFAULT FALSE,
    type VARCHAR(50),
    sha1 VARCHAR(40),
    download_url TEXT,
    local_path TEXT,
    plain_text TEXT,
    html TEXT,
    html_lawbox TEXT,
    html_columbia TEXT,
    xml_harvard TEXT,
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    raw_data JSONB,
    hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_opinions_cluster_id ON court_data.opinions(cluster_id);
CREATE INDEX idx_opinions_author ON court_data.opinions(author_str);
CREATE INDEX idx_opinions_text_gin ON court_data.opinions USING gin(to_tsvector('english', plain_text));

-- Docket entries table
CREATE TABLE IF NOT EXISTS court_data.docket_entries (
    entry_id BIGINT PRIMARY KEY,
    docket_id BIGINT REFERENCES court_data.dockets(docket_id),
    date_filed DATE,
    entry_number INTEGER,
    recap_sequence_number VARCHAR(50),
    pacer_sequence_number INTEGER,
    description TEXT,
    short_description TEXT,
    document_count INTEGER DEFAULT 0,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_entries_docket_id ON court_data.docket_entries(docket_id);
CREATE INDEX idx_entries_date_filed ON court_data.docket_entries(date_filed);

-- Parties table
CREATE TABLE IF NOT EXISTS court_data.parties (
    party_id BIGINT PRIMARY KEY,
    docket_id BIGINT REFERENCES court_data.dockets(docket_id),
    party_type VARCHAR(50),
    name TEXT,
    extra_info TEXT,
    date_terminated DATE,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parties_docket_id ON court_data.parties(docket_id);
CREATE INDEX idx_parties_name ON court_data.parties(name);

-- API logs table for monitoring
CREATE TABLE IF NOT EXISTS court_data.api_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms INTEGER,
    court_id VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_logs_created_at ON court_data.api_logs(created_at);
CREATE INDEX idx_api_logs_court_id ON court_data.api_logs(court_id);

-- Daily statistics table
CREATE TABLE IF NOT EXISTS court_data.daily_stats (
    date DATE PRIMARY KEY,
    stats JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables
CREATE TRIGGER update_dockets_updated_at BEFORE UPDATE ON court_data.dockets
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
    
CREATE TRIGGER update_opinions_updated_at BEFORE UPDATE ON court_data.opinions
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
    
CREATE TRIGGER update_entries_updated_at BEFORE UPDATE ON court_data.docket_entries
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
    
CREATE TRIGGER update_parties_updated_at BEFORE UPDATE ON court_data.parties
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
```

---

## 11. Testing and Monitoring {#testing}

### 10.1 Test Suite (`tests/test_courtlistener_integration.py`)

```python
import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from courtlistener_integration.api_client import CourtListenerClient
from courtlistener_integration.bulk_retriever import BulkRetriever
from courtlistener_integration.scheduled_retriever import ScheduledRetriever
from courtlistener_integration.rate_limiter import RateLimiter

class TestCourtListenerIntegration:
    """Test suite for CourtListener integration"""
    
    @pytest.fixture
    def api_client(self):
        return CourtListenerClient('test-token', requests_per_hour=100)
    
    @pytest.fixture
    def mock_processor(self):
        processor = Mock()
        processor.process_docket.return_value = 12345
        processor.process_opinion.return_value = 67890
        return processor
    
    def test_rate_limiter_respects_limits(self):
        """Test that rate limiter properly enforces limits"""
        limiter = RateLimiter(requests_per_hour=100, burst_size=10)
        
        # Should allow burst
        for _ in range(10):
            wait_time = limiter.acquire()
            assert wait_time == 0
        
        # Should start throttling
        wait_time = limiter.acquire()
        assert wait_time > 0
    
    @patch('requests.Session.get')
    def test_api_client_pagination(self, mock_get, api_client):
        """Test API client pagination handling"""
        # Mock paginated response
        mock_get.side_effect = [
            Mock(json=lambda: {
                'results': [{'id': 1}, {'id': 2}],
                'next': 'https://example.com/page2'
            }),
            Mock(json=lambda: {
                'results': [{'id': 3}],
                'next': None
            })
        ]
        
        results = api_client.paginate('test-endpoint/')
        assert len(results) == 3
        assert results[0]['id'] == 1
        assert results[-1]['id'] == 3
    
    @pytest.mark.asyncio
    async def test_bulk_retriever(self, api_client, mock_processor):
        """Test bulk retrieval process"""
        retriever = BulkRetriever(api_client, mock_processor)
        
        with patch.object(api_client, 'paginate') as mock_paginate:
            mock_paginate.return_value = [
                {'id': 1, 'case_name': 'Test v. Case'},
                {'id': 2, 'case_name': 'Patent v. Infringement'}
            ]
            
            await retriever.bulk_retrieve_all_courts(['deld'], lookback_days=7)
            
            assert mock_processor.process_docket.call_count == 2
    
    def test_scheduled_retriever_schedule_creation(self, api_client, mock_processor):
        """Test schedule creation for courts"""
        retriever = ScheduledRetriever(api_client, mock_processor)
        
        assert 'deld' in retriever.court_schedule
        assert len(retriever.court_schedule['deld']['times']) == 4  # High priority
    
    def test_data_processor_deduplication(self, mock_processor):
        """Test that processor handles duplicate data correctly"""
        # This would test the actual DataProcessor implementation
        pass
    
    @patch('requests.Session.get')
    def test_error_handling(self, mock_get, api_client):
        """Test error handling and retry logic"""
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            api_client.get('test-endpoint/')
    
    def test_court_identification(self):
        """Test court ID extraction and validation"""
        test_cases = [
            ('https://courtlistener.com/api/rest/v4/courts/deld/', 'deld'),
            ('https://courtlistener.com/api/rest/v4/courts/txed/', 'txed'),
        ]
        
        for url, expected_id in test_cases:
            court_id = url.split('/')[-2]
            assert court_id == expected_id
```

### 10.2 Monitoring Setup (`monitoring/courtlistener_monitor.py`)

```python
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging
from functools import wraps
import time

# Define metrics
api_requests_total = Counter('courtlistener_api_requests_total', 
                           'Total API requests', 
                           ['endpoint', 'court', 'status'])

api_request_duration = Histogram('courtlistener_api_request_duration_seconds',
                               'API request duration',
                               ['endpoint'])

rate_limit_usage = Gauge('courtlistener_rate_limit_usage_percent',
                        'Current rate limit usage percentage')

documents_processed = Counter('courtlistener_documents_processed_total',
                            'Total documents processed',
                            ['type', 'court'])

active_courts = Gauge('courtlistener_active_courts',
                     'Number of courts being monitored')

last_successful_check = Gauge('courtlistener_last_successful_check_timestamp',
                            'Timestamp of last successful check',
                            ['court'])

class MonitoringMixin:
    """Mixin to add monitoring to API client"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        
    def monitored_request(endpoint: str):
        """Decorator to monitor API requests"""
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                start_time = time.time()
                status = 'success'
                court = kwargs.get('court_id', 'unknown')
                
                try:
                    result = func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    status = 'error'
                    self.logger.error(f"API request failed: {e}")
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    api_requests_total.labels(
                        endpoint=endpoint,
                        court=court,
                        status=status
                    ).inc()
                    
                    api_request_duration.labels(
                        endpoint=endpoint
                    ).observe(duration)
                    
                    # Update rate limit usage
                    if hasattr(self, 'get_current_rate'):
                        stats = self.get_current_rate()
                        rate_limit_usage.set(stats['rate_limit_percentage'])
            
            return wrapper
        return decorator
    
    @monitored_request('dockets')
    def get_dockets(self, court_id: str, **kwargs):
        return super().get('dockets/', params={'court': court_id, **kwargs})
    
    @monitored_request('opinions')
    def get_opinions(self, court_id: str, **kwargs):
        return super().get('opinions/', 
                         params={'cluster__docket__court': court_id, **kwargs})

def start_monitoring_server(port: int = 9090):
    """Start Prometheus metrics server"""
    start_http_server(port)
    logging.info(f"Monitoring server started on port {port}")
```

---

## 12. Deployment {#deployment}

### 11.1 Docker Integration

Create `court-processor/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 processor && \
    chown -R processor:processor /app

USER processor

# Default command
CMD ["python", "-m", "courtlistener_integration.scheduled_retriever"]
```

### 11.2 Docker Compose Integration

Add to existing `docker-compose.yml`:

```yaml
  courtlistener-processor:
    build: ./court-processor
    container_name: courtlistener-processor
    environment:
      - COURTLISTENER_API_TOKEN=${COURTLISTENER_API_TOKEN}
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - LOG_LEVEL=INFO
    volumes:
      - ./court-data:/app/court-data
      - ./court-processor/config:/app/config
    depends_on:
      - db
    networks:
      - backend
    restart: unless-stopped

  courtlistener-monitor:
    build: 
      context: ./court-processor
      dockerfile: Dockerfile.monitor
    container_name: courtlistener-monitor
    ports:
      - "9091:9090"  # Prometheus metrics
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
    depends_on:
      - courtlistener-processor
    networks:
      - backend
```

### 11.3 Environment Configuration

Update `.env` file:

```bash
# CourtListener Configuration
COURTLISTENER_API_TOKEN=your-courtlistener-api-token
COURTLISTENER_RATE_LIMIT=4500
COURTLISTENER_BURST_SIZE=100

# Court Processor Configuration
COURT_PROCESSOR_LOG_LEVEL=INFO
COURT_PROCESSOR_WORKERS=2
COURT_PROCESSOR_BULK_LOOKBACK_DAYS=730
```

### 11.4 Initialization Scripts

Create `scripts/init_courtlistener.sh`:

```bash
#!/bin/bash
set -e

echo "Initializing CourtListener integration..."

# Run database migrations
docker-compose exec db psql -U $DB_USER -d $DB_NAME -f /court-processor/scripts/init_courtlistener_schema.sql

# Perform initial bulk retrieval
docker-compose exec courtlistener-processor python -m scripts.init_bulk_retrieval

# Start scheduler
docker-compose exec -d courtlistener-processor python -m scripts.start_scheduler

echo "CourtListener integration initialized successfully!"
```

### 11.5 Operational Commands

```bash
# Start the court processor
docker-compose up -d courtlistener-processor

# View logs
docker-compose logs -f courtlistener-processor

# Manually trigger court check
docker-compose exec courtlistener-processor python -c "
from courtlistener_integration.scheduled_retriever import ScheduledRetriever
retriever = ScheduledRetriever()
retriever.check_court_updates('deld')
"

# Check rate limit status
docker-compose exec courtlistener-processor python -c "
from courtlistener_integration.api_client import CourtListenerClient
client = CourtListenerClient()
print(client.get_current_rate())
"

# Generate statistics report
docker-compose exec courtlistener-processor python -m scripts.generate_stats_report
```

---

## Appendix A: Troubleshooting

### Common Issues and Solutions

1. **Rate Limit Exceeded**
   - Check current usage: `GET /api/rest/v4/` with OPTIONS
   - Reduce `requests_per_hour` in configuration
   - Implement exponential backoff

2. **Authentication Failed**
   - Verify API token is correct
   - Check token hasn't expired
   - Ensure proper header format: `Authorization: Token YOUR_TOKEN`

3. **Missing Data**
   - Some courts may have limited historical data
   - Check CourtListener coverage page
   - Consider using bulk data downloads for historical data

4. **Database Performance**
   - Add appropriate indexes
   - Implement partitioning for large tables
   - Regular VACUUM and ANALYZE

---

## Appendix B: Additional Resources

### Official Documentation
- CourtListener API: https://www.courtlistener.com/help/api/rest/
- RECAP Archive: https://www.courtlistener.com/help/recap/
- Bulk Data: https://www.courtlistener.com/help/api/bulk-data/

### Community Resources
- GitHub Discussions: https://github.com/freelawproject/courtlistener/discussions
- Free Law Project Blog: https://free.law/blog/

### Related Projects
- Juriscraper: https://github.com/freelawproject/juriscraper
- Courts-DB: https://github.com/freelawproject/courts-db
- Reporters-DB: https://github.com/freelawproject/reporters-db

---

## Conclusion

This manual provides a comprehensive guide for implementing advanced court data retrieval capabilities in the Aletheia project. The system is designed to be:

- **Scalable**: Easy to add new courts and expand coverage
- **Reliable**: Robust error handling and retry mechanisms
- **Efficient**: Optimized API usage within rate limits
- **Maintainable**: Clean architecture and comprehensive monitoring

For questions or support, consult the Aletheia project documentation or contact the development team.

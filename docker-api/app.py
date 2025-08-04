#!/usr/bin/env python3
"""
Simple Docker API service for Aletheia dashboard
Provides basic Docker operations: logs, stats, restart
"""

import json
import subprocess
import os
import re
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Docker service names from docker-compose
DOCKER_SERVICES = [
    'web', 'db', 'n8n', 'redis', 'lawyer-chat', 
    'ai-portal', 'ai-portal-nginx', 'court-processor',
    'recap-webhook', 'elasticsearch', 'haystack-service',
    'docker-api'
]

def run_docker_command(cmd):
    """Execute docker command safely"""
    try:
        print(f"Running command: {cmd}")
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        print(f"Command returned: {result.returncode}, stdout length: {len(result.stdout)}")
        if result.returncode != 0:
            print(f"Error output: {result.stderr}")
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': 'Command timed out',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'returncode': -1
        }

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/docker/test', methods=['GET'])
def test_command():
    """Test docker command execution"""
    cmd = "docker ps --format '{{.Names}}'"
    result = run_docker_command(cmd)
    return jsonify({
        'success': result['success'],
        'output': result['output'],
        'error': result['error'],
        'lines': result['output'].strip().split('\n') if result['success'] else []
    })

@app.route('/api/docker/logs/<service>', methods=['GET'])
def get_logs(service):
    """Get Docker logs for a service"""
    if service not in DOCKER_SERVICES:
        return jsonify({'error': f'Unknown service: {service}'}), 400
    
    lines = request.args.get('lines', '100')
    follow = request.args.get('follow', 'false').lower() == 'true'
    
    # Build docker logs command
    cmd = f"cd /workspace && docker compose logs --tail={lines}"
    if follow:
        cmd += " -f"
    cmd += f" {service}"
    
    result = run_docker_command(cmd)
    
    if result['success']:
        return jsonify({
            'service': service,
            'logs': result['output'],
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({
            'error': f'Failed to get logs: {result["error"]}',
            'service': service
        }), 500

@app.route('/api/docker/stats', methods=['GET'])
def get_stats():
    """Get Docker container stats"""
    # Use simpler command without table format
    cmd = "docker stats --no-stream --format \"{{.Container}}|||{{.CPUPerc}}|||{{.MemUsage}}|||{{.MemPerc}}|||{{.NetIO}}|||{{.BlockIO}}\""
    
    result = run_docker_command(cmd)
    
    if result['success']:
        # Parse stats output into JSON
        lines = result['output'].strip().split('\n')
        
        headers = ['container', 'cpu_percent', 'memory_usage', 'memory_percent', 'network_io', 'block_io']
        stats = []
        
        for line in lines:
            # Split by our custom delimiter
            parts = line.split('|||')
            if len(parts) == 6:
                stats.append(dict(zip(headers, parts)))
        
        return jsonify({
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    else:
        print(f"Failed to get stats: {result['error']}")
        return jsonify({
            'error': f'Failed to get stats: {result["error"]}'
        }), 500

@app.route('/api/docker/restart/<service>', methods=['POST'])
def restart_service(service):
    """Restart a Docker service"""
    if service not in DOCKER_SERVICES:
        return jsonify({'error': f'Unknown service: {service}'}), 400
    
    cmd = f"docker-compose restart {service}"
    result = run_docker_command(cmd)
    
    if result['success']:
        return jsonify({
            'message': f'Service {service} restarted successfully',
            'service': service,
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({
            'error': f'Failed to restart service: {result["error"]}',
            'service': service
        }), 500

@app.route('/api/docker/services', methods=['GET'])
def list_services():
    """List all available services"""
    return jsonify({
        'services': DOCKER_SERVICES,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/docker/config', methods=['GET'])
def get_config():
    """Get basic configuration information (non-sensitive)"""
    try:
        config_info = {}
        
        # Read docker-compose.yml to get service information
        if os.path.exists('/workspace/docker-compose.yml'):
            config_info['docker_compose_exists'] = True
        else:
            config_info['docker_compose_exists'] = False
        
        # Get environment variables (filter out sensitive ones)
        env_vars = {}
        sensitive_keys = ['password', 'secret', 'key', 'token', 'auth']
        
        for key, value in os.environ.items():
            # Only include environment variables that start with known prefixes
            if any(key.upper().startswith(prefix) for prefix in ['DB_', 'N8N_', 'WEB_', 'AI_', 'HAYSTACK_', 'ELASTICSEARCH_']):
                # Filter out sensitive variables
                is_sensitive = any(sensitive in key.lower() for sensitive in sensitive_keys)
                if is_sensitive:
                    env_vars[key] = '***HIDDEN***'
                else:
                    env_vars[key] = value
        
        # Get Docker Compose project name
        project_name = os.environ.get('COMPOSE_PROJECT_NAME', 'aletheia-v01')
        
        return jsonify({
            'environment_variables': env_vars,
            'project_name': project_name,
            'services_available': DOCKER_SERVICES,
            'config_file_exists': config_info['docker_compose_exists'],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get configuration: {str(e)}'
        }), 500

@app.route('/api/docker/status', methods=['GET'])
def docker_status():
    """Get overall Docker Compose status"""
    cmd = "docker-compose ps --format json"
    result = run_docker_command(cmd)
    
    if result['success']:
        try:
            # Parse JSON output
            services = []
            for line in result['output'].strip().split('\n'):
                if line.strip():
                    services.append(json.loads(line))
            
            return jsonify({
                'services': services,
                'timestamp': datetime.now().isoformat()
            })
        except json.JSONDecodeError:
            return jsonify({
                'error': 'Failed to parse Docker status',
                'raw_output': result['output']
            }), 500
    else:
        return jsonify({
            'error': f'Failed to get Docker status: {result["error"]}'
        }), 500

@app.route('/api/docker/logs/all', methods=['GET'])
def get_all_logs():
    """Get logs for all services with structured parsing"""
    lines = request.args.get('lines', '50')
    
    all_logs = {}
    for service in DOCKER_SERVICES:
        cmd = f"cd /workspace && docker compose logs --tail={lines} {service} 2>&1"
        result = run_docker_command(cmd)
        
        if result['success']:
            logs = result['output']
            # Parse logs to extract timestamp, level, and message
            parsed_logs = parse_log_lines(logs, service)
            all_logs[service] = {
                'raw': logs,
                'parsed': parsed_logs,
                'has_error': any(log.get('level') == 'ERROR' for log in parsed_logs),
                'has_warning': any(log.get('level') == 'WARNING' for log in parsed_logs),
                'line_count': len(parsed_logs)
            }
        else:
            all_logs[service] = {
                'raw': '',
                'parsed': [],
                'error': result['error'],
                'has_error': False,
                'has_warning': False,
                'line_count': 0
            }
    
    return jsonify({
        'services': all_logs,
        'timestamp': datetime.now().isoformat()
    })

def parse_log_lines(logs, service):
    """Parse log lines to extract timestamp, level, and message"""
    lines = logs.strip().split('\n')
    parsed = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Try to extract log level
        level = 'INFO'
        upper_line = line.upper()
        if 'ERROR' in upper_line or 'FATAL' in upper_line or 'CRITICAL' in upper_line:
            level = 'ERROR'
        elif 'WARNING' in upper_line or 'WARN' in upper_line:
            level = 'WARNING'
        elif 'DEBUG' in upper_line:
            level = 'DEBUG'
        
        # Try to extract timestamp (common formats)
        timestamp = None
        # ISO format: 2024-01-01T12:00:00
        iso_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
        if iso_match:
            timestamp = iso_match.group()
        else:
            # Common log format: [2024-01-01 12:00:00]
            bracket_match = re.search(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', line)
            if bracket_match:
                timestamp = bracket_match.group().strip('[]')
        
        parsed.append({
            'timestamp': timestamp,
            'level': level,
            'message': line,
            'service': service
        })
    
    return parsed

@app.route('/api/docker/health', methods=['GET'])
def get_service_health():
    """Get health status of all services based on container state and logs"""
    health_status = {}
    
    # First get container states
    cmd = "docker ps -a --format '{{.Names}}|{{.Status}}'"
    result = run_docker_command(cmd)
    
    container_status = {}
    if result['success']:
        for line in result['output'].strip().split('\n'):
            if '|' in line:
                name, status = line.split('|', 1)
                container_status[name] = 'running' if 'Up' in status else 'stopped'
    
    # Get recent logs to check for errors
    for service in DOCKER_SERVICES:
        # Check if container exists and is running
        is_running = False
        for container_name, status in container_status.items():
            if service in container_name or container_name in service:
                is_running = (status == 'running')
                break
        
        # Get recent logs
        cmd = f"cd /workspace && docker compose logs --tail=50 {service} 2>&1"
        result = run_docker_command(cmd)
        
        has_error = False
        has_warning = False
        
        if result['success'] and result['output']:
            lines = result['output'].strip().split('\n')[-20:]  # Last 20 lines
            for line in lines:
                upper_line = line.upper()
                if any(word in upper_line for word in ['ERROR', 'FATAL', 'CRITICAL', 'EXCEPTION']):
                    has_error = True
                elif any(word in upper_line for word in ['WARNING', 'WARN']):
                    has_warning = True
        
        # Determine health status
        if not is_running:
            status = 'stopped'
        elif has_error:
            status = 'error'
        elif has_warning:
            status = 'warning'
        else:
            status = 'healthy'
        
        health_status[service] = {
            'status': status,
            'is_running': is_running,
            'has_recent_errors': has_error,
            'has_recent_warnings': has_warning
        }
    
    return jsonify({
        'services': health_status,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/docker/logs/all', methods=['GET'])
def get_all_logs():
    """Get logs for all services with structured parsing"""
    lines = request.args.get('lines', '50')
    
    all_logs = {}
    for service in DOCKER_SERVICES:
        cmd = f"cd /workspace && docker compose logs --tail={lines} {service} 2>&1"
        result = run_docker_command(cmd)
        
        if result['success']:
            logs = result['output']
            # Parse logs to extract timestamp, level, and message
            parsed_logs = parse_log_lines(logs, service)
            all_logs[service] = {
                'raw': logs,
                'parsed': parsed_logs,
                'has_error': any(log.get('level') == 'ERROR' for log in parsed_logs),
                'has_warning': any(log.get('level') == 'WARNING' for log in parsed_logs),
                'line_count': len(parsed_logs)
            }
        else:
            all_logs[service] = {
                'raw': '',
                'parsed': [],
                'error': result['error'],
                'has_error': False,
                'has_warning': False,
                'line_count': 0
            }
    
    return jsonify({
        'services': all_logs,
        'timestamp': datetime.now().isoformat()
    })

def parse_log_lines(logs, service):
    """Parse log lines to extract timestamp, level, and message"""
    lines = logs.strip().split('\n')
    parsed = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Try to extract log level
        level = 'INFO'
        upper_line = line.upper()
        if 'ERROR' in upper_line or 'FATAL' in upper_line or 'CRITICAL' in upper_line:
            level = 'ERROR'
        elif 'WARNING' in upper_line or 'WARN' in upper_line:
            level = 'WARNING'
        elif 'DEBUG' in upper_line:
            level = 'DEBUG'
        
        # Try to extract timestamp (common formats)
        timestamp = None
        # ISO format: 2024-01-01T12:00:00
        iso_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
        if iso_match:
            timestamp = iso_match.group()
        else:
            # Common log format: [2024-01-01 12:00:00]
            bracket_match = re.search(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', line)
            if bracket_match:
                timestamp = bracket_match.group().strip('[]')
        
        parsed.append({
            'timestamp': timestamp,
            'level': level,
            'message': line,
            'service': service
        })
    
    return parsed

@app.route('/api/docker/health', methods=['GET'])
def get_service_health():
    """Get health status of all services based on container state and logs"""
    health_status = {}
    
    # First get container states
    cmd = "docker ps -a --format '{{.Names}}|{{.Status}}'"
    result = run_docker_command(cmd)
    
    container_status = {}
    if result['success']:
        for line in result['output'].strip().split('\n'):
            if '|' in line:
                name, status = line.split('|', 1)
                container_status[name] = 'running' if 'Up' in status else 'stopped'
    
    # Get recent logs to check for errors
    for service in DOCKER_SERVICES:
        # Check if container exists and is running
        is_running = False
        for container_name, status in container_status.items():
            if service in container_name or container_name in service:
                is_running = (status == 'running')
                break
        
        # Get recent logs
        cmd = f"cd /workspace && docker compose logs --tail=50 {service} 2>&1"
        result = run_docker_command(cmd)
        
        has_error = False
        has_warning = False
        
        if result['success'] and result['output']:
            lines = result['output'].strip().split('\n')[-20:]  # Last 20 lines
            for line in lines:
                upper_line = line.upper()
                if any(word in upper_line for word in ['ERROR', 'FATAL', 'CRITICAL', 'EXCEPTION']):
                    has_error = True
                elif any(word in upper_line for word in ['WARNING', 'WARN']):
                    has_warning = True
        
        # Determine health status
        if not is_running:
            status = 'stopped'
        elif has_error:
            status = 'error'
        elif has_warning:
            status = 'warning'
        else:
            status = 'healthy'
        
        health_status[service] = {
            'status': status,
            'is_running': is_running,
            'has_recent_errors': has_error,
            'has_recent_warnings': has_warning
        }
    
    return jsonify({
        'services': health_status,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
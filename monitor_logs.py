#!/usr/bin/env python3
"""
Log monitoring script for the health app
Usage: python monitor_logs.py [PERF|ERROR|INFO|WARN]
"""

import sys
import json
import re
from datetime import datetime
from typing import Dict, Any

def parse_log_line(line: str) -> Dict[str, Any]:
    """Parse a structured log line"""
    try:
        # Extract the JSON part after the log level
        match = re.search(r'(PERF|ERROR|INFO|WARN) \| (.+)', line)
        if match:
            log_type = match.group(1)
            json_data = json.loads(match.group(2))
            return {
                'type': log_type,
                'data': json_data
            }
    except Exception as e:
        print(f"Error parsing log line: {e}")
        return None

def filter_logs(log_type: str = None):
    """Filter and display logs based on type"""
    print(f"Monitoring logs for type: {log_type or 'ALL'}")
    print("=" * 80)
    
    try:
        while True:
            line = input()
            if not line:
                continue
                
            parsed = parse_log_line(line)
            if not parsed:
                continue
                
            # Filter by type if specified
            if log_type and parsed['type'] != log_type:
                continue
                
            # Display the log
            display_log(parsed)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except EOFError:
        print("\nInput ended.")

def display_log(parsed: Dict[str, Any]):
    """Display a parsed log entry"""
    log_type = parsed['type']
    data = parsed['data']
    
    # Color coding
    colors = {
        'PERF': '\033[92m',  # Green
        'ERROR': '\033[91m',  # Red
        'INFO': '\033[94m',   # Blue
        'WARN': '\033[93m'    # Yellow
    }
    reset = '\033[0m'
    
    color = colors.get(log_type, '')
    
    # Format timestamp
    timestamp = data.get('timestamp', '')
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp = dt.strftime('%H:%M:%S')
        except:
            pass
    
    # Display based on log type
    if log_type == 'PERF':
        operation = data.get('operation', 'unknown')
        duration = data.get('duration_ms', 0)
        session_id = data.get('session_id', 'N/A')
        
        print(f"{color}[{timestamp}] PERF{reset} | {operation} | {duration:.2f}ms | Session: {session_id}")
        
        # Show additional context
        if 'response_length' in data:
            print(f"    Response length: {data['response_length']} chars")
        if 'messages_used' in data:
            print(f"    Messages used: {data['messages_used']}")
        if 'plan_type' in data:
            print(f"    Plan type: {data['plan_type']}")
            
    elif log_type == 'ERROR':
        operation = data.get('operation', 'unknown')
        error_type = data.get('error_type', 'unknown')
        error_msg = data.get('error_message', 'unknown')
        session_id = data.get('session_id', 'N/A')
        
        print(f"{color}[{timestamp}] ERROR{reset} | {operation} | {error_type} | Session: {session_id}")
        print(f"    Error: {error_msg}")
        
        if 'duration_ms' in data:
            print(f"    Duration: {data['duration_ms']:.2f}ms")
            
    elif log_type == 'INFO':
        message = data.get('message', '')
        session_id = data.get('session_id', 'N/A')
        
        print(f"{color}[{timestamp}] INFO{reset} | {message} | Session: {session_id}")
        
    elif log_type == 'WARN':
        message = data.get('message', '')
        session_id = data.get('session_id', 'N/A')
        
        print(f"{color}[{timestamp}] WARN{reset} | {message} | Session: {session_id}")

def show_help():
    """Show help information"""
    print("Health App Log Monitor")
    print("=" * 50)
    print("Usage:")
    print("  python monitor_logs.py [PERF|ERROR|INFO|WARN]")
    print("")
    print("Examples:")
    print("  python monitor_logs.py PERF    # Monitor performance logs")
    print("  python monitor_logs.py ERROR   # Monitor error logs")
    print("  python monitor_logs.py         # Monitor all logs")
    print("")
    print("To use with your application:")
    print("  python -m uvicorn app.main:app --reload 2>&1 | python monitor_logs.py PERF")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            show_help()
            sys.exit(0)
        elif sys.argv[1] in ['PERF', 'ERROR', 'INFO', 'WARN']:
            filter_logs(sys.argv[1])
        else:
            print(f"Unknown log type: {sys.argv[1]}")
            show_help()
            sys.exit(1)
    else:
        filter_logs()

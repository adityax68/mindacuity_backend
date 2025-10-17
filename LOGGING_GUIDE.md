# Health App Logging System

## Overview

The health app now includes a comprehensive logging system with structured logs for performance monitoring and error tracking. All logs are in JSON format for easy parsing and analysis.

## Log Types

### 1. PERF (Performance) Logs
Track response times and performance metrics for various operations.

**Format:**
```json
{
  "type": "PERF",
  "operation": "process_chat_message",
  "duration_ms": 1250.45,
  "session_id": "sess_abc123",
  "function": "process_chat_message",
  "status": "success"
}
```

**Key Operations Tracked:**
- `process_chat_message` - Complete chat message processing
- `openai_response_generation` - OpenAI API response time
- `generate_assessment` - Complete assessment generation
- `anthropic_assessment_generation` - Anthropic API response time
- `assessment_database_save` - Database save time
- `session_transfer` - Session transfer time
- `chat_message_complete` - Total chat processing time
- `assessment_complete` - Total assessment time

### 2. ERROR Logs
Track errors with full context and stack traces.

**Format:**
```json
{
  "type": "ERROR",
  "operation": "process_chat_message",
  "error_type": "OpenAIError",
  "error_message": "API rate limit exceeded",
  "session_id": "sess_abc123",
  "duration_ms": 500.25,
  "function": "process_chat_message",
  "status": "error"
}
```

### 3. INFO Logs
Track important events and state changes.

**Format:**
```json
{
  "type": "INFO",
  "message": "Starting chat message processing",
  "session_id": "sess_abc123",
  "message_length": 150
}
```

### 4. WARN Logs
Track warnings and non-critical issues.

**Format:**
```json
{
  "type": "WARN",
  "message": "High response time detected",
  "session_id": "sess_abc123",
  "duration_ms": 5000.0
}
```

## Monitoring Tools

### 1. Real-time Monitoring
```bash
# Monitor all performance logs
python -m uvicorn app.main:app --reload 2>&1 | python monitor_logs.py PERF

# Monitor all error logs
python -m uvicorn app.main:app --reload 2>&1 | python monitor_logs.py ERROR

# Monitor all logs
python -m uvicorn app.main:app --reload 2>&1 | python monitor_logs.py
```

### 2. Log Analysis with Grep
```bash
# Performance logs for specific operation
./grep_logs.sh PERF process_chat_message

# All performance logs
./grep_logs.sh PERF

# Performance summary
./grep_logs.sh PERF '' summary

# Error logs for specific operation
./grep_logs.sh ERROR generate_assessment

# Error summary
./grep_logs.sh ERROR '' summary
```

### 3. Manual Grep Commands
```bash
# Find all performance logs
grep "PERF |" app.log

# Find specific operation performance
grep "PERF |" app.log | grep "process_chat_message"

# Find all errors
grep "ERROR |" app.log

# Find errors for specific session
grep "ERROR |" app.log | grep "sess_abc123"

# Find slow operations (>2 seconds)
grep "PERF |" app.log | jq 'select(.duration_ms > 2000)'
```

## Performance Monitoring

### Key Metrics to Monitor

1. **Chat Response Time**
   - Target: < 3 seconds
   - Alert if: > 5 seconds
   - Operation: `process_chat_message`

2. **OpenAI API Time**
   - Target: < 2 seconds
   - Alert if: > 4 seconds
   - Operation: `openai_response_generation`

3. **Assessment Generation**
   - Target: < 10 seconds
   - Alert if: > 20 seconds
   - Operation: `generate_assessment`

4. **Anthropic API Time**
   - Target: < 5 seconds
   - Alert if: > 10 seconds
   - Operation: `anthropic_assessment_generation`

### Performance Alerts

```bash
# Find slow chat responses
grep "PERF |" app.log | jq 'select(.operation == "process_chat_message" and .duration_ms > 3000)'

# Find slow assessments
grep "PERF |" app.log | jq 'select(.operation == "generate_assessment" and .duration_ms > 10000)'

# Find OpenAI API issues
grep "PERF |" app.log | jq 'select(.operation == "openai_response_generation" and .duration_ms > 4000)'
```

## Error Monitoring

### Common Error Types

1. **OpenAI Errors**
   - Rate limiting
   - API key issues
   - Model unavailability

2. **Anthropic Errors**
   - Rate limiting
   - API key issues
   - Model unavailability

3. **Database Errors**
   - Connection issues
   - Transaction failures
   - Constraint violations

4. **Redis Errors**
   - Connection issues
   - Memory issues
   - Timeout errors

### Error Analysis

```bash
# Count errors by type
grep "ERROR |" app.log | jq -r '.error_type' | sort | uniq -c

# Count errors by operation
grep "ERROR |" app.log | jq -r '.operation' | sort | uniq -c

# Find errors for specific session
grep "ERROR |" app.log | grep "sess_abc123"

# Find recent errors (last hour)
grep "ERROR |" app.log | jq 'select(.timestamp > (now - 3600))'
```

## Log Rotation and Management

### Recommended Setup

1. **Log Rotation**
   ```bash
   # Install logrotate
   sudo apt-get install logrotate
   
   # Create logrotate config
   sudo nano /etc/logrotate.d/health-app
   ```

2. **Logrotate Configuration**
   ```
   /path/to/health_app/backend/app.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
       create 644 app app
   }
   ```

3. **Log Aggregation**
   - Use ELK Stack (Elasticsearch, Logstash, Kibana)
   - Use Fluentd for log forwarding
   - Use Grafana for performance dashboards

## Dashboard Queries

### Grafana Queries (if using ELK Stack)

1. **Average Response Time**
   ```
   avg(duration_ms) by operation
   ```

2. **Error Rate**
   ```
   count(type="ERROR") / count(type="PERF")
   ```

3. **Top Slow Operations**
   ```
   topk(10, avg(duration_ms) by operation)
   ```

4. **Error Count by Type**
   ```
   count(type="ERROR") by error_type
   ```

## Troubleshooting

### High Response Times

1. Check OpenAI API status
2. Check Anthropic API status
3. Check database connection pool
4. Check Redis connection
5. Check server resources (CPU, memory)

### High Error Rates

1. Check API keys and quotas
2. Check database connectivity
3. Check Redis connectivity
4. Check server logs for system errors
5. Check network connectivity

### Session Issues

1. Check Redis for session data
2. Check database for conversation data
3. Check access code validation
4. Check subscription status

## Best Practices

1. **Monitor Key Metrics Daily**
   - Average response times
   - Error rates
   - Session success rates

2. **Set Up Alerts**
   - Response time > 5 seconds
   - Error rate > 5%
   - API quota usage > 80%

3. **Regular Log Analysis**
   - Weekly performance reports
   - Monthly error analysis
   - Quarterly capacity planning

4. **Log Retention**
   - Keep performance logs for 30 days
   - Keep error logs for 90 days
   - Archive old logs for compliance

## Example Commands

```bash
# Monitor performance in real-time
python -m uvicorn app.main:app --reload 2>&1 | python monitor_logs.py PERF

# Get performance summary
./grep_logs.sh PERF '' summary

# Find all errors in last hour
grep "ERROR |" app.log | jq 'select(.timestamp > (now - 3600))'

# Find slowest operations today
grep "PERF |" app.log | jq 'select(.timestamp | startswith("2024-01-15"))' | jq -r '"\(.operation) \(.duration_ms)"' | sort -k2 -nr | head -10
```

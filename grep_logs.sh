#!/bin/bash

# Health App Log Grep Script
# Usage: ./grep_logs.sh [PERF|ERROR] [operation_name]

LOG_TYPE=${1:-"PERF"}
OPERATION=${2:-""}

echo "🔍 Grepping logs for: $LOG_TYPE"
if [ -n "$OPERATION" ]; then
    echo "   Operation: $OPERATION"
fi
echo "=========================================="

# Function to show performance logs
show_perf_logs() {
    if [ -n "$OPERATION" ]; then
        grep "PERF |" | grep "\"operation\":\"$OPERATION\"" | while read line; do
            echo "$line" | jq -r '"\(.timestamp) | \(.operation) | \(.duration_ms)ms | Session: \(.session_id)"'
        done
    else
        grep "PERF |" | while read line; do
            echo "$line" | jq -r '"\(.timestamp) | \(.operation) | \(.duration_ms)ms | Session: \(.session_id)"'
        done
    fi
}

# Function to show error logs
show_error_logs() {
    if [ -n "$OPERATION" ]; then
        grep "ERROR |" | grep "\"operation\":\"$OPERATION\"" | while read line; do
            echo "$line" | jq -r '"\(.timestamp) | \(.operation) | \(.error_type) | Session: \(.session_id) | \(.error_message)"'
        done
    else
        grep "ERROR |" | while read line; do
            echo "$line" | jq -r '"\(.timestamp) | \(.operation) | \(.error_type) | Session: \(.session_id) | \(.error_message)"'
        done
    fi
}

# Function to show performance summary
show_perf_summary() {
    echo "📊 Performance Summary:"
    echo "==================="
    
    # Average response times by operation
    echo "Average Response Times:"
    grep "PERF |" | jq -r '"\(.operation) \(.duration_ms)"' | \
    awk '{sum[$1]+=$2; count[$1]++} END {for (op in sum) printf "  %-30s: %.2fms (avg of %d calls)\n", op, sum[op]/count[op], count[op]}'
    
    echo ""
    echo "Slowest Operations:"
    grep "PERF |" | jq -r '"\(.operation) \(.duration_ms)"' | \
    sort -k2 -nr | head -10 | \
    awk '{printf "  %-30s: %.2fms\n", $1, $2}'
}

# Function to show error summary
show_error_summary() {
    echo "🚨 Error Summary:"
    echo "=================="
    
    # Error count by operation
    echo "Error Count by Operation:"
    grep "ERROR |" | jq -r '.operation' | sort | uniq -c | sort -nr | \
    awk '{printf "  %-30s: %d errors\n", $2, $1}'
    
    echo ""
    echo "Error Count by Type:"
    grep "ERROR |" | jq -r '.error_type' | sort | uniq -c | sort -nr | \
    awk '{printf "  %-30s: %d errors\n", $2, $1}'
}

# Main execution
case $LOG_TYPE in
    "PERF")
        if [ "$3" = "summary" ]; then
            show_perf_summary
        else
            show_perf_logs
        fi
        ;;
    "ERROR")
        if [ "$3" = "summary" ]; then
            show_error_summary
        else
            show_error_logs
        fi
        ;;
    *)
        echo "Usage: $0 [PERF|ERROR] [operation_name] [summary]"
        echo ""
        echo "Examples:"
        echo "  $0 PERF                                    # All performance logs"
        echo "  $0 PERF process_chat_message              # Specific operation"
        echo "  $0 PERF '' summary                         # Performance summary"
        echo "  $0 ERROR generate_assessment               # Specific error operation"
        echo "  $0 ERROR '' summary                        # Error summary"
        exit 1
        ;;
esac

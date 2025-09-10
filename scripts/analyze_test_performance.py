#!/usr/bin/env python3
"""
Test Performance Analysis Script

This script analyzes the performance of test-related queries and provides
recommendations for further optimization.
"""

import os
import time
import psycopg2
from sqlalchemy import create_engine, text
from contextlib import contextmanager

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/health_app')

@contextmanager
def get_db_connection():
    """Get database connection with proper cleanup."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    finally:
        if conn:
            conn.close()

def analyze_query_performance():
    """Analyze performance of key test-related queries."""
    
    print("🔍 ANALYZING TEST QUERY PERFORMANCE")
    print("=" * 50)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Query 1: Test Definitions (Main Dashboard)
        print("\n1. 📊 Test Definitions Query (Main Dashboard)")
        print("-" * 40)
        start_time = time.time()
        cursor.execute("""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT * FROM test_definitions 
            WHERE is_active = true 
            ORDER BY test_name
        """)
        result = cursor.fetchone()[0]
        execution_time = time.time() - start_time
        
        plan = result[0]['Plan']
        print(f"Execution Time: {plan['Actual Total Time']:.2f}ms")
        print(f"Rows Returned: {plan['Actual Rows']}")
        print(f"Index Used: {'Yes' if 'Index' in str(plan) else 'No'}")
        
        # Query 2: Test Definitions by Category
        print("\n2. 🏷️ Test Definitions by Category")
        print("-" * 40)
        start_time = time.time()
        cursor.execute("""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT * FROM test_definitions 
            WHERE is_active = true AND test_category = 'depression'
            ORDER BY test_name
        """)
        result = cursor.fetchone()[0]
        execution_time = time.time() - start_time
        
        plan = result[0]['Plan']
        print(f"Execution Time: {plan['Actual Total Time']:.2f}ms")
        print(f"Rows Returned: {plan['Actual Rows']}")
        print(f"Index Used: {'Yes' if 'Index' in str(plan) else 'No'}")
        
        # Query 3: Test Details (Questions + Options + Scoring)
        print("\n3. 📋 Test Details Query (Questions + Options + Scoring)")
        print("-" * 40)
        start_time = time.time()
        cursor.execute("""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT 
                td.*,
                tq.id as question_id,
                tq.question_number,
                tq.question_text,
                tqo.id as option_id,
                tqo.option_text,
                tqo.option_value,
                tqo.display_order,
                tsr.severity_level,
                tsr.severity_label,
                tsr.interpretation
            FROM test_definitions td
            LEFT JOIN test_questions tq ON td.id = tq.test_definition_id
            LEFT JOIN test_question_options tqo ON tq.id = tqo.question_id
            LEFT JOIN test_scoring_ranges tsr ON td.id = tsr.test_definition_id
            WHERE td.test_code = 'phq9'
            ORDER BY tq.question_number, tqo.display_order, tsr.priority
        """)
        result = cursor.fetchone()[0]
        execution_time = time.time() - start_time
        
        plan = result[0]['Plan']
        print(f"Execution Time: {plan['Actual Total Time']:.2f}ms")
        print(f"Rows Returned: {plan['Actual Rows']}")
        print(f"Index Used: {'Yes' if 'Index' in str(plan) else 'No'}")
        
        # Query 4: User Assessment History
        print("\n4. 📈 User Assessment History")
        print("-" * 40)
        start_time = time.time()
        cursor.execute("""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT ca.*, td.test_name, td.test_code
            FROM clinical_assessments ca
            LEFT JOIN test_definitions td ON ca.test_definition_id = td.id
            WHERE ca.user_id = 1
            ORDER BY ca.created_at DESC
            LIMIT 50
        """)
        result = cursor.fetchone()[0]
        execution_time = time.time() - start_time
        
        plan = result[0]['Plan']
        print(f"Execution Time: {plan['Actual Total Time']:.2f}ms")
        print(f"Rows Returned: {plan['Actual Rows']}")
        print(f"Index Used: {'Yes' if 'Index' in str(plan) else 'No'}")

def check_index_usage():
    """Check which indexes are being used by the queries."""
    
    print("\n🔍 INDEX USAGE ANALYSIS")
    print("=" * 50)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check index usage statistics
        cursor.execute("""
            SELECT 
                schemaname,
                relname as tablename,
                indexrelname as indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes 
            WHERE relname IN ('test_definitions', 'test_questions', 'test_question_options', 'test_scoring_ranges', 'clinical_assessments')
            ORDER BY idx_scan DESC
        """)
        
        indexes = cursor.fetchall()
        
        print("\nIndex Usage Statistics:")
        print("-" * 30)
        for index in indexes:
            schema, table, name, scans, reads, fetches = index
            print(f"Table: {table}")
            print(f"Index: {name}")
            print(f"Scans: {scans}, Reads: {reads}, Fetches: {fetches}")
            print("-" * 30)

def get_performance_recommendations():
    """Provide performance recommendations based on analysis."""
    
    print("\n💡 PERFORMANCE RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = [
        "✅ Added composite indexes for common query patterns",
        "✅ Added indexes for foreign key relationships",
        "✅ Added indexes for ordering operations",
        "✅ Added partial indexes for filtered queries",
        "",
        "🚀 Additional Optimizations:",
        "1. Consider adding materialized views for complex analytics queries",
        "2. Implement query result caching for frequently accessed data",
        "3. Add database connection pooling for better concurrency",
        "4. Consider partitioning large tables by date ranges",
        "5. Regular VACUUM and ANALYZE operations for optimal performance",
        "",
        "📊 Monitoring:",
        "1. Set up query performance monitoring",
        "2. Monitor slow query logs",
        "3. Track index usage statistics",
        "4. Monitor database connection pool metrics"
    ]
    
    for rec in recommendations:
        print(rec)

def main():
    """Main function to run all performance analysis."""
    try:
        analyze_query_performance()
        check_index_usage()
        get_performance_recommendations()
        
        print("\n✅ Performance analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during performance analysis: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

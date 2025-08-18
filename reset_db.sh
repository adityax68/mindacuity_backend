#!/bin/bash

# Health App Database Reset Script
# This script resets the database and optionally seeds it with test data

echo "🏥 Health App Database Reset"
echo "================================"

# Check if we're in the backend directory
if [ ! -d "app" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found. Please run 'python -m venv venv' first"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import sqlalchemy, fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: Required packages not installed. Please run 'pip install -r requirements.txt'"
    exit 1
fi

# Run the reset script
echo "🔄 Running database reset..."
if [ "$1" = "--seed" ]; then
    echo "🌱 Will seed database with test data"
    python reset_db.py --seed
else
    python reset_db.py
fi

# Check if reset was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database reset completed successfully!"
    echo ""
    echo "🚀 You can now start the application with:"
    echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
else
    echo ""
    echo "❌ Database reset failed!"
    exit 1
fi 
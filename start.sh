#!/bin/bash

# Set environment variable to fix tokenizers warning
export TOKENIZERS_PARALLELISM=false

# Activate virtual environment
source venv/bin/activate && 
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 

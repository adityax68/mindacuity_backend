#!/bin/bash

# Production Deployment Script for Password Reset Migration
# Usage: ./deploy_password_reset_migration.sh

set -e  # Exit on any error

echo "🚀 Password Reset Migration Deployment Script"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - UPDATE THESE FOR YOUR PRODUCTION ENVIRONMENT
BACKEND_DIR="/path/to/health_app/backend"
VENV_PATH="$BACKEND_DIR/venv"
DB_BACKUP_DIR="/path/to/backups"
SERVICE_NAME="health_app"  # systemd service name or pm2 app name

# Function to print colored output
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ️  $1${NC}"; }

# Check if running as correct user
print_info "Checking environment..."
cd "$BACKEND_DIR" || { print_error "Backend directory not found"; exit 1; }

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_PATH/bin/activate" || { print_error "Failed to activate venv"; exit 1; }
print_success "Virtual environment activated"

# Check current migration status
print_info "Checking current migration status..."
CURRENT_VERSION=$(alembic current 2>&1 | grep -oP '(?<=\s)[a-f0-9]{12}(?=\s|\()')
echo "Current migration: $CURRENT_VERSION"

# Preview migration SQL
print_info "Generating migration preview..."
alembic upgrade head --sql > /tmp/migration_preview.sql
print_warning "Migration SQL preview saved to /tmp/migration_preview.sql"
echo "First 30 lines:"
head -n 30 /tmp/migration_preview.sql

# Ask for confirmation
echo ""
read -p "⚠️  Do you want to proceed with the migration? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    print_error "Migration cancelled by user"
    exit 0
fi

# Create database backup timestamp
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
print_info "Creating database backup before migration..."
print_warning "Make sure you have a recent database backup!"
read -p "Have you created a database backup? (yes/no): " BACKUP_CONFIRM
if [ "$BACKUP_CONFIRM" != "yes" ]; then
    print_error "Please create a backup before proceeding"
    exit 1
fi
print_success "Backup confirmed"

# Apply migration
print_info "Applying migration..."
if alembic upgrade head; then
    print_success "Migration applied successfully!"
else
    print_error "Migration failed!"
    print_warning "You may need to rollback: alembic downgrade -1"
    exit 1
fi

# Verify migration
print_info "Verifying migration..."
NEW_VERSION=$(alembic current 2>&1 | grep -oP '(?<=\s)[a-f0-9]{12}(?=\s|\()')
if [ "$NEW_VERSION" = "abdaa4f06ec2" ]; then
    print_success "Migration version confirmed: $NEW_VERSION"
else
    print_error "Migration version mismatch. Expected: abdaa4f06ec2, Got: $NEW_VERSION"
    exit 1
fi

# Verify columns exist
print_info "Verifying database schema..."
python3 << 'EOF'
from app.database import engine
from sqlalchemy import inspect
import sys

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('users')]

required_columns = [
    'password_reset_token',
    'password_reset_expires_at', 
    'password_reset_attempts',
    'last_reset_attempt'
]

all_present = True
for col in required_columns:
    if col in columns:
        print(f"✅ {col} exists")
    else:
        print(f"❌ {col} MISSING")
        all_present = False
        
# Check index
indexes = inspector.get_indexes('users')
has_index = any(idx['name'] == 'ix_users_password_reset_token' for idx in indexes)
if has_index:
    print("✅ Index ix_users_password_reset_token exists")
else:
    print("❌ Index ix_users_password_reset_token MISSING")
    all_present = False

sys.exit(0 if all_present else 1)
EOF

if [ $? -eq 0 ]; then
    print_success "Schema verification passed"
else
    print_error "Schema verification failed"
    exit 1
fi

# Restart application
print_info "Migration complete. Please restart your application manually:"
echo "  - Systemd: sudo systemctl restart $SERVICE_NAME"
echo "  - PM2: pm2 restart $SERVICE_NAME"
echo "  - Docker: docker-compose restart backend"
echo "  - Gunicorn: pkill -HUP gunicorn"
echo ""

read -p "Do you want to restart the service now? (yes/no): " RESTART_CONFIRM
if [ "$RESTART_CONFIRM" = "yes" ]; then
    print_info "Restarting service..."
    # Uncomment the appropriate command for your setup:
    # sudo systemctl restart $SERVICE_NAME
    # pm2 restart $SERVICE_NAME
    # docker-compose restart backend
    print_warning "Please uncomment and configure the restart command in the script"
fi

print_success "Deployment completed successfully! 🎉"
echo ""
echo "Next steps:"
echo "1. Test the password reset endpoint"
echo "2. Monitor application logs for errors"
echo "3. Test password reset flow end-to-end"
echo ""
print_info "Rollback command if needed: alembic downgrade -1"


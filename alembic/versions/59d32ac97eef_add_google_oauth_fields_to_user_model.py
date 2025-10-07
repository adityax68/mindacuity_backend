"""Add Google OAuth fields to User model

Revision ID: 59d32ac97eef
Revises: 
Create Date: 2025-10-07 14:59:43.962908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59d32ac97eef'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add Google OAuth fields
    op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(), nullable=True))
    
    # Create index on google_id
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)
    
    # Make existing fields nullable for Google OAuth users (only if they exist)
    op.alter_column('users', 'username', nullable=True)
    op.alter_column('users', 'hashed_password', nullable=True)
    op.alter_column('users', 'full_name', nullable=True)
    
    # Set default value for auth_provider
    op.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL")
    
    # Make auth_provider NOT NULL after setting defaults
    op.alter_column('users', 'auth_provider', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index
    op.drop_index('ix_users_google_id', table_name='users')
    
    # Remove Google OAuth columns
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'google_id')
    
    # Restore NOT NULL constraints (be careful with existing data)
    op.alter_column('users', 'full_name', nullable=False)
    op.alter_column('users', 'hashed_password', nullable=False)
    op.alter_column('users', 'username', nullable=False)

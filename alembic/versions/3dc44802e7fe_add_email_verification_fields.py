"""add_email_verification_fields

Revision ID: 3dc44802e7fe
Revises: 85f8b33dfafc
Create Date: 2025-10-10 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3dc44802e7fe'
down_revision: Union[str, Sequence[str], None] = '85f8b33dfafc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email verification fields to users table."""
    # Add email verification columns to users table
    op.add_column('users', sa.Column('email_verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('email_verification_attempts', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('last_verification_attempt', sa.DateTime(timezone=True), nullable=True))
    
    # Create index on email verification token
    op.create_index(op.f('ix_users_email_verification_token'), 'users', ['email_verification_token'], unique=False)


def downgrade() -> None:
    """Remove email verification fields from users table."""
    # Drop index first
    op.drop_index(op.f('ix_users_email_verification_token'), table_name='users')
    
    # Drop email verification columns
    op.drop_column('users', 'last_verification_attempt')
    op.drop_column('users', 'email_verification_attempts')
    op.drop_column('users', 'email_verification_expires_at')
    op.drop_column('users', 'email_verification_token')
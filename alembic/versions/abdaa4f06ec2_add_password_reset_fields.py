"""add_password_reset_fields

Revision ID: abdaa4f06ec2
Revises: 3dc44802e7fe
Create Date: 2025-10-11 12:53:53.455529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abdaa4f06ec2'
down_revision: Union[str, Sequence[str], None] = '3dc44802e7fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add password reset fields to users table
    op.add_column('users', sa.Column('password_reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_reset_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('last_reset_attempt', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for performance
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_users_password_reset_token', table_name='users')
    
    # Remove password reset fields from users table
    op.drop_column('users', 'last_reset_attempt')
    op.drop_column('users', 'password_reset_attempts')
    op.drop_column('users', 'password_reset_expires_at')
    op.drop_column('users', 'password_reset_token')

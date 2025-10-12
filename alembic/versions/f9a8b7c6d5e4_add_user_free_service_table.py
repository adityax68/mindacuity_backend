"""add_user_free_service_table

Revision ID: f9a8b7c6d5e4
Revises: abdaa4f06ec2
Create Date: 2025-10-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a8b7c6d5e4'
down_revision: Union[str, Sequence[str], None] = 'abdaa4f06ec2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_free_service table
    op.create_table(
        'user_free_service',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('access_code', sa.String(20), nullable=False, index=True),
        sa.Column('subscription_token', sa.String(255), nullable=False),
        sa.Column('plan_type', sa.String(20), server_default='basic', nullable=False),
        sa.Column('has_used', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for performance
    op.create_index('ix_user_free_service_user_id', 'user_free_service', ['user_id'], unique=True)
    op.create_index('ix_user_free_service_access_code', 'user_free_service', ['access_code'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_user_free_service_access_code', table_name='user_free_service')
    op.drop_index('ix_user_free_service_user_id', table_name='user_free_service')
    
    # Drop user_free_service table
    op.drop_table('user_free_service')


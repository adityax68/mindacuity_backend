"""add_email_system_tables

Revision ID: 85f8b33dfafc
Revises: 21cc7471d905
Create Date: 2025-10-10 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '85f8b33dfafc'
down_revision: Union[str, Sequence[str], None] = '21cc7471d905'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email system tables."""
    # Email bounces table
    op.create_table('email_bounces',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('message_id', sa.String(length=255), nullable=True),
    sa.Column('bounce_type', sa.String(length=50), nullable=False),
    sa.Column('bounce_subtype', sa.String(length=50), nullable=False),
    sa.Column('bounce_reason', sa.Text(), nullable=True),
    sa.Column('diagnostic_code', sa.String(length=255), nullable=True),
    sa.Column('notification_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('feedback_id', sa.String(length=255), nullable=True),
    sa.Column('is_processed', sa.Boolean(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_bounces_email'), 'email_bounces', ['email'], unique=False)
    op.create_index(op.f('ix_email_bounces_id'), 'email_bounces', ['id'], unique=False)
    op.create_index(op.f('ix_email_bounces_message_id'), 'email_bounces', ['message_id'], unique=False)
    
    # Email complaints table
    op.create_table('email_complaints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('message_id', sa.String(length=255), nullable=True),
    sa.Column('complaint_type', sa.String(length=50), nullable=True),
    sa.Column('complaint_reason', sa.Text(), nullable=True),
    sa.Column('notification_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('feedback_id', sa.String(length=255), nullable=True),
    sa.Column('is_processed', sa.Boolean(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_complaints_email'), 'email_complaints', ['email'], unique=False)
    op.create_index(op.f('ix_email_complaints_id'), 'email_complaints', ['id'], unique=False)
    op.create_index(op.f('ix_email_complaints_message_id'), 'email_complaints', ['message_id'], unique=False)
    
    # Email logs table
    op.create_table('email_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('recipient_email', sa.String(length=255), nullable=False),
    sa.Column('template_name', sa.String(length=100), nullable=False),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('message_id', sa.String(length=255), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('bounced_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('complained_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('bounce_type', sa.String(length=50), nullable=True),
    sa.Column('bounce_subtype', sa.String(length=50), nullable=True),
    sa.Column('bounce_reason', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('template_data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_logs_id'), 'email_logs', ['id'], unique=False)
    op.create_index(op.f('ix_email_logs_message_id'), 'email_logs', ['message_id'], unique=False)
    op.create_index(op.f('ix_email_logs_recipient_email'), 'email_logs', ['recipient_email'], unique=False)
    
    # Email templates table
    op.create_table('email_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('subject_template', sa.Text(), nullable=False),
    sa.Column('html_template', sa.Text(), nullable=False),
    sa.Column('text_template', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('usage_count', sa.Integer(), nullable=True),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_templates_id'), 'email_templates', ['id'], unique=False)
    op.create_index(op.f('ix_email_templates_name'), 'email_templates', ['name'], unique=True)
    
    # Email unsubscribes table
    op.create_table('email_unsubscribes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('unsubscribed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('source', sa.String(length=100), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_unsubscribes_email'), 'email_unsubscribes', ['email'], unique=True)


def downgrade() -> None:
    """Remove email system tables."""
    # Drop email tables in reverse order
    op.drop_index(op.f('ix_email_unsubscribes_email'), table_name='email_unsubscribes')
    op.drop_table('email_unsubscribes')
    
    op.drop_index(op.f('ix_email_templates_name'), table_name='email_templates')
    op.drop_index(op.f('ix_email_templates_id'), table_name='email_templates')
    op.drop_table('email_templates')
    
    op.drop_index(op.f('ix_email_logs_recipient_email'), table_name='email_logs')
    op.drop_index(op.f('ix_email_logs_message_id'), table_name='email_logs')
    op.drop_index(op.f('ix_email_logs_id'), table_name='email_logs')
    op.drop_table('email_logs')
    
    op.drop_index(op.f('ix_email_complaints_message_id'), table_name='email_complaints')
    op.drop_index(op.f('ix_email_complaints_id'), table_name='email_complaints')
    op.drop_index(op.f('ix_email_complaints_email'), table_name='email_complaints')
    op.drop_table('email_complaints')
    
    op.drop_index(op.f('ix_email_bounces_message_id'), table_name='email_bounces')
    op.drop_index(op.f('ix_email_bounces_id'), table_name='email_bounces')
    op.drop_index(op.f('ix_email_bounces_email'), table_name='email_bounces')
    op.drop_table('email_bounces')
"""Add age column to users table

Revision ID: 8c07f8af3b28
Revises: 59d32ac97eef
Create Date: 2025-10-07 15:04:32.494103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c07f8af3b28'
down_revision: Union[str, Sequence[str], None] = '59d32ac97eef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if age column exists, if not add it
    connection = op.get_bind()
    
    # Check if the age column exists
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'age'
    """))
    
    if not result.fetchone():
        # Age column doesn't exist, add it
        op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
        print("Added age column to users table")
    else:
        # Age column exists, make it nullable
        op.alter_column('users', 'age', nullable=True)
        print("Made existing age column nullable")


def downgrade() -> None:
    """Downgrade schema."""
    # Check if age column exists
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'age'
    """))
    
    if result.fetchone():
        # Age column exists, remove it
        op.drop_column('users', 'age')
        print("Removed age column from users table")

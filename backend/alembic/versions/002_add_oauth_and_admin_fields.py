"""Add OAuth fields, is_admin column to users table and seed admin user

Revision ID: 002_add_oauth_and_admin_fields
Revises: 001_initial_schema
Create Date: 2026-08-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_oauth_and_admin_fields'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to users table
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('provider', sa.String(length=50), nullable=False, server_default='email'))
    op.add_column('users', sa.Column('provider_id', sa.String(length=255), nullable=True))
    
    # 2. Make hashed_password nullable for OAuth users
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=255), nullable=True)

    # 3. Seed or upgrade kkssakthikumaran@gmail.com to Admin
    op.execute("""
        UPDATE users 
        SET is_admin = true 
        WHERE LOWER(email) = 'kkssakthikumaran@gmail.com';
    """)


def downgrade() -> None:
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=255), nullable=False)
    op.drop_column('users', 'provider_id')
    op.drop_column('users', 'provider')
    op.drop_column('users', 'is_admin')

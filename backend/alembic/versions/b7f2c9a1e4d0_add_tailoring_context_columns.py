"""Add tailoring context columns

Revision ID: b7f2c9a1e4d0
Revises: 419961fe9d24
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7f2c9a1e4d0'
down_revision = '419961fe9d24'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('profiles', sa.Column('github_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('profiles', sa.Column('tailoring_instructions', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column('user_instructions', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('applications', 'user_instructions')
    op.drop_column('profiles', 'tailoring_instructions')
    op.drop_column('profiles', 'github_synced_at')

"""add resume doc table

Revision ID: 6e8681181d11
Revises: 
Create Date: 2025-07-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6e8681181d11'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'resumedoc',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('model_hash', sa.String(length=64), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('upload_dt', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('parsed_json', sa.JSON(), nullable=True),
        sa.Column('vector', sa.LargeBinary(), nullable=True),
        sa.UniqueConstraint('hash', 'model_hash', name='uq_resume_hash_model')
    )

def downgrade():
    op.drop_table('resumedoc')


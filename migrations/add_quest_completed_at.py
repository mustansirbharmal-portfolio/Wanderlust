"""Add completed_at to Quest model

This migration adds the completed_at timestamp field to the Quest model
and removes the completed boolean field.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    # Add completed_at column
    op.add_column('quest', sa.Column('completed_at', sa.DateTime, nullable=True))
    op.add_column('quest', sa.Column('points', sa.Integer, nullable=False, server_default='0'))
    
    # Drop completed column
    op.drop_column('quest', 'completed')

def downgrade():
    # Add back completed column
    op.add_column('quest', sa.Column('completed', sa.Boolean, nullable=False, server_default='0'))
    
    # Drop completed_at column
    op.drop_column('quest', 'completed_at')
    op.drop_column('quest', 'points')

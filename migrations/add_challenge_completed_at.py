"""Add completed_at field to Challenge model

This migration adds the completed_at datetime field to the Challenge model
to track when challenges are completed.
"""
from sqlalchemy import text

def upgrade(db):
    """Add completed_at column to challenge table"""
    # Add the completed_at column
    db.session.execute(text('ALTER TABLE challenge ADD COLUMN completed_at DATETIME'))
    
    # Update existing completed challenges
    db.session.execute(text('''
        UPDATE challenge 
        SET completed_at = created_at 
        WHERE completed = 1 AND completed_at IS NULL
    '''))
    
    db.session.commit()

def downgrade(db):
    """Remove completed_at column from challenge table"""
    db.session.execute(text('ALTER TABLE challenge DROP COLUMN completed_at'))
    db.session.commit()

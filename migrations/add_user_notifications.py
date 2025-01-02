"""Add notification preferences to User model

This migration adds email_notifications and push_notifications boolean fields
to the User model.
"""
from sqlalchemy import text

def upgrade(db):
    """Add notification columns to user table"""
    # Add the notification columns
    db.session.execute(text('ALTER TABLE user ADD COLUMN email_notifications BOOLEAN DEFAULT 1'))
    db.session.execute(text('ALTER TABLE user ADD COLUMN push_notifications BOOLEAN DEFAULT 1'))
    db.session.commit()

def downgrade(db):
    """Remove notification columns from user table"""
    db.session.execute(text('ALTER TABLE user DROP COLUMN email_notifications'))
    db.session.execute(text('ALTER TABLE user DROP COLUMN push_notifications'))
    db.session.commit()
